# TODO for harmonictook

## Feature Arcs

### Game Expansions
- House rules variants (starting coins, limited supply)
- Harbor expansion cards (official)
- Millionaire's Row expansion (official)
- Custom card JSON loader

### Display & UX Polish
- Add ANSI-style (or maybe Curses / Qud / DF style) colored text (orange, red, green, blue, purple)
- Better game state visualization (board layout, player status)
- Save/load game state
- Replay/history buffer for last N turns
- "--fast" mode to suppress verbose output
- `LogDisplay` — writes events to file (for statistics and replay)

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
- Export game logs for analysis

## Bugfix

- Emoji don't correctly display in Windows terminals

## Tech Debt / Quality

### Game Class Refactor
**Encapsulate all game state in a single Game object**

#### Design Principles
- Game logic produces **events**, not print output ✅
- Game state lives in **one place**, not scattered across function parameters ✅
- Display is a **consumer** of game state, not embedded in it ✅
- Bots read game state through the **same interface** as a GUI would

#### Game Class - Core State ✅
```
Game
  .players: list[Player]         # All players in turn order
  .market: TableDeck             # Cards available for purchase
  .reserve: UniqueDeck           # Purple/orange card reserve pool
  .current_player_index: int     # Whose turn it is
  .turn_number: int              # For phase detection (early/mid/late game)
  .last_roll: int                # Most recent die result
  .winner: Player | None         # Set when someone wins
```

#### Game Class - Core Methods (partial)
```
✅ Game.__init__(bots, humans)          # Set up players, decks, deal starting cards
✅ Game.next_turn(display) -> list[Event]  # Execute one full turn, emit events in real-time
✅ Game.refresh_market()                # Sync unique cards with current player's holdings
✅ Game.run(display)                    # Full game loop with doubles/win detection
   [WON'T FIX] Game.roll_dice() -> list[Event]      # emit() already provides per-event hooks; YAGNI
   [WON'T FIX] Game.resolve_cards() -> list[Event]  # same — no concrete consumer needs this split
   [WON'T FIX] Game.buy_phase() -> list[Event]      # same
   [WON'T FIX] Game.check_winner() -> bool          # win condition is pure Player state; Player.isWinner() is correct
```

#### Game Class - Query Methods (partial)
```
✅ Game.get_current_player() -> Player
✅ Game.get_purchase_options() -> list[str]
✅ Game.get_player_state(player) -> dict       # name, bank, landmarks, cards (used in history + display)
✅ Game.get_market_state() -> dict[str, int]   # card name -> quantity in market
```

#### Event System ✅
Game methods return Event objects instead of printing. Each event describes
what happened; the display layer decides how to show it.

```
Event(type="roll", player="Jurph", value=7)
Event(type="payout", card="Cafe", player="Bot1", value=2)
Event(type="buy", player="Jurph", card="Forest", value=3)
Event(type="pass", player="Bot1")
Event(type="win", player="Jurph")
```

#### Display Protocol ✅
Any display implements the same interface:

```
✅ Display.show_events(events: list[Event])    # Render a batch of events
   Display.show_state(game: Game)              # Render current game state
   [WON'T FIX] Display.get_player_choice(options) -> str   # SRP violation; input belongs in Player hierarchy
```

Concrete implementations:
- ✅ `TerminalDisplay` — prints to stdout (current behavior, preserved); emits in real-time
- ✅ `NullDisplay` — swallows all output (for testing and bot simulations)
- `GuiDisplay` — renders to Pygame window (future)
- `LogDisplay` — writes to file (for statistics and replay)

#### Migration Plan
```
✅ 1. Create Game class with state only (no methods yet)
✅ 2. Move newGame() logic into Game.__init__()
✅ 3. Move nextTurn() logic into Game.next_turn(), keeping print statements temporarily
✅ 4. Move main() game loop into Game.run()
✅ 5. Update all tests to use Game() instead of newGame() tuple unpacking
✅ 6. Verified all 66 tests still pass
✅ 7. Introduce Event system and Display protocol
✅ 8. Replace print statements with events; real-time emit to display
```

#### What Changes
```
✅ newGame()                                      → Game.__init__()
✅ nextTurn(playerlist, player, avail, special)   → Game.next_turn(display)
✅ main() game loop                               → Game.run(display=TerminalDisplay())
✅ print() calls in logic                         → Event objects via emit()
   setPlayers()                                   → Game._setup_players()
   [WON'T FIX] Card .trigger() methods receive players: list → receive Game — unnecessary coupling; triggers need the player list only
```

#### Design-for-Test Requirements
```
✅ Game(players=2) sufficient to create a testable game
✅ Game state is queryable: game.players[0].bank etc.
✅ Deterministic mode: mock random.randint once, control entire game
✅ NullDisplay allows running full games silently in tests
✅ Events are inspectable: assert type=="pass", type=="roll" and is_doubles, etc.
   No input() calls in Game class (Human.chooseTarget, BusinessCenter.trigger
   still call input() directly — deferred to Human I/O refactor)
```

### Code Quality

#### Open Bugs / Tech Debt

**Design / correctness**
- **BusinessCenter.trigger** still calls `input()`/`print()` directly for Human — not event-driven. Task: Implement `Human.chooseBusinessCenterSwap(target, my_swappable, their_swappable)` to do the prompts and return `(card_to_give, card_to_take)` or `None`; then in `BusinessCenter.trigger()` call `dieroller.chooseBusinessCenterSwap(...)` for every player type (remove the `isinstance(dieroller, Human)` branch that does input/print).

**Small, one-step tasks (do in any order)**
- **Display.show_state(game)**: Add `show_state(self, game: Game) -> None` to the Display ABC; implement no-op in NullDisplay and a simple print of player list + market in TerminalDisplay.

**Deferred / later**
- Extract Shopping Mall logic to payout modifier system (when card triggers restructured to receive Game).
- Performance benchmarks (after Event system stabilizes).
- **Optional file split**: Move Player/Human/Bot, Card hierarchy, Store hierarchy, Display, Game into separate modules (e.g. `players.py`, `cards.py`, `stores.py`, `display.py`, `game.py`) — only if maintenance becomes painful.
- **Optional trigger dispatch**: Replace hardcoded `[Red, Blue, Green, Stadium, TVStation, BusinessCenter]` with a `Card.color` (or similar) and dispatch by color order so new card types don’t require editing `next_turn()`.

**Dead Code** 
- TBD 

### Testing Strategy

- Push for ~100% coverage after each major feature push
- Use TDD principles before feature pushes in order to put autopilot dev on guardrails
- CircleCI measures coverage on every push — check CI rather than running pytest locally
- Continue to run `ruff` to ensure our syntax is clear and Pythonic

#### Tests to add (one per bullet — each gives diagnostic value)

- TBD 

#### Tests that add little value (consider removing or replacing)

- **testSingleTurnNoCrash** (test_game_flow): Only asserts `next_turn()` returns a list. Either remove or replace with an assertion that checks a concrete event type or state change.
- **testBotChooseCardMocked** (test_bots): Only checks that `random.choice` was called. Consider removing or replacing with a test that asserts the returned value is in the options list.
- **test_returns_bool** (test_tournament): Only checks `run_match()` return type. Consider removing.
- **testHistoryStartsEmpty** (test_game): Only checks `Game.history == []`. Consider removing or folding into a larger "initial state" test.
- **testUserChoiceFirstOption** / **testUserChoiceLastOption** (test_utility): Same code path as testUserChoiceValidFirst. Remove one or both to avoid redundancy.
