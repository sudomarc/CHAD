"""Bounded observe/decide/act agent loop (M2).

The loop drives a task to completion, cancellation, or an explicit stopped
state when a budget is exhausted. It never infers success from a model's
claim; the final report distinguishes actions performed, files changed,
checks actually run, results, and unverified items
(docs/agent-runtime.md: core cycle, required limits, final response contract).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .contracts import Message, Role, ToolResult
from .events import Event, EventType
from .task import Task, TaskStatus, TransitionError
from .tools import Tool, ToolError, ToolRegistry

if TYPE_CHECKING:
    from .provider import Provider


class LoopOutcome(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    STOPPED = "stopped"


@dataclass(frozen=True)
class LoopLimits:
    max_iterations: int = 10
    max_requests: int = 20
    max_tool_calls: int = 40
    max_wall_clock_seconds: int = 600
    max_output_bytes: int = 1_000_000


@dataclass
class ActionPerformed:
    kind: str  # "model_request" | "tool_call"
    target: str
    ok: bool
    detail: str = ""


@dataclass
class TaskReport:
    task_id: str
    status: TaskStatus
    outcome: LoopOutcome
    iterations: int = 0
    requests: int = 0
    tool_calls: int = 0
    wall_clock_seconds: float = 0.0
    actions: list[ActionPerformed] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    results: list[ToolResult] = field(default_factory=list)
    error: str | None = None


@runtime_checkable
class Policy(Protocol):
    def allows(self, tool: Tool, arguments: dict[str, Any]) -> bool:
        """Return True if the tool may execute with these arguments now."""


class DefaultDenyPolicy:
    """Safe default: nothing is executable until an explicit policy allows it."""

    def allows(self, tool: Tool, arguments: dict[str, Any]) -> bool:
        return False


class AgentLoop:
    def __init__(
        self,
        task: Task,
        provider: Provider,
        registry: ToolRegistry,
        model: str | None = None,
        policy: Policy | None = None,
        on_event: Callable[[Event], None] | None = None,
        limits: LoopLimits | None = None,
    ) -> None:
        self.task = task
        self.provider = provider
        self.registry = registry
        self.model = model
        self.policy = policy or DefaultDenyPolicy()
        self._on_event = on_event
        self.limits = limits or LoopLimits()
        self._cancelled = False
        self._start: float | None = None
        self.iterations = 0
        self.requests = 0
        self.tool_calls = 0
        self._actions: list[ActionPerformed] = []
        self._files_changed: list[str] = []
        self._checks_run: list[str] = []

    # ------------------------------------------------------------------ events

    def _emit(self, type: EventType, payload: dict[str, Any] | None = None) -> None:
        if self._on_event is not None:
            self._on_event(Event(type=type, payload=payload or {}))

    # ------------------------------------------------------------------ control

    def cancel(self) -> None:
        self._cancelled = True

    def _within_limits(self) -> str | None:
        if self._cancelled:
            return "cancelled"
        if self._start is not None:
            elapsed = time.monotonic() - self._start
            if elapsed >= self.limits.max_wall_clock_seconds:
                return f"wall-clock limit ({self.limits.max_wall_clock_seconds}s) exhausted"
        if self.iterations >= self.limits.max_iterations:
            return f"iteration limit ({self.limits.max_iterations}) exhausted"
        if self.requests >= self.limits.max_requests:
            return f"model-request limit ({self.limits.max_requests}) exhausted"
        if self.tool_calls >= self.limits.max_tool_calls:
            return f"tool-call limit ({self.limits.max_tool_calls}) exhausted"
        return None

    # ------------------------------------------------------------------ report

    def _report(self, outcome: LoopOutcome, error: str | None = None) -> TaskReport:
        elapsed = (
            time.monotonic() - self._start if self._start is not None else 0.0
        )
        return TaskReport(
            task_id=self.task.id,
            status=self.task.status,
            outcome=outcome,
            iterations=self.iterations,
            requests=self.requests,
            tool_calls=self.tool_calls,
            wall_clock_seconds=elapsed,
            actions=list(self._actions),
            files_changed=list(self._files_changed),
            checks_run=list(self._checks_run),
            unverified=[
                "file-change and check instrumentation deferred to M4/M5 tools"
            ],
            results=list(self.task.results),
            error=error,
        )

    # ------------------------------------------------------------------ cycle

    def run(self) -> TaskReport:
        if self.task.is_terminal():
            return self._report(LoopOutcome.FAILED, error="task is already terminal")

        self._start = time.monotonic()
        self.task.transition(TaskStatus.RUNNING)
        self._emit(EventType.USER_MESSAGE_ACCEPTED, {"task": self.task.description})

        # Seed the conversation with a system message describing the task.
        self.task.messages.append(
            Message(
                role=Role.SYSTEM,
                content=(
                    "You are CHAD, a local-first coding agent. Solve the user's "
                    "task using the available tools, then state your final answer. "
                    f"Task: {self.task.description}"
                ),
            )
        )

        while True:
            stop = self._within_limits()
            if stop is not None:
                if self._cancelled:
                    self.task.transition(TaskStatus.CANCELLED)
                    return self._report(LoopOutcome.CANCELLED, error="cancelled")
                try:
                    self.task.transition(TaskStatus.FAILED)
                except TransitionError:
                    pass
                return self._report(LoopOutcome.STOPPED, error=stop)

            self.iterations += 1

            # --- OBSERVE: build the provider request from context + history
            messages = tuple(self.task.messages)

            # --- DECIDE: ask the provider
            self.requests += 1
            if self.requests > self.limits.max_requests:
                self.task.transition(TaskStatus.FAILED)
                return self._report(
                    LoopOutcome.STOPPED, error="model-request limit exhausted"
                )
            self._emit(EventType.MODEL_REQUEST_STARTED, {"request": self.requests})
            try:
                response = self.provider.request(
                    self.model or "unknown", messages, self.registry.schemas()
                )
            except Exception as exc:  # noqa: BLE001 - surface provider failure
                self._emit(EventType.MODEL_RESPONSE_RECEIVED, {"error": str(exc)})
                try:
                    self.task.transition(TaskStatus.FAILED)
                except TransitionError:
                    pass
                return self._report(LoopOutcome.FAILED, error=f"provider error: {exc}")

            self._actions.append(
                ActionPerformed("model_request", type(self.provider).__name__, True)
            )
            self._emit(
                EventType.MODEL_RESPONSE_RECEIVED,
                {
                    "tool_calls": len(response.tool_calls),
                    "content_len": len(response.content),
                },
            )

            # No tool calls: the model has produced its final answer
            # (bounded M2 behaviour; explicit completion signaling comes later).
            if not response.tool_calls:
                final = Message(role=Role.ASSISTANT, content=response.content)
                self.task.messages.append(final)
                self.task.transition(TaskStatus.COMPLETED)
                return self._report(LoopOutcome.COMPLETED)

            # --- ACT: execute each requested tool call
            if self.task.status != TaskStatus.RUNNING:
                self.task.transition(TaskStatus.RUNNING)
            for tool_call in response.tool_calls:
                self.tool_calls += 1
                if self.tool_calls > self.limits.max_tool_calls:
                    self.task.transition(TaskStatus.FAILED)
                    return self._report(
                        LoopOutcome.STOPPED, error="tool-call limit exhausted"
                    )

                tool = self.registry.get(tool_call.name)
                if tool is None:
                    result = ToolResult(
                        tool_call_id=tool_call.id,
                        name=tool_call.name,
                        error=f"unknown tool: {tool_call.name}",
                    )
                elif not self.policy.allows(tool, tool_call.arguments):
                    self._emit(
                        EventType.PERMISSION_REQUIRED,
                        {"tool": tool_call.name, "arguments": tool_call.arguments},
                    )
                    try:
                        self.task.transition(TaskStatus.WAITING_FOR_PERMISSION)
                    except TransitionError:
                        pass
                    return self._report(LoopOutcome.WAITING_FOR_PERMISSION)
                else:
                    try:
                        result = tool.call(tool_call.arguments)
                    except ToolError as exc:
                        result = ToolResult(
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                            error=str(exc),
                        )
                    except Exception as exc:  # noqa: BLE001
                        result = ToolResult(
                            tool_call_id=tool_call.id,
                            name=tool_call.name,
                            error=f"tool execution failed: {exc}",
                        )

                # Bound output bytes.
                if (
                    result.output is not None
                    and len(result.output) > self.limits.max_output_bytes
                ):
                    truncated = result.output[: self.limits.max_output_bytes]
                    result = ToolResult(
                        tool_call_id=result.tool_call_id,
                        name=result.name,
                        output=truncated + "\n...[output truncated]",
                        error=result.error,
                    )

                ok = result.error is None
                self._actions.append(
                    ActionPerformed("tool_call", tool_call.name, ok, result.error or "")
                )
                self.task.results.append(result)
                self.task.messages.append(
                    Message(
                        role=Role.TOOL,
                        content=result.output or "",
                        tool_call_id=tool_call.id,
                    )
                )
                self._emit(
                    EventType.TOOL_COMPLETED,
                    {"tool": tool_call.name, "ok": ok, "error": result.error},
                )

            self._emit(EventType.ITERATION_COMPLETED, {"iteration": self.iterations})
