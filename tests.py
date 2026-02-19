#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests.py - Unit tests for harmonictook.py

import unittest
from harmonictook import (
    newGame, Player, Bot, ThoughtfulBot, Human,
    Card, Blue, Green, Red, Stadium, TVStation, BusinessCenter,
    TableDeck,
)

# ==== Define Unit Tests ====
class TestPlayers(unittest.TestCase):
    """Tests for Player creation, bank mechanics, and dice-rolling behaviour."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
 
    def testPlayerCreation(self):
        """Verify correct player count, type, name, and starting bank."""
        self.assertEqual(len(self.playerlist), self.players)       # Two players are created 
        self.assertIsInstance(self.testbot, Player)                # Make sure they're players
        self.assertIsInstance(self.testbot, Bot)                   # Make sure they're bots
        self.assertIsNot(self.testbot, Human)
        self.assertEqual(self.testbot.name, "Robo0")    # Created automatically so he should have the default name 
        self.assertEqual(self.testbot.bank, 3)          # Should start with 3 coins

    def testPlayerBank(self):
        """Verify deposit adds correctly and deduct never goes below zero."""
        self.assertEqual(self.testbot.bank, 3)          # Should start with 3 coins
        self.testbot.deposit(10)                        # Deposit 10 coins... 
        self.assertEqual(self.testbot.bank, 13)         # Should now have 13 coins
        debt = self.testbot.deduct(99)                  # Absurd overdraft should have two effects...
        self.otherbot.deposit(debt)                     
        self.assertEqual(self.testbot.bank, 0)          # Testbot should stop deducting at zero 
        self.assertEqual(self.otherbot.bank, 16)        # Otherbot should only get 13 coins 

    def testPlayerDice(self):
        """Verify chooseDice obeys Train Station, and two-die rolls average to 7."""
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


class TestUpgrades(unittest.TestCase):
    """Tests for upgrade card effects and purple card trigger mechanics."""

    def setUp(self):
        self.players = 2
        self.availableCards, self.specialCards, self.playerlist = newGame(self.players)
        self.testbot = self.playerlist[0]
        self.otherbot = self.playerlist[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testShoppingMall(self):
        """Verify Shopping Mall adds +1 to Cafe payout when owner holds the upgrade."""
        # Test that Shopping Mall adds +1 to cafe and convenience store payouts
        testbot = self.testbot
        otherbot = self.otherbot
        
        # Give testbot a cafe and Shopping Mall
        testbot.buy("Cafe", self.availableCards)
        testbot.buy("Shopping Mall", self.availableCards)
        
        # Otherbot rolls a 3 to trigger testbot's cafe
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        
        before = testbot.bank
        otherbot_before = otherbot.bank
        
        # Trigger the cafe
        for card in testbot.deck.deck:
            if 3 in card.hitsOn and isinstance(card, Red):
                card.trigger(self.playerlist)
        
        after = testbot.bank
        otherbot_after = otherbot.bank
        
        # Cafe normally pays 1, but with Shopping Mall should pay 2
        self.assertEqual(after - before, 2)
        self.assertEqual(otherbot_before - otherbot_after, 2)
    
    def testRadioTowerReroll(self):
        """Verify Bot.chooseReroll() returns True on rolls ≤4 and False on rolls ≥5 when Radio Tower is owned."""
        # Test that bot with Radio Tower can make re-roll decision
        testbot = self.testbot
        testbot.buy("Radio Tower", self.availableCards)
        
        # Set up a low roll to trigger re-roll
        testbot._last_roll = 3
        self.assertTrue(testbot.chooseReroll())
        
        # Set up a high roll to not trigger re-roll
        testbot._last_roll = 9
        self.assertFalse(testbot.chooseReroll())
    
    def testTVStationTargeting(self):
        """Verify TV Station steals exactly 5 coins (or all if target has fewer) from the chosen target."""
        # Test that TV Station properly targets and steals coins
        testbot = self.testbot
        otherbot = self.otherbot
        
        # Give testbot a TV Station
        testbot.buy("TV Station", self.availableCards)
        
        # Testbot rolls and TV Station activates
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        
        before = testbot.bank
        otherbot_before = otherbot.bank
        
        # Find and trigger the TV Station
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.playerlist)
        
        after = testbot.bank
        otherbot_after = otherbot.bank
        
        # TV Station should steal 5 coins (or less if target has less)
        stolen = min(5, otherbot_before)
        self.assertEqual(after - before, stolen)
        self.assertEqual(otherbot_before - otherbot_after, stolen)
    
    def testBusinessCenterBot(self):
        """Verify Business Center gives a bot 5 coins in lieu of the card-swap interaction."""
        # Test that bot gets coins from Business Center instead of swapping
        testbot = self.testbot
        
        # Give testbot a Business Center
        testbot.buy("Business Center", self.availableCards)
        
        # Testbot rolls and Business Center activates
        testbot.isrollingdice = True
        
        before = testbot.bank
        
        # Find and trigger the Business Center
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.playerlist)
        
        after = testbot.bank
        
        # Bot should get 5 coins
        self.assertEqual(after - before, 5)

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

    def testThoughtfulBotPriority(self):
        """Verify ThoughtfulBot picks an upgrade over a lower-priority card when both are available."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        options = ["Wheat Field", "Radio Tower", "Mine", "Cafe"]
        choice = thoughtful.chooseCard(options)
        self.assertEqual(choice, "Radio Tower")

    def testInsufficientFunds(self):
        """Verify buy() prints a message and leaves the bank unchanged when the player can't afford the card."""
        testbot = self.testbot
        testbot.deduct(testbot.bank)  # drain to zero
        testbot.deposit(1)            # give exactly 1 coin
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


class TestUtilities(unittest.TestCase):
    """Placeholder for utility function tests."""

    def setUp(self):
        pass

    # This test breaks the build on purpose to test CircleCI status reporting.
    # Don't uncomment this test unless you want to break the build.
    # def testBreakTheBuild(self):
    #    self.assertEqual(1, 0)


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


class TestCardSortingAndComparison(unittest.TestCase):
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


class TestStoreOperations(unittest.TestCase):
    """Tests for Store, PlayerDeck, and TableDeck query methods."""

    def setUp(self):
        _, _, playerlist = newGame(2)
        self.bot = playerlist[0]

    def testPlayerDeckStartingCards(self):
        """Verify a new PlayerDeck contains exactly Wheat Field and Bakery."""
        names = self.bot.deck.names()
        self.assertIn("Wheat Field", names)
        self.assertIn("Bakery", names)
        self.assertEqual(len(names), 2)

    def testTableDeckContents(self):
        """Verify TableDeck is stocked with six copies of Wheat Field and one Stadium."""
        table = TableDeck()
        freq = table.freq()
        counts_by_name = {}
        for card, count in freq.items():
            counts_by_name[card.name] = counts_by_name.get(card.name, 0) + count
        self.assertEqual(counts_by_name.get("Wheat Field", 0), 6)
        self.assertEqual(counts_by_name.get("Stadium", 0), 1)

    def testStoreNamesFiltering(self):
        """Verify names() respects the maxcost filter."""
        table = TableDeck()
        cheap = table.names(maxcost=1)
        self.assertIn("Wheat Field", cheap)
        self.assertIn("Ranch", cheap)
        self.assertNotIn("Mine", cheap)     # costs 6
        self.assertNotIn("Stadium", cheap)  # costs 6

    def testStoreFreq(self):
        """Verify freq() counts distinct card objects correctly."""
        table = TableDeck()
        freq = table.freq()
        total = sum(freq.values())
        self.assertEqual(total, len(table.deck))


def testmain():
    unittest.main(buffer=True)

if __name__ == "__main__":
    testmain()