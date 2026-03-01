#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_cards.py — Card trigger mechanics and sort ordering tests

import unittest
from harmonictook import Game, Blue, Green, Red, Card, Stadium, TVStation, BusinessCenter


class TestCards(unittest.TestCase):
    """Tests for card trigger mechanics across Blue, Green, Red subclasses and their interactions."""

    def setUp(self):
        self.players = 2
        self.game = Game(players=self.players)
        self.testbot = self.game.players[0]
        self.otherbot = self.game.players[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testBlueCards(self):
        """Verify Blue cards pay all owners from the bank on any die roll."""
        testbot = self.testbot
        otherbot = self.otherbot
        bluecard = Blue("Dark Blue Card", 2, 1, 1, [11, 12])
        self.assertEqual(bluecard.hitsOn[0], 11)
        self.assertEqual(bluecard.cost, 1)
        for _ in range(4):
            self.game.market.append(Blue("Dark Blue Card", 2, 1, 1, [11, 12]))
        testbot.buy("Dark Blue Card", self.game.market)
        otherbot.buy("Dark Blue Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(10, 13):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after - before, 2)
        self.assertEqual(otherafter - otherbefore, 2)

    def testGreenCards(self):
        """Verify Green multiplier cards pay the die-roller scaled to matching category card count."""
        testbot = self.testbot
        otherbot = self.otherbot
        for _ in range(6):
            self.game.market.append(Blue("Light Blue Card", 77, 1, 1, [11]))
            self.game.market.append(Green("Green Card", 3, 1, 5, [12], 77))
        testbot.buy("Light Blue Card", self.game.market)
        testbot.buy("Light Blue Card", self.game.market)
        otherbot.buy("Blue Card", self.game.market)
        testbot.buy("Green Card", self.game.market)
        otherbot.buy("Green Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for dieroll in range(10, 13):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        self.assertEqual(after - before, 12)

    def testRedCards(self):
        """Verify Red cards deduct from the die-roller and credit the card owner."""
        testbot = self.testbot
        otherbot = self.otherbot
        for _ in range(3):
            self.game.market.append(Red("Crimson Card", 2, 2, 10, [1,2,3,4,5]))
        otherbot.buy("Crimson Card", self.game.market)
        testbot.buy("Crimson Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(1, 13):
           for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after-before, 3)
        self.assertEqual(otherafter-otherbefore, 1)

    def testCardInteractions(self):
        """Verify correct cumulative payouts when multiple card types activate in one round."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Wheat Field", self.game.market)
        otherbot.buy("Wheat Field", self.game.market)
        testbot.buy("Ranch", self.game.market)
        otherbot.buy("Ranch", self.game.market)
        testbot.buy("Forest", self.game.market)
        otherbot.buy("Forest", self.game.market)
        testbot.buy("Mine", self.game.market)
        otherbot.buy("Mine", self.game.market)
        testbot.buy("Apple Orchard", self.game.market)
        otherbot.buy("Apple Orchard", self.game.market)
        testbot.isrollingdice = True
        for dieroll in range(1, 12):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        # Testbot should end up with 89 + 1 + 2 + 1 + 1 + 1 + 3 + 5 = 103
        # Otherbot does not have a bakery and should end up with 101
        self.assertEqual(testbot.bank, 103)
        self.assertEqual(otherbot.bank, 101)

    def testStadiumTrigger(self):
        """Verify Stadium collects 2 coins from each player and credits them all to the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        self.game.market.append(Stadium())
        testbot.buy("Stadium", self.game.market)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, Stadium):
                card.trigger(self.game.players)
        # With 2 players: roller skips self, collects 2 from the other player → net +2
        self.assertEqual(testbot.bank - before, 2)
        self.assertEqual(otherbot_before - otherbot.bank, 2)

    def testShoppingMall(self):
        """Verify Shopping Mall adds +1 to Cafe payout when owner holds the upgrade."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Cafe", self.game.market)
        testbot.buy("Shopping Mall", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if 3 in card.hitsOn and isinstance(card, Red):
                card.trigger(self.game.players)
        after = testbot.bank
        otherbot_after = otherbot.bank
        # Cafe normally pays 1, but with Shopping Mall should pay 2
        self.assertEqual(after - before, 2)
        self.assertEqual(otherbot_before - otherbot_after, 2)


    def testShoppingMallConvenienceStore(self):
        """Verify Shopping Mall adds +1 to Convenience Store payout (Green card path)."""
        testbot = self.testbot
        testbot.buy("Convenience Store", self.game.market)
        testbot.buy("Shopping Mall", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for card in testbot.deck.deck:
            if 4 in card.hitsOn and isinstance(card, Green):
                card.trigger(self.game.players)
        # Convenience Store normally pays 3; with Shopping Mall should pay 4
        self.assertEqual(testbot.bank - before, 4)

    def testTVStationNotRoller(self):
        """Verify TVStation does not activate when its owner is not the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("TV Station", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.game.players)
        # No steal should have occurred
        self.assertEqual(testbot.bank, before)

    def testTVStationNoTargets(self):
        """Verify TVStation activates but takes no action when there are no valid targets."""
        testbot = self.testbot
        testbot.buy("TV Station", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger([testbot])  # only the roller in the list → no valid targets
        self.assertEqual(testbot.bank, before)

    def testBusinessCenterNotRoller(self):
        """Verify BusinessCenter does not activate when its owner is not the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.game.players)
        self.assertEqual(testbot.bank, before)

    def testRedSkipsSelfTrigger(self):
        """Red card owned by the roller returns no events and leaves all banks unchanged."""
        cafe = Red("Cafe", 4, 2, 1, [3])
        cafe.owner = self.testbot
        self.testbot.deck.append(cafe)
        self.testbot.isrollingdice = True
        before_roller = self.testbot.bank
        before_other = self.otherbot.bank
        events = cafe.trigger(self.game.players)
        self.assertEqual(events, [])
        self.assertEqual(self.testbot.bank, before_roller)
        self.assertEqual(self.otherbot.bank, before_other)

    def testStadiumDoesNotCollectFromRoller(self):
        """Stadium.trigger() never lists the die-roller as a collect target."""
        stadium = Stadium()
        stadium.owner = self.testbot
        self.testbot.isrollingdice = True
        events = stadium.trigger(self.game.players)
        collect_targets = [e.target for e in events if e.type == "collect"]
        self.assertNotIn(self.testbot.name, collect_targets)
        self.assertGreater(len(collect_targets), 0)  # at least one other player paid


class TestCardOrdering(unittest.TestCase):
    """Tests for Card sort ordering and comparison operators."""

    def testCardOrdering(self):
        """Verify that cards sort by mean hitsOn: Wheat Field < Ranch < Bakery < Forest."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        ranch = Blue("Ranch", 2, 1, 1, [2])
        bakery = Green("Bakery", 3, 1, 1, [2, 3])
        forest = Blue("Forest", 5, 3, 1, [5])
        cards = [forest, bakery, wheat, ranch]
        cards.sort()
        self.assertEqual(cards[0].name, "Wheat Field")
        self.assertEqual(cards[-1].name, "Forest")
        self.assertLess(wheat, ranch)
        self.assertLess(ranch, forest)
        self.assertGreater(forest, bakery)

    def testCardComparisonOperators(self):
        """Verify __ne__, __le__, __gt__ (false branch), and __ge__ on Card."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        forest = Blue("Forest", 5, 3, 1, [5])
        wheat2 = Blue("Wheat Field", 1, 1, 1, [1])  # identical sortvalue to wheat

        self.assertNotEqual(wheat, forest)          # __ne__ True branch
        self.assertFalse(wheat != wheat2)           # __ne__ False branch (equal sortvalues)

        self.assertLessEqual(wheat, forest)         # __le__ True branch (strictly less)
        self.assertLessEqual(wheat, wheat2)         # __le__ True branch (equal)
        self.assertFalse(forest <= wheat)           # __le__ False branch

        self.assertFalse(wheat > forest)            # __gt__ False branch

        self.assertGreaterEqual(forest, wheat)      # __ge__ True branch (strictly greater)
        self.assertGreaterEqual(wheat, wheat2)      # __ge__ True branch (equal)
        self.assertFalse(wheat >= forest)           # __ge__ False branch

    def testCardComparisonWithNonCard(self):
        """Verify __eq__ and __lt__ return NotImplemented (not an exception) when compared to a non-Card."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        # Directly invoke the dunder methods; Python returns False for == but the method itself returns NotImplemented
        self.assertIs(wheat.__eq__("string"), NotImplemented)
        self.assertIs(wheat.__eq__(42), NotImplemented)
        self.assertIs(wheat.__eq__(None), NotImplemented)
        self.assertIs(wheat.__lt__("string"), NotImplemented)
        self.assertIs(wheat.__lt__(42), NotImplemented)
        # Normal == operator with non-Card should resolve to False without raising
        self.assertFalse(wheat == "string")
        self.assertFalse(wheat == 42)
        self.assertFalse(wheat == None)  # noqa: E711 — explicitly testing == operator, not identity

    def testCardBaseInit(self):
        """Verify the base Card() constructor is instantiable and all fields start at their defaults."""
        card = Card()
        self.assertIsNone(card.name)
        self.assertEqual(card.cost, 0)
        self.assertEqual(card.payout, 0)
        self.assertEqual(card.hitsOn, [0])
        self.assertIsNone(card.owner)
        self.assertIsNone(card.category)
        self.assertIsNone(card.multiplies)


if __name__ == "__main__":
    unittest.main(buffer=True)
