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
  TVStation and BusinessCenter: stubs in place, not yet implemented.

- ✅ **`portfolio_ev(player, players, N) -> float`** (`strategy.py`)
  *"What total income do I expect from my whole board over the next N turns?"*
  Sum of `ev()` over the player's deck. Also the basis for estimating who is "ahead."

- ✅ **`delta_ev(card, player, players, N) -> float`** (`strategy.py`)
  *"How much better off am I if I add this card to my deck?"*
  Captures factory synergies and UpgradeCard portfolio-diff. `score_purchase_options()` wraps
  this into a ranked `{Card: float}` dict for direct use in `chooseCard()`.

- **BusinessCenter swap: argmax/argmin over `ev()`**
  *"Which card should I steal, and which should I give away?"*
  Take the opponent card with the highest `ev()` for me; surrender the card in my hand with the lowest `ev()` for me.
  Net gain = `(gain_ev − loss_ev) × P(roll 6)`. Not a heuristic — the optimal swap falls directly out of the EV primitives.
  `_ev_businesscenter` stub in `strategy.py`; also need `_ev_tvstation`.

- **`chooseCard()` via argmax(`delta_ev`)**
  *"Which card is the best purchase for me right now?"*
  Replaces the static preference list in `Bot` and `ThoughtfulBot` with a principled ranking.
  `score_purchase_options()` already produces the ranked dict; wire it into a new `EVBot` subclass.

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
- **BusinessCenter.trigger** still calls `input()`/`print()` directly instead of events — not event-driven; invisible to non-terminal displays and harder to test

**Deferred / already noted**
- **Extract Shopping Mall logic to payout modifier system** — when card triggers restructured to receive Game
- **Better use of dict() for card lookups** — once trigger logic is settled
- **Performance benchmarks** — after Event system stabilizes

### Testing Strategy

- Push for ~100% coverage after each major feature push
- Use TDD principles before feature pushes in order to put autopilot dev on guardrails
- CircleCI measures coverage on every push — check CI rather than running pytest locally
- Continue to run `ruff` to ensure our syntax is clear and Pythonic

Current state: **155 tests**, ruff clean.
