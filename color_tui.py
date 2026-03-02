#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# color_tui.py — ColorTUIDisplay: full-screen Textual TUI for Harmonic Took.
#
# Requires: pip install textual
# See docs/color-tui-plan.md for the incremental implementation plan.

from __future__ import annotations

import asyncio
import threading

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.events import Key
from textual.widgets import RichLog, Static

from harmonictook import (
    Blue, Display, Event, Game, Green, Red, Stadium, TVStation, BusinessCenter,
)


# ── Widgets ───────────────────────────────────────────────────────────────────

class MarketPanel(Static):
    """Top strip listing available market cards and their quantities."""

    DEFAULT_CSS = """
    MarketPanel {
        height: auto;
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
        height: auto;
        border: solid $warning-darken-1;
        padding: 0 1;
    }
    """


# ── Placeholder data ──────────────────────────────────────────────────────────

_PLACEHOLDER_MARKET = (
    "Mkt:\n"
    "[blue]   1[/blue] Wheat Field            [blue]▓▓▓▓▓▓[/blue]    $1  │  "
    "[green]   4[/green] Convenience Store      [green]▓▓▓▓▓▓[/green]    $2  │  "
    "[green]   7[/green] Cheese Factory         [green]▓▓▓▓▓▓[/green]    $5 \n"
    "[blue]   2[/blue] Ranch                  [blue]▓▓▓▓▓▓[/blue]    $1  │  "
    "[blue]   5[/blue] Forest                 [blue]▓▓▓▓▓▓[/blue]    $3  │  "
    "[green]   8[/green] Furniture Factory      [green]▓▓▓▓▓▓[/green]    $3 \n"
    "[green] 2-3[/green] Bakery                 [green]▓▓▓▓▓▓[/green]    $1  │  "
    "[magenta]   6[/magenta] TV Station             [magenta]▓[/magenta]░░░░░ $7  │  "
    "[blue]   9[/blue] Mine                   [blue]▓▓▓▓▓▓[/blue]    $6 \n"
    "[red]   3[/red] Cafe                   [red]▓▓▓▓▓▓[/red]    $2  │  "
    "[magenta]   6[/magenta] Business Center        [magenta]▓[/magenta]░░░░░ $8  │  "
    "[red]9-10[/red] Family Restaurant      [red]▓▓▓▓▓▓[/red]    $3 \n"
    "[dim]   ★ Train Station          ░░░░░░ $4 [/dim] │  "
    "[magenta]   6[/magenta] Stadium                [magenta]▓[/magenta]░░░░░ $6  │  "
    "[blue]  10[/blue] Apple Orchard          [blue]▓▓▓▓▓▓[/blue]    $3 \n"
    "                                      │  "
    "                                      │  "
    "[green]11-12[/green] Farmer's Market         [green]▓▓▓▓▓▓[/green]    $2 "
)

_PLACEHOLDER_PLAYERS = [
    ("Alice", 12,
     " 1│[blue]█[/blue]\n 2│[blue]█[/blue] [green]██[/green]\n 3│[green]██[/green]\n"
     " 4│·\n 5│·\n 6│[magenta]█[/magenta]\n 7│·\n 8│·\n 9│·\n10│·\n11│·\n12│·",
     "● ○ ○ ○", True),
    ("Bob",    5,
     " 1│[blue]█[/blue]\n 2│[green]█[/green]\n 3│[green]█[/green]\n"
     " 4│·\n 5│·\n 6│·\n 7│·\n 8│·\n 9│·\n10│·\n11│·\n12│·",
     "○ ○ ○ ○", False),
    ("Carol",  0,
     " 1│[blue]█[/blue]\n 2│[green]█[/green]\n 3│[green]█[/green]\n"
     " 4│·\n 5│·\n 6│·\n 7│·\n 8│·\n 9│·\n10│·\n11│·\n12│·",
     "○ ○ ○ ○", False),
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
    return f"{marker} {name}\n  {coins} coins\n{cards}\n{landmarks}"


def _cards_markup(player: object) -> str:
    """12-row die-coverage grid: one row per face (1–12), colored by card type."""
    deck = player.deck.deck  # type: ignore[attr-defined]
    lines: list[str] = []
    for face in range(1, 13):
        cards_on_face = [c for c in deck if face in getattr(c, "hitsOn", [])]
        blues   = sum(1 for c in cards_on_face if isinstance(c, Blue))
        greens  = sum(1 for c in cards_on_face if isinstance(c, Green))
        reds    = sum(1 for c in cards_on_face if isinstance(c, Red))
        purples = sum(1 for c in cards_on_face if isinstance(c, (Stadium, TVStation, BusinessCenter)))
        parts: list[str] = []
        if blues:
            parts.append(f"[blue]{'█' * blues}[/blue]")
        if greens:
            parts.append(f"[green]{'█' * greens}[/green]")
        if reds:
            parts.append(f"[red]{'█' * reds}[/red]")
        if purples:
            parts.append(f"[magenta]{'█' * purples}[/magenta]")
        coverage = " ".join(parts) if parts else "·"
        lines.append(f"{face:2d}│{coverage}")
    return "\n".join(lines)


def _landmarks_markup(player: object) -> str:
    """Produce ● ○ symbols for each of the four landmark slots."""
    flags = [
        player.hasTrainStation,    # type: ignore[attr-defined]
        player.hasShoppingMall,    # type: ignore[attr-defined]
        player.hasAmusementPark,   # type: ignore[attr-defined]
        player.hasRadioTower,      # type: ignore[attr-defined]
    ]
    return " ".join("●" if f else "○" for f in flags)


def _market_markup(game: Game) -> str:
    """Three-column market: face │ name │ colored stack bar │ price.

    Cards sorted by die face, arranged column-major (read down each column).
    Cards the active player cannot afford are dimmed.
    ▓ = cards in stock (colored by type);  ░ = empty slot.

    Field widths are derived from the cards that land in each column, so the
    layout adapts automatically to variant rulesets with different card sets.
    Cell total: face_w + 1 + name_w + 1 + 6(bar) + 1 + 1($) + cost_w = 37.
    Three cells + two " │ " separators = 117 chars ≤ 118-char content area.
    """
    _CELL_WIDTH = 37

    market = game.get_market_state()
    player = game.get_current_player()

    card_lookup: dict[str, object] = {}
    for card in game.market.deck:  # type: ignore[attr-defined]
        if card.name not in card_lookup:
            card_lookup[card.name] = card

    sorted_names = sorted(
        market.keys(),
        key=lambda n: card_lookup[n].sortvalue() if n in card_lookup else 999.0,  # type: ignore[union-attr]
    )

    n_cols = 3
    n_rows = max(1, (len(sorted_names) + n_cols - 1) // n_cols)

    def _face_str(card: object) -> str:
        hits = sorted(card.hitsOn)  # type: ignore[attr-defined]
        if hits == [99]:
            return "★"
        if len(hits) == 1:
            return str(hits[0])
        return f"{hits[0]}-{hits[-1]}"

    # Measure each column's cards to derive tight field widths
    col_face_w: list[int] = []
    col_cost_w: list[int] = []
    for c in range(n_cols):
        col_cards = [
            card_lookup[n]
            for n in sorted_names[c * n_rows:(c + 1) * n_rows]
            if n in card_lookup
        ]
        col_face_w.append(max((len(_face_str(card)) for card in col_cards), default=1))
        col_cost_w.append(max((len(str(card.cost)) for card in col_cards), default=1))  # type: ignore[attr-defined]

    # name fills the remainder so every cell hits _CELL_WIDTH visible chars
    col_name_w = [_CELL_WIDTH - fw - cw - 10 for fw, cw in zip(col_face_w, col_cost_w)]

    cells: list[str] = []
    for i, name in enumerate(sorted_names):
        col = i // n_rows
        fw, nw, cw = col_face_w[col], col_name_w[col], col_cost_w[col]

        qty = market[name]
        card = card_lookup.get(name)
        if card is None:
            continue

        face_str = _face_str(card)
        cost = card.cost  # type: ignore[attr-defined]
        affordable = player.bank >= cost  # type: ignore[attr-defined]

        if isinstance(card, Blue):
            color = "blue"
        elif isinstance(card, Green):
            color = "green"
        elif isinstance(card, Red):
            color = "red"
        else:
            color = "magenta"

        name_str = f"{name[:nw]:<{nw}s}"

        if affordable:
            filled = f"[{color}]{'▓' * qty}[/{color}]" if qty > 0 else ""
            empty = "░" * (6 - qty)
            cells.append(
                f"[{color}]{face_str:>{fw}s}[/{color}] {name_str} {filled}{empty} ${cost:>{cw}d}"
            )
        else:
            cells.append(
                f"[dim]{face_str:>{fw}s} {name_str} {'░' * 6} ${cost:>{cw}d}[/dim]"
            )

    blank = " " * _CELL_WIDTH
    rows: list[str] = []
    for r in range(n_rows):
        row_cells = [
            cells[c * n_rows + r] if c * n_rows + r < len(cells) else blank
            for c in range(n_cols)
        ]
        rows.append(" │ ".join(row_cells))

    return "Mkt:\n" + "\n".join(rows)


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

    def __init__(self, game: Game | None = None,
                 display: ColorTUIDisplay | None = None) -> None:
        super().__init__()
        self.game = game
        self._game_display = display
        self._bridge_event = threading.Event()
        self._bridge_result: object = None
        self._bridge_mode: str | None = None   # "pick_one" | "confirm" | None
        self._bridge_options: list = []
        self._key_buffer: str = ""
        self._last_prompt: str = ""
        if display is not None:
            display.app = self

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
            if self._game_display is not None:
                threading.Thread(target=self._game_worker, daemon=True).start()
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
        self.query_one(MarketPanel).update(_market_markup(game))

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

    def _game_worker(self) -> None:
        """Run the game loop in a background thread.

        Exceptions are swallowed silently: the app may exit (e.g., test teardown)
        while a turn is in progress, causing call_from_thread() to re-raise a
        widget-not-found error.
        """
        try:
            self.game.run(display=self._game_display)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001
            pass

    def show_prompt(self, options: list, formatter: callable) -> None:
        """Update IOPanel with a numbered choice list and enter pick_one mode."""
        self._bridge_options = list(options)
        self._bridge_mode = "pick_one"
        self._key_buffer = ""
        self._last_prompt = "\n".join(
            f"[{i + 1}] {formatter(opt)}" for i, opt in enumerate(options)
        )
        self._refresh_io_panel()

    def show_confirm_prompt(self, prompt: str) -> None:
        """Update IOPanel with a yes/no prompt and enter confirm mode."""
        self._bridge_mode = "confirm"
        self.query_one(IOPanel).update(f"{prompt} [y/n]")

    def show_info_text(self, content: str) -> None:
        """Write informational content to the EventLog."""
        self.query_one(EventLog).write(content)

    def _refresh_io_panel(self) -> None:
        """Redraw the IOPanel with the current prompt and key-buffer cursor."""
        self.query_one(IOPanel).update(f"{self._last_prompt}\n> {self._key_buffer}_")

    def resolve_bridge(self, value: object) -> None:
        """Resolve the current blocking bridge request and clear the IOPanel."""
        self._bridge_mode = None
        self._bridge_options = []
        self._key_buffer = ""
        self.query_one(IOPanel).update("")
        self._bridge_result = value
        self._bridge_event.set()

    def on_key(self, event: Key) -> None:
        """Route keypresses to the active bridge request."""
        if self._bridge_mode == "confirm":
            if event.character in ("y", "Y"):
                event.stop()
                self.resolve_bridge(True)
            elif event.character in ("n", "N"):
                event.stop()
                self.resolve_bridge(False)
        elif self._bridge_mode == "pick_one":
            if event.key == "backspace":
                self._key_buffer = self._key_buffer[:-1]
                self._refresh_io_panel()
                event.stop()
            elif event.key == "enter":
                try:
                    idx = int(self._key_buffer) - 1
                except ValueError:
                    return
                if 0 <= idx < len(self._bridge_options):
                    event.stop()
                    self._key_buffer = ""
                    self.resolve_bridge(self._bridge_options[idx])
            elif event.character is not None and event.character.isdigit():
                # Cap buffer at the number of digits needed to express the
                # highest valid index (e.g. 9 options → 1 digit; 10 → 2 digits).
                max_digits = len(str(len(self._bridge_options)))
                if len(self._key_buffer) < max_digits:
                    self._key_buffer += event.character
                    self._refresh_io_panel()
                event.stop()


# ── ColorTUIDisplay ───────────────────────────────────────────────────────────

class ColorTUIDisplay(Display):
    """Full-screen TUI display powered by Textual.

    Wire up via HarmonicTookApp(game=..., display=...) so the app starts the game
    worker thread automatically. pick_one() and confirm() MUST be called from a
    background thread — calling them from the Textual event loop will deadlock.

    See docs/color-tui-plan.md for the build plan.
    """

    def __init__(self, app: HarmonicTookApp | None = None) -> None:
        self.app = app

    def _call_on_ui(self, fn: callable, /, *args: object) -> None:
        """Call fn(*args) thread-safely.

        If an asyncio event loop is running in the current thread (Textual event loop),
        call fn directly. Otherwise schedule via call_from_thread() (background thread).
        """
        try:
            asyncio.get_running_loop()
            fn(*args)
        except RuntimeError:
            self.app.call_from_thread(fn, *args)  # type: ignore[union-attr]

    def show_events(self, events: list[Event]) -> None:
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.show_events() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self._call_on_ui(self.app.add_events, events)

    def show_state(self, game: Game) -> None:
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.show_state() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self._call_on_ui(self.app.update_state, game)

    def pick_one(self, options: list, prompt: str = "Your selection: ",
                 formatter: callable = str) -> object:
        """Present a numbered menu and block until resolve_bridge() is called.

        Must be called from a background thread, not the Textual event loop.
        """
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.pick_one() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self.app._bridge_event.clear()
        self._call_on_ui(self.app.show_prompt, options, formatter)
        self.app._bridge_event.wait()
        return self.app._bridge_result

    def confirm(self, prompt: str) -> bool:
        """Ask a yes/no question and block until resolve_bridge() is called.

        Must be called from a background thread, not the Textual event loop.
        """
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.confirm() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self.app._bridge_event.clear()
        self._call_on_ui(self.app.show_confirm_prompt, prompt)
        self.app._bridge_event.wait()
        return bool(self.app._bridge_result)

    def show_info(self, content: str) -> None:
        if self.app is None:
            raise RuntimeError(
                "ColorTUIDisplay.show_info() requires an app — "
                "pass app=HarmonicTookApp() to the constructor"
            )
        self._call_on_ui(self.app.show_info_text, content)


if __name__ == "__main__":
    HarmonicTookApp(game=Game(players=2), display=ColorTUIDisplay()).run()
