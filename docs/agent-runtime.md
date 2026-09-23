# CHAD agent runtime

CHAD is a general-purpose bounded agent system, not a coding-only assistant.

## Execution loop

```text
REQUEST -> CLASSIFY -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> SYNTHESIZE -> COMPLETE
```

## Agent Kernel (`chad.agent`)

The Agent Runtime Kernel is implemented in `chad/agent/`:

- `state.py`: Defines core state models and enums:
  - `AgentState`: `RECEIVED`, `CLASSIFIED`, `PLANNED`, `EXECUTING`, `WAITING_APPROVAL`, `VERIFYING`, `COMPLETED`, `FAILED`, `CANCELLED`, `DENIED`, `TIMEOUT`.
  - `AgentRole`: `ORCHESTRATOR`, `RESEARCHER`, `CODER`, `ANALYST`.
  - `ExecutionBudget`: Tracks and enforces step limits, token consumption, retry budgets, and elapsed wall-clock time.
  - `AgentEvent` & `AgentHandoff`: Immutable audit events and role handoff records.
  - `AgentRun`: Durable run representation supporting serialization (`to_dict`/`from_dict`), loop detection (`check_loop`), and state machine transitions.

- `registry.py`: Defines `AgentRoleContract` and `AgentRegistry` to manage role definitions, default system instructions, permitted tools, and action approval policies for specialist agents.

- `orchestrator.py`: Implements `AgentOrchestrator` to manage agent runs:
  - Phase state transitions (classifying, planning, executing, verifying, completing/failing).
  - Step execution with budget enforcement and loop detection.
  - Human-in-the-loop approval checkpoints (`WAITING_APPROVAL`, `approve_step`, `deny_step`).
  - Cross-role handoffs between Orchestrator, Researcher, Coder, and Analyst agents.

## Initial Specialist Roles

- **Orchestrator**: Task decomposition, specialist selection, budgets, state, evidence, synthesis.
- **Researcher**: Web research, retrieval, sources, conflicts, evidence-backed synthesis.
- **Coder**: Repository work using Vibe Coding Instructions, isolated workspaces, and real verification.
- **Analyst**: Document, data, and multimodal analysis with traceability.

## Tool Execution & Safety

Tool rule: The model proposes a tool call; CHAD validates schema and permissions, applies limits, executes, audits, and returns the result as untrusted data.

Permission vocabulary: `READ`, `DRAFT`, `WRITE`, `EXECUTE`, `EXTERNAL_SIDE_EFFECT`.

Actions requiring user approval (such as `write_file` or `run_tests` for Coder) trigger approval checkpoints (`WAITING_APPROVAL`) prior to execution.

The Vibe Coding Instructions repository is the canonical source for planning, verification, security, token economy, specialist routing, and controlled self-improvement policy. CHAD owns the runtime adapter.
