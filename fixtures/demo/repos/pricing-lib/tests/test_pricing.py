import unittest

from pricing_lib import eligible_for_discount, final_price


class PricingTests(unittest.TestCase):
    def test_threshold(self) -> None:
        for value, expected in [(0, False), (99.99, False), (100, True), (101, True)]:
            self.assertIs(eligible_for_discount(value), expected)

    def test_price(self) -> None:
        self.assertEqual(final_price(200, 10), 180)
        self.assertEqual(final_price(50, 10), 50)
