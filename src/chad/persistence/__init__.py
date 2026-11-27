"""Local-first session persistence (M5, issue #76).

SQLite store for sessions, tasks, events, messages and tool results.
Resume restores enough state to continue safely; recorded tool executions
are never replayed blindly (docs/context-and-memory.md: sessions).
"""

from .store import SessionStore

__all__ = ["SessionStore"]
