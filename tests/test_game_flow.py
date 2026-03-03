#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game_flow.py — Game loop integration tests

import unittest
from unittest.mock import patch
from harmonictook import Event, Game, NullDisplay, TVStation


class TestGameFlow(unittest.TestCase):
    """Integration tests for the nextTurn() game loop."""

    def setUp(self):
        self.game = Game(players=2)

    @patch('harmonictook.random.randint', return_value=3)
    def testNextTurnReturnsDoubles(self, mock_randint):
        """Verify next_turn() emits a doubles roll event when a bot with Train Station rolls 3+3."""
        player = self.game.players[0]
        player.deposit(100)
        player.buy("Train Station", self.game.market)
        result = self.game.next_turn()
        self.assertTrue(any(e.type == "roll" and e.is_doubles for e in result))

    @patch('harmonictook.random.randint', return_value=7)
    def testNextTurnPassAction(self, mock_randint):
        """Verify next_turn() emits a 'pass' event when the rolling player has no coins."""
        player = self.game.players[0]
        player.deduct(player.bank)  # drain to zero; roll of 7 hits no starting cards
        events = self.game.next_turn()
        pass_events = [e for e in events if e.type == "pass"]
        self.assertTrue(pass_events)

    @patch('harmonictook.random.randint', side_effect=[2, 4])
    def testNextTurnRadioTower(self, mock_randint):
        """Verify next_turn() uses the Radio Tower re-roll when the initial roll is below 5."""
        player = self.game.players[0]
        player.deposit(100)
        player.buy("Radio Tower", self.game.market)
        self.game.next_turn()
        # randint called twice: initial roll (2 → triggers re-roll) + re-roll (4)
        self.assertEqual(mock_randint.call_count, 2)

    @patch('harmonictook.random.randint', return_value=12)
    def testNextTurnMarketRefresh(self, mock_randint):
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
        """Verify get_purchase_options() returns Card objects the current player can afford."""
        from harmonictook import Card
        player = self.game.players[0]
        options = self.game.get_purchase_options()
        self.assertTrue(all(isinstance(c, Card) for c in options),
            "get_purchase_options must return Card objects, not strings")
        for card in options:
            self.assertLessEqual(card.cost, player.bank)

    def testGetPurchaseOptionsEmpty(self):
        """Verify get_purchase_options() returns an empty list when the current player is broke."""
        player = self.game.players[0]
        player.deduct(player.bank)  # drain to zero
        self.assertEqual(self.game.get_purchase_options(), [])

    def testGetPurchaseOptionsIncludesAffordableLandmarks(self):
        """Verify get_purchase_options() includes landmark upgrades the player can afford."""
        player = self.game.players[0]
        player.deposit(100)
        options = self.game.get_purchase_options()
        names = {c.name for c in options}
        self.assertIn("Train Station", names,
            "get_purchase_options must include affordable landmarks, not just market cards")

    def testRunSimpleWin(self):
        """Verify run() sets game.winner and exits when a player holds all four upgrades."""
        player = self.game.players[0]
        player.hasTrainStation = True
        player.hasShoppingMall = True
        player.hasAmusementPark = True
        player.hasRadioTower = True
        self.game.run(display=NullDisplay())
        self.assertIs(self.game.winner, player)

    def testRunAmusementParkDoublesLoop(self):
        """Verify run() gives a player an extra turn when they roll doubles and own Amusement Park."""
        player = self.game.players[0]
        player.hasAmusementPark = True
        call_count = [0]

        def mock_next_turn(display=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return [Event(type="roll", player=player.name, value=3, is_doubles=True)]
            # On the extra Amusement Park turn, give the player all upgrades so the game ends
            player.hasTrainStation = True
            player.hasShoppingMall = True
            player.hasAmusementPark = True
            player.hasRadioTower = True
            return [Event(type="roll", player=player.name, value=5, is_doubles=False)]

        with patch.object(self.game, 'next_turn', side_effect=mock_next_turn):
            self.game.run(display=NullDisplay())

        self.assertGreaterEqual(call_count[0], 2)
        self.assertIs(self.game.winner, player)


class TestReset(unittest.TestCase):
    """Player.reset() and Game.reset() restore starting state for a rematch."""

    def setUp(self):
        self.game = Game(players=2)

    def test_player_reset_restores_bank(self):
        """reset() brings the player back to 3 coins regardless of how many they had."""
        player = self.game.players[0]
        player.deposit(50)
        player.reset()
        self.assertEqual(player.bank, 3)

    def test_player_reset_restores_starting_deck(self):
        """reset() gives the player a fresh Wheat Field + Bakery deck."""
        player = self.game.players[0]
        player.deposit(100)
        player.buy("Ranch", self.game.market)
        player.buy("Forest", self.game.market)
        player.reset()
        names = [c.name for c in player.deck.deck]
        self.assertCountEqual(names, ["Wheat Field", "Bakery"])

    def test_player_reset_clears_landmarks(self):
        """reset() removes all four landmarks."""
        player = self.game.players[0]
        player.hasTrainStation = True
        player.hasShoppingMall = True
        player.hasAmusementPark = True
        player.hasRadioTower = True
        player.reset()
        self.assertFalse(player.hasTrainStation)
        self.assertFalse(player.hasShoppingMall)
        self.assertFalse(player.hasAmusementPark)
        self.assertFalse(player.hasRadioTower)

    def test_player_reset_preserves_name(self):
        """reset() does not change the player's name."""
        player = self.game.players[0]
        original_name = player.name
        player.reset()
        self.assertEqual(player.name, original_name)

    def test_game_reset_restores_all_players(self):
        """Game.reset() restores every player to starting bank and deck."""
        for p in self.game.players:
            p.deposit(50)
        self.game.reset()
        for p in self.game.players:
            self.assertEqual(p.bank, 3)
            self.assertEqual(len(p.deck.deck), 2)

    def test_game_reset_preserves_player_list(self):
        """Game.reset() keeps the same player objects in the same order."""
        original_players = list(self.game.players)
        self.game.reset()
        self.assertEqual(self.game.players, original_players)

    def test_game_reset_clears_turn_counters(self):
        """Game.reset() zeroes turn_number and clears winner."""
        self.game.turn_number = 17
        self.game.winner = self.game.players[0]
        self.game.reset()
        self.assertEqual(self.game.turn_number, 0)
        self.assertIsNone(self.game.winner)

    def test_game_reset_restores_market(self):
        """Game.reset() gives a fresh market with six copies of each card type."""
        # Drain Wheat Fields from the market
        player = self.game.players[0]
        player.deposit(100)
        for _ in range(6):
            player.buy("Wheat Field", self.game.market)
        self.game.reset()
        market = self.game.get_market_state()
        self.assertEqual(market.get("Wheat Field", 0), 6)


if __name__ == "__main__":
    unittest.main(buffer=True)
