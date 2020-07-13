#!/usr/bin/python
# harmonictook.py - Main game file

import math
import random 


class Player(object):
    def __init__(self, name = str, order = int):
        self.name = name
        self.order = 0
        self.abilities = 0 
        self.bank = 3  # start with 3 coins
        # TODO: consider whether a custom Deck() class might make more sense
        # Easy to print a player's deck, print the store, etc. 
        # Easy to overload operators for swapping stuff in and out 
        self.deck = PlayerDeck(self)

    def buy(self, Card, availableCards):
        self.bank -= Card.cost
        Card.owner = self
        self.deck.deck.append(Card)
        
    def swap(self, Card, otherPlayer, otherCard):
        Card.owner = otherPlayer
        otherCard.owner = self
        otherPlayer.deck.remove(otherCard)
        self.deck.append(otherCard)
        self.deck.remove(Card)
        otherPlayer.deck.append(Card)

    def improve(self, cost):
        if cost == 4:
            self.abilities += 1
        elif cost == 10:
            self.abilities += 2
        elif cost == 16:
            self.abilities += 4
        elif cost == 22:
            self.abilities += 8
        else:
            print("FATAL - tried to 'improve()' using a non standard cost")
            exit()

# Cards must have a name, cost, a payer, a payout amount, and one or more die rolls on which they "hit"
class Card(object):
    def __init__(self):
        self.name = None        # Name should be a string like "Wheat Field"
        self.payer = None       # Payer can be 0 (bank), 1 (die roller), or 2 (each other player)
        self.recipient = None   # Recipient can be 1 (die roller), 2 (each other player), or 3 (owner)
        self.cost = 0           # Cost should be a non-zero integer 
        self.payout = 0         # Payout can be any integer
        self.hitsOn = [0]         # "Hits" can be one or more integers achievable on 2d6 
        self.owner = None       # Cards start with no owner 

    # TODO: card.helptext goes here 

    def __str__(self):          # The string method, by default 
        return("{} {}".format(str(self.hitsOn), str(self.name)))

class Green(Card):
    def __init__(self, name=str, cost=int, payout=int, hitsOn=list):
        Card.__init__(self)
        self.payer = 0         # Green cards always pay out from the bank (0)
        self.recipient = 1     # Green cards always pay to the die roller (1)
        self.name = name
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn

    def trigger(self, owner):   # Green cards increment the owner's bank by the payout
        owner.bank += self.payout

class Red(Card):
    def __init__(self, name=str, cost=int, payout=int, hitsOn=list):
        self.name = name
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn

    def trigger(self, owner, dieroller):
        if dieroller.bank >= self.payout:
            dieroller.bank -= self.payout
            owner.bank += self.payout
        elif dieroller.bank < self.payout:
            owner.bank += dieroller.bank
            dieroller.bank = 0

class Blue(Card):
    def __init__(self, name=str, cost=int, payout=int, hitsOn=list):
        self.name = name 
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn

    def trigger(self, owner):
        owner.bank += self.payout

class Store(object):
    def __init__(self):
        self.deck = []

    def append(self, card):
        if isinstance(card, Card):
            self.deck.append(card)
        else:
            TypeError()

    def remove(self, card):
        if isinstance(card, Card):
            self.deck.remove(card)
        else:
            TypeError()

class PlayerDeck(Store):
    def __init__(self, owner):
        self.deck = []
        self.owner = owner
        self.deck.append(Blue("Wheat Field",1,1,[1]))
        self.deck.append(Green("Market",1,1,[2,3]))
        for card in self.deck:
            card.owner = self.owner

    def __str__(self):
        decktext = ""
        for card in self.deck(sorted):
            if isinstance(card, (Red, Green, Blue)):
                decktext += "{} - {}\n".format(card.hitsOn, card.name)
            else:
                decktext += str(card)
        return decktext

class TableDeck(Store):
    def __init__(self):
        self.deck = []
        for _ in range(0,6):
            # Add six of every card: Name, cost, payout, hitsOn[]
            self.append(Blue("Wheat Field",1,1,[1]))
            self.append(Blue("Ranch",1,1,[2]))
            self.append(Green("Bakery",1,1,[2,3]))
            self.append(Red("Cafe",2,1,[3]))
            self.append(Green("Convenience Store", 2, 3, [4]))
            self.append(Blue("Forest",3,1,[5]))
            self.append(Green("Cheese Factory",5,3,[7]))
            self.append(Green("Furniture Factory",3,3,[8]))
            self.append(Blue("Mine",6,5,[9]))
            self.append(Red("Family Restaurant",3,2,[9,10]))
            self.append(Blue("Apple Orchard",3,3,[10]))
            self.append(Green("Fruit and Vegetable Market",2,2,[11,12]))
        self.deck.sort()

def main():
    # entities = ["the bank", "the player who rolled the dice", "the other players", "the card owner"]
    playerlist = []
    playerlist.append(Player("Jurph", 1))
    availableCards = TableDeck()
    somecards = playerlist[0].deck.deck
    print(str(somecards))
    thiscard = somecards[0]
    print("This is a {}. It costs {} and pays out {}.".format(thiscard.name, thiscard.cost, thiscard.payout))
    print("Right now {} has {} coins.".format(playerlist[0].name, playerlist[0].bank))
    print("I just rolled a 1!")
    thiscard.trigger(thiscard.owner)
    print("Right now {} has {} coins.".format(playerlist[0].name, playerlist[0].bank))
    for card in availableCards.deck:
        print card

if __name__ == "__main__":
    main()
