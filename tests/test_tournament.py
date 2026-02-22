#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_tournament.py — Tests for the tournament evaluation harness

import unittest
from unittest.mock import patch

from harmonictook import Bot, Game, ThoughtfulBot
from tournament import run_match, run_bracket, run_tournament, print_report


def _always_wins(self_game: Game, display=None) -> None:
    """Replacement for Game.run() that immediately crowns players[0] as winner."""
    self_game.winner = self_game.players[0]


def _never_wins(self_game: Game, display=None) -> None:
    """Replacement for Game.run() that crowns players[1] (not the BUE) as winner."""
    self_game.winner = self_game.players[1]


class TestRunMatch(unittest.TestCase):
    """run_match: single-game execution and return type."""

    def test_returns_bool(self):
        """run_match always returns True or False."""
        result = run_match(Bot, n_players=2)
        self.assertIsInstance(result, bool)

    def test_bue_wins_when_rigged(self):
        """run_match returns True when BUE is set as winner by the game."""
        with patch.object(Game, 'run', _always_wins):
            self.assertTrue(run_match(Bot, n_players=2))

    def test_bue_loses_when_rigged(self):
        """run_match returns False when another player is set as winner."""
        with patch.object(Game, 'run', _never_wins):
            self.assertFalse(run_match(Bot, n_players=2))

    def test_player_count_respected(self):
        """Game is created with the requested number of players."""
        seen_counts = []

        def capture_run(self_game, display=None):
            seen_counts.append(len(self_game.players))
            self_game.winner = self_game.players[0]

        for n in (2, 3, 4):
            with patch.object(Game, 'run', capture_run):
                run_match(Bot, n_players=n)

        self.assertEqual(seen_counts, [2, 3, 4])


class TestRunBracket(unittest.TestCase):
    """run_bracket: n_games matches, correct win/loss totals."""

    def test_wins_plus_losses_equals_n_games(self):
        """wins + losses must always equal n_games."""
        with patch.object(Game, 'run', _always_wins):
            wins, losses = run_bracket(Bot, n_players=2, n_games=7)
        self.assertEqual(wins + losses, 7)

    def test_all_wins_when_rigged(self):
        """BUE with a rigged win should record wins == n_games."""
        with patch.object(Game, 'run', _always_wins):
            wins, losses = run_bracket(Bot, n_players=2, n_games=5)
        self.assertEqual(wins, 5)
        self.assertEqual(losses, 0)

    def test_all_losses_when_rigged(self):
        """BUE that never wins should record losses == n_games."""
        with patch.object(Game, 'run', _never_wins):
            wins, losses = run_bracket(Bot, n_players=2, n_games=5)
        self.assertEqual(wins, 0)
        self.assertEqual(losses, 5)

    def test_thoughtfulbot_factory(self):
        """ThoughtfulBot can be passed directly as the bue_factory."""
        with patch.object(Game, 'run', _always_wins):
            wins, losses = run_bracket(ThoughtfulBot, n_players=2, n_games=3)
        self.assertEqual(wins + losses, 3)


class TestRunTournament(unittest.TestCase):
    """run_tournament: covers all three bracket sizes."""

    def test_result_keys_are_2_3_4(self):
        """Tournament results contain exactly the 2-, 3-, and 4-player brackets."""
        with patch.object(Game, 'run', _always_wins):
            results = run_tournament(Bot, n_games=1)
        self.assertEqual(set(results.keys()), {2, 3, 4})

    def test_total_games_per_bracket(self):
        """Each bracket plays exactly n_games games."""
        with patch.object(Game, 'run', _always_wins):
            results = run_tournament(Bot, n_games=3)
        for n, (wins, losses) in results.items():
            self.assertEqual(wins + losses, 3, msg=f"bracket {n}")

    def test_perfect_record_when_rigged(self):
        """A rigged-win BUE achieves 100% across all brackets."""
        with patch.object(Game, 'run', _always_wins):
            results = run_tournament(Bot, n_games=4)
        for n, (wins, losses) in results.items():
            self.assertEqual(wins, 4, msg=f"bracket {n}")
            self.assertEqual(losses, 0, msg=f"bracket {n}")

    def test_zero_record_when_rigged(self):
        """A rigged-loss BUE achieves 0% across all brackets."""
        with patch.object(Game, 'run', _never_wins):
            results = run_tournament(Bot, n_games=4)
        for n, (wins, losses) in results.items():
            self.assertEqual(wins, 0, msg=f"bracket {n}")


class TestPrintReport(unittest.TestCase):
    """print_report: smoke test that it runs without crashing."""

    def test_runs_without_error(self):
        results = {2: (4, 1), 3: (3, 2), 4: (2, 3)}
        try:
            print_report("TestBot", results)
        except Exception as e:
            self.fail(f"print_report raised {e}")

    def test_empty_results(self):
        """Empty results dict should not crash."""
        try:
            print_report("TestBot", {})
        except Exception as e:
            self.fail(f"print_report raised {e}")


if __name__ == "__main__":
    unittest.main(buffer=True)
