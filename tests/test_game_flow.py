#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_game_flow.py — Game loop integration tests

import unittest
from unittest.mock import patch
from harmonictook import newGame, nextTurn


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


if __name__ == "__main__":
    unittest.main(buffer=True)
