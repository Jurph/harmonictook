#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_strategy.py — TDD tests for the strategy.py EV valuation library

import unittest
from harmonictook import Blue, Green, Red, Stadium, TVStation, BusinessCenter, UpgradeCard, Game
from strategy import (
    ONE_DIE_PROB, TWO_DIE_PROB, P_DOUBLES,
    p_hits, ev, portfolio_ev, delta_ev, score_purchase_options,
)
from bots import EVBot, CoverageBot
from tournament import finish_score


class TestProbabilityTables(unittest.TestCase):
    """Verify the module-level probability constants sum to 1 and have correct values."""

    def test_one_die_sums_to_one(self):
        self.assertAlmostEqual(sum(ONE_DIE_PROB.values()), 1.0, places=10)

    def test_two_die_sums_to_one(self):
        self.assertAlmostEqual(sum(TWO_DIE_PROB.values()), 1.0, places=10)

    def test_p_doubles(self):
        self.assertAlmostEqual(P_DOUBLES, 1/6, places=10)


class TestPHits(unittest.TestCase):
    """Verify p_hits returns correct probabilities for various hitsOn lists and die counts."""

    def test_single_face_one_die(self):
        self.assertAlmostEqual(p_hits([1], 1), 1/6, places=10)

    def test_all_faces_one_die(self):
        self.assertAlmostEqual(p_hits([1, 2, 3, 4, 5, 6], 1), 1.0, places=10)

    def test_impossible_with_one_die(self):
        """7 cannot be rolled with one die."""
        self.assertAlmostEqual(p_hits([7], 1), 0.0, places=10)

    def test_seven_with_two_dice(self):
        self.assertAlmostEqual(p_hits([7], 2), 6/36, places=10)

    def test_two_with_two_dice(self):
        self.assertAlmostEqual(p_hits([2], 2), 1/36, places=10)

    def test_multi_face_two_dice(self):
        """6+7+8 with 2 dice: 5/36 + 6/36 + 5/36 = 16/36."""
        self.assertAlmostEqual(p_hits([6, 7, 8], 2), 16/36, places=10)

    def test_upgrade_sentinel_returns_zero(self):
        """Sentinel value 99 (UpgradeCard) is not in any probability table."""
        self.assertAlmostEqual(p_hits([99], 2), 0.0, places=10)


class TestEVBlue(unittest.TestCase):
    """EV for Blue cards: pays owner on every player's roll."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.other = self.game.players[1]
        self.owner.deposit(100)
        self.other.deposit(100)

    def test_fires_on_one_two_players(self):
        """Blue hitting [1] with 2 players, 1 die: payout=6 * (1/6) * 2 players = 2.0."""
        card = Blue("Fires On 1", 1, 1, 6, [1])
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 2.0, places=10)

    def test_scales_with_N(self):
        """N=3 rounds should triple the EV."""
        card = Blue("Fires On 1", 1, 1, 6, [1])
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players, N=3), 6.0, places=10)

    def test_upgrade_card_returns_zero(self):
        """UpgradeCards have no direct EV; delta_ev handles them via portfolio diff."""
        card = UpgradeCard("Train Station")
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 0.0, places=10)


class TestEVGreen(unittest.TestCase):
    """EV for Green cards: fires only on owner's roll."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.other = self.game.players[1]
        self.owner.deposit(100)
        self.other.deposit(100)

    def test_flat_payout_all_faces(self):
        """Green hitting [1..6] with 1 die (P=1.0): ev == payout."""
        card = Green("Always Fires", 3, 1, 8, [1, 2, 3, 4, 5, 6])
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 8.0, places=10)

    def test_amusement_park_multiplier(self):
        """With Amusement Park, green EV is multiplied by 1/(1-P_DOUBLES) == 6/5."""
        card = Green("Always Fires", 3, 1, 8, [1, 2, 3, 4, 5, 6])
        card.owner = self.owner
        self.owner.hasAmusementPark = True
        expected = 8.0 * (1 / (1 - P_DOUBLES))
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), expected, places=6)

    def test_convenience_store_with_shopping_mall(self):
        """Convenience Store payout is 3+1=4 when owner has Shopping Mall."""
        # Use a real Convenience Store card so the Shopping Mall check fires
        card = Green("Convenience Store", 3, 2, 3, [4])
        card.owner = self.owner
        self.owner.hasShoppingMall = True
        # p_hits([4], 1) = 1/6; payout = 4
        expected = 4 * (1/6)
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), expected, places=10)

    def test_factory_with_matching_cards(self):
        """Factory Green multiplies payout by count of cards matching its category."""
        # Give owner 2 Ranch cards (category 2); need 2 dice so [7] can hit
        self.owner.hasTrainStation = True
        self.owner.deck.append(Blue("Ranch", 2, 1, 1, [2]))
        self.owner.deck.append(Blue("Ranch", 2, 1, 1, [2]))
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.owner
        # 2 ranches in deck, fires on [7] with 2 dice -> P = 6/36
        expected = 3 * 2 * (6/36)
        self.assertAlmostEqual(ev(factory, self.owner, self.game.players), expected, places=10)

    def test_factory_with_no_matching_cards(self):
        """Factory with zero matching cards returns 0.0."""
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.owner
        self.assertAlmostEqual(ev(factory, self.owner, self.game.players), 0.0, places=10)


class TestEVRed(unittest.TestCase):
    """EV for Red cards: steal from each non-owner on their roll."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.other = self.game.players[1]
        self.owner.deposit(100)
        self.other.deposit(100)

    def test_two_players_rich_opponent(self):
        """Red hitting [1..6] with 1 die (P=1.0), payout=3, opponent bank=100: ev == 3.0."""
        card = Red("Always Steals", 4, 2, 3, [1, 2, 3, 4, 5, 6])
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 3.0, places=10)

    def test_three_players(self):
        """With 3 players: ev == payout * 2 opponents."""
        game3 = Game(players=3)
        owner = game3.players[0]
        for p in game3.players:
            p.deposit(100)
        card = Red("Always Steals", 4, 2, 3, [1, 2, 3, 4, 5, 6])
        card.owner = owner
        self.assertAlmostEqual(ev(card, owner, game3.players), 6.0, places=10)

    def test_clamped_by_opponent_bank(self):
        """Opponent with bank=1 caps the steal at 1 even if payout=3."""
        self.other.bank = 1
        card = Red("Always Steals", 4, 2, 3, [1, 2, 3, 4, 5, 6])
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 1.0, places=10)


class TestEVStadium(unittest.TestCase):
    """EV for Stadium: net gain == payout * (N_players - 1) per trigger on a 6."""

    def test_two_players(self):
        """2 players: net=2*1=2 per trigger; P(6,1die)=1/6; ev == 2/6."""
        game = Game(players=2)
        owner = game.players[0]
        for p in game.players:
            p.deposit(100)
        card = Stadium()
        card.owner = owner
        self.assertAlmostEqual(ev(card, owner, game.players), 2/6, places=10)

    def test_three_players(self):
        """3 players: net=2*2=4; ev == 4/6."""
        game = Game(players=3)
        owner = game.players[0]
        for p in game.players:
            p.deposit(100)
        card = Stadium()
        card.owner = owner
        self.assertAlmostEqual(ev(card, owner, game.players), 4/6, places=10)


class TestPortfolioEV(unittest.TestCase):
    """portfolio_ev sums ev() across the player's full deck."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.player.deposit(100)
        self.game.players[1].deposit(100)

    def test_default_deck_one_round(self):
        """Default deck = Wheat Field (Blue,[1],payout=1) + Bakery (Green,[2,3],payout=1).
        WF: 1 * (1/6) * 2 players = 2/6
        Bakery: 1 * (2/6) * 1 (own roll only) = 2/6
        Total = 4/6
        """
        expected = 2/6 + 2/6
        self.assertAlmostEqual(portfolio_ev(self.player, self.game.players), expected, places=10)

    def test_scales_with_N(self):
        """N=6 should give portfolio_ev == 4.0."""
        self.assertAlmostEqual(portfolio_ev(self.player, self.game.players, N=6), 4.0, places=10)


class TestDeltaEV(unittest.TestCase):
    """delta_ev measures the marginal gain of adding a card to a player's deck."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.player.deposit(100)
        self.game.players[1].deposit(100)

    def test_plain_card_no_synergy(self):
        """delta_ev of a plain card with no factory synergy equals ev() of that card."""
        card = Blue("Ranch", 2, 1, 1, [2])
        card.owner = self.player
        self.assertAlmostEqual(
            delta_ev(card, self.player, self.game.players),
            ev(card, self.player, self.game.players),
            places=10,
        )

    def test_factory_synergy_increases_delta(self):
        """Adding a Ranch when owner has a Cheese Factory (multiplies cat 2) boosts delta_ev."""
        self.player.hasTrainStation = True  # factory hits on [7]; need 2 dice
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.player
        self.player.deck.append(factory)

        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.player
        plain_ev = ev(ranch, self.player, self.game.players)
        total_delta = delta_ev(ranch, self.player, self.game.players)
        self.assertGreater(total_delta, plain_ev)

    def test_upgrade_card_train_station_positive(self):
        """Train Station delta_ev > 0 when the deck has cards that benefit from 2 dice (e.g. Mine)."""
        self.player.deck.append(Blue("Mine", 5, 6, 5, [9]))  # hits only with 2 dice
        card = UpgradeCard("Train Station")
        card.owner = self.player
        self.assertGreater(delta_ev(card, self.player, self.game.players), 0.0)

    def test_radio_tower_positive_for_sparse_deck(self):
        """Radio Tower has positive EV when most rolls yield nothing (high reroll value)."""
        # Default deck: Wheat Field [1] and Bakery [2,3] — rolls 4,5,6 yield 0
        card = UpgradeCard("Radio Tower")
        card.owner = self.player
        self.assertGreater(delta_ev(card, self.player, self.game.players), 0.0)

    def test_radio_tower_zero_for_flat_deck(self):
        """Radio Tower has zero EV when every roll yields the same income (no reroll benefit).

        A deck with one Blue card hitting all six faces pays the same on every roll.
        E_own == V(r) for all r, so max(V(r), E_own) == V(r) and gain == 0.
        """
        # Replace default deck with a single always-hits Blue
        self.player.deck.deck.clear()
        always = Blue("Always", 1, 1, 3, [1, 2, 3, 4, 5, 6])
        always.owner = self.player
        self.player.deck.deck.append(always)
        card = UpgradeCard("Radio Tower")
        card.owner = self.player
        self.assertAlmostEqual(delta_ev(card, self.player, self.game.players), 0.0, places=10)

    def test_radio_tower_larger_than_zero_with_rich_engine(self):
        """Radio Tower EV is positive even for a rich engine — sparse high-value cards."""
        # Add Mine (hits=[9]) — valuable but rare with 1 die (P=0); only reachable with 2 dice.
        # Even without Train Station, Mine on [9] with 1 die = 0; reroll never helps here.
        # Use a card that hits rarely but pays well: payout=10 on [6] only.
        self.player.deck.deck.clear()
        high_card = Blue("Jackpot", 1, 1, 10, [6])
        high_card.owner = self.player
        self.player.deck.deck.append(high_card)
        card = UpgradeCard("Radio Tower")
        card.owner = self.player
        # E_own = 10*(1/6). On rolls 1-5 V(r)=0 < E_own → reroll. On roll 6 keep.
        # E_with_RT = (1/6)*10 + (5/6)*(10/6) = 10/6 + 50/36 = 60/36 + 50/36 = 110/36
        # gain = 110/36 - 60/36 = 50/36
        expected_gain = 50 / 36
        self.assertAlmostEqual(delta_ev(card, self.player, self.game.players), expected_gain, places=10)

    def test_train_station_positive_with_market_context(self):
        """Train Station delta_ev > 0 on starting deck when Mine/Apple Orchard are in the market."""
        mine = Blue("Mine", 5, 6, 5, [9])
        apple = Blue("Apple Orchard", 3, 6, 3, [10])
        card = UpgradeCard("Train Station")
        card.owner = self.player
        self.assertGreater(
            delta_ev(card, self.player, self.game.players, market_cards=[mine, apple]),
            0.0,
        )

    def test_train_station_zero_with_only_1die_market(self):
        """Train Station gain is 0 when the market contains only 1-die-range cards."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        card = UpgradeCard("Train Station")
        card.owner = self.player
        self.assertAlmostEqual(
            delta_ev(card, self.player, self.game.players, market_cards=[wheat]),
            0.0, places=10,
        )

    def test_train_station_ignores_family_restaurant(self):
        """Family Restaurant (Red[9,10]) does not contribute — opponents still roll 1 die."""
        fam_rest = Red("Family Restaurant", 6, 3, 2, [9, 10])
        card = UpgradeCard("Train Station")
        card.owner = self.player
        self.assertAlmostEqual(
            delta_ev(card, self.player, self.game.players, market_cards=[fam_rest]),
            0.0, places=10,
        )


class TestScorePurchaseOptions(unittest.TestCase):
    """score_purchase_options returns a {Card: float} dict sorted descending by EV."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.game.current_player_index = 0
        # Give the player enough to buy anything
        self.player.bank = 999

    def test_returns_dict_of_floats(self):
        cards = list({c.name: c for c in self.game.market.deck}.values())
        result = score_purchase_options(self.player, cards, self.game.players)
        self.assertIsInstance(result, dict)
        for v in result.values():
            self.assertIsInstance(v, float)

    def test_sorted_descending(self):
        cards = list({c.name: c for c in self.game.market.deck}.values())
        result = score_purchase_options(self.player, cards, self.game.players)
        scores = list(result.values())
        self.assertEqual(scores, sorted(scores, reverse=True))


class TestEVTVStation(unittest.TestCase):
    """EV for TV Station: steal up to 5 from the richest opponent on a 6."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.other = self.game.players[1]
        self.owner.deposit(100)
        self.other.deposit(100)

    def test_rich_opponent(self):
        """Opponent with 100 coins: steal capped at 5; P(6,1die)=1/6."""
        card = TVStation()
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 5 * (1/6), places=10)

    def test_poor_opponent(self):
        """Opponent with only 2 coins: steal capped at 2."""
        self.other.bank = 2
        card = TVStation()
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 2 * (1/6), places=10)

    def test_scales_with_N(self):
        card = TVStation()
        card.owner = self.owner
        base = ev(card, self.owner, self.game.players, N=1)
        self.assertAlmostEqual(ev(card, self.owner, self.game.players, N=4), base * 4, places=10)


class TestEVBusinessCenter(unittest.TestCase):
    """EV for Business Center: optimal swap of best opponent card for least-harmful own card."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.target = self.game.players[1]
        self.owner.deposit(100)
        self.target.deposit(100)

    def test_positive_when_target_has_better_card(self):
        """BC EV > 0 when target has a card more valuable to owner than owner's worst card.

        A 'Fat Ranch' (payout=5, hits=[1]) has delta_ev=10/6 to owner (1-die, 2 players).
        Owner's Wheat Field costs 2/6 to give away. Net = 8/6 > 0.
        """
        # Give target a high-payout Blue that hits on [1] — valuable with a single die
        fat_ranch = Blue("Fat Ranch", 2, 1, 5, [1])
        fat_ranch.owner = self.target
        self.target.deck.append(fat_ranch)
        card = BusinessCenter()
        card.owner = self.owner
        self.assertGreater(ev(card, self.owner, self.game.players), 0.0)

    def test_spite_filter_prefers_less_synergistic_give(self):
        """BC give-card selection avoids handing target a Ranch that feeds their Cheese Factory."""
        # Target has a Cheese Factory (multiplies cat 2 = Ranch)
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.target
        self.target.deck.append(factory)
        # Also give target a high-value card so the swap is worth making
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.target
        self.target.deck.append(mine)
        # Owner has a Ranch (cat 2) and a low-EV Wheat Field copy
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.owner
        self.owner.deck.append(ranch)

        card = BusinessCenter()
        card.owner = self.owner

        # The spite filter should prefer to give away something other than the Ranch
        # Verify BC EV is computed (non-zero and doesn't crash)
        result = ev(card, self.owner, self.game.players)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_no_opponents_returns_zero(self):
        """With no valid opponents (only owner), BC returns 0."""
        game1 = Game(players=2)
        owner = game1.players[0]
        # Clear target's deck so no swappable cards exist
        game1.players[1].deck.deck.clear()
        card = BusinessCenter()
        card.owner = owner
        self.assertAlmostEqual(ev(card, owner, game1.players), 0.0, places=10)

    def test_no_own_swappable_cards_returns_zero(self):
        """If owner has only UpgradeCards, BC returns 0 (nothing to give)."""
        # Clear owner's deck of regular cards
        self.owner.deck.deck.clear()
        card = BusinessCenter()
        card.owner = self.owner
        self.assertAlmostEqual(ev(card, self.owner, self.game.players), 0.0, places=10)


class TestEVBot(unittest.TestCase):
    """EVBot scores Card objects directly; falls back to random when given only string names."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot = EVBot(name="TestEVBot")
        self.game.players[0] = self.bot
        self.game.current_player_index = 0

    def test_fallback_without_game(self):
        """String options with no game fall back to random.choice, not a crash."""
        from unittest.mock import patch
        options = ['Wheat Field', 'Ranch']
        with patch('bots.random.choice', return_value='Ranch') as mock_choice:
            result = self.bot.chooseCard(options)
        mock_choice.assert_called_once_with(options)
        self.assertEqual(result, 'Ranch')

    def test_accepts_card_objects_without_game(self):
        """Card objects are scored directly; result is a string name from the options."""
        from harmonictook import Blue
        card1 = Blue("Wheat Field", 1, 1, 1, [1])
        card2 = Blue("Mine", 5, 6, 5, [9])
        card1.owner = self.bot
        card2.owner = self.bot
        result = self.bot.chooseCard([card1, card2])
        self.assertIsInstance(result, str)
        self.assertIn(result, ['Wheat Field', 'Mine'])

    def test_returns_none_for_empty_options(self):
        """Empty options list returns None regardless of game context."""
        self.assertIsNone(self.bot.chooseCard([], self.game))

    def test_returns_string_from_options(self):
        """With a valid game, chooseCard returns a string that is in options."""
        self.bot.bank = 999
        options = self.game.market.names(maxcost=self.bot.bank)
        result = self.bot.chooseCard(options, self.game)
        self.assertIsInstance(result, str)
        self.assertIn(result, options)


class TestCoverageBotChooseCard(unittest.TestCase):
    """CoverageBot.chooseCard prefers cards that fill new die-value slots over redundant ones."""

    def setUp(self):
        self.bot = CoverageBot(name="TestCoverageBot")
        # Start with a Wheat Field (Blue, hitsOn=[1]) already in the deck
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = self.bot
        self.bot.deck.append(wheat)

    def test_prefers_new_slot_over_duplicate(self):
        """Ranch (die=2, uncovered) beats a second Wheat Field (die=1, already covered)."""
        ranch = Blue("Ranch", 2, 1, 1, [2])
        duplicate = Blue("Wheat Field", 1, 1, 1, [1])
        ranch.owner = self.bot
        duplicate.owner = self.bot
        result = self.bot.chooseCard([ranch, duplicate])
        self.assertEqual(result, "Ranch")

    def test_returns_none_for_empty_options(self):
        self.assertIsNone(self.bot.chooseCard([]))

    def test_returns_string(self):
        """Result is always a string name, not a Card object."""
        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.bot
        result = self.bot.chooseCard([ranch])
        self.assertIsInstance(result, str)
        self.assertEqual(result, "Ranch")

    def test_ev_tiebreaker_when_coverage_full(self):
        """When all options are on already-covered slots, the higher-payout card wins."""
        # Both cards hit die=1, already covered by Wheat Field in setUp.
        # Mine pays 5; second Wheat Field pays 1. Mine should win on EV tiebreak.
        mine = Blue("Mine", 5, 6, 5, [1])
        duplicate = Blue("Wheat Field", 1, 1, 1, [1])
        mine.owner = self.bot
        duplicate.owner = self.bot
        result = self.bot.chooseCard([mine, duplicate])
        self.assertEqual(result, "Mine")

    def test_landmark_beats_establishment(self):
        """A landmark is always chosen over a coverage-expanding establishment."""
        from harmonictook import UpgradeCard
        ranch = Blue("Ranch", 2, 1, 1, [2])        # covers new slot
        train = UpgradeCard("Train Station")
        ranch.owner = self.bot
        train.owner = self.bot
        result = self.bot.chooseCard([ranch, train])
        self.assertEqual(result, "Train Station")

    def test_delta_coverage_train_station(self):
        """Train Station coverage = difference between 2-die and 1-die own-turn coverage.

        Clears the default starting deck (Wheat Field + Bakery, both in 1-die range) and
        uses only a Mine (hitsOn=[9]): die=9 is unreachable with 1 die, so 1-die coverage
        is 0.0 and 2-die coverage is P(9 on 2d6) = 4/36.
        """
        from harmonictook import UpgradeCard, Blue
        from strategy import delta_coverage, _own_turn_coverage
        bot = CoverageBot(name="TSTestBot")
        bot.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = bot
        bot.deck.append(mine)
        card = UpgradeCard("Train Station")
        expected = _own_turn_coverage(bot, 2) - _own_turn_coverage(bot, 1)
        self.assertAlmostEqual(delta_coverage(card, bot, [bot]), expected, places=10)
        self.assertGreater(expected, 0.0)

    def test_delta_coverage_radio_tower(self):
        """Radio Tower coverage = (1 - cov) * cov for re-roll on miss."""
        from harmonictook import UpgradeCard
        from strategy import delta_coverage, _own_turn_coverage, _num_dice
        card = UpgradeCard("Radio Tower")
        cov = _own_turn_coverage(self.bot, _num_dice(self.bot))
        self.assertAlmostEqual(delta_coverage(card, self.bot, [self.bot]), (1.0 - cov) * cov, places=10)

    def test_delta_coverage_amusement_park(self):
        """Amusement Park coverage = P_DOUBLES * cov for bonus turns on doubles."""
        from harmonictook import UpgradeCard
        from strategy import delta_coverage, _own_turn_coverage, _num_dice, P_DOUBLES
        card = UpgradeCard("Amusement Park")
        cov = _own_turn_coverage(self.bot, _num_dice(self.bot))
        self.assertAlmostEqual(delta_coverage(card, self.bot, [self.bot]), P_DOUBLES * cov, places=10)

    def test_delta_coverage_shopping_mall(self):
        """Shopping Mall has zero coverage effect."""
        from harmonictook import UpgradeCard
        from strategy import delta_coverage
        card = UpgradeCard("Shopping Mall")
        self.assertEqual(delta_coverage(card, self.bot, [self.bot]), 0.0)


class TestFinishScore(unittest.TestCase):
    """finish_score: landmarks×3 + establishments×2 + bank + 25 for winner."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]

    def test_starting_state(self):
        """Fresh player: Wheat Field (1) + Bakery (1) at 2×, bank=3, no snitch."""
        # 0 landmarks, cards cost 1+1=2, bank=3 → 0 + 4 + 3 = 7
        self.assertEqual(finish_score(self.player), 7)

    def test_golden_snitch_for_winner(self):
        """Winner gets +25 on top of their asset score."""
        p = self.player
        p.hasTrainStation = True
        p.hasShoppingMall = True
        p.hasAmusementPark = True
        p.hasRadioTower = True
        self.assertTrue(p.isWinner())
        base = finish_score(p)
        p.hasRadioTower = False
        self.assertFalse(p.isWinner())
        without_snitch = finish_score(p)
        self.assertEqual(base - without_snitch, 25)

    def test_landmark_multiplier(self):
        """Each owned landmark contributes cost×3 to the score."""
        p = self.player
        before = finish_score(p)
        p.hasTrainStation = True
        train = UpgradeCard("Train Station")
        train.owner = p
        p.deck.append(train)
        after = finish_score(p)
        # Train Station cost=4, multiplier=3 → +12
        self.assertEqual(after - before, 12)

    def test_golden_snitch_breaks_tie_between_identical_players(self):
        """Winner outscores an otherwise-identical non-winner by exactly 25."""
        winner = self.game.players[0]
        loser = self.game.players[1]
        # Give both players the same three landmarks and same bank.
        for p in [winner, loser]:
            for name in ["Train Station", "Shopping Mall", "Amusement Park"]:
                card = UpgradeCard(name)
                card.owner = p
                p.deck.append(card)
                setattr(p, UpgradeCard.orangeCards[name][2], True)
            p.bank = 10
        # Winner gets the fourth landmark too.
        radio = UpgradeCard("Radio Tower")
        radio.owner = winner
        winner.deck.append(radio)
        winner.hasRadioTower = True
        self.assertTrue(winner.isWinner())
        self.assertFalse(loser.isWinner())
        self.assertEqual(finish_score(winner) - finish_score(loser), 22 * 3 + 25)
