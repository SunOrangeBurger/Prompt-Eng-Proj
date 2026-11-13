import unittest
import sqlite3
import tempfile
from pathlib import Path

from shop_service import checkout, customer_summary, invoice_preview, notification_label


class ShopTests(unittest.TestCase):
    def test_shared_libraries(self) -> None:
        self.assertEqual(checkout(200, "{'discount': 10}"), 180)
        self.assertEqual(checkout(50, "{'discount': 10}"), 50)
        self.assertEqual(checkout(200, "{}"), 200)

    def test_bad_discount(self) -> None:
        with self.assertRaises(ValueError):
            checkout(200, "{'discount': 'free'}")

    def test_reject_executable_settings(self) -> None:
        # Deliberately red at baseline; a harmless executable expression is
        # enough to demonstrate that the settings parser accepts Python calls.
        with self.assertRaises((ValueError, SyntaxError)):
            checkout(200, "dict(discount=90)")

    def test_customer_summary(self) -> None:
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE orders (id INTEGER, customer TEXT)")
            db.execute("INSERT INTO orders VALUES (1, 'Alice')")
            self.assertEqual(customer_summary(db, "Alice"), "Order 1")
            self.assertEqual(customer_summary(db, "Bob"), "No updates")

    def test_invoice_preview(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            (Path(folder) / "invoice.txt").write_text("  paid  ", encoding="utf-8")
            self.assertEqual(invoice_preview(folder, "invoice.txt"), "paid")

    def test_notification_contract(self) -> None:
        self.assertEqual(notification_label("a@example.test", True), "Send")
        self.assertEqual(notification_label("", True), "Skip")
