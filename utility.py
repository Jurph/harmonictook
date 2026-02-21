#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# utility.py - Helper functions

def userChoice(options: list) -> str:
    """Display a numbered menu and return the element chosen by the user (1-indexed input)."""
    madeValidChoice = False
    print(" -=-= Choose One =-=- ")
    for i in range(len(options)):
        print("[{}] : {}".format(i+1, options[i]))
    while not madeValidChoice:
        j = input("Your selection: ")
        j = int(j)
        if j <= len(options):
            madeValidChoice = True
            break
        else:
            pass
    # Return the user's integer choice (1-N)
    # but subtract one because options[] is zero-indexed.
    return options[j-1]


def card_menu(cards: list) -> str:
    """Display a formatted purchase table (index, name, cost, rolls, description) and return the chosen card's name."""
    print(" -=-= Buy a Card =-=- ")
    print(f"  {'#':>2}  {'Name':<24} {'Cost':>4}   {'Rolls':<10}  Description")
    print(f"  {'':->2}  {'':->24} {'':->4}   {'':->10}  {'':->44}")
    for i, card in enumerate(cards, 1):
        rolls = "—" if card.hitsOn == [99] else ", ".join(str(r) for r in card.hitsOn)
        print(f"  [{i:>2}]  {card.name:<24} {card.cost:>4}   {rolls:<10}  {card.describe()}")
    while True:
        try:
            j = int(input("Your selection: "))
            if 1 <= j <= len(cards):
                return cards[j - 1].name
            print(f"Please enter a number between 1 and {len(cards)}.")
        except ValueError:
            print("Please enter a number.")