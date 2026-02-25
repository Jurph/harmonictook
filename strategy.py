#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# strategy.py — EV-based card valuation library for harmonictook
# Pure functions only: no side effects, no I/O. Returns scores; callers decide how to act.

from __future__ import annotations
import statistics
from harmonictook import Blue, Green, Red, Stadium, TVStation, BusinessCenter, Player, Game, Card, UpgradeCard  # noqa: F401 (UpgradeCard used in ev dispatch TODO)

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


def ev(card: Card, owner: Player, players: list[Player], N: int = 1) -> float:
    """Return the expected coins gained per N rounds from owning card.

    Dispatches to type-specific helpers. UpgradeCard always returns 0.0
    (use delta_ev to value upgrades via portfolio difference).
    """
    if isinstance(card, UpgradeCard):
        return 0.0
    if isinstance(card, Blue):
        return _ev_blue(card, owner, players, N)
    if isinstance(card, Green):
        return _ev_green(card, owner, players, N)
    if isinstance(card, Red):
        return _ev_red(card, owner, players, N)
    if isinstance(card, Stadium):
        return _ev_stadium(card, owner, players, N)
    if isinstance(card, TVStation):
        return _ev_tvstation(card, owner, players, N)
    if isinstance(card, BusinessCenter):
        return _ev_businesscenter(card, owner, players, N)
    return 0.0


def _ev_blue(card: Blue, owner: Player, players: list[Player], N: int) -> float:
    """EV for a Blue card: fires on every player's roll."""
    total_per_round = card.payout * sum(
        p_hits(card.hitsOn, _num_dice(p)) for p in players
    )
    return N * total_per_round


def _ev_green(card: Green, owner: Player, players: list[Player], N: int) -> float:
    """EV for a Green card: fires only on the owner's roll."""
    n_dice = _num_dice(owner)
    turn_mult = _turn_multiplier(owner)
    hit_prob = p_hits(card.hitsOn, n_dice)

    if getattr(card, "multiplies", None) is not None:
        count = _count_category(owner, card.multiplies)
        return N * card.payout * count * hit_prob * turn_mult
    payout_eff = card.payout
    if owner.hasShoppingMall and card.name == "Convenience Store":
        payout_eff += 1
    return N * payout_eff * hit_prob * turn_mult


def _ev_red(card: Red, owner: Player, players: list[Player], N: int) -> float:
    """EV for a Red card: fires on each other player's roll, bounded by their bank."""
    total_per_round = 0.0
    for p in players:
        if p is owner:
            continue
        total_per_round += min(card.payout, p.bank) * p_hits(card.hitsOn, _num_dice(p))
    return N * total_per_round


def _ev_stadium(card: Stadium, owner: Player, players: list[Player], N: int) -> float:
    """EV for Stadium: net gain = payout * (len(players)-1) per trigger on a 6."""
    net_per_trigger = card.payout * (len(players) - 1)
    hit_prob = p_hits([6], _num_dice(owner))
    turn_mult = _turn_multiplier(owner)
    return N * net_per_trigger * hit_prob * turn_mult


def _ev_tvstation(card: TVStation, owner: Player, players: list[Player], N: int) -> float:
    """EV for TV Station: steal up to 5 from the richest opponent when owner rolls a 6."""
    opponents = [p for p in players if p is not owner]
    if not opponents:
        return 0.0
    max_bank = max(p.bank for p in opponents)
    steal = min(5, max_bank)
    return steal * p_hits([6], _num_dice(owner)) * _turn_multiplier(owner) * N


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

        # Best card to give: bottom-4 own cards by EV, then least valuable to target
        own_by_ev = sorted(own_cards, key=lambda c: ev(c, owner, players, 1))
        bottom_4 = own_by_ev[:4]
        best_give = min(bottom_4, key=lambda c: delta_ev(c, target, players, 1))
        give_loss = ev(best_give, owner, players, 1)

        net = best_gain - give_loss
        if net > best_net:
            best_net = net

    return best_net * p_hits([6], _num_dice(owner)) * _turn_multiplier(owner) * N


def _radio_tower_gain(player: Player, players: list[Player], N: int) -> float:
    """EV gain per N rounds from Radio Tower: option value of rerolling a bad roll.

    Optimal strategy: after rolling, reroll if V(r) < E_own (expected own-turn income),
    since the expected value of a reroll is exactly E_own.

    E_with_RT = Σ_r  P(r) × max(V(r), E_own)
    gain/turn  = (E_with_RT − E_own) × turn_multiplier

    V(r) covers own-turn income only: Blue (own payout), Green, Stadium, TVStation.
    Red is excluded — it fires on opponents' turns and is unaffected by the owner's reroll.
    BusinessCenter is excluded (its income is a swap, not a coin amount).
    """
    num_dice = _num_dice(player)
    prob_table = ONE_DIE_PROB if num_dice == 1 else TWO_DIE_PROB

    def own_roll_income(r: int) -> float:
        total = 0.0
        for card in player.deck.deck:
            if r not in card.hitsOn:
                continue
            if isinstance(card, Blue):
                total += card.payout
            elif isinstance(card, Green):
                if card.multiplies:
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

    e_own = sum(prob * own_roll_income(r) for r, prob in prob_table.items())
    e_with_rt = sum(prob * max(own_roll_income(r), e_own) for r, prob in prob_table.items())
    return (e_with_rt - e_own) * _turn_multiplier(player) * N


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
        evs_1die = [ev(c, player, players, 1) for c in one_die_cards]
        player.hasTrainStation = True
        evs_2die = [ev(c, player, players, 1) for c in two_die_cards]
    finally:
        player.hasTrainStation = old_ts

    evs_2die_nonzero = [v for v in evs_2die if v > 0.0]
    if not evs_2die_nonzero:
        return 0.0

    med_2die = statistics.median(evs_2die_nonzero)
    med_1die = statistics.median(evs_1die) if evs_1die else 0.0
    return max(0.0, med_2die - med_1die) * N


def _factory_synergy_gain(new_card: Card, player: Player, players: list[Player], N: int) -> float:
    """Return the EV boost to existing factory cards caused by adding new_card to player's deck.

    For each Green factory in player's deck where card.multiplies == new_card.category,
    adds N * card.payout * p_hits(card.hitsOn, _num_dice(player)) * _turn_multiplier(player).
    """
    total = 0.0
    new_cat = getattr(new_card, "category", None)
    if new_cat is None:
        return total
    for c in player.deck.deck:
        if isinstance(c, Green) and getattr(c, "multiplies", None) == new_cat:
            total += (
                c.payout
                * 1
                * p_hits(c.hitsOn, _num_dice(player))
                * _turn_multiplier(player)
                * N
            )
    return total


def portfolio_ev(player: Player, players: list[Player], N: int = 1) -> float:
    """Return the total EV of all cards in player's deck over N rounds."""
    return sum(ev(card, player, players, N) for card in player.deck.deck)


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

    For UpgradeCards: temporarily sets the flag on player, diffs portfolio_ev, restores via finally.
    For factory-synergy cards: adds _factory_synergy_gain on top of direct ev.
    When market_cards is provided, Train Station uses forward-looking valuation instead of
    portfolio-diff (portfolio-diff undervalues it on a starting deck with no 2-die cards).
    """
    if isinstance(card, UpgradeCard):
        if card.name == "Radio Tower":
            return _radio_tower_gain(player, players, N)
        if card.name == "Train Station" and market_cards is not None:
            return _train_station_gain(player, players, market_cards, N)
        attr = UpgradeCard.orangeCards[card.name][2]
        old_val = getattr(player, attr, False)
        without_ev = portfolio_ev(player, players, N)
        try:
            setattr(player, attr, True)
            with_ev = portfolio_ev(player, players, N)
        finally:
            setattr(player, attr, old_val)
        return with_ev - without_ev
    direct = ev(card, player, players, N)
    synergy = _factory_synergy_gain(card, player, players, N)
    return direct + synergy


# ---------------------------------------------------------------------------
# PMF (probability mass functions)
# ---------------------------------------------------------------------------

def own_turn_pmf(player: Player, players: list[Player]) -> dict[int, float]:
    """Income distribution for player on their own turn.

    Fires: Blue, Green, Stadium, TVStation (Business Center contributes 0 coins).
    Applies: Radio Tower reroll on 0 income; Amusement Park bonus-turn as extra
    draw from same distribution. Train Station: player rolls 2 dice if owned.
    """
    n_dice = _num_dice(player)
    die_pmf = _die_pmf(n_dice)
    base: dict[int, float] = {}
    for roll, prob in die_pmf.items():
        income = _own_turn_income(player, players, roll)
        base[income] = base.get(income, 0.0) + prob

    # Key assumption: Radio Tower rerolls only on a 0 income turn. Later we might model 0, 1, or even 2 as unsatisfactory. 
    if getattr(player, "hasRadioTower", False):
        p0 = base.get(0, 0.0)
        rt: dict[int, float] = {0: p0 * p0}
        for x, px in base.items():
            if x != 0:
                rt[x] = px * (1.0 + p0)
        base = rt

    # Key assumption: Amusement Park gives a free turn on doubles, but we don't really handle the fact that only even turns
    # get a bonus turn, so our PMF for the first half of the turn is "evens-only". We just use the regular PMF. 
    if getattr(player, "hasAmusementPark", False):
        two_turns = _convolve(base, base)
        combined: dict[int, float] = {}
        for k in set(base) | set(two_turns):
            combined[k] = (1.0 - P_DOUBLES) * base.get(k, 0.0) + P_DOUBLES * two_turns.get(k, 0.0)
        base = combined

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


def opponent_turn_pmf(observer: Player, roller: Player, players: list[Player]) -> dict[int, float]:
    """Income distribution for observer when roller takes their turn.

    Fires: observer's Blue (all rolls), observer's Red (roller's turn only).
    Does not fire: Green, Purple, or observer's Radio Tower (roller's choice).
    """
    die_pmf = _die_pmf(_num_dice(roller))
    out: dict[int, float] = {}
    for roll, prob in die_pmf.items():
        income = _opponent_turn_income(observer, roller, roll)
        out[income] = out.get(income, 0.0) + prob
    return out


def round_pmf(player: Player, players: list[Player]) -> dict[int, float]:
    """Net income for player over one full round (own turn + all opponents' turns).

    Convolution of own_turn_pmf with opponent_turn_pmf for each opponent.
    Values may be negative (Red theft is already in opponent_turn_pmf as positive
    to observer; here we treat observer's income as positive so round = own + opp1 + opp2...).
    """
    acc = own_turn_pmf(player, players)
    for p in players:
        if p is player:
            continue
        opp_pmf = opponent_turn_pmf(player, p, players)
        acc = _convolve(acc, opp_pmf)
    return acc


def pmf_mean(pmf: dict[int, float]) -> float:
    """Weighted average income. Matches portfolio_ev when PMF is round_pmf."""
    if not pmf:
        return 0.0
    return sum(x * p for x, p in pmf.items())


def pmf_variance(pmf: dict[int, float]) -> float:
    """E[X^2] - E[X]^2."""
    if not pmf:
        return 0.0
    mu = pmf_mean(pmf)
    e2 = sum((x * x) * p for x, p in pmf.items())
    return e2 - mu * mu


def pmf_percentile(pmf: dict[int, float], p: float) -> float:
    """Smallest income x such that P(income <= x) >= p. p=0.5 is median."""
    if not pmf or p <= 0.0:
        return min(pmf.keys(), default=0)
    items = sorted(pmf.items())
    cumulative_sum = 0.0
    for x, prob in items:
        cumulative_sum += prob
        if cumulative_sum >= p:
            return float(x)
    return float(items[-1][0])


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


