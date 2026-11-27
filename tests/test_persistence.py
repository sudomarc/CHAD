"""Tests for SQLite session persistence (issue #76)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chad.persistence.store import SessionStore
from chad.runtime.contracts import Message, Role, ToolResult
from chad.runtime.events import Event, EventType
from chad.runtime.task import Task, TaskStatus


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SessionStore(Path(self.tmp.name) / "sessions.sqlite")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_create_and_list_sessions(self):
        sid1 = self.store.create_session()
        sid2 = self.store.create_session()
        sessions = self.store.list_sessions()
        ids = {s["id"] for s in sessions}
        self.assertIn(sid1, ids)
        self.assertIn(sid2, ids)
        self.assertEqual(len(sessions), 2)
        # most recent first
        self.assertEqual(sessions[0]["id"], sid2)

    def test_save_and_get_task_roundtrip(self):
        session_id = self.store.create_session()
        task = Task(id="t-1", description="inspect the repo", status=TaskStatus.RUNNING)
        self.store.save_task(task, session_id, provider="prov", model="m")
        msg = Message(role=Role.USER, content="hello")
        self.store.save_message(task.id, msg)
        res = ToolResult(tool_call_id="tc-1", name="read", output="ok")
        self.store.save_tool_result(task.id, res)

        loaded = self.store.get_task("t-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.description, "inspect the repo")
        self.assertEqual(loaded.status, TaskStatus.RUNNING)
        self.assertEqual(len(loaded.messages), 1)
        self.assertEqual(loaded.messages[0].content, "hello")
        self.assertEqual(loaded.messages[0].role, Role.USER)
        self.assertEqual(len(loaded.results), 1)
        self.assertEqual(loaded.results[0].output, "ok")
        self.assertFalse(loaded.results[0].is_error)

    def test_get_missing_task(self):
        self.assertIsNone(self.store.get_task("nope"))

    def test_task_status_persists(self):
        session_id = self.store.create_session()
        task = Task(id="t-2", description="d", status=TaskStatus.PENDING)
        task.transition(TaskStatus.RUNNING)
        self.store.save_task(task, session_id)
        task.transition(TaskStatus.COMPLETED)
        self.store.save_task(task, session_id)
        loaded = self.store.get_task("t-2")
        self.assertEqual(loaded.status, TaskStatus.COMPLETED)
        self.assertTrue(loaded.is_terminal())

    def test_events_append_and_read(self):
        session_id = self.store.create_session()
        task = Task(id="t-3", description="d")
        self.store.save_task(task, session_id)
        self.store.append_event(
            task.id, Event(EventType.TOOL_COMPLETED, payload={"ok": True})
        )
        self.store.append_event(task.id, Event(EventType.ITERATION_COMPLETED))
        events = self.store.get_events(task.id)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].type, EventType.TOOL_COMPLETED)
        self.assertTrue(events[0].payload["ok"])
        self.assertEqual(events[1].type, EventType.ITERATION_COMPLETED)

    def test_save_message(self):
        session_id = self.store.create_session()
        task = Task(id="t-4", description="d")
        self.store.save_task(task, session_id)
        msg = Message(role=Role.ASSISTANT, content="final answer")
        self.store.save_message(task.id, msg)
        loaded = self.store.get_task("t-4")
        self.assertEqual(len(loaded.messages), 1)
        self.assertEqual(loaded.messages[0].content, "final answer")
        self.assertEqual(loaded.messages[0].role, Role.ASSISTANT)

    def test_save_tool_result(self):
        session_id = self.store.create_session()
        task = Task(id="t-5", description="d")
        self.store.save_task(task, session_id)
        res = ToolResult(tool_call_id="tc", name="shell", output="hi", error=None)
        self.store.save_tool_result(task.id, res)
        loaded = self.store.get_task("t-5")
        self.assertEqual(len(loaded.results), 1)
        self.assertEqual(loaded.results[0].name, "shell")
        self.assertEqual(loaded.results[0].output, "hi")


if __name__ == "__main__":
    unittest.main()
