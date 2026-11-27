"""Normalized provider errors (M3).

Adapters translate vendor errors into these; the runtime and TUI never see
provider-specific error types (docs/model-providers.md).
"""

from __future__ import annotations


class GatewayError(Exception):
    """Base class for gateway errors."""


class AuthError(GatewayError):
    """Authentication failed (401)."""


class RateLimitError(GatewayError):
    """Rate limit exceeded (429); retry after backoff."""


class RequestTimeout(GatewayError):
    """Request timed out."""


class InvalidRequestError(GatewayError):
    """Malformed request (400); do not retry without changes."""


class UnavailableModelError(GatewayError):
    """Requested model is unavailable for this provider."""


class ProviderError(GatewayError):
    """Provider server error (5xx); transient, retry with backoff."""


def error_for_status(status: int, provider: str, detail: str = "") -> GatewayError:
    """Map an HTTP status code to the matching normalized error."""
    if status == 401:
        return AuthError(f"{provider}: authentication failed{_d(detail)}")
    if status == 404:
        return UnavailableModelError(
            f"{provider}: requested model unavailable{_d(detail)}"
        )
    if status == 429:
        return RateLimitError(f"{provider}: rate limited{_d(detail)}")
    if status == 408:
        return RequestTimeout(f"{provider}: request timed out{_d(detail)}")
    if 400 <= status < 500:
        return InvalidRequestError(
            f"{provider}: invalid request{_d(detail)}"
        )
    if 500 <= status < 600:
        return ProviderError(f"{provider}: server error{_d(detail)}")
    return GatewayError(f"{provider}: HTTP {status}{_d(detail)}")


def _d(detail: str) -> str:
    return f": {detail}" if detail else ""
