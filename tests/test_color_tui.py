#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_color_tui.py — ColorTUIDisplay and HarmonicTookApp layout tests

import threading
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

    def test_show_events_raises_runtime_error_without_app(self):
        """show_events() raises RuntimeError when no app has been connected."""
        with self.assertRaises(RuntimeError):
            self.cls().show_events([Event(type="roll", player="A", value=3)])

    def test_show_state_raises_runtime_error_without_app(self):
        """show_state() raises RuntimeError when no app has been connected."""
        game = Game(players=2)
        with self.assertRaises(RuntimeError):
            self.cls().show_state(game)

    def test_pick_one_raises_runtime_error_without_app(self):
        """pick_one() raises RuntimeError when no app has been connected."""
        with self.assertRaises(RuntimeError):
            self.cls().pick_one(["a", "b"])

    def test_confirm_raises_runtime_error_without_app(self):
        """confirm() raises RuntimeError when no app has been connected."""
        with self.assertRaises(RuntimeError):
            self.cls().confirm("Continue?")

    def test_show_info_raises_runtime_error_without_app(self):
        """show_info() raises RuntimeError when no app has been connected."""
        with self.assertRaises(RuntimeError):
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


class TestEventToStr(unittest.TestCase):
    """_event_to_str() converts Event objects to log strings or None for silent events."""

    def setUp(self):
        from color_tui import _event_to_str  # noqa: PLC0415
        self.to_str = _event_to_str

    def test_roll_contains_player_and_value(self):
        """Roll event string names the player and includes the die value."""
        result = self.to_str(Event(type="roll", player="Alice", value=6))
        self.assertIn("Alice", result)
        self.assertIn("6", result)

    def test_payout_contains_card_player_and_amount(self):
        """Payout event string names the card, player, and coin amount."""
        result = self.to_str(Event(type="payout", card="Ranch", player="Bob", value=2))
        self.assertIn("Ranch", result)
        self.assertIn("Bob", result)
        self.assertIn("2", result)

    def test_buy_contains_card_and_price(self):
        """Buy event string names the card purchased and the price paid."""
        result = self.to_str(Event(type="buy", player="Alice", card="Forest",
                                   value=3, remaining_bank=7))
        self.assertIn("Forest", result)
        self.assertIn("3", result)

    def test_win_contains_player_name(self):
        """Win event string names the winner."""
        result = self.to_str(Event(type="win", player="Carol"))
        self.assertIn("Carol", result)

    def test_pass_contains_player_name(self):
        """Pass event string names the player who passed."""
        result = self.to_str(Event(type="pass", player="Bob"))
        self.assertIn("Bob", result)

    def test_collect_is_silent(self):
        """Stadium collect events return None — they are silent in the TUI."""
        self.assertIsNone(self.to_str(Event(type="collect", player="Alice", value=2)))

    def test_deck_state_is_silent(self):
        """Deck state events return None — the panel shows deck state visually."""
        self.assertIsNone(self.to_str(Event(type="deck_state", message="some table")))

    def test_unknown_event_type_is_silent(self):
        """Unrecognised event types return None rather than raising."""
        import dataclasses  # noqa: PLC0415
        e = Event(type="roll", player="X", value=1)
        e = dataclasses.replace(e, type="totally_unknown")  # type: ignore[arg-type]
        self.assertIsNone(self.to_str(e))


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

    def test_empty_deck_shows_twelve_uncovered_rows(self):
        """A player with no establishment cards gets twelve '·' rows, one per die face."""
        game = Game(players=2)
        player = game.players[0]
        player.deck.deck.clear()
        result = self.cards_markup(player)
        self.assertEqual(result.count("·"), 12)
        self.assertEqual(result.count("│"), 12)


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
            self.assertIn("Mkt", content)

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


class TestHarmonicTookAppAddEvents(unittest.IsolatedAsyncioTestCase):
    """HarmonicTookApp.add_events() and ColorTUIDisplay.show_events() feed the EventLog."""

    async def test_single_event_adds_to_log(self):
        """A single renderable event adds exactly one line to the EventLog."""
        from color_tui import HarmonicTookApp, EventLog  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)) as pilot:
            before = len(app.query_one(EventLog).lines)
            app.add_events([Event(type="roll", player="Alice", value=4)])
            await pilot.pause()
            self.assertEqual(len(app.query_one(EventLog).lines), before + 1)

    def _line_text(self, log: object) -> str:
        """Flatten all rendered EventLog lines into a single searchable string."""
        return " ".join(
            "".join(seg.text for seg in strip)
            for strip in log.lines  # type: ignore[attr-defined]
        )

    async def test_event_text_appears_in_log(self):
        """The player name from a roll event is visible in the rendered EventLog."""
        from color_tui import HarmonicTookApp, EventLog  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)) as pilot:
            app.add_events([Event(type="roll", player="Zephyr", value=5)])
            await pilot.pause()
            self.assertIn("Zephyr", self._line_text(app.query_one(EventLog)))

    async def test_silent_event_does_not_add_to_log(self):
        """A silent event (collect) does not add a line to the EventLog."""
        from color_tui import HarmonicTookApp, EventLog  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)) as pilot:
            before = len(app.query_one(EventLog).lines)
            app.add_events([Event(type="collect", player="Alice", value=3)])
            await pilot.pause()
            self.assertEqual(len(app.query_one(EventLog).lines), before)

    async def test_mixed_batch_only_adds_renderable_events(self):
        """A batch with silent and renderable events adds only renderable ones."""
        from color_tui import HarmonicTookApp, EventLog  # noqa: PLC0415
        app = HarmonicTookApp()
        async with app.run_test(size=(120, 40)) as pilot:
            before = len(app.query_one(EventLog).lines)
            app.add_events([
                Event(type="roll",    player="Alice", value=3),   # renderable
                Event(type="collect", player="Alice", value=2),   # silent
                Event(type="payout",  card="Ranch", player="Alice", value=1),  # renderable
            ])
            await pilot.pause()
            self.assertEqual(len(app.query_one(EventLog).lines), before + 2)

    async def test_show_events_via_display_appends_to_log(self):
        """ColorTUIDisplay.show_events() routes through add_events() to the log."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay, EventLog  # noqa: PLC0415
        game = Game(players=2)
        app = HarmonicTookApp(game=game)
        display = ColorTUIDisplay(app=app)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            before = len(app.query_one(EventLog).lines)
            display.show_events([Event(type="pass", player="Bot1")])
            await pilot.pause()
            self.assertEqual(len(app.query_one(EventLog).lines), before + 1)
            self.assertIn("Bot1", self._line_text(app.query_one(EventLog)))


class TestThreadingBridge(unittest.IsolatedAsyncioTestCase):
    """pick_one(), confirm(), and show_info() use the threading.Event bridge."""

    def _line_text(self, log: object) -> str:
        return " ".join(
            "".join(seg.text for seg in strip) for strip in log.lines  # type: ignore[attr-defined]
        )

    async def test_pick_one_returns_selected_item(self):
        """pick_one() in a background thread returns the item resolved by resolve_bridge()."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay  # noqa: PLC0415
        game = Game(players=2)
        display = ColorTUIDisplay()
        app = HarmonicTookApp(game=game, display=display)
        options = ["Buy Ranch", "Pass"]
        result_holder: list = []

        async with app.run_test(size=(120, 40)) as pilot:
            def worker() -> None:
                result_holder.append(display.pick_one(options))

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            await pilot.pause(0.1)   # let the worker block on bridge_event
            app.resolve_bridge(options[1])
            t.join(timeout=2.0)

        self.assertEqual(result_holder, ["Pass"])

    async def test_confirm_returns_true_for_truthy_value(self):
        """confirm() in a background thread returns True when resolved with a truthy value."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay  # noqa: PLC0415
        game = Game(players=2)
        display = ColorTUIDisplay()
        app = HarmonicTookApp(game=game, display=display)
        result_holder: list = []

        async with app.run_test(size=(120, 40)) as pilot:
            def worker() -> None:
                result_holder.append(display.confirm("Roll two dice?"))

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            await pilot.pause(0.1)
            app.resolve_bridge(True)
            t.join(timeout=2.0)

        self.assertEqual(result_holder, [True])

    async def test_confirm_returns_false_for_falsy_value(self):
        """confirm() returns False when resolved with a falsy value."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay  # noqa: PLC0415
        game = Game(players=2)
        display = ColorTUIDisplay()
        app = HarmonicTookApp(game=game, display=display)
        result_holder: list = []

        async with app.run_test(size=(120, 40)) as pilot:
            def worker() -> None:
                result_holder.append(display.confirm("Re-roll?"))

            t = threading.Thread(target=worker, daemon=True)
            t.start()
            await pilot.pause(0.1)
            app.resolve_bridge(False)
            t.join(timeout=2.0)

        self.assertEqual(result_holder, [False])

    async def test_show_info_writes_to_event_log(self):
        """show_info() writes content to the EventLog via the Textual thread."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay, EventLog  # noqa: PLC0415
        game = Game(players=2)
        # Pass app= directly so display.app is set but the game worker is NOT started
        # (no display= arg to HarmonicTookApp, so on_mount() skips threading.Thread).
        app = HarmonicTookApp(game=game)
        display = ColorTUIDisplay(app=app)

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            before = len(app.query_one(EventLog).lines)
            display.show_info("informational message for the player")
            await pilot.pause()
            self.assertEqual(len(app.query_one(EventLog).lines), before + 1)

    async def test_bot_game_worker_logs_events(self):
        """A bot-only game started via HarmonicTookApp produces event log entries."""
        from color_tui import HarmonicTookApp, ColorTUIDisplay, EventLog  # noqa: PLC0415
        game = Game(players=2)
        display = ColorTUIDisplay()
        app = HarmonicTookApp(game=game, display=display)

        async with app.run_test(size=(120, 40)) as pilot:
            # Worker thread started by on_mount(); let it run a few turns
            await pilot.pause(0.3)
            log = app.query_one(EventLog)
            self.assertGreater(len(log.lines), 0,
                               "No events logged — worker thread may not have started")


class TestHumanKeyHandling(unittest.IsolatedAsyncioTestCase):
    """Keypresses in pick_one and confirm modes resolve the bridge correctly."""

    async def _app_with_game(self):
        """Return a fresh HarmonicTookApp with no worker thread."""
        from color_tui import HarmonicTookApp  # noqa: PLC0415
        # No display= arg → on_mount() skips the worker thread
        return HarmonicTookApp(game=Game(players=2))

    async def test_number_and_enter_resolve_pick_one(self):
        """Typing a digit and pressing Enter resolves pick_one with the matching option."""
        app = await self._app_with_game()
        options = ["Wheat Field", "Ranch", "Pass"]

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_prompt(options, str)
            await pilot.press("2")
            await pilot.press("enter")
            await pilot.pause()

        self.assertEqual(app._bridge_result, "Ranch")

    async def test_multi_digit_and_enter_resolve_pick_one(self):
        """Typing a two-digit number and Enter resolves pick_one with option[idx]."""
        app = await self._app_with_game()
        options = [f"Option {i}" for i in range(1, 12)]   # 11 options

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_prompt(options, str)
            await pilot.press("1")
            await pilot.press("1")
            await pilot.press("enter")
            await pilot.pause()

        self.assertEqual(app._bridge_result, "Option 11")

    async def test_backspace_corrects_buffer(self):
        """Backspace removes the last typed digit; Enter resolves with the corrected index."""
        app = await self._app_with_game()
        options = ["A", "B", "C"]

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_prompt(options, str)
            await pilot.press("2")
            await pilot.press("backspace")
            await pilot.press("3")
            await pilot.press("enter")
            await pilot.pause()

        self.assertEqual(app._bridge_result, "C")

    async def test_out_of_range_entry_does_not_resolve(self):
        """Entering a number larger than the option count does not resolve the bridge."""
        app = await self._app_with_game()
        options = ["A", "B"]

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_prompt(options, str)
            await pilot.press("9")
            await pilot.press("enter")
            await pilot.pause()

        self.assertIsNone(app._bridge_result)

    async def test_y_resolves_confirm_true(self):
        """Pressing 'y' when in confirm mode resolves the bridge with True."""
        app = await self._app_with_game()

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_confirm_prompt("Roll two dice?")
            await pilot.press("y")
            await pilot.pause()

        self.assertIs(app._bridge_result, True)

    async def test_n_resolves_confirm_false(self):
        """Pressing 'n' when in confirm mode resolves the bridge with False."""
        app = await self._app_with_game()

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.show_confirm_prompt("Re-roll?")
            await pilot.press("n")
            await pilot.pause()

        self.assertIs(app._bridge_result, False)

    async def test_keys_ignored_when_bridge_is_idle(self):
        """Number and letter keys do nothing when no bridge request is active."""
        app = await self._app_with_game()

        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # _bridge_mode is None — keypresses must not call resolve_bridge()
            await pilot.press("1")
            await pilot.press("y")
            await pilot.press("enter")
            await pilot.pause()

        self.assertIsNone(app._bridge_result)


if __name__ == "__main__":
    unittest.main(buffer=True)
