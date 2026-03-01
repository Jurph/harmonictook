# Test quality review: low diagnostic value

Tests that fall into:

1. **Tests code that isn't ours** — third-party or stdlib behavior; if it fails we don't learn about *our* bugs.
2. **Tests a condition that it sets up to always succeed** — tautological or trivial; success doesn't prove we did something right.
3. **Tests a condition that doesn't matter to us** — doesn't reflect requirements or real outcomes; failure/success is uninformative.

---

## Category 1: Tests code that isn't ours

| Id  | File | Test | Issue | Action |
|-----|------|------|--------|--------|
| **1A** | test_players.py | ~~testAmusementParkDoubles~~ | "At least one doubles in 200 rolls" tests the RNG, not Amusement Park. | **REMOVED.** |
| **1B** | test_players.py | testPlayerDice (100k rolls, mean ≈ 7) | 2d6 mean is 7; test checks we call RNG twice and sum. | **KEEP.** Acceptable sanity check that two-dice path is used and outcome is in the right ballpark. |

---

## Category 2: Condition set up to always succeed (tautological / trivial)

For each: optional **strengthen** idea, then **recommendation** (drop vs keep).

| File | Test | Issue | Strengthen option | Recommendation |
|------|------|--------|--------------------|-----------------|
| **test_strategy.py** | `TestPMFStatsEdgeCases.test_mean_single_outcome` | `pmf_mean({7: 1.0}) == 7` — only checks 7×1.0 = 7. | Use a two-outcome PMF and assert mean = known value (e.g. {0: 0.5, 2: 0.5} → 1.0) so the loop is exercised. | **Drop.** Real PMF tests already cover mean; this adds no diagnostic value. |
| **test_tournament.py** | `test_returns_bool` | Asserts `run_match` returns a bool. | Could assert `result in (True, False)` after a real (or rigged) game and that result matches `game.winner is bue`. | **Drop.** Return type is trivial; win/loss is already tested by test_bue_wins_when_rigged and test_bue_loses_when_rigged. |
| **test_game.py** | `testHistoryStartsEmpty` | New game → `history == []`. | Could assert that after one `next_turn()`, `len(history) == 1` and first entry has expected structure (turn_number, events). | **Drop.** Init contract is redundant to test; history growth is already tested in testHistoryGrowsAfterEachTurn. |
| **test_game_flow.py** | `testSingleTurnNoCrash` | Only "no exception and result is a list". | Assert at least one event with `type == "roll"`, and that `game.turn_number` or `game.history` changed in a defined way. | **Drop.** testNextTurnReturnsDoubles / testNextTurnPassAction / etc. already assert meaningful outcomes; this smoke test adds little. |
| **test_decks.py** | `testStoreFreq` | `sum(freq.values()) == len(table.deck)`. | Keep the invariant but add a second assertion: e.g. that a specific card name has the expected count from the table definition. | **Drop.** Invariant is self-referential; if we want to test freq(), better to assert known card counts for a known deck. |

**Category 2 summary:** Recommend **dropping all five**. Strengthen options exist but duplicate or overlap with tests that already assert meaningful behavior; the net gain in diagnostic value is small.

---

## Category 3: Condition that doesn't matter to us

For each: **improve** option (what would make the test meaningful) or **recommendation** (delete vs keep/improve).

| File | Test | Issue | Improve option | Recommendation |
|------|------|--------|----------------|-----------------|
| **test_tournament.py** | `test_runs_without_error` (TestPrintReport) | Only "print_report doesn't raise". | Capture stdout and assert report contains expected keys (e.g. "2-player", "3-player") or win/loss counts. | **Delete.** Smoke tests with no output check don't tell us what's right; if we want reporting coverage, add one test that asserts on captured output. |
| **test_tournament.py** | `test_runs_without_error` (TestPrintRoundRobinReport) | Same for print_round_robin_report. | Same: assert on captured output (labels, totals). | **Delete.** Same as above. |
| **test_tournament.py** | `test_empty_results` (both) | "Empty dict doesn't crash". | Assert that empty input produces a defined behavior (e.g. no output lines, or a specific "no results" message). | **Delete.** Defensive "no crash" with no contract on behavior is low value. |
| **test_tournament.py** | `test_thoughtfulbot_factory` | Name implies ThoughtfulBot; only checks run_bracket count with rigged game. | Either (a) rename to e.g. `test_run_bracket_accepts_thoughtful_bot_factory` and keep as a single "accepts factory" test, or (b) remove and rely on test_wins_plus_losses_equals_n_games. | **Delete.** Redundant with test_wins_plus_losses_equals_n_games; the factory type isn't exercised. |
| **test_strategy.py** | `TestEVBusinessCenter.test_spite_filter_prefers_less_synergistic_give` | Setup is for spite, but we only assert float and ≥ 0. | **Improve:** Compute delta_ev with a scenario where we *must* give Ranch (e.g. only Ranch to give) vs a scenario where we can give a non-synergy card; assert that EV is higher when we can avoid giving the synergy feeder. Or assert that the card chosen to give (e.g. via inspecting BC logic or a lower-level helper) is not Ranch when another option exists. | **Improve.** Keep the scenario; add an assertion that actually validates spite (e.g. EV comparison or which card would be given). |
| **test_utility.py** | `TestCardDescriptions` (all) | Lock describe() strings; gameplay is in trigger/payout. | If we care about UI/accessibility: keep and treat as snapshot tests. If not: assert only that describe() returns a non-empty string and (optionally) contains key terms (e.g. "roll", "Steals") without locking full text. | **Recommend deletion** unless we explicitly want describe() snapshot regression. If we keep any, reduce to one test per card type that checks "non-empty and contains at least one expected keyword". |
| **test_cards.py** | testBlueCards / testGreenCards / testRedCards (opening assertIsInstance) | `Blue(...)` then assert isinstance Blue/Card. | Remove the type assertions; keep only assertions that matter (e.g. card fires on the right roll, payout). | **Delete** the assertIsInstance(..., Card) and assertIsInstance(..., Blue) (and Green/Red) lines. Keep the rest of each test if it asserts trigger/behavior. |
| **test_game.py** | `testHistoryPlayerSnapshotType` | Asserts snapshot field types (str, int) we defined. | Replace with one assertion that the snapshot is usable (e.g. history[0].players[0].bank equals the player's bank after the turn). | **Delete.** Type checks duplicate our dataclass; testHistoryBankReflectsPostTurnBalance already checks a meaningful snapshot invariant. |

---

## Summary

- **Category 1:** 1A removed; 1B kept.
- **Category 2:** Recommend **drop all five** (optional strengthen options documented if we revisit).
- **Category 3:** Delete: tournament smoke/empty (4 tests), test_thoughtfulbot_factory, describe() suite (or shrink to keyword checks), Card type assertions in testBlueCards/testGreenCards/testRedCards, testHistoryPlayerSnapshotType. **Improve:** test_spite_filter_prefers_less_synergistic_give (assert actual spite behavior or EV comparison).
