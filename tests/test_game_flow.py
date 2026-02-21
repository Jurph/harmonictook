#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game_flow.py — Game loop integration tests

import unittest
from unittest.mock import patch
from harmonictook import Game, TVStation


class TestGameFlow(unittest.TestCase):
    """Integration tests for the nextTurn() game loop."""

    def setUp(self):
        self.game = Game(players=2)

    @patch('builtins.print')
    def testSingleTurnNoCrash(self, mock_print):
        """Verify next_turn() completes without exception for a bot player and returns a bool."""
        result = self.game.next_turn()
        self.assertIsInstance(result, bool)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=3)
    def testNextTurnReturnsDoubles(self, mock_randint, mock_print):
        """Verify next_turn() returns True when a bot with Train Station rolls doubles."""
        player = self.game.players[0]
        player.deposit(100)
        player.buy("Train Station", self.game.market)
        result = self.game.next_turn()
        self.assertTrue(result)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=7)
    def testNextTurnPassAction(self, mock_randint, mock_print):
        """Verify next_turn() takes the 'pass' branch when the rolling player has no coins."""
        player = self.game.players[0]
        player.deduct(player.bank)  # drain to zero; roll of 7 hits no starting cards
        self.game.next_turn()
        pass_calls = [c for c in mock_print.call_args_list if 'passes this turn' in str(c)]
        self.assertTrue(pass_calls)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', side_effect=[2, 4])
    def testNextTurnRadioTower(self, mock_randint, mock_print):
        """Verify next_turn() uses the Radio Tower re-roll when the initial roll is below 5."""
        player = self.game.players[0]
        player.deposit(100)
        player.buy("Radio Tower", self.game.market)
        self.game.next_turn()
        # randint called twice: initial roll (2 → triggers re-roll) + re-roll (4)
        self.assertEqual(mock_randint.call_count, 2)

    @patch('builtins.print')
    @patch('harmonictook.random.randint', return_value=12)
    def testNextTurnMarketRefresh(self, mock_randint, mock_print):
        """Verify next_turn() removes a unique card from the market when the current player already owns it."""
        player = self.game.players[0]
        player.deposit(100)
        tv = TVStation()
        tv.owner = player
        player.deck.append(tv)
        self.assertIn("TV Station", self.game.market.names())
        self.game.next_turn()
        self.assertNotIn("TV Station", self.game.market.names())


if __name__ == "__main__":
    unittest.main(buffer=True)
