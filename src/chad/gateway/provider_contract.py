"""Provider-neutral model request contract (M3).

The gateway owns this contract; the agent runtime consumes it. Providers are
free to declare what they support; the runtime never assumes streaming, tool
calling, vision, or structured output (docs/model-providers.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from chad.runtime.contracts import Message, ToolCall


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


@runtime_checkable
class Provider(Protocol):
    """A model provider implementing the normalized contract."""

    def capabilities_for(self, model: str):
        """Return declared capabilities for ``model``."""

    def request(
        self,
        model: str,
        messages: tuple[Message, ...],
        tool_schemas: tuple,
    ) -> ModelResponse:
        """Synchronously produce a completed model response.

        Never simulate streaming token events.
        """
        ...
