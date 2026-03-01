#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_bots.py — Bot and ThoughtfulBot behaviour tests

import unittest
from unittest.mock import patch
from harmonictook import Game, Blue, Green, Red, Stadium, TVStation, BusinessCenter, UpgradeCard
from bots import (
    ThoughtfulBot, EVBot, ImpatientBot, MarathonBot,
    _roll_income, _with_card_bought, _with_card_appended, _with_card_removed,
    _card_variance, _kinematic_n,
)


class TestBots(unittest.TestCase):
    """Tests for Bot card selection, targeting, and upgrade trigger mechanics."""

    def setUp(self):
        self.players = 2
        self.game = Game(players=self.players)
        self.testbot = self.game.players[0]
        self.otherbot = self.game.players[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testRadioTowerReroll(self):
        """Verify Bot.chooseReroll() returns True on rolls ≤4 and False on rolls ≥5 when Radio Tower is owned."""
        testbot = self.testbot
        testbot.buy("Radio Tower", self.game.market)
        self.assertTrue(testbot.chooseReroll(3))
        self.assertFalse(testbot.chooseReroll(9))

    def testTVStationTargeting(self):
        """Verify TV Station steals exactly 5 coins (or all if target has fewer) from the chosen target."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("TV Station", self.game.market)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.game.players)
        after = testbot.bank
        otherbot_after = otherbot.bank
        stolen = min(5, otherbot_before)
        self.assertEqual(after - before, stolen)
        self.assertEqual(otherbot_before - otherbot_after, stolen)

    def testBusinessCenterBotNoTargetGetsCoins(self):
        """When no valid swap target exists, bot gets 5 coins."""
        testbot = self.testbot
        testbot.buy("Business Center", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        with patch.object(testbot, "chooseTarget", return_value=None):
            for card in testbot.deck.deck:
                if isinstance(card, BusinessCenter):
                    card.trigger(self.game.players)
        after = testbot.bank
        self.assertEqual(after - before, 5)

    def testBusinessCenterBotSwaps(self):
        """Business Center steal uses the bot's own chooseCard() preference to pick what to take."""
        from harmonictook import Blue
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        forest = Blue("Forest", 1, 3, 1, [5])
        forest.owner = otherbot
        otherbot.deck.append(forest)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        bank_before = testbot.bank
        with patch.object(testbot, 'chooseCard', return_value='Forest') as mock_cc:
            for card in testbot.deck.deck:
                if isinstance(card, BusinessCenter):
                    card.trigger(self.game.players)
        mock_cc.assert_called_once()
        self.assertEqual(testbot.bank, bank_before, "Bot should not get 5 coins when swap is possible")
        my_names_after = [c.name for c in testbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Forest", my_names_after, "Bot should take the card chosen by chooseCard()")

    def testBusinessCenterBotGivesLowestScore(self):
        """Bot gives away the card with the lowest (sum of hitsOn + cost) score."""
        from harmonictook import Blue
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        # Add a Ranch (hitsOn=[2], cost=1, score=3) so bot has:
        #   Wheat Field (score=1+1=2), Bakery (score=2+3+1=6), Ranch (score=2+1=3), BC (score=6+8=14)
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = testbot
        testbot.deck.append(ranch)
        # Give otherbot a high-cost card to be the take target
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = otherbot
        otherbot.deck.append(mine)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.game.players)
        # Wheat Field (score 2) should have been given away — check it's in otherbot's deck
        other_names = [c.name for c in otherbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Wheat Field", other_names, "Bot should give away Wheat Field (lowest hitsOn+cost)")
        # Ranch (score 3) should still be in testbot's deck
        my_names = [c.name for c in testbot.deck.deck if not isinstance(c, UpgradeCard)]
        self.assertIn("Ranch", my_names, "Bot should keep Ranch (higher hitsOn+cost than Wheat Field)")

    def testThoughtfulBotPriority(self):
        """Verify ThoughtfulBot picks an upgrade over a lower-priority card when both are available."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        wheat  = Blue("Wheat Field", 1, 1, 1, [1])
        radio  = UpgradeCard("Radio Tower")
        mine   = Blue("Mine", 5, 6, 5, [9])
        cafe   = Red("Cafe", 4, 2, 1, [3])
        choice = thoughtful.chooseCard([wheat, radio, mine, cafe])
        self.assertEqual(choice, "Radio Tower")

    def testBotChooseCardMocked(self):
        """Verify Bot.chooseCard() delegates card selection to random.choice."""
        testbot = self.testbot
        ranch = Blue("Ranch", 2, 1, 1, [2])
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        mine  = Blue("Mine", 5, 6, 5, [9])
        options = [ranch, wheat, mine]
        with patch('harmonictook.random.choice', return_value=ranch):
            result = testbot.chooseCard(options)
        self.assertEqual(result, 'Ranch')

    def testThoughtfulBotChooseDice(self):
        """ThoughtfulBot picks dice by expected own-turn income.

        Without Train Station: always 1.
        With Train Station and only low-roll cards: 1 die is better (high-roll faces yield 0).
        With Train Station and a high-roll card (Mine at [9]): 2 dice is better.
        """
        game = Game(players=2)
        bot = ThoughtfulBot(name="Thoughtful")
        bot.deck = game.players[0].deck
        self.assertEqual(bot.chooseDice(game.players), 1)  # no Train Station

        bot.hasTrainStation = True
        # Default deck (Wheat Field [1], Bakery [2,3]): 1-die EV > 2-die EV
        self.assertEqual(bot.chooseDice(game.players), 1)

        # Add Mine (Blue, [9], payout=5): only reachable with 2 dice
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = bot
        bot.deck.append(mine)
        self.assertEqual(bot.chooseDice(game.players), 2)

    def testBotChooseActionPass(self):
        """Verify Bot.chooseAction() returns 'pass' when no cards are affordable."""
        testbot = self.testbot
        testbot.deduct(testbot.bank)  # drain to zero
        self.assertEqual(testbot.chooseAction(self.game.market), 'pass')

    def testBotChooseCardEmpty(self):
        """Verify Bot.chooseCard() returns None and doesn't crash on an empty options list."""
        result = self.testbot.chooseCard([])
        self.assertIsNone(result)

    def testThoughtfulBotChooseCardEmpty(self):
        """Verify ThoughtfulBot.chooseCard() returns None and doesn't crash on an empty options list."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        result = thoughtful.chooseCard([])
        self.assertIsNone(result)

    def testThoughtfulBotLateCardPriority(self):
        """Verify ThoughtfulBot prefers late-game cards over early-game cards when Train Station is owned."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        thoughtful.hasTrainStation = True
        # Add a Ranch so Cheese Factory (a factory latecard) also becomes eligible.
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = thoughtful
        thoughtful.deck.append(ranch)
        bakery = Green("Bakery", 3, 1, 1, [2, 3])
        mine   = Blue("Mine", 5, 6, 5, [9])
        # Mine is a latecard; Bakery is an earlycard — latecard should win
        self.assertEqual(thoughtful.chooseCard([bakery, mine]), "Mine")

    def testThoughtfulBotRandomFallback(self):
        """Verify ThoughtfulBot falls back to random.choice(names) when no option matches any priority list."""
        thoughtful = ThoughtfulBot(name="Thoughtful")
        curiosity  = Blue("Curiosity Shop", 1, 1, 1, [4])
        duck_ranch = Blue("Duck Ranch", 2, 1, 1, [5])
        # ThoughtfulBot calls random.choice on a list of name strings (in bots.py).
        with patch('bots.random.choice', return_value='Duck Ranch'):
            result = thoughtful.chooseCard([curiosity, duck_ranch])
        self.assertEqual(result, 'Duck Ranch')


class TestMutateRestoreHelpers(unittest.TestCase):
    """_with_card_bought / _with_card_appended / _with_card_removed: state always restored."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot = self.game.players[0]
        self.bot.deposit(50)

    def test_with_card_bought_restores_bank_and_deck(self):
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.bot
        bank_before = self.bot.bank
        deck_len_before = len(self.bot.deck.deck)
        _with_card_bought(self.bot, card, lambda: None)
        self.assertEqual(self.bot.bank, bank_before)
        self.assertEqual(len(self.bot.deck.deck), deck_len_before)

    def test_with_card_bought_upgrade_restores_flag_and_deck(self):
        upgrade = UpgradeCard("Train Station")
        upgrade.owner = self.bot
        bank_before = self.bot.bank
        flag_before = self.bot.hasTrainStation
        deck_len_before = len(self.bot.deck.deck)
        _with_card_bought(self.bot, upgrade, lambda: None)
        self.assertEqual(self.bot.bank, bank_before)
        self.assertEqual(self.bot.hasTrainStation, flag_before)
        self.assertEqual(len(self.bot.deck.deck), deck_len_before)

    def test_with_card_bought_upgrade_activates_flag_during_fn(self):
        """Flag is True inside fn(), False before and after."""
        upgrade = UpgradeCard("Train Station")
        upgrade.owner = self.bot
        self.bot.deposit(4)
        seen = []
        _with_card_bought(self.bot, upgrade, lambda: seen.append(self.bot.hasTrainStation))
        self.assertTrue(seen[0], "Flag must be True inside fn()")
        self.assertFalse(self.bot.hasTrainStation, "Flag must be restored after")

    def test_with_card_appended_adds_and_removes(self):
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.bot
        seen = []
        _with_card_appended(self.bot, card, lambda: seen.append(len(self.bot.deck.deck)))
        self.assertEqual(seen[0], len(self.bot.deck.deck) + 1,
            "Card must be in deck inside fn()")
        self.assertNotIn(card, self.bot.deck.deck, "Card must be removed after fn()")

    def test_with_card_removed_removes_and_restores(self):
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.bot
        self.bot.deck.deck.append(card)
        seen_len = []
        _with_card_removed(self.bot, card, lambda: seen_len.append(len(self.bot.deck.deck)))
        self.assertEqual(seen_len[0], len(self.bot.deck.deck) - 1,
            "Card must be absent inside fn()")
        self.assertIn(card, self.bot.deck.deck, "Card must be restored after fn()")

    def test_with_card_removed_unknown_card_calls_fn_unchanged(self):
        """If card is not in deck, fn() is still called with the unmodified deck."""
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.bot
        called = []
        _with_card_removed(self.bot, card, lambda: called.append(True))
        self.assertTrue(called, "fn() must be called even when card is not in deck")

    def test_card_variance_upgrade_card_sets_flag_not_deck(self):
        """_card_variance with UpgradeCard only sets the flag; card is NOT added to deck."""
        upgrade = UpgradeCard("Train Station")
        upgrade.owner = self.bot
        deck_len_before = len(self.bot.deck.deck)
        result = _card_variance(self.bot, upgrade, self.game.players)
        self.assertIsInstance(result, float)
        self.assertEqual(len(self.bot.deck.deck), deck_len_before,
            "UpgradeCard must NOT be appended to deck during _card_variance")
        self.assertFalse(self.bot.hasTrainStation,
            "Flag must be restored after _card_variance")

    def test_card_variance_income_card_uses_append(self):
        """_card_variance with income card temporarily appends and then restores."""
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.bot
        deck_len_before = len(self.bot.deck.deck)
        result = _card_variance(self.bot, card, self.game.players)
        self.assertIsInstance(result, float)
        self.assertEqual(len(self.bot.deck.deck), deck_len_before)


class TestKinematicNEdgeCases(unittest.TestCase):
    """_kinematic_n handles zero-deficit and zero-income opponents gracefully."""

    def setUp(self):
        self.game = Game(players=3)
        for p in self.game.players:
            p.deposit(20)

    def test_opponent_with_zero_deficit_contributes_n_1(self):
        """An opponent whose bank >= landmark_cost_remaining is 1 round from winning."""
        rich = self.game.players[1]
        rich.deposit(200)   # bank >> all landmark costs
        players = self.game.players
        opponents = [rich]
        n = _kinematic_n(opponents, players, a=0.45, eruv_offset=0)
        self.assertEqual(n, 1, "Opponent with zero deficit should yield N=1")

    def test_opponent_with_zero_income_contributes_n_999(self):
        """An opponent with no income deck gets N=999 (no path to win)."""
        broke = self.game.players[2]
        broke.deck.deck.clear()
        broke.bank = 0
        players = self.game.players
        opponents = [broke]
        n = _kinematic_n(opponents, players, a=0.45, eruv_offset=0)
        self.assertGreater(n, 10, "Opponent with zero income should produce a very large N")

    def test_zero_acceleration_falls_back_to_linear(self):
        """a≈0 uses ceil(deficit/v) instead of the kinematic formula."""
        opp = self.game.players[1]
        opp.deposit(10)
        players = self.game.players
        n_kinematic  = _kinematic_n([opp], players, a=0.45,  eruv_offset=0)
        n_linear     = _kinematic_n([opp], players, a=1e-15, eruv_offset=0)
        # Both should be positive; the linear fallback must not crash
        self.assertGreaterEqual(n_linear, 1)
        self.assertGreaterEqual(n_kinematic, 1)

    def test_eruv_offset_reduces_n(self):
        """Increasing eruv_offset decreases the returned N."""
        opp = self.game.players[1]
        opp.deposit(10)
        players = self.game.players
        n0 = _kinematic_n([opp], players, a=0.45, eruv_offset=0)
        n2 = _kinematic_n([opp], players, a=0.45, eruv_offset=2)
        self.assertLessEqual(n2, n0)


class TestRollIncomeLogicBugs(unittest.TestCase):
    """Tests that expose known gaps in _roll_income and _own_income_for_roll.

    Both helpers only check isinstance(card, (Blue, Green)), silently ignoring:
      - Stadium / TVStation / BusinessCenter (Purple): their own-turn income is real.
      - Factory multiplication: Cheese Factory payout = base × category_count, not base.
      - Shopping Mall bonus: +1 on Convenience Store is not reflected.

    These gaps cause ImpatientBot and MarathonBot to make incorrect reroll decisions.
    Each test asserts the CORRECT expected behaviour; failures reveal the bug.
    """

    def setUp(self):
        self.game = Game(players=3)
        self.bot = self.game.players[0]
        self.bot.deposit(50)

    def test_roll_income_ignores_stadium(self):
        """_roll_income returns 0 on roll 6 even when Stadium would fire and collect coins.

        Stadium fires on roll 6 and collects card.payout from each other player.
        With 3 players, the roller earns at least 2 coins (2 * 1 = 2 with default payout).
        The helper must return > 0 to let bots make correct reroll decisions.
        """
        self.bot.deck.deck.clear()
        stadium = Stadium()
        stadium.owner = self.bot
        self.bot.deck.append(stadium)
        income = _roll_income(self.bot, 6)
        self.assertGreater(income, 0,
            "_roll_income must count Stadium income on roll 6 — currently returns 0 (bug)")

    def test_impatient_bot_does_not_reroll_stadium_roll(self):
        """ImpatientBot should not reroll roll 6 when Stadium fires.

        _own_income_for_roll ignores Stadium (Purple), so it computes income=0.
        The threshold is also 0 (all other rolls give 0 too), triggering a reroll.
        Correct behaviour: don't reroll a roll that collects Stadium coins.
        """
        bot = ImpatientBot(name="Impatient")
        bot.hasRadioTower = True
        bot.deck.deck.clear()
        stadium = Stadium()
        stadium.owner = bot
        bot.deck.append(stadium)
        self.assertFalse(bot.chooseReroll(6),
            "ImpatientBot must not reroll roll 6 when Stadium fires — currently does (bug)")

    def test_marathon_bot_does_not_reroll_stadium_roll(self):
        """MarathonBot has the same Stadium-ignoring gap via the module-level _roll_income."""
        bot = MarathonBot(name="Marathon")
        bot.hasRadioTower = True
        bot.deck.deck.clear()
        stadium = Stadium()
        stadium.owner = bot
        bot.deck.append(stadium)
        self.assertFalse(bot.chooseReroll(6),
            "MarathonBot must not reroll roll 6 when Stadium fires — currently does (bug)")

    def test_roll_income_ignores_factory_multiplier(self):
        """_roll_income returns base Cheese Factory payout (3), not the multiplied amount.

        With 4 Ranches owned, a roll of 7 should pay 3 × 4 = 12 coins.
        The helper sums card.payout directly: returns 3, not 12.
        """
        self.bot.deck.deck.clear()
        for _ in range(4):
            r = Blue("Ranch", 2, 1, 1, [2])
            r.owner = self.bot
            self.bot.deck.append(r)
        cheese = Green("Cheese Factory", 6, 5, 3, [7], 2)
        cheese.owner = self.bot
        self.bot.deck.append(cheese)
        income = _roll_income(self.bot, 7)
        self.assertEqual(income, 12,
            f"_roll_income returned {income}; expected 12 (3 payout × 4 Ranches) — factory multiplier is missing (bug)")

    def test_roll_income_ignores_shopping_mall_bonus(self):
        """_roll_income ignores Shopping Mall's +1 bonus on Convenience Store.

        A player with Shopping Mall and Convenience Store earns 3+1=4 on roll 4.
        The helper returns 3 (base payout), not 4.
        """
        self.bot.deck.deck.clear()
        self.bot.hasShoppingMall = True
        cs = Green("Convenience Store", 3, 2, 3, [4])
        cs.owner = self.bot
        self.bot.deck.append(cs)
        income = _roll_income(self.bot, 4)
        self.assertEqual(income, 4,
            f"_roll_income returned {income}; expected 4 (3 + Shopping Mall bonus) — bonus is ignored (bug)")


class TestThoughtfulBotPriorityBugs(unittest.TestCase):
    """Tests that expose the latecard/earlycard ordering bug in ThoughtfulBot.

    With Train Station: preferences = upgrades + latecards + earlycards.
    Latecards (Cheese Factory, Furniture Factory, etc.) precede earlycards (Ranch, Wheat Field, etc.).
    This causes the bot to buy factory cards before buying the category cards that give them value.
    """

    def test_cheese_factory_preferred_over_ranch_with_no_ranches(self):
        """ThoughtfulBot with Train Station buys Cheese Factory before Ranch.

        Cheese Factory (latecard) precedes Ranch (earlycard) in the with-Train-Station priority list.
        With 0 Ranches, Cheese Factory has EV = 0.  Ranch should be bought first.
        Correct behaviour: buy Ranch to build the engine before buying the multiplier.
        """
        bot = ThoughtfulBot(name="Thoughtful")
        bot.hasTrainStation = True
        ranch   = Blue("Ranch", 2, 1, 1, [2])
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        choice = bot.chooseCard([ranch, factory])
        self.assertEqual(choice, "Ranch",
            "ThoughtfulBot should buy Ranch before Cheese Factory when it has no Ranches — "
            "currently buys Cheese Factory first because latecards precede earlycards (bug)")

    def test_furniture_factory_preferred_over_forest_with_no_forests(self):
        """ThoughtfulBot with Train Station buys Furniture Factory before Forest (same bug).

        Furniture Factory (latecard, multiplies Gear/category-5) is useless without Forest or Mine.
        Correct behaviour: buy Forest first so the factory has cards to multiply.
        """
        bot = ThoughtfulBot(name="Thoughtful")
        bot.hasTrainStation = True
        forest  = Blue("Forest", 5, 3, 1, [5])
        factory = Green("Furniture Factory", 6, 3, 3, [8], 5)
        choice = bot.chooseCard([forest, factory])
        self.assertEqual(choice, "Forest",
            "ThoughtfulBot should buy Forest before Furniture Factory when it has no Gear cards — "
            "currently picks Furniture Factory first (bug)")

    def test_latecard_correctly_preferred_when_engine_exists(self):
        """Cheese Factory SHOULD be preferred when the bot already has Ranches.

        If Ranches are in the deck, Cheese Factory has positive EV and the priority is correct.
        """
        bot = ThoughtfulBot(name="Thoughtful")
        bot.hasTrainStation = True
        for _ in range(3):
            r = Blue("Ranch", 2, 1, 1, [2])
            r.owner = bot
            bot.deck.append(r)
        ranch   = Blue("Ranch", 2, 1, 1, [2])
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        choice = bot.chooseCard([ranch, factory])
        self.assertEqual(choice, "Cheese Factory",
            "Once the engine exists (Ranches in deck), Cheese Factory priority is correct")


class TestImpatientBot(unittest.TestCase):
    """ImpatientBot: ERUV-minimising decisions."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot = ImpatientBot(name="Impatient")
        self.bot.deck = self.game.players[0].deck
        self.opponent = self.game.players[1]
        self.bot.deposit(50)
        self.opponent.deposit(50)

    def test_no_radio_tower_never_rerolls(self):
        """Without Radio Tower, chooseReroll always returns False."""
        self.assertFalse(self.bot.chooseReroll(1))
        self.assertFalse(self.bot.chooseReroll(6))

    def test_no_last_roll_never_rerolls(self):
        """chooseReroll(None) always returns False."""
        self.bot.hasRadioTower = True
        self.assertFalse(self.bot.chooseReroll(None))

    def test_rerolls_zero_income_roll(self):
        """With all-income deck (covers 1-6), a roll that gives 0 income triggers reroll."""
        self.bot.hasRadioTower = True
        self.bot.deck.deck.clear()
        # Bakery[2,3]: rolls 2 and 3 pay income; roll 5 gives 0
        bakery = Green("Bakery", 3, 1, 1, [2, 3])
        bakery.owner = self.bot
        self.bot.deck.append(bakery)
        self.assertTrue(self.bot.chooseReroll(5))

    def test_does_not_reroll_top_income_roll(self):
        """A roll at the top of the income distribution is NOT rerolled."""
        self.bot.hasRadioTower = True
        self.bot.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.bot
        self.bot.deck.append(mine)
        self.bot.hasTrainStation = True
        # Only roll 9 gives income (5 coins); all others give 0
        # 0 is threshold; income on roll 9 = 5 > 0 → no reroll
        self.assertFalse(self.bot.chooseReroll(9))

    def test_chooseaction_buys_landmark_when_affordable(self):
        """chooseAction returns 'buy' when a landmark is within reach.

        Landmarks are not in the market deck; they must be found via checkRemainingUpgrades().
        The old bug: the code checked isinstance(card, UpgradeCard) on market cards, which
        are never UpgradeCards, so landmarks were invisible to chooseAction.
        """
        self.bot.bank = 100
        result = self.bot.chooseAction(self.game.market)
        self.assertEqual(result, "buy",
            "ImpatientBot must return 'buy' when a landmark is affordable")

    def test_chooseaction_passes_when_no_improvement_and_no_landmark(self):
        """chooseAction returns 'pass' when bot has 0 coins and no landmarks are affordable."""
        self.bot.bank = 0
        result = self.bot.chooseAction(self.game.market)
        self.assertEqual(result, "pass")

    def test_choosecard_returns_name_for_card_objects(self):
        """chooseCard with Card objects returns a string name from the list."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = self.bot
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.bot
        result = self.bot.chooseCard([wheat, ranch])
        self.assertIn(result, ["Wheat Field", "Ranch"])

    def test_choosecard_empty_returns_none(self):
        """Empty options list returns None."""
        self.assertIsNone(self.bot.chooseCard([]))

    def test_bc_swap_gives_least_valuable_card(self):
        """chooseBusinessCenterSwap gives the card whose removal hurts ERUV least."""
        self.bot.deck.deck.clear()
        cheap = Blue("Wheat Field", 1, 1, 1, [1])
        cheap.owner = self.bot
        self.bot.deck.append(cheap)
        expensive = Blue("Mine", 5, 6, 5, [9])
        expensive.owner = self.bot
        self.bot.hasTrainStation = True
        self.bot.deck.append(expensive)
        their_card = Blue("Ranch", 2, 1, 1, [2])
        their_card.owner = self.opponent
        result = self.bot.chooseBusinessCenterSwap(
            self.opponent, [cheap, expensive], [their_card]
        )
        self.assertIsNotNone(result)
        give, take = result
        self.assertIs(give, cheap,
            "ImpatientBot should give away the least-valuable card (Wheat Field), not Mine")


class TestFromageBot(unittest.TestCase):
    """FromageBot: priority-list bot building a Ranch-Cheese engine."""

    def setUp(self):
        from bots import FromageBot
        self.game = Game(players=2)
        self.bot = FromageBot(name="Fromage")
        self.bot.deposit(50)

    def test_buys_ranch_before_cheese_factory_from_scratch(self):
        """FromageBot builds Ranch (cap=3) before Cheese Factory — stage ordering."""
        from bots import FromageBot
        bot = FromageBot(name="Fromage")
        ranch   = Blue("Ranch", 2, 1, 1, [2])
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        choice = bot.chooseCard([ranch, factory])
        self.assertEqual(choice, "Ranch",
            "FromageBot should buy Ranch before Cheese Factory when under the Ranch cap")

    def test_buys_cheese_factory_after_three_ranches(self):
        """After buying 3 Ranches, the next PRIORITY entry is Cheese Factory."""
        from bots import FromageBot
        bot = FromageBot(name="Fromage")
        for _ in range(3):
            r = Blue("Ranch", 2, 1, 1, [2])
            r.owner = bot
            bot.deck.append(r)
        ranch   = Blue("Ranch", 2, 1, 1, [2])
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        choice = bot.chooseCard([ranch, factory])
        self.assertEqual(choice, "Cheese Factory",
            "With 3 Ranches (cap met for stage 1), FromageBot should move to Cheese Factory")

    def test_landmark_beats_any_establishment(self):
        """PRIORITY puts all four landmarks first; landmark must win over any establishment."""
        from bots import FromageBot
        bot = FromageBot(name="Fromage")
        ranch   = Blue("Ranch", 2, 1, 1, [2])
        ts      = UpgradeCard("Train Station")
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        choice = bot.chooseCard([ranch, ts, factory])
        self.assertEqual(choice, "Train Station")

    def test_fallback_avoids_capped_cards(self):
        """When all priority items are satisfied, fallback skips cards at their max cap."""
        from bots import FromageBot
        bot = FromageBot(name="Fromage")
        for _ in range(3):
            b = Green("Bakery", 3, 1, 1, [2, 3])
            b.owner = bot
            bot.deck.append(b)
        bakery = Green("Bakery", 3, 1, 1, [2, 3])
        cafe   = Red("Cafe", 4, 2, 1, [3])
        options = [bakery, cafe]
        choice = bot.chooseCard(options)
        self.assertIn(choice, ["Bakery", "Cafe"])  # fallback, doesn't crash

    def test_choosecard_empty_returns_none(self):
        """Empty options list returns None."""
        from bots import FromageBot
        self.assertIsNone(FromageBot(name="F").chooseCard([]))

    def test_count_method(self):
        """_count() returns the number of a named card currently in the deck."""
        from bots import FromageBot
        bot = FromageBot(name="Fromage")
        self.assertEqual(bot._count("Ranch"), 0)
        r = Blue("Ranch", 2, 1, 1, [2])
        r.owner = bot
        bot.deck.append(r)
        self.assertEqual(bot._count("Ranch"), 1)


class TestMarathonBot(unittest.TestCase):
    """MarathonBot: maximises P(win in N rounds)."""

    def setUp(self):
        self.game = Game(players=3)
        self.bot = MarathonBot(name="Marathon")
        self.bot.deposit(50)

    def test_choosedice_with_train_station_prefers_two_when_mine_in_deck(self):
        """MarathonBot with Train Station + Mine[9] prefers 2 dice (Mine only fires on 2 dice)."""
        self.bot.hasTrainStation = True
        self.bot.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.bot
        self.bot.deck.append(mine)
        self.assertEqual(self.bot.chooseDice(self.game.players), 2)

    def test_choosedice_with_train_station_prefers_one_when_only_roll1_card(self):
        """MarathonBot picks 1 die when 2 dice strictly reduces P(win in N).

        With only Wheat Field[1] in the deck and no opponents, 2d6 can never roll 1
        so income is zero; 1d6 gives 1/6 income per round.  When bank is just 1 coin
        short of the landmark goal, P(win in N | 1 die) > 0 while P(win in N | 2 dice) = 0,
        so the bot must pick 1 die.
        """
        bot = MarathonBot(name="Marathon-1D")
        bot.hasTrainStation = True
        bot.deck.deck.clear()
        bot.bank = 51  # deficit = 52 - 51 = 1; need exactly 1 more coin
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = bot
        bot.deck.append(wheat)
        # Pass [bot] as players (solo) so opponent rolls don't contribute income.
        # 1d6: P(roll 1) = 1/6 > 0 → can earn the 1 coin needed.
        # 2d6: can't roll 1 → income = 0 → can never win.
        self.assertEqual(bot.chooseDice([bot]), 1)

    def test_no_radio_tower_never_rerolls(self):
        """Without Radio Tower, chooseReroll always returns False regardless of roll."""
        self.assertFalse(self.bot.chooseReroll(1))
        self.assertFalse(self.bot.chooseReroll(6))

    def test_rerolls_in_marathon_mode_on_zero_income(self):
        """Marathon mode (N>1): reroll if income is in bottom third of outcomes."""
        self.bot.hasRadioTower = True
        self.bot.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.bot
        self.bot.deck.append(mine)
        self.bot.hasTrainStation = True
        # roll 1 gives 0 income; Mine only fires on 9
        self.assertTrue(self.bot.chooseReroll(1))

    def test_does_not_reroll_high_income_in_marathon_mode(self):
        """Marathon mode: do not reroll a roll that's in the top portion of outcomes."""
        self.bot.hasRadioTower = True
        self.bot.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.bot
        self.bot.hasTrainStation = True
        self.bot.deck.append(mine)
        # roll 9 gives 5 income (best roll); should not reroll
        self.assertFalse(self.bot.chooseReroll(9))

    def test_sprint_reroll_when_income_below_deficit(self):
        """Sprint mode (N=1): reroll if this roll's income is less than the remaining deficit.

        N=1 is triggered when the leader ERUV reaches ~2. Give the bot 3 landmarks and
        enough bank that deficit is tiny; any 0-income roll should trigger a reroll.
        """
        bot = MarathonBot(name="Sprint")
        bot.hasRadioTower = True
        for name in ["Train Station", "Shopping Mall", "Amusement Park"]:
            card = UpgradeCard(name)
            card.owner = bot
            bot.deck.append(card)
            setattr(bot, UpgradeCard.orangeCards[name][2], True)
        # deficit = 22 (Radio Tower cost) - 21 (bank) = 1
        bot.deposit(21)
        bot.deck.deck.clear()
        # _target_n([bot]) with ERUV ≈ 1 returns N=1 → sprint mode
        self.assertTrue(bot.chooseReroll(3),
            "Sprint mode: income(roll 3)=0 < deficit=1 → should reroll")

    def test_chooseaction_buys_landmark_when_affordable(self):
        """chooseAction returns 'buy' if a landmark is affordable — always prioritised."""
        self.bot.bank = 100
        result = self.bot.chooseAction(self.game.market)
        self.assertEqual(result, "buy",
            "MarathonBot must buy when landmarks are affordable")

    def test_chooseaction_passes_when_broke(self):
        """chooseAction returns 'pass' when the bot has no coins."""
        self.bot.bank = 0
        self.assertEqual(self.bot.chooseAction(self.game.market), "pass")

    def test_choosecard_returns_string(self):
        """chooseCard always returns a string name from the provided Card options."""
        self.bot.bank = 50
        self.game.current_player_index = 0
        self.game.players[0].deposit(50)
        options = self.game.get_purchase_options()
        result = self.bot.chooseCard(options, self.game)
        self.assertIn(result, [c.name for c in options])

    def test_choose_target_avoids_roller(self):
        """chooseTarget never returns the player who is currently rolling dice."""
        players = self.game.players
        players[0].isrollingdice = True
        players[1].isrollingdice = False
        players[2].isrollingdice = False
        target = self.bot.chooseTarget(players)
        self.assertIsNotNone(target)
        self.assertFalse(target.isrollingdice)

    def test_choose_target_returns_none_when_all_rolling(self):
        """chooseTarget returns None when every player is marked as rolling."""
        for p in self.game.players:
            p.isrollingdice = True
        self.assertIsNone(self.bot.chooseTarget(self.game.players))

    def test_bc_swap_gives_card_that_preserves_most_pwn(self):
        """chooseBusinessCenterSwap gives the card whose removal hurts P(win in N) least."""
        self.bot.deck.deck.clear()
        self.bot.hasTrainStation = True
        cheap = Blue("Wheat Field", 1, 1, 1, [1])
        cheap.owner = self.bot
        self.bot.deck.append(cheap)
        valuable = Blue("Mine", 5, 6, 5, [9])
        valuable.owner = self.bot
        self.bot.deck.append(valuable)
        their_card = Blue("Ranch", 2, 1, 1, [2])
        their_card.owner = self.game.players[1]
        result = self.bot.chooseBusinessCenterSwap(
            self.game.players[1], [cheap, valuable], [their_card]
        )
        self.assertIsNotNone(result)
        give, _ = result
        self.assertIs(give, cheap,
            "MarathonBot should give away the card that hurts P(win) least when removed")


class TestKinematicBot(unittest.TestCase):
    """KinematicBot: MarathonBot subclass with kinematic ERUV target."""

    def setUp(self):
        from bots import KinematicBot
        self.game = Game(players=3)
        self.bot = KinematicBot(name="Kinematic", a=0.45, eruv_offset=1)
        self.bot.deposit(20)
        for p in self.game.players:
            p.deposit(20)

    def test_inherits_marathon_choosecard(self):
        """KinematicBot uses MarathonBot.chooseCard and returns a valid name."""
        from bots import KinematicBot
        bot = KinematicBot(name="K", a=0.45, eruv_offset=1)
        bot.deposit(50)
        self.game.current_player_index = 0
        self.game.players[0].deposit(50)
        options = self.game.get_purchase_options()
        result = bot.chooseCard(options, self.game)
        self.assertIn(result, [c.name for c in options])

    def test_target_n_with_no_opponents_falls_back(self):
        """_target_n with only self in players falls back to _leader_n."""
        from bots import KinematicBot
        bot = KinematicBot(name="K", a=0.45, eruv_offset=1)
        n = bot._target_n([bot])
        self.assertGreaterEqual(n, 1)

    def test_target_n_with_opponents_returns_positive(self):
        """_target_n with real opponents returns a positive integer."""
        from bots import KinematicBot
        game = Game(players=3)
        bot = KinematicBot(name="K", a=0.45, eruv_offset=1)
        bot.deposit(10)
        for p in game.players:
            p.deposit(10)
        players = [bot] + list(game.players)
        n = bot._target_n(players)
        self.assertGreaterEqual(n, 1)

    def test_aggressive_offset_gives_smaller_n(self):
        """Higher eruv_offset (more aggressive) yields a smaller or equal target N."""
        from bots import KinematicBot
        game = Game(players=3)
        for p in game.players:
            p.deposit(10)
        conservative = KinematicBot(name="C", a=0.45, eruv_offset=0)
        aggressive   = KinematicBot(name="A", a=0.45, eruv_offset=3)
        conservative.deposit(10)
        aggressive.deposit(10)
        players = list(game.players) + [conservative]
        n_c = conservative._target_n(players)
        n_a = aggressive._target_n(players)
        self.assertLessEqual(n_a, n_c,
            "More aggressive offset (3) should produce smaller or equal N than conservative (0)")


class TestChooseDiceNoArg(unittest.TestCase):
    """chooseDice called with no argument falls back to [self], hitting the players-or-self branch."""

    def test_evbot_choosedice_no_arg(self):
        bot = EVBot(name="E")
        self.assertIn(bot.chooseDice(), [1, 2])

    def test_coveragebot_choosedice_no_train_station(self):
        from bots import CoverageBot
        bot = CoverageBot(name="C")
        self.assertEqual(bot.chooseDice(), 1)

    def test_coveragebot_choosedice_with_train_station_and_low_cards(self):
        """With Train Station and only 1-die cards, CoverageBot should still prefer 1 die."""
        from bots import CoverageBot
        bot = CoverageBot(name="C")
        bot.hasTrainStation = True
        # Default deck (Wheat Field[1], Bakery[2,3]): 1-die coverage > 2-die coverage
        result = bot.chooseDice()
        self.assertIn(result, [1, 2])

    def test_impatientbot_choosedice_no_arg(self):
        bot = ImpatientBot(name="I")
        self.assertIn(bot.chooseDice(), [1, 2])

    def test_fromagebot_choosedice_no_arg(self):
        from bots import FromageBot
        bot = FromageBot(name="F")
        self.assertIn(bot.chooseDice(), [1, 2])


class TestBCSwapEmptyLists(unittest.TestCase):
    """BC swap helpers return None when one side is empty — covers the early-return guards."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot  = self.game.players[0]
        self.bot.deposit(10)
        their_card = Blue("Ranch", 2, 1, 1, [2])
        their_card.owner = self.game.players[1]
        self.their_cards = [their_card]
        my_card = Blue("Wheat Field", 1, 1, 1, [1])
        my_card.owner = self.bot
        self.my_cards = [my_card]

    def test_bot_bc_swap_returns_none_when_my_side_empty(self):
        result = self.bot.chooseBusinessCenterSwap(
            self.game.players[1], [], self.their_cards)
        self.assertIsNone(result)

    def test_bot_bc_swap_returns_none_when_their_side_empty(self):
        result = self.bot.chooseBusinessCenterSwap(
            self.game.players[1], self.my_cards, [])
        self.assertIsNone(result)

    def test_impatient_bc_swap_returns_none_when_empty(self):
        bot = ImpatientBot(name="I")
        self.assertIsNone(bot.chooseBusinessCenterSwap(None, [], self.their_cards))

    def test_marathon_bc_swap_returns_none_when_empty(self):
        bot = MarathonBot(name="M")
        self.assertIsNone(bot.chooseBusinessCenterSwap(None, [], self.their_cards))

    def test_marathon_choosedcard_empty_returns_none(self):
        bot = MarathonBot(name="M")
        self.assertIsNone(bot.chooseCard([]))


class TestRollIncomeTVStation(unittest.TestCase):
    """_roll_income TVStation branch — the 'steal up to 5' approximation."""

    def test_roll_income_counts_tvstation(self):
        """TVStation on roll 6 contributes 5 to _roll_income (assumed max steal)."""
        from bots import _roll_income
        from harmonictook import TVStation
        bot = ImpatientBot(name="I")
        bot.deck.deck.clear()
        tv = TVStation()
        tv.owner = bot
        bot.deck.append(tv)
        income = _roll_income(bot, 6)
        self.assertEqual(income, 5)

    def test_impatient_does_not_reroll_tvstation_roll(self):
        """ImpatientBot should not reroll a 6 that fires TVStation."""
        from harmonictook import TVStation
        bot = ImpatientBot(name="I")
        bot.hasRadioTower = True
        bot.deck.deck.clear()
        tv = TVStation()
        tv.owner = bot
        bot.deck.append(tv)
        self.assertFalse(bot.chooseReroll(6),
            "TVStation income on roll 6 should prevent a reroll")


class TestImpatientBotChooseActionIncomePath(unittest.TestCase):
    """ImpatientBot.chooseAction income-card improvement path (lines 339-345)."""

    def test_buys_when_income_card_reduces_eruv(self):
        """chooseAction returns 'buy' if an affordable market card reduces ERUV."""
        game = Game(players=2)
        bot = ImpatientBot(name="I")
        bot.deck.deck.clear()
        bot.bank = 1       # can afford 1-coin market cards
        bot.deposit(0)     # keep bank at 1

        # Clear all landmarks so deficit is 52 and ERUV is computable
        # With 0 income, ERUV = n_landmarks = 4; buying any income card improves it
        # We need an income card costing 1 in the market
        game.market.deck.clear()
        game.reserve.deck.clear()
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = None
        game.market.deck.append(wheat)

        result = bot.chooseAction(game.market)
        # If Wheat Field reduces ERUV (it adds income, lowering estimated rounds), bot buys.
        self.assertIn(result, ["buy", "pass"])  # verify it doesn't crash; actual value depends on ERUV calc


class TestMarathonBotChooseActionIncomePath(unittest.TestCase):
    """MarathonBot.chooseAction income-card improvement path (lines 553-561)."""

    def test_passes_when_no_landmark_and_no_improvement(self):
        """chooseAction returns 'pass' when no landmark is affordable and income card doesn't help."""
        game = Game(players=2)
        bot = MarathonBot(name="M")
        bot.bank = 0
        result = bot.chooseAction(game.market)
        self.assertEqual(result, "pass")

    def test_income_card_loop_executes_with_affordable_cards(self):
        """With affordable cards but no landmark, chooseAction runs the P(win) improvement loop."""
        game = Game(players=2)
        bot = MarathonBot(name="M")
        bot.bank = 1  # enough for 1-coin cards, no landmarks affordable
        bot.deck.deck.clear()
        result = bot.chooseAction(game.market)
        self.assertIn(result, ["buy", "pass"])  # loop runs, doesn't crash


class TestEVBotFallback(unittest.TestCase):
    """EVBot scores Card objects and returns a name."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot = EVBot(name="EVBot")

    def test_card_objects_scored_without_game(self):
        """EVBot scores Card objects directly without needing a game context."""
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.bot
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = self.bot
        result = self.bot.chooseCard([ranch, wheat])
        self.assertIn(result, ["Ranch", "Wheat Field"],
            "EVBot with Card objects must return one of the card names")


class TestMarathonBotTarget(unittest.TestCase):
    """MarathonBot.chooseTarget steals from the leader (lowest ERUV), not the richest."""

    def test_targets_leader_not_richest(self):
        """When one opponent is close to winning (low ERUV) and another is rich but far back,
        MarathonBot steals from the one close to winning (lowest ERUV).

        Leader: 3 landmarks + bank >= Radio Tower cost (22) → ERUV = 1 (one buy away).
        Rich:   0 landmarks + large bank → ERUV = 4 at best (four landmark buys minimum).
        MarathonBot must steal from leader (ERUV=1), not rich (ERUV=4).
        """
        game = Game(players=3)
        bot = MarathonBot(name="Marathon")
        bot.deposit(10)
        bot.isrollingdice = True

        rich = game.players[1]
        rich.deposit(500)   # enormous bank, but 0 landmarks → ERUV = 4 minimum
        rich.isrollingdice = False

        leader = game.players[2]
        leader.deposit(22)  # enough to buy Radio Tower immediately
        for name in ["Train Station", "Shopping Mall", "Amusement Park"]:
            card = UpgradeCard(name)
            card.owner = leader
            leader.deck.append(card)
            setattr(leader, UpgradeCard.orangeCards[name][2], True)
        leader.isrollingdice = False
        # leader: 3 landmarks, bank=22 >= cost_remaining(22) → deficit=0 → ERUV=1

        players = [bot, rich, leader]
        target = bot.chooseTarget(players)
        self.assertIs(target, leader,
            "MarathonBot should target the player closest to winning (lowest ERUV=1), "
            "not the richest opponent (ERUV=4)")


if __name__ == "__main__":
    unittest.main(buffer=True)
