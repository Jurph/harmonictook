# TODO for harmonictook

## Features

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

### Testing Strategy
**Restructure tests for PyPI packaging and comprehensive coverage**

Current state: Single `tests.py` with integration tests

Target structure (PyPI-ready):
- `tests/test_cards.py` - Card class logic, trigger mechanics, Shopping Mall modifiers
- `tests/test_players.py` - Player bank operations, dice rolling, landmark tracking
- `tests/test_bots.py` - Bot decision-making, strategy logic, chooseCard/chooseDice
- `tests/test_user_interactions.py` - Human player input handling (mocked)
- `tests/test_game_flow.py` - Full game integration tests (turn mechanics, win conditions)
- `tests/test_decks.py` - Store, PlayerDeck, TableDeck, UniqueDeck operations

Testing improvements:
- **Mock random events**: Use `unittest.mock.patch('random.randint')` for deterministic dice rolls
- **Mock user inputs**: Mock `input()` calls to test Human player interactions automatically
- **Focused unit tests**: Minimal setup, test one thing per test
- **Keep integration tests**: Verify full game flow in `test_game_flow.py`
- **Coverage target**: ~100% using `coverage.py` or `pytest-cov`

CircleCI updates:
- Update `.circleci/config.yml` test command to run all tests: `python -m pytest tests/` or `python -m unittest discover tests/`
- Ensure CI runs successfully with new test structure
- Add coverage reporting to CI pipeline

### Code Quality - High Priority (Blocks GUI/Rich Bot Features)

**1. Create GameState class to encapsulate game data**
- Current: Game state scattered across function parameters (playerlist, availableCards, specialCards, etc.)
- Target: Single GameState object containing players, decks, turn number, current player
- Benefits: Easier to serialize for save/load, cleaner API for GUI queries, simpler bot evaluation

**2. Decouple output from game logic (event system)**
- Current: Print statements embedded in trigger() methods and game flow
- Target: Game logic returns events/actions, display layer renders them
- Benefits: Essential for GUI (can't animate "card triggered" if it just prints), easier to test, supports different UIs

**3. Extract Shopping Mall logic to payout modifier system**
- Current: hasShoppingMall checks hardcoded in Green and Red card classes
- Target: Flexible modifier system that player/card classes can query
- Benefits: Expansions will add more landmark modifiers; avoid editing card classes repeatedly

### Code Quality - Medium Priority (Helps Rich Bot, Expansions)

**4. Add Category enum/constants**
- Current: Magic numbers (1=wheat, 2=ranch, etc.) scattered in code
- Target: `class Category(IntEnum): WHEAT=1, RANCH=2, SHOP=3, ...`
- Benefits: Bot evaluation code is clearer (`Category.RANCH` vs `2`), easier to extend

**5. Create helper function for finding die-roller**
- Current: Repeated loop pattern in every Purple card trigger()
- Target: `get_die_roller(players)` utility function
- Benefits: DRY principle, single place to fix bugs, easier to test

**6. Simplify market refresh logic in nextTurn()**
- Current: Four-way truth table with nested conditionals (lines 756-768)
- Target: Clearer two-branch logic (player owns it? remove from market : add to market)
- Benefits: Easier to debug, more maintainable

### Code Quality - Low Priority (Code Cleanliness)

**7. ✅ Apply @total_ordering decorator to Card class** - DONE
- Added @functools.total_ordering decorator
- Simplified from 6 methods to 2 (__eq__ and __lt__)
- Added proper NotImplemented returns for type safety

**8. ✅ Remove dead functionalTest() code** - DONE
- Removed unused functionalTest() function
- Cleaned up ~20 lines of dead code

**9. ✅ Make string formatting consistent** - DONE
- Converted all 32 .format() calls to f-strings
- Codebase now uses consistent modern Python string formatting

**10. Better use of dict() structures for card lookups**
- Look for chances to use enumerate() instead of for loops (checked: current usage is appropriate)
- Add remaining type hints where they improve clarity (not everywhere)

**11. Complete Display() class refactoring**
- Formalize the display layer once event system is in place

**12. Performance benchmarks**
- Profile game loop, card triggers, bot decision-making
- Establish baseline before GUI work
