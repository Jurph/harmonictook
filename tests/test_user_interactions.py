#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_user_interactions.py — Human player input tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, Human, Bot, Player


class TestUserInteractions(unittest.TestCase):
    """Tests for Human player input-driven decision methods."""

    def testHumanChooseDice(self):
        """Verify Human.chooseDice() reads input when Train Station is owned and returns the chosen value."""
        human = Human(name="TestHuman")
        human.hasTrainStation = True
        with patch('builtins.input', return_value='2'):
            self.assertEqual(human.chooseDice(), 2)
        with patch('builtins.input', return_value='1'):
            self.assertEqual(human.chooseDice(), 1)

    def testHumanChooseReroll(self):
        """Verify Human.chooseReroll() returns True for 'y' and False for 'n' when Radio Tower is owned."""
        human = Human(name="TestHuman")
        human.hasRadioTower = True
        with patch('builtins.input', return_value='y'):
            self.assertTrue(human.chooseReroll())
        with patch('builtins.input', return_value='n'):
            self.assertFalse(human.chooseReroll())

    def testHumanChooseTarget(self):
        """Verify Human.chooseTarget() returns the player at the chosen index from valid targets."""
        human = Human(name="TestHuman")
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', return_value='1'):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)

    def testHumanChooseAction(self):
        """Verify Human.chooseAction() returns 'buy' for 'b' and 'pass' for 'p'."""
        availableCards, _, _ = newGame(2)
        human = Human(name="TestHuman")
        with patch('builtins.input', return_value='b'):
            self.assertEqual(human.chooseAction(availableCards), 'buy')
        with patch('builtins.input', return_value='p'):
            self.assertEqual(human.chooseAction(availableCards), 'pass')

    @patch('builtins.print')
    def testHumanChooseActionShowCards(self, mock_print):
        """Verify chooseAction() displays the market on 's' and then loops back for a real choice."""
        availableCards, _, _ = newGame(2)
        human = Human(name="TestHuman")
        with patch('builtins.input', side_effect=['s', 'b']):
            result = human.chooseAction(availableCards)
        self.assertEqual(result, 'buy')

    @patch('builtins.print')
    def testHumanChooseActionUnknownInput(self, mock_print):
        """Verify chooseAction() prints an error and loops when input contains no valid key."""
        availableCards, _, _ = newGame(2)
        human = Human(name="TestHuman")
        with patch('builtins.input', side_effect=['x', 'p']):
            result = human.chooseAction(availableCards)
        self.assertEqual(result, 'pass')

    def testHumanChooseCardEmpty(self):
        """Verify Human.chooseCard() returns None when the options list is empty."""
        human = Human(name="TestHuman")
        self.assertIsNone(human.chooseCard([]))

    def testHumanChooseCardPicked(self):
        """Verify Human.chooseCard() returns the value from userChoice when options are available."""
        human = Human(name="TestHuman")
        with patch('harmonictook.utility.userChoice', return_value='Ranch'):
            result = human.chooseCard(['Ranch', 'Wheat Field'])
        self.assertEqual(result, 'Ranch')

    def testHumanChooseDiceOutOfRange(self):
        """Verify chooseDice() rejects values outside 1–2 and retries until a valid input is given."""
        human = Human(name="TestHuman")
        human.hasTrainStation = True
        with patch('builtins.input', side_effect=['5', '1']):
            self.assertEqual(human.chooseDice(), 1)

    def testHumanChooseDiceValueError(self):
        """Verify chooseDice() handles non-integer input gracefully and retries."""
        human = Human(name="TestHuman")
        human.hasTrainStation = True
        with patch('builtins.input', side_effect=['abc', '2']):
            self.assertEqual(human.chooseDice(), 2)

    def testHumanChooseTargetNoPlayers(self):
        """Verify chooseTarget() returns None immediately when all players are rolling."""
        human = Human(name="TestHuman")
        human.isrollingdice = True
        self.assertIsNone(human.chooseTarget([human]))

    @patch('builtins.print')
    def testHumanChooseTargetInvalidIndex(self, mock_print):
        """Verify chooseTarget() rejects an out-of-range index and retries."""
        human = Human(name="TestHuman")
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', side_effect=['5', '1']):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)

    @patch('builtins.print')
    def testHumanChooseTargetValueError(self, mock_print):
        """Verify chooseTarget() handles non-integer input gracefully and retries."""
        human = Human(name="TestHuman")
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', side_effect=['abc', '1']):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)


if __name__ == "__main__":
    unittest.main(buffer=True)
