"""Small HTTP client for provider adapters (stdlib only).

Adapters must not add runtime dependencies; urllib is sufficient for the
JSON-over-HTTP provider shape used here (docs/testing.md: no mandatory
external dependencies).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .errors import GatewayError, error_for_status


class HttpError(GatewayError):
    """Unclassified HTTP failure (connection problems, timeouts)."""


def post_json(
    provider_name: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST JSON and return the decoded body.

    Translates HTTP errors into normalized gateway errors.
    """
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")) if body else {}
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except OSError:
            pass
        raise error_for_status(exc.code, provider_name, detail) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise HttpError(f"{provider_name}: request failed: {exc}") from exc
