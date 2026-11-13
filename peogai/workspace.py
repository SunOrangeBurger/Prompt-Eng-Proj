import ast
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .types import Issue

IGNORED = {".git", ".peogai", ".venv", "venv", "node_modules", "__pycache__"}
MAX_FILE_BYTES = 64_000


def is_link(path: Path) -> bool:
    return path.is_symlink() or (path.exists() and bool(getattr(path.lstat(), "st_file_attributes", 0) & 1024))


def load(root: Path) -> dict[str, Any]:
    raw = json.loads((root / "workspace.json").read_text(encoding="utf-8"))
    repos = raw.get("repos")
    if not isinstance(repos, dict) or not repos:
        raise ValueError("workspace.json requires a nonempty repos object")
    for name, entry in repos.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError("Invalid repository definition")
        resolve(root, entry["path"])
        if not isinstance(entry.get("depends_on", []), list):
            raise ValueError("depends_on must be a list")
        if any(dep not in repos for dep in entry.get("depends_on", [])):
            raise ValueError(f"Unknown dependency in {name}")
    return raw


def resolve(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Paths must be relative and stay within the workspace")
    path = root / relative
    current = path
    while current != root:
        if is_link(current):
            raise ValueError(f"Links are not supported: {relative}")
        current = current.parent
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Path escapes workspace")
    return path


def files(root: Path) -> list[Path]:
    result: list[Path] = []
    def walk(folder: Path) -> None:
        for p in sorted(folder.iterdir()):
            if p.name in IGNORED or is_link(p):
                continue
            if p.is_dir():
                walk(p)
            elif p.suffix == ".py" and p.stat().st_size <= MAX_FILE_BYTES:
                result.append(p)
    walk(root)
    return result


def scan(root: Path) -> list[Issue]:
    config = load(root)
    issues: list[Issue] = []
    for repo, entry in config["repos"].items():
        for path in files(resolve(root, entry["path"])):
            if "tests" in path.relative_to(root).parts or path.name.startswith("test_"):
                continue
            relative = path.relative_to(root).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=relative)
            for node in ast.walk(tree):
                rule = message = ""
                kind = "security"
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "eval":
                    rule, message = "unsafe-eval", "eval executes input as code. Use ast.literal_eval for literal data."
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                      and node.func.attr == "execute" and node.args and isinstance(node.args[0], ast.JoinedStr)):
                    rule, message = "sql-interpolation", "Interpolating input into SQL can change the query. Bind values with placeholders."
                elif (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                      and any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)
                              and isinstance(n.left, ast.Call) and isinstance(n.left.func, ast.Name)
                              and n.left.func.id == "Path" for n in ast.walk(node))
                      and not any(isinstance(n, ast.Attribute) and n.attr == "is_relative_to" for n in ast.walk(node))):
                    rule, message = "unchecked-path", "A user filename is joined to a root without checking containment. Resolve both paths and reject escapes."
                elif (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq)
                      and isinstance(node.left, ast.Call) and isinstance(node.left.func, ast.Name)
                      and node.left.func.id == "len" and len(node.left.args) == 1
                      and isinstance(node.comparators[0], ast.Constant) and node.comparators[0].value == 0):
                    kind = "refactor"
                    rule, message = "empty-list-check", "For this list parameter, replace len(items) == 0 with not items. Preserve the surrounding function."
                elif isinstance(node, ast.If) and len(node.body) == 1 and len(node.orelse) == 1:
                    a, b = node.body[0], node.orelse[0]
                    if (isinstance(a, ast.Return) and isinstance(b, ast.Return)
                        and isinstance(a.value, ast.Constant) and a.value.value is True
                        and isinstance(b.value, ast.Constant) and b.value.value is False):
                        rule, message = "redundant-bool", "Replace the if/else returning True/False with return bool(condition)."
                        kind = "refactor"
                if rule:
                    scope = next((n for n in tree.body if n.lineno <= node.lineno <= (n.end_lineno or n.lineno)), node)
                    identity = f"{relative}:{getattr(scope, 'name', '<module>')}:{node.lineno - scope.lineno}:{rule}"
                    oracle = {"unsafe-eval": "test_reject_executable_settings", "sql-interpolation": "test_sql_injection",
                              "unchecked-path": "test_path_traversal"}.get(rule, "")
                    issues.append(Issue(hashlib.sha256(identity.encode()).hexdigest()[:10], repo,
                                        relative, node.lineno, node.end_lineno or node.lineno,
                                        "security" if kind == "security" else "refactor", rule, message, oracle))
    return sorted(issues, key=lambda i: (i.kind != "security", i.path, i.line))


def context(root: Path, issue: Issue) -> dict[str, Any]:
    """Bounded lexical retrieval; no embedding server or vector database."""
    config = load(root)
    target = resolve(root, issue.path).read_text(encoding="utf-8")
    tree = ast.parse(target)
    enclosing = next(n for n in tree.body if n.lineno <= issue.line <= (n.end_lineno or n.lineno))
    symbols = {n.name for n in ast.walk(ast.parse(target)) if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    ranked: list[tuple[int, str, str]] = []
    for entry in config["repos"].values():
        for path in files(resolve(root, entry["path"])):
            rel = path.relative_to(root).as_posix()
            if rel == issue.path:
                continue
            source = path.read_text(encoding="utf-8")
            score = sum(source.count(s) for s in symbols) + (2 if path.name.startswith("test") else 0)
            if score:
                ranked.append((score, rel, source))
    budget = 12_000
    retrieved: dict[str, str] = {}
    for _, rel, source in sorted(ranked, reverse=True)[:4]:
        retrieved[rel] = source[:min(budget, 4000)]
        budget -= len(retrieved[rel])
        if budget <= 0:
            break
    return {"dependency_graph": config["repos"], "target": target,
            "editable_symbol": getattr(enclosing, "name", "<module statement>"),
            "editable_source": ast.get_source_segment(target, enclosing),
            "read_only_symbols": [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                                  and n is not enclosing],
            "related_files": retrieved}


def snapshot(root: Path, destination: Path) -> None:
    def ignore(folder: str, names: list[str]) -> list[str]:
        return [name for name in names if name in IGNORED or
                is_link(Path(folder) / name)]
    shutil.copytree(root, destination, ignore=ignore)
