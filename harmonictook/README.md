Harmonic Took is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes because -- let's be realistic -- I am probably not going to finish this project. 

# TODO: 
- Testing
    - Build an integration test that tests most behaviors
    - Split off runTests() away from main() 
    - Add unit testing

- Implement nextTurn()

- Display
    - Implement display of a player's current spread 
    - Implement display of what a player might want to buy
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display

- Turns/Player mechanics
    - Add player improvements to player.dieroll()
    - Add two simple AIs (buys randomly, buys based on expected value)

- Orange Cards:
    - Implement payout modifiers for the Shopping Mall (orange card) 
    - Consider booleans e.g. player.canRollTwoDice
    - player.getsMallPayouts == True?
    
- Purple Cards:
    - Implement player choice for swapping (target and card)
    - Implement player choice for payout (target)
    - Implement forced uniqueness 
