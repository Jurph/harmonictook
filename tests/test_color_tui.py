#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_color_tui.py — ColorTUIDisplay and HarmonicTookApp layout tests

import unittest
from harmonictook import Display, Event, Game


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

    def test_show_state_raises_not_implemented(self):
        """show_state() raises NotImplementedError until Commit 3 lands."""
        game = Game(players=2)
        with self.assertRaises(NotImplementedError):
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


if __name__ == "__main__":
    unittest.main(buffer=True)
