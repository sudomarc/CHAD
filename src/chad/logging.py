"""Structured application logging for CHAD.

Uses the standard library only. The TUI and runtime consume log records
through the standard ``logging`` facility; this module owns the one-time
process-wide configuration so formatting stays consistent everywhere.
"""

from __future__ import annotations

import logging
import sys

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
DATEFMT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(verbose: bool = False) -> None:
    """Configure process-wide logging to stderr.

    Safe to call multiple times: ``basicConfig`` is a no-op once the root
    logger already has handlers.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        stream=sys.stderr,
        format=FORMAT,
        datefmt=DATEFMT,
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger for the calling module."""
    return logging.getLogger(f"chad.{name}")
