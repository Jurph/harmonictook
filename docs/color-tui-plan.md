# ColorTUIDisplay — Implementation Plan

Full-screen Textual-based TUI for Harmonic Took.
Lives in `color_tui.py`; depends on `textual` (optional dep — core game requires only stdlib).

## Architecture

`ColorTUIDisplay(Display)` runs `Game.run()` in a **worker thread**.
The main thread belongs to Textual. They communicate via:
- `show_events()` / `show_state()` → `app.call_from_thread(app.post_message, ...)`
- `pick_one()` / `confirm()` → post prompt to UI, block on `threading.Event`, return when UI responds

The `Display` ABC is the integration seam. `Game` is untouched.

## Layout (target)

```
┌─────────────────────────── Market ─────────────────────────────┐
│  Wheat Field ×6  Ranch ×6  Bakery ×6  ...                      │
├──────────┬──────────┬──────────┬──────────────────────────────-─┤
│ ▶ Alice  │   Bob    │  Carol   │                                 │
│  12 coins│  5 coins │  0 coins │                                 │
│  [cards] │  [cards] │  [cards] │                                 │
│  ○○●○    │  ○○○○    │  ●○○○    │  (landmarks)                   │
├──────────┴──────────┴──────────┴────────────────────────────────┤
│ Event log: Alice rolled a 6. Ranch pays 1 to Alice.             │
│ > Buy a card  Pass  Show available cards                        │
└─────────────────────────────────────────────────────────────────┘
```

Active player panel is outlined in white; others in dim gray.
Minimum terminal size: 120×40. Layout divides player columns equally by N.

## Commit Checklist

### ✅ Commit 0 — Foundation
- `TerminalDisplay` → `PlainTextDisplay`; `Display.show_state()` added to ABC
- All existing displays implement `show_state()`; 7 contract tests added

### ✅ Commit 1 — Skeleton + dependency
- `textual` added to `requirements.txt`
- `color_tui.py`: `ColorTUIDisplay(Display)` with all ABC methods stubbed
- `tests/test_color_tui.py`: instantiation, subclass check, stub behavior, import safety

### Commit 2 — Static layout
- `MachiKoroApp(App)` in `color_tui.py` with hardcoded placeholder text
- `--tui` flag (or `python color_tui.py`) renders the layout visually
- No game logic; no Display protocol wiring yet

### Commit 3 — `show_state()` populates panels
- `show_state(game)` reads `game.get_player_state()` / `game.get_market_state()` and updates widgets
- Threading bridge not yet needed (push only, no return value)
- Tested via Textual's `App.run_test()` headless mode

### Commit 4 — `show_events()` feeds the event log
- Events render into the scrolling log panel
- Tested: feed known `Event` objects, assert text appears in log widget

### Commit 5 — Threading bridge (human input)
- `pick_one()`, `confirm()`, `show_info()` via `threading.Event` handshake
- Worker thread blocks; Textual UI resolves and unblocks
- Bot-only game can run end-to-end through `ColorTUIDisplay`
- Tested: mock Textual app response, verify bridge returns correctly and unblocks

### Commit 6 — Human play
- I/O panel responds to keypresses; resolves the threading bridge
- A human can play a full game in the TUI

## Future
- Emoji card icons (Textual handles Windows encoding)
- Dice animation (rapid redraws between values before settling)
- Coin delta flash ("+3" briefly over player total after payout)
- `LogDisplay` (separate) — writes events to file for statistics/replay
