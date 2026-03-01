#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tournament.py — Swiss tournament harness for bot strategy evaluation
#
# Runs a 24-player Swiss tournament (3 of each of 8 bot families) rated with
# Glicko-1.  Each day runs four rounds: random pairs, seeded pairs, seeded
# triples, striped quads.  Per-game records can be exported to JSONL.
#
# Usage:
#   python tournament.py                     # 1-day Swiss, default 24-player field
#   python tournament.py --days 20           # 20 days of Swiss
#   python tournament.py --records out.jsonl # also export per-game JSONL records
#   python tournament.py --stats out.txt     # also export per-game stats summary

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from harmonictook import Bot, Game, Player, PlayerDeck, RecordingDisplay, UpgradeCard
from bots import EVBot, FromageBot, ImpatientBot, KinematicBot, MarathonBot, ThoughtfulBot, CoverageBot  # noqa: F401 (re-exported for callers)
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


def make_evbot(n_horizon: int) -> Callable[[str], EVBot]:
    """Return a factory that creates an EVBot with the given planning horizon."""
    def factory(name: str) -> EVBot:
        return EVBot(name=name, n_horizon=n_horizon)
    return factory


def make_kinematic_bot(a: float, eruv_offset: int) -> Callable[[str], KinematicBot]:
    """Return a factory that creates a KinematicBot with the given parameters."""
    def factory(name: str) -> KinematicBot:
        return KinematicBot(name=name, a=a, eruv_offset=eruv_offset)
    factory.__name__ = f"KinematicBot(a={a},o={eruv_offset:+d})"
    return factory


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
    """Run n_days x 4-round Swiss tournament; return players sorted by final rating.

    Each day's rounds:
      1 — Random pairs (day 1) or seeded pairs (subsequent days)
      2 — Seeded pairs (avoid same-day round-1 rematches where possible)
      3 — Seeded triples
      4 — Striped quads (ranks 1,4,7,10 / 2,5,8,11 / 3,6,9,12)

    Field is padded to a multiple of 12 with random-bot fillers if needed.
    Rating and score state is mutated in place on each TournamentPlayer.
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
    """24-player field: 3 of each of 8 bot families.

    Families and representatives:
      Random      — Rascal, Rebeka, Rex
      Thoughtful  — Tim, Tay, Thea
      Marathon    — Madison, Michael, Mia
      Impatient   — Iggy, Izzy, Iris
      EV(N=3)     — Edgar, Ellen, Evan
      Coverage    — Chadd, Carli, Casey
      Fromage     — Felicity, Franklin, Fiona
      Kinematic   — Kim, Kourtney, Khloe  (a=0.45, offset=1)

    24 players divides evenly into pairs (12), triples (8), and quads (6),
    satisfying the Swiss tournament mod-12 requirement.
    """
    ev3 = make_evbot(3)
    k45 = make_kinematic_bot(0.45, 1)
    return [
        TournamentPlayer(label="Rascal",   player_factory=Bot),
        TournamentPlayer(label="Rebeka",   player_factory=Bot),
        TournamentPlayer(label="Rex",      player_factory=Bot),
        TournamentPlayer(label="Tim",      player_factory=ThoughtfulBot),
        TournamentPlayer(label="Tay",      player_factory=ThoughtfulBot),
        TournamentPlayer(label="Thea",     player_factory=ThoughtfulBot),
        TournamentPlayer(label="Madison",  player_factory=MarathonBot),
        TournamentPlayer(label="Michael",  player_factory=MarathonBot),
        TournamentPlayer(label="Mia",      player_factory=MarathonBot),
        TournamentPlayer(label="Iggy",     player_factory=ImpatientBot),
        TournamentPlayer(label="Izzy",     player_factory=ImpatientBot),
        TournamentPlayer(label="Iris",     player_factory=ImpatientBot),
        TournamentPlayer(label="Edgar",    player_factory=ev3),
        TournamentPlayer(label="Ellen",    player_factory=ev3),
        TournamentPlayer(label="Evan",     player_factory=ev3),
        TournamentPlayer(label="Chadd",    player_factory=CoverageBot),
        TournamentPlayer(label="Carli",    player_factory=CoverageBot),
        TournamentPlayer(label="Casey",    player_factory=CoverageBot),
        TournamentPlayer(label="Felicity", player_factory=FromageBot),
        TournamentPlayer(label="Franklin", player_factory=FromageBot),
        TournamentPlayer(label="Fiona",    player_factory=FromageBot),
        TournamentPlayer(label="Kim",      player_factory=k45),
        TournamentPlayer(label="Kourtney", player_factory=k45),
        TournamentPlayer(label="Khloe",    player_factory=k45),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Swiss bot tournament")
    parser.add_argument("--days", type=int, default=1, metavar="N",
                        help="number of 4-round days in the Swiss tournament (default: 1)")
    parser.add_argument("--stats", metavar="FILE", default=None,
                        help="append per-game stats (turns, n, scores) to FILE")
    parser.add_argument("--records", metavar="FILE", default=None,
                        help="append per-game JSONL records (decks, ERUV, bot type) to FILE")
    args = parser.parse_args()

    entries = _default_swiss_field()
    run_swiss_tournament(entries, n_days=args.days, stats_path=args.stats, records_path=args.records)


if __name__ == "__main__":
    main()
