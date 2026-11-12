import ast
import difflib
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .model import propose
from .types import Check, EventSink, Issue, Proposal
from .workspace import context, files, load, resolve, scan, snapshot


def validate(root: Path, run_tests: bool) -> list[Check]:
    checks: list[Check] = []
    try:
        for entry in load(root)["repos"].values():
            for path in files(resolve(root, entry["path"])):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
        checks.append(Check("syntax", True, "All Python sources compile"))
    except (SyntaxError, ValueError) as exc:
        return [Check("syntax", False, str(exc))]
    if not run_tests:
        return checks + [Check("tests", False, "Not run; use --run-tests for trusted workspace code")]
    config = load(root)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(resolve(root, entry["path"])) for entry in config["repos"].values())
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for repo, entry in config["repos"].items():
        test_dir = resolve(root, entry["path"]) / "tests"
        if not test_dir.is_dir():
            continue
        try:
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-v"],
                cwd=root, env=env, capture_output=True, text=True, timeout=30)
            output = (result.stdout + result.stderr)[-12_000:]
            # unittest exits 0 even if it discovers no tests.
            checks.append(Check(f"tests:{repo}", result.returncode == 0 and "Ran 0 tests" not in output, output))
        except subprocess.TimeoutExpired:
            checks.append(Check(f"tests:{repo}", False, "Exceeded 30 seconds"))
    if len(checks) == 1:
        checks.append(Check("tests", False, "No test directories discovered"))
    return checks


def edit_source(source: str, proposal: Proposal) -> str:
    for edit in proposal.edits:
        if source.count(edit.old) != 1:
            raise ValueError("Each old text must match exactly once")
        source = source.replace(edit.old, edit.new, 1)
    return source


def scope_check(before: str, after: str, issue: Issue) -> None:
    """Only imports and the enclosing top-level definition may change."""
    a, b = ast.parse(before), ast.parse(after)
    selected = [i for i, n in enumerate(a.body) if n.lineno <= issue.line <= (n.end_lineno or n.lineno)]
    if len(selected) != 1:
        raise ValueError("Cannot localize issue")
    node = a.body[selected[0]]
    def unrelated(tree: ast.Module, original: bool) -> list[str]:
        result: list[str] = []
        for n in tree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                continue
            if (original and n is node) or (not original and isinstance(n, type(node))
                    and getattr(n, "name", None) == getattr(node, "name", None)):
                continue
            result.append(ast.dump(n, include_attributes=False))
        return result
    if unrelated(a, True) != unrelated(b, False):
        raise ValueError("Patch changes unrelated top-level code")
    changes = sum(line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
                  for line in difflib.unified_diff(before.splitlines(), after.splitlines()))
    if changes > 60:
        raise ValueError("Patch exceeds the 60 changed-line budget")


def repair(root: Path, issue_id: str, model: str, attempts: int, run_tests: bool,
           generator: Callable[..., Proposal] = propose, emit: EventSink | None = None) -> Path:
    started = time.monotonic()
    def event(kind: str, **data: Any) -> None:
        if emit is not None:
            emit(kind, data)
    root = root.resolve()
    issues = scan(root)
    issue = next((i for i in issues if i.id == issue_id), None)
    if issue is None:
        raise ValueError(f"Unknown issue {issue_id}; run scan first")
    if not 1 <= attempts <= 3:
        raise ValueError("Attempts must be between 1 and 3")
    run = root / ".peogai" / "runs" / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + issue.id)
    run.mkdir(parents=True)
    baseline = run / "baseline"
    snapshot(root, baseline)
    baseline_checks = validate(baseline, run_tests)
    event("baseline", issue=asdict(issue), checks=[asdict(c) for c in baseline_checks])
    source = resolve(baseline, issue.path).read_text(encoding="utf-8")
    ctx = context(baseline, issue)
    (run / "context.json").write_text(json.dumps(ctx, indent=2), encoding="utf-8")
    event("context", issue=asdict(issue), files=list(ctx["related_files"]), symbol=ctx["editable_symbol"])
    report: dict[str, Any] = {"issue": asdict(issue), "model": model, "status": "rejected",
        "baseline": [asdict(c) for c in baseline_checks], "attempts": [],
        "limitations": ["A filesystem copy is not a security sandbox.",
            "Passing tests and two heuristic rules do not prove security or behavior equivalence.",
            "No dependency CVE scan, data-flow analysis, fuzzing or automatic source application."]}
    feedback = ""
    before_signatures = {(i.path, i.rule) for i in issues}
    for attempt in range(1, attempts + 1):
        record: dict[str, Any] = {"attempt": attempt}
        try:
            event("generating", issue=asdict(issue), attempt=attempt, model=model)
            proposal = generator(issue, ctx, model, feedback)
            record["proposal"] = asdict(proposal)
            updated = edit_source(source, proposal)
            diff = "".join(difflib.unified_diff(source.splitlines(keepends=True), updated.splitlines(keepends=True),
                                               fromfile="a/" + issue.path, tofile="b/" + issue.path))
            event("proposal", issue=asdict(issue), attempt=attempt, explanation=proposal.explanation,
                  diff=diff, before=source, after=updated)
            scope_check(source, updated, issue)
            candidate = run / f"candidate-{attempt}"
            snapshot(baseline, candidate)
            resolve(candidate, issue.path).write_text(updated, encoding="utf-8")
            remaining = scan(candidate)
            removed = not any(i.path == issue.path and i.rule == issue.rule and
                              i.line <= issue.end_line for i in remaining)
            introduced = {(i.path, i.rule) for i in remaining} - before_signatures
            checks = [Check("target-rule", removed, "Targeted finding must disappear"),
                      Check("static-regressions", not introduced, str(sorted(introduced)))]
            checks += validate(candidate, run_tests)
            event("validation", issue=asdict(issue), attempt=attempt, checks=[asdict(c) for c in checks])
            record["checks"] = [asdict(c) for c in checks]
            diff = "".join(difflib.unified_diff(source.splitlines(keepends=True), updated.splitlines(keepends=True),
                                               fromfile="a/" + issue.path, tofile="b/" + issue.path))
            (run / f"attempt-{attempt}.diff").write_text(diff, encoding="utf-8")
            if all(c.passed for c in checks):
                report["status"] = "validated"
                report["candidate"] = str(candidate)
                (run / "patch.diff").write_text(diff, encoding="utf-8")
            feedback = json.dumps(record["checks"])[-12_000:]
        except (ValueError, SyntaxError, RuntimeError, KeyError, TypeError, OSError) as exc:
            record["error"] = str(exc)
            feedback = json.dumps(record)[-12_000:]
            event("rejected", issue=asdict(issue), attempt=attempt, error=str(exc))
        report["attempts"].append(record)
        (run / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if report["status"] == "validated":
            break
    report["source_sha256"] = hashlib.sha256(source.encode()).hexdigest()
    report["duration_seconds"] = round(time.monotonic() - started, 3)
    (run / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [f"# Repair: {report['status']}", "", issue.message, "", f"Target: {issue.path}:{issue.line}",
             f"Model: {model}", f"Attempts: {len(report['attempts'])}",
             f"Duration: {report['duration_seconds']} seconds", "",
             "Original workspace unchanged. Review patch.diff and report.json.", "", "## Baseline"]
    lines += [f"- {'PASS' if c.passed else 'FAIL'}: {c.name}" for c in baseline_checks]
    for record in report["attempts"]:
        lines += ["", f"## Attempt {record['attempt']}", ""]
        if "proposal" in record:
            lines += [record["proposal"]["explanation"], ""]
        if "error" in record:
            lines += [f"Rejected: {record['error']}"]
        lines += [f"- {'PASS' if c['passed'] else 'FAIL'}: {c['name']}" for c in record.get("checks", [])]
    lines += ["", "## Limits", *[f"- {s}" for s in report["limitations"]]]
    (run / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    event("repair_finished", issue=asdict(issue), status=report["status"], run=str(run),
          duration_seconds=report["duration_seconds"])
    return run
