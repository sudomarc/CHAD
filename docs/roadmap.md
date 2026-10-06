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
- Normalized gateway (`ModelGateway`).
- Lapis adapter (`HttpLapisClient`, `LocalLapisClient`).
- External provider adapter (`ExternalProviderClient`).
- Model registry and capabilities (`ModelInfo`, `ModelCapabilities`).
- Usage/errors normalization (`UsageInfo`, `LLMError` hierarchy).
- Streaming and cancellation.
- Fallback routing.

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

Phase 6 — Files, knowledge and RAG (Completed)
- Upload/storage/type validation (`FileDocument`, `DocumentValidator`).
- PDF/TXT/Markdown/DOCX/CSV/JSON/code extraction (`DocumentExtractor`).
- Chunking with character/line position tracking (`TextChunker`, `DocumentChunk`).
- Embeddings, vector store, and hybrid retrieval (`VectorStore`, `MockEmbeddingProvider`, `HybridRetriever`).
- Source traceability and prompt-injection defense (`ChunkLocation`, `RAGSearchResult`, `RAGPipeline`).

Phase 7 — Multimodal runtime (Completed)
- Image message contract (`ImageFormat`, `ImageDetail`, `ImageAttachment`).
- Vision adapters and payload converters (`VisionAdapter`, `VisionPayloadConverter`).
- Image validation and conversion (`ImageValidator`, `ImageConverter`).
- Mixed text/image context token estimation (`estimate_image_tokens`, `estimate_message_tokens`, `ContextBudget`).
- Screenshot and diagram evaluation (`ScreenshotDiagramEvaluator`, `ImageAnalysisResult`).

Phase 8 — Coder agent (Completed)
- Repository workspace (`RepositoryWorkspace`).
- Path traversal prevention and safe file operations (`read_file`, `write_file`).
- Git merge diff parsing and application (`apply_diff`).
- Secret scanning and automatic redaction (`SecretScanner`, `redact_secrets`).
- Command policy and sanitization (`CommandPolicy`).
- Sandboxed code execution runtime (`SandboxedCodeRuntime`, `CodeExecutionResult`).
- High-level Coder engine and test runner (`CoderEngine`, `run_tests`).

Phase 9 — Analyst agent (Completed)
- Structured documents, datasets, and image interpretation (`AnalysisInput`, `DatasetSummary`).
- Evidence-linked report synthesis (`AnalysisReport`, `EvidenceLink`).
- Explicit uncertainty reporting and quality assessment (`UncertaintyReport`).
- Large-document workflows with chunked hierarchical analysis (`AnalystEngine`).

Phase 10 — Memory (Completed)
- Working memory (`add_working_memory`).
- Conversation summaries (`record_conversation_summary`).
- User/project/semantic memory (`MemoryItem`, `MemoryType`, `MemoryScope`, `MemoryStore`, `MemoryEngine`).
- Retrieval and conflict handling (`search_memories`, `MemoryConflict`).
- User inspection/edit/delete (`get`, `list`, `update`, `delete`, `clear_scope`).
- Retention/export/delete guarantees (`export_json`, `import_json`).

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

Phase 13 — Economics and observability (Completed)
- Usage metering (`UsageMeter`, `TokenUsageRecord`).
- Versioned provider pricing (`ModelPricing`, `PricingRegistry`).
- Cost calculation and budgets (`CostCalculator`, `UsageBudget`, `BudgetExceededError`).
- p50/p95 latency and metrics (`MetricsTracker`, `LatencyMetrics`, `RequestMetric`).
- Logs, tracing, metrics.

Phase 14 — Security
- Threat model.
- Prompt-injection and retrieval-poisoning tests.
- Tool permissions.
- Data exfiltration tests.
- Secret handling.
- Sandbox escape tests.
- Least privilege and abuse controls.

Phase 15 — Evaluation (Completed)
- Versioned benchmark registry (`BenchmarkRegistry`, `BenchmarkSuite`, `BenchmarkTestCase`).
- Domain benchmarks: General QA, reasoning, coding, math, research, tools, files, vision, safety, French, English, multilingual.
- Evaluation runner and metrics (`EvaluationRunner`, `EvaluationReport`, `TestCaseResult`).
- Release gates and regression reports (`ReleaseGateEvaluator`, `QualityThreshold`, `RegressionReport`).

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
