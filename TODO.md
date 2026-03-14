# TODO for harmonictook

## Feature Arcs

### Game Expansions
- Harbor expansion cards (official) — new card types, Harbor landmark, limited-market rule (N visible piles, refill on depletion). Touches `Game.refresh_market()`, `Store`, and every bot's `chooseCard`. Would benefit from the JSON card loader first.
- Millionaire's Row expansion (official)
- House rules variants (starting coins, limited supply)
- Custom card JSON loader — JSON for card data (name, cost, hitsOn, payout, color, category), Python for behavior hooks (Purple specials, factory multipliers). Blue/Green/Red stat cards are straightforward; Purple cards need code.

### Display & UX Polish
- `LogDisplay` — writes events to JSONL file in `show_events()`. ~20 lines; subclass `Display`, open a file handle, `json.dumps` each event. Could replace `RecordingDisplay` + `_write_game_record` post-hoc walk in tournament.py.
- Save/load game state — `GameState`/`PlayerSnapshot` dataclasses exist. Hard part: reconstructing Card objects from serialized data (Card constructors have quirky signatures). Needs a card registry or factory function.
- Replay/history buffer for last N turns
- `GuiDisplay` (Pygame) — Display protocol and event system are ready. `--mode gui` stub exists. Full GUI from scratch.

#### Requirements for Curses game display
 - Doesn't have to run natively - since text-only is native, we could skip curses and use rich or asciimatics
 - Frame buffer that is redrawn (no more scrolling text)
 - Top half of window: each player's name, coin total, and board are shown, with landmarks indicated
 - Active player is outlined in white, the others in light gray
 - Middle 2/6 of window: available cards are shown (in a way that lets us see, or infer, stack size)
 - Bottom 1/6 of window: choices for keyboard input
 - Dice show pips in the player's window; ideally the die or dice "tumble" between values before settling
 - Once dice roll, ideally we'd see (e.g.) "+3" linger brightly over each player's total then settle back to their total number, or "-3" over one player and "+3" over another at the same time - animations can be for later
 - Can curses correctly display emoji? If so, let's pick emoji and wrap them in ASCII line borders per card (so each card would be 3x3 or 3x4 chars).
 - Player display should indicate *at least* what rolls each card(s) trigger on; if there's room, payout too
 - Market display should visually indicate color and cards remaining, and textually indicate hits-on and pays-out values
 - For players who haven't bought them, the landmarks should be visible in the marketplace

### Meta-Game Features
- Statistics tracking (win rates, average game length, card value analysis)
- Export game logs for analysis (mostly solved by LogDisplay + tournament JSONL records)

## Bugfix

- Emoji don't correctly display in Windows terminals

## Tech Debt / Quality

### Completed Work (reference only)

The Game class refactor, Event system, Display protocol, and migration from `newGame()`/`nextTurn()` are all complete. See git history for details. Summary of completed items:

- ✅ Game class encapsulates all state (players, market, reserve, current_player_index, turn_number, last_roll, winner)
- ✅ Core methods: `__init__`, `next_turn()`, `refresh_market()`, `run()`, `get_current_player()`, `get_purchase_options()`, `get_player_state()`, `get_market_state()`
- ✅ Event system: all game logic emits `list[Event]`; Display is a consumer
- ✅ Display protocol: `show_events()` + `show_state()` on all 4 implementations (PlainTextDisplay, NullDisplay, ColorTUIDisplay, RecordingDisplay)
- ✅ Migration: `newGame()` → `Game.__init__()`, `nextTurn()` → `Game.next_turn()`, `main()` loop → `Game.run()`
- ✅ BusinessCenter fully event-driven (no `isinstance(Human)` branches in game logic)
- ✅ CoverageBot wired into `setPlayers()` and tournament field
- ✅ Store.append/remove properly raise TypeError on non-Card input
- ✅ [WON'T FIX] roll_dice/resolve_cards/buy_phase decomposition — YAGNI
- ✅ [WON'T FIX] check_winner() — win condition is pure Player state
- ✅ [WON'T FIX] Display.get_player_choice() — SRP violation; input belongs in Player hierarchy
- ✅ [WON'T FIX] Card triggers receive Game — unnecessary coupling; triggers need player list only

### Open Tech Debt

**Duplicate logic**
- **`_roll_income` (bots.py) duplicates `_own_turn_income` (strategy.py)** — both compute own-turn income for a given roll. bots.py version ignores opponent count for Stadium (uses `card.payout` as floor), strategy.py uses `payout * (len(players)-1)`. The bots.py copy exists because `chooseReroll` lacks a `players` list. Bug fixes to one won't propagate to the other. Fix: give reroll methods access to a players list, then delete bots.py copy.

**Scattered patterns**
- **Bot name generation** — `ImpatientBot.NAME_OPTIONS` and `FromageBot.NAME_OPTIONS` each define their own list + `name_options()` override + `__init__` with `random.choice`. Pattern will multiply with each new bot subclass. Not urgent; consider a class-level `NAME_OPTIONS` on `Bot` with a shared `__init__` pattern if more bot types are added.

**Dead weight**
- **`functionalTest()`** (harmonictook.py) — informal smoke test. `Game.run(display=NullDisplay())` in a real test replaces it. Keep or remove at discretion.

**Deferred / later**
- Extract Shopping Mall logic to payout modifier system (when card triggers restructured to receive Game).
- Performance benchmarks (after Event system stabilizes).
- **Optional file split**: Move Player/Human/Bot, Card hierarchy, Store hierarchy, Display, Game into separate modules — only if maintenance becomes painful. harmonictook.py is ~1250 lines, approaching but not yet at the pain threshold.
- **Optional trigger dispatch**: Replace hardcoded `[Red, Blue, Green, Stadium, TVStation, BusinessCenter]` with a `Card.color` and dispatch by color order. Would make Harbor expansion cards plug in without editing `next_turn()`.

### Testing Strategy

- Push for ~100% coverage after each major feature push
- Use TDD principles before feature pushes in order to put autopilot dev on guardrails
- CircleCI measures coverage on every push — check CI rather than running pytest locally
- Continue to run `ruff` to ensure our syntax is clear and Pythonic

#### Tests that add little value (consider removing or replacing)

- **testSingleTurnNoCrash** (test_game_flow): Only asserts `next_turn()` returns a list. Either remove or replace with an assertion that checks a concrete event type or state change.
- **testBotChooseCardMocked** (test_bots): Only checks that `random.choice` was called. Consider removing or replacing with a test that asserts the returned value is in the options list.
- **test_returns_bool** (test_tournament): Only checks `run_match()` return type. Consider removing.
- **testHistoryStartsEmpty** (test_game): Only checks `Game.history == []`. Consider removing or folding into a larger "initial state" test.
- **testUserChoiceFirstOption** / **testUserChoiceLastOption** (test_utility): Same code path as testUserChoiceValidFirst. Remove one or both to avoid redundancy.
