"""Read-only detector audit: planted ground truth and independent challenge cases."""
import hashlib
import json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from peogai.workspace import scan
from peogai.engine import validate, test_cases

PROJECT = Path(__file__).resolve().parents[1]
# Independently specified locations, not inferred from detector output.
GOLD = {
    ("repos/documents-lib/documents_lib.py", 5, "unchecked-path"),
    ("repos/records-lib/records_lib.py", 6, "sql-interpolation"),
    ("repos/settings-lib/settings_lib.py", 5, "unsafe-eval"),
    ("repos/notifications-lib/notifications_lib.py", 6, "redundant-bool"),
    ("repos/notifications-lib/notifications_lib.py", 13, "empty-list-check"),
    ("repos/pricing-lib/pricing_lib.py", 5, "redundant-bool"),
}
CASES = [
    ("direct eval", "def f(x):\n    return eval(x)\n", ["unsafe-eval"]),
    ("qualified builtin eval", "import builtins\ndef f(x):\n    return builtins.eval(x)\n", ["unsafe-eval"]),
    ("aliased eval", "from builtins import eval as run\ndef f(x):\n    return run(x)\n", ["unsafe-eval"]),
    ("shadowed safe eval", "def eval(x):\n    return x\ndef f(x):\n    return eval(x)\n", []),
    ("literal eval", "import ast\ndef f(x):\n    return ast.literal_eval(x)\n", []),
    ("comment and string", "# eval(x)\ntext = 'eval(x)'\n", []),
    ("direct SQL f-string", "def f(db,x):\n    return db.execute(f\"SELECT * FROM orders WHERE name='{x}'\")\n", ["sql-interpolation"]),
    ("concatenated SQL", "def f(db,x):\n    return db.execute(\"SELECT * FROM orders WHERE name='\"+x+\"'\")\n", ["sql-interpolation"]),
    ("SQL in variable", "def f(db,x):\n    query=f\"SELECT * FROM orders WHERE name='{x}'\"\n    return db.execute(query)\n", ["sql-interpolation"]),
    ("SQL format", "def f(db,x):\n    return db.execute(\"SELECT * FROM orders WHERE name='{}'\".format(x))\n", ["sql-interpolation"]),
    ("bound SQL parameters", "def f(db,x):\n    return db.execute('SELECT * FROM orders WHERE name=?',(x,))\n", []),
    ("constant SQL f-string", "def f(db):\n    return db.execute(f'SELECT 1')\n", []),
    ("non-SQL execute API", "def f(renderer,x):\n    return renderer.execute(f'Hello {x}')\n", []),
    ("direct unchecked path", "from pathlib import Path\ndef f(root,name):\n    return (Path(root)/name).read_text()\n", ["unchecked-path"]),
    ("unchecked path via variable", "from pathlib import Path\ndef f(root,name):\n    base=Path(root)\n    return (base/name).read_text()\n", ["unchecked-path"]),
    ("aliased Path", "from pathlib import Path as P\ndef f(root,name):\n    return (P(root)/name).read_text()\n", ["unchecked-path"]),
    ("lexical guard without normalization", "from pathlib import Path\ndef f(root,name):\n    path=Path(root)/name\n    if not path.is_relative_to(Path(root)):\n        raise ValueError('escape')\n    return path.read_text()\n", ["unchecked-path"]),
    ("unused containment check", "from pathlib import Path\ndef f(root,name):\n    path=Path(root)/name\n    path.is_relative_to(Path(root))\n    return path.read_text()\n", ["unchecked-path"]),
    ("fixed trusted path", "from pathlib import Path\ndef f():\n    return (Path('/app')/'readme.txt').read_text()\n", []),
    ("resolved and enforced containment", "from pathlib import Path\ndef f(root,name):\n    base=Path(root).resolve()\n    path=(base/name).resolve()\n    if not path.is_relative_to(base):\n        raise ValueError('escape')\n    return path.read_text()\n", []),
    ("boolean branch", "def f(x):\n    if x:\n        return True\n    else:\n        return False\n", ["redundant-bool"]),
    ("empty list", "def f(items: list[str]):\n    return len(items)==0\n", ["empty-list-check"]),
    ("custom container intentional length check", "class C:\n    def __len__(self):\n        return 0\n    def __bool__(self):\n        return True\ndef f(items: C):\n    return len(items)==0\n", []),
    ("already simplified boolean", "def f(x):\n    return bool(x)\n", []),
]


def main() -> None:
    output = PROJECT / "docs/detection-audit.json"
    temp = PROJECT / ".peogai/detection-audit"
    temp.mkdir(parents=True, exist_ok=True)
    live = PROJECT / "demo/repos/documents-lib/documents_lib.py"
    original = hashlib.sha256(live.read_bytes()).hexdigest()
    fixture = scan(PROJECT / "fixtures/demo")
    found = {(i.path, i.line, i.rule) for i in fixture}
    results = []
    coverage: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(dir=temp) as folder:
        root = Path(folder)
        (root / "repo").mkdir()
        (root / "workspace.json").write_text(json.dumps({"repos": {"probe": {"path": "repo"}}}))
        for title, source, expected in CASES:
            (root / "repo/probe.py").write_text(source, encoding="utf-8")
            actual = sorted(i.rule for i in scan(root))
            results.append({"case": title, "expected": sorted(expected), "actual": actual,
                            "matches": actual == sorted(expected)})
        (root / "repo/probe.py").write_text("def f(x):\n    return eval(x)\n")
        (root / "repo/oversized.py").write_text("#" + "x" * 64_000 + "\neval(user_input)\n")
        coverage["oversized_source_is_silently_skipped"] = not any(i.path.endswith("oversized.py") for i in scan(root))
        (root / "repo/broken.py").write_text("def broken(\n")
        try:
            scan(root)
            coverage["syntax_error_aborts_scan"] = False
        except SyntaxError:
            coverage["syntax_error_aborts_scan"] = True
    live_findings = [asdict(i) for i in scan(PROJECT / "demo")]
    assert hashlib.sha256(live.read_bytes()).hexdigest() == original
    report = {"date": "2026-11-16", "planted_expected": len(GOLD), "planted_detected": len(GOLD & found),
              "planted_missing": sorted(GOLD - found), "planted_extra": sorted(found - GOLD),
              "challenge_cases": len(results), "challenge_matches": sum(r["matches"] for r in results),
              "challenge_results": results, "live_findings": live_findings,
              "coverage_behavior": coverage,
              "live_documents_source_preserved": True,
              "warning": "Curated probes are not a representative benchmark. Matching all planted patterns does not imply complete error detection."}
    report["missed_detection_cases"] = sum(bool(r["expected"]) and not r["actual"] for r in results)
    report["false_positive_cases"] = sum(not r["expected"] and bool(r["actual"]) for r in results)
    for label, path in (("pristine", PROJECT / "fixtures/demo"), ("live", PROJECT / "demo")):
        checks = validate(path, True)
        cases = test_cases(checks)
        report[label + "_tests"] = {"total": len(cases), "passed": sum(v == "ok" for v in cases.values()),
                                     "failed": [k for k, v in cases.items() if v != "ok"],
                                     "checks": [{"name": c.name, "passed": c.passed} for c in checks]}
    assert hashlib.sha256(live.read_bytes()).hexdigest() == original
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Planted: {report['planted_detected']}/{len(GOLD)}; extra: {len(found-GOLD)}")
    print(f"Challenge cases matching expectation: {report['challenge_matches']}/{len(results)}")
    for row in results:
        if not row["matches"]:
            print(f"MISMATCH: {row['case']}: expected {row['expected']}, got {row['actual']}")
    print(f"Live workspace: {len(live_findings)} findings; existing edit preserved")
    print(output)


if __name__ == "__main__":
    main()
