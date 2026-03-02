**Harmonic Took** is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes just yet. 

# What?
`h a r m o n i c t o o k`   
`r o m a n t i c h o o k`   
`m o c h a r o o k t i n`   
`t o m o c k a r h i n o`   
`t h m o r o n i c o a k`   
`m o o n c r o a k i t h`   
`t h i n k o r a c o o n`    
`m o c h a i n k r o o t`   
`t i c k m o o n h o r a`   
`n o t m a c h i k o r o`  

# Does it work? 
[![CircleCI Badge](https://circleci.com/gh/Jurph/harmonictook.svg?style=shield&circletoken=865dd863ff6582b56c01424e84fdeedfbc0e0d8e)](https://app.circleci.com/pipelines/github/Jurph/harmonictook)
[![codecov](https://codecov.io/gh/Jurph/harmonictook/branch/main/graph/badge.svg)](https://codecov.io/gh/Jurph/harmonictook)

# Latest: v0.9.2 Released

## Installation

The core game requires only the Python standard library. Clone the repo and run:

```sh
python harmonictook.py
```

For a reproducible environment (recommended), use [`uv`](https://docs.astral.sh/uv/):

```sh
uv venv                        # create .venv/
uv pip install -r requirements.txt   # installs coverage, codecov, textual
```

Then activate the venv and run as normal:

```sh
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

python harmonictook.py                   # plain-text mode (no extra deps)
python harmonictook.py --mode color      # full-screen Textual TUI
```

> **Note:** `--mode color` requires `textual`, which is included in `requirements.txt`.
> If you only want the core game, skip `requirements.txt` entirely — no third-party packages needed.

You can also run `tournament.py` to test new bot strategies against each other, including a `--swiss` CLI flag that runs a seeded Swiss tournament to really find out which bot strategy is best.

# Current features 

## Base Game 

All of the cards work correctly, including the logic from the Business Center (card-swapping), extra turns for doubles, and re-rolling dice with the Radio Tower. Support for 2, 3, or 4 players. Hot-seat multi-player for any of the humans, and any or all players can also be bots. The human running the program gets to decide who sits where at the table. 

## Pretty Good Computer Opponents! 

**Lots of personalities.** Opponents now feature seven personas who play the game differently: 

    - **Random** chooses entirely randomly, unless it has enough to buy a landmark (TRIVIAL)
    - **Thoughtful** follows a hard-coded list of priorities (EASY)
    - **Coverage** seeks to minimize the number of dice rolls that don't generate any income (MEDIUM)
    - **EVie** tries to maximize expected value in the short run (MEDIUM)
    - **Marathon** tries to predict the turn you'll win, and paces itself to win one turn sooner (MEDIUM)
    - **Fromage** attempts to rapidly assemble the Ranch+Cheese engine (HARD)
    - **Impatient** attempts to find the fastest path to victory (HARD)

Machi Koro -- I mean, uh, _harmonictook_ -- has a lot of luck involved. Even the hardest bots can be beaten with decent strategy and hot dice! 

**An arena where you can grow your own bots.** These bots were built by analyzing the results of `tournament.py`, which pits computer opponents against one another in a multi-day Swiss-style tournament. In the default, a field of bots divisible by 12 square off in random pairs, then seeded pairs, then triples, then staggered/striped 4-player tables. A metric called Estimated Rounds Until Victory (ERUV) is calculated at the game's conclusion, which looks at how many monuments a player still needed to buy, their costs, the player's coins, and the expected coins-per-turn the player's cards were generating; pairwise wins & losses are assessed on ERUV scores, and then Glicko scores are calculated. The `--records` and `--stats` command-line options allow per-game JSONL summaries and statistics, respectively. 

## Future features

- Display
  - Create a Display() class [partial] 
  - Add ANSI-style colored text (orange, red, green, blue, purple) for rich terminal display
  - Add a no-foolin' GUI 

- Gameplay 
  - Consider limited-market variant where only 8 or 10 unique cards are available (until a pile is depleted)






# The Rules

**harmonictook** is a city-building dice game for 2–4 players. Each player
manages a small city, rolling dice each turn to collect income from
establishments, then spending that income to build new establishments
or construct landmark buildings. The first player to complete all four
of their landmark buildings wins immediately. 

---

## Components (per player)

- A starting hand of two establishments: one Wheat Field and one Bakery
- Four landmark buildings (unconstructed at game start): Train Station,
  Shopping Mall, Amusement Park, Radio Tower
- A coin supply (tracked numerically; each player starts with 3 coins)

## Shared components

- The market starts with 6 of each red, green, blue, and purple card type 
- All players buy from the same market 

---

## Turn Structure

Each turn has three phases, in order:

### 1. Roll

The active player rolls one die (or may choose to roll two dice if they own 
the Train Station). The total is compared against every establishment in every
player's city.

**Train Station:** If the active player owns the Train Station, they may 
choose to roll either one or two dice for their Roll phase. 

**Radio Tower:** If the active player owns the Radio Tower, they may
choose to re-roll once after seeing the result.

### 2. Resolve Establishments

Cards activate in a fixed color order: Red → Blue → Green → Purple.
Within each color, cards are resolved player by player.

| Color  | Activates on…       | Pays…                                            |
|--------|---------------------|--------------------------------------------------|
| Red    | Any roll            | Active player → card owner (a "toll")            |
| Blue   | Any player's roll   | Bank → card owner                                |
| Green  | Active player's roll only | Bank → active player (some multiply by card count) |
| Purple | Active player's roll only | Special effects (see below)                |


**Purple (major establishment) effects:**

- **Stadium** — Collects 2 coins from every other player.
- **TV Station** — Steals 5 coins from one chosen player.
- **Business Center** — Swaps one establishment card with another
  player. (Bot players receive 5 coins instead.)

Each player may own at most one copy of each purple establishment.

**Shopping Mall modifier:** A player who has built the Shopping Mall
landmark receives +1 coin from their own Cafés, Family Restaurants, and
Convenience Stores.

### 3. Build

The active player may purchase one establishment from the market, or
construct one of their own landmarks, paying the listed cost from their
bank. They may also pass and buy nothing.

A player can never spend more coins than they have or be 'taxed' by other
players once they are at 0 coins. Banks never go negative.

---

## Establishment Reference

### Blue — pays on any roll

| Name           | Rolls | Payout |
|----------------|-------|--------|
| Wheat Field    | 1     | 1      |
| Ranch          | 2     | 1      |
| Forest         | 5     | 1      |
| Mine           | 9     | 5      |
| Apple Orchard  | 10    | 3      |

### Green — pays active player only

| Name                      | Rolls  | Payout                                      |
|---------------------------|--------|---------------------------------------------|
| Bakery                    | 2–3    | 1                                           |
| Convenience Store         | 4      | 3 (+1 with Shopping Mall)                   |
| Cheese Factory            | 7      | 3 × number of Ranch cards you own           |
| Furniture Factory         | 8      | 3 × number of Gear (Forest/Mine) cards      |
| Farmer's Market           | 11–12  | 2 × number of Grain (Wheat/Orchard) cards   |

### Red — pays card owner from active player

| Name              | Rolls  | Payout                        |
|-------------------|--------|-------------------------------|
| Café              | 3      | 1 (+1 with Shopping Mall)     |
| Family Restaurant | 9–10   | 2 (+1 with Shopping Mall)     |

### Purple — active player only, special effects

| Name              | Roll | Effect                                   |
|-------------------|------|------------------------------------------|
| Stadium           | 6    | Take 2 coins from each other player      |
| TV Station        | 6    | Take 5 coins from one chosen player      |
| Business Center   | 6    | Swap one establishment with another player |

---

## Landmarks

Landmarks are built once per player, and confer permanent abilities. 
They are not purchased from the market — they are always available to 
their owner at the listed cost. While their costs escalate in proportion 
to the power they grant, there is no requirement to build them in order: 
only to get all four before your opponents can do the same. 

| Name           | Cost | Ability                                              |
|----------------|------|------------------------------------------------------|
| Train Station  | 4    | Roll 1 or 2 dice on your turn                        |
| Shopping Mall  | 10   | +1 coin from Cafés, Family Restaurants, Convenience Stores |
| Amusement Park | 16   | Rolling doubles gives you an extra turn              |
| Radio Tower    | 22   | Once per turn, re-roll your dice                     |

---

## Win Condition

The first player to construct all four of their landmark buildings wins
immediately.

--- 

## Example Turn: 

[TODO]
