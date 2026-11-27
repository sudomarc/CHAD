"""Tests for the bounded agent loop (M2)."""

from __future__ import annotations

import unittest
from typing import Any

from chad.runtime.contracts import Role, ToolCall, ToolResult
from chad.runtime.loop import (
    AgentLoop,
    DefaultDenyPolicy,
    LoopLimits,
    LoopOutcome,
)
from chad.runtime.provider import ModelResponse
from chad.runtime.task import Task, TaskStatus
from chad.runtime.tools import Tool, ToolRegistry


class AutoApprovePolicy:
    def allows(self, tool: Tool, arguments: dict) -> bool:
        return True


class FakeTool:
    def __init__(
        self,
        name: str,
        output: str | None = None,
        error: str | None = None,
    ):
        self.name = name
        self.description = "fake"
        self.input_schema: dict[str, Any] = {}
        self.output = output
        self.error = error
        self.calls: list[dict] = []

    def call(self, arguments: dict) -> ToolResult:
        self.calls.append(dict(arguments))
        return ToolResult(
            tool_call_id="tc", name=self.name, output=self.output, error=self.error
        )


class FakeProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list = []

    def request(self, messages, tool_schemas) -> ModelResponse:
        self.calls.append((tuple(messages), tuple(tool_schemas)))
        if self.responses:
            return self.responses.pop(0)
        return ModelResponse(content="done")


def make_loop(
    responses,
    policy=None,
    limits=None,
    tool=None,
) -> AgentLoop:
    task = Task(id="t-1", description="do the thing")
    registry = ToolRegistry()
    if tool is not None:
        registry.register(tool)
    provider = FakeProvider(responses)
    return AgentLoop(
        task=task,
        provider=provider,
        registry=registry,
        policy=policy or AutoApprovePolicy(),
        limits=limits or LoopLimits(),
    )


class LoopTests(unittest.TestCase):
    def test_completes_without_tool_calls(self):
        loop = make_loop([ModelResponse(content="hello world")])
        report = loop.run()
        self.assertEqual(report.status, TaskStatus.COMPLETED)
        self.assertEqual(report.outcome, LoopOutcome.COMPLETED)
        self.assertEqual(loop.task.status, TaskStatus.COMPLETED)
        self.assertEqual(report.iterations, 1)
        self.assertEqual(report.requests, 1)
        self.assertEqual(report.tool_calls, 0)
        self.assertFalse(report.error)
        last = loop.task.messages[-1]
        self.assertEqual(last.role, Role.ASSISTANT)
        self.assertEqual(last.content, "hello world")
        self.assertEqual(len(loop.provider.calls), 1)

    def test_executes_tool_then_completes(self):
        tool = FakeTool("read", output="file contents")
        responses = [
            ModelResponse(
                content="thinking",
                tool_calls=(ToolCall(id="tc-1", name="read"),),
            ),
            ModelResponse(content="done"),
        ]
        loop = make_loop(responses, tool=tool)
        report = loop.run()
        self.assertEqual(report.status, TaskStatus.COMPLETED)
        self.assertEqual(report.outcome, LoopOutcome.COMPLETED)
        self.assertEqual(report.tool_calls, 1)
        self.assertEqual(len(tool.calls), 1)
        self.assertEqual(len(loop.task.results), 1)
        self.assertEqual(loop.task.results[0].output, "file contents")
        self.assertFalse(loop.task.results[0].is_error)
        self.assertEqual(report.actions[0].kind, "model_request")
        self.assertEqual(report.actions[1].kind, "tool_call")
        self.assertTrue(report.actions[1].ok)

    def test_unknown_tool_yields_error_result_then_continues(self):
        responses = [
            ModelResponse(
                content="try",
                tool_calls=(ToolCall(id="tc-1", name="no_such_tool"),),
            ),
            ModelResponse(content="finished"),
        ]
        loop = make_loop(responses)
        report = loop.run()
        self.assertEqual(report.status, TaskStatus.COMPLETED)
        self.assertEqual(len(loop.task.results), 1)
        self.assertTrue(loop.task.results[0].is_error)
        self.assertIn("unknown tool", loop.task.results[0].error)
        self.assertFalse(report.error)

    def test_iteration_limit_stops_explicitly(self):
        responses = [
            ModelResponse(
                content="keep going",
                tool_calls=(ToolCall(id="tc", name="read"),),
            )
        ] * 5
        loop = make_loop(responses, limits=LoopLimits(max_iterations=1))
        report = loop.run()
        self.assertEqual(report.outcome, LoopOutcome.STOPPED)
        self.assertEqual(report.iterations, 1)
        self.assertIn("iteration limit", report.error)

    def test_deny_policy_waits_for_permission(self):
        tool = FakeTool("read", output="x")
        responses = [
            ModelResponse(
                content="use tool",
                tool_calls=(ToolCall(id="tc-1", name="read"),),
            )
        ]
        loop = make_loop(responses, policy=DefaultDenyPolicy(), tool=tool)
        report = loop.run()
        self.assertEqual(report.outcome, LoopOutcome.WAITING_FOR_PERMISSION)
        self.assertEqual(loop.task.status, TaskStatus.WAITING_FOR_PERMISSION)
        self.assertEqual(len(tool.calls), 0)

    def test_cancel(self):
        loop = make_loop([ModelResponse(content="x")] * 3)
        loop.cancel()
        report = loop.run()
        self.assertEqual(report.outcome, LoopOutcome.CANCELLED)
        self.assertEqual(loop.task.status, TaskStatus.CANCELLED)

    def test_tool_exception_becomes_error_result(self):
        def boom(arguments):
            raise RuntimeError("kaboom")

        tool = FakeTool("read")
        tool.call = boom  # type: ignore[method-assign]
        responses = [
            ModelResponse(
                content="go",
                tool_calls=(ToolCall(id="tc-1", name="read"),),
            ),
            ModelResponse(content="done"),
        ]
        loop = make_loop(responses, tool=tool)
        loop.run()
        self.assertEqual(loop.task.status, TaskStatus.COMPLETED)
        self.assertTrue(loop.task.results[0].is_error)
        self.assertIn("kaboom", loop.task.results[0].error)


if __name__ == "__main__":
    unittest.main()
