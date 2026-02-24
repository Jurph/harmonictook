#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# bots.py — Strategy-informed bot subclasses for harmonictook
#
# All classes here subclass Bot (defined in harmonictook.py) and depend on
# EV/coverage functions from strategy.py. Basic Bot stays in harmonictook.py
# because it has no external dependencies; every subclass that diverges from
# Bot's random defaults lives here instead.

from __future__ import annotations

import random

from harmonictook import Bot, Card, UpgradeCard, Game
from strategy import (
    delta_coverage,
    delta_ev,
    score_purchase_options,
    _own_turn_coverage,
)


class ThoughtfulBot(Bot):
    """Priority-driven bot that follows a fixed card-preference ordering."""

    def chooseCard(self, options: list, game: Game | None = None) -> str | None:
        """Return the highest-priority card name available in options per the bot's preference list."""
        if not options:
            return None
        names = [o.name if isinstance(o, Card) else o for o in options]
        upgrades = ["Radio Tower",
        "Amusement Park",
        "Shopping Mall",
        "Train Station"]
        earlycards = ["TV Station",
        "Business Center",
        "Stadium",
        "Forest",
        "Convenience Store",
        "Ranch",
        "Wheat Field",
        "Cafe",
        "Bakery"]
        latecards = ["Mine",
        "Furniture Factory",
        "Cheese Factory",
        "Family Restaurant",
        "Apple Orchard",
        "Fruit & Vegetable Market"]
        if self.hasTrainStation:
            preferences = upgrades + latecards + earlycards
        else:
            preferences = upgrades + earlycards
        for priority in preferences:
            if priority in names:
                return priority
        return random.choice(names)

    def chooseDice(self, players: list | None = None) -> int:
        """Return 1 without Train Station; with it, randomly favour 2 dice (4:1 odds)."""
        if not self.hasTrainStation:
            return 1
        return random.choice([1, 2, 2, 2, 2])


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

    def chooseCard(self, options: list, game: Game | None = None) -> str | None:
        """Return the name of the highest delta_ev card available in options.

        options may be a list of Card objects (scored directly without a game) or
        string names (resolved from game.market if game is provided; random fallback
        otherwise). players defaults to [self] when no game is supplied.
        """
        if not options:
            return None
        # Card objects: score directly, no game required.
        card_objects = [o for o in options if isinstance(o, Card)]
        if card_objects:
            use_players = list(game.players) if game else [self]
            scored = score_purchase_options(self, card_objects, use_players, N=self.n_horizon)
            if scored:
                return next(iter(scored)).name
            return random.choice(card_objects).name
        # String names: resolve to Card objects via market for scoring.
        if game is not None:
            option_set = set(options)
            market_cards = [c for c in game.market.deck if c.name in option_set]
            if market_cards:
                scored = score_purchase_options(self, market_cards, game.players, N=self.n_horizon)
                for card in scored:
                    if card.name in options:
                        return card.name
        return random.choice(options)


class CoverageBot(Bot):
    """Bot that builds toward complete die-value coverage and rolls whichever dice count
    best covers its current deck.

    chooseCard always buys a landmark when one is available, ranking landmarks by
    (delta_coverage, delta_ev). When no landmark is in options, the same key ranks
    establishments by new-slot coverage then income. chooseDice compares
    _own_turn_coverage for 1 vs 2 dice and picks the stronger side.
    """

    def chooseCard(self, options: list, game: Game | None = None) -> str | None:
        """Always buy a landmark when one is available; otherwise buy the highest-coverage card.

        options may be Card objects (scored directly) or string names (resolved from
        game.market when game is supplied; random fallback otherwise).
        """
        if not options:
            return None

        def _score(c: Card, players: list, all_cards: list) -> tuple:
            return (delta_coverage(c, self, players), delta_ev(c, self, players, market_cards=all_cards))

        # Card objects: landmark-first, then highest (coverage, ev).
        card_objects = [o for o in options if isinstance(o, Card)]
        if card_objects:
            use_players = list(game.players) if game else [self]
            landmarks = [c for c in card_objects if isinstance(c, UpgradeCard)]
            pool = landmarks if landmarks else card_objects
            return max(pool, key=lambda c: _score(c, use_players, card_objects)).name

        # String names: resolve to Card objects via market.
        if game is not None:
            option_set = set(options)
            market_cards = [c for c in game.market.deck if c.name in option_set]
            if market_cards:
                landmarks = [c for c in market_cards if isinstance(c, UpgradeCard)]
                pool = landmarks if landmarks else market_cards
                return max(pool, key=lambda c: _score(c, game.players, market_cards)).name

        return random.choice(options)

    def chooseDice(self, players: list | None = None) -> int:
        """Roll 2 dice if they cover more of the deck's hitsOn range than 1 die; else roll 1."""
        if not self.hasTrainStation:
            return 1
        return 2 if _own_turn_coverage(self, 2) > _own_turn_coverage(self, 1) else 1
