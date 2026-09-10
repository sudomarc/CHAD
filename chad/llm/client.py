from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass

from chad.core.conversation import ChatRequest


@dataclass(frozen=True, slots=True)
class ModelInfo:
    id: str
    display_name: str
    context_length: int | None = None
    backend: str = "lapis"


class LLMError(RuntimeError):
    """Base class for user-facing model/backend failures."""


class ModelUnavailableError(LLMError):
    pass


class GenerationError(LLMError):
    pass


class LapisClient(ABC):
    """Small application boundary around Lapis inference capabilities."""

    @abstractmethod
    def generate(self, request: ChatRequest) -> str:
        raise NotImplementedError

    def stream_generate(self, request: ChatRequest) -> Iterator[str]:
        raise NotImplementedError("streaming is not supported by this backend")

    async def astream_generate(self, request: ChatRequest) -> AsyncIterator[str]:
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
