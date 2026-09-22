
# CHAD agent runtime

CHAD is a general-purpose bounded agent system, not a coding-only assistant.

## Execution loop

~~~text
REQUEST
  -> CLASSIFY
  -> PLAN
  -> AUTHORIZE
  -> EXECUTE
  -> VERIFY
  -> SYNTHESIZE
  -> COMPLETE
~~~

Each run has explicit step, token, time, retry and tool budgets.

## Initial roles

### Orchestrator
Coordinates planning, specialist selection, budgets, state transitions, evidence collection and final synthesis.

### Researcher
Performs web research and retrieval, preserves source mapping, detects conflicts and returns bounded evidence-backed synthesis.

### Coder
Performs repository work using the Vibe Coding Instructions engineering policy, isolated workspaces and real verification.

### Analyst
Analyzes documents, data and multimodal inputs with source traceability and explicit uncertainty.

Roles are policies over shared infrastructure, not separate applications.

## Tool model

The model proposes a tool call. CHAD validates the schema, checks permissions, applies limits, executes the tool, audits the event and returns the result as untrusted data.

No model output directly executes application code.

## Permission levels

READ
DRAFT
WRITE
EXECUTE
EXTERNAL_SIDE_EFFECT

Higher-risk levels require stronger controls and, when appropriate, explicit user approval.

## Run states

RECEIVED
CLASSIFIED
PLANNED
EXECUTING
WAITING_APPROVAL
VERIFYING
COMPLETED
FAILED
CANCELLED
DENIED
TIMEOUT

## Vibe Coding Instructions

The framework is the canonical source for evidence-driven planning, verification, security, token economy, specialist routing and controlled self-improvement.

CHAD owns the runtime adapter that executes those policies.

Canonical framework:
https://github.com/sudomarc/vibe-coding-instructions
