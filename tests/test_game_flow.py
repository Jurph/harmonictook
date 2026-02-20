#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game_flow.py — Game loop integration tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, nextTurn, TVStation


class TestGameFlow(unittest.TestCase):
    """Integration tests for the nextTurn() game loop."""

    def setUp(self):
        self.availableCards, self.specialCards, self.playerlist = newGame(2)

    @patch('builtins.print')
    def testSingleTurnNoCrash(self, mock_print):
        """Verify nextTurn() completes without exception for a bot player and returns a bool."""
        result = nextTurn(self.playerlist, self.playerlist[0], self.availableCards, self.specialCards)
        self.assertIsInstance(result, bool)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=3)
    def testNextTurnReturnsDoubles(self, mock_randint, mock_print):
        """Verify nextTurn() returns True when a bot with Train Station rolls doubles."""
        player = self.playerlist[0]
        player.deposit(100)
        player.buy("Train Station", self.availableCards)
        result = nextTurn(self.playerlist, player, self.availableCards, self.specialCards)
        self.assertTrue(result)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=7)
    def testNextTurnPassAction(self, mock_randint, mock_print):
        """Verify nextTurn() takes the 'pass' branch when the rolling player has no coins."""
        player = self.playerlist[0]
        player.deduct(player.bank)  # drain to zero; roll of 7 hits no starting cards
        nextTurn(self.playerlist, player, self.availableCards, self.specialCards)
        pass_calls = [c for c in mock_print.call_args_list if 'passes this turn' in str(c)]
        self.assertTrue(pass_calls)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', side_effect=[2, 4])
    def testNextTurnRadioTower(self, mock_randint, mock_print):
        """Verify nextTurn() uses the Radio Tower re-roll when the initial roll is below 5."""
        player = self.playerlist[0]
        player.deposit(100)
        player.buy("Radio Tower", self.availableCards)
        nextTurn(self.playerlist, player, self.availableCards, self.specialCards)
        # randint called twice: initial roll (2 → triggers re-roll) + re-roll (4)
        self.assertEqual(mock_randint.call_count, 2)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=12)
    def testNextTurnMarketRefresh(self, mock_randint, mock_print):
        """Verify nextTurn() removes a unique card from the market when the current player already owns it."""
        player = self.playerlist[0]
        player.deposit(100)
        tv = TVStation()
        tv.owner = player
        player.deck.append(tv)
        self.assertIn("TV Station", self.availableCards.names())
        nextTurn(self.playerlist, player, self.availableCards, self.specialCards)
        self.assertNotIn("TV Station", self.availableCards.names())


if __name__ == "__main__":
    unittest.main(buffer=True)
