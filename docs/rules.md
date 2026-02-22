# harmonictook — Game Rules

harmonictook is a city-building dice game for 2–4 players. Each player
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
| Blue   | Any player's roll   | Bank → card owner                                |
| Green  | Active player's roll only | Bank → active player (some multiply by card count) |
| Red    | Any roll            | Active player → card owner (a "toll")            |
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
| Fruit & Vegetable Market  | 11–12  | 2 × number of Grain (Wheat/Orchard) cards   |

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

