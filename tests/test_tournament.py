#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_tournament.py — Tests for the Swiss tournament harness

import unittest

from harmonictook import Bot
from bots import EVBot
from tournament import (
    make_evbot,
    TournamentPlayer, _seeded_tables, _striped_tables, _avoid_pair_repeats,
)


def _tp(label: str, rating: float = 1500.0) -> TournamentPlayer:
    """Helper: create a TournamentPlayer with given label and rating."""
    return TournamentPlayer(label=label, player_factory=Bot, rating=rating)


class TestMakeEvbot(unittest.TestCase):
    """make_evbot factory helper."""

    def test_produces_evbot_with_correct_horizon(self):
        """make_evbot(N) returns a factory whose instances have n_horizon == N."""
        factory = make_evbot(7)
        bot = factory(name="TestBot")
        self.assertIsInstance(bot, EVBot)
        self.assertEqual(bot.n_horizon, 7)


class TestSeededTables(unittest.TestCase):
    """_seeded_tables: sorts by rating descending, groups, highest rated sits last."""

    def test_two_players_higher_rated_sits_last(self):
        """In a pair table, the higher-rated player is at index 1 (last turn)."""
        strong = _tp("Strong", rating=1700.0)
        weak   = _tp("Weak",   rating=1300.0)
        tables = _seeded_tables([weak, strong], table_size=2)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0][0].label, "Weak",
            "Lower-rated player should sit first (index 0)")
        self.assertEqual(tables[0][1].label, "Strong",
            "Higher-rated player should sit last (index 1)")

    def test_six_players_form_three_pair_tables(self):
        """6 players at table_size=2 → exactly 3 tables."""
        players = [_tp(f"P{i}", rating=1500.0 + i * 50) for i in range(6)]
        tables = _seeded_tables(players, table_size=2)
        self.assertEqual(len(tables), 3)
        for t in tables:
            self.assertEqual(len(t), 2)

    def test_top_seeds_grouped_together(self):
        """First table contains the two highest-rated players."""
        ratings = [1900, 1800, 1700, 1600]
        players = [_tp(f"P{r}", rating=float(r)) for r in ratings]
        tables = _seeded_tables(players, table_size=2)
        top_table_labels = {t.label for t in tables[0]}
        self.assertEqual(top_table_labels, {"P1900", "P1800"},
            "Top two seeds must share the first table")

    def test_triple_tables_contain_three_players(self):
        """table_size=3 with 6 players → two tables of exactly 3."""
        players = [_tp(f"P{i}", rating=float(1500 + i * 10)) for i in range(6)]
        tables = _seeded_tables(players, table_size=3)
        self.assertEqual(len(tables), 2)
        for t in tables:
            self.assertEqual(len(t), 3)

    def test_each_player_appears_exactly_once(self):
        """Every player appears in exactly one table with no duplicates."""
        players = [_tp(f"P{i}") for i in range(12)]
        tables = _seeded_tables(players, table_size=4)
        all_labels = [tp.label for table in tables for tp in table]
        self.assertEqual(len(all_labels), 12)
        self.assertEqual(len(set(all_labels)), 12, "Duplicate player in seeded tables")


class TestStripedTables(unittest.TestCase):
    """_striped_tables: interleaves ratings so each table spans the full range."""

    def test_twelve_players_form_three_quad_tables(self):
        """12 players at table_size=4 → exactly 3 tables of 4."""
        players = [_tp(f"P{i}", rating=float(1500 + i * 20)) for i in range(12)]
        tables = _striped_tables(players, table_size=4)
        self.assertEqual(len(tables), 3)
        for t in tables:
            self.assertEqual(len(t), 4)

    def test_each_player_appears_exactly_once(self):
        """Every player appears in exactly one table."""
        players = [_tp(f"P{i}") for i in range(12)]
        tables = _striped_tables(players, table_size=4)
        all_labels = [tp.label for table in tables for tp in table]
        self.assertEqual(len(set(all_labels)), 12, "Duplicate player in striped tables")

    def test_first_table_contains_rank_1_4_7_10(self):
        """First striped table contains players ranked 1, 4, 7, 10 by rating."""
        ratings = list(range(1, 13))
        players = [_tp(f"R{r}", rating=float(r)) for r in ratings]
        tables = _striped_tables(players, table_size=4)
        top_table_ratings = {tp.rating for tp in tables[0]}
        self.assertEqual(top_table_ratings, {12.0, 9.0, 6.0, 3.0},
            "First striped table should contain interleaved top/bottom seeds")

    def test_highest_rated_in_each_table_sits_last(self):
        """In each striped table, the highest-rated player is at the last index."""
        players = [_tp(f"P{i}", rating=float(1500 + i * 10)) for i in range(12)]
        tables = _striped_tables(players, table_size=4)
        for table in tables:
            ratings = [tp.rating for tp in table]
            self.assertEqual(ratings[-1], max(ratings),
                "Highest-rated player must sit last in each striped table")


class TestAvoidPairRepeats(unittest.TestCase):
    """_avoid_pair_repeats: swaps adjacent pair tables to prevent same-day rematches."""

    def test_no_swap_when_no_conflict(self):
        """Tables without same-day conflicts are returned unchanged."""
        a, b, c, d = _tp("A"), _tp("B"), _tp("C"), _tp("D")
        tables = [[a, b], [c, d]]
        recent: dict = {"A": {"X"}, "B": {"Y"}, "C": {}, "D": {}}
        result = _avoid_pair_repeats(tables, recent)
        self.assertEqual(result[0][0].label, "A")
        self.assertEqual(result[0][1].label, "B")
        self.assertEqual(result[1][0].label, "C")
        self.assertEqual(result[1][1].label, "D")

    def test_swap_happens_when_conflict_exists(self):
        """If A and B played in round 1, table [A,B] is swapped with table [C,D]."""
        a, b, c, d = _tp("A"), _tp("B"), _tp("C"), _tp("D")
        tables = [[a, b], [c, d]]
        recent = {"A": {"B"}, "B": {"A"}, "C": set(), "D": set()}
        result = _avoid_pair_repeats(tables, recent)
        labels = [{t.label for t in table} for table in result]
        self.assertNotEqual(labels[0], {"A", "B"},
            "A and B must be split into different tables after deconflict")

    def test_no_swap_when_alternative_also_conflicts(self):
        """If the proposed swap would also be a rematch, no swap occurs."""
        a, b, c, d = _tp("A"), _tp("B"), _tp("C"), _tp("D")
        tables = [[a, b], [c, d]]
        recent = {"A": {"B", "C"}, "B": {"A", "D"}, "C": set(), "D": set()}
        result = _avoid_pair_repeats(tables, recent)
        self.assertEqual(result[0][0].label, "A")
        self.assertEqual(result[0][1].label, "B")


if __name__ == "__main__":
    unittest.main(buffer=True)
