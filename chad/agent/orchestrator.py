from __future__ import annotations

from typing import Any, Callable

from chad.agent.registry import AgentRegistry
from chad.agent.state import AgentRole, AgentRun, AgentState
from chad.llm.gateway import ModelGateway


class AgentOrchestrator:
    """State machine and execution orchestrator for CHAD agent runs."""

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        gateway: ModelGateway | None = None,
    ) -> None:
        self.registry = registry or AgentRegistry()
        self.gateway = gateway

    def start_run(
        self,
        goal: str,
        role: AgentRole = AgentRole.ORCHESTRATOR,
        max_steps: int | None = None,
    ) -> AgentRun:
        contract = self.registry.get(role)
        effective_max_steps = max_steps or contract.max_steps
        run = AgentRun(goal=goal, current_role=role)
        run.budget.max_steps = effective_max_steps

        # Execute classification & planning phase transitions
        run.transition_to(AgentState.CLASSIFIED, description=f"Goal classified for role {role.value}")
        run.transition_to(AgentState.PLANNED, description=f"Execution plan initialized for role {role.value}")
        return run

    def execute_step(
        self,
        run: AgentRun,
        action_name: str,
        action_payload: dict[str, Any] | None = None,
        tokens_used: int = 0,
        executor_fn: Callable[[dict[str, Any]], str] | None = None,
    ) -> AgentRun:
        if run.current_state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.DENIED,
            AgentState.TIMEOUT,
        ):
            raise ValueError(f"Cannot execute step on terminal state {run.current_state}")

        if run.current_state == AgentState.WAITING_APPROVAL:
            raise ValueError("Run is waiting for user approval. Call approve_step() or deny_step().")

        # Budget check
        is_exceeded, reason = run.budget.is_exceeded()
        if is_exceeded:
            run.transition_to(AgentState.TIMEOUT, description=f"Budget exceeded: {reason}")
            return run

        contract = self.registry.get(run.current_role)

        # Approval checkpoint
        if action_name in contract.requires_approval_actions:
            run.pending_approval = {
                "action": action_name,
                "payload": action_payload or {},
                "role": run.current_role.value,
            }
            run.transition_to(
                AgentState.WAITING_APPROVAL,
                description=f"Action '{action_name}' requires approval before execution.",
                metadata={"action": action_name, "payload": action_payload or {}},
            )
            return run

        # Transition to EXECUTING state if needed
        if run.current_state != AgentState.EXECUTING:
            run.transition_to(AgentState.EXECUTING, description=f"Executing step action: {action_name}")

        run.budget.record_step(tokens_used=tokens_used)

        # Run action logic if provided
        step_result = "Action recorded"
        if executor_fn is not None:
            try:
                step_result = executor_fn(action_payload or {})
            except Exception as exc:
                run.budget.record_retry()
                if run.budget.used_retries > run.budget.max_retries:
                    run.transition_to(
                        AgentState.FAILED,
                        description=f"Step action '{action_name}' failed and retries exhausted: {exc}",
                    )
                    return run
                run._add_event(
                    event_type="STEP_RETRY",
                    state_from=AgentState.EXECUTING,
                    state_to=AgentState.EXECUTING,
                    description=f"Action '{action_name}' failed ({exc}). Retrying ({run.budget.used_retries}/{run.budget.max_retries}).",
                )
                return run

        run._add_event(
            event_type="STEP_EXECUTED",
            state_from=AgentState.EXECUTING,
            state_to=AgentState.EXECUTING,
            description=f"Executed action '{action_name}': {step_result[:100]}",
            metadata={"action": action_name, "result": step_result},
        )

        # Loop detection check after recording event
        if run.check_loop():
            run.transition_to(
                AgentState.FAILED,
                description="Execution loop detected: identical actions repeated multiple times.",
            )
            return run

        return run

    def approve_step(
        self,
        run: AgentRun,
        executor_fn: Callable[[dict[str, Any]], str] | None = None,
    ) -> AgentRun:
        if run.current_state != AgentState.WAITING_APPROVAL or not run.pending_approval:
            raise ValueError("Run is not currently waiting for approval.")

        approval_info = run.pending_approval
        action_name = str(approval_info.get("action", "approved_action"))
        payload = dict(approval_info.get("payload", {}))  # type: ignore[arg-type]
        run.pending_approval = None

        run.transition_to(
            AgentState.EXECUTING,
            description=f"Action '{action_name}' approved by user.",
        )

        run.budget.record_step()

        step_result = "Approved action executed"
        if executor_fn is not None:
            try:
                step_result = executor_fn(payload)
            except Exception as exc:
                run.transition_to(
                    AgentState.FAILED,
                    description=f"Approved action '{action_name}' failed execution: {exc}",
                )
                return run

        run._add_event(
            event_type="STEP_EXECUTED",
            state_from=AgentState.EXECUTING,
            state_to=AgentState.EXECUTING,
            description=f"Executed approved action '{action_name}': {step_result[:100]}",
            metadata={"action": action_name, "result": step_result},
        )
        return run

    def deny_step(self, run: AgentRun, reason: str = "User denied action") -> AgentRun:
        if run.current_state != AgentState.WAITING_APPROVAL:
            raise ValueError("Run is not currently waiting for approval.")

        run.pending_approval = None
        run.transition_to(
            AgentState.DENIED,
            description=f"Action denied: {reason}",
        )
        return run

    def handoff(
        self,
        run: AgentRun,
        target_role: AgentRole,
        reason: str,
        payload: dict[str, Any] | None = None,
    ) -> AgentRun:
        if run.current_state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.DENIED,
            AgentState.TIMEOUT,
        ):
            raise ValueError(f"Cannot perform handoff on terminal state {run.current_state}")

        run.record_handoff(target_role=target_role, reason=reason, payload=payload)
        return run

    def complete_run(self, run: AgentRun, result: str) -> AgentRun:
        if run.current_state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.DENIED,
            AgentState.TIMEOUT,
        ):
            raise ValueError(f"Cannot complete run in terminal state {run.current_state}")

        run.transition_to(AgentState.VERIFYING, description="Verifying run final outputs")
        run.result = result
        run.transition_to(AgentState.COMPLETED, description="Run completed successfully")
        return run

    def cancel_run(self, run: AgentRun, reason: str = "User cancelled run") -> AgentRun:
        if run.current_state in (
            AgentState.COMPLETED,
            AgentState.FAILED,
            AgentState.CANCELLED,
            AgentState.DENIED,
            AgentState.TIMEOUT,
        ):
            return run

        run.transition_to(AgentState.CANCELLED, description=f"Run cancelled: {reason}")
        return run
