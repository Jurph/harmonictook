#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_integration.py — Mid-game state injection integration tests

import unittest
from unittest.mock import patch
from harmonictook import Game, NullDisplay, Blue, Green, Red, Stadium


class TestMidgameIntegration(unittest.TestCase):
    """
    Integration tests for card trigger mechanics using direct state injection.

    setUp constructs a single mid-game snapshot with three players:

      Roller (index 0) — a fully built card engine:
        - Shopping Mall and Amusement Park set directly (no Radio Tower;
          Bot.chooseReroll() would fire on totals < 5 and consume extra
          randint calls, breaking side_effect sequences)
        - Cheese Factory engine:  3 Ranches  (cat 2) → roll 7  pays 9
        - Furniture Factory engine: 2 Forests + 1 Mine (cat 5) → roll 8  pays 9
        - F&V Market engine: 2 Wheat Fields + 1 Apple Orchard (cat 1) → roll 11 pays 6
        - Convenience Store → roll 4 pays 4 (3 base + 1 Shopping Mall)
        - Cafe and Family Restaurant (Red): collect from others when they roll
        - Stadium → roll 6 collects 2 from each player

      Rich (index 1) — 100 coins; targeted by red-card toll tests.

      Poor (index 2) — exactly 1 coin; exercises partial Stadium deduction.

    All three players have Train Station set directly so every turn consumes
    exactly two randint calls (2-dice roll), keeping side_effect sequences
    predictable. The market and reserve are cleared so bots always pass in the
    buy phase and Rich's 100 coins can never accidentally win the game.
    """

    def setUp(self):
        self.game  = Game(players=3)
        self.roller = self.game.players[0]
        self.rich   = self.game.players[1]
        self.poor   = self.game.players[2]

        # Everyone rolls 2 dice: exactly 2 randint calls per turn, no exceptions.
        # Bot.chooseDice() always returns 2 when hasTrainStation is True.
        for p in self.game.players:
            p.hasTrainStation = True

        # Roller's landmarks (no Radio Tower — avoids reroll consuming extra randint calls)
        self.roller.hasShoppingMall  = True
        self.roller.hasAmusementPark = True
        self.roller.deposit(50)

        # Rich is flush but the empty market means they can never buy anything
        self.rich.deposit(100)

        # Poor has exactly 1 coin to exercise partial Stadium deduction
        self.poor.deduct(self.poor.bank)
        self.poor.deposit(1)

        def give(card):
            card.owner = self.roller
            self.roller.deck.append(card)

        # Cheese Factory engine — roll 7 pays 3 Ranches × 3 = 9
        for _ in range(3):
            give(Blue("Ranch", 2, 1, 1, [2]))
        give(Green("Cheese Factory", 6, 5, 3, [7], 2))

        # Furniture Factory engine — roll 8 pays 3 Gear cards × 3 = 9
        # (2 Forests + 1 Mine, all category 5)
        give(Blue("Forest", 5, 3, 1, [5]))
        give(Blue("Forest", 5, 3, 1, [5]))
        give(Blue("Mine",   5, 6, 5, [9]))
        give(Green("Furniture Factory", 6, 3, 3, [8], 5))

        # F&V Market engine — roll 11 pays 3 Grain cards × 2 = 6
        # PlayerDeck already contributes 1 starting Wheat Field (cat 1);
        # adding 1 more Wheat Field and 1 Apple Orchard brings Grain count to 3
        give(Blue("Wheat Field",   1, 1, 1, [1]))
        give(Blue("Apple Orchard", 1, 3, 3, [10]))
        give(Green("Farmer's Market", 8, 2, 2, [11, 12], 1))

        # Convenience Store — roll 4 pays 3 + 1 (Shopping Mall) = 4
        give(Green("Convenience Store", 3, 2, 3, [4]))

        # Red toll cards — collect from the die roller when others roll
        give(Red("Cafe",              4, 2, 1, [3]))
        give(Red("Family Restaurant", 4, 3, 2, [9, 10]))

        # Stadium — roll 6 collects up to 2 coins from each player
        stadium = Stadium()
        stadium.owner = self.roller
        self.roller.deck.append(stadium)

        # Seal market and reserve so bots always pass — no confounding purchases
        self.game.market.deck.clear()
        self.game.reserve.deck.clear()

    # ------------------------------------------------------------------ #
    # Roller's turn tests                                                  #
    # ------------------------------------------------------------------ #

    @patch('harmonictook.random.randint', side_effect=[2, 2])   # 2+2=4
    def testConvenienceStoreWithShoppingMall(self, _):
        """Roll 4: Convenience Store pays 3 base + 1 Shopping Mall = 4 coins."""
        self.game.current_player_index = 0
        before = self.roller.bank
        events = self.game.next_turn(NullDisplay())
        payouts = [e for e in events if e.type == "payout" and e.card == "Convenience Store"]
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].value, 4)
        self.assertEqual(self.roller.bank - before, 4)

    @patch('harmonictook.random.randint', side_effect=[3, 4])   # 3+4=7
    def testCheeseFactoryMultiplier(self, _):
        """Roll 7 with 3 Ranches: Cheese Factory pays 3 × 3 = 9 coins."""
        self.game.current_player_index = 0
        before = self.roller.bank
        events = self.game.next_turn(NullDisplay())
        factory_counts = [e for e in events if e.type == "factory_count" and e.card_type == 2]
        self.assertEqual(factory_counts[0].value, 3)            # 3 Ranch cards counted
        payouts = [e for e in events if e.type == "payout" and e.card == "Cheese Factory"]
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].value, 9)
        self.assertEqual(self.roller.bank - before, 9)

    @patch('harmonictook.random.randint', side_effect=[4, 4])   # 4+4=8
    def testFurnitureFactoryMultiplier(self, _):
        """Roll 8 with 2 Forests + 1 Mine (3 Gear cards): Furniture Factory pays 3 × 3 = 9 coins."""
        self.game.current_player_index = 0
        before = self.roller.bank
        events = self.game.next_turn(NullDisplay())
        payouts = [e for e in events if e.type == "payout" and e.card == "Furniture Factory"]
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].value, 9)
        self.assertEqual(self.roller.bank - before, 9)

    @patch('harmonictook.random.randint', side_effect=[5, 6])   # 5+6=11
    def testFarmersMarketMultiplier(self, _):
        """Roll 11 with 2 Wheat Fields + 1 Apple Orchard (3 Grain): Farmer's Market pays 3 × 2 = 6 coins."""
        self.game.current_player_index = 0
        before = self.roller.bank
        events = self.game.next_turn(NullDisplay())
        payouts = [e for e in events if e.type == "payout" and e.card == "Farmer's Market"]
        self.assertEqual(len(payouts), 1)
        self.assertEqual(payouts[0].value, 6)
        self.assertEqual(self.roller.bank - before, 6)

    @patch('harmonictook.random.randint', side_effect=[3, 3])   # 3+3=6
    def testStadiumPartialDrain(self, _):
        """Roll 6: Stadium collects 2 from Rich but only 1 from Poor (who has only 1 coin)."""
        self.game.current_player_index = 0
        events = self.game.next_turn(NullDisplay())
        poor_collects = [e for e in events if e.type == "collect" and e.target == self.poor.name]
        self.assertEqual(len(poor_collects), 1)
        self.assertEqual(poor_collects[0].value, 1)   # capped at 1, not 2
        self.assertEqual(self.poor.bank, 0)
        # Sanity: Rich paid the full 2
        rich_collects = [e for e in events if e.type == "collect" and e.target == self.rich.name]
        self.assertEqual(rich_collects[0].value, 2)

    # ------------------------------------------------------------------ #
    # Rich's turn tests — red and blue cards fire for Roller on others' rolls #
    # ------------------------------------------------------------------ #

    @patch('harmonictook.random.randint', side_effect=[1, 2])   # 1+2=3
    def testCafeRedOnNonOwnersTurn(self, _):
        """Rich rolls 3: Roller's Cafe collects 1 base + 1 Shopping Mall = 2 coins from Rich."""
        self.game.current_player_index = 1
        before_roller = self.roller.bank
        events = self.game.next_turn(NullDisplay())
        # target=rich because Rich (the die roller) is being stolen from
        steals = [e for e in events if e.type == "steal" and e.target == self.rich.name]
        self.assertEqual(len(steals), 1)
        self.assertEqual(steals[0].value, 2)
        self.assertEqual(self.roller.bank - before_roller, 2)
        # Note: Rich also gains 1 from their own Bakery (hitsOn=[2,3]); Roller's bank is unaffected

    @patch('harmonictook.random.randint', side_effect=[4, 5])   # 4+5=9
    def testMineAndFamilyRestaurantSameRoll(self, _):
        """Rich rolls 9: Mine (Blue) pays Roller 5 from the bank AND Family Restaurant (Red) collects 3 from Rich — both on the same roll."""
        self.game.current_player_index = 1
        before_roller = self.roller.bank
        before_rich   = self.rich.bank
        events = self.game.next_turn(NullDisplay())
        mine_payouts = [e for e in events if e.type == "payout" and e.card == "Mine"]
        fr_steals    = [e for e in events if e.type == "steal"   and e.target == self.rich.name]
        self.assertEqual(len(mine_payouts), 1)
        self.assertEqual(mine_payouts[0].value, 5)              # Blue: bank → Roller
        self.assertEqual(len(fr_steals), 1)
        self.assertEqual(fr_steals[0].value, 3)                 # Red: 2 base + 1 Shopping Mall
        self.assertEqual(self.roller.bank - before_roller, 8)   # 5 (Mine) + 3 (toll)
        self.assertEqual(before_rich - self.rich.bank, 3)       # only the toll; Mine pays from bank


class TestTriggerOrder(unittest.TestCase):
    """Regression tests for card trigger color order: Red → Blue → Green → Purple.

    If the order were wrong (e.g. Blue before Red), a Red card could steal income
    that Blue already paid the roller — inflating Red's effective take. The correct
    rule is Red first (opponent collects toll before the roller earns anything).
    """

    def test_red_fires_before_green(self):
        """On the roller's turn, Red (opponent's Cafe on [3]) precedes Green (roller's Bakery on [3])."""
        game = Game(players=2)
        roller = game.players[0]
        opponent = game.players[1]
        game.current_player_index = 0
        roller.deposit(10)
        opponent.deposit(10)

        # Opponent owns a Cafe (Red[3]); fires when roller rolls 3, steals from roller
        cafe = Red("Cafe", 4, 2, 1, [3])
        cafe.owner = opponent
        opponent.deck.append(cafe)
        # Roller's starting deck already contains Bakery (Green[2,3])

        with patch('harmonictook.random.randint', return_value=3):
            events = game.next_turn(NullDisplay())

        types = [e.type for e in events]
        steal_idx = next(i for i, t in enumerate(types) if t == "steal")
        payout_idx = next(
            i for i, t in enumerate(types)
            if t == "payout" and events[i].card == "Bakery"
        )
        self.assertLess(steal_idx, payout_idx,
                        "Red (steal) must appear before Green (payout) in event order")


if __name__ == "__main__":
    unittest.main(buffer=True)
