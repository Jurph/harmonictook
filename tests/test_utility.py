#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_utility.py — Tests for utility.userChoice()

import unittest
from unittest.mock import patch
import utility


class TestUserChoice(unittest.TestCase):
    """Tests for utility.userChoice() menu selection logic."""

    @patch('builtins.print')
    def testUserChoiceValidFirst(self, mock_print):
        """Verify userChoice() returns the element at the chosen 1-indexed position."""
        options = ["Alpha", "Beta", "Gamma"]
        with patch('builtins.input', return_value='2'):
            result = utility.userChoice(options)
        self.assertEqual(result, "Beta")

    @patch('builtins.print')
    def testUserChoiceFirstOption(self, mock_print):
        """Verify userChoice() correctly returns the first element when '1' is entered."""
        options = ["Wheat Field", "Ranch", "Bakery"]
        with patch('builtins.input', return_value='1'):
            result = utility.userChoice(options)
        self.assertEqual(result, "Wheat Field")

    @patch('builtins.print')
    def testUserChoiceLastOption(self, mock_print):
        """Verify userChoice() correctly returns the last element when N is entered."""
        options = ["Wheat Field", "Ranch", "Bakery"]
        with patch('builtins.input', return_value='3'):
            result = utility.userChoice(options)
        self.assertEqual(result, "Bakery")

    @patch('builtins.print')
    def testUserChoiceOutOfBoundsRetries(self, mock_print):
        """Verify userChoice() ignores out-of-range inputs and retries until valid."""
        options = ["Alpha", "Beta"]
        with patch('builtins.input', side_effect=['5', '99', '1']):
            result = utility.userChoice(options)
        self.assertEqual(result, "Alpha")

    @patch('builtins.print')
    def testUserChoiceSingleOption(self, mock_print):
        """Verify userChoice() works correctly with a single-item list."""
        with patch('builtins.input', return_value='1'):
            result = utility.userChoice(["Only Choice"])
        self.assertEqual(result, "Only Choice")


if __name__ == "__main__":
    unittest.main(buffer=True)
