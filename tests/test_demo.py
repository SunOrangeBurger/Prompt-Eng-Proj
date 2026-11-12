import json
import tempfile
import unittest
from pathlib import Path

from peogai.demo import reset_demo, run_demo
from peogai.types import Edit, Proposal
from peogai.workspace import scan, snapshot

PROJECT = Path(__file__).resolve().parents[1]
TEMP = PROJECT / ".peogai" / "test-tmp"
TEMP.mkdir(parents=True, exist_ok=True)


def fake_model(*args: object) -> Proposal:
    issue = args[0]
    if getattr(issue, "rule") == "unsafe-eval":
        return Proposal("Literal parsing", [Edit("    value = eval(text)",
                                                "    import ast\n    value = ast.literal_eval(text)")])
    return Proposal("Simplify boolean return", [Edit(
        "    if total >= 100:\n        return True\n    else:\n        return False",
        "    return bool(total >= 100)")])


class DemoTests(unittest.TestCase):
    def test_two_runs_restore_fixtures_and_apply_fixes(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP) as temp:
            root = Path(temp)
            snapshot(PROJECT / "fixtures/demo", root / "fixtures/demo")
            sentinel = root / "keep.txt"
            sentinel.write_text("keep")
            events: list[tuple[str, dict]] = []
            def emit(kind: str, data: dict) -> None:
                events.append((kind, data))
            for _ in range(2):
                events.clear()
                summary = run_demo("fake", 1, True, emit, root, fake_model)
                self.assertEqual(summary["status"], "completed")
                self.assertEqual(summary["remaining_findings"], 0)
                self.assertEqual(len(events[0][1]["issues"]), 2)
                self.assertEqual(events[0][0], "reset")
                self.assertEqual(sum(kind == "applied" for kind, _ in events), 2)
                self.assertIn("proposal", [kind for kind, _ in events])
                self.assertIn("validation", [kind for kind, _ in events])
                self.assertEqual(len(scan(root / "demo")), 0)
                self.assertEqual(len(scan(root / "fixtures/demo")), 2)
                self.assertEqual(sentinel.read_text(), "keep")
            (root / "demo" / "extra.txt").write_text("temporary")
            reset_demo(root)
            self.assertFalse((root / "demo" / "extra.txt").exists())
            self.assertEqual(len(scan(root / "demo")), 2)
            history = (root / ".peogai/demo-history.jsonl").read_text().splitlines()
            self.assertEqual(len(history), 2)
            self.assertTrue(all(json.loads(line)["status"] == "completed" for line in history))

    def test_invalid_attempts_do_not_reset_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP) as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                run_demo("fake", 0, True, lambda *_: None, root, fake_model)
            self.assertFalse((root / "demo").exists())

    def test_reset_requires_pristine_fixture(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEMP) as temp:
            root = Path(temp)
            (root / "demo").mkdir()
            marker = root / "demo" / "keep.txt"
            marker.write_text("keep")
            with self.assertRaises(ValueError):
                reset_demo(root)
            self.assertTrue(marker.exists())
