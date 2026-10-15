from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any

from chad.tools.permissions import PermissionEngine
from chad.tools.registry import ToolRegistry
from chad.tools.schema import ToolAuditEvent, ToolResult, ToolStatus


@dataclass(slots=True)
class ToolExecutor:
    registry: ToolRegistry
    permission_engine: PermissionEngine = field(default_factory=PermissionEngine)
    audit_logs: list[ToolAuditEvent] = field(default_factory=list)

    def execute(
        self,
        tool_id: str,
        input_payload: dict[str, Any],
        user_role: str = "user",
        has_user_approval: bool = False,
        user_id: str | None = None,
    ) -> ToolResult:
        if not self.registry.is_registered(tool_id):
            res = ToolResult(
                tool_id=tool_id,
                status=ToolStatus.ERROR,
                error=f"Tool '{tool_id}' is not registered.",
            )
            self._record_audit(tool_id, "execute", res, input_payload, user_id)
            return res

        registered_tool = self.registry.get(tool_id)
        tool_def = registered_tool.definition

        permitted, reason = self.permission_engine.is_permitted(
            tool_def, user_role=user_role, has_user_approval=has_user_approval
        )
        if not permitted:
            res = ToolResult(
                tool_id=tool_id,
                status=ToolStatus.PERMISSION_DENIED,
                error=reason,
            )
            self._record_audit(tool_id, "execute", res, input_payload, user_id)
            return res

        start_time = time.time()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(registered_tool.handler, **input_payload)
                output = future.result(timeout=tool_def.timeout_seconds)
                elapsed = time.time() - start_time
                res = ToolResult(
                    tool_id=tool_id,
                    status=ToolStatus.SUCCESS,
                    output=output,
                    execution_time_seconds=elapsed,
                )
        except concurrent.futures.TimeoutError:
            elapsed = time.time() - start_time
            res = ToolResult(
                tool_id=tool_id,
                status=ToolStatus.TIMEOUT,
                error=f"Tool execution timed out after {tool_def.timeout_seconds} seconds.",
                execution_time_seconds=elapsed,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - start_time
            res = ToolResult(
                tool_id=tool_id,
                status=ToolStatus.ERROR,
                error=f"Tool execution failed: {exc}",
                execution_time_seconds=elapsed,
            )

        self._record_audit(tool_id, "execute", res, input_payload, user_id)
        return res

    def _record_audit(
        self,
        tool_id: str,
        action: str,
        result: ToolResult,
        input_payload: dict[str, Any],
        user_id: str | None,
    ) -> None:
        event = ToolAuditEvent(
            tool_id=tool_id,
            action=action,
            status=result.status,
            input_payload=input_payload,
            output_payload=result.output,
            error_message=result.error,
            user_id=user_id,
        )
        self.audit_logs.append(event)
