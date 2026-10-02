from __future__ import annotations

import json
import time
from collections.abc import Iterator

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
from chad.llm.vision import VisionPayloadConverter


class ExternalProviderClient(LapisClient):
    """Adapter for external OpenAI-compatible inference APIs (e.g. OpenAI, Groq, Mistral, OpenRouter)."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: str | None = None,
        model: str = "gpt-4o",
        provider_name: str = "external",
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        capabilities: ModelCapabilities | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/"
        self._model_id = model
        self._provider_name = provider_name
        self._timeout = timeout

        req_headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "CHAD-AgentRuntime/1.0",
        }
        if headers:
            req_headers.update(headers)
        if api_key and "Authorization" not in req_headers:
            req_headers["Authorization"] = f"Bearer {api_key}"

        self._client = httpx.Client(
            base_url=self._base_url,
            headers=req_headers,
            timeout=self._timeout,
        )

        self._capabilities = capabilities or ModelCapabilities(
            text_generation=True,
            streaming=True,
            vision=True,
            tool_calling=True,
            structured_output=True,
            context_length=128000,
        )

        self._vision_converter = VisionPayloadConverter()
        self._model = ModelInfo(
            id=self._model_id,
            display_name=f"{self._provider_name.capitalize()} — {self._model_id}",
            context_length=self._capabilities.context_length,
            backend=self._provider_name,
            supports_streaming=self._capabilities.streaming,
            capabilities=self._capabilities,
        )

    def current_model(self) -> ModelInfo:
        return self._model

    def list_models(self) -> list[ModelInfo]:
        try:
            response = self._client.get("models")
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data")
            if isinstance(data, list) and data:
                models: list[ModelInfo] = []
                for item in data:
                    if isinstance(item, dict) and item.get("id"):
                        m_id = str(item["id"])
                        models.append(
                            ModelInfo(
                                id=m_id,
                                display_name=f"{self._provider_name.capitalize()} — {m_id}",
                                context_length=self._capabilities.context_length,
                                backend=self._provider_name,
                                supports_streaming=self._capabilities.streaming,
                                capabilities=self._capabilities,
                            )
                        )
                if models:
                    return models
        except (httpx.HTTPError, ValueError, TypeError):
            pass
        return [self._model]

    def _build_payload(self, request: ChatRequest, stream: bool = False) -> dict[str, object]:
        messages_payload = [
            self._vision_converter.format_message(msg) for msg in request.messages
        ]

        payload: dict[str, object] = {
            "model": request.model or self._model_id,
            "messages": messages_payload,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_new_tokens,
            "stream": stream,
        }
        return payload

    def _map_http_error(self, exc: httpx.HTTPStatusError) -> LLMError:
        status = exc.response.status_code
        detail = exc.response.text.strip() or exc.response.reason_phrase
        if status in (401, 403):
            return AuthenticationError(
                f"{self._provider_name.capitalize()} API authentication failed: {detail}"
            )
        if status == 429:
            return RateLimitError(
                f"{self._provider_name.capitalize()} API rate limit exceeded: {detail}"
            )
        if status in (400, 422):
            return InvalidRequestError(
                f"{self._provider_name.capitalize()} API invalid request: {detail}"
            )
        if status >= 500:
            return ProviderServerError(
                f"{self._provider_name.capitalize()} API server error ({status}): {detail}"
            )
        return GenerationError(
            f"{self._provider_name.capitalize()} API request failed: {detail}"
        )

    def generate_response(self, request: ChatRequest) -> ModelResponse:
        request.validate()
        payload = self._build_payload(request, stream=False)

        start_time = time.perf_counter()
        try:
            response = self._client.post("chat/completions", json=payload)
            response.raise_for_status()
            latency_ms = (time.perf_counter() - start_time) * 1000
            data = response.json()

            if not isinstance(data, dict) or "choices" not in data:
                raise MalformedResponseError(
                    f"{self._provider_name.capitalize()} API response missing 'choices' field."
                )

            choices = data.get("choices", [])
            if not choices or not isinstance(choices[0], dict):
                raise MalformedResponseError(
                    f"{self._provider_name.capitalize()} API response has empty 'choices'."
                )

            choice = choices[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if not isinstance(content, str):
                raise MalformedResponseError(
                    f"{self._provider_name.capitalize()} API returned non-text content."
                )

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
                model_id=str(data.get("model", request.model or self._model_id)),
                provider=self._provider_name,
                request_id=str(request_id) if request_id else None,
                finish_reason=str(finish_reason) if finish_reason else None,
                usage=usage,
                latency_ms=latency_ms,
                raw_response=data,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"{self._provider_name.capitalize()} API request timed out."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            if isinstance(exc, (MalformedResponseError, AuthenticationError, RateLimitError)):
                raise
            raise GenerationError(
                f"{self._provider_name.capitalize()} API returned an invalid generation response."
            ) from exc

    def generate(self, request: ChatRequest) -> str:
        return self.generate_response(request).content

    def stream_generate(self, request: ChatRequest) -> Iterator[str]:
        request.validate()
        payload = self._build_payload(request, stream=True)

        try:
            with self._client.stream("POST", "chat/completions", json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if choices and isinstance(choices[0], dict):
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"{self._provider_name.capitalize()} API streaming timed out."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise self._map_http_error(exc) from exc
        except httpx.HTTPError as exc:
            raise GenerationError(
                f"{self._provider_name.capitalize()} API streaming failed."
            ) from exc

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ExternalProviderClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
