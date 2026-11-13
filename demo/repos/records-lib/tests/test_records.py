import sqlite3
import unittest

from records_lib import find_orders


class RecordsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE orders (id INTEGER, customer TEXT)")
        self.db.executemany("INSERT INTO orders VALUES (?, ?)", [(1, "Alice"), (2, "Bob")])

    def test_known_customer(self) -> None:
        self.assertEqual(find_orders(self.db, "Alice"), [(1, "Alice")])

    def test_unknown_customer(self) -> None:
        self.assertEqual(find_orders(self.db, "Nobody"), [])

    def test_empty_customer(self) -> None:
        self.assertEqual(find_orders(self.db, ""), [])

    def test_sql_injection(self) -> None:
        self.assertEqual(find_orders(self.db, "' OR 1=1 --"), [])
