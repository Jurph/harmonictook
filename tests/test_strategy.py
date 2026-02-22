#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_strategy.py — TDD tests for the strategy.py EV valuation library

import unittest
from harmonictook import Blue, Green, Red, Stadium, UpgradeCard, Game
from strategy import (
    ONE_DIE_PROB, TWO_DIE_PROB, P_DOUBLES,
    p_hits, ev, portfolio_ev, delta_ev, score_purchase_options,
)


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


class TestScorePurchaseOptions(unittest.TestCase):
    """score_purchase_options returns a {Card: float} dict sorted descending by EV."""

    def setUp(self):
        self.game = Game(players=2)
        self.player = self.game.players[0]
        self.game.current_player_index = 0
        # Give the player enough to buy anything
        self.player.bank = 999

    def test_returns_dict_of_floats(self):
        result = score_purchase_options(self.player, self.game)
        self.assertIsInstance(result, dict)
        for v in result.values():
            self.assertIsInstance(v, float)

    def test_sorted_descending(self):
        result = score_purchase_options(self.player, self.game)
        scores = list(result.values())
        self.assertEqual(scores, sorted(scores, reverse=True))
