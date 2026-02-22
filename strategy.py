#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# strategy.py — EV-based card valuation library for harmonictook
# Pure functions only: no side effects, no I/O. Returns scores; callers decide how to act.

from __future__ import annotations
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


def delta_ev(card: Card, player: Player, players: list[Player], N: int = 1) -> float:
    """Return the marginal EV gain from adding card to player's deck.

    For UpgradeCards: temporarily sets the flag on player, diffs portfolio_ev, restores via finally.
    For factory-synergy cards: adds _factory_synergy_gain on top of direct ev.
    """
    if isinstance(card, UpgradeCard):
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


def score_purchase_options(player: Player, game: Game, N: int = 1) -> dict[Card, float]:
    """Return a {Card: delta_ev} dict for all cards the player can currently afford, sorted descending.

    Calls game.get_purchase_options() then resolves each name to a Card in game.market.deck.
    """
    options = game.get_purchase_options()
    if not options:
        return {}
    seen: set[str] = set()
    cards: list[Card] = []
    for c in game.market.deck:
        if c.name in options and c.name not in seen:
            seen.add(c.name)
            cards.append(c)
    scored = [(card, delta_ev(card, player, game.players, N)) for card in cards]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return dict(scored)
