import json
import tempfile
import time
import unittest
from pathlib import Path

from peogai.demo import DEMO_LOCK, DemoController, reset_demo, run_demo
from peogai.engine import regression_gates, validate, test_cases
from peogai.review import fingerprint
from peogai.types import Check
from peogai.workspace import scan, snapshot
from test_demo import fake_model

PROJECT = Path(__file__).resolve().parents[1]
TEMP = PROJECT / ".peogai/test-tmp"
TEMP.mkdir(parents=True, exist_ok=True)


def wait_for_review(controller: DemoController) -> dict:
    until = time.monotonic() + 25
    while time.monotonic() < until:
        state = controller.snapshot()
        if state["status"] != "running" and DEMO_LOCK.acquire(blocking=False):
            DEMO_LOCK.release()
            if state["status"] != "awaiting_review":
                raise AssertionError(state)
            return state["pending"]
        time.sleep(.02)
    raise AssertionError("Review preparation timed out")


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(dir=TEMP)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        snapshot(PROJECT / "fixtures/demo", self.root / "fixtures/demo")
        reset_demo(self.root)
        self.controller = DemoController("fake", 1, self.root, fake_model)
        self.issue = next(i for i in scan(self.root / "demo") if i.rule == "unsafe-eval")

    def propose(self) -> dict:
        self.assertTrue(self.controller.start(self.issue.id, reset=False))
        return wait_for_review(self.controller)

    def test_generation_does_not_apply_approval_applies_once(self) -> None:
        original = fingerprint(self.root / "demo")
        review = self.propose()
        self.assertEqual(fingerprint(self.root / "demo"), original)
        self.assertTrue(any(c["baseline_failures"] for c in review["checks"]))
        with self.assertRaises(ValueError):
            self.controller.decision("wrong-id", True)
        self.assertEqual(fingerprint(self.root / "demo"), original)
        self.controller.decision(review["id"], True, "Reviewed the code and tests")
        self.assertNotEqual(fingerprint(self.root / "demo"), original)
        self.assertEqual(len(scan(self.root / "demo")), 5)
        with self.assertRaises(ValueError):
            self.controller.decision(review["id"], True)
        audit = json.loads((self.root / ".peogai/review-history.jsonl").read_text())
        self.assertEqual(audit["decision"], "approved")

    def test_reject_preserves_source_and_records_reason(self) -> None:
        original = fingerprint(self.root / "demo")
        review = self.propose()
        self.controller.decision(review["id"], False, "Need more coverage")
        self.assertEqual(fingerprint(self.root / "demo"), original)
        audit = json.loads((self.root / ".peogai/review-history.jsonl").read_text())
        self.assertEqual(audit["reason"], "Need more coverage")
        next_review = self.propose()
        with self.assertRaises(ValueError):
            self.controller.decision(review["id"], True)
        self.controller.decision(next_review["id"], False)

    def test_external_change_blocks_apply_and_reset_invalidates_review(self) -> None:
        review = self.propose()
        target = self.root / "demo" / self.issue.path
        before = target.read_bytes()
        manifest = self.root / "demo/workspace.json"
        manifest.write_text(manifest.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "Workspace changed"):
            self.controller.decision(review["id"], True)
        self.assertEqual(target.read_bytes(), before)
        target.write_text("def broken(\n")
        self.assertTrue(self.controller.reset())
        with self.assertRaises(ValueError):
            self.controller.decision(review["id"], True)
        self.assertEqual(len(scan(self.root / "demo")), 6)

    def test_no_implicit_console_approval(self) -> None:
        summary = run_demo("fake", 1, True, lambda *_: None, self.root, fake_model)
        self.assertEqual(summary["status"], "awaiting_review")
        self.assertEqual(len(scan(self.root / "demo")), 6)

    def test_inventory_and_new_regression_gates(self) -> None:
        baseline = [Check("tests:x", False, "test_ok (suite.X) ... ok\ntest_bad (suite.X) ... FAIL\nFAILED (failures=1)")]
        unchanged = regression_gates(baseline, baseline)
        self.assertTrue(all(c.passed for c in unchanged))
        broken = [Check("tests:x", False, "test_ok (suite.X) ... ERROR\ntest_bad (suite.X) ... FAIL\nFAILED (failures=1, errors=1)")]
        self.assertFalse(all(c.passed for c in regression_gates(baseline, broken)))
        lost = [Check("tests:x", True, "test_ok (suite.X) ... ok")]
        self.assertFalse(all(c.passed for c in regression_gates(baseline, lost)))

    def test_fixture_scale_and_baseline(self) -> None:
        checks = validate(self.root / "demo", True)
        cases = test_cases(checks)
        self.assertEqual(len(cases), 25)
        self.assertEqual(sum(v == "FAIL" for v in cases.values()), 3)
