from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
import time
from typing import TYPE_CHECKING

from chad.core.conversation import ChatRequest
from chad.llm.client import (
    LapisClient,
    LLMError,
    ModelInfo,
    ModelUnavailableError,
)

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    text_generation: bool = True
    streaming: bool = False
    vision: bool = False
    tool_calling: bool = False
    structured_output: bool = False
    embeddings: bool = False
    context_length: int | None = None


@dataclass(frozen=True, slots=True)
class UsageInfo:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ModelResponse:
    content: str
    model_id: str
    provider: str = "lapis"
    request_id: str | None = None
    finish_reason: str | None = None
    usage: UsageInfo | None = None
    latency_ms: float | None = None
    tool_calls: tuple[dict, ...] = field(default_factory=tuple)
    raw_response: dict | None = None


# Normalized error taxonomy
class AuthenticationError(LLMError):
    pass


class InvalidRequestError(LLMError):
    pass


class ContextLimitExceededError(LLMError):
    pass


class RateLimitError(LLMError):
    pass


class TimeoutError(LLMError):
    pass


class ProviderServerError(LLMError):
    pass


class MalformedResponseError(LLMError):
    pass


class CancellationError(LLMError):
    pass


class PolicyDenialError(LLMError):
    pass


class ModelGateway:
    """Provider-neutral model gateway for CHAD."""

    def __init__(self, default_client: LapisClient | None = None) -> None:
        self._providers: dict[str, LapisClient] = {}
        self._model_to_provider: dict[str, str] = {}
        self._default_provider: str | None = None

        if default_client is not None:
            model_info = default_client.current_model()
            provider_id = model_info.backend or "default"
            self.register_provider(provider_id, default_client, is_default=True)

    def register_provider(
        self,
        provider_id: str,
        client: LapisClient,
        is_default: bool = False,
    ) -> None:
        self._providers[provider_id] = client
        if is_default or self._default_provider is None:
            self._default_provider = provider_id

        for model in client.list_models():
            self._model_to_provider[model.id] = provider_id

    def list_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        for client in self._providers.values():
            models.extend(client.list_models())
        return models

    def get_model(self, model_id: str) -> ModelInfo:
        provider_id = self._model_to_provider.get(model_id)
        if provider_id is None:
            if self._default_provider is not None:
                client = self._providers[self._default_provider]
                return client.current_model()
            raise ModelUnavailableError(f"Model {model_id} is not available in Model Gateway.")
        client = self._providers[provider_id]
        for model in client.list_models():
            if model.id == model_id:
                return model
        return client.current_model()

    def capabilities(self, model_id: str) -> ModelCapabilities:
        model = self.get_model(model_id)
        if getattr(model, "capabilities", None) is not None:
            return model.capabilities  # type: ignore[return-value]
        return ModelCapabilities(
            text_generation=True,
            streaming=model.supports_streaming,
            context_length=model.context_length,
        )

    def _get_client_for_model(self, model_id: str | None) -> tuple[LapisClient, str]:
        if model_id is not None and model_id in self._model_to_provider:
            provider_id = self._model_to_provider[model_id]
            return self._providers[provider_id], model_id
        if self._default_provider is not None:
            client = self._providers[self._default_provider]
            target_model = model_id or client.current_model().id
            return client, target_model
        raise ModelUnavailableError("No model provider is registered with Model Gateway.")

    def generate(
        self,
        request: ChatRequest,
        model_id: str | None = None,
        fallback_models: tuple[str, ...] = (),
    ) -> ModelResponse:
        target_models = (model_id or request.model,) + fallback_models
        last_error: Exception | None = None

        for candidate_model in target_models:
            try:
                client, resolved_model = self._get_client_for_model(candidate_model)
                start_time = time.perf_counter()

                if hasattr(client, "generate_response"):
                    response = client.generate_response(request)
                    if not isinstance(response, ModelResponse):
                        latency_ms = (time.perf_counter() - start_time) * 1000
                        response = ModelResponse(
                            content=str(response),
                            model_id=resolved_model,
                            provider=client.current_model().backend,
                            latency_ms=latency_ms,
                        )
                    return response

                raw_text = client.generate(request)
                latency_ms = (time.perf_counter() - start_time) * 1000
                return ModelResponse(
                    content=raw_text,
                    model_id=resolved_model,
                    provider=client.current_model().backend,
                    latency_ms=latency_ms,
                )
            except (ModelUnavailableError, ProviderServerError, TimeoutError) as exc:
                last_error = exc
                continue
            except LLMError:
                raise

        if last_error is not None:
            raise last_error
        raise ModelUnavailableError("No model available to service generation request.")

    def stream(self, request: ChatRequest, model_id: str | None = None) -> Iterator[str]:
        client, _ = self._get_client_for_model(model_id or request.model)
        yield from client.stream_generate(request)
