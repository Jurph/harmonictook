Harmonic Took is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes because -- let's be realistic -- I am probably not going to finish this project. 

# TODO: 
- Fix bug where card symbols don't correctly display
- Make better use of dict() structures to do lookups 

- Testing
    - Add unit testing

- Display
    - Create a Display() class 
    - Implement display of a player's current spread 
    - Implement display of what a player might want to buy
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display

- Bots
    - Add two simple AIs (buys randomly, evaluates a static priority table)
    
- Turns/Player mechanics
    - Add player improvements (rolling doubles, rolling two dice) to player.dieroll()
    - Implement a prompt of player options i.e. [B]uy, [I]mprove, [P]ass, ([R]e-roll), [S]how available cards

- Orange Cards:
    - Implement payout modifiers for the Shopping Mall (orange card) 
    - Consider booleans e.g. player.canRollTwoDice
    - player.getsMallPayouts == True?
    
- Purple Cards:
    - Implement player choice for swapping (target and card)
    - Implement player choice for payout (target)
    - Implement forced uniqueness for purple cards
