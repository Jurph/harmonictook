#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# harmonictook.py - Main game file

import math
import random
import utility
import argparse
import unittest
import statistics

class Player(object):
    def __init__(self, name = "Player"):
        self.name = name
        self.order = 0
        self.isrollingdice = False
        self.abilities = 0
        self.bank = 3                  # Everyone starts with 3 coins
        self.deck = PlayerDeck(self)
        self.hasTrainStation = False
        self.hasShoppingMall = False
        self.hasAmusementPark = False
        self.hasRadioTower = False

    def isWinner(self):
        if self.hasAmusementPark and self.hasRadioTower and self.hasShoppingMall and self.hasTrainStation:
            return True
        else:
            return False

    def dieroll(self):
        self.isrollingdice = True
        isDoubles = False
        dice = self.chooseDice()
        if dice == 1:
            return random.randint(1,6), False
        elif dice == 2:
            a = random.randint(1,6)
            b = random.randint(1,6)
            if a == b:
                isDoubles = True
            else:
                isDoubles = False
            total = a + b
            return total, isDoubles
        else:
            return 7, False

    def chooseDice(self):
        return 1
    
    def chooseReroll(self):
        return False
    
    def chooseTarget(self, players: list):
        # Default: random choice
        valid_targets = [p for p in players if not p.isrollingdice]
        if valid_targets:
            return random.choice(valid_targets)
        return None

    def deposit(self, amount: int):
        self.bank += amount

    def deduct(self, amount: int):   # Deducts coins from player's account without going negative 
        if self.bank >= amount:
            deducted = amount
        else:
            deducted = self.bank
        self.bank -= deducted
        return deducted         # ...and returns the amount that was deducted, for payment purposes

    def buy(self, name: str, availableCards):
        card = None
        specials = self.checkRemainingUpgrades()
        # Check if the name passed in is on the card list or specials list
        for item in availableCards.deck:
            if item.name.lower() == name.lower():
                card = item
                break
            else:
                pass
        for item in specials:
            if item.name.lower() == name.lower():
                card = item
                break
            else:
                pass
        if isinstance(card, Card):
            if self.bank >= card.cost:
                self.deduct(card.cost)
                self.deck.append(card)
                card.owner = self
                print("{} bought a {} for {} coins, and now has {} coins.".format(self.name, card.name, card.cost, self.bank))
            else:
                print("Sorry: a {} costs {} and {} only has {}.".format(card.name, card.cost, self.name, self.bank))
                return
        if isinstance(card,(Red, Green, Blue, TVStation, Stadium, BusinessCenter)):
            availableCards.deck.remove(card)            
        elif isinstance(card, UpgradeCard):
            specials.remove(card)
            card.bestowPower()
        else:
            print("Sorry: we don't have anything called '{}'.".format(name))

    def checkRemainingUpgrades(self):
        upgrades = []
        #TODO should I just define a second Store() called Player.upgrades() and put these in Player.special.deck? 
        if not self.hasTrainStation:
            upgrades.append(UpgradeCard("Train Station"))
        if not self.hasShoppingMall:
            upgrades.append(UpgradeCard("Shopping Mall"))
        if not self.hasAmusementPark:
            upgrades.append(UpgradeCard("Amusement Park"))
        if not self.hasRadioTower:
            upgrades.append(UpgradeCard("Radio Tower"))
        return upgrades

    def swap(self, Card, otherPlayer, otherCard):
        Card.owner = otherPlayer
        otherCard.owner = self
        otherPlayer.deck.remove(otherCard)
        self.deck.append(otherCard)
        self.deck.remove(Card)
        otherPlayer.deck.append(Card)

class Human(Player): # TODO : make this more robust - type checking etc. 
    def chooseAction(self, availableCards):
        while True:
            action = input("[B]uy a card, [P]ass, or [S]how available cards? ").lower()
            if 'b' in action:
                return 'buy'
            elif 'p' in action:
                return 'pass'
            elif 's' in action:
                print("\n-=-= Available Cards =-=-")
                display(availableCards)
                continue
            else:
                print("Please enter B, P, or S.")
    
    def chooseCard(self, options=list):
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        else:
            cardname = utility.userChoice(options)
            return cardname 

    def chooseDice(self):
        dice = 1
        if self.hasTrainStation:
            while True:
                try:
                    dice = int(input("Roll [1] or [2] dice?  "))
                    if 1 <= dice <= 2:
                        break
                    else:
                        print("Sorry: please enter 1 or 2.")
                except ValueError:
                    print("Sorry: please enter 1 or 2.")
        return dice
    
    def chooseReroll(self):
        if self.hasRadioTower:
            choice = input("Use Radio Tower to re-roll? ([Y]es / [N]o) ")
            if "y" in choice.lower():
                return True
        return False
    
    def chooseTarget(self, players: list):
        valid_targets = [p for p in players if not p.isrollingdice]
        if not valid_targets:
            return None
        print("Choose a target player:")
        for i, player in enumerate(valid_targets):
            print("[{}] {} ({} coins)".format(i+1, player.name, player.bank))
        while True:
            try:
                choice = int(input("Your selection: "))
                if 1 <= choice <= len(valid_targets):
                    return valid_targets[choice - 1]
                else:
                    print("Invalid choice. Try again.")
            except ValueError:
                print("Please enter a number.")

class Bot(Player):
    def chooseAction(self, availableCards):
        # Bots always try to buy if they have enough money
        options = availableCards.names(maxcost=self.bank)
        if len(options) > 0:
            return 'buy'
        return 'pass'
    
    def chooseCard(self, options=list):
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        else:
            cardname = random.choice(options)
            return cardname

    def chooseDice(self): # Just rolls the most dice he can 
        if self.hasTrainStation:
            return 2
        else:
            return 1
    
    def chooseReroll(self):
        # Simple bot: re-roll if result is 1-4
        if self.hasRadioTower and hasattr(self, '_last_roll'):
            return self._last_roll < 5
        return False

class ThoughtfulBot(Bot):
    def chooseCard(self, options=list):
        if len(options) == 0:
            print("Can't buy anything.")
            return None
        else:
            upgrades = ["Radio Tower",
            "Amusement Park",
            "Shopping Mall",
            "Train Station"]
            earlycards = ["TV Station",
            "Business Center",
            "Stadium",
            "Forest",
            "Convenience Store",
            "Ranch",
            "Wheat Field",
            "Cafe",
            "Bakery"]
            latecards = ["Mine",
            "Furniture Factory",
            "Cheese Factory",
            "Family Restaurant",
            "Apple Orchard",
            "Fruit and Vegetable Market"]
            if self.hasTrainStation:
                preferences = upgrades + latecards + earlycards
            else:
                preferences = upgrades + earlycards
            for priority in preferences:
                if priority in options:
                    return priority
            return random.choice(options)

    def chooseDice(self):
        if not self.hasTrainStation:
            return 1
        else:
            return random.choice([1,2,2,2,2])


# === Define Class Card() === #
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
    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list, multiplies=None):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.multiplies = multiplies
        self.hitsOn = []
        self.hitsOn = hitsOn
        self.payer = 0         # Green cards always pay out from the bank (0)
        self.recipient = 1     # Green cards always pay to the die roller (1)

    def trigger(self, players: list):   # Green cards increment the owner's bank by the payout
        subtotal = 0
        if self.owner.isrollingdice:
            if not self.multiplies:
                payout_amount = self.payout
                # Shopping Mall adds +1 to convenience store payouts
                if self.owner.hasShoppingMall and self.name == "Convenience Store":
                    payout_amount += 1
                self.owner.deposit(payout_amount)
                print("{} pays out {} to {}.".format(self.name, payout_amount, self.owner.name))
            else:
                for card in self.owner.deck.deck:
                    if card.category == self.multiplies:
                        subtotal += 1
                    else:
                        pass
                print("{} has {} cards of type {}...".format(self.owner.name, subtotal, self.multiplies))
                amount = self.payout * subtotal
                print("{} pays out {} to {}.".format(self.name, amount, self.owner.name))
                self.owner.deposit(amount)
        else:
            print("{} didn't roll the dice - no payout from {}.".format(self.owner.name, self.name))

class Red(Card):
    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list):
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
        payout_amount = self.payout
        # Shopping Mall adds +1 to cafe and convenience store payouts
        if self.owner.hasShoppingMall and self.name in ["Cafe", "Family Restaurant", "Convenience Store"]:
            payout_amount += 1
        payout = dieroller.deduct(payout_amount)
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
    
    def trigger(self, players: list):
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
    
    def trigger(self, players: list):
        for person in players:
            if person.isrollingdice:
                dieroller = person
            else:
                pass
        if dieroller == self.owner:
            print("{} activates TV Station!".format(self.owner.name))
            target = dieroller.chooseTarget(players)
            if target:
                print("{} targets {}!".format(self.owner.name, target.name))
                payment = target.deduct(self.payout)
                dieroller.deposit(payment)
                print("{} collected {} coins from {}.".format(self.owner.name, payment, target.name))
            else:
                print("No valid targets for TV Station.")
        else:
            print("TV Station doesn't activate (not die roller's turn).")

class BusinessCenter(Card):
    def __init__(self, name="Business Center"):
        self.name = name
        self.category = 7
        self.cost = 8
        self.recipient = 3      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 4          # Business Center collects from one targeted player (4)
        self.payout = 0         # Payout is the ability to swap cards (!)
    
    def trigger(self, players: list):
        for person in players:
            if person.isrollingdice:
                dieroller = person
        if self.owner == dieroller:
            print("{} activates Business Center!".format(self.owner.name))
            # For bots, just give them coins since card swapping is complex
            if not isinstance(dieroller, Human):
                print("{} gets 5 coins (bot doesn't swap cards).".format(dieroller.name))
                dieroller.deposit(5)
            else:
                swap_choice = input("Do you want to swap cards? ([Y]es / [N]o) ")
                if "y" in swap_choice.lower():
                    target = dieroller.chooseTarget(players)
                    if target and len(target.deck.deck) > 0:
                        print("Choose your card to give away:")
                        my_cards = [c for c in dieroller.deck.deck if not isinstance(c, UpgradeCard)]
                        their_cards = [c for c in target.deck.deck if not isinstance(c, UpgradeCard)]
                        if my_cards and their_cards:
                            my_card = utility.userChoice([c.name for c in my_cards])
                            my_card_obj = [c for c in my_cards if c.name == my_card][0]
                            print("Choose {}'s card to take:".format(target.name))
                            their_card = utility.userChoice([c.name for c in their_cards])
                            their_card_obj = [c for c in their_cards if c.name == their_card][0]
                            dieroller.swap(my_card_obj, target, their_card_obj)
                            print("Swapped {} for {}'s {}.".format(my_card, target.name, their_card))
                        else:
                            print("Not enough swappable cards.")
                    else:
                        print("No valid swap target.")
        else:
            print("Business Center doesn't activate (not die roller's turn).")

class UpgradeCard(Card):
    def __init__(self, name):
        # TODO: perfect example of when to do @class attribs, I think 
        self.orangeCards = {
            "Train Station" : [4, 7, "hasTrainStation"],
            "Shopping Mall" : [10, 7, "hasShoppingMall"],
            "Amusement Park" : [16, 7, "hasAmusementPark"],
            "Radio Tower" : [22, 7, "hasRadioTower"]
        }
        self.name = name
        self.cost = self.orangeCards[name][0]
        self.category = self.orangeCards[name][1]
        self.owner = None
        self.hitsOn = [99] # For sorting purposes these cards should be listed last among a player's assets, with a number that can never be rolled 

    def bestowPower(self):
        setattr(self.owner, self.orangeCards[self.name][2], True)
        # print("DEBUG: bestowed a Special Power!!")
        # print("{} now {}".format(self.owner.name, self.orangeCards[self.name][2]))

# "Stores" are wrappers for a deck[] list and a few functions; decks hold Card objects
class Store(object):
    def __init__(self):
        self.deck = []
        self.frequencies = {}

    def names(self, maxcost=99, flavor=Card): # A de-duplicated list of the available names
        namelist = []
        for card in self.deck:
            if (card.name not in namelist) and isinstance(card, flavor) and (card.cost <= maxcost): # TODO: target hitsOn?
                namelist.append(card.name)
            else:
                pass
        return namelist

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
            self.append(Green("Cheese Factory",6,5,3,[7],2))
            self.append(Green("Furniture Factory",6,3,3,[8],5))
            self.append(Blue("Mine",5,6,5,[9]))
            self.append(Red("Family Restaurant",4,3,2,[9,10]))
            self.append(Blue("Apple Orchard",1,3,3,[10]))
            self.append(Green("Fruit and Vegetable Market",8,2,2,[11,12],1))
        self.append(TVStation())
        self.append(BusinessCenter())
        self.append(Stadium())
        self.deck.sort() 
        
# The UniqueDeck will replenish the TableDeck so players are only 
# ever offered one copy of cards they can't buy twice
class UniqueDeck(Store):
    def __init__(self, players: list):
        self.deck = []
        self.frequencies = {}
        for _ in range(0, len(players)+1):
            self.append(TVStation())
            self.append(BusinessCenter())
            self.append(Stadium())
            self.append(UpgradeCard("Train Station"))
            self.append(UpgradeCard("Shopping Mall"))
            self.append(UpgradeCard("Amusement Park"))
            self.append(UpgradeCard("Radio Tower"))
        self.deck.sort()

# ==== Define top-level game functions ====
def setPlayers(players=None, bots=0, humans=0):
    playerlist = []
    if bots > 0 or humans > 0:
        total = bots + humans
        if total < 2:
            print("Need at least 2 players. Adding a bot.")
            bots += 2 - total
        elif total > 4:
            print("Maximum 4 players. Trimming bots.")
            bots = max(0, 4 - humans)
        for i in range(humans):
            playerlist.append(Human(name="Player{}".format(i + 1)))
        for i in range(bots):
            playerlist.append(ThoughtfulBot(name="Robo{}".format(i)))
        return playerlist
    elif players is None:
        moreplayers = True
        while moreplayers:
            humanorbot = input("Add a [H]uman or add a [B]ot? ")
            if "h" in humanorbot.lower():
                playername = input("What's the human's name? ")            
                playerlist.append(Human(name=str(playername)))
            elif "b" in humanorbot.lower():
                playername = input("What's the bot's name? ")
                if playername[0] == "T":
                    playerlist.append(ThoughtfulBot(name=str(playername)))
                else:
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
    elif isinstance(players, int):
        if players < 2:
            players = 2
        elif players > 4:
            players = 4
    else:
        print("Unexpected variable for `players` in call to setPlayers()")
        return
    
    if players >=2 and players <= 4:
        for num in range(players):
            playerlist.append(Bot(name=str("Robo" + str(num))))
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

def newGame(players=None, bots=0, humans=0):
    availableCards = TableDeck()
    playerlist = setPlayers(players, bots=bots, humans=humans)
    specialCards = UniqueDeck(playerlist)
    return availableCards, specialCards, playerlist

def nextTurn(playerlist: list, player, availableCards, specialCards):
    # Reset the turn counter; start a new turn
    for person in playerlist:
        person.isrollingdice = False
    player.isrollingdice = True
    isDoubles = False

    # Refresh purchase options
    # If the player has a copy of the unique cards, don't present them as options
    for card in specialCards.deck:
        # print("DEBUG: current player is {}".format(player.name))
        # print("DEBUG: player card list is {}".format(player.deck.names()))
        # print("DEBUG: checking if {} is here...".format(card.name))
        if (card.name not in player.deck.names()) and (card.name in availableCards.names()):
            pass
            # print("DEBUG: the {} is still for sale.".format(card.name))
        elif (card.name not in player.deck.names()) and (card.name not in availableCards.names()):
            # print("DEBUG: didn't find a {} for sale or in player deck".format(card.name))
            availableCards.append(card)
            specialCards.remove(card)
        elif (card.name in player.deck.names()) and (card.name in availableCards.names()):
            # print("DEBUG: Shouldn't offer the player a {}".format(card.name))
            availableCards.remove(card)
            specialCards.append(card)
        elif (card.name in player.deck.names()) and (card.name not in availableCards.names()):
            pass
            # print("DEBUG: {} is correctly off the market.".format(card.name))
        else:
            print("WARN: Somehow left the truth table")
            pass

    # TODO: consider refactoring to a player-specific PlayerOptions 
    # deck with orange and purple cards, and then just updating it
    # and adding it to availableCards each turn 

    # Die Rolling Phase 
    print("-=-=-= It's {}'s turn =-=-=-".format(player.name))
    dieroll, isDoubles = player.dieroll()
    print("{} rolled a {}.".format(player.name, dieroll))
    
    # Radio Tower re-roll option
    player._last_roll = dieroll  # Store for bot decision-making
    if player.chooseReroll():
        print("{} uses the Radio Tower to re-roll!".format(player.name))
        dieroll, isDoubles = player.dieroll()
        print("{} rolled a {}.".format(player.name, dieroll))
    for person in playerlist:
        for card in person.deck.deck:
            if dieroll in card.hitsOn:
                print("{}'s {} activates on a {}...".format(person.name, card.name, dieroll))
                card.trigger(playerlist) # TODO: integrate order of parsing

    # Buy Phase 
    for person in playerlist:
        print("{} now has {} coins.".format(person.name, person.bank))
    print("-=-=-={}'s Deck=-=-=-".format(player.name))
    display(player.deck)
    
    action = player.chooseAction(availableCards)
    if action == 'buy':
        options = availableCards.names(maxcost=player.bank)
        cardname = player.chooseCard(options)
        if cardname is not None:
            player.buy(cardname, availableCards)
    elif action == 'pass':
        print("{} passes this turn.".format(player.name))
    
    return isDoubles

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
    # TODO: Eventually add "buffer=True" to suppress stdout
    # Pull in command-line input 
    parser = argparse.ArgumentParser(description='The card game Machi Koro')
    parser.add_argument('-t', '--test', dest='unittests', action='store_true', required=False, help='run unit tests instead of executing the game code')
    parser.add_argument('--bots', type=int, default=0, metavar='N', help='number of bot players (skips interactive setup)')
    parser.add_argument('--humans', type=int, default=0, metavar='N', help='number of human players (skips interactive setup)')
    args = parser.parse_args()
    availableCards, specialCards, playerlist = newGame(bots=args.bots, humans=args.humans)
    noWinnerYet = True
    while noWinnerYet:
        for turntaker in playerlist:
            isDoubles = nextTurn(playerlist, turntaker, availableCards, specialCards)
            if turntaker.isWinner():
                noWinnerYet = False
                print("{} wins!".format(turntaker.name))
                exit()
            else:
                pass
            # Amusement Park: extra turn on doubles
            while isDoubles and turntaker.hasAmusementPark:
                print("{} rolled doubles and gets to go again!".format(turntaker.name))
                isDoubles = nextTurn(playerlist, turntaker, availableCards, specialCards)
                if turntaker.isWinner():
                    noWinnerYet = False
                    print("{} wins!".format(turntaker.name))
                    exit()
            
   
if __name__ == "__main__":
    main()