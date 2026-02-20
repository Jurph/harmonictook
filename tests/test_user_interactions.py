#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_user_interactions.py — Human player input tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, Human, Bot


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


if __name__ == "__main__":
    unittest.main(buffer=True)
