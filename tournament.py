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
import json
import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from harmonictook import Bot, Game, NullDisplay, Player, PlayerDeck, RecordingDisplay, UpgradeCard
from bots import EVBot, ImpatientBot, KinematicBot, MarathonBot, ThoughtfulBot, CoverageBot  # noqa: F401 (re-exported for callers)
from strategy import pmf_mean, round_pmf, tuv_expected


_GLICKO_Q: float = math.log(10.0) / 400.0
_GLICKO_RD_INIT: float = 350.0
_GLICKO_RD_MIN: float = 50.0


def _glicko_g(rd: float) -> float:
    """Glicko g-function: reduces opponent weight by their rating uncertainty."""
    return 1.0 / math.sqrt(1.0 + 3.0 * _GLICKO_Q**2 * rd**2 / math.pi**2)


def _glicko_e(r: float, r_j: float, rd_j: float) -> float:
    """Expected score for a player rated r against an opponent rated r_j with RD rd_j."""
    return 1.0 / (1.0 + 10.0 ** (-_glicko_g(rd_j) * (r - r_j) / 400.0))


def _glicko_update(
    r: float, rd: float, results: list[tuple[float, float, float]]
) -> tuple[float, float]:
    """Apply one Glicko-1 rating period update.

    results: list of (r_j, rd_j, s_j) for each opponent faced this period.
    s_j is 1.0 (win), 0.5 (draw), or 0.0 (loss).
    Returns (new_rating, new_rd).
    """
    if not results:
        return r, rd
    d_sq_inv = _GLICKO_Q**2 * sum(
        _glicko_g(rd_j)**2 * _glicko_e(r, r_j, rd_j) * (1.0 - _glicko_e(r, r_j, rd_j))
        for r_j, rd_j, _ in results
    )
    d_sq = 1.0 / d_sq_inv if d_sq_inv > 0.0 else float("inf")
    new_rd_sq = 1.0 / (1.0 / rd**2 + 1.0 / d_sq)
    score_sum = sum(
        _glicko_g(rd_j) * (s_j - _glicko_e(r, r_j, rd_j))
        for r_j, rd_j, s_j in results
    )
    new_r = r + _GLICKO_Q * new_rd_sq * score_sum
    new_rd = max(_GLICKO_RD_MIN, math.sqrt(new_rd_sq))
    return new_r, new_rd


@dataclass
class TournamentPlayer:
    """Persistent entry in a Swiss tournament."""
    label: str
    player_factory: Callable[[str], Player]
    rating: float = field(default=1500.0)
    rd: float = field(default=_GLICKO_RD_INIT)
    scores: list[int] = field(default_factory=list)


@dataclass
class RoundResult:
    """Result of one table within a tournament round."""
    table: list[str]                  # labels in finish order (highest score first)
    finish_scores: dict[str, int]     # label → finish_score
    rating_deltas: dict[str, float]   # label → rating change from this table


def finish_score(player: Player, game: Game) -> int:
    """Return a player's end-of-game score for tournament finish ordering.

    ERUV-based: 50 - round(ERUV), so expected rounds until victory maps to a score.
    Winner (ERUV=0) scores 50; a player ~2 rounds from winning scores ~48;
    ~10 rounds out scores ~40. Higher score = closer to victory / better position.
    """
    eruv = tuv_expected(player, game)
    return int(round(50.0 - eruv))


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


def make_kinematic_bot(a: float, eruv_offset: int) -> Callable[[str], KinematicBot]:
    """Return a factory that creates a KinematicBot with the given parameters."""
    def factory(name: str) -> KinematicBot:
        return KinematicBot(name=name, a=a, eruv_offset=eruv_offset)
    factory.__name__ = f"KinematicBot(a={a},o={eruv_offset:+d})"
    return factory


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


def _write_game_record(
    records_path: str,
    game: Game,
    instances: dict[str, Player],
    scores: dict[str, int],
    all_events: list,
) -> None:
    """Append one JSONL record describing the end state of a completed game.

    Each line is a compact JSON object with top-level game metadata and a 'players'
    list. Landmarks are separated from income cards so downstream queries can filter
    on upgrade ownership without knowing which card names are upgrades.

    Per-player fields:
      income_ev     — mean coins per round at game end (for acceleration analysis)
      card_payouts  — {card_name: {fires, total}} aggregated from game events
    """
    # Aggregate card payouts from event stream: payout (Blue/Green/factory),
    # steal (Red/TVStation), collect (Stadium) — all now carry card=self.name.
    payout_types = {"payout", "steal", "collect"}
    by_player: dict[str, dict[str, dict[str, int]]] = {lbl: {} for lbl in instances}
    for ev in all_events:
        if ev.type not in payout_types or not ev.card or ev.player not in by_player:
            continue
        entry = by_player[ev.player].setdefault(ev.card, {"fires": 0, "total": 0})
        entry["fires"] += 1
        entry["total"] += ev.value

    player_records = []
    for label, player in instances.items():
        landmarks = sorted(c.name for c in player.deck.deck if isinstance(c, UpgradeCard))
        income_cards = [c.name for c in player.deck.deck if not isinstance(c, UpgradeCard)]
        deck_counts = dict(Counter(income_cards))
        income_ev = pmf_mean(round_pmf(player, game.players))
        player_records.append({
            "label": label,
            "bot_type": type(player).__name__,
            "winner": player is game.winner,
            "score": scores[label],
            "eruv": tuv_expected(player, game),
            "bank": player.bank,
            "landmarks": landmarks,
            "deck": deck_counts,
            "income_ev": round(income_ev, 4),
            "card_payouts": by_player[label],
        })
    record = {
        "turns": game.turn_number,
        "n_players": len(game.players),
        "players": player_records,
    }
    with open(records_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def _run_table(
    players: list[TournamentPlayer],
    stats_path: str | None = None,
    records_path: str | None = None,
) -> RoundResult:
    """Run one game; update Glicko rating+RD and scores in place; return the round result."""
    n = len(players)

    game = Game(players=n)
    instances: dict[str, Player] = {}
    for i, tp in enumerate(players):
        p = tp.player_factory(tp.label)
        p.deck = PlayerDeck(p)
        game.players[i] = p
        instances[tp.label] = p
    recorder = RecordingDisplay()
    game.run(display=recorder)

    scores: dict[str, int] = {tp.label: finish_score(instances[tp.label], game) for tp in players}

    if stats_path is not None:
        player_scores = "  ".join(f"{tp.label}={scores[tp.label]}" for tp in players)
        with open(stats_path, "a", encoding="utf-8") as f:
            f.write(f"turns={game.turn_number}  n={n}  {player_scores}\n")

    if records_path is not None:
        _write_game_record(records_path, game, instances, scores, recorder.events)

    # Build per-player opponent result lists using pre-game ratings (snapshot before any update)
    result_lists: dict[str, list[tuple[float, float, float]]] = {tp.label: [] for tp in players}
    for i in range(n):
        for j in range(i + 1, n):
            a, b = players[i], players[j]
            sa, sb = scores[a.label], scores[b.label]
            s_a = 1.0 if sa > sb else (0.5 if sa == sb else 0.0)
            s_b = 1.0 - s_a
            result_lists[a.label].append((b.rating, b.rd, s_a))
            result_lists[b.label].append((a.rating, a.rd, s_b))

    deltas: dict[str, float] = {}
    for tp in players:
        new_r, new_rd = _glicko_update(tp.rating, tp.rd, result_lists[tp.label])
        deltas[tp.label] = new_r - tp.rating
        tp.rating = new_r
        tp.rd = new_rd
        tp.scores.append(scores[tp.label])

    finish_order = sorted(players, key=lambda tp: -scores[tp.label])
    return RoundResult(
        table=[tp.label for tp in finish_order],
        finish_scores=scores,
        rating_deltas=deltas,
    )


def _seeded_tables(players: list[TournamentPlayer], table_size: int) -> list[list[TournamentPlayer]]:
    """Sort players by rating descending, group into tables; highest-rated player sits last."""
    by_rating = sorted(players, key=lambda tp: -tp.rating)
    tables = []
    for i in range(0, len(by_rating), table_size):
        group = by_rating[i:i + table_size]
        tables.append(list(reversed(group)))  # highest rating → last turn order
    return tables


def _striped_tables(players: list[TournamentPlayer], table_size: int) -> list[list[TournamentPlayer]]:
    """Sort players by rating descending, then stripe into tables by rank modulo n_tables.

    For 12 players at table_size=4: ranks 1,4,7,10 / 2,5,8,11 / 3,6,9,12.
    Each table spans the full rating range, so upsets carry maximum rating-change weight.
    Highest-rated player at each table sits last (same turn-order convention as _seeded_tables).
    """
    by_rating = sorted(players, key=lambda tp: -tp.rating)
    n_tables = len(by_rating) // table_size
    tables = []
    for i in range(n_tables):
        group = by_rating[i::n_tables][:table_size]
        tables.append(list(reversed(group)))  # highest rating → last turn order
    return tables


def _avoid_pair_repeats(
    tables: list[list[TournamentPlayer]],
    recent: dict[str, set[str]],
) -> list[list[TournamentPlayer]]:
    """Best-effort: swap players between adjacent pair tables to avoid same-day rematches.

    recent maps each player label to the set of labels they played in this day's round 1.
    """
    for i in range(len(tables) - 1):
        a, b = tables[i]
        if b.label in recent.get(a.label, set()):
            c, d = tables[i + 1]
            if (c.label not in recent.get(a.label, set())
                    and d.label not in recent.get(b.label, set())):
                tables[i] = [a, c]
                tables[i + 1] = [b, d]
    return tables


def print_standings(players: list[TournamentPlayer], after_round: int) -> None:
    """Print standings table sorted by Glicko rating descending."""
    sorted_players = sorted(players, key=lambda tp: -tp.rating)
    print(f"\n  Standings after Round {after_round}:")
    print(f"  {'Rank':>4}  {'Player':<14}  {'Rating ± RD':>16}  {'Avg score':>9}")
    print(f"  {'----':>4}  {'-' * 14}  {'-' * 16:>16}  {'---------':>9}")
    for rank, tp in enumerate(sorted_players, 1):
        avg = sum(tp.scores) / len(tp.scores) if tp.scores else 0.0
        rating_str = f"{tp.rating:.0f} ± {tp.rd:.0f}"
        print(f"  {rank:>4}  {tp.label:<14}  {rating_str:>16}  {avg:>9.1f}")
    print()


def run_swiss_tournament(
    entries: list[TournamentPlayer],
    n_days: int = 1,
    verbose: bool = True,
    stats_path: str | None = None,
    records_path: str | None = None,
) -> list[TournamentPlayer]:
    """Run n_days x 4-round Swiss tournament; return players sorted by final Elo.

    Each day's rounds:
      1 — Random pairs (day 1) or seeded pairs (subsequent days)
      2 — Seeded pairs (avoid same-day round-1 rematches where possible)
      3 — Seeded triples
      4 — Seeded quads

    Field is padded to a multiple of 12 with Bot fillers if needed.
    All Elo and scores state is mutated in place on each TournamentPlayer.
    """
    filler_n = 0
    while len(entries) % 12 != 0:
        filler_n += 1
        entries.append(TournamentPlayer(label=f"Random{filler_n}", player_factory=Bot))

    total_rounds = 0

    def _print_round(rn: int, fmt: str, results: list[RoundResult]) -> None:
        print(f"\n{'=' * 56}")
        print(f"  Round {rn}: {fmt}")
        print(f"{'=' * 56}")
        for r in results:
            finish_str = "  ".join(f"{lbl}({r.finish_scores[lbl]})" for lbl in r.table)
            delta_str = "  ".join(f"{lbl}({r.rating_deltas[lbl]:+.1f})" for lbl in r.table)
            print(f"  Finish:    {finish_str}")
            print(f"  Rating d:  {delta_str}")

    for day in range(1, n_days + 1):
        if verbose and n_days > 1:
            print(f"\n{'#' * 56}")
            print(f"  Day {day} of {n_days}")
            print(f"{'#' * 56}")

        # Round 1 — random on day 1, seeded thereafter
        if day == 1:
            shuffled = list(entries)
            random.shuffle(shuffled)
            r1_tables = [shuffled[i:i + 2] for i in range(0, len(shuffled), 2)]
        else:
            r1_tables = _seeded_tables(entries, 2)
        r1_results = [_run_table(t, stats_path, records_path) for t in r1_tables]
        total_rounds += 1

        # Build same-day round-1 opponent map for deconflict in round 2
        recent: dict[str, set[str]] = {}
        for table in r1_tables:
            for tp in table:
                recent[tp.label] = {o.label for o in table if o.label != tp.label}

        if verbose:
            fmt1 = "Random pairs" if day == 1 else "Seeded pairs"
            _print_round(total_rounds, fmt1, r1_results)
            print_standings(entries, total_rounds)

        # Round 2 — seeded pairs, avoid same-day round-1 rematches
        r2_tables = _seeded_tables(entries, 2)
        r2_tables = _avoid_pair_repeats(r2_tables, recent)
        r2_results = [_run_table(t, stats_path, records_path) for t in r2_tables]
        total_rounds += 1
        if verbose:
            _print_round(total_rounds, "Seeded pairs", r2_results)
            print_standings(entries, total_rounds)

        # Round 3 — seeded triples
        r3_tables = _seeded_tables(entries, 3)
        r3_results = [_run_table(t, stats_path, records_path) for t in r3_tables]
        total_rounds += 1
        if verbose:
            _print_round(total_rounds, "Seeded triples", r3_results)
            print_standings(entries, total_rounds)

        # Round 4 — striped quads: ranks 1,4,7,10 / 2,5,8,11 / 3,6,9,12
        r4_tables = _striped_tables(entries, 4)
        r4_results = [_run_table(t, stats_path, records_path) for t in r4_tables]
        total_rounds += 1
        if verbose:
            _print_round(total_rounds, "Seeded quads", r4_results)
            print_standings(entries, total_rounds)

    return sorted(entries, key=lambda tp: -tp.rating)


def _default_swiss_field() -> list[TournamentPlayer]:
    """12-player field: 3 of each bot type with naming convention R/T/E/C."""
    ev3 = make_evbot(3)
    return [
        TournamentPlayer(label="Rascal",  player_factory=Bot),
        TournamentPlayer(label="Rebeka",  player_factory=Bot),
        TournamentPlayer(label="Tim",     player_factory=ThoughtfulBot),
        TournamentPlayer(label="Tay",     player_factory=ThoughtfulBot),
        TournamentPlayer(label="Edgar",   player_factory=ev3),
        TournamentPlayer(label="Ellen",   player_factory=ev3),
        TournamentPlayer(label="Chadd",   player_factory=CoverageBot),
        TournamentPlayer(label="Carli",   player_factory=CoverageBot),
        TournamentPlayer(label="Iggy",    player_factory=ImpatientBot),
        TournamentPlayer(label="Izzy",    player_factory=ImpatientBot),
        TournamentPlayer(label="Madison", player_factory=MarathonBot),
        TournamentPlayer(label="Michael", player_factory=MarathonBot),
    ]


def _kinematic_tournament_field() -> list[TournamentPlayer]:
    """24-player field: 12 KinematicBots (6 best-performing (a, offset) cells
    from a prior 72-player sweep × 2 each) + 12 benchmark bots (2 each of
    Bot, ThoughtfulBot, EVBot, CoverageBot, ImpatientBot, MarathonBot).

    Selected cells (a, offset) by win rate in sweep:
      (0.45, 1): 48.1%   (0.30, 2): 45.6%   (0.20, 2): 45.0%
      (0.45, 0): 44.4%   (0.30, 1): 44.4%   (0.20, 1): 43.1%

    High-a values (0.60–0.90) and offset=4 at high-a were excluded;
    they produce pathological behaviour (turns-to-win > 120).
    """
    cells = [
        (0.45, 1),
        (0.30, 2),
        (0.20, 2),
        (0.45, 0),
        (0.30, 1),
        (0.20, 1),
    ]

    entries: list[TournamentPlayer] = []
    for a, offset in cells:
        a_tag = f"{int(a * 100):02d}"
        o_tag = f"m{abs(offset)}" if offset < 0 else f"{offset:02d}"
        factory = make_kinematic_bot(a, offset)
        entries.append(TournamentPlayer(label=f"KLONE-{a_tag}-{o_tag}", player_factory=factory))
        entries.append(TournamentPlayer(label=f"KOPPY-{a_tag}-{o_tag}", player_factory=factory))

    ev3 = make_evbot(3)
    entries += [
        TournamentPlayer(label="Rascal",  player_factory=Bot),
        TournamentPlayer(label="Rebeka",  player_factory=Bot),
        TournamentPlayer(label="Tim",     player_factory=ThoughtfulBot),
        TournamentPlayer(label="Tay",     player_factory=ThoughtfulBot),
        TournamentPlayer(label="Edgar",   player_factory=ev3),
        TournamentPlayer(label="Ellen",   player_factory=ev3),
        TournamentPlayer(label="Chadd",   player_factory=CoverageBot),
        TournamentPlayer(label="Carli",   player_factory=CoverageBot),
        TournamentPlayer(label="Iggy",    player_factory=ImpatientBot),
        TournamentPlayer(label="Izzy",    player_factory=ImpatientBot),
        TournamentPlayer(label="Madison", player_factory=MarathonBot),
        TournamentPlayer(label="Michael", player_factory=MarathonBot),
    ]
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Headless bot tournament")
    parser.add_argument("--games", type=int, default=5, metavar="N",
                        help="games per bracket / round-robin (default: 5; recommend 100+ for round-robin)")
    parser.add_argument("--round-robin", action="store_true",
                        help="run N-horizon shootout instead of BUE vs Bot sparring")
    parser.add_argument("--swiss", action="store_true",
                        help="run Swiss tournament with 12 named bots (3 of each type)")
    parser.add_argument("--kinematic", action="store_true",
                        help="run 24-player kinematic field (12 KinematicBots + 12 benchmarks)")
    parser.add_argument("--days", type=int, default=1, metavar="N",
                        help="number of 4-round days in the Swiss tournament (default: 1)")
    parser.add_argument("--horizons", type=int, nargs="+", default=[1, 3, 5, 7],
                        metavar="N", help="EV horizons to compare in round-robin (default: 1 3 5 7)")
    parser.add_argument("--stats", metavar="FILE", default=None,
                        help="append per-game stats (turns, n, scores) to FILE")
    parser.add_argument("--records", metavar="FILE", default=None,
                        help="append per-game JSONL records (decks, ERUV, bot type) to FILE")
    args = parser.parse_args()

    if args.kinematic:
        entries = _kinematic_tournament_field()
        run_swiss_tournament(entries, n_days=args.days, stats_path=args.stats, records_path=args.records)
    elif args.swiss:
        entries = _default_swiss_field()
        run_swiss_tournament(entries, n_days=args.days, stats_path=args.stats, records_path=args.records)
    elif args.round_robin:
        named_factories = [(f"EVBot(N={n})", make_evbot(n)) for n in args.horizons]
        results = run_round_robin(named_factories, n_games=args.games)
        print_round_robin_report(results, n_games=args.games)
    else:
        bue_factory = EVBot
        results = run_tournament(bue_factory, n_games=args.games)
        print_report(EVBot.__name__, results)


if __name__ == "__main__":
    main()
