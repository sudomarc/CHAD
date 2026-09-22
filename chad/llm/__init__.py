"""LLM client boundaries, model gateway, and Lapis adapters."""

from chad.llm.client import GenerationError, LapisClient, LLMError, ModelInfo, ModelUnavailableError
from chad.llm.gateway import (
    AuthenticationError,
    CancellationError,
    ContextLimitExceededError,
    InvalidRequestError,
    MalformedResponseError,
    ModelCapabilities,
    ModelGateway,
    ModelResponse,
    PolicyDenialError,
    ProviderServerError,
    RateLimitError,
    TimeoutError,
    UsageInfo,
)

__all__ = [
    "AuthenticationError",
    "CancellationError",
    "ContextLimitExceededError",
    "GenerationError",
    "InvalidRequestError",
    "LLMError",
    "LapisClient",
    "MalformedResponseError",
    "ModelCapabilities",
    "ModelGateway",
    "ModelInfo",
    "ModelResponse",
    "ModelUnavailableError",
    "PolicyDenialError",
    "ProviderServerError",
    "RateLimitError",
    "TimeoutError",
    "UsageInfo",
]
