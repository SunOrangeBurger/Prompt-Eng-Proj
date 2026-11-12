import json
import tempfile
import unittest
from pathlib import Path

from peogai.engine import edit_source, repair, scope_check, validate
from peogai.model import parse
from peogai.types import Edit, Proposal
from peogai.workspace import resolve, scan, snapshot

PROJECT = Path(__file__).resolve().parents[1]
DEMO = PROJECT / "fixtures" / "demo"
TEST_TMP = PROJECT / ".peogai" / "test-tmp"
TEST_TMP.mkdir(parents=True, exist_ok=True)


class AgentTests(unittest.TestCase):
    def test_scan_and_cross_repo_tests(self) -> None:
        self.assertEqual({i.rule for i in scan(DEMO)}, {"unsafe-eval", "redundant-bool"})
        checks = validate(DEMO, True)
        self.assertTrue(next(c for c in checks if c.name == "tests:pricing-lib").passed)
        self.assertFalse(next(c for c in checks if c.name == "tests:shop-service").passed)

    def test_path_escape(self) -> None:
        with self.assertRaises(ValueError):
            resolve(DEMO, "../outside.py")

    def test_invalid_model_response(self) -> None:
        with self.assertRaises(ValueError):
            parse('{"explanation":"x","edits":[{"old":"","new":"x"}]}')
        with self.assertRaises(ValueError):
            edit_source("abc abc", Proposal("", [Edit("abc", "def")]))

    def test_reject_unrelated_changes(self) -> None:
        issue = next(i for i in scan(DEMO) if i.rule == "redundant-bool")
        before = resolve(DEMO, issue.path).read_text(encoding="utf-8")
        with self.assertRaises(ValueError):
            scope_check(before, before.replace("return total\n", "return 0\n"), issue)

    def test_retry_and_original_preserved(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            root = Path(temp) / "workspace"
            snapshot(DEMO, root)
            issue = next(i for i in scan(root) if i.rule == "unsafe-eval")
            original = resolve(root, issue.path).read_bytes()
            calls = 0
            def fake(*args: object) -> Proposal:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return Proposal("bad", [Edit("missing text", "x")])
                return Proposal("Parse literals without executing code", [
                    Edit("    value = eval(text)", "    import ast\n    value = ast.literal_eval(text)")])
            run = repair(root, issue.id, "fake", 2, True, fake)
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["status"], "validated")
            self.assertEqual(len(report["attempts"]), 2)
            self.assertEqual(resolve(root, issue.path).read_bytes(), original)
            self.assertTrue((run / "patch.diff").exists())

    def test_tests_gate_validation(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            root = Path(temp) / "workspace"
            snapshot(DEMO, root)
            issue = next(i for i in scan(root) if i.rule == "unsafe-eval")
            def fake(*args: object) -> Proposal:
                return Proposal("Break public behavior", [Edit("    value = eval(text)", "    value = {}")])
            run = repair(root, issue.id, "fake", 1, True, fake)
            report = json.loads((run / "report.json").read_text())
            self.assertEqual(report["status"], "rejected")
            self.assertFalse((run / "patch.diff").exists())


if __name__ == "__main__":
    unittest.main()
