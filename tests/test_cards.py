#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_cards.py — Card trigger mechanics and sort ordering tests

import unittest
from harmonictook import newGame, Blue, Green, Red, Card, Stadium


class TestCards(unittest.TestCase):
    """Tests for card trigger mechanics across Blue, Green, Red subclasses and their interactions."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testBlueCards(self):
        """Verify Blue cards pay all owners from the bank on any die roll."""
        testbot = self.testbot
        otherbot = self.otherbot
        bluecard = Blue("Dark Blue Card", 2, 1, 1, [11, 12])
        self.assertIsInstance(bluecard, Card)
        self.assertIsInstance(bluecard, Blue)
        self.assertEqual(bluecard.hitsOn[0], 11)
        self.assertEqual(bluecard.cost, 1)
        for _ in range(4):
            self.availableCards.append(Blue("Dark Blue Card", 2, 1, 1, [11, 12]))
        testbot.buy("Dark Blue Card", self.availableCards)
        otherbot.buy("Dark Blue Card", self.availableCards)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(10, 13):
            for bot in self.playerlist:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.playerlist)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after - before, 2)
        self.assertEqual(otherafter - otherbefore, 2)

    def testGreenCards(self):
        """Verify Green multiplier cards pay the die-roller scaled to matching category card count."""
        testbot = self.testbot
        otherbot = self.otherbot
        greencard = Green("Green Card", 3, 1, 5, [12], 77)
        self.assertIsInstance(greencard, Card)
        self.assertIsInstance(greencard, Green)
        for _ in range(6):
            self.availableCards.append(Blue("Light Blue Card", 77, 1, 1, [11]))
            self.availableCards.append(Green("Green Card", 3, 1, 5, [12], 77))
        testbot.buy("Light Blue Card", self.availableCards)
        testbot.buy("Light Blue Card", self.availableCards)
        otherbot.buy("Blue Card", self.availableCards)
        testbot.buy("Green Card", self.availableCards)
        otherbot.buy("Green Card", self.availableCards)
        testbot.isrollingdice = True
        before = testbot.bank
        for dieroll in range(10, 13):
            for bot in self.playerlist:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.playerlist)
        after = testbot.bank
        self.assertEqual(after - before, 12)

    def testRedCards(self):
        """Verify Red cards deduct from the die-roller and credit the card owner."""
        testbot = self.testbot
        otherbot = self.otherbot
        redcard = Red("Maroon Card", 2, 2, 25, [1,2,3,4,5])
        self.assertIsInstance(redcard, Card)
        self.assertIsInstance(redcard, Red)
        for _ in range(3):
            self.availableCards.append(Red("Crimson Card", 2, 2, 10, [1,2,3,4,5]))
        otherbot.buy("Crimson Card", self.availableCards)
        testbot.buy("Crimson Card", self.availableCards)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(1, 13):
           for bot in self.playerlist:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.playerlist)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after-before, 3)
        self.assertEqual(otherafter-otherbefore, 1)

    def testCardInteractions(self):
        """Verify correct cumulative payouts when multiple card types activate in one round."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Wheat Field", self.availableCards)
        otherbot.buy("Wheat Field", self.availableCards)
        testbot.buy("Ranch", self.availableCards)
        otherbot.buy("Ranch", self.availableCards)
        testbot.buy("Forest", self.availableCards)
        otherbot.buy("Forest", self.availableCards)
        testbot.buy("Mine", self.availableCards)
        otherbot.buy("Mine", self.availableCards)
        testbot.buy("Apple Orchard", self.availableCards)
        otherbot.buy("Apple Orchard", self.availableCards)
        testbot.dieroll()
        for dieroll in range(1, 12):
            for bot in self.playerlist:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.playerlist)
        # Testbot should end up with 89 + 1 + 2 + 1 + 1 + 1 + 3 + 5 = 103
        # Otherbot does not have a bakery and should end up with 101
        self.assertEqual(testbot.bank, 103)
        self.assertEqual(otherbot.bank, 101)

    def testStadiumTrigger(self):
        """Verify Stadium collects 2 coins from each player and credits them all to the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        self.availableCards.append(Stadium())
        testbot.buy("Stadium", self.availableCards)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, Stadium):
                card.trigger(self.playerlist)
        # With 2 players: roller deducts from self (net 0) and collects 2 from other → net +2
        self.assertEqual(testbot.bank - before, 2)
        self.assertEqual(otherbot_before - otherbot.bank, 2)

    def testShoppingMall(self):
        """Verify Shopping Mall adds +1 to Cafe payout when owner holds the upgrade."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Cafe", self.availableCards)
        testbot.buy("Shopping Mall", self.availableCards)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if 3 in card.hitsOn and isinstance(card, Red):
                card.trigger(self.playerlist)
        after = testbot.bank
        otherbot_after = otherbot.bank
        # Cafe normally pays 1, but with Shopping Mall should pay 2
        self.assertEqual(after - before, 2)
        self.assertEqual(otherbot_before - otherbot_after, 2)


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


if __name__ == "__main__":
    unittest.main(buffer=True)
