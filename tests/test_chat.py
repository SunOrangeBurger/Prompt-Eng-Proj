import tempfile
import threading
import time
import unittest
from pathlib import Path

from peogai.demo import DEMO_LOCK, DemoController, reset_demo
from peogai.review import fingerprint
from peogai.workspace import scan, snapshot
from test_demo import fake_model
from test_review import wait_for_review

PROJECT = Path(__file__).resolve().parents[1]
TEMP = PROJECT / ".peogai/test-tmp"
TEMP.mkdir(parents=True, exist_ok=True)


def wait_for_chat(controller: DemoController) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not controller.snapshot()["chat_busy"] and DEMO_LOCK.acquire(blocking=False):
            DEMO_LOCK.release()
            return
        time.sleep(.01)
    raise AssertionError("Chat did not finish")


class ChatTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(dir=TEMP)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        snapshot(PROJECT / "fixtures/demo", self.root / "fixtures/demo")
        reset_demo(self.root)
        self.calls: list[tuple[str, dict, str]] = []
        def chatter(message: str, context: dict, model: str) -> str:
            self.calls.append((message, context, model))
            return "This is a read-only explanation of the selected code."
        self.controller = DemoController("fake", 1, self.root, fake_model, chatter)
        self.issue = next(i for i in scan(self.root / "demo") if i.rule == "unsafe-eval")

    def test_question_uses_selected_source_and_never_applies(self) -> None:
        before = fingerprint(self.root / "demo")
        self.assertTrue(self.controller.ask(self.issue.path, "Why is this unsafe?"))
        wait_for_chat(self.controller)
        self.assertEqual(self.calls[0][1]["path"], self.issue.path)
        self.assertIn("eval(text)", self.calls[0][1]["source"])
        state = self.controller.snapshot()
        self.assertIsNone(state["pending"])
        self.assertEqual(state["events"][-1]["kind"], "assistant_message")
        self.assertEqual(fingerprint(self.root / "demo"), before)
        with self.assertRaises(ValueError):
            self.controller.ask("../outside.py", "Read this")
        with self.assertRaises(ValueError):
            self.controller.ask(self.issue.path, "x" * 2001)

    def test_follow_up_preserves_pending_review_and_forwards_request(self) -> None:
        contexts: list[dict] = []
        def generator(*args: object):
            contexts.append(args[1])
            return fake_model(*args)
        self.controller.generator = generator
        before = fingerprint(self.root / "demo")
        self.assertTrue(self.controller.start(self.issue.id, reset=False, request="Keep dictionary inputs working"))
        review = wait_for_review(self.controller)
        self.assertEqual(contexts[0]["reviewer_request"], "Keep dictionary inputs working")
        self.assertTrue(self.controller.ask(self.issue.path, "What risks remain in this patch?"))
        wait_for_chat(self.controller)
        self.assertIsNotNone(self.calls[0][1]["pending_review"])
        self.assertEqual(self.controller.snapshot()["pending"]["id"], review["id"])
        self.assertEqual(fingerprint(self.root / "demo"), before)
        self.controller.decision(review["id"], False, "Chat test")
        self.assertEqual(fingerprint(self.root / "demo"), before)

    def test_chat_blocks_mutations_until_finished_and_recovers_from_errors(self) -> None:
        entered, release = threading.Event(), threading.Event()
        def blocked(*args: object) -> str:
            entered.set()
            release.wait(5)
            raise RuntimeError("Test model failure")
        self.controller.chatter = blocked
        try:
            self.assertTrue(self.controller.ask(self.issue.path, "Explain this"))
            self.assertTrue(entered.wait(2))
            self.assertFalse(self.controller.reset())
            self.assertFalse(self.controller.start(self.issue.id, reset=False))
            self.assertFalse(self.controller.ask(self.issue.path, "A second question"))
        finally:
            release.set()
            wait_for_chat(self.controller)
        self.assertEqual(self.controller.snapshot()["events"][-1]["kind"], "chat_error")
        self.assertTrue(self.controller.reset())
