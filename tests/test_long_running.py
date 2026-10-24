from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from chad.agent import (
    AgentRole,
    AgentScheduler,
    CheckpointStatus,
    CostReliabilityPlanner,
    DurableTaskQueue,
    HumanCheckpointEngine,
    MultiAgentDelegator,
    TaskStatus,
)


def test_durable_task_queue_basic(tmp_path):
    persistence_file = tmp_path / "tasks.json"
    queue = DurableTaskQueue(persistence_path=persistence_file)

    # Enqueue tasks with different priorities
    t1 = queue.enqueue("Task low priority", priority=1)
    t2 = queue.enqueue("Task high priority", priority=10)

    assert len(queue.list_tasks()) == 2
    assert t1.status == TaskStatus.PENDING
    assert t2.status == TaskStatus.PENDING

    # Dequeue should return higher priority task
    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.task_id == t2.task_id
    assert dequeued.status == TaskStatus.RUNNING

    # Pause and cancel
    queue.pause_task(t1.task_id)
    assert queue.get_task(t1.task_id).status == TaskStatus.PAUSED

    queue.cancel_task(t1.task_id, reason="Testing cancellation")
    assert queue.get_task(t1.task_id).status == TaskStatus.CANCELLED
    assert queue.get_task(t1.task_id).error == "Testing cancellation"

    # Verify persistence
    queue2 = DurableTaskQueue(persistence_path=persistence_file)
    assert len(queue2.list_tasks()) == 2
    assert queue2.get_task(t1.task_id).status == TaskStatus.CANCELLED


def test_durable_task_queue_resume_run(tmp_path):
    persistence_file = tmp_path / "tasks.json"
    queue = DurableTaskQueue(persistence_path=persistence_file)

    task = queue.enqueue("Analyze codebase", role=AgentRole.ANALYST)
    run = queue.resume_run(task.task_id)

    assert run.goal == "Analyze codebase"
    assert run.current_role == AgentRole.ANALYST
    assert queue.get_task(task.task_id).status == TaskStatus.RUNNING


def test_agent_scheduler(tmp_path):
    queue = DurableTaskQueue(persistence_path=tmp_path / "sched_tasks.json")
    scheduler = AgentScheduler(queue=queue)

    now = datetime.now(UTC)

    # Interval task due immediately
    sched1 = scheduler.schedule_task(
        goal="Recurring research",
        role=AgentRole.RESEARCHER,
        interval_seconds=60.0,
    )

    # Future scheduled task
    future_time = now + timedelta(hours=1)
    sched2 = scheduler.schedule_task(
        goal="Future audit",
        role=AgentRole.CODER,
        scheduled_at=future_time,
    )

    assert scheduler._schedules[sched2.schedule_id].goal == "Future audit"

    due_tasks = scheduler.get_due_tasks(now=now)
    assert len(due_tasks) == 1
    assert due_tasks[0].schedule_id == sched1.schedule_id

    # Trigger due tasks
    enqueued = scheduler.trigger_due_tasks(now=now)
    assert len(enqueued) == 1
    assert enqueued[0].goal == "Recurring research"

    # Disabling schedule
    scheduler.disable_schedule(sched1.schedule_id)
    assert len(scheduler.get_due_tasks(now=now + timedelta(seconds=120))) == 0

    scheduler.enable_schedule(sched1.schedule_id)
    assert len(scheduler.get_due_tasks(now=now + timedelta(seconds=120))) == 1


def test_human_checkpoint_engine():
    engine = HumanCheckpointEngine()

    cp1 = engine.register_checkpoint(run_id="run_123", action_name="write_file", timeout_seconds=10.0)
    cp2 = engine.register_checkpoint(run_id="run_123", action_name="execute_code", timeout_seconds=5.0)

    assert cp1.status == CheckpointStatus.PENDING

    # Approve cp1
    approved = engine.approve_checkpoint(cp1.checkpoint_id, reason="User confirmed")
    assert approved.status == CheckpointStatus.APPROVED
    assert approved.reason == "User confirmed"

    # Deny cp2
    denied = engine.deny_checkpoint(cp2.checkpoint_id, reason="Untrusted path")
    assert denied.status == CheckpointStatus.DENIED

    # Timeout check
    cp3 = engine.register_checkpoint(run_id="run_456", action_name="deploy", timeout_seconds=2.0)
    future_time = datetime.fromisoformat(cp3.created_at) + timedelta(seconds=10)
    timed_out_list = engine.evaluate_timeouts(current_time=future_time)

    assert len(timed_out_list) == 1
    assert timed_out_list[0].checkpoint_id == cp3.checkpoint_id
    assert cp3.status == CheckpointStatus.TIMED_OUT


def test_multi_agent_delegator():
    from chad.agent import AgentOrchestrator, AgentState

    orch = AgentOrchestrator()
    parent_run = orch.start_run("Parent complex task")
    delegator = MultiAgentDelegator(orchestrator=orch)

    res = delegator.delegate_subtask(
        parent_run=parent_run,
        target_role=AgentRole.RESEARCHER,
        sub_goal="Gather background information",
        executor_fn=lambda payload: "Research evidence collected",
    )

    assert res.role == AgentRole.RESEARCHER
    assert res.status == AgentState.COMPLETED
    assert res.result == "Sub-task completed for role researcher"


def test_cost_reliability_planner():
    planner = CostReliabilityPlanner()

    strategies = planner.evaluate_strategies(
        goal="Audit codebase security",
        max_cost_budget=0.10,
        min_reliability=0.8,
    )

    assert len(strategies) > 0
    # Higher tradeoff_score should come first
    assert strategies[0].tradeoff_score >= strategies[-1].tradeoff_score

    best = planner.select_best_strategy(
        goal="Audit codebase security",
        max_cost_budget=0.10,
        min_reliability=0.8,
    )
    assert best.estimated_cost_usd <= 0.10
    assert best.reliability_score >= 0.8

    # Budget too low raises ValueError
    with pytest.raises(ValueError, match="No strategy available"):
        planner.select_best_strategy(goal="Impossible budget", max_cost_budget=0.0001)
