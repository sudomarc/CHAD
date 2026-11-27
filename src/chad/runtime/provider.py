"""Provider-neutral model request contract.

Providers translate between this contract and vendor APIs. The runtime does
not assume streaming, tool calling, vision, or structured output; capability
support is declared per-model by the adapter (docs/model-providers.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .contracts import Message, ToolCall
from .tools import ToolSchema


@dataclass(frozen=True)
class ModelResponse:
    content: str
    tool_calls: tuple[ToolCall, ...] = ()


@runtime_checkable
class Provider(Protocol):
    """A model provider implementing the normalized contract."""

    def request(
        self,
        messages: tuple[Message, ...],
        tool_schemas: tuple[ToolSchema, ...],
    ) -> ModelResponse:
        """Synchronously produce a model response.

        Returns a completed response; never simulate streaming token events.
        """
        ...
