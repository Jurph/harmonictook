Harmonic Took is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes because -- let's be realistic -- I am probably not going to finish this project. 

# What?
`h a r m o n i c t o o k`   
`t h m o r o n i c o a k`   
`m o o n c r o a k i t h`   
`t h i n k o r a c o o n`   
`n o t m a c h i k o r o`   

# TODO: 

- Make better use of dict() structures to do lookups 

- Testing
    - Add unit testing

- Display
    - Create a Display() class [partial]
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display
    - BUG: emoji don't correctly display in Windows terminals

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
