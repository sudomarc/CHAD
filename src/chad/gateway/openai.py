"""OpenAI-compatible chat-completions adapter (M3, issue #80).

Maps the CHAD provider contract to OpenAI's ``/v1/chat/completions`` shape.
All HTTP goes through ``_http.post_json``; errors are normalized via
``error_for_status``. No streaming — completed responses only, per
docs/model-providers.md.
"""

from __future__ import annotations

import json as _json
from typing import Any

from chad.gateway._http import post_json
from chad.gateway.capabilities import Capabilities
from chad.gateway.errors import GatewayError
from chad.gateway.provider_contract import ModelResponse
from chad.runtime.contracts import ToolCall


class OpenAIProvider:
    name = "openai"
    base_url = "https://api.openai.com/v1"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = (base_url or self.base_url).rstrip("/")
        self.timeout = timeout

    def capabilities_for(self, model: str) -> Capabilities:
        return Capabilities(
            model=model,
            provider="openai",
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
            raise GatewayError("openai: API key not configured (OPENAI_API_KEY)")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": m.role.value, "content": m.content} for m in messages
            ],
            "stream": False,
        }
        if tool_schemas:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": s.name,
                        "description": s.description or "",
                        "parameters": s.input_schema or {},
                    },
                }
                for s in tool_schemas
            ]
        body = post_json(
            self.name,
            f"{self.base_url}/chat/completions",
            headers,
            payload,
            timeout=self.timeout,
        )
        choice = (body.get("choices") or [{}])[0]
        message = choice.get("message", {})
        content = message.get("content") or ""
        tool_calls: tuple[ToolCall, ...] = ()
        for call in message.get("tool_calls") or []:
            fn = call.get("function", {})
            arguments = fn.get("arguments", "{}")
            try:
                parsed: Any = _json.loads(arguments)
            except _json.JSONDecodeError:
                parsed = {}
            tool_calls += (
                ToolCall(
                    id=call.get("id") or "",
                    name=fn.get("name") or "",
                    arguments=parsed if isinstance(parsed, dict) else {},
                ),
            )
        return ModelResponse(content=content, tool_calls=tool_calls)
