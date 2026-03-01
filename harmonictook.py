#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# harmonictook.py - Main game file

from __future__ import annotations

import random
import utility
import argparse
from functools import total_ordering
from dataclasses import dataclass
from abc import ABC, abstractmethod
from statistics import mean
from typing import Literal


EventType = Literal[
    "turn_start", "roll", "reroll", "card_activates",
    "payout", "payout_skip", "factory_count",
    "steal", "steal_activate", "steal_target", "steal_no_target", "steal_skip",
    "collect", "bc_activate", "bc_bot_payout", "bc_swap", "bc_no_cards", "bc_no_target", "bc_skip",
    "bank_status", "deck_state", "buy", "buy_failed", "buy_not_found",
    "pass", "win", "doubles_bonus",
]


@dataclass
class Event:
    """A discrete game occurrence passed from logic to a Display renderer."""
    type: EventType
    player: str = ""        # primary player name
    card: str = ""          # card name
    target: str = ""        # target player name (steals, swaps)
    value: int = 0          # die value, payout amount, or cost
    is_doubles: bool = False
    card_type: int = 0      # category int for factory_count events
    message: str = ""       # fallback / pre-formatted text
    remaining_bank: int = 0 # player's bank after a buy or failed buy


@dataclass
class PlayerSnapshot:
    """A lightweight snapshot of one player's state captured after a turn."""
    name: str
    bank: int
    landmarks: int      # count of completed landmark buildings (0–4)
    cards: int          # non-landmark cards in deck (engine size)


@dataclass
class GameState:
    """A snapshot of the full game state after one completed turn."""
    turn_number: int
    active_player: str
    roll: int | None            # final die result for this turn (post-reroll if any)
    players: list[PlayerSnapshot]
    events: list[Event]         # full event log for this turn


class Player(object):
    """Base class for all players; holds bank, deck, and upgrade flags."""

    def __init__(self, name: str = "Player"):
        self.name = name
        self.isrollingdice = False
        self.bank = 3                  # Everyone starts with 3 coins
        self.deck = PlayerDeck(self)
        self.hasTrainStation = False
        self.hasShoppingMall = False
        self.hasAmusementPark = False
        self.hasRadioTower = False

    def isWinner(self) -> bool:
        """Return True if the player holds all four upgrade cards."""
        return self.hasAmusementPark and self.hasRadioTower and self.hasShoppingMall and self.hasTrainStation

    def dieroll(self, players: list | None = None) -> tuple[int, bool]:
        """Roll dice as determined by chooseDice(); return (total, isDoubles)."""
        isDoubles = False
        dice = self.chooseDice(players)
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
            raise ValueError(f"chooseDice() must return 1 or 2, got {dice}")

    def chooseDice(self, players: list | None = None) -> int:
        """Return 2 if Train Station is owned, otherwise 1."""
        return 2 if self.hasTrainStation else 1

    def chooseReroll(self, last_roll: int | None = None) -> bool:
        """Return True if the player wants to use the Radio Tower to re-roll; base always returns False."""
        return False

    def chooseAction(self, availableCards: Store) -> str:
        """Choose a turn action; subclasses must implement this method."""
        raise NotImplementedError

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Choose a card to buy; subclasses must implement this method."""
        raise NotImplementedError

    def chooseTarget(self, players: list[Player]) -> Player | None:
        """Return a randomly selected non-rolling player to target, or None if no valid targets."""
        # Default: random choice
        valid_targets = [p for p in players if not p.isrollingdice]
        if valid_targets:
            return random.choice(valid_targets)
        return None

    def chooseBusinessCenterSwap(
        self, target: Player, my_swappable: list, their_swappable: list
    ) -> tuple[Card, Card] | None:
        """Choose which card to give and which to take when activating Business Center.
        Subclasses implement their own workflow (e.g. bot heuristic, CLI prompts, or GUI
        "click opponent then choose cards"). Default: decline (return None)."""
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
        return deducted

    def buy(self, name: str, availableCards: Store) -> list[Event]:
        """Purchase the named card from availableCards (or upgrades list) if affordable."""
        events: list[Event] = []
        card = None
        specials = self.checkRemainingUpgrades()
        # Check if the name passed in is on the card list or specials list
        for item in availableCards.deck:
            if item.name.lower() == name.lower():
                card = item
                break
        for item in specials:
            if item.name.lower() == name.lower():
                card = item
                break
        if isinstance(card, Card):
            if self.bank >= card.cost:
                self.deduct(card.cost)
                self.deck.append(card)
                card.owner = self
                events.append(Event(type="buy", player=self.name, card=card.name, value=card.cost, remaining_bank=self.bank))
            else:
                events.append(Event(type="buy_failed", player=self.name, card=card.name, value=card.cost, remaining_bank=self.bank))
                return events
        if isinstance(card, (Red, Green, Blue, TVStation, Stadium, BusinessCenter)):
            availableCards.deck.remove(card)
        elif isinstance(card, UpgradeCard):
            card.bestowPower()
        else:
            events.append(Event(type="buy_not_found", card=name))
        return events

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
                print(deck_to_string(availableCards))
                continue
            else:
                print("Please enter B, P, or S.")

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Prompt the human to pick a card from a list of Card objects.

        Displays a rich table when game is supplied; plain numbered list otherwise.
        """
        if not options:
            print("Oh no - no valid purchase options this turn.")
            return None
        if game is not None:
            return utility.card_menu(options)
        return utility.userChoice([c.name for c in options])

    def chooseDice(self, players: list | None = None) -> int:
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

    def chooseReroll(self, last_roll: int | None = None) -> bool:
        """Prompt the human to use the Radio Tower re-roll if they own it; returns their decision."""
        if self.hasRadioTower:
            choice = input("Use Radio Tower to re-roll? ([Y]es / [N]o) ")
            if "y" in choice.lower():
                return True
        return False

    def chooseTarget(self, players: list[Player]) -> Player | None:
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
        if availableCards.names(maxcost=self.bank):
            return 'buy'
        return 'pass'

    def chooseCard(self, options: list[Card], game: Game | None = None) -> str | None:
        """Return a randomly selected card name, or None if the list is empty."""
        if not options:
            return None
        return random.choice(options).name

    def chooseReroll(self, last_roll: int | None = None) -> bool:
        """Return True if the bot owns Radio Tower and the last roll was below 5."""
        return self.hasRadioTower and last_roll is not None and last_roll < 5

    def chooseTarget(self, players: list[Player]) -> Player | None:
        """Return the non-rolling player with the most coins, or None if no valid targets."""
        valid_targets = [p for p in players if not p.isrollingdice]
        if not valid_targets:
            return None
        return max(valid_targets, key=lambda p: p.bank)

    def chooseBusinessCenterSwap(
        self, target: Player, my_swappable: list, their_swappable: list
    ) -> tuple[Card, Card] | None:
        """Choose which card to give and which to take when activating Business Center.

        Take: delegates to chooseCard() so steal preference is consistent with buy preference.
        Give: the card with the lowest (sum of hitsOn + cost) — least valuable to keep.
        Returns (card_to_give, card_to_take) or None to decline.
        """
        if not my_swappable or not their_swappable:
            return None
        steal_name = self.chooseCard(their_swappable)
        if steal_name is None:
            return None
        card_to_take = next(c for c in their_swappable if c.name == steal_name)
        card_to_give = min(
            my_swappable,
            key=lambda c: sum(getattr(c, "hitsOn", [0])) + getattr(c, "cost", 0),
        )
        return (card_to_give, card_to_take)


def get_die_roller(players: list[Player]) -> Player:
    """Return the player whose isrollingdice flag is True, or raise ValueError if none."""
    for person in players:
        if person.isrollingdice:
            return person
    raise ValueError("No player is currently rolling the dice")


# === Define Class Card() === #
@total_ordering
class Card(object):
    """Abstract base card; subclasses implement trigger() to define activation behaviour."""

    def __init__(self):
        self.name = None
        self.cost = 0
        self.payout = 0
        self.hitsOn = [0]
        self.owner = None       # Cards start with no owner
        self.category = None    # Categories from the list below
        self.multiplies = None  # Also categories

    def describe(self) -> str:
        """Return a plain-English description of this card's effect for display in purchase menus."""
        return ""

    def sortvalue(self) -> float:
        """Return a float used for stable deck ordering: mean hitsOn, then cost, then name."""
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

    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list, multiplies: int | None = None):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.multiplies = multiplies
        self.hitsOn = hitsOn

    _category_names = {1: "Grain", 2: "Ranch", 3: "Bakery", 4: "Café",
                       5: "Gear", 6: "Factory", 7: "Major", 8: "Fruit"}

    def describe(self) -> str:
        """Describe this Green card's effect; factory cards name the category they multiply."""
        if self.multiplies:
            cat = self._category_names.get(self.multiplies, f"cat-{self.multiplies}")
            return f"Pays {self.payout} coin(s) per {cat} card you own, on your roll"
        suffix = " (+1 with Shopping Mall)" if self.name == "Convenience Store" else ""
        return f"Pays {self.payout} coin(s) from bank when you roll{suffix}"

    def trigger(self, players: list[Player]) -> list[Event]:
        """Pay the die-roller from the bank if it is their turn; factory cards multiply by matching category count."""
        events: list[Event] = []
        if self.owner.isrollingdice:
            if not self.multiplies:
                payout_amount = self.payout
                # Shopping Mall adds +1 to convenience store payouts
                if self.owner.hasShoppingMall and self.name == "Convenience Store":
                    payout_amount += 1
                self.owner.deposit(payout_amount)
                events.append(Event(type="payout", card=self.name, player=self.owner.name, value=payout_amount))
            else:
                subtotal = 0
                for card in self.owner.deck.deck:
                    if card.category == self.multiplies:
                        subtotal += 1
                events.append(Event(type="factory_count", player=self.owner.name, card_type=self.multiplies, value=subtotal))
                amount = self.payout * subtotal
                self.owner.deposit(amount)
                events.append(Event(type="payout", card=self.name, player=self.owner.name, value=amount))
        else:
            events.append(Event(type="payout_skip", player=self.owner.name, card=self.name))
        return events

class Red(Card):
    """Red card: steals coins from the die-roller and gives them to the card owner."""

    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn

    def describe(self) -> str:
        """Describe this Red card's steal effect; notes Shopping Mall bonus where applicable."""
        suffix = " (+1 with Shopping Mall)" if self.name in ("Cafe", "Family Restaurant") else ""
        return f"Steals {self.payout} coin(s) from the roller on their turn{suffix}"

    def trigger(self, players: list[Player]) -> list[Event]:
        """Deduct payout coins from the die-roller and deposit them with the card owner."""
        dieroller = get_die_roller(players)
        if self.owner is dieroller:
            return []
        payout_amount = self.payout
        if self.owner.hasShoppingMall and self.name in ["Cafe", "Family Restaurant"]:
            payout_amount += 1
        payout = dieroller.deduct(payout_amount)
        self.owner.deposit(payout)
        return [Event(type="steal", card=self.name, player=self.owner.name, target=dieroller.name, value=payout)]

class Blue(Card):
    """Blue card: pays the bank → card owner regardless of who rolled the dice."""

    def __init__(self, name: str, category: int, cost: int, payout: int, hitsOn: list):
        self.name = name
        self.category = category
        self.cost = cost
        self.payout = payout
        self.hitsOn = hitsOn

    def describe(self) -> str:
        """Describe this Blue card's passive income effect."""
        return f"Pays {self.payout} coin(s) to owner on any player's roll"

    def trigger(self, players: list[Player]) -> list[Event]:
        """Deposit payout coins from the bank into the card owner's account."""
        self.owner.deposit(self.payout)
        return [Event(type="payout", card=self.name, player=self.owner.name, value=self.payout)]

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
        """Describe the Stadium's collect-from-all effect."""
        return f"Collect {self.payout} coins from EACH player when you roll 6"

    def trigger(self, players: list[Player]) -> list[Event]:
        """Collect 2 coins from each other player and deposit them with the die-roller."""
        events: list[Event] = []
        dieroller = get_die_roller(players)
        for person in players:
            if person is dieroller:
                continue
            payment = person.deduct(self.payout)
            dieroller.deposit(payment)
            events.append(Event(type="collect", card=self.name, player=dieroller.name, target=person.name, value=payment))
        return events

class TVStation(Card):
    """Purple card: on a 6, lets the owner steal 5 coins from a chosen target player."""

    def __init__(self, name="TV Station"):
        self.name = name
        self.category = 7
        self.cost = 7
        self.hitsOn = [6]
        self.payout = 5

    def describe(self) -> str:
        """Describe the TV Station's targeted-steal effect."""
        return f"Steal {self.payout} coins from a chosen player when you roll 6"

    def trigger(self, players: list[Player]) -> list[Event]:
        """If the owner is the die-roller, steal up to 5 coins from a chosen target."""
        events: list[Event] = []
        dieroller = get_die_roller(players)
        if dieroller == self.owner:
            events.append(Event(type="steal_activate", player=self.owner.name))
            target = dieroller.chooseTarget(players)
            if target:
                events.append(Event(type="steal_target", player=self.owner.name, target=target.name))
                payment = target.deduct(self.payout)
                dieroller.deposit(payment)
                events.append(Event(type="steal", card=self.name, player=self.owner.name, target=target.name, value=payment))
            else:
                events.append(Event(type="steal_no_target", player=self.owner.name))
        else:
            events.append(Event(type="steal_skip"))
        return events

class BusinessCenter(Card):
    """Purple card: on a 6, lets the owner swap a card with another player."""

    def __init__(self, name="Business Center"):
        self.name = name
        self.category = 7
        self.cost = 8
        self.hitsOn = [6]
        self.payout = 0

    def describe(self) -> str:
        """Describe the Business Center's card-swap effect."""
        return "Swap one of your cards with any player's card when you roll 6"

    def trigger(self, players: list[Player]) -> list[Event]:
        """If the owner is the die-roller, swap a card with a target (or give the bot 5 coins)."""
        events: list[Event] = []
        dieroller = get_die_roller(players)
        if self.owner == dieroller:
            events.append(Event(type="bc_activate", player=self.owner.name))
            if not isinstance(dieroller, Human):
                # Bot: choose target and swap via chooseBusinessCenterSwap, or take 5 coins
                target = dieroller.chooseTarget(players)
                if target and len(target.deck.deck) > 0:
                    my_cards = [c for c in dieroller.deck.deck if not isinstance(c, UpgradeCard)]
                    their_cards = [c for c in target.deck.deck if not isinstance(c, UpgradeCard)]
                    swap_result = dieroller.chooseBusinessCenterSwap(
                        target, my_cards, their_cards
                    )
                    if swap_result:
                        card_to_give, card_to_take = swap_result
                        dieroller.swap(card_to_give, target, card_to_take)
                        events.append(
                            Event(
                                type="bc_swap",
                                player=dieroller.name,
                                card=card_to_give.name,
                                target=target.name,
                                message=card_to_take.name,
                            )
                        )
                    else:
                        dieroller.deposit(5)
                        events.append(Event(type="bc_bot_payout", player=dieroller.name, value=5))
                else:
                    dieroller.deposit(5)
                    events.append(Event(type="bc_bot_payout", player=dieroller.name, value=5))
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
                            events.append(Event(type="bc_swap", player=dieroller.name, card=my_card, target=target.name, message=their_card))
                        else:
                            events.append(Event(type="bc_no_cards"))
                    else:
                        events.append(Event(type="bc_no_target"))
        else:
            events.append(Event(type="bc_skip"))
        return events

class UpgradeCard(Card):
    """Orange landmark card that grants a permanent ability when purchased."""

    orangeCards = {
        "Train Station" : [4, 7, "hasTrainStation"],
        "Shopping Mall" : [10, 7, "hasShoppingMall"],
        "Amusement Park" : [16, 7, "hasAmusementPark"],
        "Radio Tower" : [22, 7, "hasRadioTower"]
    }

    def __init__(self, name: str):
        super().__init__()
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
        """Return the permanent ability description for this landmark card."""
        return self._descriptions.get(self.name, "")

    def bestowPower(self) -> None:
        """Set the corresponding boolean flag on the owner to activate this upgrade's ability."""
        setattr(self.owner, self.orangeCards[self.name][2], True)

# "Stores" are wrappers for a deck[] list and a few functions; decks hold Card objects
class Store(object):
    """Generic sorted collection of Card objects with query and mutation helpers."""

    def __init__(self):
        self.deck = []

    def names(self, maxcost: int = 99, flavor: type = Card) -> list[str]:
        """Return a de-duplicated list of card names with cost ≤ maxcost and matching flavor type."""
        namelist = []
        for card in self.deck:
            if (card.name not in namelist) and isinstance(card, flavor) and (card.cost <= maxcost):
                namelist.append(card.name)
        return namelist

    def freq(self) -> dict[Card, int]:
        """Return a {card: count} dict of card occurrences in this deck."""
        f = {}
        for card in self.deck:
            if f.get(card):
                f[card] += 1
            else:
                f[card] = 1
        return f

    def append(self, card: Card) -> None:
        """Add card to the deck and re-sort. Raises TypeError if card is not a Card."""
        if not isinstance(card, Card):
            raise TypeError(f"Expected Card, got {type(card).__name__}")
        self.deck.append(card)
        self.deck.sort()

    def remove(self, card: Card) -> None:
        """Remove card from the deck and re-sort. Raises TypeError if card is not a Card."""
        if not isinstance(card, Card):
            raise TypeError(f"Expected Card, got {type(card).__name__}")
        self.deck.remove(card)
        self.deck.sort()

class PlayerDeck(Store):
    """A player's personal card collection; pre-loaded with Wheat Field and Bakery."""

    def __init__(self, owner: Player):
        self.deck = []
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
def setPlayers(players: int | None = None, bots: int = 0, humans: int = 0) -> list[Player]:
    """Build and return the player list from explicit counts, an integer, or interactive prompts."""
    # Lazy import — bots.py imports harmonictook (for Bot, Player, etc.) and strategy
    # (for EV functions), so importing at module level would create a circular dependency.
    # By the time setPlayers() is called the module is fully loaded and this resolves cleanly.
    from bots import (  # noqa: PLC0415
        ThoughtfulBot, EVBot, CoverageBot, ImpatientBot, MarathonBot,
        FromageBot, KinematicBot,
    )
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
        _PLAYER_OPTIONS = [
            "Human",
            "Hard",
            "Medium",
            "Easy",
            "Surprise Me!",
        ]
        moreplayers = True
        while moreplayers:
            choice = utility.userChoice(_PLAYER_OPTIONS)
            if choice == "Human":
                playername = input("What's the human's name? ")
                playerlist.append(Human(name=str(playername)))
            else:
                playername = input("What's the bot's name? ")
                if "Hard" in choice:
                    cls = random.choices([FromageBot, ImpatientBot], weights=[50, 50])[0]
                elif "Medium" in choice:
                    cls = random.choice([MarathonBot, EVBot, ThoughtfulBot])
                elif "Easy" in choice:
                    cls = random.choices([CoverageBot, Bot], weights=[75, 25])[0]
                else:  # Surprise me
                    cls = random.choice([ThoughtfulBot, MarathonBot, ImpatientBot,
                                         EVBot, CoverageBot, FromageBot, KinematicBot])
                playerlist.append(cls(name=str(playername)))
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
        raise ValueError(f"Unexpected type for `players` in call to setPlayers(): {type(players)}")

    if players >=2 and players <= 4:
        for num in range(players):
            playerlist.append(Bot(name=str("Robo" + str(num))))
    return playerlist

def deck_to_string(deckObject: Store) -> str:
    """Return a formatted frequency table for the given Store's cards as a string."""
    f = deckObject.freq()
    rowstring = ""
    for card, quantity in f.items():
        rowstring += f"{str(card) + '|':16}"
        for _ in range(quantity):
            rowstring += "[]"
        rowstring += f"{quantity}\n"
    return rowstring


class Display(ABC):
    """Abstract base class for all game renderers."""

    @abstractmethod
    def show_events(self, events: list[Event]) -> None:
        """Render a list of game events."""
        ...


class TerminalDisplay(Display):
    """Renders game events to the terminal via print()."""

    def show_events(self, events: list[Event]) -> None:
        for event in events:
            self._render(event)

    def _render(self, event: Event) -> None:  # noqa: C901
        t = event.type
        if t == "turn_start":
            print(f"-=-=-= It's {event.player}'s turn =-=-=-")
        elif t == "roll":
            print(f"{event.player} rolled a {event.value}.")
        elif t == "reroll":
            print(f"{event.player} uses the Radio Tower to re-roll!")
        elif t == "card_activates":
            print(f"{event.player}'s {event.card} activates on a {event.value}...")
        elif t == "payout":
            print(f"{event.card} pays out {event.value} to {event.player}.")
        elif t == "payout_skip":
            print(f"{event.player} didn't roll the dice - no payout from {event.card}.")
        elif t == "factory_count":
            print(f"{event.player} has {event.value} cards of type {event.card_type}...")
        elif t == "steal":
            print(f"{event.player} collected {event.value} coins from {event.target}.")
        elif t == "steal_activate":
            print(f"{event.player} activates TV Station!")
        elif t == "steal_target":
            print(f"{event.player} targets {event.target}!")
        elif t == "steal_no_target":
            print("No valid targets for TV Station.")
        elif t == "steal_skip":
            print("TV Station doesn't activate (not die roller's turn).")
        elif t == "collect":
            pass  # Stadium collects are silent
        elif t == "bc_activate":
            print(f"{event.player} activates Business Center!")
        elif t == "bc_bot_payout":
            print(f"{event.player} gets {event.value} coins (no swap).")
        elif t == "bc_swap":
            print(f"Swapped {event.card} for {event.target}'s {event.message}.")
        elif t == "bc_no_cards":
            print("Not enough swappable cards.")
        elif t == "bc_no_target":
            print("No valid swap target.")
        elif t == "bc_skip":
            print("Business Center doesn't activate (not die roller's turn).")
        elif t == "bank_status":
            print(f"{event.player} now has {event.value} coins.")
        elif t == "deck_state":
            print(event.message, end="")
        elif t == "buy":
            print(f"{event.player} bought a {event.card} for {event.value} coins, and now has {event.remaining_bank} coins.")
        elif t == "buy_failed":
            print(f"Sorry: a {event.card} costs {event.value} and {event.player} only has {event.remaining_bank}.")
        elif t == "buy_not_found":
            print(f"Sorry: we don't have anything called '{event.card}'.")
        elif t == "pass":
            print(f"{event.player} passes this turn.")
        elif t == "win":
            print(f"{event.player} wins!")
        elif t == "doubles_bonus":
            print(f"{event.player} rolled doubles and gets to go again!")


class NullDisplay(Display):
    """Swallows all events without rendering; used for testing and headless runs."""

    def show_events(self, events: list[Event]) -> None:
        pass


class RecordingDisplay(Display):
    """Accumulates all events from a game run for post-hoc analysis.

    After game.run(), inspect self.events to aggregate card payouts,
    compute acceleration, or build any other per-game metrics.
    """

    def __init__(self) -> None:
        self.events: list[Event] = []

    def show_events(self, events: list[Event]) -> None:
        self.events.extend(events)


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
        self.history: list[GameState] = []

    def get_current_player(self) -> Player:
        """Return the player whose turn it currently is."""
        return self.players[self.current_player_index]

    def get_purchase_options(self) -> list[Card]:
        """Return Card objects affordable by the current player.

        Includes both market establishments and any landmark upgrades the player
        can afford but has not yet built. Distinct by name — duplicates pruned.
        """
        player = self.get_current_player()
        seen: set[str] = set()
        options: list[Card] = []
        for card in self.market.deck:
            if card.cost <= player.bank and card.name not in seen:
                seen.add(card.name)
                options.append(card)
        for upgrade in player.checkRemainingUpgrades():
            if upgrade.cost <= player.bank and upgrade.name not in seen:
                seen.add(upgrade.name)
                options.append(upgrade)
        return options

    def get_player_state(self, player: Player) -> dict:
        """Return a display-friendly dict for one player: name, bank, landmarks count, cards count."""
        landmarks = sum([
            player.hasTrainStation,
            player.hasShoppingMall,
            player.hasAmusementPark,
            player.hasRadioTower,
        ])
        cards = sum(1 for c in player.deck.deck if not isinstance(c, UpgradeCard))
        return {
            "name": player.name,
            "bank": player.bank,
            "landmarks": landmarks,
            "cards": cards,
        }

    def get_market_state(self) -> dict[str, int]:
        """Return available cards in the market as name -> quantity."""
        counts: dict[str, int] = {}
        for card in self.market.deck:
            counts[card.name] = counts.get(card.name, 0) + 1
        return counts

    def refresh_market(self) -> None:
        """Sync unique cards between reserve and market based on the current player's holdings."""
        player = self.get_current_player()
        for card in list(self.reserve.deck):
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

    def next_turn(self, display: Display | None = None) -> list[Event]:
        """Execute one full turn for the current player; return list of game events.

        Events are emitted to display immediately as they occur so that
        interactive prompts always have context rendered above them.
        """
        if display is None:
            display = NullDisplay()
        events: list[Event] = []

        def emit(event: Event) -> None:
            events.append(event)
            display.show_events([event])

        player = self.get_current_player()

        # Reset isrollingdice flags; mark the active player
        for person in self.players:
            person.isrollingdice = False
        player.isrollingdice = True

        self.refresh_market()

        # Pre-turn status: show coins and deck before any prompts fire
        for person in self.players:
            emit(Event(type="bank_status", player=person.name, value=person.bank))
        deck_header = f"-=-=-={player.name}'s Deck=-=-=-\n"
        emit(Event(type="deck_state", player=player.name, message=deck_header + deck_to_string(player.deck)))

        # Die Rolling Phase
        emit(Event(type="turn_start", player=player.name))
        dieroll, isDoubles = player.dieroll(self.players)
        self.last_roll = dieroll
        emit(Event(type="roll", player=player.name, value=dieroll, is_doubles=isDoubles))

        # Radio Tower re-roll option
        if player.chooseReroll(dieroll):
            emit(Event(type="reroll", player=player.name))
            dieroll, isDoubles = player.dieroll(self.players)
            self.last_roll = dieroll
            emit(Event(type="roll", player=player.name, value=dieroll, is_doubles=isDoubles))

        # Card triggers in correct color order: Red → Blue → Green → Purple
        for card_color in [Red, Blue, Green, Stadium, TVStation, BusinessCenter]:
            for person in self.players:
                for card in person.deck.deck:
                    if dieroll in card.hitsOn and isinstance(card, card_color):
                        emit(Event(type="card_activates", player=person.name, card=card.name, value=dieroll))
                        for trigger_event in card.trigger(self.players):
                            emit(trigger_event)

        # Post-trigger bank status: show updated coins before the buy decision
        for person in self.players:
            emit(Event(type="bank_status", player=person.name, value=person.bank))

        action = player.chooseAction(self.market)
        if action == 'buy':
            options = self.get_purchase_options()
            cardname = player.chooseCard(options, self)
            if cardname is not None:
                for buy_event in player.buy(cardname, self.market):
                    emit(buy_event)
        elif action == 'pass':
            emit(Event(type="pass", player=player.name))

        self.history.append(GameState(
            turn_number=self.turn_number,
            active_player=player.name,
            roll=self.last_roll,
            players=[
                PlayerSnapshot(**self.get_player_state(p))
                for p in self.players
            ],
            events=events,
        ))
        self.turn_number += 1
        return events

    def _declare_winner(self, player: Player, display: Display) -> None:
        """Record the winner and emit the win event."""
        self.winner = player
        display.show_events([Event(type="win", player=player.name)])

    def run(self, display: Display | None = None) -> None:
        """Run the game loop until a player wins."""
        if display is None:
            display = TerminalDisplay()
        while True:
            for i, turntaker in enumerate(self.players):
                self.current_player_index = i
                # next_turn emits to display in real-time; we only inspect events for doubles
                events = self.next_turn(display)
                roll_events = [e for e in events if e.type == "roll"]
                is_doubles = roll_events[-1].is_doubles if roll_events else False
                if turntaker.isWinner():
                    self._declare_winner(turntaker, display)
                    return
                while is_doubles and turntaker.hasAmusementPark:
                    display.show_events([Event(type="doubles_bonus", player=turntaker.name)])
                    events = self.next_turn(display)
                    roll_events = [e for e in events if e.type == "roll"]
                    is_doubles = roll_events[-1].is_doubles if roll_events else False
                    if turntaker.isWinner():
                        self._declare_winner(turntaker, display)
                        return


def main():
    # CLI flags control player count only. Bot type selection is done interactively
    # in setPlayers(); adding per-bot-type flags here would duplicate that interface.
    parser = argparse.ArgumentParser(description='The card game Machi Koro')
    parser.add_argument('--bots', type=int, default=0, metavar='N', help='number of bot players (skips interactive setup)')
    parser.add_argument('--humans', type=int, default=0, metavar='N', help='number of human players (skips interactive setup)')
    args = parser.parse_args()
    game = Game(bots=args.bots, humans=args.humans)
    game.run(display=TerminalDisplay())


if __name__ == "__main__":
    import sys
    sys.modules['harmonictook'] = sys.modules['__main__']
    main()