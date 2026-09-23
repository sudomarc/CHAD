from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class AgentState(StrEnum):
    RECEIVED = "RECEIVED"
    CLASSIFIED = "CLASSIFIED"
    PLANNED = "PLANNED"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    DENIED = "DENIED"
    TIMEOUT = "TIMEOUT"


class AgentRole(StrEnum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    ANALYST = "analyst"


TERMINAL_STATES = {
    AgentState.COMPLETED,
    AgentState.FAILED,
    AgentState.CANCELLED,
    AgentState.DENIED,
    AgentState.TIMEOUT,
}


@dataclass(slots=True)
class ExecutionBudget:
    max_steps: int = 20
    max_tokens: int = 100_000
    max_time_seconds: float = 300.0
    max_retries: int = 3
    used_steps: int = 0
    used_tokens: int = 0
    used_retries: int = 0
    start_time: float | None = field(default_factory=time.time)

    def record_step(self, tokens_used: int = 0) -> None:
        if self.start_time is None:
            self.start_time = time.time()
        self.used_steps += 1
        self.used_tokens += tokens_used

    def record_retry(self) -> None:
        self.used_retries += 1

    def is_exceeded(self) -> tuple[bool, str | None]:
        if self.used_steps >= self.max_steps:
            return True, f"Step limit reached ({self.used_steps}/{self.max_steps})"
        if self.used_tokens >= self.max_tokens:
            return True, f"Token limit reached ({self.used_tokens}/{self.max_tokens})"
        if self.used_retries > self.max_retries:
            return True, f"Retry limit reached ({self.used_retries}/{self.max_retries})"
        if self.start_time is not None:
            elapsed = time.time() - self.start_time
            if elapsed >= self.max_time_seconds:
                return True, f"Time limit exceeded ({elapsed:.1f}s/{self.max_time_seconds:.1f}s)"
        return False, None

    def to_dict(self) -> dict[str, object]:
        return {
            "max_steps": self.max_steps,
            "max_tokens": self.max_tokens,
            "max_time_seconds": self.max_time_seconds,
            "max_retries": self.max_retries,
            "used_steps": self.used_steps,
            "used_tokens": self.used_tokens,
            "used_retries": self.used_retries,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ExecutionBudget:
        return cls(
            max_steps=int(data.get("max_steps", 20)),
            max_tokens=int(data.get("max_tokens", 100_000)),
            max_time_seconds=float(data.get("max_time_seconds", 300.0)),
            max_retries=int(data.get("max_retries", 3)),
            used_steps=int(data.get("used_steps", 0)),
            used_tokens=int(data.get("used_tokens", 0)),
            used_retries=int(data.get("used_retries", 0)),
            start_time=float(data["start_time"]) if data.get("start_time") is not None else None,
        )


@dataclass(frozen=True, slots=True)
class AgentEvent:
    timestamp: str
    event_type: str
    role: AgentRole
    state_from: AgentState | None
    state_to: AgentState
    description: str
    metadata: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "role": self.role.value,
            "state_from": self.state_from.value if self.state_from else None,
            "state_to": self.state_to.value,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentEvent:
        return cls(
            timestamp=str(data["timestamp"]),
            event_type=str(data["event_type"]),
            role=AgentRole(data["role"]),
            state_from=AgentState(data["state_from"]) if data.get("state_from") else None,
            state_to=AgentState(data["state_to"]),
            description=str(data["description"]),
            metadata=dict(data.get("metadata", {})),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, slots=True)
class AgentHandoff:
    from_role: AgentRole
    to_role: AgentRole
    reason: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    payload: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "from_role": self.from_role.value,
            "to_role": self.to_role.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentHandoff:
        return cls(
            from_role=AgentRole(data["from_role"]),
            to_role=AgentRole(data["to_role"]),
            reason=str(data["reason"]),
            timestamp=str(data.get("timestamp") or datetime.now(UTC).isoformat()),
            payload=dict(data.get("payload", {})),  # type: ignore[arg-type]
        )


@dataclass(slots=True)
class AgentRun:
    goal: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    current_role: AgentRole = AgentRole.ORCHESTRATOR
    current_state: AgentState = AgentState.RECEIVED
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    events: list[AgentEvent] = field(default_factory=list)
    handoffs: list[AgentHandoff] = field(default_factory=list)
    pending_approval: dict[str, object] | None = None
    result: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.goal.strip():
            raise ValueError("agent run goal cannot be empty")
        if not self.events:
            self._add_event(
                event_type="RUN_CREATED",
                state_from=None,
                state_to=self.current_state,
                description=f"Run created for goal: {self.goal}",
            )

    def _add_event(
        self,
        event_type: str,
        state_from: AgentState | None,
        state_to: AgentState,
        description: str,
        metadata: dict[str, object] | None = None,
    ) -> AgentEvent:
        now_str = datetime.now(UTC).isoformat()
        self.updated_at = now_str
        event = AgentEvent(
            timestamp=now_str,
            event_type=event_type,
            role=self.current_role,
            state_from=state_from,
            state_to=state_to,
            description=description,
            metadata=metadata or {},
        )
        self.events.append(event)
        return event

    def transition_to(
        self,
        new_state: AgentState,
        description: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        if self.current_state in TERMINAL_STATES and new_state not in TERMINAL_STATES:
            raise ValueError(
                f"Cannot transition from terminal state {self.current_state} to {new_state}"
            )
        old_state = self.current_state
        self.current_state = new_state
        self._add_event(
            event_type="STATE_TRANSITION",
            state_from=old_state,
            state_to=new_state,
            description=description,
            metadata=metadata,
        )

    def record_handoff(
        self,
        target_role: AgentRole,
        reason: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        handoff = AgentHandoff(
            from_role=self.current_role,
            to_role=target_role,
            reason=reason,
            payload=payload or {},
        )
        self.handoffs.append(handoff)
        old_role = self.current_role
        self.current_role = target_role
        self._add_event(
            event_type="HANDOFF",
            state_from=self.current_state,
            state_to=self.current_state,
            description=f"Handoff from {old_role} to {target_role}: {reason}",
            metadata={"handoff": handoff.to_dict()},
        )

    def check_loop(self, max_repeats: int = 3) -> bool:
        """Detect if the agent is stuck repeating the same state/description sequence."""
        if len(self.events) < max_repeats * 2:
            return False

        recent_transitions = [
            (e.state_to, e.description)
            for e in self.events
            if e.event_type in ("STATE_TRANSITION", "STEP_EXECUTED")
        ]
        if len(recent_transitions) < max_repeats:
            return False

        last_item = recent_transitions[-1]
        repeats = sum(1 for item in recent_transitions[-max_repeats:] if item == last_item)
        return repeats >= max_repeats

    def to_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "current_role": self.current_role.value,
            "current_state": self.current_state.value,
            "budget": self.budget.to_dict(),
            "events": [e.to_dict() for e in self.events],
            "handoffs": [h.to_dict() for h in self.handoffs],
            "pending_approval": self.pending_approval,
            "result": self.result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentRun:
        run = cls(
            run_id=str(data["run_id"]),
            goal=str(data["goal"]),
            current_role=AgentRole(data.get("current_role", AgentRole.ORCHESTRATOR.value)),
            current_state=AgentState(data.get("current_state", AgentState.RECEIVED.value)),
            budget=ExecutionBudget.from_dict(dict(data["budget"])) if "budget" in data else ExecutionBudget(),  # type: ignore[arg-type]
            events=[AgentEvent.from_dict(e) for e in data.get("events", [])],  # type: ignore[arg-type]
            handoffs=[AgentHandoff.from_dict(h) for h in data.get("handoffs", [])],  # type: ignore[arg-type]
            pending_approval=dict(data["pending_approval"]) if data.get("pending_approval") else None,  # type: ignore[arg-type]
            result=str(data["result"]) if data.get("result") is not None else None,
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        )
        return run
