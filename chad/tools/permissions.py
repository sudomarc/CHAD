from __future__ import annotations

from dataclasses import dataclass, field

from chad.tools.schema import ToolDefinition, ToolPermissionLevel


@dataclass(slots=True)
class PermissionEngine:
    blocked_tools: set[str] = field(default_factory=set)
    user_approval_tools: set[str] = field(default_factory=set)

    def is_permitted(
        self,
        tool: ToolDefinition,
        user_role: str = "user",
        has_user_approval: bool = False,
    ) -> tuple[bool, str]:
        if tool.id in self.blocked_tools or tool.permission_level == ToolPermissionLevel.BLOCKED:
            return False, f"Tool '{tool.id}' is blocked by permission policy."

        if tool.permission_level == ToolPermissionLevel.ADMIN_ONLY and user_role != "admin":
            return False, f"Tool '{tool.id}' requires admin privileges."

        if (
            tool.permission_level == ToolPermissionLevel.USER_APPROVAL
            or tool.id in self.user_approval_tools
        ):
            if not has_user_approval:
                return (
                    False,
                    f"Tool '{tool.id}' requires explicit user approval before execution.",
                )

        return True, "Execution permitted."
