#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_user_interactions.py — Human player input tests via Display primitives

import unittest
from unittest.mock import patch
from harmonictook import Game, Human, Bot, Blue, TerminalDisplay


def _human_with_display(name: str = "TestHuman") -> Human:
    """Create a Human with a TerminalDisplay wired up (as Game.run() would do)."""
    h = Human(name=name)
    h.display = TerminalDisplay()
    return h


class TestHumanChooseDice(unittest.TestCase):
    """Human.chooseDice delegates to display.pick_one([1, 2])."""

    def test_picks_two_dice(self):
        human = _human_with_display()
        human.hasTrainStation = True
        with patch('builtins.input', return_value='2'):
            self.assertEqual(human.chooseDice(), 2)

    def test_picks_one_die(self):
        human = _human_with_display()
        human.hasTrainStation = True
        with patch('builtins.input', return_value='1'):
            self.assertEqual(human.chooseDice(), 1)

    def test_no_train_station_always_one(self):
        human = _human_with_display()
        self.assertEqual(human.chooseDice(), 1)

    def test_retries_on_out_of_range(self):
        human = _human_with_display()
        human.hasTrainStation = True
        with patch('builtins.input', side_effect=['5', '1']):
            self.assertEqual(human.chooseDice(), 1)

    def test_retries_on_non_integer(self):
        human = _human_with_display()
        human.hasTrainStation = True
        with patch('builtins.input', side_effect=['abc', '2']):
            self.assertEqual(human.chooseDice(), 2)


class TestHumanChooseReroll(unittest.TestCase):
    """Human.chooseReroll delegates to display.confirm."""

    def test_yes_returns_true(self):
        human = _human_with_display()
        human.hasRadioTower = True
        with patch('builtins.input', return_value='y'):
            self.assertTrue(human.chooseReroll())

    def test_no_returns_false(self):
        human = _human_with_display()
        human.hasRadioTower = True
        with patch('builtins.input', return_value='n'):
            self.assertFalse(human.chooseReroll())

    def test_no_radio_tower_always_false(self):
        human = _human_with_display()
        self.assertFalse(human.chooseReroll())


class TestHumanChooseTarget(unittest.TestCase):
    """Human.chooseTarget delegates to display.pick_one on valid targets."""

    def test_picks_target(self):
        human = _human_with_display()
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', return_value='1'):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)

    def test_no_valid_targets_returns_none(self):
        human = _human_with_display()
        human.isrollingdice = True
        self.assertIsNone(human.chooseTarget([human]))

    def test_retries_on_invalid_index(self):
        human = _human_with_display()
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', side_effect=['5', '1']):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)

    def test_retries_on_non_integer(self):
        human = _human_with_display()
        bot = Bot(name="TestBot")
        human.isrollingdice = True
        bot.isrollingdice = False
        with patch('builtins.input', side_effect=['abc', '1']):
            result = human.chooseTarget([human, bot])
        self.assertIs(result, bot)


class TestHumanChooseAction(unittest.TestCase):
    """Human.chooseAction presents a 3-option menu via display.pick_one."""

    def test_buy(self):
        human = _human_with_display()
        market = Game(players=2).market
        with patch('builtins.input', return_value='1'):
            self.assertEqual(human.chooseAction(market), 'buy')

    def test_pass(self):
        human = _human_with_display()
        market = Game(players=2).market
        with patch('builtins.input', return_value='2'):
            self.assertEqual(human.chooseAction(market), 'pass')

    def test_show_cards_then_buy(self):
        """Picking 'Show available cards' loops back; then 'Buy' returns 'buy'."""
        human = _human_with_display()
        market = Game(players=2).market
        with patch('builtins.input', side_effect=['3', '1']):
            result = human.chooseAction(market)
        self.assertEqual(result, 'buy')


class TestHumanChooseCard(unittest.TestCase):
    """Human.chooseCard presents Card objects via display.pick_one."""

    def test_empty_returns_none(self):
        human = _human_with_display()
        self.assertIsNone(human.chooseCard([]))

    def test_picks_card_by_index(self):
        human = _human_with_display()
        ranch = Blue("Ranch", 2, 1, 1, [2])
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        with patch('builtins.input', return_value='1'):
            result = human.chooseCard([ranch, wheat])
        self.assertEqual(result, 'Ranch')

    def test_picks_second_card(self):
        human = _human_with_display()
        ranch = Blue("Ranch", 2, 1, 1, [2])
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        with patch('builtins.input', return_value='2'):
            result = human.chooseCard([ranch, wheat])
        self.assertEqual(result, 'Wheat Field')


class TestHumanBusinessCenterSwap(unittest.TestCase):
    """Human.chooseBusinessCenterSwap uses display.confirm and display.pick_one."""

    def test_decline_returns_none(self):
        from harmonictook import BusinessCenter
        human = _human_with_display()
        bot = Bot(name="Target")
        human.isrollingdice = True
        bot.isrollingdice = False
        bc = BusinessCenter()
        bc.owner = human
        before_human = len(human.deck.deck)
        before_bot = len(bot.deck.deck)
        # First input: pick target (bot is index 1), then decline swap
        with patch('builtins.input', side_effect=['1', 'n']):
            bc.trigger([human, bot])
        self.assertEqual(len(human.deck.deck), before_human)
        self.assertEqual(len(bot.deck.deck), before_bot)

    def test_accept_and_swap(self):
        from harmonictook import BusinessCenter
        human = _human_with_display()
        bot = Bot(name="Target")
        human.isrollingdice = True
        bot.isrollingdice = False
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = human
        human.deck.deck.append(ranch)
        bc = BusinessCenter()
        bc.owner = human
        self.assertIn("Ranch", human.deck.names())
        self.assertNotIn("Ranch", bot.deck.names())
        # inputs: target=1(bot), swap=y, give=Ranch(3rd card), take=Wheat Field(1st of bot's)
        with patch('builtins.input', side_effect=['1', 'y', '3', '1']):
            bc.trigger([human, bot])
        self.assertNotIn("Ranch", human.deck.names())
        self.assertIn("Ranch", bot.deck.names())

    def test_no_target_gives_coins(self):
        from harmonictook import BusinessCenter
        human = _human_with_display()
        human.isrollingdice = True
        bc = BusinessCenter()
        bc.owner = human
        bank_before = human.bank
        bc.trigger([human])
        self.assertEqual(human.bank, bank_before + 5)


if __name__ == "__main__":
    unittest.main(buffer=True)
