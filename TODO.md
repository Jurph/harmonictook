# TODO for harmonictook

## Feature Arcs 

### Rich Bot Design
**Dynamic card-valuation framework to support flexible bot strategies**

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
- Add rendering layer on top
- Separate game state from display
- Design for asset upgrades (easy to swap in better graphics later)

### Game Expansions
- Harbor expansion cards (official)
- Millionaire's Row expansion (official)
- Custom card JSON loader
- House rules variants (starting coins, limited supply)

### Display & UX Polish
- Add descriptive text to cards in menus
- Complete Display() class implementation
- Add ANSI-style colored text (orange, red, green, blue, purple)
- Better game state visualization (board layout, player status)
- Save/load game state
- Replay/history buffer for last N turns
- "--fast" mode to suppress verbose output

### Meta-Game Features
- Statistics tracking (win rates, average game length, card value analysis)
- Tournament mode (best of N games, ladder rankings)
- Bot vs bot simulations for strategy testing
- Export game logs for analysis

## Bugfix

- **CRITICAL: Card trigger order violates Machi Koro rules**
  - Current: Cards trigger in player order (die-roller's cards first, then others)
  - Correct: Must trigger by color: Red (steal first) → Blue (pay all) → Green (pay die-roller) → Purple (die-roller only)
  - Impact: Red cards (cafes/restaurants) are significantly weaker than intended because die-roller gets paid before being stolen from
  - Fix requires: Sorting cards by color/payer before triggering, plus get_die_roller() helper function

- Emoji don't correctly display in Windows terminals

## Tech Debt / Quality

### Game Class Refactor
**Encapsulate all game state in a single Game object**

This is the keystone refactor. It enables GUI, Rich Bot, save/load, and clean testing.

#### Design Principles
- Game logic produces **events**, not print output
- Game state lives in **one place**, not scattered across function parameters
- Display is a **consumer** of game state, not embedded in it
- Bots read game state through the **same interface** as a GUI would

#### Game Class - Core State
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

#### Game Class - Core Methods
```
Game.__init__(bots, humans)      # Set up players, decks, deal starting cards
Game.next_turn() -> list[Event]  # Execute one full turn, return what happened
Game.roll_dice() -> list[Event]  # Roll phase (includes Radio Tower re-roll)
Game.resolve_cards() -> list[Event]  # Trigger cards in correct color order (Red → Blue → Green → Purple)
Game.buy_phase() -> list[Event]  # Player chooses to buy or pass
Game.refresh_market()            # Sync unique cards with current player's holdings
Game.check_winner() -> bool      # Check if current player has all landmarks
```

#### Game Class - Query Methods (for GUI and Bots)
```
Game.get_current_player() -> Player
Game.get_purchase_options() -> list[str]    # Cards affordable by current player
Game.get_player_state(player) -> dict       # Bank, deck, landmarks for display
Game.get_market_state() -> dict             # Available cards with quantities
Game.get_die_roller() -> Player             # Helper: who rolled this turn
```

#### Event System
Game methods return Event objects instead of printing. Each event describes
what happened; the display layer decides how to show it.

```
Event(type="roll", player="Jurph", value=7)
Event(type="trigger", card="Cafe", owner="Bot1", target="Jurph", amount=2)
Event(type="buy", player="Jurph", card="Forest", cost=3)
Event(type="pass", player="Bot1")
Event(type="win", player="Jurph")
```

#### Display Protocol
Any display (terminal, GUI, test harness) implements the same interface:

```
Display.show_events(events: list[Event])    # Render a batch of events
Display.show_state(game: Game)              # Render current game state
Display.get_player_choice(options) -> str   # Prompt for input (buy/pass/target)
```

Concrete implementations:
- `TerminalDisplay` — prints to stdout (current behavior, preserved)
- `GuiDisplay` — renders to Pygame window (future)
- `NullDisplay` — swallows all output (for testing and bot simulations)
- `LogDisplay` — writes to file (for statistics and replay)

#### Migration Plan
1. Create Game class with state only (no methods yet)
2. Move `newGame()` logic into `Game.__init__()`
3. Move `nextTurn()` logic into `Game.next_turn()`, keeping print statements temporarily
4. Move `main()` game loop into `Game.run()`
5. Update all tests to use `Game()` instead of `newGame()` tuple unpacking
6. Verify all 66 tests still pass after each step
7. **Then** introduce Event system and Display protocol (separate PR)
8. **Then** replace print statements with events (separate PR)

#### What Changes
- `newGame()` → `Game.__init__()`
- `nextTurn(playerlist, player, availableCards, specialCards)` → `Game.next_turn()`
- `setPlayers()` → `Game._setup_players()`
- `display()` → `TerminalDisplay.show_deck()`
- `main()` game loop → `Game.run(display=TerminalDisplay())`
- Card `.trigger()` methods receive `Game` instead of `players: list`

#### What Stays the Same
- Player class hierarchy (Player, Human, Bot, ThoughtfulBot)
- Card class hierarchy (Card, Blue, Green, Red, Purple subtypes)
- Store/Deck classes (Store, PlayerDeck, TableDeck, UniqueDeck)
- All card trigger logic (just restructured to return events)

#### Design-for-Test Requirements
- `Game(bots=2)` must be sufficient to create a testable game (no interactive setup)
- `NullDisplay` allows running full games silently in tests
- Events are inspectable: test can assert "a Cafe triggered for 2 coins"
- Game state is queryable: test can check `game.players[0].bank` at any point
- Deterministic mode: mock `random.randint` once, control entire game
- No `input()` calls in Game class — all player interaction goes through Display

### Code Quality — Sequenced Around Game() Refactor

#### Blockers (do these BEFORE Game() refactor)

**get_die_roller() helper function**
- Current: Repeated loop pattern in every Purple card trigger()
- Target: `get_die_roller(players)` utility function
- Why first: Cleaning this up now means less mess to move into Game(). Also needed for the trigger-order bugfix.

**Fix card trigger order (see Bugfix section)**
- Why first: The Game.resolve_cards() method should be built correctly from day one. Fix the ordering logic in the current codebase, then migrate the corrected version into Game().

#### Include in Game() Refactor (do these AS PART OF the refactor)

**Encapsulate game state in Game class**
- Absorbs `newGame()`, `nextTurn()`, `setPlayers()`, `main()` game loop
- See Game Class Refactor section above for full plan

**Decouple output from game logic (Event system + Display protocol)**
- Print statements become Events; Display layer renders them
- TerminalDisplay preserves current behavior; NullDisplay enables silent testing
- Migration plan steps 7-8 in Game Class Refactor section

**Simplify market refresh logic**
- Current: Four-way truth table with nested conditionals in nextTurn()
- Becomes `Game.refresh_market()` — rewrite it cleanly as part of the move

**Extract Shopping Mall logic to payout modifier system**
- Current: hasShoppingMall checks hardcoded in Green and Red card classes
- Best time to fix: when card triggers are being restructured to return Events

#### Future (easier AFTER Game() is done)

**Complete Display class implementations**
- TerminalDisplay ships with Game() refactor
- GuiDisplay, LogDisplay built on top of the Display protocol afterward

**Add remaining type hints**
- Easier once the API surface is stable (Game, Event, Display interfaces)

**Better use of dict() structures for card lookups**
- Evaluate once card trigger logic is settled in its final home

**Performance benchmarks**
- Profile game loop, card triggers, bot decision-making
- Establish baseline after Game() refactor stabilizes

#### Testing Strategy — Status
**✅ Test restructuring: DONE** (66 tests across 6 files, all passing)

Remaining testing work:
- Add `tests/test_game.py` for the new Game class (part of Game() refactor)
- Add coverage reporting to CircleCI pipeline (Codecov integration in progress)
- Coverage target: ~100% using `coverage.py`
