"""unittest-Beispiel, läuft ohne zusätzliche Pakete."""

import unittest

from hallo import begruessung, summe


class TestHallo(unittest.TestCase):
    def test_begruessung(self) -> None:
        self.assertEqual(begruessung("Andreas"), "Hallo Andreas")

    def test_summe(self) -> None:
        self.assertEqual(summe(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
