"""Model gateway (M3).

Provider-neutral request/response contract. Adapters live under this package
and are independently testable with mocked HTTP responses. Live provider
tests require credentials and are opt-in (docs/model-providers.md).
"""

from .anthropic import AnthropicProvider
from .capabilities import Capabilities
from .errors import (
    AuthError,
    GatewayError,
    InvalidRequestError,
    ProviderError,
    RateLimitError,
    RequestTimeout,
    UnavailableModelError,
)
from .fake import FakeProvider
from .google import GoogleProvider
from .lapis import LapisLLMProvider
from .openai import OpenAIProvider
from .provider_contract import ModelResponse, Provider
from .registry import Gateway, ProviderRegistration

__all__ = [
    "AnthropicProvider",
    "AuthError",
    "Capabilities",
    "FakeProvider",
    "Gateway",
    "GatewayError",
    "GoogleProvider",
    "InvalidRequestError",
    "LapisLLMProvider",
    "ModelResponse",
    "OpenAIProvider",
    "Provider",
    "ProviderError",
    "ProviderRegistration",
    "RateLimitError",
    "RequestTimeout",
    "UnavailableModelError",
]
