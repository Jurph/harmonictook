#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests.py - Unit tests for harmonictook.py

import unittest
from harmonictook import *

# ==== Define Unit Tests ====
class TestPlayers(unittest.TestCase):
    def setUp(self):
        self.players = 2
        self.availableCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
 
    def testPlayerCreation(self):
        self.assertEqual(len(self.playerlist), self.players)       # Two players are created 
        self.assertIsInstance(self.testbot, Player)                # Make sure they're players
        self.assertIsInstance(self.testbot, Bot)                   # Make sure they're bots
        self.assertIsNot(self.testbot, Human)
        self.assertEqual(self.testbot.name, "Robo0")    # Created automatically so he should have the default name 
        self.assertEqual(self.testbot.bank, 3)          # Should start with 3 coins

    def testPlayerBank(self):
        self.assertEqual(self.testbot.bank, 3)          # Should start with 3 coins
        self.testbot.deposit(10)                        # Deposit 10 coins... 
        self.assertEqual(self.testbot.bank, 13)         # Should now have 13 coins
        debt = self.testbot.deduct(99)                  # Absurd overdraft should have two effects...
        self.otherbot.deposit(debt)                     
        self.assertEqual(self.testbot.bank, 0)          # Testbot should stop deducting at zero 
        self.assertEqual(self.otherbot.bank, 16)        # Otherbot should only get 13 coins 

    def testPlayerDice(self):
        self.assertEqual(self.testbot.chooseDice(), 1)  # Should only choose one die
        self.testbot.deposit(10)
        self.testbot.buy("Train Station", self.availableCards)
        self.assertEqual(self.testbot.chooseDice(), 2)  # Should choose two dice
        sum = 0
        for _ in range(100000):
            roll, isDoubles = self.testbot.dieroll()
            sum += roll
        self.assertAlmostEqual(sum/100000, 7.0, 1)      # Should average out to seven quickly

class TestCards(unittest.TestCase):
    def setUp(self):
        self.players = 2
        self.availableCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
        self.testbot.deposit(100) 
        self.otherbot.deposit(100)

    def testBlueCards(self): # Tests for Card subclass Blue
        testbot = self.testbot
        otherbot = self.otherbot
        bluecard = Blue("Dark Blue Card", 2, 1, 1, [12])
        self.assertIsInstance(bluecard, Card)
        self.assertIsInstance(bluecard, Blue)
        self.assertEqual(bluecard.hitsOn[0], 12)
        self.assertEqual(bluecard.cost, 1)

    def testGreenCards(self): # Tests for Card subclass Green
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
        self.assertEqual(after-before, 12)

    def testRedCards(self):
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


def testmain():
    unittest.main(buffer=True)

if __name__ == "__main__":
    testmain()