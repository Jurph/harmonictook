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

- ✅ **EVBot is playable** — available via `setPlayers()` interactive menu ("Tough Bot (EV-ranked strategy)") and in `tournament.py`. Bot type is chosen in-game; no CLI flags needed.

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
- Bot vs bot simulations for strategy testing
- Export game logs for analysis

### Tournament Mode

**Swiss Tournament with Elo Ratings**

Elo is a pairwise rating system. Multi-player Machi Koro games (2–4 players)
require decomposing a finish order into pairwise outcomes before updating ratings.
The core design challenge is defining "score" so that finish positions are
comparable and Elo updates are meaningful.

#### Step 1 — Finish Scoring (ordering non-winners)

A game ends when one player owns all four landmarks. The winner is clear; the
others need an ordering. Define a single integer **finish score** that rewards
converting coins into assets:

```
finish_score = (sum of owned landmark costs) × 3
             + (sum of owned establishment costs) × 2
             + bank coins
             + 25  ← "golden snitch" for the winner only
```

Landmark costs: Train Station=4, Shopping Mall=10, Amusement Park=16,
Radio Tower=22. The 3× multiplier rewards landmark investment over card
investment over hoarding; the 25-point golden snitch ensures the winner
always outranks a non-winner regardless of bank size.

Starting cards (Wheat Field cost=1, Bakery cost=1) are counted at 2× since
tracking "purchased vs given" would require new Player state; the rounding
error from two 1-coin cards is negligible.

`finish_score(player)` is implemented in `tournament.py`.

#### Step 2 — Pairwise Elo from Multi-Player Finish

Convert the N-player finish order into C(N, 2) pairwise outcomes, then apply
one standard Elo update per pair:

```
expected_i = 1 / (1 + 10^((r_j - r_i) / 400))
result_i   = 1 if finish_score_i > finish_score_j else 0
           = 0.5 if finish_score_i == finish_score_j  (exact tie only)
r_i_new    = r_i + K' * (result_i - expected_i)
```

To avoid over-updating ratings from N-1 simultaneous pairings, scale the
K-factor down: `K' = K / (N - 1)`. With K=32 and a 4-player table,
`K' ≈ 10.7` per pair. This keeps per-game rating movement comparable to a
2-player game regardless of table size.

Initial rating: **1500** (chess standard). K-factor: **32** (fixed, no decay).
Draws are exact ties only — losing by a single point is a loss.

#### Step 3 — Tournament Structure

All entrants play every round (no elimination). Pad the field to a multiple
of 12 with `Bot` instances labelled "RandomBot" so tables divide cleanly.

**Four rounds, played in order:**

| Round | Format        | Tables  | Seeding         | Opponents faced |
|-------|---------------|---------|-----------------|-----------------|
| 1     | Random pairs  | N/2     | None (shuffle)  | 1               |
| 2     | Seeded pairs  | N/2     | Elo adjacency   | 1               |
| 3     | Seeded triples| N/3     | Elo adjacency   | 2               |
| 4     | Seeded quads  | N/4     | Elo adjacency   | 3               |

Each player faces exactly **7 distinct opponents** across the tournament
(1 + 1 + 2 + 3). With 12 entrants, that is every other participant.

**Seeded pairing rule:** sort all players by current Elo descending, then
assign to tables in order (players 1–2, 3–4, etc. for pairs; 1–3, 4–6 for
triples; 1–4, 5–8 for quads). Within each table, **highest Elo sits last**
(latest turn order, slight handicap for the stronger player). Prefer pairings
that avoid repeating a round-1 opponent in round 2; skip if impossible.

**Padding:** `Bot` fills spots up to the next multiple of 12. Padding bots
receive Elo updates normally so they act as a calibrated floor. With 24+
entrants, run two "days" of 4 rounds each (8 rounds total, 15 opponents).

#### Data Structures

```python
@dataclass
class TournamentPlayer:
    player_factory: Callable[[str], Player]  # e.g. make_evbot(n=3)
    label: str                               # display name
    elo: float = 1500.0
    opponents_faced: list[str] = field(default_factory=list)

@dataclass
class RoundResult:
    table: list[str]        # player labels in finish order (1st → last)
    finish_scores: dict[str, int]   # label → finish_score
    elo_deltas: dict[str, float]    # label → Elo change this round
```

Note: `tournament_points` removed — Elo alone is the standing metric.

#### Reporting

After each round, print a standings table sorted by Elo descending:

```
  Rank  Player            Elo     Δ      Opponents faced
  ----  ----------------  ------  -----  ---------------
     1  EVBot(N=5)        1543.2  +14.1  RandomBot, EVBot(N=1)
     2  CoverageBot       1521.0   +6.3  ThoughtfulBot, RandomBot
     3  ThoughtfulBot     1488.4   -5.9  CoverageBot, EVBot(N=3)
     4  EVBot(N=1)        1447.4  -14.5  EVBot(N=5), RandomBot
```

Optionally: color gradient (cyan → green → yellow → red) for visual ranking.

#### Out of Scope (for now)
- Seeded brackets / single-elimination
- Human players in rated tournaments
- Persistence of Elo ratings across separate tournament runs

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

**Suspected dead code (verify then delete)**
- ✅ `main()` CLI flag `-t/--test` (`dest='unittests'`) — removed (was parsed but never read).
- ✅ Event type `"warn"` — removed from `EventType`, renderer branch, and unreachable else-branch in `refresh_market()` (nothing ever emitted it).
- ✅ `specials.remove(card)` in `Player.buy()` — removed (modified a local list from `checkRemainingUpgrades()` that went out of scope immediately; `bestowPower()` does the real work).

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
