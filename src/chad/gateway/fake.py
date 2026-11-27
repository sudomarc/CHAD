"""Fake model provider adapter for deterministic tests (M3 / issue #69).

Returns scripted completions without any network or credentials. Used by
runtime and TUI tests so CI never depends on live provider access.
"""

from __future__ import annotations

from typing import Any

from chad.gateway.capabilities import Capabilities
from chad.gateway.errors import GatewayError
from chad.gateway.provider_contract import ModelResponse


class FakeProvider:
    name = "fake"

    def __init__(
        self,
        responses: list[ModelResponse] | None = None,
        error: GatewayError | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def capabilities_for(self, model: str) -> Capabilities:
        return Capabilities(
            model=model,
            provider="fake",
            streaming=False,
            tool_calling=True,
        )

    def request(
        self,
        model: str,
        messages: tuple,
        tool_schemas: tuple,
    ) -> ModelResponse:
        self.calls.append(
            {"model": model, "messages": list(messages), "tool_schemas": list(tool_schemas)}
        )
        if self.error is not None:
            raise self.error
        if self.responses:
            return self.responses.pop(0)
        return ModelResponse(content="ok")
