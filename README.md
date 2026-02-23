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

# Latest: v0.9 Released 

The game runs in native python (3.7 and newer) with no installation required. Type `harmonictook.py` to run the game in a terminal window. Future versions may add required dependencies, if I add a GUI. You can also run `tournament.py` to test new bot strategies against each other. 

# Future features

- Opponents
    - Add card-valuation engine that scores cards' expected value 
    - Score card value(s) on multiple dimensions (rush, boom, attack, defend) 
    - Build opponents with different mixes of strategies 

- Display
    - Add descriptive text to the cards for the menus 
    - Create a Display() class [partial] from which I can do either a pretty terminal version, or GUI+mouse+keyboard 
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display

- BUG: emoji don't correctly display in Windows terminals
