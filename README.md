**Harmonic Took** is a multiplayer city building game that might remind you of other multiplayer city building card games you might have played. But it's not that game! It's not really multiplayer, and it's not complete, and it doesn't include all of the fun stuff the game includes because -- let's be realistic -- I am probably not going to finish this project. 

# What?
`h a r m o n i c t o o k`   
`t h m o r o n i c o a k`   
`m o o n c r o a k i t h`   
`t h i n k o r a c o o n`   
`n o t m a c h i k o r o`   

# NEXT UP: 

- Implement a prompt of player options i.e. [B]uy, [I]mprove, [P]ass, ([R]e-roll), [S]how available cards
- Ensure improvements are passed as valid [B]uy options
- Reload purple cards into availableCards deck after purchase 

# TODO: 

- Testing
    - Run CI tests on commit to git
    - Learn how mocks work so I don't have to instantiate a bunch of BS classes just to run a test 
  
- Display
    - Create a Display() class [partial]
    - Add ANSI-style colored text (orange, red, green, blue, purple) for rich display
    - BUG: emoji don't correctly display in Windows terminals

- Bots
    - Add two simple AIs (buys randomly, evaluates a static priority table)
    
- Turns/Player mechanics
    - Implement TV Station (rolling doubles) to player.dieroll()
    - Implement Orange Card (choose to re-roll) to player.dieroll()

- Orange Cards:
    - Implement payout modifiers for the Shopping Mall (orange card) 
    - player.getsMallPayouts == True?
    
- Purple Cards:
    - Implement player choice for swapping (target and card)
    - Implement player choice for payout (target)
    - Implement forced uniqueness for purple cards

- Design Quality:
    - Make better use of dict() structures to do lookups 
    - Consider @classmethods to handle some clunky stuff 
    - Look for chances to use "enumerate()" instead of for loops