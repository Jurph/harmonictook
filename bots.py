#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# bots.py — Strategy-informed bot subclasses for harmonictook
#
# All classes here subclass Bot (defined in harmonictook.py) and depend on
# EV/coverage functions from strategy.py. Basic Bot stays in harmonictook.py
# because it has no external dependencies; every subclass that diverges from
# Bot's random defaults lives here instead.

from __future__ import annotations

import math
import random

from harmonictook import Blue, Bot, Card, Game, Green, Stadium, TVStation, UpgradeCard
from strategy import (
    delta_coverage,
    delta_ev,
    own_turn_pmf,
    pmf_mean,
    pmf_variance,
    round_pmf,
    score_purchase_options,
    _count_category,
    _landmark_cost_remaining,
    _n_landmarks_remaining,
    _own_turn_coverage,
    _prob_win_in_n_rounds,
)


def _roll_income(player: Bot, roll: int) -> int:
    """Coin income for player on their own turn when the die total is roll.

    Covers Blue, Green (including factory multiplication and Shopping Mall bonus),
    Stadium (payout * 1, conservative floor — exact multiplier requires player list),
    and TVStation (assumes max 5-coin steal). Used by reroll heuristics; approximations
    are acceptable as long as profitable rolls register as non-zero.
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
            # Exact income = payout × n_opponents, unknown here; use payout as a floor.
            total += card.payout
        elif isinstance(card, TVStation):
            # Steal up to 5; assume opponents have coins for reroll decision purposes.
            total += 5
    return total


def _with_card_bought(player: Bot, card: Card, fn) -> float:
    """Temporarily buy card (deduct cost, mutate deck/flags), call fn(), restore all state.

    Handles UpgradeCards (set flag + append to deck) and income cards (append only).
    Restores bank, deck, and flag even if fn() raises.
    """
    player.bank -= card.cost
    if isinstance(card, UpgradeCard):
        attr = UpgradeCard.orangeCards[card.name][2]
        old_val = getattr(player, attr, False)
        setattr(player, attr, True)
        player.deck.deck.append(card)
        try:
            return fn()
        finally:
            player.deck.deck.pop()
            setattr(player, attr, old_val)
            player.bank += card.cost
    else:
        player.deck.deck.append(card)
        try:
            return fn()
        finally:
            player.deck.deck.pop()
            player.bank += card.cost


def _with_card_appended(player: Bot, card: Card, fn) -> float:
    """Temporarily append card to deck (no payment, no flag change), call fn(), restore."""
    player.deck.deck.append(card)
    try:
        return fn()
    finally:
        player.deck.deck.pop()


def _with_card_removed(player: Bot, card: Card, fn) -> float:
    """Temporarily remove card from deck by identity, call fn(), restore.

    Uses object identity to handle duplicate-name cards correctly.
    If card is not in deck, fn() is called on the unmodified deck.
    """
    idx = next((i for i, c in enumerate(player.deck.deck) if c is card), None)
    if idx is None:
        return fn()
    removed = player.deck.deck.pop(idx)
    try:
        return fn()
    finally:
        player.deck.deck.insert(idx, removed)


def _card_variance(player: Bot, card: Card, players: list) -> float:
    """Income variance of round_pmf after temporarily adding card (used as tiebreaker).

    For UpgradeCards, activates the flag without appending to deck or deducting cost —
    variance reflects the income distribution change only.
    """
    if isinstance(card, UpgradeCard):
        attr = UpgradeCard.orangeCards[card.name][2]
        old_val = getattr(player, attr, False)
        setattr(player, attr, True)
        try:
            return pmf_variance(round_pmf(player, players))
        finally:
            setattr(player, attr, old_val)
    return _with_card_appended(player, card, lambda: pmf_variance(round_pmf(player, players)))


def _eruv_for(player: Bot, players: list) -> float:
    """Compute ERUV for any player given a players list (no Game required)."""
    n_lm = _n_landmarks_remaining(player)
    cost = _landmark_cost_remaining(player)
    income = pmf_mean(round_pmf(player, players))
    if income <= 0:
        return float(n_lm)
    deficit = max(0, cost - player.bank)
    return float(max(n_lm, math.ceil(deficit / income)))


_MARATHON_TARGET: dict[int, int] = {2: 20, 3: 17, 4: 17}
_MARATHON_TARGET_DEFAULT: int = 17


def _leader_n(players: list) -> int:
    """Target N for MarathonBot: min of empirical fast-game target and leader-ERUV pace.

    Empirical targets (per-player median from tournament data, rounded down):
      2P → 20, 3P+ → 17.
    Leader pace: floor(min_ERUV_across_players) - 1.
    Early game: empirical cap dominates (prevents unrealistic aggression).
    Late game: leader pace dominates when the leader is within striking distance.
    """
    active = [p for p in players if not p.isWinner()]
    if not active:
        return 1
    min_eruv = min(_eruv_for(p, players) for p in active)
    leader_n = max(1, math.floor(min_eruv) - 1)
    empirical_n = _MARATHON_TARGET.get(len(players), _MARATHON_TARGET_DEFAULT)
    return min(empirical_n, leader_n)


def _dice_by_ev(player: Bot, players: list) -> int:
    """Return whichever dice count (1 or 2) yields higher expected own-turn income.

    Temporarily flips hasTrainStation to compare pmf_mean(own_turn_pmf) for each
    option. Always returns 1 if the player has no Train Station.
    """
    if not player.hasTrainStation:
        return 1
    old = player.hasTrainStation
    try:
        player.hasTrainStation = False
        ev1 = pmf_mean(own_turn_pmf(player, players))
        player.hasTrainStation = True
        ev2 = pmf_mean(own_turn_pmf(player, players))
    finally:
        player.hasTrainStation = old
    return 2 if ev2 >= ev1 else 1


class ThoughtfulBot(Bot):
    """Priority-driven bot that follows a fixed card-preference ordering."""

    # Cards that require a matching-category engine before they have non-zero EV.
    # key = card name, value = (multiplies_category, minimum_count_needed).
    _FACTORY_PREREQS: dict[str, tuple[int, int]] = {
        "Cheese Factory":           (2, 1),  # category 2 = Ranch
        "Furniture Factory":        (5, 1),  # category 5 = Forest / Mine
        "Farmer's Market":          (1, 1),  # category 1 = Wheat Field / Apple Orchard
    }

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return the highest-priority card name from a list of Card objects.

        When Train Station is owned, latecards are added before earlycards, but factory
        latecards are skipped if the player has fewer matching-category cards than the
        required minimum — buying a 0-EV factory is never the right move.
        """
        if not options:
            return None
        names = [c.name for c in options]
        upgrades = ["Radio Tower", "Amusement Park", "Shopping Mall", "Train Station"]
        earlycards = [
            "TV Station", "Business Center", "Stadium", "Forest",
            "Convenience Store", "Ranch", "Wheat Field", "Cafe", "Bakery",
        ]
        latecards = [
            "Mine", "Furniture Factory", "Cheese Factory",
            "Family Restaurant", "Apple Orchard", "Farmer's Market",
        ]
        if self.hasTrainStation:
            eligible_latecards = [
                c for c in latecards
                if c not in self._FACTORY_PREREQS
                or _count_category(self, self._FACTORY_PREREQS[c][0]) >= self._FACTORY_PREREQS[c][1]
            ]
            preferences = upgrades + eligible_latecards + earlycards
        else:
            preferences = upgrades + earlycards
        for priority in preferences:
            if priority in names:
                return priority
        return random.choice(names)

    def chooseDice(self, players: list | None = None) -> int:
        return _dice_by_ev(self, players or [self])


class EVBot(Bot):
    """Bot that ranks purchase options by delta_ev and buys the highest-scoring card.

    n_horizon controls the N-round planning horizon passed to score_purchase_options.
    Inherits Bot.chooseAction (buy if affordable) and Bot.chooseDice/chooseReroll.
    chooseCard accepts Card objects (scored directly, no game needed) or string names
    (resolved from game.market when game is supplied; random fallback otherwise).
    """

    def __init__(self, name: str = "EVBot", n_horizon: int = 1) -> None:
        super().__init__(name=name)
        self.n_horizon = n_horizon

    def chooseDice(self, players: list | None = None) -> int:
        return _dice_by_ev(self, players or [self])

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return the name of the highest delta_ev Card from options.

        players defaults to [self] when no game is supplied.
        """
        if not options:
            return None
        use_players = list(game.players) if game else [self]
        scored = score_purchase_options(self, options, use_players, N=self.n_horizon)
        return next(iter(scored)).name if scored else random.choice(options).name


class CoverageBot(Bot):
    """Bot that builds toward complete die-value coverage and rolls whichever dice count
    best covers its current deck.

    chooseCard always buys a landmark when one is available, ranking landmarks by
    (delta_coverage, delta_ev). When no landmark is in options, the same key ranks
    establishments by new-slot coverage then income. chooseDice compares
    _own_turn_coverage for 1 vs 2 dice and picks the stronger side.
    """

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Buy the highest (delta_coverage, delta_ev) Card; landmarks always take priority.

        When UpgradeCards are present in options they form the entire candidate pool —
        the bot never picks an establishment while a landmark is available.
        """
        if not options:
            return None

        def _score(c: Card, players: list, all_cards: list) -> tuple:
            return (delta_coverage(c, self, players), delta_ev(c, self, players, market_cards=all_cards))

        use_players = list(game.players) if game else [self]
        landmarks = [c for c in options if isinstance(c, UpgradeCard)]
        pool = landmarks if landmarks else options
        return max(pool, key=lambda c: _score(c, use_players, options)).name

    def chooseDice(self, players: list | None = None) -> int:
        """Roll 2 dice if they cover more of the deck's hitsOn range than 1 die; else roll 1."""
        if not self.hasTrainStation:
            return 1
        return 2 if _own_turn_coverage(self, 2) > _own_turn_coverage(self, 1) else 1


class ImpatientBot(Bot):
    """Bot that minimizes expected rounds until victory (ERUV) at every decision.

    At each choice point, computes how each option changes tuv_expected and picks
    whichever option minimizes it. Income variance breaks ties — lower variance means
    a more predictable path to victory.

    chooseAction and chooseReroll use [self] as the player list (no game reference
    available there); this underestimates Blue-card income from opponents' turns but
    is directionally correct for the buy/pass and reroll decisions.
    chooseCard and chooseBusinessCenterSwap use game.players when available.
    """

    # ------------------------------------------------------------------
    # Public decision methods
    # ------------------------------------------------------------------

    def chooseDice(self, players: list | None = None) -> int:
        return _dice_by_ev(self, players or [self])

    def chooseReroll(self, last_roll: int | None = None) -> bool:
        """Reroll if this roll's income falls in the bottom third of all possible outcomes.

        Builds an income table for rolls 1-12, sorts it, and rerolls if the current
        roll's income is at or below the 4th-lowest value (bottom 4 of 12 = bottom third).
        """
        if not self.hasRadioTower or last_roll is None:
            return False
        incomes = sorted(self._own_income_for_roll(x) for x in range(1, 13))
        threshold = incomes[3]  # top of the bottom third
        return self._own_income_for_roll(last_roll) <= threshold

    def chooseAction(self, availableCards) -> str:
        """Buy a landmark if affordable; buy income card only if it reduces ERUV; else pass.

        Landmarks are checked via checkRemainingUpgrades() — they are never in the market
        deck and cannot be detected by iterating availableCards.deck.
        """
        # Landmarks are the win condition — always buy one if it's within reach.
        for upgrade in self.checkRemainingUpgrades():
            if upgrade.cost <= self.bank:
                return 'buy'
        options = availableCards.names(maxcost=self.bank)
        if not options:
            return 'pass'
        players = [self]  # approximation: no game reference here
        base_tuv = self._tuv_with(players)
        for name in options:
            card = next((c for c in availableCards.deck if c.name == name), None)
            if card is not None and self._tuv_after_buy(card, players) < base_tuv:
                return 'buy'
        return 'pass'

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return the name of the Card that minimizes post-purchase ERUV.

        Ties broken by income variance (lower = more predictable path to victory).
        """
        if not options:
            return None
        players = list(game.players) if game else [self]
        best_name: str | None = None
        best_tuv = float('inf')
        best_var = float('inf')
        for card in options:
            t = self._tuv_after_buy(card, players)
            v = self._var_after_buy(card, players)
            if t < best_tuv or (t == best_tuv and v < best_var):
                best_tuv, best_var, best_name = t, v, card.name
        return best_name if best_name is not None else random.choice(options).name

    def chooseBusinessCenterSwap(
        self, target, my_swappable: list, their_swappable: list
    ) -> tuple[Card, Card] | None:
        """Choose what to give and take in a Business Center swap.

        Give: the card whose removal increases our ERUV the least (least valuable to keep).
        Take: the card whose addition decreases our ERUV the most.
        Players approximated as [self] — no game reference available here.
        """
        if not my_swappable or not their_swappable:
            return None
        players = [self]
        card_to_give = min(my_swappable, key=lambda c: self._tuv_after_remove(c, players))
        card_to_take = min(their_swappable, key=lambda c: self._tuv_after_add(c, players))
        return (card_to_give, card_to_take)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _own_income_for_roll(self, roll: int) -> int:
        """Coin income on own turn for a given roll. Delegates to module-level _roll_income."""
        return _roll_income(self, roll)

    def _tuv_with(self, players: list) -> float:
        """ERUV from a players list. Delegates to module-level _eruv_for."""
        return _eruv_for(self, players)

    def _tuv_after_buy(self, card: Card, players: list) -> float:
        """ERUV after buying card (deduct cost, mutate deck/flags, compute, restore)."""
        return _with_card_bought(self, card, lambda: self._tuv_with(players))

    def _tuv_after_add(self, card: Card, players: list) -> float:
        """ERUV after adding card with no payment (Business Center take evaluation)."""
        return _with_card_appended(self, card, lambda: self._tuv_with(players))

    def _tuv_after_remove(self, card: Card, players: list) -> float:
        """ERUV after removing card from deck by identity (Business Center give evaluation)."""
        return _with_card_removed(self, card, lambda: self._tuv_with(players))

    def _var_after_buy(self, card: Card, players: list) -> float:
        """Income variance if card were active (no payment). Delegates to _card_variance."""
        return _card_variance(self, card, players)


class FromageBot(Bot):
    """Priority-driven bot with per-card purchase caps, derived from tournament data.

    Builds a Ranch-Cheese engine as its primary win path.  The PRIORITY list is
    processed in order: the bot buys the first entry where it owns fewer than cap
    copies and the card is available.  Duplicate entries (e.g. Ranch appears three
    times at caps 3, 5, 7) let the engine build in stages — get cattle first, then
    unlock the Cheese Factory multiplier, then expand cattle further.

    Fallback when all priority items are satisfied: prefer options not already at
    their cap; if everything is at cap, buy anything available.
    """

    #: (card_name, max_copies): walked in order each turn.
    PRIORITY: list[tuple[str, int]] = [
        # Landmarks — always buy when affordable; they are the win condition.
        ("Radio Tower",              1),
        ("Amusement Park",           1),
        ("Shopping Mall",            1),
        ("Train Station",            1),
        # Stage 1: cattle foundation.
        ("Ranch",                    3),
        # Stage 2: first multiplier — now a 7-roll pays 9+ coins.
        ("Cheese Factory",           1),
        # Stage 3: cheap reliable income while the engine grows.
        ("Convenience Store",        4),
        # Stage 4: expand cattle with CF already active.
        ("Ranch",                    5),
        # Stage 5: Mine — high direct payout AND gear for a potential FF.
        ("Mine",                     2),
        # Stage 6: second multiplier — only worth it with 5+ cattle.
        ("Cheese Factory",           2),
        # Stage 7: maximise cattle.
        ("Ranch",                    7),
        # Fill remaining income slots with reliable cards.
        ("Bakery",                   3),
        ("Apple Orchard",            2),
        ("Wheat Field",              3),
        ("Family Restaurant",        1),
        # Low-value additions: one each is fine, stacking is not.
        ("Forest",                   2),
        ("Furniture Factory",        1),
        ("TV Station",               1),
        ("Business Center",          1),
        ("Stadium",                  1),
        ("Cafe",                     1),
        ("Farmer's Market",          2),
    ]

    def _count(self, name: str) -> int:
        """Count copies of a card by name in this player's deck."""
        return sum(1 for c in self.deck.deck if c.name == name)

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return the first priority-list Card whose count is below its cap.

        Falls back to Cards not yet at their cap; if everything is at cap,
        picks uniformly at random from all options.
        """
        if not options:
            return None
        names = [c.name for c in options]
        name_set = set(names)
        for card_name, cap in self.PRIORITY:
            if card_name in name_set and self._count(card_name) < cap:
                return card_name
        # Fallback: avoid cards that are at or above their highest stated cap.
        max_cap = {name: 0 for name in name_set}
        for card_name, cap in self.PRIORITY:
            if card_name in max_cap:
                max_cap[card_name] = max(max_cap[card_name], cap)
        uncapped = [n for n in names if self._count(n) < max_cap.get(n, 1)]
        return random.choice(uncapped if uncapped else names)

    def chooseDice(self, players: list | None = None) -> int:
        return _dice_by_ev(self, players or [self])


class MarathonBot(Bot):
    """Bot that maximizes P(win in N rounds), N = max(1, floor(leader_ERUV) - 1).

    Paces to win one round ahead of the current leader — whether that's itself or an
    opponent. Always buys landmarks when affordable (they are the win condition).
    Coasts (passes) when saving coins for a landmark beats buying an income card.
    Targets the lowest-ERUV opponent for theft: always hits the most dangerous player.

    chooseAction and chooseReroll approximate N from [self] (no game reference there).
    chooseCard and chooseBusinessCenterSwap use game.players when available.
    """

    def _target_n(self, players: list) -> int:
        """Target rounds-to-win horizon. Overrideable by subclasses."""
        return _leader_n(players)

    # ------------------------------------------------------------------
    # Public decision methods
    # ------------------------------------------------------------------

    def chooseDice(self, players: list | None = None) -> int:
        """Pick the dice count that maximizes P(win in N)."""
        use_players = players or [self]
        if not self.hasTrainStation:
            return 1
        n = self._target_n(use_players)
        old = self.hasTrainStation
        try:
            self.hasTrainStation = False
            p1 = _prob_win_in_n_rounds(self, use_players, n)
            self.hasTrainStation = True
            p2 = _prob_win_in_n_rounds(self, use_players, n)
        finally:
            self.hasTrainStation = old
        return 2 if p2 >= p1 else 1

    def chooseReroll(self, last_roll: int | None = None) -> bool:
        """Two-regime reroll: sprint if N=1 (reroll unless income covers deficit),
        marathon if N>1 (reroll if income falls in the bottom third of outcomes).

        N is approximated from own ERUV using [self] as players.
        """
        if not self.hasRadioTower or last_roll is None:
            return False
        income = _roll_income(self, last_roll)
        n = self._target_n([self])
        if n == 1:
            deficit = max(0, _landmark_cost_remaining(self) - self.bank)
            return income < deficit
        incomes = sorted(_roll_income(self, x) for x in range(1, 13))
        return income <= incomes[3]  # bottom third of 12 outcomes

    def chooseAction(self, availableCards) -> str:
        """Buy a landmark if affordable; buy income card only if P(win in N) improves; else coast.

        Landmarks are checked via checkRemainingUpgrades() — they are never in the market
        deck and cannot be detected by iterating availableCards.deck.
        """
        # Landmarks are the win condition — always buy one if it's within reach.
        for upgrade in self.checkRemainingUpgrades():
            if upgrade.cost <= self.bank:
                return 'buy'
        options = availableCards.names(maxcost=self.bank)
        if not options:
            return 'pass'
        players = [self]
        # Income card: only buy if doing so raises P(win in N) above coasting.
        n = self._target_n(players)
        base_pwn = _prob_win_in_n_rounds(self, players, n)
        for name in options:
            card = next((c for c in availableCards.deck if c.name == name), None)
            if card is not None and self._pwn_after_buy(card, players, n) > base_pwn:
                return 'buy'
        return 'pass'

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return the name of the Card that maximises P(win in N). Tiebreak: lower income variance."""
        if not options:
            return None
        players = list(game.players) if game else [self]
        n = self._target_n(players)
        best_name: str | None = None
        best_pwn = -1.0
        best_var = float('inf')
        for card in options:
            p = self._pwn_after_buy(card, players, n)
            v = _card_variance(self, card, players)
            if p > best_pwn or (p == best_pwn and v < best_var):
                best_pwn, best_var, best_name = p, v, card.name
        return best_name if best_name is not None else random.choice(options).name

    def chooseTarget(self, players: list) -> 'Bot | None':
        """Steal from the opponent with the lowest ERUV; tiebreak on richest."""
        valid = [p for p in players if not p.isrollingdice]
        if not valid:
            return None
        return min(valid, key=lambda p: (_eruv_for(p, players), -p.bank))

    def chooseBusinessCenterSwap(
        self, target, my_swappable: list, their_swappable: list
    ) -> 'tuple[Card, Card] | None':
        """Give the card whose removal hurts P(win in N) least; take the card that helps most."""
        if not my_swappable or not their_swappable:
            return None
        players = [self]
        n = self._target_n(players)
        card_to_give = max(my_swappable, key=lambda c: self._pwn_after_remove(c, players, n))
        card_to_take = max(their_swappable, key=lambda c: self._pwn_after_add(c, players, n))
        return (card_to_give, card_to_take)

    # ------------------------------------------------------------------
    # Private helpers — P(win in N) mutation variants
    # ------------------------------------------------------------------

    def _pwn_after_buy(self, card: Card, players: list, n: int) -> float:
        """P(win in N) after buying card (deduct cost, mutate deck/flags, compute, restore)."""
        return _with_card_bought(self, card, lambda: _prob_win_in_n_rounds(self, players, n))

    def _pwn_after_add(self, card: Card, players: list, n: int) -> float:
        """P(win in N) after adding card with no payment (Business Center take)."""
        return _with_card_appended(self, card, lambda: _prob_win_in_n_rounds(self, players, n))

    def _pwn_after_remove(self, card: Card, players: list, n: int) -> float:
        """P(win in N) after removing card from deck by identity (Business Center give)."""
        return _with_card_removed(self, card, lambda: _prob_win_in_n_rounds(self, players, n))


def _kinematic_n(
    opponents: list,
    players: list,
    a: float,
    eruv_offset: int,
) -> int:
    """Kinematic target N: when does the most dangerous opponent finish, minus offset.

    For each opponent, estimates their rounds-to-win using:
        N = (-v + sqrt(v² + 2·a_eff·deficit)) / a_eff
    where a_eff = a * (n_players + 3) / 7  (table-size scaling, anchored at 4P).

    Falls back to ceil(deficit / v) when a ≈ 0.
    Applies the empirical cap from _MARATHON_TARGET, then subtracts eruv_offset.
    Returns at least 1.
    """
    n_players = len(players)
    a_eff = a * (n_players + 3) / 7

    ns = []
    for opp in opponents:
        deficit = max(0.0, float(_landmark_cost_remaining(opp) - opp.bank))
        if deficit <= 0.0:
            ns.append(1)
            continue
        v = pmf_mean(round_pmf(opp, players))
        if v <= 0.0:
            ns.append(999)
            continue
        if a_eff < 1e-9:
            n_k = deficit / v
        else:
            n_k = (-v + math.sqrt(v * v + 2.0 * a_eff * deficit)) / a_eff
        ns.append(max(1, math.ceil(n_k)))

    leader_n = min(ns) if ns else 1
    empirical_n = _MARATHON_TARGET.get(n_players, _MARATHON_TARGET_DEFAULT)
    return max(1, min(empirical_n, leader_n) - eruv_offset)


class KinematicBot(MarathonBot):
    """MarathonBot whose target N uses a kinematic ERUV model with tunable parameters.

    Instead of floor(min_ERUV) - 1, estimates each opponent's rounds-to-win via
    the kinematic equation: N = (-v + sqrt(v² + 2·a_eff·deficit)) / a_eff,
    then targets min(opponent_N) - eruv_offset.

    Parameters
    ----------
    a : float
        Assumed opponent acceleration in coins/round².
        ~0.20 = fast-path opponent (ImpatientBot regime)
        ~0.45 = field median
        ~0.90 = engine-builder (ThoughtfulBot/CoverageBot regime)
    eruv_offset : int
        Rounds ahead of (positive) or behind (negative) the kinematic leader to target.
        Typical range: -1 (patient) … 4 (aggressive sprint).
    """

    def __init__(self, name: str, a: float = 0.45, eruv_offset: int = 1) -> None:
        super().__init__(name=name)
        self.a = a
        self.eruv_offset = eruv_offset

    def _target_n(self, players: list) -> int:
        """Kinematic override: estimate opponent finish times, aim eruv_offset ahead."""
        active = [p for p in players if not p.isWinner()]
        others = [p for p in active if p is not self]
        if not others:
            # No opponent context (e.g. chooseReroll call with [self]): fall back.
            return _leader_n(players)
        return _kinematic_n(others, players, self.a, self.eruv_offset)
