from __future__ import annotations

import httpx

from chad.core.conversation import ChatRequest
from chad.llm.client import GenerationError, LapisClient, ModelInfo, ModelUnavailableError


class HttpLapisClient(LapisClient):
    """CHAD client for the public LapisLLM HTTP inference API."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", model: str | None = None) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._client = httpx.Client(base_url=self._base_url, timeout=None)
        self._model_id = model
        self._model = self._discover_model()

    def _discover_model(self) -> ModelInfo:
        try:
            response = self._client.get("v1/models")
            response.raise_for_status()
            payload = response.json()
            models = payload.get("data")
            if not isinstance(models, list) or not models:
                raise ModelUnavailableError("Lapis API returned no available models.")
            selected = next(
                (item for item in models if item.get("id") == self._model_id),
                models[0] if self._model_id is None else None,
            )
            if not isinstance(selected, dict) or not selected.get("id"):
                raise ModelUnavailableError(f"Lapis model not found: {self._model_id}")
            return ModelInfo(
                id=str(selected["id"]),
                display_name=str(selected.get("id", "Lapis")),
                context_length=selected.get("context_length"),
            )
        except ModelUnavailableError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ModelUnavailableError(
                f"Unable to connect to the Lapis API at {self._base_url.rstrip('/')}"
            ) from exc

    def generate(self, request: ChatRequest) -> str:
        request.validate()
        payload = {
            "model": request.model or self._model.id,
            "messages": [
                {"role": message.role.value, "content": message.content}
                for message in request.messages
            ],
            "temperature": request.temperature,
            "top_k": request.top_k,
            "top_p": request.top_p,
            "max_tokens": request.max_new_tokens,
        }
        try:
            response = self._client.post("v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Lapis API returned non-text content")
            return content.strip()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or exc.response.reason_phrase
            raise GenerationError(f"Lapis API generation failed: {detail}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise GenerationError("Lapis API returned an invalid generation response.") from exc

    def current_model(self) -> ModelInfo:
        return self._model

    def close(self) -> None:
        self._client.close()
