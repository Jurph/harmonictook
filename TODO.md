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

- Emoji don't correctly display in Windows terminals

## Tech Debt / Quality

### Game Class Refactor
**Encapsulate all game state in a single Game object**

#### Design Principles
- Game logic produces **events**, not print output
- Game state lives in **one place**, not scattered across function parameters
- Display is a **consumer** of game state, not embedded in it
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
✅ Game.__init__(bots, humans)      # Set up players, decks, deal starting cards
✅ Game.next_turn() -> bool         # Execute one full turn (currently returns bool, not Events)
✅ Game.refresh_market()            # Sync unique cards with current player's holdings
✅ Game.run()                       # Full game loop with doubles/win detection
   Game.roll_dice() -> list[Event]  # Roll phase as discrete step (post-Event system)
   Game.resolve_cards() -> list[Event]  # Card triggers as discrete step (post-Event system)
   Game.buy_phase() -> list[Event]  # Buy phase as discrete step (post-Event system)
   Game.check_winner() -> bool      # Move win check from Player.isWinner() to Game
```

#### Game Class - Query Methods (partial)
```
✅ Game.get_current_player() -> Player
✅ Game.get_purchase_options() -> list[str]
   Game.get_player_state(player) -> dict       # Bank, deck, landmarks for display
   Game.get_market_state() -> dict             # Available cards with quantities
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
```
✅ 1. Create Game class with state only (no methods yet)
✅ 2. Move newGame() logic into Game.__init__()
✅ 3. Move nextTurn() logic into Game.next_turn(), keeping print statements temporarily
✅ 4. Move main() game loop into Game.run()
✅ 5. Update all tests to use Game() instead of newGame() tuple unpacking
✅ 6. Verified all 66 tests still pass
   7. Introduce Event system and Display protocol (separate PR)
   8. Replace print statements with events (separate PR)
```

#### What Changes
```
✅ newGame()                                      → Game.__init__()
✅ nextTurn(playerlist, player, avail, special)   → Game.next_turn()
   setPlayers()                                   → Game._setup_players()
   display()                                      → TerminalDisplay.show_deck()
   main() game loop                               → Game.run(display=TerminalDisplay())
   Card .trigger() methods receive players: list  → receive Game instead
```

#### Design-for-Test Requirements
```
✅ Game(players=2) sufficient to create a testable game
✅ Game state is queryable: game.players[0].bank etc.
✅ Deterministic mode: mock random.randint once, control entire game
   NullDisplay allows running full games silently in tests
   Events are inspectable: assert "a Cafe triggered for 2 coins"
   No input() calls in Game class (BusinessCenter.trigger() still calls input() directly)
```

### Code Quality

#### Completed ✅
- `get_die_roller(players)` helper — extracted from all Purple card trigger() methods
- Card trigger order fixed: Red → Blue → Green → Purple (was player-deck order)
- Game state encapsulated in Game class (absorbs newGame, nextTurn, main)
- Market refresh moved to `Game.refresh_market()`

#### Remaining

**Decouple output from game logic (Event system + Display protocol)**
- Print statements become Events; Display layer renders them
- TerminalDisplay preserves current behavior; NullDisplay enables silent testing
- Migration plan steps 7-8 above

**Extract Shopping Mall logic to payout modifier system**
- Current: hasShoppingMall checks hardcoded in Green and Red card classes
- Best time to fix: when card triggers are being restructured to return Events

**Add remaining type hints**
- Easier once the API surface is stable (Game, Event, Display interfaces)

**Better use of dict() structures for card lookups**
- Evaluate once card trigger logic is settled in its final home

**Performance benchmarks**
- Profile game loop, card triggers, bot decision-making
- Establish baseline after Event system stabilizes

### Testing Strategy

- ✅ Test restructuring complete: 66 tests across 6 files, all passing
- Push for 100% coverage after each major feature push
- Use TDD principles before feature pushes in order to put autopilot dev on guardrails
- CircleCI measures coverage on every push — check CI rather than running locally

Remaining testing work:

*High diagnostic value (do these first)*
1. ✅ **Convenience Store + Shopping Mall** — Green card modifier path. Existing Shopping Mall test uses Cafe (Red); add test for Green Convenience Store bonus.
2. ✅ **Business Center human swap** — Mock full input flow: swap yes/no, choose target, choose cards. Real game logic with branching.
3. ✅ **Store.append / Store.remove with non-Card** — Pass non-Card; verify behavior. Current code does `TypeError()` but doesn't raise it — confirmed bug, tests document behavior.
4. ✅ **Card comparison with non-Card** — Compare Card to non-Card (e.g. `card == "string"`); assert NotImplemented, no crash.
5. ✅ **utility.userChoice()** — Mock `input()`, verify selection and bounds. Core purchase menu; currently low coverage on utility.py.

*Medium diagnostic value (fill coverage gaps)*
6. ✅ **dieroll() edge case** — When `chooseDice()` returns something other than 1 or 2, returns `7, False`. One test that triggers this defensive path.
7. ✅ **Card base __init__** — Base Card() constructor. Subclasses override it; ensures base is constructible.
8. ✅ **get_die_roller() ValueError** — Call with no player having `isrollingdice`; assert ValueError.
9. ✅ **PlayerDeck.__str__ with UpgradeCards** — Deck string when it contains landmarks. Currently only Red/Green/Blue path exercised.
10. ✅ **Game.get_purchase_options()** — Assert it returns affordable card names for current player.
11. ✅ **Game.run()** — Full game loop, win detection, Amusement Park doubles. Needs mocked dice for deterministic run-to-win.
12. ✅ **main()** — Entry point. Low value; optional.
13. ✅ **Market refresh branch** — The truth-table edge case in Game.refresh_market(). One test that drives that condition.
14. ✅ **Add tests/test_game.py** — Dedicated suite for Game class (creation, next_turn, refresh_market, run with mocks).
