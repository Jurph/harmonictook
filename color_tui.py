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

from harmonictook import Display, Event, Game


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


def _player_markup(name: str, coins: int, cards: str, landmarks: str, active: bool) -> str:
    marker = "▶" if active else " "
    return f"{marker} {name}\n  {coins} coins\n\n  {cards}\n\n  {landmarks}"


# ── App ───────────────────────────────────────────────────────────────────────

class MachiKoroApp(App):
    """Full-screen Machi Koro TUI. Placeholder data until Commit 3 wires game state."""

    TITLE = "Harmonic Took"
    BINDINGS = [("q", "quit", "Quit")]
    CSS = """
    #player-area { height: 1fr; }
    """

    def compose(self) -> ComposeResult:
        yield MarketPanel(_PLACEHOLDER_MARKET, id="market")
        with Horizontal(id="player-area"):
            for name, coins, cards, landmarks, active in _PLACEHOLDER_PLAYERS:
                classes = "active" if active else "inactive"
                yield PlayerPanel(
                    _player_markup(name, coins, cards, landmarks, active),
                    classes=classes,
                )
        yield EventLog(id="event-log")
        yield IOPanel(_PLACEHOLDER_IO, id="io-panel")

    def on_mount(self) -> None:
        log = self.query_one(EventLog)
        for line in _PLACEHOLDER_EVENTS:
            log.write(line)


# ── ColorTUIDisplay ───────────────────────────────────────────────────────────

class ColorTUIDisplay(Display):
    """Full-screen TUI display powered by Textual.

    Not yet implemented — stub satisfies the Display ABC so the class
    can be imported and instantiated. Each method will raise
    NotImplementedError until the corresponding commit lands.

    See docs/color-tui-plan.md for the build plan.
    """

    def show_events(self, events: list[Event]) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_events() not yet implemented")

    def show_state(self, game: Game) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_state() not yet implemented")

    def pick_one(self, options: list, prompt: str = "Your selection: ",
                 formatter: callable = str) -> object:
        raise NotImplementedError("ColorTUIDisplay.pick_one() not yet implemented")

    def confirm(self, prompt: str) -> bool:
        raise NotImplementedError("ColorTUIDisplay.confirm() not yet implemented")

    def show_info(self, content: str) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_info() not yet implemented")


if __name__ == "__main__":
    MachiKoroApp().run()
