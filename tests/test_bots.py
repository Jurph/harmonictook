#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_bots.py — Bot and ThoughtfulBot behaviour tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, Bot, ThoughtfulBot, TVStation, BusinessCenter


class TestBots(unittest.TestCase):
    """Tests for Bot card selection, targeting, and upgrade trigger mechanics."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testRadioTowerReroll(self):
        """Verify Bot.chooseReroll() returns True on rolls ≤4 and False on rolls ≥5 when Radio Tower is owned."""
        testbot = self.testbot
        testbot.buy("Radio Tower", self.availableCards)
        testbot._last_roll = 3
        self.assertTrue(testbot.chooseReroll())
        testbot._last_roll = 9
        self.assertFalse(testbot.chooseReroll())

    def testTVStationTargeting(self):
        """Verify TV Station steals exactly 5 coins (or all if target has fewer) from the chosen target."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("TV Station", self.availableCards)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.playerlist)
        after = testbot.bank
        otherbot_after = otherbot.bank
        stolen = min(5, otherbot_before)
        self.assertEqual(after - before, stolen)
        self.assertEqual(otherbot_before - otherbot_after, stolen)

    def testBusinessCenterBot(self):
        """Verify Business Center gives a bot 5 coins in lieu of the card-swap interaction."""
        testbot = self.testbot
        testbot.buy("Business Center", self.availableCards)
        testbot.isrollingdice = True
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.playerlist)
        after = testbot.bank
        self.assertEqual(after - before, 5)

    def testThoughtfulBotPriority(self):
        """Verify ThoughtfulBot picks an upgrade over a lower-priority card when both are available."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        options = ["Wheat Field", "Radio Tower", "Mine", "Cafe"]
        choice = thoughtful.chooseCard(options)
        self.assertEqual(choice, "Radio Tower")

    def testBotChooseCardMocked(self):
        """Verify Bot.chooseCard() delegates card selection to random.choice."""
        testbot = self.testbot
        options = ["Ranch", "Wheat Field", "Mine"]
        with patch('harmonictook.random.choice', return_value='Ranch'):
            result = testbot.chooseCard(options)
        self.assertEqual(result, 'Ranch')

    def testThoughtfulBotChooseDice(self):
        """Verify ThoughtfulBot returns 1 without Train Station and uses random.choice with it."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        self.assertEqual(thoughtful.chooseDice(), 1)
        thoughtful.hasTrainStation = True
        with patch('harmonictook.random.choice', return_value=2):
            result = thoughtful.chooseDice()
        self.assertEqual(result, 2)

    def testBotChooseActionPass(self):
        """Verify Bot.chooseAction() returns 'pass' when no cards are affordable."""
        testbot = self.testbot
        testbot.deduct(testbot.bank)  # drain to zero
        self.assertEqual(testbot.chooseAction(self.availableCards), 'pass')

    def testBotChooseCardEmpty(self):
        """Verify Bot.chooseCard() returns None and doesn't crash on an empty options list."""
        result = self.testbot.chooseCard([])
        self.assertIsNone(result)

    def testThoughtfulBotChooseCardEmpty(self):
        """Verify ThoughtfulBot.chooseCard() returns None and doesn't crash on an empty options list."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        result = thoughtful.chooseCard([])
        self.assertIsNone(result)

    def testThoughtfulBotLateCardPriority(self):
        """Verify ThoughtfulBot prefers late-game cards over early-game cards when Train Station is owned."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        thoughtful.hasTrainStation = True
        # Mine is a latecard; Bakery is an earlycard — latecard should win
        self.assertEqual(thoughtful.chooseCard(["Bakery", "Mine"]), "Mine")

    def testThoughtfulBotRandomFallback(self):
        """Verify ThoughtfulBot falls back to random.choice when no option matches any priority list."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        options = ["Curiosity Shop", "Duck Ranch"]  # neither is in any priority list
        with patch('harmonictook.random.choice', return_value='Duck Ranch'):
            result = thoughtful.chooseCard(options)
        self.assertEqual(result, 'Duck Ranch')


if __name__ == "__main__":
    unittest.main(buffer=True)
