#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_players.py — Player creation, bank, dice, buying, and win condition tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, Player, Bot, Human


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


if __name__ == "__main__":
    unittest.main(buffer=True)
