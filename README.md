**Harmonic Took** is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes because -- let's be realistic -- I am probably not going to finish this project. 

# What?
`h a r m o n i c t o o k`   
`t h m o r o n i c o a k`   
`m o o n c r o a k i t h`   
`t h i n k o r a c o o n`   
`n o t m a c h i k o r o`   

# Does it work? 
[![CircleCI Badge](https://circleci.com/gh/Jurph/harmonictook.svg?style=shield&circletoken=865dd863ff6582b56c01424e84fdeedfbc0e0d8e)](https://app.circleci.com/pipelines/github/Jurph/harmonictook)
[![codecov](https://codecov.io/gh/Jurph/harmonictook/branch/main/graph/badge.svg)](https://codecov.io/gh/Jurph/harmonictook)

# STATUS: v0.9 Released 

The game is now playable with all core mechanics implemented:

## Completed Features:
- ✅ Player turn menu ([B]uy, [P]ass, [S]how available cards)
- ✅ Shopping Mall payout modifiers (+1 to cafes and convenience stores)
- ✅ Radio Tower re-roll mechanic
- ✅ Amusement Park extra turn on doubles (infinite loop bug fixed)
- ✅ TV Station player targeting
- ✅ Business Center card swapping (bots get coin alternative)
- ✅ Two AI types (Bot: random, ThoughtfulBot: priority-based)
- ✅ All tests passing (11/11)

# OPTIONAL ENHANCEMENTS: 

- Display
    - Add descriptive text to the cards for the menus 
    - Create a Display() class [partial]
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display
    - BUG: emoji don't correctly display in Windows terminals

- Testing
    - Learn how mocks work so I don't have to instantiate a bunch of BS classes just to run a test 

- Design Quality:
    - Make better use of dict() structures to do lookups 
    - Consider @classmethods to handle some clunky stuff 
    - Look for chances to use "enumerate()" instead of for loops
