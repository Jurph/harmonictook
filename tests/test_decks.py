#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_decks.py — Store, PlayerDeck, and TableDeck tests

import unittest
from harmonictook import Game, TableDeck, UpgradeCard


class TestStoreOperations(unittest.TestCase):
    """Tests for Store, PlayerDeck, and TableDeck query methods."""

    def setUp(self):
        self.bot = Game(players=2).players[0]

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

    def testStoreAppendNonCard(self):
        """Verify Store.append() raises TypeError for non-Card objects and leaves deck unchanged."""
        table = TableDeck()
        size_before = len(table.deck)
        for bad in ("not a card", 42, None):
            with self.assertRaises(TypeError):
                table.append(bad)
        self.assertEqual(len(table.deck), size_before)

    def testPlayerDeckStrWithUpgradeCard(self):
        """Verify PlayerDeck.__str__() uses str(card) for UpgradeCards without raising."""
        player = Game(players=2).players[0]
        upgrade = UpgradeCard("Train Station")
        upgrade.owner = player
        player.deck.deck.append(upgrade)
        result = str(player.deck)
        # Wheat Field and Bakery go through the Red/Green/Blue branch
        self.assertIn("Wheat Field", result)
        self.assertIn("Bakery", result)
        # Train Station goes through the else → str(card) branch
        self.assertIn("Train Station", result)

    def testStoreRemoveNonCard(self):
        """Verify Store.remove() raises TypeError for non-Card objects and leaves deck unchanged."""
        table = TableDeck()
        size_before = len(table.deck)
        for bad in ("not a card", 42):
            with self.assertRaises(TypeError):
                table.remove(bad)
        self.assertEqual(len(table.deck), size_before)


if __name__ == "__main__":
    unittest.main(buffer=True)
