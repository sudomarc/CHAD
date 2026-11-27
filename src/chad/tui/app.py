"""CHAD terminal UI shell (Textual).

Provides a transcript view, user input, a status line, and cancellation.
The shell is runtime-agnostic: an optional ``runtime`` object may be attached
later (issue #81 connects it to the bounded agent runtime). Without a
runtime, the shell runs in standalone mode and echoes user input.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


class Transcript(VerticalScroll):
    """Scrollable, read-only transcript of messages."""

    DEFAULT_CSS = """
    Transcript {
        height: 1fr;
        border: solid $primary-lighten-3;
        padding: 1;
    }
    Transcript > Static {
        width: 1fr;
        padding: 0 0 1 0;
    }
    Transcript .user {
        color: $text;
    }
    Transcript .system {
        color: $warning;
        text-style: italic;
    }
    Transcript .runtime {
        color: $success;
    }
    Transcript .error {
        color: $error;
    }
    """

    def add(self, text: str, kind: str = "system") -> None:
        stamp = f"[{_now()}]"
        line = Static(f"{stamp}  {text}", classes=kind, expand=True)
        self.mount(line)
        self.scroll_end(animate=False)


class StatusBar(Static):
    """Status line showing the current runtime state."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    StatusBar.running {
        color: $success;
    }
    StatusBar.waiting {
        color: $warning;
    }
    StatusBar.error {
        color: $error;
    }
    """

    status = reactive("idle")

    def watch_status(self, status: str) -> None:
        self.remove_class("running", "waiting", "error")
        if status in {"running", "waiting", "error"}:
            self.add_class(status)
        stamp = f"[{_now()}]"
        self.update(f"{stamp}  status: {status}")


class ChadApp(App):
    """CHAD TUI application.

    Attributes:
        runtime: optional runtime object with ``submit(task)`` and ``cancel()``
            methods. When absent, input is echoed in the transcript.
    """

    CSS = """
    Screen {
        layout: vertical;
    }
    #transcript {
        height: 1fr;
        border: solid $primary-lighten-3;
        padding: 1;
    }
    #status {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    #input-container {
        height: 3;
        padding: 0 1;
    }
    #command-input {
        width: 1fr;
    }
    #actions {
        height: auto;
        align: right middle;
    }
    Button {
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[
        list[Binding | tuple[str, str] | tuple[str, str, str]]
    ] = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+c", "cancel", "Cancel", show=True),
        Binding("ctrl+l", "clear", "Clear", show=True),
    ]

    def __init__(
        self,
        runtime: object | None = None,
        on_submit: Callable[[str], None] | None = None,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()
        self.runtime = runtime
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        self._running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Transcript(id="transcript")
        yield StatusBar(id="status")
        with Vertical(id="input-container"):
            yield Input(placeholder="Type a task and press Enter…", id="command-input")
        yield Footer()

    def on_mount(self) -> None:
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()
        transcript = self.query_one("#transcript", Transcript)
        status = self.query_one("#status", StatusBar)
        transcript.add("CHAD TUI shell ready.", kind="system")
        status.status = "idle"

    # --- input handling -------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        transcript = self.query_one("#transcript", Transcript)
        transcript.add(text, kind="user")
        self._dispatch(text)

    def _dispatch(self, text: str) -> None:
        status = self.query_one("#status", StatusBar)
        if self.runtime is not None and hasattr(self.runtime, "submit"):
            status.status = "running"
            self._running = True
            try:
                self.runtime.submit(text)
            except Exception as exc:  # noqa: BLE001 - surface to user
                transcript = self.query_one("#transcript", Transcript)
                transcript.add(f"submit error: {exc}", kind="error")
                status.status = "error"
                self._running = False
        elif self._on_submit is not None:
            status.status = "running"
            self._running = True
            try:
                self._on_submit(text)
            except Exception as exc:  # noqa: BLE001
                transcript = self.query_one("#transcript", Transcript)
                transcript.add(f"handler error: {exc}", kind="error")
                status.status = "error"
                self._running = False
        else:
            # Standalone mode: echo the input back as a system message.
            transcript = self.query_one("#transcript", Transcript)
            transcript.add(f"(standalone) received: {text}", kind="system")
            status.status = "idle"

    # --- actions --------------------------------------------------------

    def action_cancel(self) -> None:
        status = self.query_one("#status", StatusBar)
        transcript = self.query_one("#transcript", Transcript)
        if self.runtime is not None and hasattr(self.runtime, "cancel"):
            self.runtime.cancel()
            transcript.add("cancellation requested.", kind="system")
        elif self._on_cancel is not None:
            self._on_cancel()
            transcript.add("cancellation requested.", kind="system")
        else:
            transcript.add("nothing to cancel (standalone mode).", kind="system")
        status.status = "idle"
        self._running = False

    def action_clear(self) -> None:
        transcript = self.query_one("#transcript", Transcript)
        transcript.remove_children()
        transcript.add("transcript cleared.", kind="system")

    def action_quit(self) -> None:  # type: ignore
        self.exit()
