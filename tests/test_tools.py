from __future__ import annotations

import time

import pytest

from chad.tools import (
    CALCULATOR_TOOL,
    FILE_READ_TOOL,
    PermissionEngine,
    ToolDefinition,
    ToolExecutor,
    ToolPermissionLevel,
    ToolRegistry,
    ToolStatus,
    register_builtin_tools,
    safe_calculator,
    safe_read_file,
)


def test_tool_definition_serialization():
    tool_dict = CALCULATOR_TOOL.to_dict()
    assert tool_dict["id"] == "calculator"
    assert tool_dict["permission_level"] == "ALWAYS_ALLOW"

    deserialized = ToolDefinition.from_dict(tool_dict)
    assert deserialized.id == CALCULATOR_TOOL.id
    assert deserialized.permission_level == CALCULATOR_TOOL.permission_level


def test_tool_registry():
    registry = ToolRegistry()
    assert not registry.is_registered("calculator")

    register_builtin_tools(registry)
    assert registry.is_registered("calculator")
    assert registry.is_registered("datetime_now")
    assert registry.is_registered("read_file")

    registered = registry.get("calculator")
    assert registered.definition.name == "Safe Calculator"

    with pytest.raises(ValueError, match="already registered"):
        register_builtin_tools(registry)

    with pytest.raises(KeyError):
        registry.get("non_existent_tool")


def test_permission_engine():
    engine = PermissionEngine()

    # ALWAYS_ALLOW
    permitted, reason = engine.is_permitted(CALCULATOR_TOOL)
    assert permitted

    # USER_APPROVAL required
    permitted, reason = engine.is_permitted(FILE_READ_TOOL, has_user_approval=False)
    assert not permitted
    assert "user approval" in reason

    permitted, reason = engine.is_permitted(FILE_READ_TOOL, has_user_approval=True)
    assert permitted

    # ADMIN_ONLY
    admin_tool = ToolDefinition(
        id="admin_tool",
        name="Admin Tool",
        description="Admin tool",
        input_schema={},
        permission_level=ToolPermissionLevel.ADMIN_ONLY,
    )
    permitted, reason = engine.is_permitted(admin_tool, user_role="user")
    assert not permitted
    assert "admin privileges" in reason

    permitted, reason = engine.is_permitted(admin_tool, user_role="admin")
    assert permitted

    # BLOCKED
    engine.blocked_tools.add("calculator")
    permitted, reason = engine.is_permitted(CALCULATOR_TOOL)
    assert not permitted


def test_tool_executor_success_and_audit():
    registry = ToolRegistry()
    register_builtin_tools(registry)
    executor = ToolExecutor(registry=registry)

    res = executor.execute("calculator", {"expression": "12 + 30 * 2"})
    assert res.status == ToolStatus.SUCCESS
    assert res.output == 72
    assert res.execution_time_seconds >= 0

    assert len(executor.audit_logs) == 1
    audit = executor.audit_logs[0]
    assert audit.tool_id == "calculator"
    assert audit.status == ToolStatus.SUCCESS
    assert audit.input_payload == {"expression": "12 + 30 * 2"}
    assert audit.output_payload == 72


def test_tool_executor_permission_denied():
    registry = ToolRegistry()
    register_builtin_tools(registry)
    executor = ToolExecutor(registry=registry)

    # Read file without user approval
    res = executor.execute("read_file", {"filepath": "AGENTS.md"}, has_user_approval=False)
    assert res.status == ToolStatus.PERMISSION_DENIED
    assert "user approval" in res.error

    # Audit log recorded
    assert len(executor.audit_logs) == 1
    assert executor.audit_logs[0].status == ToolStatus.PERMISSION_DENIED


def test_tool_executor_timeout():
    registry = ToolRegistry()

    def slow_func():
        time.sleep(0.5)
        return "done"

    slow_tool = ToolDefinition(
        id="slow_tool",
        name="Slow Tool",
        description="Slow tool",
        input_schema={},
        timeout_seconds=0.1,
    )
    registry.register(slow_tool, slow_func)
    executor = ToolExecutor(registry=registry)

    res = executor.execute("slow_tool", {})
    assert res.status == ToolStatus.TIMEOUT
    assert "timed out" in res.error


def test_builtin_tools(tmp_path):
    # Calculator
    assert safe_calculator("2 ** 3") == 8
    assert safe_calculator("-10 + 5") == -5
    with pytest.raises(ValueError, match="Invalid or unsafe math expression"):
        safe_calculator("__import__('os').system('ls')")

    # Read file
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello CHAD Tool Platform!", encoding="utf-8")

    content = safe_read_file(str(test_file))
    assert content == "Hello CHAD Tool Platform!"

    with pytest.raises(FileNotFoundError):
        safe_read_file(str(tmp_path / "non_existent.txt"))
