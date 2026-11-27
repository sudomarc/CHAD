"""Gateway registry: routes provider/model to the right adapter."""

from __future__ import annotations

from typing import Protocol

from .capabilities import Capabilities
from .errors import GatewayError
from .provider_contract import ModelResponse


class ProviderRegistration(Protocol):
    """An adapter registered for one provider."""

    name: str

    def capabilities_for(self, model: str) -> Capabilities:
        ...

    def request(
        self,
        model: str,
        messages: tuple,
        tool_schemas: tuple,
    ) -> ModelResponse:
        ...


class Gateway:
    def __init__(self) -> None:
        self._adapters: dict[str, ProviderRegistration] = {}

    def register(self, adapter: ProviderRegistration) -> None:
        self._adapters[adapter.name] = adapter

    def providers(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def has(self, provider: str) -> bool:
        return provider in self._adapters

    def capabilities(self, provider: str, model: str) -> Capabilities:
        if provider not in self._adapters:
            raise GatewayError(f"unknown provider: {provider}")
        return self._adapters[provider].capabilities_for(model)

    def request(
        self,
        provider: str,
        model: str,
        messages: tuple,
        tool_schemas: tuple = (),
    ) -> ModelResponse:
        if provider not in self._adapters:
            raise GatewayError(f"unknown provider: {provider}")
        return self._adapters[provider].request(model, messages, tool_schemas)
