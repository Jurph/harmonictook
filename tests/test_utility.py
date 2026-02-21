#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_utility.py — Tests for utility.userChoice()

import unittest
from unittest.mock import patch
import utility
from harmonictook import Blue, Green, Red, Stadium, TVStation, BusinessCenter, UpgradeCard


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


class TestCardDescriptions(unittest.TestCase):
    """Verify describe() returns human-readable strings for every card type."""

    def testBlueDescribe(self):
        card = Blue("Wheat Field", 1, 1, 1, [1])
        self.assertIn("any player's roll", card.describe())
        self.assertIn("1", card.describe())

    def testGreenDescribeSimple(self):
        card = Green("Bakery", 3, 1, 1, [2, 3])
        desc = card.describe()
        self.assertIn("when you roll", desc)
        self.assertNotIn("per", desc)

    def testGreenDescribeConvenienceStoreSuffix(self):
        card = Green("Convenience Store", 3, 2, 3, [4])
        self.assertIn("Shopping Mall", card.describe())

    def testGreenDescribeFactory(self):
        cheese = Green("Cheese Factory", 6, 5, 3, [7], multiplies=2)
        self.assertIn("Ranch", cheese.describe())
        furniture = Green("Furniture Factory", 6, 3, 3, [8], multiplies=5)
        self.assertIn("Gear", furniture.describe())
        fvm = Green("Fruit and Vegetable Market", 8, 2, 2, [11, 12], multiplies=1)
        self.assertIn("Grain", fvm.describe())

    def testRedDescribe(self):
        card = Red("Cafe", 4, 2, 1, [3])
        self.assertIn("Steals", card.describe())
        self.assertIn("Shopping Mall", card.describe())

    def testRedDescribeNoSuffix(self):
        # A hypothetical Red card that doesn't qualify for the Shopping Mall note
        card = Red("Some Other Red", 4, 2, 1, [5])
        self.assertNotIn("Shopping Mall", card.describe())

    def testPurpleDescriptions(self):
        self.assertIn("EACH player", Stadium().describe())
        self.assertIn("chosen player", TVStation().describe())
        self.assertIn("Swap", BusinessCenter().describe())

    def testUpgradeCardDescriptions(self):
        self.assertIn("2 dice", UpgradeCard("Train Station").describe())
        self.assertIn("+1 coin", UpgradeCard("Shopping Mall").describe())
        self.assertIn("extra turn", UpgradeCard("Amusement Park").describe())
        self.assertIn("reroll", UpgradeCard("Radio Tower").describe())


class TestCardMenu(unittest.TestCase):
    """Verify card_menu() displays the table and returns the chosen card's name."""

    @patch('builtins.print')
    def testCardMenuReturnsChosenName(self, mock_print):
        cards = [Blue("Wheat Field", 1, 1, 1, [1]), Green("Bakery", 3, 1, 1, [2, 3])]
        with patch('builtins.input', return_value='2'):
            result = utility.card_menu(cards)
        self.assertEqual(result, "Bakery")

    @patch('builtins.print')
    def testCardMenuShowsUpgradeCardWithDash(self, mock_print):
        """Verify UpgradeCards (hitsOn=[99]) show '—' instead of the sentinel value."""
        cards = [UpgradeCard("Train Station")]
        with patch('builtins.input', return_value='1'):
            utility.card_menu(cards)
        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("—", printed)
        self.assertNotIn("99", printed)

    @patch('builtins.print')
    def testCardMenuRejectsOutOfBounds(self, mock_print):
        """Verify card_menu() retries on out-of-range input before accepting a valid selection."""
        cards = [Blue("Wheat Field", 1, 1, 1, [1])]
        with patch('builtins.input', side_effect=['5', '1']):
            result = utility.card_menu(cards)
        self.assertEqual(result, "Wheat Field")


if __name__ == "__main__":
    unittest.main(buffer=True)
