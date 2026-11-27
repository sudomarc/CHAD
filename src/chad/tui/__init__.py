"""Terminal User Interface for CHAD.

The TUI owns presentation and user interaction only: it consumes runtime
events and submits user actions. It does not determine runtime policy or
provider behavior. See docs/architecture.md (dependency direction).
"""

from .app import ChadApp

__all__ = ["ChadApp"]
