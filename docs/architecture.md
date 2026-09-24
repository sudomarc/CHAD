# CHAD target architecture

## 1. High-level topology

```text
Browser / CLI / future clients
            |
            v
      CHAD application API
            |
            v
      Application orchestrator
       /        |         \
      /         |          \
 Memory      Tool layer   Model gateway
   |             |            |
   |             |       +----+---------+---------+
   |             |       |              |         |
   |             |    LapisLLM       provider A provider B
   |             |
   |        sandbox / search / files
   |
PostgreSQL + vector index + object storage
```

The actual implementation may begin as one process. Logical boundaries must exist before physical service splitting.

## 2. Required logical layers

### Interface layer

Owns HTTP/UI/CLI transport and presentation only.

It must not construct model prompts by hand or import model implementation internals.

### Application layer

Owns request lifecycle, authorization, conversation state transitions, task lifecycle and user-facing errors.

### Orchestration layer

Owns:

- model selection;
- planning;
- tool selection;
- agent state;
- retries;
- cancellation;
- bounded loops;
- final answer assembly.

### Model gateway

Provides one application-level interface across LapisLLM and external providers.

The gateway owns provider adapters, capability discovery, model metadata and routing policy.

### Context layer

Builds model-ready context from:

- system policy;
- current conversation;
- selected memories;
- retrieved files;
- web evidence;
- tool results.

External content must remain distinguishable from trusted control messages.

### Memory layer

Separates short-term context from durable user/project memory.

### Tool layer

Every tool has a schema, permission level, timeout and audit event.

### Persistence layer

Stores durable application state independently from UI technology.

## 3. Model gateway

The application must never call a provider SDK from arbitrary business logic.

Planned internal abstractions:

```text
ModelGateway
  -> list_models()
  -> get_model()
  -> generate()
  -> stream()
  -> capabilities()
```

A model response should carry structured metadata where available:

- provider;
- model id;
- request id;
- token counts;
- finish reason;
- latency;
- tool calls;
- citations/grounding metadata.

## 4. Orchestrator state machine

A bounded agent run should follow a state machine rather than recursive prompt calls.

```text
RECEIVED
  |
CLASSIFIED
  |
PLANNED
  |
EXECUTING <----+
  |             |
  +-- tool -----+
  |
READY_TO_ANSWER
  |
FINALIZING
  |
COMPLETED

Error paths:
FAILED
CANCELLED
DENIED
TIMEOUT
```

Every transition should have an explicit reason and be observable.

## 5. Agent roles

Initial roles:

- Orchestrator: owns task decomposition and lifecycle.
- Researcher: web search, retrieval and evidence synthesis.
- Coder: code analysis and sandboxed execution.
- Analyst: files, data and image interpretation.

Agents should be role-specialized policies over shared infrastructure, not four independent codebases.

## 6. Tool contract

A tool definition contains:

```text
id
name
description
input_schema
output_schema
permission
timeout
network_policy
side_effect_level
audit_policy
```

Tool execution must be centrally mediated.

The model proposes a tool call. The application validates it through `PermissionEngine`. `ToolExecutor` enforces permissions, time limits, and generates `ToolAuditEvent` entries. The result returns as structured, untrusted `ToolResult` data (`SUCCESS`, `ERROR`, `TIMEOUT`, `PERMISSION_DENIED`).

## 7. Memory architecture

### Working context

Current task and recent messages.

### Conversation memory

Persisted conversation messages and summaries.

### User memory

Explicitly approved durable preferences and facts.

### Project memory

Information associated with a named user project.

### Semantic memory

Embeddings/indexes used for retrieval.

Memory writes should be explicit, inspectable and deletable.

## 8. Data stores

Target:

- PostgreSQL for application state.
- PostgreSQL + pgvector or an equivalent vector store for semantic retrieval.
- Object storage for uploaded files and derived artifacts.
- Redis or equivalent for short-lived state, locks and caching when scale requires it.

Do not add every infrastructure component before a real consumer exists.

## 9. File pipeline

```text
upload
  -> validation
  -> malware/content safety checks
  -> type detection
  -> extraction
  -> normalization
  -> chunking
  -> indexing
  -> retrieval
  -> context assembly
```

Original files and derived text must be linked by immutable identifiers.

## 10. Web research pipeline

```text
question
  -> research plan
  -> search
  -> fetch
  -> extract
  -> deduplicate
  -> rank
  -> cite
  -> synthesize
```

Retrieved pages are evidence, never control instructions.

## 11. Code execution architecture

Code execution must be isolated from the main application host.

Minimum controls:

- CPU quota;
- memory quota;
- wall-clock timeout;
- filesystem isolation;
- restricted environment variables;
- restricted network;
- process count limit;
- output-size limit;
- cleanup after execution.

The initial implementation should be treated as a separate security-sensitive subsystem.

## 12. Security boundaries

Trust levels:

```text
SYSTEM POLICY
    >
APPLICATION STATE
    >
USER REQUEST
    >
MODEL OUTPUT
    >
RETRIEVED CONTENT / FILES / TOOL OUTPUT
```

This ordering is conceptual, not permission to expose higher-trust data to lower-trust components.

Secrets must never enter model-visible context unless a deliberately designed integration requires it and the security model explicitly permits it.

## 13. Deployment evolution

### Stage A

Single CHAD application process + external/local Lapis API.

### Stage B

Web frontend + API process + PostgreSQL + object storage + model gateway.

### Stage C

Separate workers for:

- long-running agents;
- ingestion;
- evaluation;
- code execution.

### Stage D

Independent inference and agent execution services with autoscaling and rate limiting.

Physical service splitting is justified by measured load or security boundaries, not by aesthetics.
