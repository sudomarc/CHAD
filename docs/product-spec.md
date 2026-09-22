# CHAD product specification

## 1. Product identity

**Product:** CHAD

**Purpose:** a general-purpose agentic AI system that can converse, reason, research, analyze files, use tools, delegate bounded work to specialist agents, and execute multi-step tasks under explicit policy and resource limits.

**Engine relationship:** CHAD consumes LapisLLM through a stable application/runtime boundary and may also consume other model providers through a provider-neutral gateway.

## 2. Vision

CHAD should become a serious AI assistant rather than a thin chat wrapper.

The product is successful when a user can give a complex request without manually deciding which model, tool, retrieval strategy, or agent should execute each step.

The product should optimize for:

1. useful outcomes;
2. correctness and evidence;
3. reliable tool execution;
4. controllable autonomy;
5. understandable behavior;
6. reasonable cost and latency.

## 3. Product principles

### Model-agnostic

CHAD must not be architecturally coupled to one provider or one model family.

### Evidence-aware

Web and retrieved content are data. They do not override system policy, application state, or tool permissions.

### Tool-first, not prompt-only

Capabilities such as search, file analysis and code execution must be represented as explicit tools with schemas, permissions, timeouts and auditability.

### Human-controlled autonomy

The agent may plan and execute bounded work, but risky external actions require explicit authorization.

### Observable by design

Each model call and tool call should be traceable without exposing secrets.

### Progressive independence

CHAD may use high-quality external models while LapisLLM develops toward stronger proprietary instruction, tool-use and reasoning capabilities.

## 4. V1 user experience

V1 is an agent-runtime product with conversation as the primary interface and a provider-neutral AI gateway underneath.

### Core interactions

- Create a conversation.
- Send and receive messages.
- Stream generated text when the selected backend supports real streaming.
- Stop an in-progress generation.
- Regenerate an answer.
- Edit a user message and branch or continue from the edited state.
- Rename, archive, reopen and delete conversations.
- Select an available model.
- Configure safe generation defaults.
- Upload supported files.
- Inspect tool activity and cited sources.
- Provide positive/negative feedback on a response.

### V1 agent behavior

The orchestrator is the default execution path for tasks that require more than a single model response. It decides whether a request is best handled directly or delegated to a specialist agent.

Specialists operate under explicit role, tool, permission and budget contracts. The runtime records each step and distinguishes model output, tool results, retrieved evidence and external side effects.

### V1 task classes

- General question answering.
- Summarization and rewriting.
- Coding assistance.
- Document analysis.
- Basic web research.
- Image understanding when a compatible model is configured.

### V1 non-goals

- Fully autonomous financial transactions.
- Sending messages or emails without explicit authorization.
- Arbitrary host-level code execution.
- Unbounded autonomous loops.
- Claims of frontier-model parity without reproducible evaluations.
- Moving consumer-product state into LapisLLM.

## 5. Capability matrix

| Capability | V1 | Later |
|---|---:|---:|
| Chat | Required | — |
| Streaming | Required where backend supports it | Better transport/fallbacks |
| Conversation history | Required | Shared/workspace history |
| Model switching | Required | Automatic routing policies |
| Web search | Required | Multi-source research plans |
| File upload | Required | Rich project workspaces |
| Vision | Required where supported | Multimodal agent workflows |
| Code analysis | Required | Sandboxed code agent |
| Code execution | Bounded beta | Hardened multi-runtime execution |
| Long-term memory | Controlled beta | Rich project/user memory |
| Multi-agent workflows | Required for bounded specialist tasks | Durable collaboration |
| Connectors | Minimal | GitHub, Notion, Drive, Slack, etc. |
| Voice | No | Planned |
| Image generation | No | Planned |
| Desktop/mobile | No | Planned |

## 6. User-visible safety model

Every potentially consequential action must communicate what will happen before execution when feasible.

The UI should distinguish:

- model generation;
- retrieved evidence;
- tool execution;
- external side effects;
- actions awaiting approval.

A refusal, permission denial, provider failure and tool failure are different states and should not be presented as the same generic error.

## 7. Success metrics

The project should not use one vanity metric.

Track:

- task success rate;
- factuality / citation correctness;
- tool-call success rate;
- agent completion rate;
- unsafe-action prevention rate;
- median and p95 latency;
- input/output token usage;
- cost per successful task;
- conversation retention for product studies;
- regression count per release.

Metrics must always identify the model, task set, date/version and evaluation methodology.

## 8. Product boundary

CHAD owns:

- users;
- sessions;
- conversations;
- memory;
- files;
- tools;
- agents;
- UX;
- model/provider selection;
- application policy;
- billing/quotas when introduced.

LapisLLM owns:

- model architecture;
- tokenization;
- training;
- checkpoints;
- inference runtime;
- model evaluation;
- serving primitives.

Dependency remains:

CHAD -> LapisLLM
