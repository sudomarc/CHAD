CHAD agent runtime

CHAD is a general-purpose bounded agent system, not a coding-only assistant.

Execution loop: REQUEST -> CLASSIFY -> PLAN -> AUTHORIZE -> EXECUTE -> VERIFY -> SYNTHESIZE -> COMPLETE.

Initial roles:
- Orchestrator: task decomposition, specialist selection, budgets, state, evidence, synthesis.
- Researcher: web research, retrieval, sources, conflicts, evidence-backed synthesis.
- Coder: repository work using Vibe Coding Instructions, isolated workspaces, and real verification.
- Analyst: document, data, and multimodal analysis with traceability.

Tool rule: the model proposes a tool call; CHAD validates schema and permissions, applies limits, executes, audits, and returns the result as untrusted data.

Permission vocabulary: READ, DRAFT, WRITE, EXECUTE, EXTERNAL_SIDE_EFFECT.

Agent states: RECEIVED, CLASSIFIED, PLANNED, EXECUTING, WAITING_APPROVAL, VERIFYING, COMPLETED, FAILED, CANCELLED, DENIED, TIMEOUT.

The Vibe Coding Instructions repository is the canonical source for planning, verification, security, token economy, specialist routing, and controlled self-improvement policy. CHAD owns the runtime adapter.
