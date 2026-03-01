#!/usr/bin/python3
# -*- coding: UTF-8 -*-
# color_tui.py — ColorTUIDisplay: full-screen Textual TUI for Harmonic Took.
#
# Requires: pip install textual
# See docs/color-tui-plan.md for the incremental implementation plan.

from __future__ import annotations

from harmonictook import Display, Event, Game


class ColorTUIDisplay(Display):
    """Full-screen TUI display powered by Textual.

    Not yet implemented — stub satisfies the Display ABC so the class
    can be imported and instantiated. Each method will raise
    NotImplementedError until the corresponding commit lands.

    See docs/color-tui-plan.md for the build plan.
    """

    def show_events(self, events: list[Event]) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_events() not yet implemented")

    def show_state(self, game: Game) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_state() not yet implemented")

    def pick_one(self, options: list, prompt: str = "Your selection: ",
                 formatter: callable = str) -> object:
        raise NotImplementedError("ColorTUIDisplay.pick_one() not yet implemented")

    def confirm(self, prompt: str) -> bool:
        raise NotImplementedError("ColorTUIDisplay.confirm() not yet implemented")

    def show_info(self, content: str) -> None:
        raise NotImplementedError("ColorTUIDisplay.show_info() not yet implemented")
