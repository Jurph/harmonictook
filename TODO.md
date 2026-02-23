# TODO for harmonictook

## Feature Arcs

### Rich Bot Design
**Dynamic card-valuation framework to support flexible bot strategies**

Expected value calculations:
- Calculate the expected income from the current board state for the next N rounds (lets bots think "a little bit" ahead or "a lot" ahead)
- Calculate other players' expected income from same
- Calculate whether one or two dice yield better income against current board state
- Calculate expected income from a specific card for the next N rounds
- Estimate which player is "ahead" based on the expected income of their board for the next N rounds

**EV infrastructure — implementation ladder**

Each step answers a plain-English question a bot needs to ask. Each step depends on the one above it.

- ✅ **Probability tables + `p_hits(hitsOn, num_dice) -> float`** (`strategy.py`)
  *"How often do I expect a given card to hit?"*
  Module-level constants: `ONE_DIE_PROB`, `TWO_DIE_PROB`, `P_DOUBLES = 1/6`.
  Fundamental primitive — everything else is built on this.

- ✅ **`ev(card, owner, players, N) -> float` per card color** (`strategy.py`)
  *"What income should I expect this card to generate over the next N turns?"*
  Blue ✅, Green ✅ (factory multipliers + Shopping Mall), Red ✅ (bounded by opponent bank),
  Stadium ✅, Amusement Park turn multiplier ✅ (`× 1/(1 − P_DOUBLES)`).
  TVStation ✅, BusinessCenter ✅ (optimal swap: delta_ev gain side, spite-filtered give side).

- ✅ **`portfolio_ev(player, players, N) -> float`** (`strategy.py`)
  *"What total income do I expect from my whole board over the next N turns?"*
  Sum of `ev()` over the player's deck. Also the basis for estimating who is "ahead."

- ✅ **`delta_ev(card, player, players, N) -> float`** (`strategy.py`)
  *"How much better off am I if I add this card to my deck?"*
  Captures factory synergies and UpgradeCard portfolio-diff. `score_purchase_options()` wraps
  this into a ranked `{Card: float}` dict for direct use in `chooseCard()`.

- ✅ **BusinessCenter swap: argmax/argmin over `delta_ev()`** (`strategy.py`)
  *"Which card should I steal, and which should I give away?"*
  Per opponent: take the card with highest `delta_ev` to owner (factory synergies included);
  give away the least-harmful of owner's bottom-4 cards by EV — spite filter prevents handing
  the opponent a card that powers their engine. Give and take must be from the same opponent.

- ✅ **`chooseCard()` via argmax(delta_ev)** — EVBot in strategy.py uses score_purchase_options(); next_turn() passes game into chooseCard(options, self).

- **Wire EVBot into CLI (one pass)**
  - Add `--evbot` (or similar) to argparse in `main()`.
  - In `setPlayers()` or player setup from CLI args, when evbot requested, use `EVBot` instead of `Bot`/`ThoughtfulBot`.
  - Ensure `chooseCard(options, game)` receives `game` so EVBot can call `score_purchase_options()`.

Build a multi-dimensional card evaluation engine that scores cards across strategic dimensions:
- Coverage (number of die results that trigger the card)
- Passivity (value on other players' turns, scaled by player count)
- Expected Value (coins-per-turn with probability calculations)
- Synergy (multiplier effects with existing portfolio)
- Spite (hurting opponents / defensive value)
- Tempo (cost/payout ratio, break-even analysis)
- Monopoly Potential (cornering markets, blocking opponents)
- Landmark Progress (raw income toward win condition)

Strategy profiles can blend these dimensions with custom weights:
- ConservativeBot (high coverage + passivity)
- AggressiveBot (high spite + tempo)
- EconomistBot (pure expected value maximization)
- AdaptiveBot (shifts strategy based on game phase)

A bot's strategy is also a composition of its different behaviors: 
- How aggressively does it pursue landmarks? 
- 

### Graphical User Interface
**Native GUI using Pygame (or similar Python framework)**

MVP approach - simple assets that can be upgraded later:
- Blank card backgrounds with colored borders (blue/green/red/purple/orange)
- Text overlays for card name, cost, and die numbers
- Single emoji icon per card for visual identity
- Simple coin/landmark icons
- Basic dice graphics (or just numbers)

Core features:
- Click-to-select card purchasing
- Visual player boards showing coins and landmarks
- Card display with hover-for-details
- Turn indicator and game state display
- Bot move visualization (show what they bought/rolled)

Architecture:
- Keep existing game logic intact
- Add rendering layer on top (Display protocol already in place)
- Design for asset upgrades (easy to swap in better graphics later)

### Game Expansions
- Harbor expansion cards (official)
- Millionaire's Row expansion (official)
- Custom card JSON loader
- House rules variants (starting coins, limited supply)

### Display & UX Polish
- Add ANSI-style colored text (orange, red, green, blue, purple)
- Better game state visualization (board layout, player status)
- Save/load game state
- Replay/history buffer for last N turns
- "--fast" mode to suppress verbose output
- `LogDisplay` — writes events to file (for statistics and replay)

### Meta-Game Features
- Statistics tracking (win rates, average game length, card value analysis)
- Tournament mode (best of N games, ladder rankings)
- Bot vs bot simulations for strategy testing
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
   Game.get_player_state(player) -> dict       # Bank, deck, landmarks for display
   Game.get_market_state() -> dict             # Available cards with quantities
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
- **Game.get_player_state(player)**: Implement a method that returns a dict suitable for display, e.g. `{"name": player.name, "bank": player.bank, "landmarks": count, "cards": count}`. Used by GUI/LogDisplay.
- **Game.get_market_state()**: Implement a method that returns available cards with quantities (e.g. list of (name, count) or dict). Used by GUI/LogDisplay.
- **Display.show_state(game)**: Add `show_state(self, game: Game) -> None` to the Display ABC; implement no-op in NullDisplay and a simple print of player list + market in TerminalDisplay.

**Deferred / later**
- Extract Shopping Mall logic to payout modifier system (when card triggers restructured to receive Game).
- Performance benchmarks (after Event system stabilizes).
- **Optional file split**: Move Player/Human/Bot, Card hierarchy, Store hierarchy, Display, Game into separate modules (e.g. `players.py`, `cards.py`, `stores.py`, `display.py`, `game.py`) — only if maintenance becomes painful.
- **Optional trigger dispatch**: Replace hardcoded `[Red, Blue, Green, Stadium, TVStation, BusinessCenter]` with a `Card.color` (or similar) and dispatch by color order so new card types don’t require editing `next_turn()`.

### Testing Strategy

- Push for ~100% coverage after each major feature push
- Use TDD principles before feature pushes in order to put autopilot dev on guardrails
- CircleCI measures coverage on every push — check CI rather than running pytest locally
- Continue to run `ruff` to ensure our syntax is clear and Pythonic

#### Tests to add (one per bullet — each gives diagnostic value)
- **userChoice ValueError**: In test_utility, mock `input` to return `"abc"` then a valid number; assert no crash and that the valid choice is returned.
- **userChoice out-of-range**: Mock `input` to return `0` or `-1` then a valid number; assert the second choice is returned (and no crash).
- **Amusement Park bonus turn**: Integration test: one player has Amusement Park, roll doubles, assert they get a second turn (e.g. two "turn_start" or two roll events in one round).
- **testCardInteractions**: Replace hardcoded 103/101 with values derived from `starting_bank + sum(payouts)` so the test doesn’t silently break if starting bank changes.
- **BC swap purple (optional)**: Assert that a bot can swap a purple establishment (e.g. Stadium) via Business Center — documents that purples are swappable per rules.

#### Tests that add little value (consider removing or replacing)
- **testSingleTurnNoCrash** (test_game_flow): Only asserts `next_turn()` returns a list. Either remove or replace with an assertion that checks a concrete event type or state change.
- **testBotChooseCardMocked** (test_bots): Only checks that `random.choice` was called. Consider removing or replacing with a test that asserts the returned value is in the options list.
- **test_returns_bool** (test_tournament): Only checks `run_match()` return type. Consider removing.
- **testHistoryStartsEmpty** (test_game): Only checks `Game.history == []`. Consider removing or folding into a larger "initial state" test.
- **testUserChoiceFirstOption** / **testUserChoiceLastOption** (test_utility): Same code path as testUserChoiceValidFirst. Remove one or both to avoid redundancy.
