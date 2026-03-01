#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_color_tui.py — ColorTUIDisplay and HarmonicTookApp layout tests

import unittest
from harmonictook import Display, Event, Game, UpgradeCard


class TestColorTUIDisplaySkeleton(unittest.TestCase):
    """ColorTUIDisplay satisfies the Display ABC and fails loudly on unimplemented methods."""

    def setUp(self):
        from color_tui import ColorTUIDisplay  # noqa: PLC0415
        self.cls = ColorTUIDisplay

    def test_can_be_instantiated(self):
        """ColorTUIDisplay() constructs without error — ABC is fully satisfied."""
        instance = self.cls()
        self.assertIsNotNone(instance)

    def test_is_display_subclass(self):
        """ColorTUIDisplay is a subclass of Display."""
        self.assertTrue(issubclass(self.cls, Display))

    def test_show_events_raises_not_implemented(self):
        """show_events() raises NotImplementedError until Commit 4 lands."""
        with self.assertRaises(NotImplementedError):
            self.cls().show_events([Event(type="roll", player="A", value=3)])

    def test_show_state_raises_runtime_error_without_app(self):
        """show_state() raises RuntimeError when no app has been connected."""
        game = Game(players=2)
        with self.assertRaises(RuntimeError):
            self.cls().show_state(game)

    def test_pick_one_raises_not_implemented(self):
        """pick_one() raises NotImplementedError until Commit 5 lands."""
        with self.assertRaises(NotImplementedError):
            self.cls().pick_one(["a", "b"])

    def test_confirm_raises_not_implemented(self):
        """confirm() raises NotImplementedError until Commit 5 lands."""
        with self.assertRaises(NotImplementedError):
            self.cls().confirm("Continue?")

    def test_show_info_raises_not_implemented(self):
        """show_info() raises NotImplementedError until Commit 5 lands."""
        with self.assertRaises(NotImplementedError):
            self.cls().show_info("hello")

    def test_import_does_not_open_terminal(self):
        """Importing color_tui must not launch a Textual app or touch the terminal.

        Verified implicitly: if this test suite runs at all, the import was safe.
        Explicitly: no App instance is created at module level.
        """
        import color_tui  # noqa: PLC0415
        self.assertFalse(
            hasattr(color_tui, '_app_instance'),
            "color_tui must not create a Textual App at import time",
        )


class TestPlayerMarkup(unittest.TestCase):
    """_player_markup() formats player state correctly for PlayerPanel content."""

    def setUp(self):
        from color_tui import _player_markup  # noqa: PLC0415
        self.markup = _player_markup

    def test_active_player_has_arrow(self):
        """Active player's markup contains the ▶ marker."""
        result = self.markup("Alice", 12, "cards", "landmarks", active=True)
        self.assertIn("▶", result)

    def test_inactive_player_has_no_arrow(self):
        """Inactive player's markup does not contain the ▶ marker."""
        result = self.markup("Bob", 5, "cards", "landmarks", active=False)
        self.assertNotIn("▶", result)

    def test_markup_contains_player_name(self):
        """Player name appears in the markup regardless of active state."""
        for active in (True, False):
            with self.subTest(active=active):
                result = self.markup("Carol", 0, "cards", "landmarks", active=active)
                self.assertIn("Carol", result)

    def test_markup_contains_coin_count(self):
        """Coin count appears in the markup."""
        result = self.markup("Alice", 12, "cards", "landmarks", active=True)
        self.assertIn("12", result)

    def test_markup_contains_cards_and_landmarks(self):
        """Cards and landmarks strings are passed through into the markup."""
        result = self.markup("Alice", 0, "[green]■■[/green]", "● ○ ○ ○", active=True)
        self.assertIn("[green]■■[/green]", result)
        self.assertIn("● ○ ○ ○", result)


class TestHarmonicTookAppLayout(unittest.IsolatedAsyncioTestCase):
    """HarmonicTookApp composes the correct widget tree with placeholder data."""

    async def test_app_composes_without_error(self):
        """HarmonicTookApp runs headlessly without raising."""
        from color_tui import HarmonicTookApp  # noqa: PLC0415
        async with HarmonicTookApp().run_test(size=(120, 40)):
            pass

    async def test_market_panel_present(self):
        """A MarketPanel widget with id='market' exists in the layout."""
        from color_tui import HarmonicTookApp, MarketPanel  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            market = app.query_one("#market", MarketPanel)
            self.assertIsNotNone(market)

    async def test_player_area_present(self):
        """The Horizontal player area with id='player-area' exists."""
        from color_tui import HarmonicTookApp  # noqa: PLC0415
        from textual.containers import Horizontal  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            area = app.query_one("#player-area", Horizontal)
            self.assertIsNotNone(area)

    async def test_placeholder_renders_three_player_panels(self):
        """Placeholder data produces exactly three PlayerPanel widgets."""
        from color_tui import HarmonicTookApp, PlayerPanel, _PLACEHOLDER_PLAYERS  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            panels = app.query(PlayerPanel)
            self.assertEqual(len(panels), len(_PLACEHOLDER_PLAYERS))

    async def test_exactly_one_active_player_panel(self):
        """Exactly one PlayerPanel carries the 'active' CSS class."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            active_panels = [p for p in app.query(PlayerPanel) if p.has_class("active")]
            self.assertEqual(len(active_panels), 1)

    async def test_event_log_present(self):
        """An EventLog widget with id='event-log' exists in the layout."""
        from color_tui import HarmonicTookApp, EventLog  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            log = app.query_one("#event-log", EventLog)
            self.assertIsNotNone(log)

    async def test_io_panel_present(self):
        """An IOPanel widget with id='io-panel' exists in the layout."""
        from color_tui import HarmonicTookApp, IOPanel  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            io = app.query_one("#io-panel", IOPanel)
            self.assertIsNotNone(io)

    async def test_inactive_panels_not_marked_active(self):
        """PlayerPanels for non-active players do not carry the 'active' class."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)):
            inactive = [p for p in app.query(PlayerPanel) if p.has_class("inactive")]
            # Two of three placeholder players are inactive
            self.assertEqual(len(inactive), 2)

    async def test_event_log_receives_entries_on_mount(self):
        """EventLog contains at least one rendered line after on_mount() runs."""
        from color_tui import HarmonicTookApp, EventLog, _PLACEHOLDER_EVENTS  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            log = app.query_one(EventLog)
            self.assertGreaterEqual(len(log.lines), len(_PLACEHOLDER_EVENTS))


class TestCardsAndLandmarksMarkup(unittest.TestCase):
    """_cards_markup() and _landmarks_markup() reflect actual player deck state."""

    def setUp(self):
        from color_tui import _cards_markup, _landmarks_markup  # noqa: PLC0415
        self.cards_markup = _cards_markup
        self.landmarks_markup = _landmarks_markup

    def test_starting_deck_has_blue_and_green(self):
        """A fresh player has one blue card (Wheat Field) and one green card (Bakery)."""
        game = Game(players=2)
        result = self.cards_markup(game.players[0])
        self.assertIn("[blue]", result)
        self.assertIn("[green]", result)

    def test_no_landmarks_gives_all_empty_circles(self):
        """A player with no landmarks gets four ○ symbols."""
        game = Game(players=2)
        result = self.landmarks_markup(game.players[0])
        self.assertEqual(result.count("○"), 4)
        self.assertEqual(result.count("●"), 0)

    def test_owning_train_station_fills_first_circle(self):
        """hasTrainStation=True produces exactly one ● in the first slot."""
        game = Game(players=2)
        player = game.players[0]
        player.hasTrainStation = True
        result = self.landmarks_markup(player)
        self.assertEqual(result.count("●"), 1)
        self.assertTrue(result.startswith("●"))

    def test_all_landmarks_gives_all_filled_circles(self):
        """A player with all four landmarks gets four ● symbols."""
        game = Game(players=2)
        player = game.players[0]
        player.hasTrainStation = True
        player.hasShoppingMall = True
        player.hasAmusementPark = True
        player.hasRadioTower = True
        result = self.landmarks_markup(player)
        self.assertEqual(result.count("●"), 4)
        self.assertEqual(result.count("○"), 0)

    def test_red_card_in_deck_shows_red_squares(self):
        """A player who owns a red card gets red squares in the card markup."""
        from harmonictook import Red  # noqa: PLC0415
        game = Game(players=2)
        player = game.players[0]
        red_card = Red("Cafe", 2, 1, 1, [3])
        red_card.owner = player
        player.deck.deck.append(red_card)
        result = self.cards_markup(player)
        self.assertIn("[red]", result)

    def test_empty_deck_returns_dash(self):
        """A player with no establishment cards gets a — placeholder."""
        game = Game(players=2)
        player = game.players[0]
        player.deck.deck.clear()
        result = self.cards_markup(player)
        self.assertEqual(result, "—")


class TestHarmonicTookAppUpdateState(unittest.IsolatedAsyncioTestCase):
    """HarmonicTookApp.update_state() and ColorTUIDisplay.show_state() wire game→widgets."""

    def _panel_content(self, panel: object) -> str:
        return str(getattr(panel, "_Static__content", ""))

    async def test_update_state_sets_market_text(self):
        """Market panel content contains real card names after update_state()."""
        from color_tui import HarmonicTookApp, MarketPanel  # noqa: PLC0415
        game = Game(players=2)
        app = HarmonicTookApp(game=game)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            content = self._panel_content(app.query_one(MarketPanel))
            self.assertIn("Wheat Field", content)
            self.assertIn("Market", content)

    async def test_update_state_sets_player_names(self):
        """Each PlayerPanel contains the corresponding player's name."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        game = Game(players=2)
        app = HarmonicTookApp(game=game)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            panels = list(app.query(PlayerPanel))
            for panel, player in zip(panels, game.players):
                self.assertIn(player.name, self._panel_content(panel))

    async def test_update_state_sets_coin_count(self):
        """PlayerPanel reflects the player's current bank balance."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        game = Game(players=2)
        game.players[0].deposit(7)
        app = HarmonicTookApp(game=game)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            content = self._panel_content(list(app.query(PlayerPanel))[0])
            self.assertIn("10", content)  # 3 starting coins + 7 deposited

    async def test_update_state_marks_active_player(self):
        """The panel for the current player carries the 'active' CSS class."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        game = Game(players=3)
        game.current_player_index = 1
        app = HarmonicTookApp(game=game)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            panels = list(app.query(PlayerPanel))
            self.assertTrue(panels[1].has_class("active"))
            self.assertFalse(panels[0].has_class("active"))
            self.assertFalse(panels[2].has_class("active"))

    async def test_update_state_panel_count_matches_player_count(self):
        """Exactly N PlayerPanels are created for an N-player game."""
        from color_tui import HarmonicTookApp, PlayerPanel  # noqa: PLC0415
        for n in (2, 3, 4):
            with self.subTest(players=n):
                app = HarmonicTookApp(game=Game(players=n))
                async with app.run_test(size=(120, 40)):
                    self.assertEqual(len(app.query(PlayerPanel)), n)

    async def test_show_state_via_display_updates_market(self):
        """ColorTUIDisplay.show_state() delegates to app.update_state()."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay, MarketPanel  # noqa: PLC0415
        game = Game(players=2)
        app = HarmonicTookApp(game=game)
        display = ColorTUIDisplay(app=app)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            game.players[0].deposit(10)  # mutate state
            display.show_state(game)
            await pilot.pause()
            content = self._panel_content(app.query_one(MarketPanel))
            self.assertIn("Wheat Field", content)


if __name__ == "__main__":
    unittest.main(buffer=True)
