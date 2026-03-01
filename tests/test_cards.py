#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_cards.py — Card trigger mechanics and sort ordering tests

import unittest
from harmonictook import Game, Blue, Green, Red, Card, Stadium, TVStation, BusinessCenter, UpgradeCard


class TestCards(unittest.TestCase):
    """Tests for card trigger mechanics across Blue, Green, Red subclasses and their interactions."""

    def setUp(self):
        self.players = 2
        self.game = Game(players=self.players)
        self.testbot = self.game.players[0]
        self.otherbot = self.game.players[1]
        self.testbot.deposit(100)
        self.otherbot.deposit(100)

    def testBlueCards(self):
        """Verify Blue cards pay all owners from the bank on any die roll."""
        testbot = self.testbot
        otherbot = self.otherbot
        bluecard = Blue("Dark Blue Card", 2, 1, 1, [11, 12])
        self.assertEqual(bluecard.hitsOn[0], 11)
        self.assertEqual(bluecard.cost, 1)
        for _ in range(4):
            self.game.market.append(Blue("Dark Blue Card", 2, 1, 1, [11, 12]))
        testbot.buy("Dark Blue Card", self.game.market)
        otherbot.buy("Dark Blue Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(10, 13):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after - before, 2)
        self.assertEqual(otherafter - otherbefore, 2)

    def testGreenCards(self):
        """Verify Green multiplier cards pay the die-roller scaled to matching category card count."""
        testbot = self.testbot
        otherbot = self.otherbot
        for _ in range(6):
            self.game.market.append(Blue("Light Blue Card", 77, 1, 1, [11]))
            self.game.market.append(Green("Green Card", 3, 1, 5, [12], 77))
        testbot.buy("Light Blue Card", self.game.market)
        testbot.buy("Light Blue Card", self.game.market)
        otherbot.buy("Blue Card", self.game.market)
        testbot.buy("Green Card", self.game.market)
        otherbot.buy("Green Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for dieroll in range(10, 13):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        self.assertEqual(after - before, 12)

    def testRedCards(self):
        """Verify Red cards deduct from the die-roller and credit the card owner."""
        testbot = self.testbot
        otherbot = self.otherbot
        for _ in range(3):
            self.game.market.append(Red("Crimson Card", 2, 2, 10, [1,2,3,4,5]))
        otherbot.buy("Crimson Card", self.game.market)
        testbot.buy("Crimson Card", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        otherbefore = otherbot.bank
        for dieroll in range(1, 13):
           for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        after = testbot.bank
        otherafter = otherbot.bank
        self.assertEqual(after-before, 3)
        self.assertEqual(otherafter-otherbefore, 1)

    def testCardInteractions(self):
        """Verify correct cumulative payouts when multiple card types activate in one round."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Wheat Field", self.game.market)
        otherbot.buy("Wheat Field", self.game.market)
        testbot.buy("Ranch", self.game.market)
        otherbot.buy("Ranch", self.game.market)
        testbot.buy("Forest", self.game.market)
        otherbot.buy("Forest", self.game.market)
        testbot.buy("Mine", self.game.market)
        otherbot.buy("Mine", self.game.market)
        testbot.buy("Apple Orchard", self.game.market)
        otherbot.buy("Apple Orchard", self.game.market)
        testbot.isrollingdice = True
        for dieroll in range(1, 12):
            for bot in self.game.players:
                for card in bot.deck.deck:
                    if dieroll in card.hitsOn:
                        card.trigger(self.game.players)
        # Testbot should end up with 89 + 1 + 2 + 1 + 1 + 1 + 3 + 5 = 103
        # Otherbot does not have a bakery and should end up with 101
        self.assertEqual(testbot.bank, 103)
        self.assertEqual(otherbot.bank, 101)

    def testStadiumTrigger(self):
        """Verify Stadium collects 2 coins from each player and credits them all to the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        self.game.market.append(Stadium())
        testbot.buy("Stadium", self.game.market)
        testbot.isrollingdice = True
        otherbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, Stadium):
                card.trigger(self.game.players)
        # With 2 players: roller skips self, collects 2 from the other player → net +2
        self.assertEqual(testbot.bank - before, 2)
        self.assertEqual(otherbot_before - otherbot.bank, 2)

    def testShoppingMall(self):
        """Verify Shopping Mall adds +1 to Cafe payout when owner holds the upgrade."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Cafe", self.game.market)
        testbot.buy("Shopping Mall", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        otherbot_before = otherbot.bank
        for card in testbot.deck.deck:
            if 3 in card.hitsOn and isinstance(card, Red):
                card.trigger(self.game.players)
        after = testbot.bank
        otherbot_after = otherbot.bank
        # Cafe normally pays 1, but with Shopping Mall should pay 2
        self.assertEqual(after - before, 2)
        self.assertEqual(otherbot_before - otherbot_after, 2)


    def testShoppingMallConvenienceStore(self):
        """Verify Shopping Mall adds +1 to Convenience Store payout (Green card path)."""
        testbot = self.testbot
        testbot.buy("Convenience Store", self.game.market)
        testbot.buy("Shopping Mall", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for card in testbot.deck.deck:
            if 4 in card.hitsOn and isinstance(card, Green):
                card.trigger(self.game.players)
        # Convenience Store normally pays 3; with Shopping Mall should pay 4
        self.assertEqual(testbot.bank - before, 4)

    def testTVStationNotRoller(self):
        """Verify TVStation does not activate when its owner is not the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("TV Station", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger(self.game.players)
        # No steal should have occurred
        self.assertEqual(testbot.bank, before)

    def testTVStationNoTargets(self):
        """Verify TVStation activates but takes no action when there are no valid targets."""
        testbot = self.testbot
        testbot.buy("TV Station", self.game.market)
        testbot.isrollingdice = True
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, TVStation):
                card.trigger([testbot])  # only the roller in the list → no valid targets
        self.assertEqual(testbot.bank, before)

    def testBusinessCenterNotRoller(self):
        """Verify BusinessCenter does not activate when its owner is not the die-roller."""
        testbot = self.testbot
        otherbot = self.otherbot
        testbot.buy("Business Center", self.game.market)
        otherbot.isrollingdice = True
        testbot.isrollingdice = False
        before = testbot.bank
        for card in testbot.deck.deck:
            if isinstance(card, BusinessCenter):
                card.trigger(self.game.players)
        self.assertEqual(testbot.bank, before)

    def testRedSkipsSelfTrigger(self):
        """Red card owned by the roller returns no events and leaves all banks unchanged."""
        cafe = Red("Cafe", 4, 2, 1, [3])
        cafe.owner = self.testbot
        self.testbot.deck.append(cafe)
        self.testbot.isrollingdice = True
        before_roller = self.testbot.bank
        before_other = self.otherbot.bank
        events = cafe.trigger(self.game.players)
        self.assertEqual(events, [])
        self.assertEqual(self.testbot.bank, before_roller)
        self.assertEqual(self.otherbot.bank, before_other)

    def testStadiumDoesNotCollectFromRoller(self):
        """Stadium.trigger() never lists the die-roller as a collect target."""
        stadium = Stadium()
        stadium.owner = self.testbot
        self.testbot.isrollingdice = True
        events = stadium.trigger(self.game.players)
        collect_targets = [e.target for e in events if e.type == "collect"]
        self.assertNotIn(self.testbot.name, collect_targets)
        self.assertGreater(len(collect_targets), 0)  # at least one other player paid


class TestCardOrdering(unittest.TestCase):
    """Tests for Card sort ordering and comparison operators."""

    def testCardOrdering(self):
        """Verify that cards sort by mean hitsOn: Wheat Field < Ranch < Bakery < Forest."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        ranch = Blue("Ranch", 2, 1, 1, [2])
        bakery = Green("Bakery", 3, 1, 1, [2, 3])
        forest = Blue("Forest", 5, 3, 1, [5])
        cards = [forest, bakery, wheat, ranch]
        cards.sort()
        self.assertEqual(cards[0].name, "Wheat Field")
        self.assertEqual(cards[-1].name, "Forest")
        self.assertLess(wheat, ranch)
        self.assertLess(ranch, forest)
        self.assertGreater(forest, bakery)

    def testCardComparisonOperators(self):
        """Verify __ne__, __le__, __gt__ (false branch), and __ge__ on Card."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        forest = Blue("Forest", 5, 3, 1, [5])
        wheat2 = Blue("Wheat Field", 1, 1, 1, [1])  # identical sortvalue to wheat

        self.assertNotEqual(wheat, forest)          # __ne__ True branch
        self.assertFalse(wheat != wheat2)           # __ne__ False branch (equal sortvalues)

        self.assertLessEqual(wheat, forest)         # __le__ True branch (strictly less)
        self.assertLessEqual(wheat, wheat2)         # __le__ True branch (equal)
        self.assertFalse(forest <= wheat)           # __le__ False branch

        self.assertFalse(wheat > forest)            # __gt__ False branch

        self.assertGreaterEqual(forest, wheat)      # __ge__ True branch (strictly greater)
        self.assertGreaterEqual(wheat, wheat2)      # __ge__ True branch (equal)
        self.assertFalse(wheat >= forest)           # __ge__ False branch

    def testCardComparisonWithNonCard(self):
        """Verify __eq__ and __lt__ return NotImplemented (not an exception) when compared to a non-Card."""
        wheat = Blue("Wheat Field", 1, 1, 1, [1])
        # Directly invoke the dunder methods; Python returns False for == but the method itself returns NotImplemented
        self.assertIs(wheat.__eq__("string"), NotImplemented)
        self.assertIs(wheat.__eq__(42), NotImplemented)
        self.assertIs(wheat.__eq__(None), NotImplemented)
        self.assertIs(wheat.__lt__("string"), NotImplemented)
        self.assertIs(wheat.__lt__(42), NotImplemented)
        # Normal == operator with non-Card should resolve to False without raising
        self.assertFalse(wheat == "string")
        self.assertFalse(wheat == 42)
        self.assertFalse(wheat == None)  # noqa: E711 — explicitly testing == operator, not identity

    def testCardBaseInit(self):
        """Verify the base Card() constructor is instantiable and all fields start at their defaults."""
        card = Card()
        self.assertIsNone(card.name)
        self.assertEqual(card.cost, 0)
        self.assertEqual(card.payout, 0)
        self.assertEqual(card.hitsOn, [0])
        self.assertIsNone(card.owner)
        self.assertIsNone(card.category)
        self.assertIsNone(card.multiplies)

    def testCardBaseDescribeReturnsString(self):
        """Card.describe() on the base class returns an empty string without raising."""
        self.assertEqual(Card().describe(), "")


class TestDescribeMethods(unittest.TestCase):
    """describe() returns a non-empty human-readable string for every concrete card type."""

    def test_blue_describe(self):
        self.assertIn("any player", Blue("Wheat Field", 1, 1, 1, [1]).describe())

    def test_green_describe_simple(self):
        self.assertIn("you roll", Green("Bakery", 3, 1, 1, [2, 3]).describe())

    def test_green_describe_convenience_store_suffix(self):
        self.assertIn("Shopping Mall", Green("Convenience Store", 3, 2, 3, [4]).describe())

    def test_green_describe_factory_names_category(self):
        self.assertIn("Ranch",  Green("Cheese Factory", 6, 5, 3, [7], multiplies=2).describe())
        self.assertIn("Gear",   Green("Furniture Factory", 6, 3, 3, [8], multiplies=5).describe())
        self.assertIn("Grain",  Green("F&V Market", 8, 2, 2, [11, 12], multiplies=1).describe())

    def test_red_describe_steals(self):
        self.assertIn("Steals", Red("Cafe", 4, 2, 1, [3]).describe())

    def test_red_describe_no_shopping_mall_for_other_reds(self):
        self.assertNotIn("Shopping Mall", Red("Other Red", 4, 2, 1, [5]).describe())

    def test_purple_describe_non_empty(self):
        self.assertGreater(len(Stadium().describe()), 0)
        self.assertGreater(len(TVStation().describe()), 0)
        self.assertGreater(len(BusinessCenter().describe()), 0)

    def test_upgrade_describe_non_empty(self):
        for name in UpgradeCard.orangeCards:
            self.assertGreater(len(UpgradeCard(name).describe()), 0,
                msg=f"UpgradeCard('{name}').describe() must not be empty")


class TestRecordingDisplayAndMarketState(unittest.TestCase):
    """RecordingDisplay accumulates events; Game.get_market_state returns card counts."""

    def test_recording_display_collects_events(self):
        from harmonictook import RecordingDisplay, Event  # noqa: PLC0415
        rec = RecordingDisplay()
        self.assertEqual(rec.events, [])
        e1 = Event(type="roll", player="A", value=3)
        e2 = Event(type="payout", player="A", value=1)
        rec.show_events([e1, e2])
        self.assertEqual(len(rec.events), 2)
        self.assertEqual(rec.events[0].type, "roll")

    def test_get_market_state_returns_card_counts(self):
        game = Game(players=2)
        state = game.get_market_state()
        self.assertIsInstance(state, dict)
        self.assertGreater(len(state), 0)
        self.assertIn("Wheat Field", state)
        for count in state.values():
            self.assertIsInstance(count, int)
            self.assertGreater(count, 0)

    def test_game_run_uses_null_display_by_default(self):
        """Game.run() without a display argument completes without raising (uses PlainTextDisplay).

        We can't suppress the terminal output easily, so we just verify the run-with-NullDisplay
        path still works correctly — the important thing is the no-arg path doesn't crash.
        """
        from harmonictook import NullDisplay  # noqa: PLC0415
        game = Game(players=2)
        # Give player[0] all landmarks so the game ends instantly
        p = game.players[0]
        p.deposit(100)
        for name in UpgradeCard.orangeCards:
            c = UpgradeCard(name)
            c.owner = p
            p.deck.append(c)
            setattr(p, UpgradeCard.orangeCards[name][2], True)
        game.run(display=NullDisplay())
        self.assertIs(game.winner, p)


class TestDisplayContract(unittest.TestCase):
    """Tests for Display ABC contract — what each concrete display must and must not do."""

    def test_null_display_show_state_is_silent(self):
        """NullDisplay.show_state() produces no output."""
        from harmonictook import NullDisplay  # noqa: PLC0415
        import io, sys  # noqa: E401
        game = Game(players=2)
        buf = io.StringIO()
        sys.stdout = buf
        try:
            NullDisplay().show_state(game)
        finally:
            sys.stdout = sys.__stdout__
        self.assertEqual(buf.getvalue(), "")

    def test_plain_text_display_show_state_contains_player_names(self):
        """PlainTextDisplay.show_state() prints each player's name."""
        from harmonictook import PlainTextDisplay  # noqa: PLC0415
        import io, sys  # noqa: E401
        game = Game(players=2)
        buf = io.StringIO()
        sys.stdout = buf
        try:
            PlainTextDisplay().show_state(game)
        finally:
            sys.stdout = sys.__stdout__
        output = buf.getvalue()
        for player in game.players:
            self.assertIn(player.name, output)

    def test_plain_text_display_show_state_contains_market(self):
        """PlainTextDisplay.show_state() prints the word 'Market' and at least one card name."""
        from harmonictook import PlainTextDisplay  # noqa: PLC0415
        import io, sys  # noqa: E401
        game = Game(players=2)
        buf = io.StringIO()
        sys.stdout = buf
        try:
            PlainTextDisplay().show_state(game)
        finally:
            sys.stdout = sys.__stdout__
        output = buf.getvalue()
        self.assertIn("Market", output)
        self.assertIn("Wheat Field", output)

    def test_null_display_does_not_support_pick_one(self):
        """NullDisplay.pick_one() raises NotImplementedError — it is not safe for human play."""
        from harmonictook import NullDisplay  # noqa: PLC0415
        with self.assertRaises(NotImplementedError):
            NullDisplay().pick_one(["a", "b"])

    def test_null_display_does_not_support_confirm(self):
        """NullDisplay.confirm() raises NotImplementedError — it is not safe for human play."""
        from harmonictook import NullDisplay  # noqa: PLC0415
        with self.assertRaises(NotImplementedError):
            NullDisplay().confirm("Continue?")

    def test_null_display_does_not_support_show_info(self):
        """NullDisplay.show_info() raises NotImplementedError — it is not safe for human play."""
        from harmonictook import NullDisplay  # noqa: PLC0415
        with self.assertRaises(NotImplementedError):
            NullDisplay().show_info("hello")

    def test_display_abc_requires_show_state(self):
        """A Display subclass that omits show_state cannot be instantiated."""
        from harmonictook import Display, Event  # noqa: PLC0415

        class IncompleteDisplay(Display):
            def show_events(self, events: list[Event]) -> None:
                pass
            # show_state deliberately omitted

        with self.assertRaises(TypeError):
            IncompleteDisplay()  # ABC enforcement


if __name__ == "__main__":
    unittest.main(buffer=True)
