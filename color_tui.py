#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# color_tui.py — ColorTUIDisplay: full-screen Textual TUI for Harmonic Took.
#
# Requires: pip install textual
# See docs/color-tui-plan.md for the incremental implementation plan.

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import RichLog, Static

from harmonictook import (
    Blue, Display, Event, Game, Green, Red, Stadium, TVStation, BusinessCenter,
)


# ── Widgets ───────────────────────────────────────────────────────────────────

class MarketPanel(Static):
    """Top strip listing available market cards and their quantities."""

    DEFAULT_CSS = """
    MarketPanel {
        height: 3;
        border: solid $success-darken-1;
        padding: 0 1;
    }
    """


class PlayerPanel(Static):
    """One player's board: name, coins, card stacks, landmark row."""

    DEFAULT_CSS = """
    PlayerPanel {
        width: 1fr;
        border: solid grey;
        padding: 1 1;
    }
    PlayerPanel.active {
        border: solid white;
    }
    """


class EventLog(RichLog):
    """Scrolling log of game events."""

    DEFAULT_CSS = """
    EventLog {
        height: 6;
        border: solid $primary-darken-1;
        padding: 0 1;
    }
    """


class IOPanel(Static):
    """Current player's available actions or prompt."""

    DEFAULT_CSS = """
    IOPanel {
        height: 3;
        border: solid $warning-darken-1;
        padding: 0 1;
    }
    """


# ── Placeholder data ──────────────────────────────────────────────────────────

_PLACEHOLDER_MARKET = (
    "Market:  Wheat Field ×6   Ranch ×6   Bakery ×6   "
    "Cafe ×6   Convenience Store ×6   ..."
)

_PLACEHOLDER_PLAYERS = [
    ("Alice", 12, "[green]■■■[/green] [cyan]■■[/cyan]", "● ○ ○ ○", True),
    ("Bob",    5, "[green]■■[/green]",                   "○ ○ ○ ○", False),
    ("Carol",  0, "[green]■[/green]",                    "○ ○ ○ ○", False),
]

_PLACEHOLDER_EVENTS = [
    "Alice rolled a 6.",
    "Ranch pays 1 coin to Alice.",
    "Alice bought a Bakery for 1 coin, and now has 11 coins.",
]

_PLACEHOLDER_IO = "[1] Buy a card   [2] Pass   [3] Show available cards"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _player_markup(name: str, coins: int, cards: str, landmarks: str, active: bool) -> str:
    marker = "▶" if active else " "
    return f"{marker} {name}\n  {coins} coins\n\n  {cards}\n\n  {landmarks}"


def _cards_markup(player: object) -> str:
    """Produce colored ■ squares summarising a player's establishment deck."""
    deck = player.deck.deck  # type: ignore[attr-defined]
    blues   = sum(1 for c in deck if isinstance(c, Blue))
    greens  = sum(1 for c in deck if isinstance(c, Green))
    reds    = sum(1 for c in deck if isinstance(c, Red))
    purples = sum(1 for c in deck if isinstance(c, (Stadium, TVStation, BusinessCenter)))
    parts: list[str] = []
    if blues:   parts.append(f"[blue]{'■' * blues}[/blue]")
    if greens:  parts.append(f"[green]{'■' * greens}[/green]")
    if reds:    parts.append(f"[red]{'■' * reds}[/red]")
    if purples: parts.append(f"[magenta]{'■' * purples}[/magenta]")
    return " ".join(parts) or "—"


def _landmarks_markup(player: object) -> str:
    """Produce ● ○ symbols for each of the four landmark slots."""
    flags = [
        player.hasTrainStation,    # type: ignore[attr-defined]
        player.hasShoppingMall,    # type: ignore[attr-defined]
        player.hasAmusementPark,   # type: ignore[attr-defined]
        player.hasRadioTower,      # type: ignore[attr-defined]
    ]
    return " ".join("●" if f else "○" for f in flags)


def _event_to_str(event: Event) -> str | None:  # noqa: C901
    """Convert a game Event to a log string, or None if the event is silent in the TUI."""
    t = event.type
    if t == "turn_start":
        return f"--- {event.player}'s turn ---"
    if t == "roll":
        return f"{event.player} rolled a {event.value}."
    if t == "reroll":
        return f"{event.player} uses the Radio Tower to re-roll!"
    if t == "card_activates":
        return f"{event.player}'s {event.card} activates on a {event.value}..."
    if t == "payout":
        return f"{event.card} pays out {event.value} to {event.player}."
    if t == "payout_skip":
        return f"{event.player} didn't roll the dice — no payout from {event.card}."
    if t == "factory_count":
        return f"{event.player} has {event.value} cards of type {event.card_type}..."
    if t == "steal":
        return f"{event.player} collected {event.value} coins from {event.target}."
    if t == "steal_activate":
        return f"{event.player} activates TV Station!"
    if t == "steal_target":
        return f"{event.player} targets {event.target}!"
    if t == "steal_no_target":
        return "No valid targets for TV Station."
    if t == "steal_skip":
        return "TV Station doesn't activate (not die roller's turn)."
    if t == "collect":
        return None  # Stadium collects are silent
    if t == "bc_activate":
        return f"{event.player} activates Business Center!"
    if t == "bc_bot_payout":
        return f"{event.player} gets {event.value} coins (no swap)."
    if t == "bc_swap":
        return f"Swapped {event.card} for {event.target}'s {event.message}."
    if t == "bc_no_cards":
        return "Not enough swappable cards."
    if t == "bc_no_target":
        return "No valid swap target."
    if t == "bc_skip":
        return "Business Center doesn't activate (not die roller's turn)."
    if t == "bank_status":
        return f"{event.player} now has {event.value} coins."
    if t == "deck_state":
        return None  # panel shows deck state visually; no log entry needed
    if t == "buy":
        return (f"{event.player} bought {event.card} for {event.value} coins, "
                f"and now has {event.remaining_bank} coins.")
    if t == "buy_failed":
        return (f"Sorry: {event.card} costs {event.value} "
                f"and {event.player} only has {event.remaining_bank}.")
    if t == "buy_not_found":
        return f"Sorry: we don't have anything called '{event.card}'."
    if t == "pass":
        return f"{event.player} passes this turn."
    if t == "win":
        return f"{event.player} wins!"
    if t == "doubles_bonus":
        return f"{event.player} rolled doubles and gets to go again!"
    return None  # unknown event type — fail silently


# ── App ───────────────────────────────────────────────────────────────────────

class HarmonicTookApp(App):
    """Full-screen Harmonic Took TUI."""

    TITLE = "Harmonic Took"
    BINDINGS = [("q", "quit", "Quit")]
    CSS = """
    #player-area { height: 1fr; }
    """

    def __init__(self, game: Game | None = None) -> None:
        super().__init__()
        self.game = game

    def compose(self) -> ComposeResult:
        yield MarketPanel(_PLACEHOLDER_MARKET if self.game is None else "", id="market")
        with Horizontal(id="player-area"):
            if self.game is None:
                for name, coins, cards, landmarks, active in _PLACEHOLDER_PLAYERS:
                    yield PlayerPanel(
                        _player_markup(name, coins, cards, landmarks, active),
                        classes="active" if active else "inactive",
                    )
            else:
                active_player = self.game.get_current_player()
                for player in self.game.players:
                    yield PlayerPanel(
                        "",
                        classes="active" if player is active_player else "inactive",
                    )
        yield EventLog(id="event-log")
        yield IOPanel(_PLACEHOLDER_IO if self.game is None else "", id="io-panel")

    def on_mount(self) -> None:
        if self.game is not None:
            self.update_state(self.game)
        else:
            log = self.query_one(EventLog)
            for line in _PLACEHOLDER_EVENTS:
                log.write(line)

    def add_events(self, events: list[Event]) -> None:
        """Write renderable events to the EventLog; silent events are dropped."""
        log = self.query_one(EventLog)
        for event in events:
            text = _event_to_str(event)
            if text is not None:
                log.write(text)

    def update_state(self, game: Game) -> None:
        """Repopulate all panels from current game state. Safe to call from any thread."""
        market = game.get_market_state()
        market_text = "Market:  " + "   ".join(
            f"{name} ×{qty}" for name, qty in sorted(market.items())
        )
        self.query_one(MarketPanel).update(market_text)

        active_player = game.get_current_player()
        for panel, player in zip(self.query(PlayerPanel), game.players):
            is_active = player is active_player
            state = game.get_player_state(player)
            panel.update(_player_markup(
                state["name"], state["bank"],
                _cards_markup(player),
                _landmarks_markup(player),
                active=is_active,
            ))
            panel.set_class(is_active, "active")
            panel.set_class(not is_active, "inactive")


# ── ColorTUIDisplay ───────────────────────────────────────────────────────────

class ColorTUIDisplay(Display):
    """Full-screen TUI display powered by Textual.

    Construct with an app instance to enable show_state(); other methods
    will raise NotImplementedError until subsequent commits land.

    See docs/color-tui-plan.md for the build plan.
    """

    def __init__(self, app: HarmonicTookApp | None = None) -> None:
        self.app = app

    def show_events(self, events: list[Event]) -> None:
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.show_events() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self.app.add_events(events)

    def show_state(self, game: Game) -> None:
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.show_state() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self.app.update_state(game)

    def pick_one(self, options: list, prompt: str = "Your selection: ",
                 formatter: callable = str) -> object:
        raise NotImplementedError("ColorTUIDisplay.pick_one() not yet implemented")

    def confirm(self, prompt: str) -> bool:
        raise NotImplementedError("ColorTUIDisplay.confirm() not yet implemented")

    def show_info(self, content: str) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_info() not yet implemented")


if __name__ == "__main__":
    HarmonicTookApp().run()
