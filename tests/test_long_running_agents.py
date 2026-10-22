from __future__ import annotations

from datetime import UTC, datetime, timedelta

from chad.agent import (
    AgentOrchestrator,
    AgentRole,
    AgentScheduler,
    AgentState,
    CostReliabilityPlanner,
    DurableTaskQueue,
    HumanCheckpointEngine,
    MultiAgentDelegator,
    TaskPriority,
    TaskStatus,
)


def test_durable_task_queue_operations(tmp_path) -> None:
    db_file = tmp_path / "queue.json"
    queue = DurableTaskQueue(storage_path=db_file)

    task1 = queue.enqueue(
        goal="Low priority task",
        role=AgentRole.RESEARCHER,
        priority=TaskPriority.LOW,
    )
    task2 = queue.enqueue(
        goal="High priority task",
        role=AgentRole.CODER,
        priority=TaskPriority.HIGH,
    )

    assert task1.status == TaskStatus.PENDING
    assert task2.status == TaskStatus.PENDING

    # Dequeue should pick highest priority task first
    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.task_id == task2.task_id
    assert dequeued.status == TaskStatus.RUNNING

    # Pause and resume operations
    queue.pause_task(task1.task_id, reason="Hold for review")
    assert queue.get_task(task1.task_id).status == TaskStatus.PAUSED

    queue.resume_task(task1.task_id)
    assert queue.get_task(task1.task_id).status == TaskStatus.PENDING

    # Complete task
    completed = queue.complete_task(task2.task_id, result="Code patch ready")
    assert completed.status == TaskStatus.COMPLETED
    assert completed.result == "Code patch ready"

    # Persistence verification across queue instances
    queue_reloaded = DurableTaskQueue(storage_path=db_file)
    assert queue_reloaded.get_task(task2.task_id).status == TaskStatus.COMPLETED


def test_durable_task_queue_failure_and_cancellation() -> None:
    queue = DurableTaskQueue()
    task = queue.enqueue(goal="Failing task", priority=TaskPriority.NORMAL)

    # Fail attempt 1 and 2 (retries remaining)
    queue.fail_task(task.task_id, error="Transient network error")
    assert task.status == TaskStatus.PENDING
    assert task.retries_left == 2

    queue.fail_task(task.task_id, error="Transient error 2")
    assert task.status == TaskStatus.PENDING
    assert task.retries_left == 1

    # Fail attempt 3 (exhausted)
    queue.fail_task(task.task_id, error="Fatal error")
    assert task.status == TaskStatus.FAILED
    assert task.retries_left == 0

    # Cancel task
    task2 = queue.enqueue(goal="Cancelled task")
    queue.cancel_task(task2.task_id, reason="User abort")
    assert task2.status == TaskStatus.CANCELLED


def test_agent_scheduler(tmp_path) -> None:
    queue = DurableTaskQueue(storage_path=tmp_path / "sched_queue.json")
    scheduler = AgentScheduler(queue=queue)

    past_time = datetime.now(UTC) - timedelta(minutes=5)
    future_time = datetime.now(UTC) + timedelta(hours=1)

    due_task = scheduler.schedule_task(
        goal="Overdue task",
        run_at=past_time,
        priority=TaskPriority.HIGH,
    )
    upcoming_task = scheduler.schedule_task(
        goal="Future task",
        run_at=future_time,
        priority=TaskPriority.NORMAL,
    )

    assert due_task.status == TaskStatus.SCHEDULED
    assert upcoming_task.status == TaskStatus.SCHEDULED

    due_list = scheduler.poll_due_tasks()
    assert len(due_list) == 1
    assert due_list[0].task_id == due_task.task_id
    assert due_task.status == TaskStatus.PENDING


def test_agent_scheduler_recurring(tmp_path) -> None:
    queue = DurableTaskQueue(storage_path=tmp_path / "rec_queue.json")
    scheduler = AgentScheduler(queue=queue)

    scheduler.schedule_recurring(
        goal="Periodic health check",
        interval_seconds=60.0,
        priority=TaskPriority.NORMAL,
    )

    # Force the scheduled task to past time to simulate poll
    task = queue.list_tasks()[0]
    task.scheduled_at = (datetime.now(UTC) - timedelta(seconds=5)).isoformat()

    due = scheduler.poll_due_tasks()
    assert len(due) == 1

    # Polling recurring task should automatically schedule the next occurrence
    all_tasks = queue.list_tasks()
    assert len(all_tasks) == 2


def test_human_checkpoint_engine(tmp_path) -> None:
    ckpt_file = tmp_path / "checkpoints.json"
    engine = HumanCheckpointEngine(storage_path=ckpt_file)
    orchestrator = AgentOrchestrator()

    run = orchestrator.start_run(goal="Deploy to production environment", role=AgentRole.CODER)

    checkpoint = engine.create_checkpoint(
        run=run,
        reason="Production deployment approval required",
        prompt="Do you approve deploying commit hash abc1234?",
    )

    assert run.current_state == AgentState.WAITING_APPROVAL
    assert checkpoint.status == "PENDING"
    assert checkpoint.run_id == run.run_id

    # Resolve approval
    engine.resolve_checkpoint(
        checkpoint_id=checkpoint.checkpoint_id,
        approved=True,
        human_input="Approved by DevOps lead",
        orchestrator=orchestrator,
        run=run,
    )

    assert checkpoint.status == "APPROVED"
    assert checkpoint.human_input == "Approved by DevOps lead"
    assert run.current_state == AgentState.EXECUTING

    # Reload persistence test
    engine_reloaded = HumanCheckpointEngine(storage_path=ckpt_file)
    assert engine_reloaded.get_checkpoint(checkpoint.checkpoint_id).status == "APPROVED"


def test_multi_agent_delegator() -> None:
    orchestrator = AgentOrchestrator()
    delegator = MultiAgentDelegator(orchestrator=orchestrator)

    parent_run = orchestrator.start_run(goal="Full system analysis and refactoring", role=AgentRole.ORCHESTRATOR)

    subtasks = [
        {"goal": "Research security advisories", "role": AgentRole.RESEARCHER},
        {"goal": "Refactor database models", "role": AgentRole.CODER},
        {"goal": "Analyze query latency data", "role": AgentRole.ANALYST},
    ]

    nodes = delegator.delegate_subtasks(parent_run=parent_run, subtasks=subtasks)
    assert len(nodes) == 3
    assert len(parent_run.handoffs) == 3

    # Execute delegation
    executor_map = {
        AgentRole.RESEARCHER: lambda g: f"Found 0 vulnerabilities for: {g}",
        AgentRole.CODER: lambda g: "Models refactored with clean migration",
        AgentRole.ANALYST: lambda g: "p95 latency reduced by 15ms",
    }

    results = delegator.execute_delegation(
        parent_run=parent_run,
        subtask_nodes=nodes,
        executor_map=executor_map,
    )

    assert len(results) == 3
    assert all(n.status == AgentState.COMPLETED for n in nodes)
    assert "Found 0 vulnerabilities" in results[nodes[0].subtask_id]


def test_cost_reliability_planner() -> None:
    planner = CostReliabilityPlanner()

    plan = planner.plan_execution(
        goal="Analyze large dataset",
        max_cost_budget=0.01,
        required_reliability=0.90,
    )

    assert plan["primary_model"] in ("lapis_local", "gpt-4o-mini")
    assert plan["estimated_cost"] <= 0.01
    assert "max_retries" in plan
    assert "strategy" in plan

    # Record successful outcome and verify reliability updates
    old_rel = planner.provider_reliability["lapis_local"]
    planner.record_outcome(provider_or_model="lapis_local", success=True)
    assert planner.provider_reliability["lapis_local"] >= old_rel

    # Record failure outcome
    planner.record_outcome(provider_or_model="lapis_local", success=False)
    assert planner.provider_reliability["lapis_local"] < 1.0
