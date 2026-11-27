"""Tests for the Task state machine (M2)."""

from __future__ import annotations

import unittest

from chad.runtime.contracts import Message, Role, ToolResult
from chad.runtime.task import Task, TaskStatus, TransitionError


class TaskTests(unittest.TestCase):
    def make_task(self) -> Task:
        return Task(id="t-1", description="inspect the repo")

    def test_initial_status_pending(self):
        task = self.make_task()
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertFalse(task.is_terminal())

    def test_valid_transition_chain(self):
        task = self.make_task()
        task.transition(TaskStatus.RUNNING)
        self.assertEqual(task.status, TaskStatus.RUNNING)
        self.assertFalse(task.is_terminal())
        task.transition(TaskStatus.COMPLETED)
        self.assertEqual(task.status, TaskStatus.COMPLETED)
        self.assertTrue(task.is_terminal())

    def test_running_can_wait_or_fail_or_cancel(self):
        task = self.make_task()
        task.transition(TaskStatus.RUNNING)
        for target in (
            TaskStatus.WAITING_FOR_PERMISSION,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.COMPLETED,
        ):
            t = Task(id="x", description="d", status=TaskStatus.RUNNING)
            t.transition(target)
            self.assertEqual(t.status, target)

    def test_waiting_can_resume_or_terminate(self):
        task = Task(id="x", description="d", status=TaskStatus.WAITING_FOR_PERMISSION)
        task.transition(TaskStatus.RUNNING)
        self.assertEqual(task.status, TaskStatus.RUNNING)

    def test_invalid_transition_rejected(self):
        task = self.make_task()
        with self.assertRaises(TransitionError):
            task.transition(TaskStatus.COMPLETED)  # pending -> completed invalid
        # still pending after failed transition
        self.assertEqual(task.status, TaskStatus.PENDING)

    def test_terminal_states_reject_further_transition(self):
        task = self.make_task()
        task.transition(TaskStatus.RUNNING)
        task.transition(TaskStatus.COMPLETED)
        with self.assertRaises(TransitionError):
            task.transition(TaskStatus.RUNNING)

    def test_messages_and_results_accumulate(self):
        task = self.make_task()
        task.messages.append(Message(role=Role.USER, content="hi"))
        task.results.append(
            ToolResult(tool_call_id="tc-1", name="read", output="ok")
        )
        self.assertEqual(len(task.messages), 1)
        self.assertEqual(len(task.results), 1)
        self.assertTrue(task.results[0].is_error is False)

    def test_tool_result_error_flag(self):
        ok = ToolResult(tool_call_id="a", name="x", output="y")
        err = ToolResult(tool_call_id="b", name="x", error="boom")
        self.assertFalse(ok.is_error)
        self.assertTrue(err.is_error)


if __name__ == "__main__":
    unittest.main()
