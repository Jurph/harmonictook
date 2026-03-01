#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game.py — Game class creation, state, and refresh_market tests

import unittest
from unittest.mock import patch, MagicMock
from harmonictook import Game, Human, TVStation, GameState, NullDisplay
from bots import ThoughtfulBot


class TestGameCreation(unittest.TestCase):
    """Tests for Game.__init__ with different argument combinations."""

    def testGameCreationPlayerCount(self):
        """Verify Game(players=N) creates the right number of players."""
        self.assertEqual(len(Game(players=2).players), 2)
        self.assertEqual(len(Game(players=3).players), 3)
        self.assertEqual(len(Game(players=4).players), 4)

    def testGameCreationWithBots(self):
        """Verify Game(bots=N) creates N ThoughtfulBot players."""
        game = Game(bots=3)
        self.assertEqual(len(game.players), 3)
        for player in game.players:
            self.assertIsInstance(player, ThoughtfulBot)

    def testGameCreationWithHumansAndBots(self):
        """Verify Game(humans=1, bots=1) creates a Human followed by a Bot."""
        game = Game(humans=1, bots=1)
        self.assertEqual(len(game.players), 2)
        self.assertIsInstance(game.players[0], Human)
        self.assertIsInstance(game.players[1], ThoughtfulBot)

    def testGameInitialState(self):
        """Verify Game starts with turn_number=0, index=0, last_roll=None, winner=None."""
        game = Game(players=2)
        self.assertEqual(game.turn_number, 0)
        self.assertEqual(game.current_player_index, 0)
        self.assertIsNone(game.last_roll)
        self.assertIsNone(game.winner)

    def testGameMarketAndReserveExist(self):
        """Verify Game creates a populated market and reserve on construction."""
        game = Game(players=2)
        self.assertGreater(len(game.market.deck), 0)
        self.assertGreater(len(game.reserve.deck), 0)


class TestRefreshMarket(unittest.TestCase):
    """Targeted tests for Game.refresh_market() branch coverage."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.game.current_player_index = 0

    def testRefreshMarketAddsCardBackToMarket(self):
        """Verify branch 2: card not in player deck AND not in market → add to market from reserve."""
        # Remove TV Station from the market to simulate a prior refresh
        tv_in_market = [c for c in self.game.market.deck if c.name == "TV Station"]
        for card in tv_in_market:
            self.game.market.deck.remove(card)
        self.assertNotIn("TV Station", self.game.market.names())
        # TV Station is not in player's deck either
        self.assertNotIn("TV Station", self.player.deck.names())
        # refresh_market should detect it's missing from market and add it back
        self.game.refresh_market()
        self.assertIn("TV Station", self.game.market.names())

    def testRefreshMarketPassBranchAlreadyInMarket(self):
        """Verify branch 1: card not in player deck, already in market → market unchanged."""
        self.assertIn("TV Station", self.game.market.names())
        self.assertNotIn("TV Station", self.player.deck.names())
        tv_count_before = sum(1 for c in self.game.market.deck if c.name == "TV Station")
        self.game.refresh_market()
        tv_count_after = sum(1 for c in self.game.market.deck if c.name == "TV Station")
        self.assertIn("TV Station", self.game.market.names())
        self.assertEqual(tv_count_after, tv_count_before, "TV Station count in market must not change when already present")

    def testRefreshMarketPassBranchOwnedNotInMarket(self):
        """Verify branch 4: card in player deck, not in market → market stays clean."""
        # Give player a TV Station and remove it from the market (simulates after branch 3 ran)
        tv = TVStation()
        tv.owner = self.player
        self.player.deck.deck.append(tv)
        tv_in_market = [c for c in self.game.market.deck if c.name == "TV Station"]
        for card in tv_in_market:
            self.game.market.deck.remove(card)
        self.assertNotIn("TV Station", self.game.market.names())
        self.game.refresh_market()
        # Card is owned and already absent from market → should stay absent
        self.assertNotIn("TV Station", self.game.market.names())


class TestMain(unittest.TestCase):
    """Tests for the main() entry point."""

    @patch('builtins.print')
    def testMainCreatesGameAndRuns(self, mock_print):
        """Verify main() constructs a Game and calls run() exactly once."""
        import harmonictook
        mock_game = MagicMock()
        with patch('harmonictook.Game', return_value=mock_game) as mock_game_cls:
            with patch('sys.argv', ['harmonictook.py', '--bots', '2']):
                harmonictook.main()
        mock_game_cls.assert_called_once_with(bots=2, humans=0)
        mock_game.run.assert_called_once()

    @patch('builtins.print')
    def testMainDefaultArgs(self, mock_print):
        """Verify main() with no flags calls Game(bots=0, humans=0) and run()."""
        import harmonictook
        mock_game = MagicMock()
        with patch('harmonictook.Game', return_value=mock_game) as mock_game_cls:
            with patch('sys.argv', ['harmonictook.py']):
                harmonictook.main()
        mock_game_cls.assert_called_once_with(bots=0, humans=0)
        mock_game.run.assert_called_once()


class TestGameHistory(unittest.TestCase):
    """Tests for Game.history (list[GameState]) and the PlayerSnapshot/GameState dataclasses."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryGrowsAfterEachTurn(self, _):
        """Verify history gains one entry per next_turn() call."""
        self.game.next_turn(NullDisplay())
        self.assertEqual(len(self.game.history), 1)
        self.game.next_turn(NullDisplay())
        self.assertEqual(len(self.game.history), 2)

    @patch('harmonictook.random.randint', return_value=12)
    def testHistorySnapshotFields(self, _):
        """Verify GameState captures turn_number, active_player, roll, and player count."""
        self.game.next_turn(NullDisplay())
        state = self.game.history[0]
        self.assertIsInstance(state, GameState)
        self.assertEqual(state.turn_number, 0)
        self.assertEqual(state.active_player, self.player.name)
        self.assertEqual(state.roll, 12)
        self.assertEqual(len(state.players), 2)

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryBankReflectsPostTurnBalance(self, _):
        """Verify snapshot bank matches the player's actual bank after the turn completes."""
        # Drain player so roll=12 causes no payout and they can't buy anything
        self.player.deduct(self.player.bank)
        self.game.next_turn(NullDisplay())
        snap = next(s for s in self.game.history[0].players if s.name == self.player.name)
        self.assertEqual(snap.bank, self.player.bank)

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryLandmarkCount(self, _):
        """Verify landmarks field counts only owned landmarks (0 → 1 after buying Train Station)."""
        self.game.next_turn(NullDisplay())
        self.assertEqual(self.game.history[0].players[0].landmarks, 0)
        self.player.hasTrainStation = True
        self.player.deduct(self.player.bank)  # drain to 0 — bot can't buy a second landmark
        self.game.next_turn(NullDisplay())
        self.assertEqual(self.game.history[1].players[0].landmarks, 1)

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryCardCountExcludesLandmarks(self, _):
        """Verify cards field counts non-landmark cards only; buying Train Station does not increment it."""
        # PlayerDeck starts with exactly 2 cards: Wheat Field and Bakery.
        # Give just enough to buy Train Station (cost 4); bot starts with 3, needs 1 more.
        self.player.deposit(1)
        self.player.buy("Train Station", self.game.market)
        # bank now 0 — bot cannot buy during next_turn, so card/landmark counts are stable
        self.game.next_turn(NullDisplay())
        snap = self.game.history[0].players[0]
        self.assertEqual(snap.cards, 2)     # Wheat Field + Bakery; Train Station excluded
        self.assertEqual(snap.landmarks, 1) # Train Station counted as landmark, not card

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryEventsStored(self, _):
        """Verify GameState stores the turn's event list and it contains at least a roll event."""
        self.game.next_turn(NullDisplay())
        state = self.game.history[0]
        self.assertIsInstance(state.events, list)
        self.assertTrue(any(e.type == "roll" for e in state.events))

    @patch('harmonictook.random.randint', return_value=12)
    def testHistoryTurnNumbersAreSequential(self, _):
        """Verify turn_number increments by 1 for each consecutive entry in history."""
        for _ in range(4):
            self.game.next_turn(NullDisplay())
        for i, state in enumerate(self.game.history):
            self.assertEqual(state.turn_number, i)


if __name__ == "__main__":
    unittest.main(buffer=True)
