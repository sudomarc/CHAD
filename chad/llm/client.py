from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING

from chad.core.conversation import ChatRequest

if TYPE_CHECKING:
    from chad.llm.cancellation import CancellationToken
    from chad.llm.gateway import ModelCapabilities, ModelResponse


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    display_name: str
    context_length: int | None = None
    backend: str = "lapis"
    supports_streaming: bool = False
    supports_cancellation: bool = False
    capabilities: ModelCapabilities | None = None


class LLMError(RuntimeError):
    """Base class for user-facing model/backend failures."""


class ModelUnavailableError(LLMError):
    pass


class GenerationError(LLMError):
    pass


class LapisClient(ABC):
    """Small application boundary around Lapis inference capabilities."""

    @abstractmethod
    def generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> str:
        raise NotImplementedError

    def generate_response(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> ModelResponse:
        import inspect

        from chad.llm.gateway import ModelResponse

        if cancellation_token is not None:
            cancellation_token.throw_if_cancelled()
        sig = inspect.signature(self.generate)
        if "cancellation_token" in sig.parameters:
            raw_text = self.generate(request, cancellation_token=cancellation_token)
        else:
            raw_text = self.generate(request)
        model = self.current_model()
        return ModelResponse(
            content=raw_text,
            model_id=model.id,
            provider=model.backend,
        )

    def stream_generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> Iterator[str]:
        raise NotImplementedError("streaming is not supported by this backend")

    async def astream_generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncIterator[str]:
        raise NotImplementedError("streaming is not supported by this backend")
        yield ""

    @abstractmethod
    def current_model(self) -> ModelInfo:
        raise NotImplementedError

    def list_models(self) -> list[ModelInfo]:
        return [self.current_model()]

    @property
    def supports_streaming(self) -> bool:
        return self.__class__.stream_generate is not LapisClient.stream_generate
