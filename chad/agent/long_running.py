from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import IntEnum, StrEnum
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from chad.agent.orchestrator import AgentOrchestrator
from chad.agent.state import AgentRole, AgentRun, AgentState


class TaskPriority(IntEnum):
    LOW = 0
    NORMAL = 10
    HIGH = 20
    CRITICAL = 30


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_CHECKPOINT = "WAITING_CHECKPOINT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class TaskItem:
    goal: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    role: AgentRole = AgentRole.ORCHESTRATOR
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    scheduled_at: str | None = None
    retries_left: int = 3
    last_error: str | None = None
    result: str | None = None
    run: AgentRun | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "role": self.role.value,
            "priority": int(self.priority),
            "status": self.status.value,
            "scheduled_at": self.scheduled_at,
            "retries_left": self.retries_left,
            "last_error": self.last_error,
            "result": self.result,
            "run": self.run.to_dict() if self.run else None,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskItem:
        run_data = data.get("run")
        return cls(
            task_id=str(data["task_id"]),
            goal=str(data["goal"]),
            role=AgentRole(data.get("role", AgentRole.ORCHESTRATOR.value)),
            priority=TaskPriority(int(data.get("priority", TaskPriority.NORMAL))),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            scheduled_at=data.get("scheduled_at"),
            retries_left=int(data.get("retries_left", 3)),
            last_error=data.get("last_error"),
            result=data.get("result"),
            run=AgentRun.from_dict(dict(run_data)) if run_data else None,
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        )


class DurableTaskQueue:
    """File-persisted or in-memory queue for background agent tasks."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._tasks: dict[str, TaskItem] = {}
        self._load()

    def _save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {tid: task.to_dict() for tid, task in self._tasks.items()}
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._tasks = {tid: TaskItem.from_dict(item) for tid, item in raw.items()}
        except Exception as exc:
            raise RuntimeError(f"Failed to load task queue from {self.storage_path}: {exc}") from exc

    def enqueue(
        self,
        goal: str,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        priority: TaskPriority = TaskPriority.NORMAL,
        scheduled_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TaskItem:
        status = TaskStatus.SCHEDULED if scheduled_at else TaskStatus.PENDING
        task = TaskItem(
            goal=goal,
            role=role,
            priority=priority,
            status=status,
            scheduled_at=scheduled_at,
            metadata=metadata or {},
        )
        self._tasks[task.task_id] = task
        self._save()
        return task

    def dequeue(self) -> TaskItem | None:
        now_iso = datetime.now(UTC).isoformat()
        candidates: list[TaskItem] = []

        for task in self._tasks.values():
            if task.status == TaskStatus.PENDING or (
                task.status == TaskStatus.SCHEDULED and task.scheduled_at and task.scheduled_at <= now_iso
            ):
                candidates.append(task)

        if not candidates:
            return None

        # Sort by priority descending, then created_at ascending
        candidates.sort(key=lambda t: (-int(t.priority), t.created_at))
        selected = candidates[0]
        selected.status = TaskStatus.RUNNING
        selected.updated_at = now_iso
        self._save()
        return selected

    def pause_task(self, task_id: str, reason: str = "") -> TaskItem:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found in queue.")
        task = self._tasks[task_id]
        task.status = TaskStatus.PAUSED
        task.metadata["pause_reason"] = reason
        task.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return task

    def resume_task(self, task_id: str) -> TaskItem:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found in queue.")
        task = self._tasks[task_id]
        task.status = TaskStatus.PENDING
        task.updated_at = datetime.now(UTC).isoformat()
        self._save()
        return task

    def complete_task(self, task_id: str, result: str) -> TaskItem:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found in queue.")
        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.result = result
        task.updated_at = datetime.now(UTC).isoformat()
        if task.run and task.run.current_state != AgentState.COMPLETED:
            task.run.current_state = AgentState.COMPLETED
            task.run.result = result
        self._save()
        return task

    def fail_task(self, task_id: str, error: str) -> TaskItem:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found in queue.")
        task = self._tasks[task_id]
        task.retries_left -= 1
        task.last_error = error
        task.updated_at = datetime.now(UTC).isoformat()

        if task.retries_left > 0:
            task.status = TaskStatus.PENDING
        else:
            task.status = TaskStatus.FAILED
            if task.run and task.run.current_state != AgentState.FAILED:
                task.run.current_state = AgentState.FAILED

        self._save()
        return task

    def cancel_task(self, task_id: str, reason: str = "User cancelled") -> TaskItem:
        if task_id not in self._tasks:
            raise KeyError(f"Task {task_id} not found in queue.")
        task = self._tasks[task_id]
        task.status = TaskStatus.CANCELLED
        task.metadata["cancel_reason"] = reason
        task.updated_at = datetime.now(UTC).isoformat()
        if task.run:
            task.run.current_state = AgentState.CANCELLED
        self._save()
        return task

    def get_task(self, task_id: str) -> TaskItem | None:
        return self._tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskItem]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: (-int(t.priority), t.created_at))
        return tasks


class AgentScheduler:
    """Schedules background agent tasks with delay or recurring intervals."""

    def __init__(self, queue: DurableTaskQueue) -> None:
        self.queue = queue
        self._recurring_rules: list[dict[str, Any]] = []

    def schedule_task(
        self,
        goal: str,
        run_at: str | datetime,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> TaskItem:
        if isinstance(run_at, datetime):
            scheduled_iso = run_at.astimezone(UTC).isoformat()
        else:
            scheduled_iso = str(run_at)

        return self.queue.enqueue(
            goal=goal,
            role=role,
            priority=priority,
            scheduled_at=scheduled_iso,
            metadata=metadata,
        )

    def schedule_recurring(
        self,
        goal: str,
        interval_seconds: float,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> TaskItem:
        next_run = datetime.now(UTC) + timedelta(seconds=interval_seconds)
        rule = {
            "rule_id": str(uuid4()),
            "goal": goal,
            "interval_seconds": interval_seconds,
            "role": role,
            "priority": priority,
            "metadata": metadata or {},
            "last_run": None,
        }
        self._recurring_rules.append(rule)
        return self.schedule_task(
            goal=goal,
            run_at=next_run,
            role=role,
            priority=priority,
            metadata={**(metadata or {}), "recurring_rule_id": rule["rule_id"]},
        )

    def poll_due_tasks(self) -> list[TaskItem]:
        now_iso = datetime.now(UTC).isoformat()
        due_tasks = [
            task
            for task in self.queue.list_tasks(status=TaskStatus.SCHEDULED)
            if task.scheduled_at and task.scheduled_at <= now_iso
        ]
        for task in due_tasks:
            task.status = TaskStatus.PENDING
            task.updated_at = now_iso

            # Check if this task belongs to a recurring rule
            rule_id = task.metadata.get("recurring_rule_id")
            if rule_id:
                rule = next((r for r in self._recurring_rules if r["rule_id"] == rule_id), None)
                if rule:
                    next_run = datetime.now(UTC) + timedelta(seconds=rule["interval_seconds"])
                    self.schedule_task(
                        goal=rule["goal"],
                        run_at=next_run,
                        role=rule["role"],
                        priority=rule["priority"],
                        metadata={**rule["metadata"], "recurring_rule_id": rule_id},
                    )

        if self.queue.storage_path:
            self.queue._save()

        return due_tasks


@dataclass(slots=True)
class HumanCheckpoint:
    run_id: str
    reason: str
    prompt: str
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED
    human_input: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    resolved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "reason": self.reason,
            "prompt": self.prompt,
            "status": self.status,
            "human_input": self.human_input,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HumanCheckpoint:
        return cls(
            checkpoint_id=str(data["checkpoint_id"]),
            run_id=str(data["run_id"]),
            reason=str(data["reason"]),
            prompt=str(data["prompt"]),
            status=str(data.get("status", "PENDING")),
            human_input=data.get("human_input"),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            resolved_at=data.get("resolved_at"),
        )


class HumanCheckpointEngine:
    """Manages human approval checkpoints for long-running agent workflows."""

    def __init__(self, storage_path: str | Path | None = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else None
        self._checkpoints: dict[str, HumanCheckpoint] = {}
        self._load()

    def _save(self) -> None:
        if not self.storage_path:
            return
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {cid: ck.to_dict() for cid, ck in self._checkpoints.items()}
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        try:
            raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._checkpoints = {cid: HumanCheckpoint.from_dict(item) for cid, item in raw.items()}
        except Exception as exc:
            raise RuntimeError(f"Failed to load checkpoints from {self.storage_path}: {exc}") from exc

    def create_checkpoint(self, run: AgentRun, reason: str, prompt: str) -> HumanCheckpoint:
        checkpoint = HumanCheckpoint(run_id=run.run_id, reason=reason, prompt=prompt)
        run.pending_approval = {
            "checkpoint_id": checkpoint.checkpoint_id,
            "reason": reason,
            "prompt": prompt,
        }
        run.transition_to(
            AgentState.WAITING_APPROVAL,
            description=f"Human checkpoint triggered: {reason}",
            metadata={"checkpoint_id": checkpoint.checkpoint_id},
        )
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        self._save()
        return checkpoint

    def resolve_checkpoint(
        self,
        checkpoint_id: str,
        approved: bool,
        human_input: str | None = None,
        orchestrator: AgentOrchestrator | None = None,
        run: AgentRun | None = None,
    ) -> HumanCheckpoint:
        if checkpoint_id not in self._checkpoints:
            raise KeyError(f"Checkpoint {checkpoint_id} not found.")

        checkpoint = self._checkpoints[checkpoint_id]
        checkpoint.status = "APPROVED" if approved else "REJECTED"
        checkpoint.human_input = human_input
        checkpoint.resolved_at = datetime.now(UTC).isoformat()

        if run and orchestrator:
            if approved:
                orchestrator.approve_step(run, executor_fn=lambda p: human_input or "Approved by human")
            else:
                orchestrator.deny_step(run, reason=f"Rejected at checkpoint: {human_input or 'User denied'}")

        self._save()
        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> HumanCheckpoint | None:
        return self._checkpoints.get(checkpoint_id)

    def list_checkpoints(self, run_id: str | None = None, status: str | None = None) -> list[HumanCheckpoint]:
        res = list(self._checkpoints.values())
        if run_id:
            res = [c for c in res if c.run_id == run_id]
        if status:
            res = [c for c in res if c.status == status]
        return res


@dataclass(slots=True)
class SubtaskNode:
    goal: str
    role: AgentRole
    parent_run_id: str
    subtask_id: str = field(default_factory=lambda: str(uuid4()))
    child_run_id: str | None = None
    status: AgentState = AgentState.RECEIVED
    result: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "goal": self.goal,
            "role": self.role.value,
            "parent_run_id": self.parent_run_id,
            "child_run_id": self.child_run_id,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubtaskNode:
        return cls(
            subtask_id=str(data["subtask_id"]),
            goal=str(data["goal"]),
            role=AgentRole(data["role"]),
            parent_run_id=str(data["parent_run_id"]),
            child_run_id=data.get("child_run_id"),
            status=AgentState(data.get("status", AgentState.RECEIVED.value)),
            result=data.get("result"),
            error=data.get("error"),
        )


class MultiAgentDelegator:
    """Coordinates multi-agent delegation, parent-child agent run graphs, and subtask aggregation."""

    def __init__(self, orchestrator: AgentOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or AgentOrchestrator()

    def delegate_subtasks(
        self,
        parent_run: AgentRun,
        subtasks: list[dict[str, Any]],
    ) -> list[SubtaskNode]:
        nodes: list[SubtaskNode] = []
        for task_spec in subtasks:
            goal = str(task_spec["goal"])
            role = AgentRole(task_spec.get("role", AgentRole.RESEARCHER.value))

            child_run = self.orchestrator.start_run(goal=goal, role=role)
            node = SubtaskNode(
                goal=goal,
                role=role,
                parent_run_id=parent_run.run_id,
                child_run_id=child_run.run_id,
                status=child_run.current_state,
            )
            nodes.append(node)

            parent_run.record_handoff(
                target_role=role,
                reason=f"Delegating subtask: {goal}",
                payload={"subtask_id": node.subtask_id, "child_run_id": child_run.run_id},
            )

        return nodes

    def execute_delegation(
        self,
        parent_run: AgentRun,
        subtask_nodes: list[SubtaskNode],
        executor_map: dict[AgentRole, Callable[[str], str]] | None = None,
    ) -> dict[str, str]:
        results: dict[str, str] = {}
        executor_map = executor_map or {}

        for node in subtask_nodes:
            role_val = node.role

            def _default_exec(g: str, r: AgentRole = role_val) -> str:
                return f"Executed subtask for role {r.value}: {g}"

            exec_fn = executor_map.get(node.role, _default_exec)
            try:
                subtask_output = exec_fn(node.goal)
                node.result = subtask_output
                node.status = AgentState.COMPLETED
                results[node.subtask_id] = subtask_output

                parent_run._add_event(
                    event_type="SUBTASK_COMPLETED",
                    state_from=parent_run.current_state,
                    state_to=parent_run.current_state,
                    description=f"Subtask '{node.goal[:50]}' completed by {node.role.value}",
                    metadata={"subtask_id": node.subtask_id, "result": subtask_output},
                )
            except Exception as exc:  # noqa: BLE001
                node.error = str(exc)
                node.status = AgentState.FAILED
                results[node.subtask_id] = f"Error: {exc}"

                parent_run._add_event(
                    event_type="SUBTASK_FAILED",
                    state_from=parent_run.current_state,
                    state_to=parent_run.current_state,
                    description=f"Subtask '{node.goal[:50]}' failed: {exc}",
                    metadata={"subtask_id": node.subtask_id, "error": str(exc)},
                )

        return results


class CostReliabilityPlanner:
    """Planning module selecting execution strategies based on cost limits and provider reliability."""

    def __init__(self) -> None:
        self.provider_reliability: dict[str, float] = {
            "lapis_local": 0.95,
            "openai": 0.99,
            "anthropic": 0.98,
        }
        self.model_costs: dict[str, float] = {
            "lapis_local": 0.001,
            "gpt-4o-mini": 0.005,
            "gpt-4o": 0.03,
            "claude-3-5-sonnet": 0.03,
        }

    def plan_execution(
        self,
        goal: str,
        max_cost_budget: float = 0.05,
        required_reliability: float = 0.90,
    ) -> dict[str, Any]:
        """Formulate execution plan with recommended primary and fallback model choices."""
        eligible_models = [
            model
            for model, cost in self.model_costs.items()
            if cost <= max_cost_budget
        ]

        if not eligible_models:
            # Fallback to cheapest available model
            cheapest = min(self.model_costs.items(), key=lambda x: x[1])[0]
            eligible_models = [cheapest]

        # Sort eligible models by reliability then cost
        ranked = sorted(
            eligible_models,
            key=lambda m: (
                self.provider_reliability.get(m, 0.90) >= required_reliability,
                -self.model_costs.get(m, 0.0),
            ),
            reverse=True,
        )

        primary_model = ranked[0]
        fallback_models = [m for m in ranked[1:] if m != primary_model]

        # Determine retry policy based on primary model reliability
        rel_score = self.provider_reliability.get(primary_model, 0.90)
        max_retries = 3 if rel_score >= 0.95 else 5

        return {
            "goal": goal,
            "primary_model": primary_model,
            "fallback_models": fallback_models,
            "estimated_cost": self.model_costs.get(primary_model, 0.01),
            "reliability_score": rel_score,
            "max_retries": max_retries,
            "strategy": "HIGH_RELIABILITY" if rel_score >= 0.95 else "COST_OPTIMIZED",
        }

    def record_outcome(
        self,
        provider_or_model: str,
        success: bool,
        latency_s: float = 0.0,
        cost: float = 0.0,
    ) -> None:
        """Update dynamic reliability scores based on execution outcomes."""
        curr = self.provider_reliability.get(provider_or_model, 0.90)
        if success:
            updated = min(1.0, curr * 0.95 + 0.05)
        else:
            updated = max(0.1, curr * 0.85)
        self.provider_reliability[provider_or_model] = round(updated, 3)
