#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_bots.py — Bot and ThoughtfulBot behaviour tests

import unittest
from unittest.mock import patch
from harmonictook import Game, Bot, ThoughtfulBot, TVStation, BusinessCenter, UpgradeCard


class TestBots(unittest.TestCase):
    """Tests for Bot card selection, targeting, and upgrade trigger mechanics."""

    def setUp(self):
        self.players = 2
        self.game = Game(players=self.players)
        self.testbot = self.game.players[0]
        self.otherbot = self.game.players[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testRadioTowerReroll(self):
        """Verify Bot.chooseReroll() returns True on rolls ≤4 and False on rolls ≥5 when Radio Tower is owned."""
        testbot = self.testbot
        testbot.buy("Radio Tower", self.game.market)
        testbot._last_roll = 3
        self.assertTrue(testbot.chooseReroll())
        testbot._last_roll = 9
        self.assertFalse(testbot.chooseReroll())

    def testTVStationTargeting(self):
        """Verify TV Station steals exactly 5 coins (or all if target has fewer) from the chosen target."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("TV Station", self.game.market)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.game.players)
        after = testbot.bank
        otherbot_after = otherbot.bank
        stolen = min(5, otherbot_before)
        self.assertEqual(after - before, stolen)
        self.assertEqual(otherbot_before - otherbot_after, stolen)

    def testBusinessCenterBotNoTargetGetsCoins(self):
        """When no valid swap target exists, bot gets 5 coins."""
        testbot = self.testbot
        testbot.buy("Business Center", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        with patch.object(testbot, "chooseTarget", return_value=None):
            for card in testbot.deck.deck:
                if isinstance(card, BusinessCenter):
                    card.trigger(self.game.players)
        after = testbot.bank
        self.assertEqual(after - before, 5)

    def testBusinessCenterBotSwaps(self):
        """When a valid target and swappable cards exist, bot swaps: take highest-cost from target, give lowest (hitsOn sum + cost)."""
        from harmonictook import Blue
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        # Give otherbot a higher-cost card so the swap is visible (bot takes highest-cost)
        forest = Blue("Forest", 1, 3, 1, [5])
        forest.owner = otherbot
        otherbot.deck.append(forest)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        my_swappable_before = [c.name for c in testbot.deck.deck if not isinstance(c, UpgradeCard)]
        their_names_before = [c.name for c in otherbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Forest", their_names_before)
        bank_before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.game.players)
        # Bot should have swapped, not received 5 coins
        self.assertEqual(testbot.bank, bank_before, "Bot should not get 5 coins when swap is possible")
        # Bot takes highest-cost from target (Forest cost 3): Forest should now be in testbot's deck
        my_names_after = [c.name for c in testbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Forest", my_names_after, "Bot should take highest-cost card (Forest) from target")

    def testBusinessCenterBotGivesLowestScore(self):
        """Bot gives away the card with the lowest (sum of hitsOn + cost) score."""
        from harmonictook import Blue, Green
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        # Add a Ranch (hitsOn=[2], cost=1, score=3) so bot has:
        #   Wheat Field (score=1+1=2), Bakery (score=2+3+1=6), Ranch (score=2+1=3), BC (score=6+8=14)
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = testbot
        testbot.deck.append(ranch)
        # Give otherbot a high-cost card to be the take target
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = otherbot
        otherbot.deck.append(mine)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.game.players)
        # Wheat Field (score 2) should have been given away — check it's in otherbot's deck
        other_names = [c.name for c in otherbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Wheat Field", other_names, "Bot should give away Wheat Field (lowest hitsOn+cost)")
        # Ranch (score 3) should still be in testbot's deck
        my_names = [c.name for c in testbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Ranch", my_names, "Bot should keep Ranch (higher hitsOn+cost than Wheat Field)")

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
        self.assertEqual(testbot.chooseAction(self.game.market), 'pass')

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
