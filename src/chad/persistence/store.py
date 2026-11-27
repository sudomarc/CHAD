"""SQLite session store."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chad.runtime.contracts import Message, Role, ToolCall, ToolResult
from chad.runtime.events import Event, EventType
from chad.runtime.task import Task, TaskStatus

_ISO = "%Y-%m-%dT%H:%M:%S.%f"


def _now_iso() -> str:
    return datetime.now(UTC).strftime(_ISO)


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, _ISO)


class SessionStore:
    """SQLite-backed persistence for sessions and task history."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        id           TEXT PRIMARY KEY,
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tasks (
        id            TEXT PRIMARY KEY,
        session_id    TEXT NOT NULL,
        description   TEXT NOT NULL,
        status        TEXT NOT NULL,
        provider      TEXT,
        model         TEXT,
        error         TEXT,
        created_at    TEXT NOT NULL,
        updated_at    TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );
    CREATE TABLE IF NOT EXISTS events (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id   TEXT NOT NULL,
        type      TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        payload   TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id      TEXT NOT NULL,
        role         TEXT NOT NULL,
        content      TEXT NOT NULL,
        tool_call_id TEXT,
        message_id   TEXT,
        created_at   TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );
    CREATE TABLE IF NOT EXISTS tool_results (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id      TEXT NOT NULL,
        tool_call_id TEXT NOT NULL,
        name         TEXT NOT NULL,
        output       TEXT,
        error        TEXT,
        created_at   TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    );
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    # ---------------------------------------------------------------- sessions

    def create_session(self) -> str:
        import uuid

        session_id = f"sess-{uuid.uuid4().hex[:12]}"
        now = _now_iso()
        self._conn.execute(
            "INSERT INTO sessions (id, created_at, updated_at) VALUES (?, ?, ?)",
            (session_id, now, now),
        )
        self._conn.commit()
        return session_id

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT id, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        ).fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "updated_at": r["updated_at"]} for r in rows]

    # ---------------------------------------------------------------- tasks

    def save_task(self, task: Task, session_id: str, provider: str | None = None, model: str | None = None) -> None:
        now = _now_iso()
        self._conn.execute(
            """
            INSERT INTO tasks (id, session_id, description, status, provider, model, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                session_id=excluded.session_id,
                description=excluded.description,
                status=excluded.status,
                provider=excluded.provider,
                model=excluded.model,
                error=excluded.error,
                updated_at=excluded.updated_at
            """,
            (
                task.id,
                session_id,
                task.description,
                task.status.value,
                provider,
                model,
                task.error,
                task.created_at.strftime(_ISO),
                now,
            ),
        )
        self._conn.commit()

    def get_task(self, task_id: str) -> Task | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        task = Task(
            id=row["id"],
            description=row["description"],
            status=TaskStatus(row["status"]),
            error=row["error"],
            created_at=_parse_iso(row["created_at"]),
            updated_at=_parse_iso(row["updated_at"]),
        )
        task.messages = self._load_messages(task_id)
        task.results = self._load_results(task_id)
        return task

    # ---------------------------------------------------------------- events

    def append_event(self, task_id: str, event: Event) -> None:
        self._conn.execute(
            "INSERT INTO events (task_id, type, timestamp, payload) VALUES (?, ?, ?, ?)",
            (
                task_id,
                event.type.value,
                event.timestamp.strftime(_ISO),
                json.dumps(event.payload),
            ),
        )
        self._conn.commit()

    def get_events(self, task_id: str) -> list[Event]:
        rows = self._conn.execute(
            "SELECT * FROM events WHERE task_id = ? ORDER BY id ASC", (task_id,)
        ).fetchall()
        events: list[Event] = []
        for row in rows:
            events.append(
                Event(
                    type=EventType(row["type"]),
                    timestamp=_parse_iso(row["timestamp"]),
                    payload=json.loads(row["payload"]),
                )
            )
        return events

    # ---------------------------------------------------------------- messages

    def save_message(self, task_id: str, message: Message) -> None:
        self._conn.execute(
            """
            INSERT INTO messages (task_id, role, content, tool_call_id, message_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                message.role.value,
                message.content,
                message.tool_call_id,
                message.id,
                _now_iso(),
            ),
        )
        self._conn.commit()

    def _load_messages(self, task_id: str) -> list[Message]:
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE task_id = ? ORDER BY id ASC", (task_id,)
        ).fetchall()
        messages: list[Message] = []
        for row in rows:
            tool_calls: list[ToolCall] = []
            messages.append(
                Message(
                    role=Role(row["role"]),
                    content=row["content"],
                    tool_calls=tuple(tool_calls),
                    tool_call_id=row["tool_call_id"],
                    id=row["message_id"],
                )
            )
        return messages

    # ---------------------------------------------------------------- tool results

    def save_tool_result(self, task_id: str, result: ToolResult) -> None:
        self._conn.execute(
            """
            INSERT INTO tool_results (task_id, tool_call_id, name, output, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                result.tool_call_id,
                result.name,
                result.output,
                result.error,
                _now_iso(),
            ),
        )
        self._conn.commit()

    def _load_results(self, task_id: str) -> list[ToolResult]:
        rows = self._conn.execute(
            "SELECT * FROM tool_results WHERE task_id = ? ORDER BY id ASC", (task_id,)
        ).fetchall()
        results: list[ToolResult] = []
        for row in rows:
            results.append(
                ToolResult(
                    tool_call_id=row["tool_call_id"],
                    name=row["name"],
                    output=row["output"],
                    error=row["error"],
                    id=f"res-{row['id']}",
                )
            )
        return results

    # ---------------------------------------------------------------- lifecycle

    def close(self) -> None:
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
