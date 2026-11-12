import unittest

from settings_lib import parse_settings


class SettingsTests(unittest.TestCase):
    def test_literals(self) -> None:
        self.assertEqual(parse_settings("{'discount': 10, 'active': True}"), {"discount": 10, "active": True})

    def test_not_dictionary(self) -> None:
        with self.assertRaises(ValueError):
            parse_settings("[1, 2]")
