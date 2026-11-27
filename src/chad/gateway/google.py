"""Google Gemini generateContent adapter (M3, issue #80).

Maps the CHAD provider contract to Gemini's
``/v1beta/models/{model}:generateContent`` shape via ``_http.post_json``.
Completed responses only; no streaming simulation
(docs/model-providers.md).
"""

from __future__ import annotations

from typing import Any

from chad.gateway._http import post_json
from chad.gateway.capabilities import Capabilities
from chad.gateway.errors import GatewayError
from chad.gateway.provider_contract import ModelResponse

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GoogleProvider:
    name = "google"

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
            provider="google",
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
            raise GatewayError("google: API key not configured (GOOGLE_API_KEY)")
        contents: list[dict[str, Any]] = []
        for m in messages:
            role = "user" if m.role.value in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        payload: dict[str, Any] = {"contents": contents}
        if tool_schemas:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": s.name,
                            "description": s.description or "",
                            "parameters": s.input_schema or {},
                        }
                        for s in tool_schemas
                    ]
                }
            ]
        body = post_json(
            self.name,
            f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
            {"Content-Type": "application/json"},
            payload,
            timeout=self.timeout,
        )
        content = ""
        candidates = body.get("candidates") or []
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            for part in parts:
                if part.get("text"):
                    content += part["text"]
        return ModelResponse(content=content, tool_calls=())
