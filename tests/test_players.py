#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_players.py — Player creation, bank, dice, buying, and win condition tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, Player, Bot, Human, ThoughtfulBot, setPlayers


class TestPlayerBasics(unittest.TestCase):
    """Tests for Player creation, bank mechanics, and dice-rolling behaviour."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]

    def testPlayerCreation(self):
        """Verify correct player count, type, name, and starting bank."""
        self.assertEqual(len(self.playerlist), self.players)
        self.assertIsInstance(self.testbot, Player)
        self.assertIsInstance(self.testbot, Bot)
        self.assertIsNot(self.testbot, Human)
        self.assertEqual(self.testbot.name, "Robo0")
        self.assertEqual(self.testbot.bank, 3)

    def testPlayerBank(self):
        """Verify deposit adds correctly and deduct never goes below zero."""
        self.assertEqual(self.testbot.bank, 3)
        self.testbot.deposit(10)
        self.assertEqual(self.testbot.bank, 13)
        debt = self.testbot.deduct(99)
        self.otherbot.deposit(debt)
        self.assertEqual(self.testbot.bank, 0)
        self.assertEqual(self.otherbot.bank, 16)

    def testPlayerDice(self):
        """Verify chooseDice obeys Train Station, and two-die rolls average to 7."""
        self.assertEqual(self.testbot.chooseDice(), 1)
        self.testbot.deposit(10)
        self.testbot.buy("Train Station", self.availableCards)
        self.assertEqual(self.testbot.chooseDice(), 2)
        sum = 0
        for _ in range(100000):
            roll, isDoubles = self.testbot.dieroll()
            sum += roll
        self.assertAlmostEqual(sum/100000, 7.0, 1)


class TestPlayerBuying(unittest.TestCase):
    """Tests for upgrade purchasing, card swapping, and buy-error handling."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testAmusementParkDoubles(self):
        """Verify dieroll() can return isDoubles=True at least once in 200 two-die rolls."""
        testbot = self.testbot
        testbot.buy("Train Station", self.availableCards)
        self.assertTrue(testbot.hasTrainStation)
        found_doubles = False
        for _ in range(200):
            _, is_doubles = testbot.dieroll()
            if is_doubles:
                found_doubles = True
                break
        self.assertTrue(found_doubles, "Expected at least one doubles in 200 two-die rolls")

    def testInsufficientFunds(self):
        """Verify buy() prints a message and leaves the bank unchanged when the player can't afford the card."""
        testbot = self.testbot
        testbot.deduct(testbot.bank)
        testbot.deposit(1)
        bank_before = testbot.bank
        testbot.buy("Forest", self.availableCards)  # costs 3
        self.assertEqual(testbot.bank, bank_before)

    def testBuyNonexistentCard(self):
        """Verify buy() does not crash and leaves the bank unchanged for an unknown card name."""
        testbot = self.testbot
        bank_before = testbot.bank
        testbot.buy("Totally Fake Card", self.availableCards)
        self.assertEqual(testbot.bank, bank_before)

    def testPlayerSwap(self):
        """Verify swap() moves cards between players and updates ownership correctly."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Forest", self.availableCards)
        otherbot.buy("Ranch", self.availableCards)
        forest = next(c for c in testbot.deck.deck if c.name == "Forest")
        ranch = next(c for c in otherbot.deck.deck if c.name == "Ranch")
        testbot.swap(forest, otherbot, ranch)
        testbot_names = [c.name for c in testbot.deck.deck]
        otherbot_names = [c.name for c in otherbot.deck.deck]
        self.assertIn("Ranch", testbot_names)
        self.assertNotIn("Forest", testbot_names)
        self.assertIn("Forest", otherbot_names)
        self.assertNotIn("Ranch", otherbot_names)
        self.assertEqual(ranch.owner, testbot)
        self.assertEqual(forest.owner, otherbot)

    def testCheckRemainingUpgrades(self):
        """Verify checkRemainingUpgrades() shrinks by one each time an upgrade is purchased."""
        testbot = self.testbot
        self.assertEqual(len(testbot.checkRemainingUpgrades()), 4)
        testbot.buy("Train Station", self.availableCards)
        self.assertEqual(len(testbot.checkRemainingUpgrades()), 3)
        testbot.buy("Shopping Mall", self.availableCards)
        self.assertEqual(len(testbot.checkRemainingUpgrades()), 2)
        testbot.buy("Amusement Park", self.availableCards)
        self.assertEqual(len(testbot.checkRemainingUpgrades()), 1)
        testbot.buy("Radio Tower", self.availableCards)
        self.assertEqual(len(testbot.checkRemainingUpgrades()), 0)


    def testDeterministicDiceRoll(self):
        """Verify dieroll() uses random.randint: non-equal rolls give sum/no-doubles, equal rolls give doubles."""
        testbot = self.testbot
        testbot.buy("Train Station", self.availableCards)
        with patch('harmonictook.random.randint', side_effect=[3, 4]):
            roll, isDoubles = testbot.dieroll()
        self.assertEqual(roll, 7)
        self.assertFalse(isDoubles)
        with patch('harmonictook.random.randint', side_effect=[5, 5]):
            roll, isDoubles = testbot.dieroll()
        self.assertEqual(roll, 10)
        self.assertTrue(isDoubles)


class TestWinCondition(unittest.TestCase):
    """Tests for the isWinner() win detection logic."""

    def setUp(self):
        _, _, playerlist = newGame(2)
        self.bot = playerlist[0]
        self.bot.deposit(100)

    def testIsWinner(self):
        """Verify isWinner() returns False with 0–3 upgrades and True only when all four are held."""
        self.assertFalse(self.bot.isWinner())
        self.bot.hasTrainStation = True
        self.assertFalse(self.bot.isWinner())
        self.bot.hasShoppingMall = True
        self.assertFalse(self.bot.isWinner())
        self.bot.hasAmusementPark = True
        self.assertFalse(self.bot.isWinner())
        self.bot.hasRadioTower = True
        self.assertTrue(self.bot.isWinner())


class TestSetPlayers(unittest.TestCase):
    """Tests for setPlayers() covering all three dispatch branches."""

    def testSetPlayersBotArgs(self):
        """Verify setPlayers(bots=2) returns 2 ThoughtfulBots."""
        result = setPlayers(bots=2)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], ThoughtfulBot)
        self.assertIsInstance(result[1], ThoughtfulBot)

    def testSetPlayersHumanBotArgs(self):
        """Verify setPlayers(humans=1, bots=1) returns Human followed by ThoughtfulBot."""
        result = setPlayers(humans=1, bots=1)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Human)
        self.assertIsInstance(result[1], ThoughtfulBot)

    @patch('builtins.print')
    def testSetPlayersTooFew(self, mock_print):
        """Verify setPlayers(bots=1) pads to 2 and prints a warning."""
        result = setPlayers(bots=1)
        self.assertEqual(len(result), 2)
        self.assertTrue(any('at least 2' in str(c) for c in mock_print.call_args_list))

    @patch('builtins.print')
    def testSetPlayersTooMany(self, mock_print):
        """Verify setPlayers(humans=3, bots=2) trims to 4 and prints a warning."""
        result = setPlayers(humans=3, bots=2)
        self.assertEqual(len(result), 4)
        self.assertTrue(any('Maximum 4' in str(c) for c in mock_print.call_args_list))

    def testSetPlayersIntClampLow(self):
        """Verify setPlayers(1) clamps up to 2 and returns 2 Bots."""
        result = setPlayers(1)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Bot)

    def testSetPlayersIntClampHigh(self):
        """Verify setPlayers(5) clamps down to 4 and returns 4 Bots."""
        result = setPlayers(5)
        self.assertEqual(len(result), 4)

    @patch('builtins.print')
    def testSetPlayersUnexpectedType(self, mock_print):
        """Verify setPlayers(3.14) prints a warning and returns None."""
        result = setPlayers(3.14)
        self.assertIsNone(result)
        self.assertTrue(any('Unexpected' in str(c) for c in mock_print.call_args_list))

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['b', 'Robo', 'b', 'Thinker', 'n'])
    def testSetPlayersInteractiveTwoBots(self, mock_input, mock_print):
        """Verify interactive: 'Robo' (no T) → Bot, 'Thinker' (T-name) → ThoughtfulBot, 'n' → done."""
        result = setPlayers()
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Bot)
        self.assertIsInstance(result[1], ThoughtfulBot)
        self.assertEqual(result[1].name, 'Thinker')

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['h', 'Alice', 'b', 'Bob', 'n'])
    def testSetPlayersInteractiveHuman(self, mock_input, mock_print):
        """Verify interactive: 'h'+'Alice' → Human, 'b'+'Bob' → Bot, 'n' → done."""
        result = setPlayers()
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], Human)
        self.assertEqual(result[0].name, 'Alice')
        self.assertIsInstance(result[1], Bot)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['xyz', 'b', 'Robo', 'b', 'Thinker', 'n'])
    def testSetPlayersInteractiveUnknownInput(self, mock_input, mock_print):
        """Verify interactive: unrecognised H/B input prints an error and loops."""
        result = setPlayers()
        self.assertEqual(len(result), 2)
        self.assertTrue(any('H or B' in str(c) for c in mock_print.call_args_list))

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['b', 'R1', 'b', 'R2', 'y', 'b', 'R3', 'y', 'b', 'R4'])
    def testSetPlayersInteractiveFourPlayers(self, mock_input, mock_print):
        """Verify interactive: loop auto-breaks at 4 players without asking for more."""
        result = setPlayers()
        self.assertEqual(len(result), 4)

    @patch('builtins.print')
    @patch('builtins.input', side_effect=['b', 'R1', 'b', 'R2', 'sure', 'b', 'R3', 'n'])
    def testSetPlayersInteractiveBadYesNo(self, mock_input, mock_print):
        """Verify interactive: unrecognised Y/N answer (no 'y' or 'n') prints an error and loops."""
        result = setPlayers()
        self.assertEqual(len(result), 3)
        self.assertTrue(any('Y or N' in str(c) for c in mock_print.call_args_list))


if __name__ == "__main__":
    unittest.main(buffer=True)
