import unittest
from app import normalize


class CivicResolveCoreTests(unittest.TestCase):

    def test_normalize_removes_punctuation_and_collapses_spaces(self):
        self.assertEqual(
            normalize("Road!!!   Damage"),
            "road damage"
        )

    def test_normalize_lowercases(self):
        self.assertEqual(
            normalize("Water Supply"),
            "water supply"
        )


if __name__ == "__main__":
    unittest.main()
