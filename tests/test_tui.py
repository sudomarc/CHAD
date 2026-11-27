"""Tests for the CHAD TUI shell."""

from __future__ import annotations

import asyncio
import unittest

from textual.widgets import Input

from chad.tui.app import ChadApp, StatusBar, Transcript


class TuiAppTests(unittest.TestCase):
    def test_app_instantiates(self):
        app = ChadApp()
        self.assertIsNone(app.runtime)
        self.assertFalse(app._running)

    def test_app_has_bindings(self):
        app = ChadApp()
        binding_keys = {b.key for b in app.BINDINGS}
        self.assertIn("ctrl+q", binding_keys)
        self.assertIn("ctrl+c", binding_keys)
        self.assertIn("ctrl+l", binding_keys)

    def test_compose_creates_widgets(self):
        asyncio.run(self._mounted())

    async def _mounted(self):
        app = ChadApp()
        async with app.run_test() as pilot:
            transcript = app.query_one("#transcript", Transcript)
            status = app.query_one("#status", StatusBar)
            input_widget = app.query_one("#command-input", Input)
            self.assertIsInstance(transcript, Transcript)
            self.assertIsInstance(status, StatusBar)
            self.assertEqual(input_widget.placeholder, "Type a task and press Enter…")
            self.assertEqual(status.status, "idle")
            await pilot.pause()

    def test_no_runtime_means_standalone(self):
        app = ChadApp()
        self.assertIsNone(app.runtime)
        self.assertIsNone(app._on_submit)
        self.assertIsNone(app._on_cancel)


if __name__ == "__main__":
    unittest.main()
