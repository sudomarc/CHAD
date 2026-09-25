CHAD roadmap

CHAD is the agentic application and runtime of the CHAD + LapisLLM + Vibe Coding Instructions ecosystem.

Phase 0 — Ecosystem foundation
- Define cross-repository compatibility matrix.
- Define release compatibility policy.
- Define shared contract-test fixtures.
- Reference Vibe role contracts from runtime configuration.

Phase 1 — Conversation kernel
- Stable message identity and timestamps.
- Context budgeting and validation.
- Message edits and branching.
- Regeneration.
- Archive/delete lifecycle.
- Summaries, correlation IDs, idempotency.

Phase 2 — Model Gateway
- Normalized gateway.
- Lapis adapter.
- External provider adapter.
- Model registry and capabilities.
- Usage/errors normalization.
- Streaming and cancellation.
- Health, fallback, cost/latency/privacy-aware routing.

Phase 3 — Agent runtime kernel (Completed)
- Agent registry and role loader (`AgentRegistry`, `AgentRoleContract`).
- Orchestrator state machine (`AgentOrchestrator`, `AgentState`).
- Step, token, time, and retry budgets (`ExecutionBudget`).
- Approval checkpoints (`WAITING_APPROVAL`, `approve_step`, `deny_step`).
- Loop detection (`check_loop`).
- Durable runs, handoffs, event log, resumption (`AgentRun`, `AgentEvent`, `AgentHandoff`).

Phase 4 — Tool platform (Completed)
- Tool registry and schemas (`ToolRegistry`, `ToolDefinition`).
- Permission engine (`PermissionEngine`, `ToolPermissionLevel`).
- Time/resource limits and execution engine (`ToolExecutor`).
- Audit events (`ToolAuditEvent`).
- Built-in tools: calculator, date/time, safe read file.
- Structured outputs and tool failure taxonomy (`ToolStatus`).

Phase 5 — Research agent (Completed)
- Search/fetch providers (`SearchProvider`, `FetchProvider`, `MockSearchProvider`, `MockFetchProvider`).
- Query decomposition (`QueryDecomposer`, `DecomposedQuery`).
- Evidence store (`EvidenceStore`, `EvidenceItem`).
- Ranking/deduplication (`get_ranked_evidence`, URL/hash deduplication).
- Contradiction detection (`detect_contradictions`).
- Citations and report synthesis (`ResearchReport`, `ResearchEngine`).
- Prompt-injection defenses (`sanitize_untrusted_content`).
- Research tools: `web_search`, `fetch_page`, `extract_evidence`.

Phase 6 — Files, knowledge and RAG
- Upload/storage/type validation.
- PDF/TXT/Markdown/DOCX/CSV/JSON/code extraction.
- Chunking.
- Embeddings and vector/hybrid retrieval.
- Source traceability.
- Retrieval evaluation and parser isolation.

Phase 7 — Multimodal runtime
- Image message contract.
- Vision adapters.
- Image validation/conversion.
- Mixed text/image context.
- Screenshot/diagram evaluation.

Phase 8 — Coder agent
- Repository workspace.
- Safe file operations and diffs.
- Test execution.
- Sandboxed code runtime.
- CPU/memory/time/network limits.
- Secret scanning and command policy.
- Vibe policy integration tests.

Phase 9 — Analyst agent
- Structured documents/data/images.
- Evidence-linked reports.
- Uncertainty reporting.
- Large-document workflows.

Phase 10 — Memory
- Working memory.
- Conversation summaries.
- User/project/semantic memory.
- Retrieval and conflict handling.
- User inspection/edit/delete.
- Retention/export/delete guarantees.

Phase 11 — Web product
- Next.js/React/TypeScript client.
- Chat/history/model/tool/source/file/agent-progress/approval UI.
- Accessibility, responsiveness, browser verification.

Phase 12 — Multi-user platform
- Authentication/authorization.
- Data ownership.
- Sessions.
- Rate/token/storage quotas.
- Account deletion and audit boundaries.

Phase 13 — Economics and observability
- Usage metering.
- Versioned provider pricing.
- Cost calculation and budgets.
- p50/p95 latency.
- Logs, tracing, metrics.
- Cost per verified success.

Phase 14 — Security
- Threat model.
- Prompt-injection and retrieval-poisoning tests.
- Tool permissions.
- Data exfiltration tests.
- Secret handling.
- Sandbox escape tests.
- Least privilege and abuse controls.

Phase 15 — Evaluation
- Versioned benchmark registry.
- General QA, reasoning, coding, math, research, tools, files, vision.
- French, English, multilingual, safety.
- Agent completion/recovery.
- Release gates and regression reports.

Phase 16 — External connectors
- GitHub, Notion, Drive, Slack, Calendar, Email.
- OAuth/scopes.
- Read/write separation.
- Side-effect confirmation.
- Revocation and health checks.

Phase 17 — Long-running agents
- Durable queues and background tasks.
- Resume after interruption.
- Scheduling.
- Human checkpoints.
- Multi-agent delegation.
- Cost/reliability-aware planning.

Phase 18 — Product maturity
- Projects/workspaces.
- Artifacts.
- Collaboration/sharing.
- Voice.
- Desktop/mobile.
- Rich canvas.
- Advanced multimodal workflows.

Cross-repository release gate: owning repository implements the capability, public contract is documented, dependents consume it through adapters, integration verification exists, security is reviewed, and material quality claims have evidence.
