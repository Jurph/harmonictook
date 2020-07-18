#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# harmonictook.py - Main game file

import math
import random
import statistics

class Player(object):
    def __init__(self, name = "Player"):
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
            if item.name.lower() == name.lower():
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
                print("{} bought a {} for {} coins, and now has {} coins.".format(self.name, card.name, card.cost, self.bank))
            else:
                print("Sorry: a {} costs {} and {} only has {}.".format(card.name, card.cost, self.name, self.bank))
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

class Human(Player): # TODO : make this more robust - type checking etc. 
    def choose(self, variable, options=list):
        decided = False
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        while not decided:
            guess = input("Human player {}, enter your choice: ".format(self.name))
            if guess in options:
                variable = guess
                decided = True     
            else:
                print("Sorry: {} isn't a valid choice.".format(guess))
        return variable

class Bot(Player):
    def choose(self, variable, options=list):
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        else:
            variable = random.choice(options)
            return variable

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
        if self.sortvalue() == other.sortvalue():
            return True
        else:
            return False
    
    def __ne__(self, other):
        if self.sortvalue() == other.sortvalue():
            return False
        else:
            return True

    def __lt__(self, other):
        if self.sortvalue() < other.sortvalue():
            return True
        else:
            return False
    
    def __le__(self, other):
        if self.sortvalue() <= other.sortvalue():
            return True
        else:
            return False
    
    def __gt__(self, other):
        if self.sortvalue() > other.sortvalue():
            return True
        else:
            return False

    def __ge__(self, other):
        if self.sortvalue() >= other.sortvalue():
            return True
        else:
            return False

    def __hash__(self):
        return hash((self.name, self.category, self.cost))

    def __str__(self):  
        # TODO: figure out which scope this list belongs in for card display
        categories = {1:"|🌽|", 2:"|🐄|", 3:"|🏪|", 4:"|☕|", 5:"|⚙️| ", 6:"|🏭|", 7:"|🗼|", 8:"|🍎|"}
        # WARNING: In Unicode, the "gear" emoji is decorated with U+FE0F, an invisible zero-space
        # codepoint. Its full name is 'U+2699 U+FE0F'. Calls to format() double-count it when 
        # trying to do fixed width. Adding a space for padding and telling format() to display it
        # as single-width seems to work. There probably are other solutions, but this one works.
        catvalue = self.category
        cardstring = "{:7} {:3} : {:16}".format(str(self.hitsOn), categories[catvalue], self.name)
        # print("DEBUG: category for {} was {}".format(self.name, self.category))
        # print("DEBUG: emoji lookup for category {} results in {:4}".format(catvalue, categories[catvalue]))
        return cardstring

    # TODO: card.helptext goes here - potentially adding info to __str__ 

class Green(Card):
    def __init__(self, name=str, category=int, cost=int, payout=int, hitsOn=list, multiplies=None):
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
        if self.owner.isrollingdice:
            if not self.multiplies: # TODO: check this
                self.owner.deposit(self.payout)
                print("{} pays out {} to {}.".format(self.name, self.payout, self.owner.name))
            else:
                for card in self.owner.deck.deck:
                    if card.category == self.multiplies:
                        subtotal += 1
                    else:
                        pass
                print("{} has {} {} cards...".format(self.owner.name, subtotal, self.multiplies))
                amount = self.payout * subtotal
                print("{} pays out {} to {}.".format(self.name, amount, self.owner.name))
                self.owner.deposit(amount)
        else:
            print("{} didn't roll the dice - no payout.".format(self.owner.name))

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
        print("{} pays out {} to {}.".format(self.name, self.payout, self.owner.name))
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
        target = random.choice(players)
        while target.isrollingdice:
            target = random.choice(players)
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
        if self.owner == dieroller:
            print("Swapping cards is not implemented just yet. Here's five bucks, kid.")
            dieroller.deposit(5)
        else:
            print("No payout.")

# "Stores" are just Decks, which are themselves wrappers for a deck[] list and a few functions
class Store(object):
    def __init__(self):
        self.deck = []
        self.frequencies = {}

    def freq(self):
        f = {}
        for card in self.deck:
            if f.get(card):
                f[card] += 1
            else:
                f[card] = 1
        self.frequencies = f
        return self.frequencies

    def append(self, card):
        if isinstance(card, Card):
            self.deck.append(card)
            self.deck.sort()
        else:
            TypeError()

    def remove(self, card):
        if isinstance(card, Card):
            self.deck.remove(card)
            self.deck.sort()
        else:
            TypeError()

class PlayerDeck(Store):
    def __init__(self, owner):
        self.deck = []
        self.frequencies = {}
        self.owner = owner
        # TODO: don't repeat yourself - define these in one place and insert them from there
        self.deck.append(Blue("Wheat Field",1,1,1,[1]))
        self.deck.append(Green("Bakery",3,1,1,[2,3]))
        for card in self.deck:
            card.owner = self.owner

    def __str__(self):
        decktext = ""
        for card in self.deck:
            if isinstance(card, (Red, Green, Blue)):
                decktext += "{} - {}\n".format(card.hitsOn, card.name)
            else:
                decktext += str(card)
        return decktext

class TableDeck(Store):
    def __init__(self):
        self.deck = []
        self.frequencies = {}
        # categories = {1:"🌽", 2:"🐄", 3:"🏪", 4:"☕", 5:"⚙️", 6:"🏭", 7:"🗼", 8:"🍎"}
        for _ in range(0,6):
            # Add six of every card: Name, category, cost, payout, hitsOn[], and optionally, what it multiplies
            self.append(Blue("Wheat Field",1,1,1,[1]))
            self.append(Blue("Ranch",2,1,1,[2]))
            self.append(Green("Bakery",3,1,1,[2,3]))
            self.append(Red("Cafe",4,2,1,[3]))
            self.append(Green("Convenience Store",3,2,3,[4]))
            self.append(Blue("Forest",5,3,1,[5]))
            self.append(TVStation())
            self.append(BusinessCenter())
            self.append(Stadium())
            self.append(Green("Cheese Factory",6,5,3,[7],2))
            self.append(Green("Furniture Factory",6,3,3,[8],5))
            self.append(Blue("Mine",5,6,5,[9]))
            self.append(Red("Family Restaurant",4,3,2,[9,10]))
            self.append(Blue("Apple Orchard",1,3,3,[10]))
            self.append(Green("Fruit and Vegetable Market",8,2,2,[11,12],1))
        self.deck.sort() 
        
    def names(self, maxcost=99, flavor=Card): # A de-duplicated list of the available names
        namelist = []
        for card in self.deck:
            if (card.name not in namelist) and isinstance(card, flavor) and (card.cost <= maxcost): # TODO: target hitsOn?
                namelist.append(card.name)
            else:
                pass
        return namelist

def setPlayers():
    playerlist = []
    moreplayers = True
    while moreplayers:
        humanorbot = input("Add a [H]uman or add a [B]ot? ")
        if "h" in humanorbot.lower():
            playername = input("What's the human's name? ")            
            playerlist.append(Human(name=str(playername)))
        elif "b" in humanorbot.lower():
            playername = input("What's the bot's name? ")
            playerlist.append(Bot(name=str(playername)))
        else:
            print("Sorry, I couldn't find an H or B in your answer. ")
        if len(playerlist) == 4:
            break
        elif len(playerlist) >= 2:
            yesorno = input("Add another player? ([Y]es / [N]o) ")
            if "y" in yesorno.lower():
                pass
            elif "n" in yesorno.lower():
                moreplayers = False
                break
            else:
                print("Sorry, I couldn't find a Y or N in your answer. ")
    return playerlist

def display(deckObject):
    f = deckObject.freq()
    rowstring = ""
    for card, quantity in f.items():
        rowstring += "{:16}".format((str(card) + "|"))
        for _ in range(quantity):
            rowstring += "[]"
        rowstring += str(quantity) + "\n"
    print(rowstring)

def newGame():
    availableCards = TableDeck()
    playerlist = setPlayers()
    return availableCards, playerlist

def nextTurn(playerlist, player, availableCards):
    # Reset the turn counter
    for person in playerlist:
        person.isrollingdice = False
    player.isrollingdice = True

    # Die Rolling Phase 
    print("-=-=-= It's {}'s turn =-=-=-".format(player.name))
    dieroll = player.dieroll(1) # TODO: let the player choose
    print("{} rolled a {}.".format(player.name, dieroll))
    for person in playerlist:
        for card in person.deck.deck:
            if dieroll in card.hitsOn:
                print("{}'s {} activates on a {}...".format(person.name, card.name, dieroll))
                card.trigger(playerlist) # TODO: integrate order of parsing

    # Buy Phase 
    for person in playerlist:
        print("{} now has {} coins.".format(person.name, person.bank))
    options = availableCards.names(maxcost=player.bank)
    display(player.deck)
    cardname = player.choose(card, options)
    if cardname != None:
        player.buy(cardname, availableCards)

def functionalTest():
    # Right now this is a set of integration tests... 
    # entities = ["the bank", "the player who rolled the dice", "the other players", "the card owner"]
    playerlist = []
    playerlist.append(Human("Jurph"))
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
    print("-=-=-=-=-=-")

def main():
    availableCards, playerlist = newGame()
    while True:
        for turntaker in playerlist:
            nextTurn(playerlist, turntaker, availableCards)

if __name__ == "__main__":
    main()