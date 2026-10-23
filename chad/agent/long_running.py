from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from chad.agent.orchestrator import AgentOrchestrator
from chad.agent.state import AgentRole, AgentRun, AgentState


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class TaskRecord:
    goal: str
    task_id: str = field(default_factory=lambda: str(uuid4()))
    role: AgentRole = AgentRole.ORCHESTRATOR
    priority: int = 0  # higher number = higher priority
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    run: AgentRun | None = None
    error: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "role": self.role.value,
            "priority": self.priority,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "run": self.run.to_dict() if self.run else None,
            "error": self.error,
            "payload": self.payload,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskRecord:
        run_data = data.get("run")
        return cls(
            task_id=str(data["task_id"]),
            goal=str(data["goal"]),
            role=AgentRole(data.get("role", AgentRole.ORCHESTRATOR.value)),
            priority=int(data.get("priority", 0)),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            retry_count=int(data.get("retry_count", 0)),
            max_retries=int(data.get("max_retries", 3)),
            run=AgentRun.from_dict(run_data) if run_data else None,
            error=str(data["error"]) if data.get("error") is not None else None,
            payload=dict(data.get("payload", {})),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        )


class DurableTaskQueue:
    """Persistent and durable task queue for background task execution and interruption recovery."""

    def __init__(self, persistence_path: str | Path | None = None) -> None:
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self._tasks: dict[str, TaskRecord] = {}
        if self.persistence_path and self.persistence_path.exists():
            self.load()

    def enqueue(
        self,
        goal: str,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        priority: int = 0,
        max_retries: int = 3,
        payload: dict[str, Any] | None = None,
    ) -> TaskRecord:
        task = TaskRecord(
            goal=goal,
            role=role,
            priority=priority,
            max_retries=max_retries,
            payload=payload or {},
        )
        self._tasks[task.task_id] = task
        self.save()
        return task

    def dequeue(self) -> TaskRecord | None:
        """Fetch highest-priority PENDING task and mark RUNNING."""
        pending_tasks = [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
        if not pending_tasks:
            return None
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        next_task = pending_tasks[0]
        next_task.status = TaskStatus.RUNNING
        next_task.updated_at = datetime.now(UTC).isoformat()
        self.save()
        return next_task

    def get_task(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        run: AgentRun | None = None,
        error: str | None = None,
    ) -> TaskRecord:
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        task.status = status
        if run is not None:
            task.run = run
        if error is not None:
            task.error = error
        task.updated_at = datetime.now(UTC).isoformat()
        self.save()
        return task

    def resume_run(
        self,
        task_id: str,
        orchestrator: AgentOrchestrator | None = None,
    ) -> AgentRun:
        """Resume or recover an interrupted task run."""
        task = self.get_task(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        orch = orchestrator or AgentOrchestrator()

        if task.run is None:
            task.run = orch.start_run(goal=task.goal, role=task.role)
        elif task.run.current_state in (
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.TIMEOUT,
        ):
            if task.retry_count >= task.max_retries:
                raise ValueError(
                    f"Cannot resume task {task_id}: max retries ({task.max_retries}) reached"
                )
            task.retry_count += 1
            task.run = orch.start_run(goal=task.goal, role=task.role)

        task.status = TaskStatus.RUNNING
        task.updated_at = datetime.now(UTC).isoformat()
        self.save()
        return task.run

    def pause_task(self, task_id: str) -> TaskRecord:
        return self.update_task_status(task_id, TaskStatus.PAUSED)

    def cancel_task(self, task_id: str, reason: str = "Cancelled by user") -> TaskRecord:
        return self.update_task_status(task_id, TaskStatus.CANCELLED, error=reason)

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskRecord]:
        tasks = list(self._tasks.values())
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def save(self) -> None:
        if not self.persistence_path:
            return
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        data = {tid: t.to_dict() for tid, t in self._tasks.items()}
        self.persistence_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.persistence_path or not self.persistence_path.exists():
            return
        content = self.persistence_path.read_text(encoding="utf-8")
        if not content.strip():
            return
        data = json.loads(content)
        self._tasks = {tid: TaskRecord.from_dict(raw) for tid, raw in data.items()}


@dataclass(slots=True)
class ScheduledTask:
    schedule_id: str = field(default_factory=lambda: str(uuid4()))
    goal: str = ""
    role: AgentRole = AgentRole.ORCHESTRATOR
    interval_seconds: float | None = None
    scheduled_at: str | None = None
    enabled: bool = True
    last_run_at: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_due(self, now: datetime | None = None) -> bool:
        if not self.enabled:
            return False
        current_time = now or datetime.now(UTC)

        if self.scheduled_at:
            sched_dt = datetime.fromisoformat(self.scheduled_at)
            if current_time >= sched_dt and self.last_run_at is None:
                return True

        if self.interval_seconds and self.interval_seconds > 0:
            if self.last_run_at is None:
                return True
            last_dt = datetime.fromisoformat(self.last_run_at)
            elapsed = (current_time - last_dt).total_seconds()
            if elapsed >= self.interval_seconds:
                return True

        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "goal": self.goal,
            "role": self.role.value,
            "interval_seconds": self.interval_seconds,
            "scheduled_at": self.scheduled_at,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at,
            "payload": self.payload,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
        return cls(
            schedule_id=str(data["schedule_id"]),
            goal=str(data["goal"]),
            role=AgentRole(data.get("role", AgentRole.ORCHESTRATOR.value)),
            interval_seconds=float(data["interval_seconds"])
            if data.get("interval_seconds") is not None
            else None,
            scheduled_at=str(data["scheduled_at"]) if data.get("scheduled_at") is not None else None,
            enabled=bool(data.get("enabled", True)),
            last_run_at=str(data["last_run_at"]) if data.get("last_run_at") is not None else None,
            payload=dict(data.get("payload", {})),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
        )


class AgentScheduler:
    """Schedules delayed or recurring tasks for agent execution."""

    def __init__(self, queue: DurableTaskQueue | None = None) -> None:
        self.queue = queue or DurableTaskQueue()
        self._schedules: dict[str, ScheduledTask] = {}

    def schedule_task(
        self,
        goal: str,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        interval_seconds: float | None = None,
        scheduled_at: str | datetime | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ScheduledTask:
        sched_time_str = None
        if isinstance(scheduled_at, datetime):
            sched_time_str = scheduled_at.isoformat()
        elif isinstance(scheduled_at, str):
            sched_time_str = scheduled_at

        task = ScheduledTask(
            goal=goal,
            role=role,
            interval_seconds=interval_seconds,
            scheduled_at=sched_time_str,
            payload=payload or {},
        )
        self._schedules[task.schedule_id] = task
        return task

    def enable_schedule(self, schedule_id: str) -> None:
        if schedule_id in self._schedules:
            self._schedules[schedule_id].enabled = True

    def disable_schedule(self, schedule_id: str) -> None:
        if schedule_id in self._schedules:
            self._schedules[schedule_id].enabled = False

    def get_due_tasks(self, now: datetime | None = None) -> list[ScheduledTask]:
        return [s for s in self._schedules.values() if s.is_due(now=now)]

    def trigger_due_tasks(self, now: datetime | None = None) -> list[TaskRecord]:
        due = self.get_due_tasks(now=now)
        enqueued_records: list[TaskRecord] = []
        now_str = (now or datetime.now(UTC)).isoformat()

        for sched in due:
            record = self.queue.enqueue(
                goal=sched.goal,
                role=sched.role,
                payload=sched.payload,
            )
            sched.last_run_at = now_str
            enqueued_records.append(record)

        return enqueued_records


class CheckpointStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(slots=True)
class CheckpointRecord:
    checkpoint_id: str = field(default_factory=lambda: str(uuid4()))
    run_id: str = ""
    action_name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: CheckpointStatus = CheckpointStatus.PENDING
    timeout_seconds: float = 300.0
    reason: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "action_name": self.action_name,
            "payload": self.payload,
            "status": self.status.value,
            "timeout_seconds": self.timeout_seconds,
            "reason": self.reason,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CheckpointRecord:
        return cls(
            checkpoint_id=str(data["checkpoint_id"]),
            run_id=str(data.get("run_id", "")),
            action_name=str(data.get("action_name", "")),
            payload=dict(data.get("payload", {})),
            status=CheckpointStatus(data.get("status", CheckpointStatus.PENDING.value)),
            timeout_seconds=float(data.get("timeout_seconds", 300.0)),
            reason=str(data["reason"]) if data.get("reason") is not None else None,
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        )


class HumanCheckpointEngine:
    """Manages human-in-the-loop checkpoints and decision evaluation."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointRecord] = {}

    def register_checkpoint(
        self,
        run_id: str,
        action_name: str,
        payload: dict[str, Any] | None = None,
        timeout_seconds: float = 300.0,
    ) -> CheckpointRecord:
        checkpoint = CheckpointRecord(
            run_id=run_id,
            action_name=action_name,
            payload=payload or {},
            timeout_seconds=timeout_seconds,
        )
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint
        return checkpoint

    def approve_checkpoint(
        self, checkpoint_id: str, reason: str = "Approved by human operator"
    ) -> CheckpointRecord:
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        if cp.status != CheckpointStatus.PENDING:
            raise ValueError(f"Checkpoint {checkpoint_id} is in state {cp.status}, cannot approve")
        cp.status = CheckpointStatus.APPROVED
        cp.reason = reason
        cp.updated_at = datetime.now(UTC).isoformat()
        return cp

    def deny_checkpoint(
        self, checkpoint_id: str, reason: str = "Denied by human operator"
    ) -> CheckpointRecord:
        cp = self._checkpoints.get(checkpoint_id)
        if not cp:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        if cp.status != CheckpointStatus.PENDING:
            raise ValueError(f"Checkpoint {checkpoint_id} is in state {cp.status}, cannot deny")
        cp.status = CheckpointStatus.DENIED
        cp.reason = reason
        cp.updated_at = datetime.now(UTC).isoformat()
        return cp

    def evaluate_timeouts(self, current_time: datetime | None = None) -> list[CheckpointRecord]:
        now_dt = current_time or datetime.now(UTC)
        timed_out: list[CheckpointRecord] = []
        for cp in self._checkpoints.values():
            if cp.status == CheckpointStatus.PENDING:
                created_dt = datetime.fromisoformat(cp.created_at)
                elapsed = (now_dt - created_dt).total_seconds()
                if elapsed >= cp.timeout_seconds:
                    cp.status = CheckpointStatus.TIMED_OUT
                    cp.reason = f"Timed out after {elapsed:.1f}s (limit {cp.timeout_seconds}s)"
                    cp.updated_at = now_dt.isoformat()
                    timed_out.append(cp)
        return timed_out

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointRecord | None:
        return self._checkpoints.get(checkpoint_id)


@dataclass(slots=True)
class DelegatedTaskResult:
    sub_run_id: str
    role: AgentRole
    goal: str
    status: AgentState
    result: str | None = None
    error: str | None = None


class MultiAgentDelegator:
    """Delegates complex sub-tasks across multiple specialist agent roles."""

    def __init__(self, orchestrator: AgentOrchestrator | None = None) -> None:
        self.orchestrator = orchestrator or AgentOrchestrator()

    def delegate_subtask(
        self,
        parent_run: AgentRun,
        target_role: AgentRole,
        sub_goal: str,
        executor_fn: Callable[[dict[str, Any]], str] | None = None,
    ) -> DelegatedTaskResult:
        self.orchestrator.handoff(
            run=parent_run,
            target_role=target_role,
            reason=f"Delegating sub-task: {sub_goal}",
        )

        sub_run = self.orchestrator.start_run(goal=sub_goal, role=target_role)

        try:
            if executor_fn is not None:
                self.orchestrator.execute_step(
                    run=sub_run,
                    action_name="delegated_execution",
                    executor_fn=executor_fn,
                )
            if sub_run.current_state not in (
                AgentState.FAILED,
                AgentState.CANCELLED,
                AgentState.DENIED,
                AgentState.TIMEOUT,
            ):
                self.orchestrator.complete_run(
                    sub_run,
                    result=sub_run.result or f"Sub-task completed for role {target_role.value}",
                )
            res = DelegatedTaskResult(
                sub_run_id=sub_run.run_id,
                role=target_role,
                goal=sub_goal,
                status=sub_run.current_state,
                result=sub_run.result,
            )
        except Exception as exc:  # noqa: BLE001
            sub_run.transition_to(AgentState.FAILED, description=f"Delegated subtask error: {exc}")
            res = DelegatedTaskResult(
                sub_run_id=sub_run.run_id,
                role=target_role,
                goal=sub_goal,
                status=sub_run.current_state,
                error=str(exc),
            )

        self.orchestrator.handoff(
            run=parent_run,
            target_role=AgentRole.ORCHESTRATOR,
            reason=f"Sub-task completed with status {sub_run.current_state}",
        )

        return res


@dataclass(slots=True)
class ExecutionStrategy:
    strategy_name: str
    recommended_role: AgentRole
    estimated_cost_usd: float
    reliability_score: float  # 0.0 to 1.0
    max_retries: int
    model_choice: str
    tradeoff_score: float


class CostReliabilityPlanner:
    """Plans execution strategies balancing monetary cost and reliability requirements."""

    def __init__(self, reliability_scores: dict[AgentRole, float] | None = None) -> None:
        self.reliability_scores = reliability_scores or {
            AgentRole.ORCHESTRATOR: 0.95,
            AgentRole.RESEARCHER: 0.90,
            AgentRole.CODER: 0.85,
            AgentRole.ANALYST: 0.92,
        }

    def evaluate_strategies(
        self,
        goal: str,
        max_cost_budget: float = 1.0,
        min_reliability: float = 0.8,
    ) -> list[ExecutionStrategy]:
        strategies = [
            ExecutionStrategy(
                strategy_name="fast_economy",
                recommended_role=AgentRole.ORCHESTRATOR,
                estimated_cost_usd=0.01,
                reliability_score=0.82,
                max_retries=1,
                model_choice="lapis-mini",
                tradeoff_score=0.82 / 0.01,
            ),
            ExecutionStrategy(
                strategy_name="balanced_standard",
                recommended_role=AgentRole.RESEARCHER,
                estimated_cost_usd=0.05,
                reliability_score=0.92,
                max_retries=3,
                model_choice="lapis-base",
                tradeoff_score=0.92 / 0.05,
            ),
            ExecutionStrategy(
                strategy_name="high_reliability",
                recommended_role=AgentRole.CODER,
                estimated_cost_usd=0.15,
                reliability_score=0.98,
                max_retries=5,
                model_choice="lapis-pro",
                tradeoff_score=0.98 / 0.15,
            ),
        ]

        valid_strategies = [
            s
            for s in strategies
            if s.estimated_cost_usd <= max_cost_budget and s.reliability_score >= min_reliability
        ]

        valid_strategies.sort(key=lambda s: s.tradeoff_score, reverse=True)
        return valid_strategies

    def select_best_strategy(
        self,
        goal: str,
        max_cost_budget: float = 1.0,
        min_reliability: float = 0.8,
    ) -> ExecutionStrategy:
        strategies = self.evaluate_strategies(
            goal=goal,
            max_cost_budget=max_cost_budget,
            min_reliability=min_reliability,
        )
        if not strategies:
            raise ValueError(
                f"No strategy available meeting cost <= ${max_cost_budget:.2f} and reliability >= {min_reliability}"
            )
        return strategies[0]
