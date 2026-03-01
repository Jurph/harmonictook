#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_strategy.py — TDD tests for the strategy.py EV valuation library

import unittest
from harmonictook import Blue, Green, Red, Stadium, TVStation, BusinessCenter, UpgradeCard, Game
from strategy import (
    ONE_DIE_PROB, TWO_DIE_PROB, P_DOUBLES,
    p_hits, portfolio_ev, portfolio_coverage, delta_ev, delta_coverage,
    coverage_value, score_purchase_options,
    _die_pmf, _convolve, _landmark_cost_remaining, _prob_win_in_n_rounds,
    own_turn_pmf, opponent_turn_pmf, round_pmf,
    pmf_mean, pmf_variance, pmf_percentile, pmf_mass_at_least,
    prob_victory_within_n_rounds,
    tuv_expected, tuv_percentile, tuv_variance, delta_tuv,
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
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 2.0, places=10)

    def test_scales_with_N(self):
        """N=3 rounds should triple the EV."""
        card = Blue("Fires On 1", 1, 1, 6, [1])
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players, N=3), 6.0, places=10)


class TestEVGreen(unittest.TestCase):
    """EV for Green cards: fires only on owner's roll."""

    def setUp(self):
        self.game = Game(players=2)
        self.owner = self.game.players[0]
        self.other = self.game.players[1]
        self.owner.deposit(100)
        self.other.deposit(100)

    def test_flat_payout_all_faces(self):
        """Green hitting [1..6] with 1 die (P=1.0): delta_ev == payout."""
        card = Green("Always Fires", 3, 1, 8, [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 8.0, places=10)

    def test_amusement_park_multiplier(self):
        """With Amusement Park, green EV is multiplied by (1 + P_DOUBLES) per the PMF model.

        The PMF models Amusement Park as one conditional bonus turn, giving mean = E*(1+P_D).
        """
        card = Green("Always Fires", 3, 1, 8, [1, 2, 3, 4, 5, 6])
        self.owner.hasAmusementPark = True
        expected = 8.0 * (1 + P_DOUBLES)
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), expected, places=6)

    def test_convenience_store_with_shopping_mall(self):
        """Convenience Store payout is 3+1=4 when owner has Shopping Mall."""
        card = Green("Convenience Store", 3, 2, 3, [4])
        self.owner.hasShoppingMall = True
        # p_hits([4], 1) = 1/6; payout = 4
        expected = 4 * (1/6)
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), expected, places=10)

    def test_factory_with_matching_cards(self):
        """Factory Green multiplies payout by count of cards matching its category."""
        # Give owner 2 Ranch cards (category 2); need 2 dice so [7] can hit
        self.owner.hasTrainStation = True
        self.owner.deck.append(Blue("Ranch", 2, 1, 1, [2]))
        self.owner.deck.append(Blue("Ranch", 2, 1, 1, [2]))
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        # 2 ranches in deck, fires on [7] with 2 dice -> P = 6/36
        expected = 3 * 2 * (6/36)
        self.assertAlmostEqual(delta_ev(factory, self.owner, self.game.players), expected, places=10)

    def test_factory_with_no_matching_cards(self):
        """Factory with zero matching cards returns 0.0."""
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        self.assertAlmostEqual(delta_ev(factory, self.owner, self.game.players), 0.0, places=10)


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
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 3.0, places=10)

    def test_three_players(self):
        """With 3 players: ev == payout * 2 opponents."""
        game3 = Game(players=3)
        owner = game3.players[0]
        for p in game3.players:
            p.deposit(100)
        card = Red("Always Steals", 4, 2, 3, [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(delta_ev(card, owner, game3.players), 6.0, places=10)

    def test_clamped_by_opponent_bank(self):
        """Opponent with bank=1 caps the steal at 1 even if payout=3."""
        self.other.bank = 1
        card = Red("Always Steals", 4, 2, 3, [1, 2, 3, 4, 5, 6])
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 1.0, places=10)


class TestEVStadium(unittest.TestCase):
    """EV for Stadium: net gain == payout * (N_players - 1) per trigger on a 6."""

    def test_two_players(self):
        """2 players: net=2*1=2 per trigger; P(6,1die)=1/6; ev == 2/6."""
        game = Game(players=2)
        owner = game.players[0]
        for p in game.players:
            p.deposit(100)
        card = Stadium()
        self.assertAlmostEqual(delta_ev(card, owner, game.players), 2/6, places=10)

    def test_three_players(self):
        """3 players: net=2*2=4; ev == 4/6."""
        game = Game(players=3)
        owner = game.players[0]
        for p in game.players:
            p.deposit(100)
        card = Stadium()
        self.assertAlmostEqual(delta_ev(card, owner, game.players), 4/6, places=10)


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

    def test_plain_card_analytical_value(self):
        """delta_ev of a plain Blue card matches the analytically expected value.

        Ranch (Blue, cat2, payout=1, hitsOn=[2]) in a 2-player game with 1 die each:
        fires on own turn P(2)=1/6 and on opponent's turn P(2)=1/6 -> total 2/6 per round.
        """
        card = Blue("Ranch", 2, 1, 1, [2])
        self.assertAlmostEqual(
            delta_ev(card, self.player, self.game.players),
            2 / 6,
            places=10,
        )

    def test_factory_synergy_increases_delta(self):
        """Adding a Ranch when owner has a Cheese Factory (multiplies cat 2) boosts delta_ev.

        Standalone Ranch EV = 2/6 per round (fires own + opponent turn on [2]).
        With a Cheese Factory (payout=3, hits=[7] with 2 dice, P=6/36), adding a Ranch
        also triggers the factory: extra 3*(6/36) = 1/2 per round. Total > 2/6.
        """
        self.player.hasTrainStation = True  # factory hits on [7]; need 2 dice
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.player
        self.player.deck.append(factory)

        ranch = Blue("Ranch", 2, 1, 1, [2])
        standalone_ranch_ev = 2 / 6
        total_delta = delta_ev(ranch, self.player, self.game.players)
        self.assertGreater(total_delta, standalone_ranch_ev)

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
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 5 * (1/6), places=10)

    def test_poor_opponent(self):
        """Opponent with only 2 coins: steal capped at 2."""
        self.other.bank = 2
        card = TVStation()
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 2 * (1/6), places=10)

    def test_scales_with_N(self):
        card = TVStation()
        base = delta_ev(card, self.owner, self.game.players, N=1)
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players, N=4), base * 4, places=10)


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
        fat_ranch = Blue("Fat Ranch", 2, 1, 5, [1])
        fat_ranch.owner = self.target
        self.target.deck.append(fat_ranch)
        card = BusinessCenter()
        self.assertGreater(delta_ev(card, self.owner, self.game.players), 0.0)

    def test_spite_filter_prefers_less_synergistic_give(self):
        """BC EV is lower when Ranch feeds the target's Cheese Factory.

        Owner: Ranch (Blue[2], cheap give) and FatBakery (Green[2], payout=5, expensive give).
        Target: Cheese Factory (multiplies Ranch/cat-2) and TakeBait (Blue[2], payout=10).
        Everyone rolls 2 dice so Cheese Factory ([7]) can fire.

        Without Cheese Factory: Ranch has lowest delta_ev to target → given, give_loss ≈ 2/36.
        With Cheese Factory: Ranch's delta_ev to target jumps (synergy +18/36), forcing the
        spite filter to give FatBakery instead, increasing give_loss to 5/36.
        Net BC EV is therefore measurably lower when Cheese Factory is present.
        """
        self.owner.deck.deck.clear()
        self.target.deck.deck.clear()
        self.owner.hasTrainStation = True
        self.target.hasTrainStation = True

        ranch = Blue("Ranch", 2, 1, 1, [2])
        ranch.owner = self.owner
        self.owner.deck.append(ranch)
        fat_bakery = Green("FatBakery", 3, 1, 5, [2])
        fat_bakery.owner = self.owner
        self.owner.deck.append(fat_bakery)

        take_bait = Blue("TakeBait", 1, 1, 10, [2])
        take_bait.owner = self.target
        self.target.deck.append(take_bait)
        factory = Green("Cheese Factory", 6, 5, 3, [7], 2)
        factory.owner = self.target
        self.target.deck.append(factory)

        card = BusinessCenter()
        ev_with_factory = delta_ev(card, self.owner, self.game.players)
        self.target.deck.deck.remove(factory)
        ev_without_factory = delta_ev(card, self.owner, self.game.players)

        self.assertGreater(ev_without_factory, ev_with_factory,
            msg="Spite filter should force a more expensive give when Ranch feeds target's "
                "Cheese Factory, reducing BC net EV")

    def test_no_opponents_returns_zero(self):
        """With no valid opponents (only owner), BC returns 0."""
        game1 = Game(players=2)
        owner = game1.players[0]
        game1.players[1].deck.deck.clear()
        card = BusinessCenter()
        self.assertAlmostEqual(delta_ev(card, owner, game1.players), 0.0, places=10)

    def test_no_own_swappable_cards_returns_zero(self):
        """If owner has only UpgradeCards, BC returns 0 (nothing to give)."""
        self.owner.deck.deck.clear()
        card = BusinessCenter()
        self.assertAlmostEqual(delta_ev(card, self.owner, self.game.players), 0.0, places=10)


class TestEVBot(unittest.TestCase):
    """EVBot scores Card objects directly; falls back to random when given only string names."""

    def setUp(self):
        self.game = Game(players=2)
        self.bot = EVBot(name="TestEVBot")
        self.game.players[0] = self.bot
        self.game.current_player_index = 0

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
        """With a valid game, chooseCard returns a string name from the Card options."""
        self.bot.bank = 999
        self.game.players[0].deposit(999)
        options = self.game.get_purchase_options()
        result = self.bot.chooseCard(options, self.game)
        self.assertIsInstance(result, str)
        self.assertIn(result, [c.name for c in options])


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
    """finish_score: ERUV-based 50 - round(ERUV); winner scores 50."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]

    def test_winner_scores_50(self):
        """Winner has ERUV=0 so finish_score is 50."""
        p = self.player
        for name in UpgradeCard.orangeCards:
            card = UpgradeCard(name)
            card.owner = p
            p.deck.append(card)
            setattr(p, UpgradeCard.orangeCards[name][2], True)
        self.assertTrue(p.isWinner())
        self.assertEqual(finish_score(p, self.game), 50)

    def test_starting_state_below_50(self):
        """Fresh player has many rounds to go; score = 50 - ERUV is < 50 (may be negative)."""
        score = finish_score(self.player, self.game)
        self.assertLess(score, 50)

    def test_winner_outscores_non_winner(self):
        """Winner (50) outscores an otherwise-identical non-winner (50 - ERUV)."""
        winner = self.game.players[0]
        loser = self.game.players[1]
        for p in [winner, loser]:
            for name in ["Train Station", "Shopping Mall", "Amusement Park"]:
                card = UpgradeCard(name)
                card.owner = p
                p.deck.append(card)
                setattr(p, UpgradeCard.orangeCards[name][2], True)
            p.bank = 10
        radio = UpgradeCard("Radio Tower")
        radio.owner = winner
        winner.deck.append(radio)
        winner.hasRadioTower = True
        self.assertTrue(winner.isWinner())
        self.assertFalse(loser.isWinner())
        self.assertEqual(finish_score(winner, self.game), 50)
        self.assertGreater(finish_score(winner, self.game), finish_score(loser, self.game))

    def test_more_bank_higher_score(self):
        """More coins reduce the income deficit so ERUV drops and finish_score increases."""
        p = self.player
        p.deck.deck.clear()
        card = Blue("Wheat", 1, 1, 1, [1])
        card.owner = p
        p.deck.append(card)
        p.deposit(0)
        before = finish_score(p, self.game)
        p.deposit(15)
        after = finish_score(p, self.game)
        self.assertGreater(after, before)


class TestDiePMFGuardrails(unittest.TestCase):
    """_die_pmf: impossible values must be absent, symmetry, recursive 3-die case."""

    def test_one_die_excludes_impossible_values(self):
        """Values outside 1–6 cannot appear in a 1-die PMF."""
        pmf = _die_pmf(1)
        for v in [0, 7, 12]:
            self.assertNotIn(v, pmf, msg=f"key {v} should not appear in 1-die PMF")

    def test_two_dice_exclude_impossible_values(self):
        """Values 1 and 13+ cannot be rolled with 2 dice."""
        pmf = _die_pmf(2)
        for v in [0, 1, 13]:
            self.assertNotIn(v, pmf, msg=f"key {v} should not appear in 2-die PMF")

    def test_two_dice_symmetric(self):
        """2d6 is symmetric around 7: pmf[k] == pmf[14-k] for k in 2..7."""
        pmf = _die_pmf(2)
        for k in range(2, 8):
            self.assertAlmostEqual(pmf[k], pmf[14 - k], places=10,
                msg=f"pmf[{k}] != pmf[{14-k}] — 2d6 should be symmetric")

    def test_three_dice_support_and_sum(self):
        """3d6: support is exactly {{3..18}} and probabilities sum to 1."""
        pmf = _die_pmf(3)
        self.assertEqual(set(pmf.keys()), set(range(3, 19)))
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)

    def test_three_dice_min_max_probability(self):
        """3d6: P(3) == P(18) == 1/216 (only one way to roll all-ones or all-sixes)."""
        pmf = _die_pmf(3)
        self.assertAlmostEqual(pmf[3], 1 / 216, places=10)
        self.assertAlmostEqual(pmf[18], 1 / 216, places=10)

    def test_returns_copy_not_module_constant(self):
        """Mutating the returned dict must not corrupt the module-level ONE_DIE_PROB."""
        from strategy import ONE_DIE_PROB
        pmf = _die_pmf(1)
        pmf[1] = 999.0
        self.assertAlmostEqual(ONE_DIE_PROB[1], 1 / 6, places=10)


class TestConvolveProperties(unittest.TestCase):
    """_convolve: identity element, commutativity, exact support — no spurious keys."""

    def test_identity_element(self):
        """convolve(pmf, {{0: 1.0}}) is equivalent to pmf for every key."""
        d = _die_pmf(1)
        result = _convolve(d, {0: 1.0})
        for k, v in d.items():
            self.assertAlmostEqual(result.get(k, 0.0), v, places=10,
                msg=f"key {k} changed after convolving with identity {{0: 1.0}}")

    def test_commutative(self):
        """_convolve(a, b) and _convolve(b, a) agree on every key."""
        a = {1: 0.4, 2: 0.6}
        b = {10: 0.3, 20: 0.7}
        ab = _convolve(a, b)
        ba = _convolve(b, a)
        for k in set(ab) | set(ba):
            self.assertAlmostEqual(ab.get(k, 0.0), ba.get(k, 0.0), places=10)

    def test_exact_support_two_point_masses(self):
        """Convolving two point masses produces exactly one outcome at their sum."""
        result = _convolve({3: 1.0}, {5: 1.0})
        self.assertEqual(set(result.keys()), {8})
        self.assertAlmostEqual(result[8], 1.0, places=10)

    def test_no_spurious_keys(self):
        """Result contains only keys x+y reachable from (a, b) — nothing outside that set."""
        a = {1: 0.5, 3: 0.5}
        b = {10: 0.4, 20: 0.6}
        result = _convolve(a, b)
        reachable = {x + y for x in a for y in b}  # {11, 21, 13, 23}
        self.assertEqual(set(result.keys()), reachable)


class TestPMFStatsEdgeCases(unittest.TestCase):
    """pmf_mean, pmf_variance, pmf_percentile: edge cases and mathematical invariants."""

    def test_mean_empty_returns_zero(self):
        self.assertAlmostEqual(pmf_mean({}), 0.0, places=10)

    def test_variance_empty_returns_zero(self):
        self.assertAlmostEqual(pmf_variance({}), 0.0, places=10)

    def test_variance_degenerate_is_zero(self):
        """A certain outcome has zero spread — variance must be exactly 0 regardless of value."""
        for x in [0, 1, -3, 100]:
            self.assertAlmostEqual(pmf_variance({x: 1.0}), 0.0, places=10,
                msg=f"Degenerate PMF at x={x} should have variance 0")

    def test_variance_nonnegative_invariant(self):
        """Variance must be >= 0 for any valid distribution (guards against floating-point sign flip)."""
        for pmf in [_die_pmf(1), _die_pmf(2), {0: 0.5, 1: 0.3, 3: 0.2}]:
            self.assertGreaterEqual(pmf_variance(pmf), -1e-12,
                msg="Variance must be non-negative")

    def test_percentile_p_zero_or_negative_returns_minimum(self):
        """p <= 0.0 always returns the smallest income in the PMF."""
        pmf = {2: 0.5, 5: 0.5}
        self.assertAlmostEqual(pmf_percentile(pmf, 0.0), 2.0, places=10)
        self.assertAlmostEqual(pmf_percentile(pmf, -1.0), 2.0, places=10)

    def test_percentile_p_one_returns_maximum(self):
        """p=1.0 returns the largest income key even when cumulative probabilities are imprecise."""
        pmf = {1: 0.4, 3: 0.3, 6: 0.3}
        self.assertAlmostEqual(pmf_percentile(pmf, 1.0), 6.0, places=10)

    def test_percentile_empty_pmf_returns_zero(self):
        """Empty PMF with any p returns 0.0 without raising."""
        self.assertAlmostEqual(pmf_percentile({}, 0.5), 0.0, places=10)
        self.assertAlmostEqual(pmf_percentile({}, 1.0), 0.0, places=10)

    def test_percentile_at_exact_cdf_boundary(self):
        """p exactly at a cumulative boundary returns that boundary's income, not the next."""
        # CDF: P(X <= 1) = 0.3, P(X <= 4) = 0.8, P(X <= 7) = 1.0
        pmf = {1: 0.3, 4: 0.5, 7: 0.2}
        self.assertAlmostEqual(pmf_percentile(pmf, 0.3), 1.0, places=10)
        self.assertAlmostEqual(pmf_percentile(pmf, 0.8), 4.0, places=10)


class TestOwnTurnPMFLandmarks(unittest.TestCase):
    """own_turn_pmf with Radio Tower, Amusement Park, and Train Station effects."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.player.deck.deck.clear()
        self.player.deposit(10)
        self.game.players[1].deposit(10)
        # Baseline: Blue[1] gives income 1 on 1/6 of rolls, 0 on 5/6
        card = Blue("Wheat", 1, 1, 1, [1])
        card.owner = self.player
        self.player.deck.append(card)

    def _pmf(self):
        return own_turn_pmf(self.player, self.game.players)

    def test_radio_tower_p0_equals_base_p0_squared(self):
        """P(income=0 | RT) == P(income=0 | no RT)² — the double-miss probability."""
        base_p0 = self._pmf().get(0, 0.0)
        self.player.hasRadioTower = True
        rt_p0 = self._pmf().get(0, 0.0)
        self.assertAlmostEqual(rt_p0, base_p0 * base_p0, places=10)

    def test_radio_tower_preserves_total_probability(self):
        """PMF with Radio Tower still sums to 1.0 (no mass lost or created by reroll)."""
        self.player.hasRadioTower = True
        self.assertAlmostEqual(sum(self._pmf().values()), 1.0, places=10)

    def test_radio_tower_never_lowers_mean(self):
        """Radio Tower is strictly non-harmful: mean income with RT >= mean without RT."""
        base_mean = pmf_mean(self._pmf())
        self.player.hasRadioTower = True
        self.assertGreaterEqual(pmf_mean(self._pmf()), base_mean - 1e-12)

    def test_radio_tower_no_effect_when_every_roll_pays(self):
        """RT leaves the mean unchanged when P(income=0) is already 0 — nothing to reroll."""
        self.player.deck.deck.clear()
        always = Blue("Always", 1, 1, 3, [1, 2, 3, 4, 5, 6])
        always.owner = self.player
        self.player.deck.append(always)
        base_mean = pmf_mean(self._pmf())
        self.player.hasRadioTower = True
        self.assertAlmostEqual(pmf_mean(self._pmf()), base_mean, places=10)

    def test_amusement_park_mean_equals_base_times_one_plus_p_doubles(self):
        """AP PMF mean == base_mean * (1 + P_DOUBLES).

        This is the deliberate PMF underestimate: it models one bonus draw on doubles,
        not the full geometric series. portfolio_ev uses 1/(1-P_D) for comparison.
        """
        base_mean = pmf_mean(self._pmf())
        self.player.hasAmusementPark = True
        self.assertAlmostEqual(pmf_mean(self._pmf()), base_mean * (1 + P_DOUBLES), places=10)

    def test_amusement_park_preserves_total_probability(self):
        """AP convolution distributes mass between single-turn and double-turn — sum stays 1.0."""
        self.player.hasAmusementPark = True
        self.assertAlmostEqual(sum(self._pmf().values()), 1.0, places=10)

    def test_train_station_enables_high_roll_income(self):
        """With Train Station, a Blue[9] card can fire; with 1 die, roll 9 is unreachable."""
        self.player.deck.deck.clear()
        mine = Blue("Mine", 5, 6, 5, [9])
        mine.owner = self.player
        self.player.deck.append(mine)
        # 1 die: max roll is 6, so Blue[9] never fires — income is always 0
        base = self._pmf()
        self.assertEqual(set(base.keys()), {0},
            msg="With 1 die, roll 9 is unreachable — income must always be 0")
        # 2 dice: P(9) = 4/36, Mine pays 5
        self.player.hasTrainStation = True
        ts = self._pmf()
        self.assertIn(5, ts, msg="Mine (payout=5) should be reachable on roll 9 with 2 dice")
        self.assertAlmostEqual(ts.get(5, 0.0), 4 / 36, places=10)


class TestOpponentTurnPMF(unittest.TestCase):
    """opponent_turn_pmf fires Blue and Red for observer; Green and Purple must not fire."""

    def setUp(self):
        self.game = Game(players=2)
        self.observer = self.game.players[0]
        self.roller = self.game.players[1]
        self.observer.deck.deck.clear()
        self.roller.deposit(100)

    def test_green_card_does_not_fire_on_opponent_turn(self):
        """Observer's Green card must yield 0 income on every opponent roll — Green is own-turn only."""
        bakery = Green("Bakery", 2, 1, 1, [2, 3])
        bakery.owner = self.observer
        self.observer.deck.append(bakery)
        pmf = opponent_turn_pmf(self.observer, self.roller, self.game.players)
        self.assertEqual(set(pmf.keys()), {0},
            msg="Green should never appear in opponent_turn_pmf")
        self.assertAlmostEqual(pmf[0], 1.0, places=10)

    def test_blue_card_fires_on_opponent_turn(self):
        """Observer's Blue[1] pays out when roller rolls 1 (P=1/6 with 1 die)."""
        wheat = Blue("Wheat", 1, 1, 1, [1])
        wheat.owner = self.observer
        self.observer.deck.append(wheat)
        pmf = opponent_turn_pmf(self.observer, self.roller, self.game.players)
        self.assertAlmostEqual(pmf.get(1, 0.0), 1 / 6, places=10)
        self.assertAlmostEqual(pmf.get(0, 0.0), 5 / 6, places=10)

    def test_red_card_income_bounded_by_roller_bank(self):
        """Observer steals min(payout, roller.bank) — a poor roller limits the take."""
        self.roller.bank = 2
        cafe = Red("Cafe", 3, 2, 5, [1, 2, 3, 4, 5, 6])
        cafe.owner = self.observer
        self.observer.deck.append(cafe)
        pmf = opponent_turn_pmf(self.observer, self.roller, self.game.players)
        # Every roll triggers; steal = min(5, 2) = 2 on every outcome
        self.assertEqual(set(pmf.keys()), {2})
        self.assertAlmostEqual(pmf[2], 1.0, places=10)

    def test_red_card_yields_zero_when_roller_has_no_coins(self):
        """Red card income is 0 when the roller is broke — nothing to steal."""
        self.roller.bank = 0
        cafe = Red("Cafe", 3, 2, 5, [1, 2, 3, 4, 5, 6])
        cafe.owner = self.observer
        self.observer.deck.append(cafe)
        pmf = opponent_turn_pmf(self.observer, self.roller, self.game.players)
        self.assertEqual(set(pmf.keys()), {0})
        self.assertAlmostEqual(pmf[0], 1.0, places=10)

    def test_sum_always_one(self):
        """opponent_turn_pmf probabilities sum to 1.0 for any card combination."""
        game = Game(players=2)
        pmf = opponent_turn_pmf(game.players[0], game.players[1], game.players)
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)


class TestRoundPMF(unittest.TestCase):
    """round_pmf: convolution of own turn + each opponent turn."""

    def test_sum_always_one(self):
        """round_pmf probabilities sum to 1.0."""
        game = Game(players=2)
        for p in game.players:
            p.deposit(10)
        self.assertAlmostEqual(
            sum(round_pmf(game.players[0], game.players).values()), 1.0, places=10
        )

    def test_solo_player_equals_own_turn_pmf(self):
        """round_pmf(p, [p]) is identical to own_turn_pmf(p, [p]) — no opponents, no convolution."""
        game = Game(players=2)
        player = game.players[0]
        player.deposit(10)
        solo_round = round_pmf(player, [player])
        own = own_turn_pmf(player, [player])
        for k in set(solo_round) | set(own):
            self.assertAlmostEqual(
                solo_round.get(k, 0.0), own.get(k, 0.0), places=10,
                msg=f"key {k}: round_pmf and own_turn_pmf differ for a solo player",
            )

    def test_all_income_nonnegative_with_only_blue_cards(self):
        """With no Red cards, every income outcome in round_pmf is >= 0."""
        game = Game(players=3)
        for p in game.players:
            p.deck.deck.clear()
            p.deposit(10)
            card = Blue("Wheat", 1, 1, 1, [1])
            card.owner = p
            p.deck.append(card)
        pmf = round_pmf(game.players[0], game.players)
        for k in pmf:
            self.assertGreaterEqual(k, 0,
                msg=f"income key {k} is negative — Blue cards should never produce negative income")


class TestPMF(unittest.TestCase):
    """PMF building blocks and round_pmf vs portfolio_ev."""

    def test_die_pmf_one_die(self):
        pmf = _die_pmf(1)
        self.assertEqual(set(pmf.keys()), {1, 2, 3, 4, 5, 6})
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)
        for v in pmf.values():
            self.assertAlmostEqual(v, 1/6, places=10)

    def test_die_pmf_two_dice(self):
        pmf = _die_pmf(2)
        self.assertEqual(set(pmf.keys()), set(range(2, 13)))
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)
        self.assertAlmostEqual(pmf[7], 6/36, places=10)

    def test_convolve_preserves_mass(self):
        a = {0: 0.5, 1: 0.5}
        b = {0: 0.5, 1: 0.5}
        c = _convolve(a, b)
        self.assertAlmostEqual(sum(c.values()), 1.0, places=10)
        self.assertAlmostEqual(c[0], 0.25, places=10)
        self.assertAlmostEqual(c[1], 0.5, places=10)
        self.assertAlmostEqual(c[2], 0.25, places=10)

    def test_pmf_mean_variance_percentile(self):
        pmf = {0: 0.25, 2: 0.5, 4: 0.25}
        self.assertAlmostEqual(pmf_mean(pmf), 2.0, places=10)
        # E[X^2] = 0 + 4*0.5 + 16*0.25 = 6, Var = 6 - 2^2 = 2
        self.assertAlmostEqual(pmf_variance(pmf), 2.0, places=10)
        self.assertAlmostEqual(pmf_percentile(pmf, 0.5), 2.0, places=10)
        self.assertAlmostEqual(pmf_percentile(pmf, 0.25), 0.0, places=10)
        self.assertAlmostEqual(pmf_percentile(pmf, 0.9), 4.0, places=10)

    def test_own_turn_pmf_empty_deck(self):
        game = Game(players=2)
        player = game.players[0]
        player.deck.deck.clear()
        pmf = own_turn_pmf(player, game.players)
        self.assertEqual(set(pmf.keys()), {0})
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)
        self.assertAlmostEqual(pmf_mean(pmf), 0.0, places=10)

    def test_own_turn_pmf_single_blue(self):
        game = Game(players=2)
        player = game.players[0]
        player.deck.deck.clear()
        card = Blue("Wheat", 1, 1, 1, [1])
        card.owner = player
        player.deck.append(card)
        pmf = own_turn_pmf(player, game.players)
        self.assertAlmostEqual(sum(pmf.values()), 1.0, places=10)
        # 1 die: P(1)=1/6 → income 1, else 0
        self.assertAlmostEqual(pmf.get(0, 0), 5/6, places=10)
        self.assertAlmostEqual(pmf.get(1, 0), 1/6, places=10)
        self.assertAlmostEqual(pmf_mean(pmf), 1/6, places=10)

    def test_round_pmf_mean_matches_portfolio_ev_simple(self):
        """pmf_mean(round_pmf(...)) matches portfolio_ev for a simple 2p deck (no Amusement Park).

        Caveat: verification only holds for non-AP players; AP uses E*(1+P_D) vs portfolio_ev's E/(1-P_D).
        """
        game = Game(players=2)
        p0 = game.players[0]
        for p in game.players:
            p.deposit(10)
            p.deck.deck.clear()
        # One Blue [1] each: each gets 1 on roll 1 from own turn, 1 on opponent roll 1
        for p in game.players:
            card = Blue("Wheat", 1, 1, 1, [1])
            card.owner = p
            p.deck.append(card)
        ev_p0 = portfolio_ev(p0, game.players, N=1)
        rp = round_pmf(p0, game.players)
        pmf_ev = pmf_mean(rp)
        self.assertAlmostEqual(ev_p0, pmf_ev, places=6,
            msg="round_pmf mean should match portfolio_ev")


class TestTUV(unittest.TestCase):
    """TUV (turns until victory) consumes round_pmf; winner has 0, delta_tuv sign = who is behind."""

    def test_winner_has_zero_tuv(self):
        game = Game(players=2)
        p = game.players[0]
        for name in UpgradeCard.orangeCards:
            card = UpgradeCard(name)
            card.owner = p
            p.deck.append(card)
            setattr(p, UpgradeCard.orangeCards[name][2], True)
        self.assertTrue(p.isWinner())
        self.assertAlmostEqual(tuv_expected(p, game), 0.0, places=10)

    def test_tuv_expected_positive_when_not_winner(self):
        game = Game(players=2)
        p = game.players[0]
        p.deck.deck.clear()
        p.deposit(0)
        # No income, 4 landmarks left → TUV at least 4
        self.assertGreaterEqual(tuv_expected(p, game), 4.0)

    def test_landmark_cost_remaining_zero_for_winner(self):
        """Player who has bought all four landmarks has 0 cost remaining."""
        game = Game(players=2)
        p = game.players[0]
        p.deck.deck.clear()
        for name in UpgradeCard.orangeCards:
            card = UpgradeCard(name)
            card.owner = p
            p.deck.append(card)
        self.assertEqual(_landmark_cost_remaining(p), 0)

    def test_landmark_cost_remaining_all_four_when_none_owned(self):
        """Player with no landmarks has cost remaining = sum of all four (4+10+16+22=52)."""
        game = Game(players=2)
        p = game.players[0]
        p.deck.deck.clear()
        self.assertEqual(_landmark_cost_remaining(p), 4 + 10 + 16 + 22)

    def test_delta_tuv_positive_when_a_behind(self):
        game = Game(players=2)
        a, b = game.players[0], game.players[1]
        a.deck.deck.clear()
        b.deck.deck.clear()
        a.deposit(0)
        b.deposit(50)
        for name in UpgradeCard.orangeCards:
            card = UpgradeCard(name)
            card.owner = b
            b.deck.append(card)
            setattr(b, UpgradeCard.orangeCards[name][2], True)
        self.assertTrue(b.isWinner())
        self.assertFalse(a.isWinner())
        self.assertGreater(delta_tuv(a, b, game), 0)

    def test_prob_victory_within_n_rounds_winner_is_one(self):
        """Already-won player has probability 1.0 of being across the goal in any N."""
        game = Game(players=2)
        p = game.players[0]
        for name in UpgradeCard.orangeCards:
            card = UpgradeCard(name)
            card.owner = p
            p.deck.append(card)
            setattr(p, UpgradeCard.orangeCards[name][2], True)
        self.assertAlmostEqual(prob_victory_within_n_rounds(p, game, 1), 1.0, places=10)
        # Winner: probability of having won within N rounds is 1.0
        self.assertTrue(p.isWinner())

    def test_prob_victory_within_n_rounds_zero_deficit_is_one(self):
        """Player with bank >= cost_remaining has probability 1.0 (no income needed)."""
        game = Game(players=2)
        p = game.players[0]
        p.deck.deck.clear()
        p.deposit(100)
        self.assertEqual(_landmark_cost_remaining(p), 52)
        self.assertGreaterEqual(p.bank, 52)
        self.assertAlmostEqual(prob_victory_within_n_rounds(p, game, 1), 1.0, places=10)

    def test_pmf_mass_at_least(self):
        pmf = {0: 0.25, 2: 0.5, 4: 0.25}
        self.assertAlmostEqual(pmf_mass_at_least(pmf, 0), 1.0, places=10)
        self.assertAlmostEqual(pmf_mass_at_least(pmf, 2), 0.75, places=10)
        self.assertAlmostEqual(pmf_mass_at_least(pmf, 4), 0.25, places=10)
        self.assertAlmostEqual(pmf_mass_at_least(pmf, 5), 0.0, places=10)


class TestTUVPercentileAndVariance(unittest.TestCase):
    """tuv_percentile and tuv_variance: percentile-based and variance-based TUV."""

    def setUp(self):
        self.game = Game(players=2)
        self.p = self.game.players[0]
        self.p.deck.deck.clear()
        self.p.deposit(10)
        self.game.players[1].deposit(10)
        card = Blue("Wheat Field", 1, 1, 1, [1])
        card.owner = self.p
        self.p.deck.append(card)

    def test_winner_has_zero_tuv_percentile(self):
        """Winner has no deficit; tuv_percentile returns 0.0 regardless of p."""
        for name in UpgradeCard.orangeCards:
            c = UpgradeCard(name)
            c.owner = self.p
            self.p.deck.append(c)
            setattr(self.p, UpgradeCard.orangeCards[name][2], True)
        self.assertTrue(self.p.isWinner())
        self.assertAlmostEqual(tuv_percentile(self.p, self.game, p=0.1), 0.0, places=10)
        self.assertAlmostEqual(tuv_percentile(self.p, self.game, p=0.9), 0.0, places=10)

    def test_higher_p_gives_lower_or_equal_tuv_when_income_positive(self):
        """Higher p → higher income estimate (more optimistic) → lower or equal TUV.

        Add Blue cards covering rolls 1–5 so P(income=0 per round) = 1/36 ≈ 0.028.
        Both p=0.05 and p=0.5 then give positive income estimates; the 50th-percentile
        income is higher than the 5th-percentile income, so t(p=0.5) <= t(p=0.05).
        """
        self.p.deck.deck.clear()
        self.p.bank = 0  # maximize deficit so TUV differences are visible
        for roll in range(1, 6):
            c = Blue(f"B{roll}", 1, 1, 1, [roll])
            c.owner = self.p
            self.p.deck.append(c)
        t_pessimist = tuv_percentile(self.p, self.game, p=0.05)
        t_optimist  = tuv_percentile(self.p, self.game, p=0.5)
        self.assertLessEqual(t_optimist, t_pessimist,
            "Higher p (more optimistic income estimate) must yield lower or equal TUV")

    def test_tuv_variance_increases_with_more_coverage_gaps(self):
        """A deck with sparse coverage has higher income variance than a fully-covered deck.

        More zero-income rounds → higher variance around the mean.
        """
        # Sparse: only Wheat Field[1] — low coverage, high variance
        v_sparse = tuv_variance(self.p, self.game)
        # Dense: add cards covering 1-6 → income guaranteed every own-turn roll
        for roll in [2, 3, 4, 5, 6]:
            c = Blue(f"Card{roll}", 1, 1, 1, [roll])
            c.owner = self.p
            self.p.deck.append(c)
        v_dense = tuv_variance(self.p, self.game)
        self.assertGreater(v_sparse, v_dense,
            "Sparse-coverage deck should have higher per-round income variance")

    def test_tuv_variance_nonnegative(self):
        """Income variance is always >= 0 (guards against floating-point sign flip)."""
        self.assertGreaterEqual(tuv_variance(self.p, self.game), 0.0)


class TestGlicko(unittest.TestCase):
    """Glicko-1 rating math: known numerical values from the Glicko-1 paper."""

    def test_glicko_update_no_games_unchanged(self):
        """An empty result list leaves rating and RD unchanged."""
        from tournament import _glicko_update
        r, rd = _glicko_update(1500.0, 200.0, [])
        self.assertAlmostEqual(r, 1500.0, places=6)
        self.assertAlmostEqual(rd, 200.0, places=6)

    def test_glicko_update_win_increases_rating(self):
        """Winning a game against an equally-rated opponent raises the rating."""
        from tournament import _glicko_update
        r, _ = _glicko_update(1500.0, 200.0, [(1500.0, 200.0, 1.0)])
        self.assertGreater(r, 1500.0)

    def test_glicko_update_loss_decreases_rating(self):
        """Losing a game against an equally-rated opponent lowers the rating."""
        from tournament import _glicko_update
        r, _ = _glicko_update(1500.0, 200.0, [(1500.0, 200.0, 0.0)])
        self.assertLess(r, 1500.0)

    def test_glicko_update_draw_unchanged(self):
        """Drawing against an equally-rated opponent leaves rating unchanged."""
        from tournament import _glicko_update
        r, _ = _glicko_update(1500.0, 200.0, [(1500.0, 200.0, 0.5)])
        self.assertAlmostEqual(r, 1500.0, places=6)

    def test_glicko_update_rd_decreases_after_games(self):
        """Playing games reduces RD (rating uncertainty shrinks with evidence)."""
        from tournament import _glicko_update
        _, new_rd = _glicko_update(1500.0, 200.0, [
            (1500.0, 200.0, 1.0),
            (1500.0, 200.0, 0.0),
        ])
        self.assertLess(new_rd, 200.0)

    def test_glicko_rd_floor(self):
        """RD never drops below _GLICKO_RD_MIN=50 even with many games played."""
        from tournament import _glicko_update, _GLICKO_RD_MIN
        _, rd = _glicko_update(1500.0, 50.1, [(1500.0, 50.0, 0.5)] * 100)
        self.assertGreaterEqual(rd, _GLICKO_RD_MIN)


class TestStrategyCoveragePaths(unittest.TestCase):
    """Tests that exercise previously uncovered branches in strategy.py."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.other  = self.game.players[1]
        self.player.deposit(50)
        self.other.deposit(50)

    # ------------------------------------------------------------------
    # portfolio_coverage
    # ------------------------------------------------------------------
    def test_portfolio_coverage_returns_float(self):
        """portfolio_coverage sums coverage_value across the full deck."""
        result = portfolio_coverage(self.player, self.game.players)
        self.assertIsInstance(result, float)
        self.assertGreater(result, 0.0)

    # ------------------------------------------------------------------
    # _turn_multiplier AP branch — exercised via coverage_value
    # ------------------------------------------------------------------
    def test_coverage_value_green_with_amusement_park(self):
        """coverage_value for a Green card with Amusement Park uses the turn multiplier > 1."""
        self.player.hasAmusementPark = True
        card = Green("Bakery", 3, 1, 1, [2, 3])
        card.owner = self.player
        cov_ap = coverage_value(card, self.player, self.game.players)
        self.player.hasAmusementPark = False
        cov_no_ap = coverage_value(card, self.player, self.game.players)
        self.assertGreater(cov_ap, cov_no_ap, "AP multiplier must increase coverage_value")

    # ------------------------------------------------------------------
    # delta_coverage — Red card fires on opponents' turns only
    # ------------------------------------------------------------------
    def test_delta_coverage_red_card_only_fires_on_opponents(self):
        """delta_coverage for a Red card is > 0 (fires on opponents' rolls, not owner's)."""
        cafe = Red("Cafe", 4, 2, 1, [3])
        cafe.owner = self.player
        result = delta_coverage(cafe, self.player, self.game.players)
        self.assertGreater(result, 0.0, "Red card must have positive delta_coverage via opponents' rolls")

    # ------------------------------------------------------------------
    # _ev_businesscenter — no opponents in players list
    # ------------------------------------------------------------------
    def test_ev_businesscenter_solo_game_returns_zero(self):
        """BC EV is 0 when the player is the only entry in the players list (no opponents)."""
        card = BusinessCenter()
        result = delta_ev(card, self.player, [self.player])
        self.assertAlmostEqual(result, 0.0, places=10)

    # ------------------------------------------------------------------
    # pmf_mass_at_least — empty PMF
    # ------------------------------------------------------------------
    def test_pmf_mass_at_least_empty_returns_zero(self):
        """pmf_mass_at_least on an empty PMF is 0.0 for any threshold."""
        self.assertAlmostEqual(pmf_mass_at_least({}, 0), 0.0, places=10)
        self.assertAlmostEqual(pmf_mass_at_least({}, 5), 0.0, places=10)

    # ------------------------------------------------------------------
    # _prob_win_in_n_rounds — n_rounds == 0 returns 0.0
    # ------------------------------------------------------------------
    def test_prob_win_in_n_rounds_zero_rounds_is_zero(self):
        """No rounds remain → P(win) = 0.0."""
        self.player.deck.deck.clear()
        self.player.bank = 0
        result = _prob_win_in_n_rounds(self.player, self.game.players, n_rounds=0)
        self.assertAlmostEqual(result, 0.0, places=10)

    # ------------------------------------------------------------------
    # tuv_percentile — income ≤ 0 falls back to n_landmarks_remaining
    # ------------------------------------------------------------------
    def test_tuv_percentile_zero_income_returns_n_landmarks(self):
        """When the p-th percentile income is 0, tuv_percentile returns n_landmarks_remaining."""
        p = self.player
        p.deck.deck.clear()
        p.bank = 0
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        wheat.owner = p
        p.deck.append(wheat)
        # P(income=0 per round) ≈ 69.4%; median (p=0.5) is 0 → triggers income-zero fallback.
        result = tuv_percentile(p, self.game, p=0.5)
        self.assertEqual(result, 4.0, "With 0 median income, TUV must equal n_landmarks_remaining=4")

    # ------------------------------------------------------------------
    # score_purchase_options — empty cards list returns {}
    # ------------------------------------------------------------------
    def test_score_purchase_options_empty_returns_empty_dict(self):
        """score_purchase_options with no cards returns an empty dict."""
        result = score_purchase_options(self.player, [], self.game.players)
        self.assertEqual(result, {})
