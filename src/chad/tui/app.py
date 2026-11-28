"""CHAD terminal UI shell (Textual).

Provides a transcript view, user input, a status line, and cancellation.
The shell is connected to the bounded agent runtime, rendering events
as they occur and exposing approval/denial workflows.
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
    Transcript .assistant {
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
    Transcript .tool-call {
        color: $primary;
    }
    Transcript .tool-result {
        color: $accent;
    }
    Transcript .permission {
        color: $warning;
        background: $warning-darken-2;
        padding: 1;
        margin: 0 -1;
    }
    """

    def add(self, text: str, kind: str = "system") -> None:
        stamp = f"[{_now()}]"
        line = Static(f"{stamp}  {text}", classes=kind, expand=True)
        self.mount(line)
        self.scroll_end(animate=False)

    def add_multiline(self, text: str, kind: str = "system") -> None:
        """Add multi-line text, preserving line breaks."""
        stamp = f"[{_now()}]"
        # Split into lines and add each with the same timestamp
        for i, line_text in enumerate(text.splitlines()):
            prefix = stamp if i == 0 else " " * len(stamp)
            line = Static(f"{prefix}  {line_text}", classes=kind, expand=True)
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

    The TUI connects to the agent runtime and renders events in real-time.
    Supports approval/denial of tool calls, cancellation, and session management.
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
    #permission-container {
        height: auto;
        padding: 1;
        border: solid $warning;
        background: $warning-darken-3;
    }
    #permission-message {
        color: $warning;
        margin: 0 0 1 0;
    }
    #permission-buttons {
        align: right middle;
    }
    Button {
        margin: 0 1;
    }
    .hidden {
        display: none;
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
    ) -> None:
        super().__init__()
        self.runtime = runtime
        self._running = False
        self._pending_permission: dict | None = None
        self._permission_callback: Callable[[bool], None] | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Transcript(id="transcript")
        yield StatusBar(id="status")
        with Vertical(id="input-container"):
            yield Input(placeholder="Type a task and press Enter…", id="command-input")
        # Permission dialog (hidden by default)
        with Vertical(id="permission-container", classes="hidden"):
            yield Static(id="permission-message")
            with Vertical(id="permission-buttons"):
                yield Input(placeholder="Type 'allow' or 'deny'", id="permission-input")
        yield Footer()

    def on_mount(self) -> None:
        input_widget = self.query_one("#command-input", Input)
        input_widget.focus()
        transcript = self.query_one("#transcript", Transcript)
        status = self.query_one("#status", StatusBar)
        transcript.add("CHAD — Local-first coding agent ready.", kind="system")
        transcript.add("Type a task and press Enter to start.", kind="system")
        status.status = "idle"

        # Connect runtime event handler if available
        if self.runtime and hasattr(self.runtime, "_on_event_callback"):
            self.runtime._on_event_callback = self._handle_runtime_event

    def _handle_runtime_event(self, event) -> None:
        """Handle events from the agent runtime."""

        # Use call_from_thread for thread-safe UI updates
        def update_ui():
            self._process_event(event)

        self.call_from_thread(update_ui)

    def _process_event(self, event) -> None:
        """Process a runtime event and update the UI."""
        from chad.runtime.events import EventType

        transcript = self.query_one("#transcript", Transcript)
        status = self.query_one("#status", StatusBar)

        if event.type == EventType.MODEL_REQUEST_STARTED:
            transcript.add("Model request started…", kind="runtime")
            status.status = "running"

        elif event.type == EventType.MODEL_RESPONSE_RECEIVED:
            tool_calls = event.payload.get("tool_calls", 0)
            content_len = event.payload.get("content_len", 0)
            if tool_calls > 0:
                transcript.add(f"Model requested {tool_calls} tool call(s)", kind="runtime")
            elif content_len > 0:
                transcript.add("Model responded (no tool calls)", kind="runtime")

        elif event.type == EventType.TOOL_REQUESTED:
            transcript.add(f"Tool requested: {event.payload.get('tool', 'unknown')}", kind="tool-call")

        elif event.type == EventType.PERMISSION_REQUIRED:
            self._show_permission_dialog(event.payload)

        elif event.type == EventType.TOOL_COMPLETED:
            tool = event.payload.get("tool", "unknown")
            ok = event.payload.get("ok", False)
            error = event.payload.get("error")
            if ok:
                transcript.add(f"✓ Tool completed: {tool}", kind="tool-result")
            else:
                transcript.add(f"✗ Tool failed: {tool} — {error}", kind="error")

        elif event.type == EventType.ITERATION_COMPLETED:
            iteration = event.payload.get("iteration", 0)
            transcript.add(f"Iteration {iteration} completed", kind="runtime")

        elif event.type == EventType.TASK_FINISHED:
            status.status = "idle"
            transcript.add("Task completed.", kind="system")
            self._running = False

        elif event.type == EventType.TASK_FAILED:
            error = event.payload.get("error", "unknown error")
            status.status = "error"
            transcript.add(f"Task failed: {error}", kind="error")
            self._running = False

        elif event.type == EventType.TASK_CANCELLED:
            status.status = "idle"
            transcript.add("Task cancelled.", kind="system")
            self._running = False

    def _show_permission_dialog(self, payload: dict) -> None:
        """Show a permission dialog for tool execution."""
        tool = payload.get("tool", "unknown")
        arguments = payload.get("arguments", {})

        transcript = self.query_one("#transcript", Transcript)
        transcript.add(
            f"Permission required for tool: {tool}\nArguments: {arguments}",
            kind="permission"
        )

        # Show permission container
        permission_container = self.query_one("#permission-container")
        permission_container.remove_class("hidden")

        # Focus the permission input
        permission_input = self.query_one("#permission-input", Input)
        permission_input.focus()
        permission_input.placeholder = "Type 'allow' to approve, 'deny' to reject"

        # Store callback for permission decision
        self._pending_permission = payload
        self._permission_callback = None  # Will be set by runtime when it waits

        status = self.query_one("#status", StatusBar)
        status.status = "waiting"

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Check if this is the permission input
        if event.input.id == "permission-input":
            self._handle_permission_response(event.value.strip())
            return

        text = event.value.strip()
        if not text:
            return
        event.input.value = ""
        transcript = self.query_one("#transcript", Transcript)
        transcript.add(text, kind="user")
        self._dispatch(text)

    def _handle_permission_response(self, response: str) -> None:
        """Handle user response to permission dialog."""
        permission_container = self.query_one("#permission-container")
        permission_container.add_class("hidden")

        permission_input = self.query_one("#permission-input", Input)
        permission_input.value = ""

        # Resume input focus
        command_input = self.query_one("#command-input", Input)
        command_input.focus()

        # Process the response
        allowed = response.lower() in ("allow", "yes", "y", "a")
        transcript = self.query_one("#transcript", Transcript)

        if allowed:
            transcript.add("Permission granted.", kind="system")
        else:
            transcript.add("Permission denied.", kind="error")

        # Note: In a real implementation, this would call back to the runtime
        # to resume execution. For now we just log it.
        self._pending_permission = None

    def _dispatch(self, text: str) -> None:
        status = self.query_one("#status", StatusBar)
        transcript = self.query_one("#transcript", Transcript)

        if self.runtime is not None and hasattr(self.runtime, "submit"):
            status.status = "running"
            self._running = True
            try:
                self.runtime.submit(text)
            except Exception as exc:  # noqa: BLE001 - surface to user
                transcript.add(f"submit error: {exc}", kind="error")
                status.status = "error"
                self._running = False

    # --- actions --------------------------------------------------------

    def action_cancel(self) -> None:
        status = self.query_one("#status", StatusBar)
        transcript = self.query_one("#transcript", Transcript)
        if self.runtime is not None and hasattr(self.runtime, "cancel"):
            self.runtime.cancel()
            transcript.add("Cancellation requested.", kind="system")
        else:
            transcript.add("Nothing to cancel.", kind="system")
        status.status = "idle"
        self._running = False

    def action_clear(self) -> None:
        transcript = self.query_one("#transcript", Transcript)
        transcript.remove_children()
        transcript.add("Transcript cleared.", kind="system")

    def action_quit(self) -> None:  # type: ignore
        self.exit()