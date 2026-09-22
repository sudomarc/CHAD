from __future__ import annotations

import time

import httpx

from chad.core.conversation import ChatRequest
from chad.llm.client import GenerationError, LapisClient, ModelInfo, ModelUnavailableError
from chad.llm.gateway import (
    AuthenticationError,
    InvalidRequestError,
    MalformedResponseError,
    ModelCapabilities,
    ModelResponse,
    ProviderServerError,
    RateLimitError,
    TimeoutError,
    UsageInfo,
)


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

            context_length = (
                int(selected["context_length"])
                if isinstance(selected.get("context_length"), int)
                else None
            )
            supports_streaming = bool(selected.get("supports_streaming", False))

            capabilities = ModelCapabilities(
                text_generation=True,
                streaming=supports_streaming,
                context_length=context_length,
            )

            return ModelInfo(
                id=str(selected["id"]),
                display_name=str(selected.get("id", "Lapis")),
                context_length=context_length,
                backend="lapis",
                supports_streaming=supports_streaming,
                supports_cancellation=bool(selected.get("supports_cancellation", False)),
                capabilities=capabilities,
            )
        except ModelUnavailableError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ModelUnavailableError(
                f"Unable to connect to the Lapis API at {self._base_url.rstrip('/')}"
            ) from exc

    def generate_response(self, request: ChatRequest) -> ModelResponse:
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

        start_time = time.perf_counter()
        try:
            response = self._client.post("v1/chat/completions", json=payload)
            response.raise_for_status()
            latency_ms = (time.perf_counter() - start_time) * 1000
            data = response.json()

            if not isinstance(data, dict) or "choices" not in data:
                raise MalformedResponseError("Lapis API response missing 'choices' field.")

            choices = data.get("choices", [])
            if not choices or not isinstance(choices[0], dict):
                raise MalformedResponseError("Lapis API response has empty 'choices'.")

            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if not isinstance(content, str):
                raise MalformedResponseError("Lapis API returned non-text content.")

            finish_reason = choice.get("finish_reason")
            request_id = data.get("id")

            usage_data = data.get("usage")
            usage: UsageInfo | None = None
            if isinstance(usage_data, dict):
                usage = UsageInfo(
                    prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
                    completion_tokens=int(usage_data.get("completion_tokens", 0)),
                    total_tokens=int(usage_data.get("total_tokens", 0)),
                )

            return ModelResponse(
                content=content.strip(),
                model_id=str(data.get("model", request.model or self._model.id)),
                provider="lapis",
                request_id=str(request_id) if request_id else None,
                finish_reason=str(finish_reason) if finish_reason else None,
                usage=usage,
                latency_ms=latency_ms,
                raw_response=data,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("Lapis API request timed out.") from exc
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            detail = exc.response.text.strip() or exc.response.reason_phrase
            if status in (401, 403):
                raise AuthenticationError(f"Lapis API authentication failed: {detail}") from exc
            if status == 429:
                raise RateLimitError(f"Lapis API rate limit exceeded: {detail}") from exc
            if status in (400, 422):
                raise InvalidRequestError(f"Lapis API invalid request: {detail}") from exc
            if status >= 500:
                raise ProviderServerError(f"Lapis API server error ({status}): {detail}") from exc
            raise GenerationError(f"Lapis API generation failed: {detail}") from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            if isinstance(exc, (MalformedResponseError, AuthenticationError, RateLimitError)):
                raise
            raise GenerationError("Lapis API returned an invalid generation response.") from exc

    def generate(self, request: ChatRequest) -> str:
        return self.generate_response(request).content

    def current_model(self) -> ModelInfo:
        return self._model

    def close(self) -> None:
        self._client.close()
