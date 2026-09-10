from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True, slots=True)
class CommandResult:
    handled: bool
    should_exit: bool = False
    output: str | None = None


class CommandRouter:
    """Application controls. Non-command text remains ordinary model input."""

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[str], CommandResult]] = {
            "/help": lambda _: CommandResult(True, output=self.help_text()),
            "/quit": lambda _: CommandResult(True, should_exit=True),
            "/exit": lambda _: CommandResult(True, should_exit=True),
            "/clear": lambda _: CommandResult(True, output="__CLEAR__"),
            "/new": lambda _: CommandResult(True, output="__NEW__"),
        }

    def dispatch(self, text: str) -> CommandResult:
        stripped = text.strip()
        if not stripped.startswith("/"):
            return CommandResult(False)
        name = stripped.split(maxsplit=1)[0].lower()
        handler = self._handlers.get(name)
        if handler is None:
            return CommandResult(True, output=f"Unknown CHAD command: {name}. Try /help.")
        return handler(stripped)

    @staticmethod
    def help_text() -> str:
        return (
            "CHAD controls:\n"
            "  /help       Show this help\n"
            "  /new        Start a new conversation\n"
            "  /clear      Clear the current display\n"
            "  /quit       Exit CHAD\n\n"
            "Everything else is sent to your Lapis model as normal conversation."
        )
