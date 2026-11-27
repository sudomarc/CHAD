"""Anthropic Messages API adapter (M3, issue #80).

Maps the CHAD provider contract to Anthropic's ``/v1/messages`` shape via
``_http.post_json``. Completed responses only; no streaming simulation
(docs/model-providers.md).
"""

from __future__ import annotations

from typing import Any

from chad.gateway._http import post_json
from chad.gateway.capabilities import Capabilities
from chad.gateway.errors import GatewayError
from chad.gateway.provider_contract import ModelResponse
from chad.runtime.contracts import ToolCall

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    def capabilities_for(self, model: str) -> Capabilities:
        return Capabilities(
            model=model,
            provider="anthropic",
            streaming=False,
            tool_calling=True,
        )

    def request(
        self,
        model: str,
        messages: tuple,
        tool_schemas: tuple,
    ) -> ModelResponse:
        if not self.api_key:
            raise GatewayError(
                "anthropic: API key not configured (ANTHROPIC_API_KEY)"
            )
        system = ""
        chat_messages: list[dict[str, Any]] = []
        for m in messages:
            role = m.role.value
            if role == "system":
                system += m.content + "\n"
            else:
                role = "user" if role == "user" else "assistant"
                chat_messages.append({"role": role, "content": m.content})
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": chat_messages,
        }
        if system:
            payload["system"] = system.rstrip("\n")
        if tool_schemas:
            payload["tools"] = [
                {
                    "name": s.name,
                    "description": s.description or "",
                    "input_schema": s.input_schema or {},
                }
                for s in tool_schemas
            ]
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        body = post_json(
            self.name,
            f"{self.base_url}/messages",
            headers,
            payload,
            timeout=self.timeout,
        )
        content = ""
        tool_calls: tuple[ToolCall, ...] = ()
        for block in body.get("content") or []:
            btype = block.get("type")
            if btype == "text":
                content += block.get("text", "")
            elif btype == "tool_use":
                tool_calls += (
                    ToolCall(
                        id=block.get("id") or "",
                        name=block.get("name") or "",
                        arguments=block.get("input") or {},
                    ),
                )
        return ModelResponse(content=content, tool_calls=tool_calls)
