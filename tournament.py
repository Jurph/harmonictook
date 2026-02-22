#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tournament.py — Headless evaluation harness for bot strategies
#
# Runs a Bot Under Evaluation (BUE) against Bot sparring partners across
# 2-, 3-, and 4-player brackets and reports win rates.
#
# Usage:
#   python tournament.py                        # ThoughtfulBot vs Bots, 5 games each
#   python tournament.py --games 20             # 20 games per bracket
#   python tournament.py --bue thoughtful       # explicit BUE selection (future)

from __future__ import annotations

import argparse
import random
from typing import Callable

from harmonictook import Game, NullDisplay, Player, PlayerDeck
from strategy import EVBot


def run_match(bue_factory: Callable[[str], Player], n_players: int) -> bool:
    """Run one headless game: BUE at index 0 vs (n_players-1) Bot sparring partners.

    Returns True if the BUE wins.
    BUE is always placed at index 0 (first-mover bias noted; acceptable for v1).
    """
    game = Game(players=n_players)
    bue = bue_factory(name="BUE")
    bue.deck = PlayerDeck(bue)
    game.players[0] = bue
    game.run(display=NullDisplay())
    return game.winner is bue


def run_bracket(
    bue_factory: Callable[[str], Player],
    n_players: int,
    n_games: int = 5,
) -> tuple[int, int]:
    """Run n_games matches at n_players table size.

    Returns (wins, losses).
    """
    wins = sum(1 for _ in range(n_games) if run_match(bue_factory, n_players))
    return wins, n_games - wins


def run_tournament(
    bue_factory: Callable[[str], Player],
    n_games: int = 5,
) -> dict[int, tuple[int, int]]:
    """Run full tournament across 2-, 3-, and 4-player brackets.

    Returns {n_players: (wins, losses)} for each bracket.
    """
    return {n: run_bracket(bue_factory, n, n_games) for n in (2, 3, 4)}


def make_evbot(n_horizon: int) -> Callable[[str], EVBot]:
    """Return a factory that creates an EVBot with the given planning horizon."""
    def factory(name: str) -> EVBot:
        return EVBot(name=name, n_horizon=n_horizon)
    return factory


def run_round_robin(
    named_factories: list[tuple[str, Callable[[str], Player]]],
    n_games: int = 100,
) -> dict[str, int]:
    """Run n_games with one bot per factory at the same table, randomizing seats each game.

    Returns {label: win_count} for each named factory.
    Seats are shuffled each game to remove first-mover positional bias.
    """
    wins = {label: 0 for label, _ in named_factories}
    for _ in range(n_games):
        entries = [(label, factory(name=label)) for label, factory in named_factories]
        random.shuffle(entries)
        n = len(entries)
        game = Game(players=n)
        player_to_label: dict[int, str] = {}
        for i, (label, player) in enumerate(entries):
            player.deck = PlayerDeck(player)
            game.players[i] = player
            player_to_label[id(player)] = label
        game.run(display=NullDisplay())
        if game.winner is not None:
            label = player_to_label.get(id(game.winner))
            if label is not None:
                wins[label] += 1
    return wins


def print_round_robin_report(results: dict[str, int], n_games: int) -> None:
    """Print round-robin results sorted by win count descending."""
    n_bots = len(results)
    expected_pct = 100.0 / n_bots if n_bots else 0.0
    print(f"\n=== N-Horizon Shootout: {n_bots}-player table, {n_games} games ===")
    print(f"  (Randomized seating; expected ~{expected_pct:.1f}% per bot if equally matched)\n")
    for label, bot_wins in sorted(results.items(), key=lambda x: -x[1]):
        pct = 100.0 * bot_wins / n_games if n_games else 0.0
        print(f"  {label:20s}  {bot_wins:3d} wins  ({pct:.1f}%)")
    print()


def print_report(bue_name: str, results: dict[int, tuple[int, int]]) -> None:
    """Print a human-readable tournament summary."""
    print(f"\n=== Tournament Results: {bue_name} ===")
    total_wins = total_games = 0
    for n_players, (wins, losses) in sorted(results.items()):
        games = wins + losses
        pct = 100.0 * wins / games if games else 0.0
        print(f"  {n_players}-player:  {wins}W / {losses}L  ({pct:.1f}%)")
        total_wins += wins
        total_games += games
    total_pct = 100.0 * total_wins / total_games if total_games else 0.0
    print("  -----------------------------")
    print(f"  Overall:   {total_wins}W / {total_games - total_wins}L  ({total_pct:.1f}%)\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless bot tournament")
    parser.add_argument("--games", type=int, default=5, metavar="N",
                        help="games per bracket / round-robin (default: 5; recommend 100+ for round-robin)")
    parser.add_argument("--round-robin", action="store_true",
                        help="run N-horizon shootout instead of BUE vs Bot sparring")
    parser.add_argument("--horizons", type=int, nargs="+", default=[1, 3, 5, 7],
                        metavar="N", help="EV horizons to compare in round-robin (default: 1 3 5 7)")
    args = parser.parse_args()

    if args.round_robin:
        named_factories = [(f"EVBot(N={n})", make_evbot(n)) for n in args.horizons]
        results = run_round_robin(named_factories, n_games=args.games)
        print_round_robin_report(results, n_games=args.games)
    else:
        bue_factory = EVBot
        results = run_tournament(bue_factory, n_games=args.games)
        print_report(EVBot.__name__, results)


if __name__ == "__main__":
    main()
