"""Per-model capability declarations.

Capabilities must be explicit per model: streaming, tool calling, vision,
structured output, context limit, and supported modalities. Unknown values
remain unknown; nothing is assumed (docs/model-providers.md).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capabilities:
    model: str
    provider: str
    streaming: bool = False
    tool_calling: bool = False
    vision: bool = False
    structured_output: bool = False
    context_limit: int | None = None
    modalities: tuple[str, ...] = ("text",)


KNOWN_CAPABILITIES: dict[tuple[str, str], Capabilities] = {}


def register_capabilities(caps: Capabilities) -> None:
    KNOWN_CAPABILITIES[(caps.provider, caps.model)] = caps


def capabilities_for(provider: str, model: str) -> Capabilities:
    """Return declared capabilities for a model, or unknown defaults."""
    key = (provider, model)
    if key in KNOWN_CAPABILITIES:
        return KNOWN_CAPABILITIES[key]
    return Capabilities(model=model, provider=provider)
