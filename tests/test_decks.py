#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_decks.py — Store, PlayerDeck, and TableDeck tests

import unittest
from harmonictook import Game, TableDeck


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

    def testStoreFreq(self):
        """Verify freq() counts distinct card objects correctly."""
        table = TableDeck()
        freq = table.freq()
        total = sum(freq.values())
        self.assertEqual(total, len(table.deck))


    def testStoreAppendNonCard(self):
        """Verify Store.append() silently ignores non-Card objects (known bug: TypeError is created but not raised)."""
        table = TableDeck()
        size_before = len(table.deck)
        table.append("not a card")
        table.append(42)
        table.append(None)
        # Bug: TypeError() is instantiated but never raised; deck should be unchanged
        self.assertEqual(len(table.deck), size_before)

    def testStoreRemoveNonCard(self):
        """Verify Store.remove() silently ignores non-Card objects (known bug: TypeError is created but not raised)."""
        table = TableDeck()
        size_before = len(table.deck)
        table.remove("not a card")
        table.remove(42)
        self.assertEqual(len(table.deck), size_before)


if __name__ == "__main__":
    unittest.main(buffer=True)
