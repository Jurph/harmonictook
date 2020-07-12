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
        self.deck.append(WheatField)
        self.deck.append(Bakery)

    def buy(self, Card):
        self.bank -= Card.cost
        self.deck.append(Card)

    def swap(self, Card, otherPlayer, otherCard):
        self.deck.remove(Card)
        self.deck.append(otherCard)
        otherPlayer.deck.append(Card)
        otherPlayer.deck.remove(otherCard)

# Cards must have a name, cost, a target, a payout amount, and one or more die rolls on which they "hit"
class Card(object):
    def __init__(self):
        self.name = None        # Name should be a string like "Wheat Field"
        self.target = None      # Target can be 0 (bank), 1 (die roller), or 2 (each other player)
        self.recipient = None   # Recipient can be 1 (die roller), 2 (each other player), or 3 (owner)
        self.cost = 0           # Cost should be a non-zero integer 
        self.payout = 0         # Payout can be any integer
        self.hits = [0]         # "Hits" can be one or more integers achievable on 2d6 
        self.owner = None       # Cards start with no owner 

    def trigger(self, owner):   # When triggered a card should interact with a player's bank
        owner.bank += self.payout
                                # By default the card increments the owner's bank by the payout

    def __str__(self):          # The string method, by default 
        return("[{}] {}".format(self.hits, self.name))

class Green(Card):
    def __init__(self, name):
        self.name = name
        self.target = 0         # Target can be 0 (bank), 1 (die roller), or 2 (each other player)
        self.recipient = 1      # Recipient can be 1 (die roller), 2 (each other player), or 3 (owner)

    def trigger(self, owner):   # Green cards increment the owner's bank by the payout
        owner.bank += self.payout

class WheatField(Green):
    def __init__(self):
        self.name = "Wheat Field"
        self.cost = 1           # Cost should be a non-zero integer 
        self.payout = 1         # Payout can be any integer
        self.hits = [1]         # "Hits" can be one or more integers achievable on 2d6 

class Bakery(Green):
    def __init__(self):
        self.name = "Bakery"
        self.cost = 1
        self.payout = 1
        self.hits = [2, 3]

class Red(Card):
    def __init__(self, name):
        self.name = name

    def trigger(self, owner, dieroller):
        if dieroller.bank >= self.payout:
            dieroller.bank -= self.payout
            owner.bank += self.payout
        elif dieroller.bank < self.payout:
            owner.bank += dieroller.bank
            dieroller.bank = 0

class Blue(Card):
    def __init__(self, name):
        self.name = name 

    def trigger(self, owner):
        owner.bank += self.payout

class Store(object):
    def __init__(self):
        self.deck = []


def main():
    playerlist = []
    playerlist.append(Player("jurph", 1))
    somecards = playerlist[0].deck
    for card in somecards:
        print("{} has a {}".format(playerlist[0].name, str(card)))
    print("It works.")

if __name__ == "__main__":
    main()
