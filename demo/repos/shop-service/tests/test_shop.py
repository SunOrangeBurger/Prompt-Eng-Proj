import unittest

from shop_service import checkout


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
