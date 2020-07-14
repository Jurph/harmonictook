#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# harmonictook.py - Main game file

import math
import random
import statistics

class Player(object):
    def __init__(self, name = str, order = int):
        self.name = name
        self.order = 0
        self.isrollingdice = False
        self.abilities = 0
        self.bank = 3                  # Everyone starts with 3 coins
        self.deck = PlayerDeck(self)

    def dieroll(self, dice):
        self.isrollingdice = True
        # TODO: integrate with self.abilities (Booleans?) to allow/block 2 dice
        if dice == 1:
            return random.randint(1,6)
        elif dice == 2:
            return random.randint(1,6) + random.randint(1,6)
        else:
            print("Sorry: you can only roll up to two dice")

    def deposit(self, amount):
        self.bank += amount

    def deduct(self, amount):
        if self.bank >= amount:
            deducted = amount
        else:
            deducted = self.bank
        self.bank -= deducted
        return deducted

    def buy(self, name, availableCards):
        card = None
        for item in availableCards.deck:
            if item.name == name:
                card = item
                break
            else:
                pass
        if isinstance(card,Card):
            if self.bank >= card.cost:
                self.deduct(card.cost)
                self.deck.append(card)
                card.owner = self
                availableCards.deck.remove(card)
                print("Bought a {} for {} coins. You now have {} coins.".format(card.name, card.cost, self.bank))
            else:
                print("Sorry: a {} costs {} and you only have {}.".format(card.name, card.cost, self.bank))
        else:
            print("Sorry: we don't have anything called '{}'.".format(name))
        
    def swap(self, Card, otherPlayer, otherCard):
        Card.owner = otherPlayer
        otherCard.owner = self
        otherPlayer.deck.remove(otherCard)
        self.deck.append(otherCard)
        self.deck.remove(Card)
        otherPlayer.deck.append(Card)

    def improve(self, cost):
        if cost == 4:
            self.abilities += 1 # Can roll two dice 
        elif cost == 10:
            self.abilities += 2 # Shops (3) and Cups (4) pay out +1 
        elif cost == 16:
            self.abilities += 4 # Doubles grant a second turn 
        elif cost == 22:
            self.abilities += 8 # Can re-roll (player's choice)
        else:
            print("FATAL - tried to 'improve()' using a non standard cost")
            exit()

# Cards must have a name, cost, a payer, a payout amount, and one or more die rolls on which they "hit"
class Card(object):
    def __init__(self):
        self.name = None        # Name should be a string like "Wheat Field"
        self.payer = None       # Payer can be 0 (bank), 1 (die roller), 2 (each other player), 3 (owner), or 4 (specific player)
        self.recipient = None   # Recipient can be 1 (die roller), 2 (each other player), or 3 (owner)
        self.cost = 0           # Cost should be a non-zero integer 
        self.payout = 0         # Payout can be any integer
        self.hitsOn = [0]       # "Hits" can be one or more integers achievable on 2d6 
        self.owner = None       # Cards start with no owner 
        self.category = None    # Categories from the list below  
        self.multiplies = None  # Also categories 

    def sortvalue(self):
        from statistics import mean
        value = 0.000
        value += mean(self.hitsOn)   # Sort by mean hit value 
        value += self.cost/100                  # Then by cost
        value += ord(str(self.name)[0])/255     # Then by pseudo-alphabetical 
        return value

    def __eq__(self, other):
        if self.name == other.name:
            return True
        elif str(self) == str(other):
            return True
        else:
            return False
    
    def __ne__(self, other):
        if self.name == other.name:
            return False
        elif str(self) == str(other):
            return False
        else:
            return True

    def __lt__(self, other):
        if self.sortvalue < other.sortvalue:
            return True
        else:
            return False
    
    def __le__(self, other):
        if self.sortvalue <= other.sortvalue:
            return True
        else:
            return False
    
    def __gt__(self, other):
        if self.sortvalue > other.sortvalue:
            return True
        else:
            return False

    def __ge__(self, other):
        if self.sortvalue >= other.sortvalue:
            return True
        else:
            return False

    def __str__(self):          # The string method, by default, for all cards  
    # TODO: figure out which scope this list belongs in for card display
        categories = {1:"🌽", 2:"🐄", 3:"🏪", 4:"☕", 5:"⚙️ ", 6:"🏭", 7:"🗼", 8:"🍎"}
        return("{:8} {:4} : {}".format(str(self.hitsOn), categories[int(self.category)], str(self.name)))

    # TODO: card.helptext goes here - potentially adding info to __str__ 

class Green(Card):
    def __init__(self, name=str, category=int, cost=int, payout=int, hitsOn=list, multiplies=int):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.multiplies = multiplies
        self.hitsOn = hitsOn
        self.payer = 0         # Green cards always pay out from the bank (0)
        self.recipient = 1     # Green cards always pay to the die roller (1)

    def trigger(self, players):   # Green cards increment the owner's bank by the payout
        subtotal = 0
        if self.multiplies == None:
            self.owner.deposit(self.payout)
        else:
            for card in self.owner.deck.deck:
                if card.category == self.multiplies:
                    subtotal += 1
                else:
                    pass
            amount = self.payout * subtotal
            self.owner.deposit(amount)

class Red(Card):
    def __init__(self, name=str, category=int, cost=int, payout=int, hitsOn=list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn
        self.payer = 1          # Red cards pay out from the die-roller (1) 
        self.recipient = 3      # Red cards pay to the card owner (3)

    def trigger(self, players):
        for person in players:
            if person.isrollingdice:
                dieroller = person
            else:
                pass
        payout = dieroller.deduct(self.payout)
        self.owner.deposit(payout)
        
class Blue(Card):
    def __init__(self, name=str, category=int, cost=int, payout=int, hitsOn=list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn
        self.payer = 0          # Blue cards pay out fromm the bank (0)
        self.recipient = 3      # Blue cards pay out to the card owner (3)

    def trigger(self, players):
        self.owner.deposit(self.payout)

class Stadium(Card):
    def __init__(self, name="Stadium"):
        self.name = name
        self.category = 7
        self.cost = 6
        self.recipient = 3      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 2          # Stadium collects from all players
        self.payout = 2
    
    def trigger(self, players):
        for person in players:
            if person.isrollingdice:
                dieroller = person
            else:
                pass
        for person in players:
            payment = person.deduct(self.payout)
            dieroller.deposit(payment)

class TVStation(Card):
    def __init__(self, name="TV Station"):
        self.name = name
        self.category = 7
        self.cost = 7
        self.recipient = 1      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 4          # TV Station collects from one player
        self.payout = 5
    
    def trigger(self, players):
        for person in players:
            if person.isrollingdice:
                dieroller = person
            else:
                pass
        score = 0
        target = 0
        for person in players:

            if person == dieroller:
                pass
            if person.bank() < self.payout:
                pass
            else:
                if person.abilities > score:
                    target = person
                    score = person.abilities
                else:
                    pass
        payment = target.deduct(self.payout)
        dieroller.deposit(payment)

class BusinessCenter(Card):
    def __init__(self, name="Business Center"):
        self.name = name
        self.category = 7
        self.cost = 8
        self.recipient = 3      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 4          # Business Center collects from one targeted player (4)
        self.payout = 0         # Payout is the ability to swap cards (!)
    
    def trigger(self, players):
        for person in players:
            if person.isrollingdice:
                dieroller = person
        print("Swapping cards is not implemented just yet. Here's five bucks, kid.")
        dieroller.deposit(5)

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

    def sort(self):
        return

class PlayerDeck(Store):
    def __init__(self, owner):
        self.deck = []
        self.owner = owner
        # TODO: don't repeat yourself - define these in one place and insert them from there
        self.deck.append(Blue("Wheat Field",1,1,1,[1]))
        self.deck.append(Green("Bakery",3,1,1,[2,3]))
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
        categories = {1:"🌽", 2:"🐄", 3:"🏪", 4:"☕", 5:"⚙️", 6:"🏭", 7:"🗼", 8:"🍎"}
        for _ in range(0,6):
            # Add six of every card: Name, category, cost, payout, multiplies, hitsOn[]
            self.append(Blue("Wheat Field",1,1,1,[1]))
            self.append(Blue("Ranch",2,1,1,[2]))
            self.append(Green("Bakery",3,1,1,[2,3]))
            self.append(Red("Cafe",4,2,1,[3]))
            self.append(Green("Convenience Store",3,2,3,[4]))
            self.append(Blue("Forest",5,3,1,[5]))
            self.append(TVStation())
            self.append(BusinessCenter())
            self.append(Stadium())
            self.append(Green("Cheese Factory",6,5,3,[7],1))
            self.append(Green("Furniture Factory",6,3,3,[8],5))
            self.append(Blue("Mine",5,6,5,[9]))
            self.append(Red("Family Restaurant",4,3,2,[9,10]))
            self.append(Blue("Apple Orchard",1,3,3,[10]))
            self.append(Green("Fruit and Vegetable Market",8,2,2,[11,12]))
        # self.deck.sort() 
        # TODO: define a custom Store.deck.sort() method that doesn't exhaust the recursion depth.

def main():
    # Right now this is a set of integration tests... 
    # entities = ["the bank", "the player who rolled the dice", "the other players", "the card owner"]
    playerlist = []
    playerlist.append(Player("Jurph", 1))
    jurph = playerlist[0]
    availableCards = TableDeck()
    for card in jurph.deck.deck:
        print(card)
    # thiscard = jurph.deck.deck[0]
    print("Right now {} has {} coins.".format(playerlist[0].name, playerlist[0].bank))
    dieroll = jurph.dieroll(1)
    print("{} rolled a {}...".format(playerlist[0].name, dieroll))
    for card in jurph.deck.deck:
        if dieroll in card.hitsOn:
            card.trigger(card.owner) # TODO: integrate order of parsing
    print("Right now {} has {} coins.".format(playerlist[0].name, playerlist[0].bank))
    jurph.buy("Mine", availableCards)
    jurph.buy("Duck", availableCards)
    jurph.buy("Forest", availableCards)
    jurph.buy("Ranch", availableCards)
    # TODO: pretty-print the decks in a useful format 
    for card in jurph.deck.deck:
        print(card)


if __name__ == "__main__":
    main()
