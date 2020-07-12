#!/usr/bin/python
# harmonictook.py - Main game file

import math
import random 

class Player(object):
    def __init__(self, name = str, order = int):
        self.name = name
        self.order = 0
        self.bank = 3  # start with 3 coins
        self.deck = []
        self.deck.append(Green("wheat field"), Green("bakery"))

# Cards must have a name, cost, a target, a payout amount, and one or more die rolls on which they "hit"
# Wheat Field costs 1, targets the die-roller, pays out 1, and hits on a 1.
# Bakery costs 1, targets the bank, pays out 1 to the die-roller who owns it, and hits on a 2 or 3.
# Cafe costs 2, targets the die-roller, pays out 1 to the owner, and hits on a 3.
class Card(object):
    def __init__(self):
        self.name = None
        self.cost = 0
        self.target = "Bank"
        self.payout = 0
        self.recipient = "Roller"
        self.hits = [0]

    def trigger(self, owner):
        owner.bank += payout

    def __str__(self):
        return("[{}] {}".format(self.hits, self.name))

class Green(Card):
    def __init__(self, name)




def main():
    print("It works.")

if __name__ == "__main__":
    main()
