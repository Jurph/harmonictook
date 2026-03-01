#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# strategy.py — EV-based card valuation library for harmonictook
# Pure functions only: no side effects, no I/O. Returns scores; callers decide how to act.

from __future__ import annotations
import math
import statistics
from harmonictook import Blue, Green, Red, Stadium, TVStation, BusinessCenter, Player, Game, Card, UpgradeCard

# ---------------------------------------------------------------------------
# Probability tables
# ---------------------------------------------------------------------------

ONE_DIE_PROB: dict[int, float] = {i: 1/6 for i in range(1, 7)}

TWO_DIE_PROB: dict[int, float] = {
    2: 1/36, 3: 2/36, 4: 3/36,  5: 4/36,  6: 5/36,
    7: 6/36, 8: 5/36, 9: 4/36, 10: 3/36, 11: 2/36, 12: 1/36,
}

P_DOUBLES: float = 6 / 36


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _num_dice(player: Player) -> int:
    """Return the number of dice this player rolls (2 with Train Station, else 1)."""
    return 2 if player.hasTrainStation else 1


def _turn_multiplier(player: Player) -> float:
    """Return the expected turns-per-round multiplier from Amusement Park (doubles re-roll)."""
    if player.hasAmusementPark:
        return 1.0 / (1.0 - P_DOUBLES)
    return 1.0


def _count_category(player: Player, category: int) -> int:
    """Return the count of cards in player's deck with the given category."""
    return sum(1 for c in player.deck.deck if getattr(c, "category", None) == category)


def _own_turn_coverage(player: Player, num_dice: int) -> float:
    """Return P(at least one card fires when player rolls num_dice dice on their own turn).

    This is NOT per-round coverage — it only evaluates the player's own roll.
    It is used exclusively by chooseDice(), which controls only the player's own
    roll distribution. Red cards are excluded because they fire on opponents' rolls
    and are unaffected by this player's dice choice. For full per-round coverage
    (including Red card income from opponents' turns), use portfolio_coverage().

    Die values where multiple cards overlap are counted once (coverage, not income count).
    """
    prob_table = ONE_DIE_PROB if num_dice == 1 else TWO_DIE_PROB
    own_turn_cards = [c for c in player.deck.deck if not isinstance(c, (Red, UpgradeCard))]
    return sum(
        prob
        for die_value, prob in prob_table.items()
        if any(die_value in card.hitsOn for card in own_turn_cards)
    )


def _die_pmf(n_dice: int) -> dict[int, float]:
    """Return the Probability Mass Function (PMF) for rolling n_dice d6s and summing.

    n_dice=1 → 6 outcomes equally weighted. n_dice=2 → 11 outcomes, triangular.
    """
    if n_dice == 1:
        return dict(ONE_DIE_PROB)
    if n_dice == 2:
        return dict(TWO_DIE_PROB)
    # 3+ dice: convolve repeatedly
    acc = _die_pmf(1)
    for _ in range(n_dice - 1):
        acc = _convolve(acc, ONE_DIE_PROB)
    return acc


def _convolve(a: dict[int, float], b: dict[int, float]) -> dict[int, float]:
    """Combine two independent PMFs by summing their outcomes.

    result[x + y] += a[x] * b[y] for all (x, y) pairs.
    """
    out: dict[int, float] = {}
    for x, px in a.items():
        for y, py in b.items():
            k = x + y
            out[k] = out.get(k, 0.0) + px * py
    return out


def _own_turn_income(player: Player, players: list[Player], roll: int) -> int:
    """Coin income for player on their own turn when the die total is roll.

    Blue, Green, Stadium, TVStation only. Business Center is 0 (swap, not coins).
    """
    total = 0
    for card in player.deck.deck:
        if roll not in card.hitsOn:
            continue
        if isinstance(card, Blue):
            total += card.payout
        elif isinstance(card, Green):
            if getattr(card, "multiplies", None) is not None:
                total += card.payout * _count_category(player, card.multiplies)
            else:
                payout = card.payout
                if player.hasShoppingMall and card.name == "Convenience Store":
                    payout += 1
                total += payout
        elif isinstance(card, Stadium):
            total += card.payout * (len(players) - 1)
        elif isinstance(card, TVStation):
            opponents = [p for p in players if p is not player]
            if opponents:
                total += min(5, max(p.bank for p in opponents))
    return total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def p_hits(hitsOn: list[int], num_dice: int) -> float:
    """Return the probability that a roll of num_dice dice lands on any value in hitsOn.

    Uses ONE_DIE_PROB for num_dice==1 and TWO_DIE_PROB for num_dice==2.
    Missing keys (e.g. 7 with 1 die, or sentinel 99) return 0.0 via dict.get.
    """
    prob = ONE_DIE_PROB if num_dice == 1 else TWO_DIE_PROB
    return sum(prob.get(v, 0.0) for v in hitsOn)


def _ev_businesscenter(card: BusinessCenter, owner: Player, players: list[Player], N: int) -> float:
    """EV for Business Center: optimal card swap on a 6.

    For each opponent, find the best (take, give) pair:
      - take: opponent card with highest delta_ev to owner (captures synergy gains)
      - give: among owner's bottom-4 cards by EV, pick the one worth least to that opponent
              (spite filter: don't hand them a card that powers their engine)

    Give and take must be from the same opponent. Net = best_take_gain - give_loss.
    BusinessCenter cards are excluded from both sides to prevent recursive EV calls.
    """
    opponents = [p for p in players if p is not owner]
    if not opponents:
        return 0.0

    own_cards = [c for c in owner.deck.deck
                 if not isinstance(c, (UpgradeCard, BusinessCenter))]
    if not own_cards:
        return 0.0

    best_net = 0.0

    for target in opponents:
        target_cards = [c for c in target.deck.deck
                        if not isinstance(c, (UpgradeCard, BusinessCenter))]
        if not target_cards:
            continue

        # Best card to take: maximises delta_ev to owner (factory synergies included)
        best_gain = max(delta_ev(c, owner, players, 1) for c in target_cards)

        # Best card to give: bottom-4 own cards by marginal EV, then least valuable to target
        own_by_ev = sorted(own_cards, key=lambda c: delta_ev(c, owner, players, 1))
        bottom_4 = own_by_ev[:4]
        best_give = min(bottom_4, key=lambda c: delta_ev(c, target, players, 1))
        give_loss = delta_ev(best_give, owner, players, 1)

        net = best_gain - give_loss
        if net > best_net:
            best_net = net

    return best_net * p_hits([6], _num_dice(owner)) * _turn_multiplier(owner) * N



def _train_station_gain(
    player: Player, players: list[Player], market_cards: list[Card], N: int
) -> float:
    """Forward-looking EV of Train Station: gain from switching to the 2-dice card range.

    Partitions market cards into 1-die-range (max hit ≤ 6) and 2-die-range (min hit ≥ 7).
    Filters 2-die results to non-zero EV only — this naturally excludes factories with no
    multiplier targets and Red[7+] cards (Family Restaurant) whose trigger depends on
    opponents' dice counts, not the owner's.
    Returns max(0, median(ev_2die_nonzero) − median(ev_1die)) × N.
    """
    one_die_cards = [
        c for c in market_cards
        if not isinstance(c, UpgradeCard) and c.hitsOn and max(c.hitsOn) <= 6
    ]
    two_die_cards = [
        c for c in market_cards
        if not isinstance(c, UpgradeCard) and c.hitsOn and min(c.hitsOn) >= 7
    ]
    if not two_die_cards:
        return 0.0

    old_ts = player.hasTrainStation
    try:
        player.hasTrainStation = False
        evs_1die = [delta_ev(c, player, players, 1) for c in one_die_cards]
        player.hasTrainStation = True
        evs_2die = [delta_ev(c, player, players, 1) for c in two_die_cards]
    finally:
        player.hasTrainStation = old_ts

    evs_2die_nonzero = [v for v in evs_2die if v > 0.0]
    if not evs_2die_nonzero:
        return 0.0

    med_2die = statistics.median(evs_2die_nonzero)
    med_1die = statistics.median(evs_1die) if evs_1die else 0.0
    return max(0.0, med_2die - med_1die) * N



def portfolio_ev(player: Player, players: list[Player], N: int = 1) -> float:
    """Return expected total income over N rounds, derived from round_pmf.

    Note: Amusement Park uses the PMF one-bonus-turn approximation (mean = E*(1+P_D)),
    which differs slightly from the geometric-series formula (E/(1-P_D)) used in older
    per-card EV calculations. The PMF value is the canonical one.
    """
    return N * pmf_mean(round_pmf(player, players))


def coverage_value(card: Card, owner: Player, players: list[Player]) -> float:
    """Return the expected number of times card fires per round.

    A 'round' is one full cycle: every player takes one turn, weighted by each
    player's turn multiplier (Amusement Park extra turns from doubles).

    - Blue:   fires on every player's roll → scales with player count
    - Red:    fires on each other player's roll → scales with opponent count
    - Green / Purple (Stadium, TVStation, BusinessCenter): fires only on the
              owner's roll → independent of player count
    - UpgradeCard: 0.0 (not triggered by dice)

    In a 2-player game a Blue and a Green card with identical hitsOn and no
    Train Stations have equal coverage (1 own turn, 1 opponent turn).
    In a 4-player game the same Blue card fires on 4 turns vs the Green's 1,
    so coverage skews toward cards that trigger on opponents' rolls.
    """
    if isinstance(card, UpgradeCard):
        return 0.0
    if isinstance(card, Blue):
        return sum(p_hits(card.hitsOn, _num_dice(p)) * _turn_multiplier(p) for p in players)
    if isinstance(card, Red):
        return sum(
            p_hits(card.hitsOn, _num_dice(p)) * _turn_multiplier(p)
            for p in players if p is not owner
        )
    # Green, Stadium, TVStation, BusinessCenter: fires only on the owner's roll
    return p_hits(card.hitsOn, _num_dice(owner)) * _turn_multiplier(owner)


def portfolio_coverage(player: Player, players: list[Player]) -> float:
    """Return the expected number of income events per round across the player's whole deck."""
    return sum(coverage_value(card, player, players) for card in player.deck.deck)


def _card_fires_on(card: Card, owner: Player, roller: Player, die_value: int) -> bool:
    """Return True if card fires when roller rolls die_value."""
    if isinstance(card, UpgradeCard) or die_value not in card.hitsOn:
        return False
    if isinstance(card, Blue):
        return True
    if isinstance(card, Red):
        return roller is not owner
    # Green, Stadium, TVStation, BusinessCenter: owner's roll only
    return roller is owner


def _deck_fires_on(owner: Player, roller: Player, die_value: int) -> bool:
    """Return True if any card in owner's deck fires when roller rolls die_value."""
    return any(_card_fires_on(c, owner, roller, die_value) for c in owner.deck.deck)


def delta_coverage(card: Card, owner: Player, players: list[Player]) -> float:
    """Return the marginal coverage gained by adding card to owner's deck.

    Unlike coverage_value (which counts expected fires regardless of existing deck),
    delta_coverage only counts fires on (roller, die_value) pairs not already covered
    by the owner's current deck. A second Wheat Field on an already-covered die value
    contributes 0.0; a Ranch (Blue, [2]) partially overlaps a Bakery (Green, [2,3])
    because it covers opponents rolling 2, which the Bakery doesn't.

    UpgradeCards with coverage effects:
      Train Station:  unlocks 2-die rolls → cov_2 - cov_1 on owner's turn.
      Radio Tower:    re-roll on miss → (1 - cov) * cov additional hits per turn.
      Amusement Park: bonus turn on doubles → P_DOUBLES * cov additional hits per turn.
      Shopping Mall:  payout multiplier only; zero coverage effect.
    """
    if isinstance(card, UpgradeCard):
        if card.name == "Train Station":
            return _own_turn_coverage(owner, 2) - _own_turn_coverage(owner, 1)
        if card.name == "Radio Tower":
            cov = _own_turn_coverage(owner, _num_dice(owner))
            return (1.0 - cov) * cov
        if card.name == "Amusement Park":
            cov = _own_turn_coverage(owner, _num_dice(owner))
            return P_DOUBLES * cov
        return 0.0  # Shopping Mall: pure payout multiplier, no coverage effect
    total = 0.0
    for roller in players:
        prob_table = ONE_DIE_PROB if _num_dice(roller) == 1 else TWO_DIE_PROB
        turn_mult = _turn_multiplier(roller)
        for die_value, prob in prob_table.items():
            if _card_fires_on(card, owner, roller, die_value) and not _deck_fires_on(owner, roller, die_value):
                total += prob * turn_mult
    return total


def delta_ev(
    card: Card, player: Player, players: list[Player],
    N: int = 1, market_cards: list[Card] | None = None
) -> float:
    """Return the marginal EV gain from adding card to player's deck.

    For income cards (Blue, Green, Red, Purple): temporarily appends card to the deck,
    diffs pmf_mean(round_pmf), then pops it back off. Factory synergies and Shopping Mall
    bonuses are captured automatically because round_pmf sees the full deck.
    Uses pop() rather than remove() to avoid Card.__eq__ ambiguity on duplicate sortvalues.

    For UpgradeCards: temporarily sets the attribute flag, diffs pmf_mean(round_pmf),
    restores via finally. Train Station with market_cards uses the forward-looking
    _train_station_gain heuristic (PMF diff undervalues it on a deck with no 2-die cards yet).

    BusinessCenter is dispatched to _ev_businesscenter (swap value, not coin income).
    """
    if isinstance(card, BusinessCenter):
        return _ev_businesscenter(card, player, players, N)
    if isinstance(card, UpgradeCard):
        if card.name == "Train Station" and market_cards is not None:
            return _train_station_gain(player, players, market_cards, N)
        attr = UpgradeCard.orangeCards[card.name][2]
        old_val = getattr(player, attr, False)
        try:
            setattr(player, attr, False)
            without_ev = pmf_mean(round_pmf(player, players))
            setattr(player, attr, True)
            with_ev = pmf_mean(round_pmf(player, players))
        finally:
            setattr(player, attr, old_val)
        return N * (with_ev - without_ev)
    without_ev = pmf_mean(round_pmf(player, players))
    player.deck.deck.append(card)
    try:
        with_ev = pmf_mean(round_pmf(player, players))
    finally:
        player.deck.deck.pop()
    return N * (with_ev - without_ev)


# ---------------------------------------------------------------------------
# PMF (probability mass functions)
# ---------------------------------------------------------------------------
#
# The PMF is the primitive for round-level income. It gives us:
#   - Expected (mean) rounds to plan for victory (ERUV / tuv_expected).
#   - Optimist/pessimist views via percentiles (e.g. 25/75 or 10/90) with tuv_percentile.
#   - Comparison of who's leading (opponent ERUV / delta_tuv).
#   - Confidence over a horizon: "how sure are we that we'll be across the goal line
#     in N rounds?" via prob_victory_within_n_rounds. High variance in the PMF means
#     we can spend margin shoring up weak spots (e.g. coverage, synergy) instead of
#     assuming the mean path.


def _apply_amusement_park(base: dict[int, float]) -> dict[int, float]:
    """Blend a PMF with its 2-turn convolution weighted by P_DOUBLES.

    Models the Amusement Park bonus turn: with probability P_DOUBLES the player
    takes a second draw from the same distribution; with 1-P_DOUBLES they keep
    the first. Result mean = E*(1+P_D), which slightly underestimates the true
    geometric-series value E/(1-P_D).
    """
    two_turns = _convolve(base, base)
    combined: dict[int, float] = {}
    for k in set(base) | set(two_turns):
        combined[k] = (1.0 - P_DOUBLES) * base.get(k, 0.0) + P_DOUBLES * two_turns.get(k, 0.0)
    return combined


def own_turn_pmf(player: Player, players: list[Player]) -> dict[int, float]:
    """Income distribution (PMF) for player on their own turn.

    Returns dict[int, float]: income in coins -> probability. Fires: Blue, Green,
    Stadium, TVStation (Business Center contributes 0 coins). Applies: Radio Tower
    reroll on 0 income; Amusement Park bonus-turn as extra draw from same distribution.
    Train Station: player rolls 2 dice if owned.
    """
    n_dice = _num_dice(player)
    die_pmf = _die_pmf(n_dice)
    base: dict[int, float] = {}
    for roll, prob in die_pmf.items():
        income = _own_turn_income(player, players, roll)
        base[income] = base.get(income, 0.0) + prob

    # Optimal Radio Tower strategy: reroll if income < E_own.
    # P(final=x) = P(x) * (I(x >= mu) + P_reroll), where P_reroll = sum of P(x) for x < mu.
    if getattr(player, "hasRadioTower", False):
        mu = pmf_mean(base)
        p_reroll = sum(px for x, px in base.items() if x < mu)
        base = {x: px * ((1.0 if x >= mu else 0.0) + p_reroll) for x, px in base.items()}

    # Amusement Park: (1-P_D)*base + P_D*convolve(base,base) → mean = E*(1+P_D).
    # Note: portfolio_ev uses the geometric-series multiplier 1/(1-P_D), so
    # pmf_mean(round_pmf(...)) only matches portfolio_ev for non-AP players.
    if getattr(player, "hasAmusementPark", False):
        base = _apply_amusement_park(base)

    return base


def _opponent_turn_income(observer: Player, roller: Player, roll: int) -> int:
    """Coin income for observer when roller rolls roll: Blues + Reds (steal from roller)."""
    total = 0
    for card in observer.deck.deck:
        if roll not in card.hitsOn:
            continue
        if isinstance(card, Blue):
            total += card.payout
        elif isinstance(card, Red):
            total += min(card.payout, roller.bank)
    return total


def opponent_turn_pmf(
    observer: Player, roller: Player, players: list[Player]
) -> dict[int, float]:
    """PMF of income for observer when roller takes their turn.

    Fires: observer's Blue (all rolls), observer's Red (roller's turn only).
    Does not fire: Green, Purple, or observer's Radio Tower (roller's choice).
    Amusement Park on roller: same one-bonus-turn approximation as own_turn_pmf.
    """
    die_pmf = _die_pmf(_num_dice(roller))
    base: dict[int, float] = {}
    for roll, prob in die_pmf.items():
        income = _opponent_turn_income(observer, roller, roll)
        base[income] = base.get(income, 0.0) + prob
    if getattr(roller, "hasAmusementPark", False):
        return _apply_amusement_park(base)
    return base


def round_pmf(player: Player, players: list[Player]) -> dict[int, float]:
    """PMF of net income for player over one full round (own turn + all opponents' turns).

    Convolution of own_turn_pmf with opponent_turn_pmf for each opponent. All income
    values are non-negative. This is the building block for ERUV, percentile TUV,
    and confidence intervals (e.g. P(victory within N rounds)).
    """
    acc = own_turn_pmf(player, players)
    for p in players:
        if p is player:
            continue
        opp_pmf = opponent_turn_pmf(player, p, players)
        acc = _convolve(acc, opp_pmf)
    return acc


def pmf_mean(pmf: dict[int, float]) -> float:
    """Expected (mean) income from the PMF. E[X] = sum(x * p).

    When pmf is round_pmf(...), this is expected income per round — the denominator
    for planning "expected rounds until victory" (ERUV). Matches portfolio_ev for
    non–Amusement Park players.
    """
    if not pmf:
        return 0.0
    return sum(x * p for x, p in pmf.items())


def pmf_variance(pmf: dict[int, float]) -> float:
    """Variance of the distribution. E[X^2] - E[X]^2.

    High variance means outcome is uncertain; we're less sure we'll hit the mean path.
    Use this to decide whether to shore up weak spots in the engine (coverage, synergy)
    or to treat ERUV as a confident estimate.
    """
    if not pmf:
        return 0.0
    mu = pmf_mean(pmf)
    e2 = sum((x * x) * p for x, p in pmf.items())
    return e2 - mu * mu


def pmf_percentile(pmf: dict[int, float], p: float) -> float:
    """Smallest income x such that P(income <= x) >= p.

    p=0.5 is median. p>0.5 gives an optimistic (high) income; p<0.5 pessimistic.
    Enables 25/75 or 10/90 optimist/pessimist TUV when passed to tuv_percentile(..., p).
    """
    if not pmf or p <= 0.0:
        return float(min(pmf.keys(), default=0))
    items = sorted(pmf.items())
    cumulative_sum = 0.0
    for x, prob in items:
        cumulative_sum += prob
        if cumulative_sum >= p:
            return float(x)
    return float(items[-1][0])


def pmf_mass_at_least(pmf: dict[int, float], threshold: int) -> float:
    """Probability that the outcome is >= threshold. Sum of p for all x >= threshold."""
    if not pmf:
        return 0.0
    return sum(p for x, p in pmf.items() if x >= threshold)


def _prob_win_in_n_rounds(
    player: Player, players: list[Player], n_rounds: int
) -> float:
    """Core computation: P(cumulative n_rounds income >= deficit), given a players list.

    Shared by prob_victory_within_n_rounds (Game wrapper) and MarathonBot (no Game).
    Returns 1.0 if player has already won or deficit is already met; 0.0 if n_rounds=0.
    """
    if player.isWinner():
        return 1.0
    deficit = max(0, _landmark_cost_remaining(player) - player.bank)
    if deficit <= 0:
        return 1.0
    if n_rounds <= 0:
        return 0.0
    rp = round_pmf(player, players)
    acc: dict[int, float] = {0: 1.0}
    for _ in range(n_rounds):
        acc = _convolve(acc, rp)
    return pmf_mass_at_least(acc, deficit)


def prob_victory_within_n_rounds(
    player: Player, game: Game, n_rounds: int
) -> float:
    """Probability that cumulative income over n_rounds meets or exceeds the coin deficit.

    Uses the n-fold convolution of round_pmf: "how sure are we that we'll be across
    the goal line in N rounds?" Assumes we only need to earn deficit = cost_remaining - bank;
    does not enforce the landmark-count floor (caller may require n_rounds >= n_landmarks).
    Returns 1.0 if player has already won.
    """
    return _prob_win_in_n_rounds(player, game.players, n_rounds)


# ---------------------------------------------------------------------------
# TUV (turns until victory) / ERUV (expected rounds until victory)
# ---------------------------------------------------------------------------
#
# ERUV is the expected (mean) number of rounds until victory — we plan using the mean
# income path. We also support percentile-based views (25/75 or 10/90 optimist/pessimist)
# and comparing opponent_ERUV (delta_tuv) to see who's leading and who's likely to win.
# For a given horizon N, use prob_victory_within_n_rounds for a confidence interval:
# "how sure are we that we'll be across the goal line in N rounds?" When variance is
# high, we can spend margin shoring up weak spots in our PMF instead of trusting the mean.


def _n_landmarks_remaining(player: Player) -> int:
    """Number of landmarks the player still needs to buy (0–4)."""
    owned = sum(1 for c in player.deck.deck if isinstance(c, UpgradeCard))
    return max(0, 4 - owned)


def _landmark_cost_remaining(player: Player) -> int:
    """Total cost (in coins) of landmarks the player has not yet purchased.

    Sums UpgradeCard.orangeCards cost for each landmark the player does not own.
    """
    owned_names = {c.name for c in player.deck.deck if isinstance(c, UpgradeCard)}
    return sum(
        UpgradeCard.orangeCards[name][0]
        for name in UpgradeCard.orangeCards
        if name not in owned_names
    )


def tuv_expected(player: Player, game: Game) -> float:
    """Expected rounds until victory (ERUV): mean-based plan.

    max(n_landmarks_remaining, ceil((cost_remaining - bank) / mean_income_per_round)).
    Uses pmf_mean(round_pmf(...)) as per-round income. Returns 0.0 if player has won.
    Example: 5.22 means we plan for ~5–6 rounds; use prob_victory_within_n_rounds for
    confidence (e.g. how sure we are we'll be across the goal line in 6 rounds).
    """
    if player.isWinner():
        return 0.0
    n_landmarks = _n_landmarks_remaining(player)
    cost_remaining = _landmark_cost_remaining(player)
    income_per_round = pmf_mean(round_pmf(player, game.players))
    if income_per_round <= 0:
        return float(n_landmarks)
    deficit = max(0, cost_remaining - player.bank)
    income_ceiling = math.ceil(deficit / income_per_round)
    return float(max(n_landmarks, income_ceiling))


def tuv_percentile(player: Player, game: Game, p: float = 0.5) -> float:
    """Rounds-until-victory using percentile income instead of mean.

    p=0.5 is median. p>0.5 optimistic (e.g. 0.75 or 0.9 for "if things go well");
    p<0.5 pessimistic (e.g. 0.25 or 0.1 for worst-case). Enables 25/75 or 10/90
    optimist/pessimist planning.
    """
    if player.isWinner():
        return 0.0
    n_landmarks = _n_landmarks_remaining(player)
    cost_remaining = _landmark_cost_remaining(player)
    income = pmf_percentile(round_pmf(player, game.players), p)
    if income <= 0:
        return float(n_landmarks)
    deficit = max(0, cost_remaining - player.bank)
    return float(max(n_landmarks, math.ceil(deficit / income)))


def tuv_variance(player: Player, game: Game) -> float:
    """Variance of per-round income (from round_pmf).

    High variance = outcome uncertain; ERUV is less reliable and we may want to shore
    up weak spots. Low variance = win/loss trajectory is already fairly determined.
    """
    return pmf_variance(round_pmf(player, game.players))


def delta_tuv(player_a: Player, player_b: Player, game: Game) -> float:
    """Difference in expected rounds until victory: ERUV(A) - ERUV(B).

    Positive = A is behind (more rounds left), negative = A is ahead. Use to compare
    opponent_ERUV and determine who's leading and who's likely to win.
    """
    return tuv_expected(player_a, game) - tuv_expected(player_b, game)


def score_purchase_options(player: Player, cards: list[Card], players: list[Player], N: int = 1) -> dict[Card, float]:
    """Return a {Card: delta_ev} dict for cards, sorted descending by delta_ev.

    cards should be pre-filtered to distinct, affordable options.
    players is passed to delta_ev for opponent-count-sensitive EV (Red, Blue, Purple cards).
    """
    if not cards:
        return {}
    scored = [
        (card, delta_ev(card, player, players, N, market_cards=cards))
        for card in cards
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return dict(scored)


