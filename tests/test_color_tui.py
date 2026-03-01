#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# tests/test_color_tui.py — ColorTUIDisplay skeleton tests
#
# These tests verify the Commit 1 skeleton: the class is importable,
# wired into the Display hierarchy, and each stub raises NotImplementedError
# with a message that tells the caller what's missing.

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


if __name__ == "__main__":
    unittest.main(buffer=True)
