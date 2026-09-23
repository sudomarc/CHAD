from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chad.agent.state import AgentRole


@dataclass(frozen=True, slots=True)
class AgentRoleContract:
    role: AgentRole
    name: str
    description: str
    system_instructions: str
    permitted_tools: tuple[str, ...] = field(default_factory=tuple)
    requires_approval_actions: tuple[str, ...] = field(default_factory=tuple)
    max_steps: int = 20

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "name": self.name,
            "description": self.description,
            "system_instructions": self.system_instructions,
            "permitted_tools": list(self.permitted_tools),
            "requires_approval_actions": list(self.requires_approval_actions),
            "max_steps": self.max_steps,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentRoleContract:
        return cls(
            role=AgentRole(data["role"]),
            name=str(data["name"]),
            description=str(data["description"]),
            system_instructions=str(data["system_instructions"]),
            permitted_tools=tuple(data.get("permitted_tools", ())),
            requires_approval_actions=tuple(data.get("requires_approval_actions", ())),
            max_steps=int(data.get("max_steps", 20)),
        )


DEFAULT_ROLE_CONTRACTS: dict[AgentRole, AgentRoleContract] = {
    AgentRole.ORCHESTRATOR: AgentRoleContract(
        role=AgentRole.ORCHESTRATOR,
        name="Orchestrator",
        description="Coordinates overall multi-step tasks, specialist handoffs, and final synthesis.",
        system_instructions=(
            "You are the Orchestrator agent. Break down complex user goals into logical steps, "
            "delegate to specialist agents (Researcher, Coder, Analyst) when needed, "
            "and synthesize final results."
        ),
        permitted_tools=("delegate_task", "synthesize_results"),
        requires_approval_actions=(),
        max_steps=20,
    ),
    AgentRole.RESEARCHER: AgentRoleContract(
        role=AgentRole.RESEARCHER,
        name="Researcher",
        description="Performs web search, retrieval, source evaluation, and evidence synthesis.",
        system_instructions=(
            "You are the Researcher agent. Search for accurate information, evaluate source reliability, "
            "synthesize evidence with explicit citations, and report uncertainties."
        ),
        permitted_tools=("web_search", "fetch_page", "extract_evidence"),
        requires_approval_actions=(),
        max_steps=15,
    ),
    AgentRole.CODER: AgentRoleContract(
        role=AgentRole.CODER,
        name="Coder",
        description="Analyzes repositories, writes code, executes tests, and verifies changes safely.",
        system_instructions=(
            "You are the Coder agent. Follow strict Vibe coding policies, inspect code before modifying, "
            "verify all changes with tests, and ensure workspace safety."
        ),
        permitted_tools=("read_file", "write_file", "run_tests", "git_status"),
        requires_approval_actions=("write_file", "run_tests"),
        max_steps=25,
    ),
    AgentRole.ANALYST: AgentRoleContract(
        role=AgentRole.ANALYST,
        name="Analyst",
        description="Analyzes structured documents, datasets, images, and derived artifacts.",
        system_instructions=(
            "You are the Analyst agent. Analyze input documents, data tables, or structured inputs, "
            "extract key insights, verify logic, and generate actionable evidence-linked reports."
        ),
        permitted_tools=("parse_document", "analyze_data", "summarize_findings"),
        requires_approval_actions=(),
        max_steps=15,
    ),
}


class AgentRegistry:
    """Registry and role loader for CHAD agent roles."""

    def __init__(self) -> None:
        self._contracts: dict[AgentRole, AgentRoleContract] = dict(DEFAULT_ROLE_CONTRACTS)

    def register(self, contract: AgentRoleContract) -> None:
        self._contracts[contract.role] = contract

    def get(self, role: AgentRole | str) -> AgentRoleContract:
        try:
            role_enum = AgentRole(role) if isinstance(role, str) else role
        except ValueError as exc:
            raise KeyError(f"Role {role} is not registered in AgentRegistry") from exc

        if role_enum not in self._contracts:
            raise KeyError(f"Role {role} is not registered in AgentRegistry")
        return self._contracts[role_enum]

    def list_roles(self) -> list[AgentRoleContract]:
        return list(self._contracts.values())
