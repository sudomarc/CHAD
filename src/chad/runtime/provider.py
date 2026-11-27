"""Lazy re-exports of the provider-neutral model contract owned by the gateway.

The contract itself lives in ``chad.gateway.provider_contract``; the runtime
consumes it (docs/architecture.md: dependency direction). Re-export is lazy
so importing ``chad.runtime`` never pulls in the gateway (and vice versa),
which avoids an import cycle.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name in ("ModelResponse", "Provider"):
        from chad.gateway.provider_contract import ModelResponse, Provider

        return {"ModelResponse": ModelResponse, "Provider": Provider}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
