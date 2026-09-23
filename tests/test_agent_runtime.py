from __future__ import annotations

import pytest

from chad.agent import (
    AgentEvent,
    AgentHandoff,
    AgentOrchestrator,
    AgentRegistry,
    AgentRole,
    AgentRoleContract,
    AgentRun,
    AgentState,
    ExecutionBudget,
)


def test_agent_state_enum_and_terminal_states() -> None:
    assert AgentState.RECEIVED == "RECEIVED"
    assert AgentState.COMPLETED == "COMPLETED"
    assert AgentRole.ORCHESTRATOR == "orchestrator"
    assert AgentRole.CODER == "coder"


def test_agent_run_initialization_and_validation() -> None:
    with pytest.raises(ValueError, match="goal cannot be empty"):
        AgentRun(goal="  ")

    run = AgentRun(goal="Implement agent runtime")
    assert run.goal == "Implement agent runtime"
    assert run.current_role == AgentRole.ORCHESTRATOR
    assert run.current_state == AgentState.RECEIVED
    assert len(run.events) == 1
    assert run.events[0].event_type == "RUN_CREATED"


def test_agent_state_transitions() -> None:
    run = AgentRun(goal="Test transitions")
    run.transition_to(AgentState.CLASSIFIED, description="Classified goal")
    assert run.current_state == AgentState.CLASSIFIED

    run.transition_to(AgentState.PLANNED, description="Planned steps")
    assert run.current_state == AgentState.PLANNED

    run.transition_to(AgentState.COMPLETED, description="Finished")

    with pytest.raises(ValueError, match="Cannot transition from terminal state"):
        run.transition_to(AgentState.EXECUTING, description="Reopen")


def test_execution_budget_limits() -> None:
    budget = ExecutionBudget(max_steps=3, max_tokens=1000, max_retries=1, max_time_seconds=60.0)
    assert budget.is_exceeded() == (False, None)

    budget.record_step(tokens_used=500)
    assert budget.used_steps == 1
    assert budget.used_tokens == 500
    assert budget.is_exceeded() == (False, None)

    budget.record_step(tokens_used=600)
    assert budget.used_tokens == 1100
    exceeded, reason = budget.is_exceeded()
    assert exceeded is True
    assert "Token limit reached" in (reason or "")

    budget_step = ExecutionBudget(max_steps=2)
    budget_step.record_step()
    budget_step.record_step()
    exceeded_step, reason_step = budget_step.is_exceeded()
    assert exceeded_step is True
    assert "Step limit reached" in (reason_step or "")


def test_agent_registry() -> None:
    registry = AgentRegistry()
    orchestrator_contract = registry.get(AgentRole.ORCHESTRATOR)
    assert orchestrator_contract.role == AgentRole.ORCHESTRATOR
    assert "synthesize_results" in orchestrator_contract.permitted_tools

    coder_contract = registry.get(AgentRole.CODER)
    assert coder_contract.role == AgentRole.CODER
    assert "write_file" in coder_contract.requires_approval_actions

    custom_contract = AgentRoleContract(
        role=AgentRole.RESEARCHER,
        name="Custom Researcher",
        description="Custom research agent",
        system_instructions="Search web",
    )
    registry.register(custom_contract)
    assert registry.get(AgentRole.RESEARCHER).name == "Custom Researcher"

    with pytest.raises(KeyError, match="not registered"):
        registry.get("invalid_role")  # type: ignore[arg-type]


def test_orchestrator_start_run() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Research AI trends", role=AgentRole.RESEARCHER)

    assert run.current_role == AgentRole.RESEARCHER
    assert run.current_state == AgentState.PLANNED
    assert len(run.events) == 3  # CREATED, CLASSIFIED, PLANNED


def test_orchestrator_execute_step_and_completion() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Simple calculation")

    orchestrator.execute_step(
        run,
        action_name="delegate_task",
        action_payload={"task": "add 2+2"},
        tokens_used=50,
        executor_fn=lambda payload: "Result: 4",
    )

    assert run.current_state == AgentState.EXECUTING
    assert run.budget.used_steps == 1
    assert run.budget.used_tokens == 50

    orchestrator.complete_run(run, result="The calculation output is 4")
    assert run.current_state == AgentState.COMPLETED
    assert run.result == "The calculation output is 4"


def test_orchestrator_approval_checkpoint_workflow() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Fix bug in code", role=AgentRole.CODER)

    # Action requires approval for Coder role (write_file)
    orchestrator.execute_step(
        run,
        action_name="write_file",
        action_payload={"filepath": "main.py", "content": "print('hello')"},
    )

    assert run.current_state == AgentState.WAITING_APPROVAL
    assert run.pending_approval is not None
    assert run.pending_approval["action"] == "write_file"

    # Try executing another step while waiting for approval
    with pytest.raises(ValueError, match="waiting for user approval"):
        orchestrator.execute_step(run, action_name="git_status")

    # Approve step
    orchestrator.approve_step(
        run,
        executor_fn=lambda payload: f"Wrote file {payload['filepath']}",
    )
    assert run.current_state == AgentState.EXECUTING
    assert run.pending_approval is None


def test_orchestrator_deny_approval() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Delete file", role=AgentRole.CODER)

    orchestrator.execute_step(
        run,
        action_name="write_file",
        action_payload={"filepath": "important.py"},
    )
    assert run.current_state == AgentState.WAITING_APPROVAL

    orchestrator.deny_step(run, reason="Unsafe operation")
    assert run.current_state == AgentState.DENIED


def test_orchestrator_loop_detection() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Infinite loop goal")

    # Trigger repeated identical execution steps
    for _ in range(3):
        orchestrator.execute_step(run, action_name="delegate_task", action_payload={})

    assert run.current_state == AgentState.FAILED
    assert "loop detected" in run.events[-1].description.lower()


def test_orchestrator_handoff() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Multi-disciplinary goal")

    orchestrator.handoff(
        run,
        target_role=AgentRole.CODER,
        reason="Need code modifications",
        payload={"task": "Write test cases"},
    )

    assert run.current_role == AgentRole.CODER
    assert len(run.handoffs) == 1
    assert isinstance(run.handoffs[0], AgentHandoff)
    assert run.handoffs[0].from_role == AgentRole.ORCHESTRATOR
    assert run.handoffs[0].to_role == AgentRole.CODER


def test_agent_run_and_event_serialization_roundtrip() -> None:
    orchestrator = AgentOrchestrator()
    run = orchestrator.start_run(goal="Serialization test", role=AgentRole.RESEARCHER)
    orchestrator.execute_step(run, action_name="web_search", action_payload={"query": "python"})
    orchestrator.handoff(run, target_role=AgentRole.ANALYST, reason="Data analysis needed")

    serialized = run.to_dict()
    deserialized = AgentRun.from_dict(serialized)

    assert deserialized.run_id == run.run_id
    assert deserialized.goal == run.goal
    assert deserialized.current_role == AgentRole.ANALYST
    assert deserialized.current_state == run.current_state
    assert deserialized.budget.used_steps == run.budget.used_steps
    assert len(deserialized.events) == len(run.events)
    assert isinstance(deserialized.events[0], AgentEvent)
    assert len(deserialized.handoffs) == len(run.handoffs)
    assert isinstance(deserialized.handoffs[0], AgentHandoff)
    assert deserialized.handoffs[0].from_role == AgentRole.RESEARCHER
    assert deserialized.handoffs[0].to_role == AgentRole.ANALYST
