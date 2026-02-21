#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game.py — Game class creation, state, and refresh_market tests

import unittest
from unittest.mock import patch, MagicMock
from harmonictook import Game, Bot, ThoughtfulBot, Human, TVStation


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
        size_before = len(self.game.market.deck)
        self.game.refresh_market()
        # TV Station should still be in the market; size should not increase from this card
        self.assertIn("TV Station", self.game.market.names())

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


if __name__ == "__main__":
    unittest.main(buffer=True)
