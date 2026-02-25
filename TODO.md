# TODO for harmonictook

## Feature Arcs

### More metrics for bots to use 

We've been computing "expected value" and "coverage" piecemeal, but we need a primitive we can build all future strategy primitives from. Enter the **probability mass function** (PMF) which paves the way for **expected rounds until victory** and even **likelihood of victory**, as we roll in things like variance! 

#### PMF Basics

The **probability mass function** (PMF) is the true primitive. It is a `dict[int, float]`
mapping integer income amounts to probabilities. All existing summary statistics — EV,
coverage, variance — are derived quantities. Building the PMF explicitly makes them
exact and consistent, and enables new metrics like TUV that the old approach cannot
express cleanly.

**Key building blocks** (all live in `strategy.py`; all accept a `Game` or `players`
parameter; none cache; stub implementations return `NotImplemented`):

```
_die_pmf(n_dice) -> dict[int, float]
    Return the PMF for rolling n_dice d6s and summing.
    n_dice=1 → 6 outcomes equally weighted.
    n_dice=2 → 11 outcomes, triangular distribution.

_convolve(a, b) -> dict[int, float]
    Combine two independent PMFs by summing their outcomes.
    result[x+y] += a[x] * b[y] for all (x, y) pairs.
    Used to stack per-round PMFs across multiple opponents.

own_turn_pmf(player, players) -> dict[int, float]
    Income distribution for `player`'s own turn.
    Fires: Blue cards, Green cards, Purple cards (Stadium, TVStation, BC).
    Applies: Radio Tower reroll rule, Amusement Park bonus-turn approximation.
    Train Station: assumes player rolls 2 dice if they own Train Station.

opponent_turn_pmf(observer, roller, players) -> dict[int, float]
    Income distribution for `observer` when `roller` takes their turn.
    Fires: observer's Blue cards (all rolls) + observer's Red cards (roller's turn only).
    Does NOT fire: Green, Purple, or Radio Tower belonging to the roller.
    Radio Tower belonging to observer is ignored (roller's choice, not observer's).

round_pmf(player, players) -> dict[int, float]
    Net income for `player` over one full round (their own turn + all opponents' turns).
    = _convolve(own_turn_pmf(player), opponent_turn_pmf(player, opp1),
                opponent_turn_pmf(player, opp2), ...)
    Result income values may be negative (Red card theft).

pmf_mean(pmf) -> float
    Weighted average income. Equivalent to existing portfolio_ev() once PMF is correct.

pmf_variance(pmf) -> float
    E[X^2] - E[X]^2. Useful for measuring consistency of income.

pmf_percentile(pmf, p) -> float
    Find the smallest income x such that P(income <= x) >= p.
    p=0.5 is the median. Bots in losing positions can target higher p (need lucky outcome).
```

**Design simplifications (explicit decisions):**

1. **Radio Tower**: Player rerolls iff their first roll yields 0 income (not 0 on the die —
   0 *income* from their portfolio). This is applied inside `own_turn_pmf`. Probability
   math: `P(income=0 with RT) = P(zero_income)²`; `P(income=x>0 with RT) = P(roll=x) +
   P(zero_income) * P(reroll=x)`. Build `pmf_percentile` (not just `pmf_median`) so bots
   can choose their risk threshold.

2. **Amusement Park**: Doubles (matching dice: 2-2, 3-3, etc.) give the player a bonus
   turn. Simplification: value the bonus turn as `pmf_mean(own_turn_pmf(...))` — i.e.,
   average EV of an extra own turn. This underestimates slightly (no recursion on further
   doubles) but avoids infinite recursion and is tractable. Exact formula via geometric
   series would multiply EV by 6/5 (doubles prob 1/6 → mean extra turns = 1/5), but the
   PMF approach approximates this per-outcome.

3. **Dice choice**: Any player who owns Train Station is assumed to roll 2 dice. No
   theory of mind about whether 2 dice is actually optimal. This is revisited if/when
   a smarter dice-selection model is warranted.

**Migration path**: Existing `p_hits`, `ev`, `portfolio_ev`, `coverage_value` stay as-is
for now. PMF functions are additive — they do not replace or modify any existing function.
Once the PMF implementation is verified to produce matching summary statistics, the
existing functions can be reimplemented as thin wrappers (optional cleanup pass).

#### ERUV, TUV, delta-TUV...

**Turns Until Victory (TUV)** answers "how many more rounds does this player need, at
current income rate, to win?" It replaces vague notions of "closeness" with a concrete
round count that bots can compare across players.

**Closed-form estimate:**

```
TUV(player) = max(
    n_landmarks_remaining,                              # landmark-count floor
    ceil((total_remaining_landmark_cost - bank) / ev)  # income-deficit ceiling
)
```

The two terms represent independent binding constraints. A player who has enough coins
but needs 3 more landmarks still needs 3 rounds minimum. A player who has no coins but
could win in one more buy still needs to earn the money first.

**Why landmarks affect the denominator, not just the ceiling**: Train Station, Shopping
Mall, Amusement Park, and Radio Tower all change the player's income distribution. They
don't just reduce `n_landmarks_remaining` by 1 — they shift `ev_per_turn`:
- Amusement Park: doubles give a free turn. Exact effect multiplies rounds-until-income
  by 5/6 (geometric series: E[extra turns per doubles] = 1/5, so mean turns per income
  cycle = 6/5, so TUV denominator grows by factor 6/5, TUV shrinks by factor 5/6).
- Radio Tower: reroll on 0-income turn raises EV and lowers variance; increases
  denominator.
- Shopping Mall: +1 coin on Bakery/Convenience Store activations; raises EV.
- Train Station: 2-dice rolling opens up higher-value cards; changes EV distribution.

This is why TUV should eventually consume `round_pmf` rather than `portfolio_ev` — the
PMF correctly models all of these effects together.

**Three TUV flavors (to be implemented in `strategy.py`):**

```
tuv_expected(player, game) -> float
    E[turns to win] = max(n_landmarks_remaining,
                          ceil((cost_remaining - bank) / pmf_mean(round_pmf(...))))
    For now, uses portfolio_ev() as the denominator approximation.

tuv_percentile(player, game, p=0.5) -> float
    Use pmf_percentile(round_pmf(...), p) as the per-round income estimate.
    p=0.5 is median TUV. p>0.5 is optimistic (lucky runs). p<0.5 is pessimistic.
    Allows a trailing bot to ask "what TUV do I get if income goes well?" (p=0.8)
    versus a leading bot asking "what's my worst-case TUV?" (p=0.3).

tuv_variance(player, game) -> float
    Variance in turns-to-win, derived from pmf_variance(round_pmf(...)).
    High variance = outcome is uncertain; low variance = win/loss already determined.
```

**delta-TUV**: `tuv_expected(player_A) - tuv_expected(player_B)` — how many turns ahead
or behind player A is relative to player B. Positive = A is losing. Negative = A is
winning. A bot can use delta-TUV to decide whether to play aggressively (negative delta,
can afford it) or defensively (positive delta, must catch up).

**Implementation plan (when ready):**
1. Stub `own_turn_pmf`, `opponent_turn_pmf`, `round_pmf` returning `NotImplemented`
2. Implement `_die_pmf` and `_convolve` (pure math, easy to test)
3. Implement `own_turn_pmf` for a player with no landmarks (baseline)
4. Add each landmark's effect one at a time, with a test for each
5. Implement `opponent_turn_pmf` (Blue + Red only)
6. Implement `round_pmf` via convolution
7. Verify `pmf_mean(round_pmf(...))` matches `portfolio_ev(...)` for simple cases
8. Implement `tuv_expected` consuming `round_pmf`; verify against closed-form
9. Design TUVBot: a bot that selects purchases by minimizing its own TUV (or
   maximizing delta-TUV vs. the leading opponent). EVBot remains a pure EV machine
   and is not modified. TUVBot, if built correctly, may approach nearly-optimal play.

#### Applications once PMF is built

**Tournament finish scoring**: Replace the current heuristic formula
(`landmark_cost × 3 + card_cost × 2 + bank_coins + 25 for winner`) with
`50.0 - round(tuv_expected(player, game), 1)`. This gives empirically-grounded
credit for game progress: a player 2 rounds from winning scores ~48; one 10 rounds
out scores ~40. The winner's score is naturally highest (TUV = 0 → score = 50).
The fixed `+25` golden-snitch is no longer needed — TUV already creates the gap.
Update `finish_score()` in `tournament.py` once `tuv_expected` is implemented and
verified.

**Migrate EV and coverage to PMF-derived**: Once `pmf_mean(round_pmf(...))` is
verified to match `portfolio_ev(...)` for simple cases, reimplement `portfolio_ev`
as a thin wrapper. Similarly, `coverage_value` (fraction of nonzero outcomes) is
`1.0 - pmf[0]` from `own_turn_pmf`. These migrations are optional cleanup — the
PMF is the source of truth, the wrappers just preserve the existing API.


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
nearly always outranks a non-winner unless the non-winner has failed to
seize the victory. 

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
(1 + 1 + 2 + 3). 

**Seeded pairing rule:** sort all players by current Elo descending, then
assign to tables in order (players 1–2, 3–4, etc. for pairs; 1–3, 4–6 for
triples; 1–4, 5–8 for quads). Within each table, **highest Elo sits last**
(latest turn order, slight handicap for the stronger player). Prefer pairings
that avoid repeating a round-1 opponent in round 2; skip if impossible.

**Padding:** `Bot` fills spots up to the next multiple of 12. Padding bots
receive Elo updates normally so they act as a calibrated floor. 


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
