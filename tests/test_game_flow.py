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


    def testGetPurchaseOptionsAffordable(self):
        """Verify get_purchase_options() returns only cards the current player can afford."""
        player = self.game.players[0]
        # With 3 starting coins, only cards costing ≤ 3 should appear
        options = self.game.get_purchase_options()
        for name in options:
            card = next(c for c in self.game.market.deck if c.name == name)
            self.assertLessEqual(card.cost, player.bank)

    def testGetPurchaseOptionsEmpty(self):
        """Verify get_purchase_options() returns an empty list when the current player is broke."""
        player = self.game.players[0]
        player.deduct(player.bank)  # drain to zero
        options = self.game.get_purchase_options()
        self.assertEqual(options, [])

    @patch('builtins.print')
    def testRunSimpleWin(self, mock_print):
        """Verify run() sets game.winner and exits when a player holds all four upgrades."""
        player = self.game.players[0]
        player.hasTrainStation = True
        player.hasShoppingMall = True
        player.hasAmusementPark = True
        player.hasRadioTower = True
        self.game.run()
        self.assertIs(self.game.winner, player)

    @patch('builtins.print')
    def testRunAmusementParkDoublesLoop(self, mock_print):
        """Verify run() gives a player an extra turn when they roll doubles and own Amusement Park."""
        player = self.game.players[0]
        player.hasAmusementPark = True
        call_count = [0]

        def mock_next_turn():
            call_count[0] += 1
            if call_count[0] == 1:
                return True  # doubles on first turn → triggers Amusement Park loop
            # On the extra Amusement Park turn, give the player all upgrades so the game ends
            player.hasTrainStation = True
            player.hasShoppingMall = True
            player.hasAmusementPark = True
            player.hasRadioTower = True
            return False

        with patch.object(self.game, 'next_turn', side_effect=mock_next_turn):
            self.game.run()

        self.assertGreaterEqual(call_count[0], 2)
        self.assertIs(self.game.winner, player)


if __name__ == "__main__":
    unittest.main(buffer=True)
