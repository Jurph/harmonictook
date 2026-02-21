#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# harmonictook.py - Main game file

from __future__ import annotations

import random
import utility
import argparse
from functools import total_ordering

class Player(object):
    """Base class for all players; holds bank, deck, and upgrade flags."""

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

    def isWinner(self) -> bool:
        """Return True if the player holds all four upgrade cards."""
        if self.hasAmusementPark and self.hasRadioTower and self.hasShoppingMall and self.hasTrainStation:
            return True
        else:
            return False

    def dieroll(self) -> tuple[int, bool]:
        """Roll dice as determined by chooseDice(); return (total, isDoubles)."""
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

    def chooseDice(self) -> int:
        """Return the number of dice to roll; base implementation always returns 1."""
        return 1

    def chooseReroll(self) -> bool:
        """Return True if the player wants to use the Radio Tower to re-roll; base always returns False."""
        return False

    def chooseTarget(self, players: list) -> Player | None:
        """Return a randomly selected non-rolling player to target, or None if no valid targets."""
        # Default: random choice
        valid_targets = [p for p in players if not p.isrollingdice]
        if valid_targets:
            return random.choice(valid_targets)
        return None

    def deposit(self, amount: int) -> None:
        """Add amount coins to the player's bank."""
        self.bank += amount

    def deduct(self, amount: int) -> int:
        """Deduct up to amount coins (never below zero); return the coins actually taken."""
        if self.bank >= amount:
            deducted = amount
        else:
            deducted = self.bank
        self.bank -= deducted
        return deducted         # ...and returns the amount that was deducted, for payment purposes

    def buy(self, name: str, availableCards: Store) -> None:
        """Purchase the named card from availableCards (or upgrades list) if affordable."""
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
                print(f"{self.name} bought a {card.name} for {card.cost} coins, and now has {self.bank} coins.")
            else:
                print(f"Sorry: a {card.name} costs {card.cost} and {self.name} only has {self.bank}.")
                return
        if isinstance(card,(Red, Green, Blue, TVStation, Stadium, BusinessCenter)):
            availableCards.deck.remove(card)
        elif isinstance(card, UpgradeCard):
            specials.remove(card)
            card.bestowPower()
        else:
            print(f"Sorry: we don't have anything called '{name}'.")

    def checkRemainingUpgrades(self) -> list:
        """Return a list of UpgradeCard objects for upgrades this player has not yet purchased."""
        upgrades = []
        if not self.hasTrainStation:
            upgrades.append(UpgradeCard("Train Station"))
        if not self.hasShoppingMall:
            upgrades.append(UpgradeCard("Shopping Mall"))
        if not self.hasAmusementPark:
            upgrades.append(UpgradeCard("Amusement Park"))
        if not self.hasRadioTower:
            upgrades.append(UpgradeCard("Radio Tower"))
        return upgrades

    def swap(self, card: Card, otherPlayer: Player, otherCard: Card) -> None:
        """Exchange card with otherPlayer's otherCard, updating ownership and decks."""
        card.owner = otherPlayer
        otherCard.owner = self
        otherPlayer.deck.remove(otherCard)
        self.deck.append(otherCard)
        self.deck.remove(card)
        otherPlayer.deck.append(card)

class Human(Player):
    """Interactive player subclass that prompts for all decisions via stdin."""

    def chooseAction(self, availableCards: Store) -> str:
        """Prompt the human for a turn action; returns 'buy' or 'pass'."""
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

    def chooseCard(self, options: list, market=None) -> str | None:
        """Prompt the human to pick a card; shows a rich table when market is supplied."""
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        if market is not None:
            cards = [next(c for c in market.deck if c.name == name) for name in options]
            return utility.card_menu(cards)
        return utility.userChoice(options)

    def chooseDice(self) -> int:
        """Prompt the human (if they own Train Station) to choose 1 or 2 dice; default is 1."""
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

    def chooseReroll(self) -> bool:
        """Prompt the human to use the Radio Tower re-roll if they own it; returns their decision."""
        if self.hasRadioTower:
            choice = input("Use Radio Tower to re-roll? ([Y]es / [N]o) ")
            if "y" in choice.lower():
                return True
        return False

    def chooseTarget(self, players: list) -> Player | None:
        """Prompt the human to pick a target from non-rolling players; returns the chosen player or None."""
        valid_targets = [p for p in players if not p.isrollingdice]
        if not valid_targets:
            return None
        print("Choose a target player:")
        for i, player in enumerate(valid_targets):
            print(f"[{i+1}] {player.name} ({player.bank} coins)")
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
    """Simple automated player that buys affordable cards at random."""

    def chooseAction(self, availableCards: Store) -> str:
        """Return 'buy' if any affordable card is available, otherwise 'pass'."""
        # Bots always try to buy if they have enough money
        options = availableCards.names(maxcost=self.bank)
        if len(options) > 0:
            return 'buy'
        return 'pass'

    def chooseCard(self, options: list, market=None) -> str | None:
        """Return a randomly selected card name from options, or None if the list is empty."""
        if len(options) == 0:
            print("Oh no - no valid purchase options this turn.")
            return None
        return random.choice(options)

    def chooseDice(self) -> int:
        """Return 2 if the bot owns Train Station, otherwise 1."""
        if self.hasTrainStation:
            return 2
        else:
            return 1

    def chooseReroll(self) -> bool:
        """Return True if the bot owns Radio Tower and the last roll was below 5."""
        # Simple bot: re-roll if result is 1-4
        if self.hasRadioTower and hasattr(self, '_last_roll'):
            return self._last_roll < 5
        return False

class ThoughtfulBot(Bot):
    """Priority-driven bot that follows a fixed card-preference ordering."""

    def chooseCard(self, options: list, market=None) -> str | None:
        """Return the highest-priority card name available in options per the bot's preference list."""
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
            "Fruit & Vegetable Market"]
            if self.hasTrainStation:
                preferences = upgrades + latecards + earlycards
            else:
                preferences = upgrades + earlycards
            for priority in preferences:
                if priority in options:
                    return priority
            return random.choice(options)

    def chooseDice(self) -> int:
        """Return 1 without Train Station; with it, randomly favour 2 dice (4:1 odds)."""
        if not self.hasTrainStation:
            return 1
        else:
            return random.choice([1,2,2,2,2])


def get_die_roller(players: list) -> Player:
    """Return the player whose isrollingdice flag is True, or raise ValueError if none."""
    for person in players:
        if person.isrollingdice:
            return person
    raise ValueError("No player is currently rolling the dice")


# === Define Class Card() === #
# Cards must have a name, cost, a payer, a payout amount, and one or more die rolls on which they "hit"
@total_ordering
class Card(object):
    """Abstract base card; subclasses define payer/recipient logic and trigger behaviour."""

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

    def describe(self) -> str:
        """Return a plain-English description of this card's effect for display in purchase menus."""
        return ""

    def sortvalue(self) -> float:
        """Return a float used for stable deck ordering: mean hitsOn, then cost, then name."""
        from statistics import mean
        value = 0.000
        value += mean(self.hitsOn)   # Sort by mean hit value
        value += self.cost/100                  # Then by cost
        value += ord(str(self.name)[0])/255     # Then by pseudo-alphabetical
        return value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.sortvalue() == other.sortvalue()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.sortvalue() < other.sortvalue()

    def __hash__(self) -> int:
        return hash((self.name, self.category, self.cost))

    def __str__(self) -> str:
        categories = {1:"|🌽|", 2:"|🐄|", 3:"|🏪|", 4:"|☕|", 5:"|⚙️| ", 6:"|🏭|", 7:"|🗼|", 8:"|🍎|"}
        # WARNING: In Unicode, the "gear" emoji is decorated with U+FE0F, an invisible zero-space
        # codepoint. Its full name is 'U+2699 U+FE0F'. Calls to format() double-count it when
        # trying to do fixed width. Adding a space for padding and telling format() to display it
        # as single-width seems to work. There probably are other solutions, but this one works.
        catvalue = self.category
        cardstring = f"{str(self.hitsOn):7} {categories[catvalue]:3} : {self.name:16}"
        return cardstring

class Green(Card):
    """Green card: pays the bank → die-roller on their own turn; optionally multiplies by category count."""

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

    _category_names = {1: "Grain", 2: "Ranch", 3: "Bakery", 4: "Café",
                       5: "Gear", 6: "Factory", 7: "Major", 8: "Fruit"}

    def describe(self) -> str:
        """Describe this Green card's effect; factory cards name the category they multiply."""
        if self.multiplies:
            cat = self._category_names.get(self.multiplies, f"cat-{self.multiplies}")
            return f"Pays {self.payout} coin(s) per {cat} card you own, on your roll"
        suffix = " (+1 with Shopping Mall)" if self.name == "Convenience Store" else ""
        return f"Pays {self.payout} coin(s) from bank when you roll{suffix}"

    def trigger(self, players: list) -> None:
        """Pay the die-roller from the bank if it is their turn; factory cards multiply by matching category count."""
        subtotal = 0
        if self.owner.isrollingdice:
            if not self.multiplies:
                payout_amount = self.payout
                # Shopping Mall adds +1 to convenience store payouts
                if self.owner.hasShoppingMall and self.name == "Convenience Store":
                    payout_amount += 1
                self.owner.deposit(payout_amount)
                print(f"{self.name} pays out {payout_amount} to {self.owner.name}.")
            else:
                for card in self.owner.deck.deck:
                    if card.category == self.multiplies:
                        subtotal += 1
                    else:
                        pass
                print(f"{self.owner.name} has {subtotal} cards of type {self.multiplies}...")
                amount = self.payout * subtotal
                print(f"{self.name} pays out {amount} to {self.owner.name}.")
                self.owner.deposit(amount)
        else:
            print(f"{self.owner.name} didn't roll the dice - no payout from {self.name}.")

class Red(Card):
    """Red card: steals coins from the die-roller and gives them to the card owner."""

    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn
        self.payer = 1          # Red cards pay out from the die-roller (1)
        self.recipient = 3      # Red cards pay to the card owner (3)

    def describe(self) -> str:
        """Describe this Red card's steal effect; notes Shopping Mall bonus where applicable."""
        suffix = " (+1 with Shopping Mall)" if self.name in ("Cafe", "Family Restaurant") else ""
        return f"Steals {self.payout} coin(s) from the roller on their turn{suffix}"

    def trigger(self, players: list) -> None:
        """Deduct payout coins from the die-roller and deposit them with the card owner."""
        dieroller = get_die_roller(players)
        payout_amount = self.payout
        # Shopping Mall adds +1 to cafe and convenience store payouts
        if self.owner.hasShoppingMall and self.name in ["Cafe", "Family Restaurant", "Convenience Store"]:
            payout_amount += 1
        payout = dieroller.deduct(payout_amount)
        self.owner.deposit(payout)

class Blue(Card):
    """Blue card: pays the bank → card owner regardless of who rolled the dice."""

    def __init__(self, name=str, category=int, cost=int, payout=int, hitsOn=list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn
        self.payer = 0          # Blue cards pay out fromm the bank (0)
        self.recipient = 3      # Blue cards pay out to the card owner (3)

    def describe(self) -> str:
        """Describe this Blue card's passive income effect."""
        return f"Pays {self.payout} coin(s) to owner on any player's roll"

    def trigger(self, players: list) -> None:
        """Deposit payout coins from the bank into the card owner's account."""
        print(f"{self.name} pays out {self.payout} to {self.owner.name}.")
        self.owner.deposit(self.payout)

class Stadium(Card):
    """Purple card: on a 6, collects 2 coins from every player for the die-roller."""

    def __init__(self, name="Stadium"):
        self.name = name
        self.category = 7
        self.cost = 6
        self.recipient = 3      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 2          # Stadium collects from all players
        self.payout = 2

    def describe(self) -> str:
        return f"Collect {self.payout} coins from EACH player when you roll 6"

    def trigger(self, players: list) -> None:
        """Collect 2 coins from each player and deposit them with the die-roller."""
        dieroller = get_die_roller(players)
        for person in players:
            payment = person.deduct(self.payout)
            dieroller.deposit(payment)

class TVStation(Card):
    """Purple card: on a 6, lets the owner steal 5 coins from a chosen target player."""

    def __init__(self, name="TV Station"):
        self.name = name
        self.category = 7
        self.cost = 7
        self.recipient = 1      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 4          # TV Station collects from one player
        self.payout = 5

    def describe(self) -> str:
        return f"Steal {self.payout} coins from a chosen player when you roll 6"

    def trigger(self, players: list) -> None:
        """If the owner is the die-roller, steal up to 5 coins from a chosen target."""
        dieroller = get_die_roller(players)
        if dieroller == self.owner:
            print(f"{self.owner.name} activates TV Station!")
            target = dieroller.chooseTarget(players)
            if target:
                print(f"{self.owner.name} targets {target.name}!")
                payment = target.deduct(self.payout)
                dieroller.deposit(payment)
                print(f"{self.owner.name} collected {payment} coins from {target.name}.")
            else:
                print("No valid targets for TV Station.")
        else:
            print("TV Station doesn't activate (not die roller's turn).")

class BusinessCenter(Card):
    """Purple card: on a 6, lets the owner swap a card with another player (bots get 5 coins instead)."""

    def __init__(self, name="Business Center"):
        self.name = name
        self.category = 7
        self.cost = 8
        self.recipient = 3      # Purple cards pay out to the die-roller (1)
        self.hitsOn = [6]       # Purple cards all hit on [6]
        self.payer = 4          # Business Center collects from one targeted player (4)
        self.payout = 0         # Payout is the ability to swap cards (!)

    def describe(self) -> str:
        return "Swap one of your cards with any player's card when you roll 6"

    def trigger(self, players: list) -> None:
        """If the owner is the die-roller, swap a card with a target (or give the bot 5 coins)."""
        dieroller = get_die_roller(players)
        if self.owner == dieroller:
            print(f"{self.owner.name} activates Business Center!")
            # For bots, just give them coins since card swapping is complex
            if not isinstance(dieroller, Human):
                print(f"{dieroller.name} gets 5 coins (bot doesn't swap cards).")
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
                            print(f"Choose {target.name}'s card to take:")
                            their_card = utility.userChoice([c.name for c in their_cards])
                            their_card_obj = [c for c in their_cards if c.name == their_card][0]
                            dieroller.swap(my_card_obj, target, their_card_obj)
                            print(f"Swapped {my_card} for {target.name}'s {their_card}.")
                        else:
                            print("Not enough swappable cards.")
                    else:
                        print("No valid swap target.")
        else:
            print("Business Center doesn't activate (not die roller's turn).")

class UpgradeCard(Card):
    """Orange landmark card that grants a permanent ability when purchased."""

    orangeCards = {
        "Train Station" : [4, 7, "hasTrainStation"],
        "Shopping Mall" : [10, 7, "hasShoppingMall"],
        "Amusement Park" : [16, 7, "hasAmusementPark"],
        "Radio Tower" : [22, 7, "hasRadioTower"]
    }

    def __init__(self, name: str):
        self.name = name
        self.cost = self.orangeCards[name][0]
        self.category = self.orangeCards[name][1]
        self.owner = None
        self.hitsOn = [99]  # For sorting purposes these cards should be listed last among a player's assets, with a number that can never be rolled

    _descriptions = {
        "Train Station":  "Roll 1 or 2 dice on your turn",
        "Shopping Mall":  "+1 coin from Cafes, Restaurants, and Convenience Stores",
        "Amusement Park": "Roll doubles -> take an extra turn",
        "Radio Tower":    "Once per turn, reroll your dice",
    }

    def describe(self) -> str:
        return self._descriptions.get(self.name, "")

    def bestowPower(self) -> None:
        """Set the corresponding boolean flag on the owner to activate this upgrade's ability."""
        setattr(self.owner, self.orangeCards[self.name][2], True)

# "Stores" are wrappers for a deck[] list and a few functions; decks hold Card objects
class Store(object):
    """Generic sorted collection of Card objects with query and mutation helpers."""

    def __init__(self):
        self.deck = []
        self.frequencies = {}

    def names(self, maxcost: int = 99, flavor: type = Card) -> list:
        """Return a de-duplicated list of card names with cost ≤ maxcost and matching flavor type."""
        namelist = []
        for card in self.deck:
            if (card.name not in namelist) and isinstance(card, flavor) and (card.cost <= maxcost):
                namelist.append(card.name)
            else:
                pass
        return namelist

    def freq(self) -> dict:
        """Return a {card: count} dict of card occurrences and cache it in self.frequencies."""
        f = {}
        for card in self.deck:
            if f.get(card):
                f[card] += 1
            else:
                f[card] = 1
        self.frequencies = f
        return self.frequencies

    def append(self, card: Card) -> None:
        """Add card to the deck and re-sort; silently ignore non-Card objects."""
        if isinstance(card, Card):
            self.deck.append(card)
            self.deck.sort()
        else:
            TypeError()

    def remove(self, card: Card) -> None:
        """Remove card from the deck and re-sort; silently ignore non-Card objects."""
        if isinstance(card, Card):
            self.deck.remove(card)
            self.deck.sort()
        else:
            TypeError()

class PlayerDeck(Store):
    """A player's personal card collection; pre-loaded with Wheat Field and Bakery."""

    def __init__(self, owner):
        self.deck = []
        self.frequencies = {}
        self.owner = owner
        self.deck.append(Blue("Wheat Field",1,1,1,[1]))
        self.deck.append(Green("Bakery",3,1,1,[2,3]))
        for card in self.deck:
            card.owner = self.owner

    def __str__(self) -> str:
        decktext = ""
        for card in self.deck:
            if isinstance(card, (Red, Green, Blue)):
                decktext += f"{card.hitsOn} - {card.name}\n"
            else:
                decktext += str(card)
        return decktext

class TableDeck(Store):
    """The shared market; populated with six copies of each standard card plus one of each purple card."""

    def __init__(self):
        self.deck = []
        self.frequencies = {}
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
            self.append(Green("Fruit & Vegetable Market",8,2,2,[11,12],1))
        self.append(TVStation())
        self.append(BusinessCenter())
        self.append(Stadium())
        self.deck.sort()

# The UniqueDeck will replenish the TableDeck so players are only
# ever offered one copy of cards they can't buy twice
class UniqueDeck(Store):
    """Reserve pool of purple and orange cards used to replenish the TableDeck each turn."""

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
def setPlayers(players=None, bots: int = 0, humans: int = 0) -> list:
    """Build and return the player list from explicit counts, an integer, or interactive prompts."""
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
            playerlist.append(Human(name=f"Player{i + 1}"))
        for i in range(bots):
            playerlist.append(ThoughtfulBot(name=f"Robo{i}"))
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

def display(deckObject: Store) -> None:
    """Print a formatted frequency table for the given Store's cards."""
    f = deckObject.freq()
    rowstring = ""
    for card, quantity in f.items():
        rowstring += f"{str(card) + '|':16}"
        for _ in range(quantity):
            rowstring += "[]"
        rowstring += f"{quantity}\n"
    print(rowstring)

class Game:
    """Encapsulates all state and logic for a single Machi Koro game."""

    def __init__(self, players=None, bots: int = 0, humans: int = 0):
        """Set up players, market, and reserve for a new game."""
        self.players: list = setPlayers(players, bots=bots, humans=humans)
        self.market: TableDeck = TableDeck()
        self.reserve: UniqueDeck = UniqueDeck(self.players)
        self.current_player_index: int = 0
        self.turn_number: int = 0
        self.last_roll: int | None = None
        self.winner: Player | None = None

    def get_current_player(self) -> Player:
        """Return the player whose turn it currently is."""
        return self.players[self.current_player_index]

    def get_purchase_options(self) -> list:
        """Return card names in the market affordable by the current player."""
        return self.market.names(maxcost=self.get_current_player().bank)

    def refresh_market(self) -> None:
        """Sync unique cards between reserve and market based on the current player's holdings."""
        player = self.get_current_player()
        for card in self.reserve.deck:
            if (card.name not in player.deck.names()) and (card.name in self.market.names()):
                pass
            elif (card.name not in player.deck.names()) and (card.name not in self.market.names()):
                self.market.append(card)
                self.reserve.remove(card)
            elif (card.name in player.deck.names()) and (card.name in self.market.names()):
                self.market.remove(card)
                self.reserve.append(card)
            elif (card.name in player.deck.names()) and (card.name not in self.market.names()):
                pass
            else:
                print("WARN: Somehow left the truth table")

    def next_turn(self) -> bool:
        """Execute one full turn for the current player; return isDoubles."""
        player = self.get_current_player()

        # Reset isrollingdice flags; mark the active player
        for person in self.players:
            person.isrollingdice = False
        player.isrollingdice = True
        isDoubles = False

        self.refresh_market()

        # Die Rolling Phase
        print(f"-=-=-= It's {player.name}'s turn =-=-=-")
        dieroll, isDoubles = player.dieroll()
        self.last_roll = dieroll
        print(f"{player.name} rolled a {dieroll}.")

        # Radio Tower re-roll option
        player._last_roll = dieroll
        if player.chooseReroll():
            print(f"{player.name} uses the Radio Tower to re-roll!")
            dieroll, isDoubles = player.dieroll()
            self.last_roll = dieroll
            print(f"{player.name} rolled a {dieroll}.")

        # Card triggers in correct color order: Red → Blue → Green → Purple
        for card_color in [Red, Blue, Green, Stadium, TVStation, BusinessCenter]:
            for person in self.players:
                for card in person.deck.deck:
                    if dieroll in card.hitsOn and isinstance(card, card_color):
                        print(f"{person.name}'s {card.name} activates on a {dieroll}...")
                        card.trigger(self.players)

        # Buy Phase
        for person in self.players:
            print(f"{person.name} now has {person.bank} coins.")
        print(f"-=-=-={player.name}'s Deck=-=-=-")
        display(player.deck)

        action = player.chooseAction(self.market)
        if action == 'buy':
            options = self.market.names(maxcost=player.bank)
            cardname = player.chooseCard(options, self.market)
            if cardname is not None:
                player.buy(cardname, self.market)
        elif action == 'pass':
            print(f"{player.name} passes this turn.")

        self.turn_number += 1
        return isDoubles

    def run(self) -> None:
        """Run the game loop until a player wins."""
        no_winner_yet = True
        while no_winner_yet:
            for i, turntaker in enumerate(self.players):
                self.current_player_index = i
                is_doubles = self.next_turn()
                if turntaker.isWinner():
                    no_winner_yet = False
                    self.winner = turntaker
                    print(f"{turntaker.name} wins!")
                    return
                while is_doubles and turntaker.hasAmusementPark:
                    print(f"{turntaker.name} rolled doubles and gets to go again!")
                    is_doubles = self.next_turn()
                    if turntaker.isWinner():
                        no_winner_yet = False
                        self.winner = turntaker
                        print(f"{turntaker.name} wins!")
                        return


def main():
    parser = argparse.ArgumentParser(description='The card game Machi Koro')
    parser.add_argument('-t', '--test', dest='unittests', action='store_true', required=False, help='run unit tests instead of executing the game code')
    parser.add_argument('--bots', type=int, default=0, metavar='N', help='number of bot players (skips interactive setup)')
    parser.add_argument('--humans', type=int, default=0, metavar='N', help='number of human players (skips interactive setup)')
    args = parser.parse_args()
    game = Game(bots=args.bots, humans=args.humans)
    game.run()


if __name__ == "__main__":
    main()
