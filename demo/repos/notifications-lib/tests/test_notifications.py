import unittest

from notifications_lib import format_digest, loyalty_message, should_notify


class NotificationTests(unittest.TestCase):
    def test_opted_in(self) -> None:
        self.assertIs(should_notify("a@example.test", True), True)

    def test_opted_out(self) -> None:
        self.assertIs(should_notify("a@example.test", False), False)

    def test_missing_email(self) -> None:
        self.assertIs(should_notify("", True), False)

    def test_empty_digest(self) -> None:
        self.assertEqual(format_digest([]), "No updates")

    def test_nonempty_digest(self) -> None:
        self.assertEqual(format_digest(["one", "two"]), "one, two")

    def test_loyalty_threshold(self) -> None:
        self.assertEqual(loyalty_message(100), "Discount unlocked")
        self.assertEqual(loyalty_message(99), "Keep shopping")
