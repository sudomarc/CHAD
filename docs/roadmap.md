# CHAD exhaustive roadmap

## Status legend

- [x] Verified in the current repository.
- [~] Partially present / foundation exists.
- [ ] Planned.
- [!] Security-sensitive or blocked by an external capability.

This roadmap is intentionally exhaustive at the architecture level. Individual implementation issues should be derived from these workstreams rather than bypassing them.

---

# Phase 0 — Governance and architecture

## Goal

Make CHAD a disciplined product repository before adding complexity.

### Repository

- [x] Keep CHAD separate from LapisLLM.
- [x] Keep the dependency direction CHAD -> LapisLLM.
- [x] Maintain AGENTS.md.
- [ ] Add documentation source-of-truth structure.
- [ ] Add issue templates for feature, bug, architecture/security work.
- [ ] Add pull-request checklist.
- [ ] Add architecture decision records (ADR) convention.
- [ ] Define versioning and release policy.
- [ ] Define compatibility policy for Lapis API versions.

### Architecture

- [ ] Freeze logical boundaries: interface, application, orchestration, context, memory, tools, model gateway, persistence.
- [ ] Define domain error taxonomy.
- [ ] Define IDs and correlation IDs.
- [ ] Define lifecycle states for conversations and agent runs.
- [ ] Define idempotency rules for retried operations.
- [ ] Define cancellation semantics.
- [ ] Define timeout budgets.

### Exit criteria

- Architecture docs agree with code.
- No new feature is introduced without an identified owning layer.
- Application code has one model backend boundary.

---

# Phase 1 — Production-quality conversational core

## Goal

Turn the current foundation into a robust text assistant.

### Conversation engine

- [x] Explicit message roles.
- [~] Persistent conversation model.
- [ ] Message IDs.
- [ ] Message timestamps.
- [ ] Message edit/branch semantics.
- [ ] Regeneration semantics.
- [ ] Conversation title generation.
- [ ] Conversation archive/delete.
- [ ] Pagination for history.
- [ ] Conversation summarization.
- [ ] Context-budget accounting.
- [ ] Deterministic context construction.

### Model interaction

- [x] Lapis HTTP integration.
- [x] Model discovery.
- [~] Model selection.
- [ ] Capability discovery.
- [ ] Normalized usage metadata.
- [ ] Provider-neutral response objects.
- [ ] Real cancellation.
- [ ] Real streaming.
- [ ] Retry policy.
- [ ] Timeout policy.
- [ ] Circuit breaker / degraded mode where justified.

### UX

- [~] CLI conversation.
- [ ] Web UI.
- [ ] Markdown rendering.
- [ ] Code block rendering.
- [ ] Copy actions.
- [ ] Regenerate.
- [ ] Stop generation.
- [ ] Edit message.
- [ ] Model selector.
- [ ] Settings panel.
- [ ] Conversation sidebar.
- [ ] Error recovery UI.

### Exit criteria

- A user can reliably create, continue, reopen and manage conversations.
- Backend failures do not corrupt stored conversations.
- Tests cover the full request lifecycle.

---

# Phase 2 — Web application foundation

## Goal

Create the first serious CHAD product interface.

### Frontend

- [ ] Next.js + React + TypeScript application.
- [ ] Responsive chat layout.
- [ ] Accessible keyboard navigation.
- [ ] Loading/streaming states.
- [ ] Error states.
- [ ] Empty states.
- [ ] Conversation list.
- [ ] Model selector.
- [ ] Settings.
- [ ] File upload surface.
- [ ] Tool activity surface.
- [ ] Source/citation surface.

### Backend

- [ ] FastAPI application boundary.
- [ ] API versioning.
- [ ] Request validation.
- [ ] Authentication-ready user boundary.
- [ ] Correlation IDs.
- [ ] Structured error responses.
- [ ] Health/readiness endpoints.
- [ ] Metrics endpoint or telemetry integration.

### Exit criteria

- Browser and API use the same application core.
- UI does not bypass domain/application services.
- End-to-end chat works against a real backend.

---

# Phase 3 — Model gateway and multi-model support

## Goal

Remove provider coupling and introduce controlled model routing.

### Gateway

- [ ] Create normalized ModelGateway interface.
- [ ] Create Lapis adapter.
- [ ] Create one external provider adapter.
- [ ] Add capability discovery.
- [ ] Add model registry.
- [ ] Add provider health checks.
- [ ] Add request metadata.
- [ ] Add normalized error taxonomy.
- [ ] Add usage normalization.
- [ ] Add cancellation propagation.
- [ ] Add streaming abstraction.

### Model router

- [ ] Rule-based router V1.
- [ ] Task classification.
- [ ] Model capability matching.
- [ ] Context-length matching.
- [ ] Cost budget matching.
- [ ] Latency target matching.
- [ ] Privacy constraint matching.
- [ ] Fallback model policy.
- [ ] Routing observability.
- [ ] Manual model override.

### Exit criteria

- CHAD can switch between at least two real backends through one interface.
- Provider details do not leak into application logic.
- Routing decisions are inspectable.

---

# Phase 4 — Web research

## Goal

Build a real research subsystem.

### Search

- [ ] Search provider interface.
- [ ] Search request schema.
- [ ] Result normalization.
- [ ] Result ranking.
- [ ] Deduplication.

### Fetch

- [ ] Safe page fetching.
- [ ] Content extraction.
- [ ] Size limits.
- [ ] Redirect policy.
- [ ] Timeout policy.
- [ ] Content-type validation.

### Research agent

- [ ] Research planner.
- [ ] Query decomposition.
- [ ] Multi-query search.
- [ ] Evidence collection.
- [ ] Source selection.
- [ ] Contradiction detection.
- [ ] Citation mapping.
- [ ] Final synthesis.

### Security

- [ ] Treat pages as untrusted data.
- [ ] Prompt-injection detection.
- [ ] Never execute webpage instructions.
- [ ] Restrict tool chaining from retrieved content.

### Exit criteria

- A research request can produce an answer with traceable sources.
- Retrieved content cannot directly invoke privileged actions.

---

# Phase 5 — Files and knowledge

## Goal

Make uploaded documents first-class inputs.

### Ingestion

- [ ] File upload API.
- [ ] MIME/type detection.
- [ ] Extension spoofing defense.
- [ ] Size limits.
- [ ] Safe file storage.
- [ ] Text extraction.
- [ ] Metadata extraction.
- [ ] Chunking.
- [ ] Chunk identifiers.

### Retrieval

- [ ] Embedding interface.
- [ ] Vector store integration.
- [ ] Hybrid retrieval option.
- [ ] Result ranking.
- [ ] Context assembly.
- [ ] Citation backreferences.

### File UX

- [ ] Upload progress.
- [ ] File preview.
- [ ] File list.
- [ ] Remove file.
- [ ] Attach file to conversation.
- [ ] Explain extraction failures.

### Supported formats

Initial target:

- [ ] PDF.
- [ ] TXT.
- [ ] Markdown.
- [ ] DOCX.
- [ ] CSV.
- [ ] JSON.
- [ ] Images.
- [ ] Source code.

### Security

- [ ] Malware scanning boundary.
- [ ] Archive bomb protection.
- [ ] Parser isolation where required.
- [ ] Untrusted content labeling.

### Exit criteria

- Users can ask questions over documents with reproducible retrieval.
- Original files and derived chunks remain traceable.

---

# Phase 6 — Vision and multimodal context

## Goal

Support image understanding through the model gateway.

### Backend

- [ ] Multimodal request schema.
- [ ] Image capability discovery.
- [ ] Provider adapter support.
- [ ] Image-size validation.
- [ ] Image conversion pipeline.
- [ ] Safe temporary storage.

### UX

- [ ] Image attachment.
- [ ] Preview.
- [ ] Remove/replace image.
- [ ] Mixed text + image messages.

### Evaluation

- [ ] OCR-like extraction tests.
- [ ] Diagram interpretation tests.
- [ ] Screenshot analysis tests.
- [ ] Adversarial image/content tests.

### Exit criteria

- Images can be analyzed without special-casing a provider in UI code.

---

# Phase 7 — Tools platform

## Goal

Give models controlled ways to act.

### Tool runtime

- [ ] Tool registry.
- [ ] Schema validation.
- [ ] Permission engine.
- [ ] Timeout enforcement.
- [ ] Rate limiting.
- [ ] Result-size limits.
- [ ] Audit events.
- [ ] Retry classification.
- [ ] Tool error normalization.

### Initial tools

- [ ] Calculator.
- [ ] Date/time.
- [ ] Web search.
- [ ] Web fetch.
- [ ] File reader.
- [ ] Python sandbox.
- [ ] Code execution sandbox.

### Tool UX

- [ ] Tool activity indicator.
- [ ] Expandable tool details.
- [ ] Permission prompt where needed.
- [ ] Failure presentation.
- [ ] Cancellation.

### Exit criteria

- Every tool call is validated before execution.
- No model output can directly execute arbitrary application code.

---

# Phase 8 — Sandboxed code agent

## Goal

Support real coding tasks safely.

### Workspace

- [ ] Ephemeral workspace model.
- [ ] File tree.
- [ ] Read/write API.
- [ ] Artifact collection.

### Execution

- [ ] Isolated runtime.
- [ ] CPU limit.
- [ ] Memory limit.
- [ ] Timeout.
- [ ] Process limit.
- [ ] Filesystem policy.
- [ ] Network policy.
- [ ] Environment-variable policy.
- [ ] Output truncation.
- [ ] Cleanup.

### Agent behavior

- [ ] Inspect repository.
- [ ] Plan changes.
- [ ] Modify files.
- [ ] Run tests.
- [ ] Read failures.
- [ ] Iterate.
- [ ] Produce a final diff/report.

### Safety

- [ ] Explicit command policy.
- [ ] Dangerous operation denylist/policy engine.
- [ ] Secret scanning.
- [ ] Sandbox escape test suite.

### Exit criteria

- Coding tasks can be completed in an isolated workspace.
- Main application host is never the execution environment.

---

# Phase 9 — Agent orchestration

## Goal

Upgrade CHAD from a chatbot to a bounded agentic assistant.

### Orchestrator

- [ ] Task classification.
- [ ] Plan generation.
- [ ] Plan validation.
- [ ] Tool selection.
- [ ] Agent selection.
- [ ] State machine.
- [ ] Step budget.
- [ ] Token budget.
- [ ] Time budget.
- [ ] Retry budget.
- [ ] Cancellation.
- [ ] Failure recovery.
- [ ] Final-answer synthesis.

### Specialist roles

- [ ] Researcher.
- [ ] Coder.
- [ ] Analyst.
- [ ] Future domain specialists.

### Execution policies

- [ ] Read-only mode.
- [ ] Draft mode.
- [ ] User-approved write mode.
- [ ] High-risk action confirmation.
- [ ] Maximum autonomous step count.
- [ ] Loop detection.

### Exit criteria

- Complex tasks execute through explicit bounded states.
- Agents cannot silently escalate privileges.

---

# Phase 10 — Memory

## Goal

Provide useful continuity without uncontrolled data retention.

### Conversation memory

- [ ] Durable conversation records.
- [ ] Summaries.
- [ ] Context compression.
- [ ] Conversation retrieval.

### User memory

- [ ] Memory extraction candidate generation.
- [ ] Explicit save.
- [ ] Automatic save policy with user controls.
- [ ] Memory inspection.
- [ ] Memory editing.
- [ ] Memory deletion.
- [ ] Memory disable switch.

### Project memory

- [ ] Project entities.
- [ ] Project files.
- [ ] Project-specific instructions.
- [ ] Project semantic index.

### Retrieval

- [ ] Embeddings.
- [ ] Similarity search.
- [ ] Recency weighting.
- [ ] Source weighting.
- [ ] Memory conflict handling.

### Security/privacy

- [ ] Data retention policy.
- [ ] Delete guarantees.
- [ ] Export path.
- [ ] Access controls.
- [ ] No secret memory by default.

### Exit criteria

- Memory improves task continuity without becoming invisible, permanent state.

---

# Phase 11 — Authentication, accounts and multi-user foundations

## Goal

Move from local developer software to a real hosted product.

### Identity

- [ ] Authentication provider.
- [ ] User IDs.
- [ ] Session management.
- [ ] Device/session revocation.
- [ ] Account deletion.

### Authorization

- [ ] User-owned conversations.
- [ ] Project ownership.
- [ ] File ownership.
- [ ] Tool authorization.
- [ ] Admin boundaries.

### Quotas

- [ ] Per-user rate limits.
- [ ] Token budgets.
- [ ] Tool budgets.
- [ ] Storage limits.
- [ ] Concurrency limits.

### Exit criteria

- Cross-user data access is impossible through ordinary application paths.

---

# Phase 12 — Billing and cost controls

## Goal

Make the system economically measurable.

### Metering

- [ ] Input tokens.
- [ ] Output tokens.
- [ ] Model calls.
- [ ] Tool calls.
- [ ] Search calls.
- [ ] Storage.
- [ ] Execution time.

### Cost model

- [ ] Provider price table.
- [ ] Versioned pricing.
- [ ] Currency normalization.
- [ ] Estimated cost at request time.
- [ ] Actual cost reconciliation.

### Cost controls

- [ ] Per-user budget.
- [ ] Per-request budget.
- [ ] Model tier restrictions.
- [ ] Cheap-model routing.
- [ ] Caching.
- [ ] Context compression.
- [ ] Batch operations where useful.

### Exit criteria

- Cost per successful task can be measured by model/provider and task category.

---

# Phase 13 — Observability and operations

## Goal

Make failures diagnosable in production.

### Logging

- [ ] Structured logs.
- [ ] Correlation IDs.
- [ ] Redaction.
- [ ] Event taxonomy.

### Metrics

- [ ] Latency.
- [ ] Throughput.
- [ ] Error rates.
- [ ] Tool success.
- [ ] Agent completion.
- [ ] Token usage.
- [ ] Cost.
- [ ] Queue depth.

### Tracing

- [ ] Request span.
- [ ] Model span.
- [ ] Retrieval span.
- [ ] Tool span.
- [ ] Agent step span.

### Operations

- [ ] Health checks.
- [ ] Readiness checks.
- [ ] Graceful shutdown.
- [ ] Backpressure.
- [ ] Circuit breakers.
- [ ] Rate limiting.
- [ ] Alerting.

### Exit criteria

- A production failure can be traced from user request to model/tool event without exposing secrets.

---

# Phase 14 — Security hardening

## Goal

Treat CHAD as a security-sensitive AI platform.

### Application security

- [ ] Input validation.
- [ ] Output escaping.
- [ ] CSRF policy where applicable.
- [ ] Secure headers.
- [ ] Dependency auditing.
- [ ] Secret management.
- [ ] Least-privilege service accounts.

### AI security

- [ ] Prompt-injection tests.
- [ ] Indirect prompt-injection tests.
- [ ] Tool-confusion tests.
- [ ] Data exfiltration tests.
- [ ] Retrieval poisoning tests.
- [ ] Model-output validation.
- [ ] Permission escalation tests.

### Sandbox security

- [ ] Container isolation.
- [ ] Kernel/runtime hardening as appropriate.
- [ ] Network isolation.
- [ ] Resource limits.
- [ ] Escape testing.

### Privacy

- [ ] Data classification.
- [ ] Retention policy.
- [ ] User deletion.
- [ ] Export.
- [ ] Provider data-use configuration.
- [ ] Audit policy.

### Exit criteria

- Security boundaries are tested, documented and monitored.
- Critical vulnerabilities block release.

---

# Phase 15 — Evaluation platform

## Goal

Measure CHAD continuously.

### Test harness

- [ ] Versioned task datasets.
- [ ] Golden answers where appropriate.
- [ ] Model-graded evaluation with safeguards.
- [ ] Deterministic subsets.
- [ ] Human review workflow.

### Task families

- [ ] General QA.
- [ ] Reasoning.
- [ ] Coding.
- [ ] Mathematics.
- [ ] Research.
- [ ] Long context.
- [ ] Instruction following.
- [ ] Tool use.
- [ ] File analysis.
- [ ] Vision.
- [ ] English.
- [ ] French.
- [ ] Multilingual.
- [ ] Safety.

### Release system

- [ ] Baseline version.
- [ ] Candidate version.
- [ ] Regression comparison.
- [ ] Threshold policy.
- [ ] Report generation.
- [ ] Artifact retention.

### Exit criteria

- Every major release has reproducible evaluation evidence.

---

# Phase 16 — LapisLLM post-training

## Goal

Increase the share of intelligence provided by our own model.

This phase belongs primarily in the LapisLLM repository but is included here because CHAD depends on its runtime contracts.

### Model work

- [ ] Instruction-tuning dataset pipeline.
- [ ] High-quality supervised fine-tuning.
- [ ] Tool-use training.
- [ ] Preference data.
- [ ] Preference optimization.
- [ ] Safety tuning.
- [ ] Evaluation integration.

### Product integration

- [ ] Publish compatible Lapis model metadata.
- [ ] Register model in CHAD.
- [ ] Add capability flags.
- [ ] Benchmark against external backends.
- [ ] Route selected task classes to Lapis.

### Exit criteria

- Lapis can serve a documented instruction-following checkpoint through the existing runtime boundary.

---

# Phase 17 — LapisLLM scale and efficiency

## Goal

Move from development-scale models toward serious inference/training systems.

### Training

- [ ] Exact mid-epoch replay.
- [ ] Strong resume semantics.
- [ ] Mixed precision.
- [ ] Distributed training.
- [ ] Multi-GPU training.
- [ ] Data sharding.
- [ ] Deduplication.
- [ ] Larger datasets.
- [ ] Better data mixture controls.

### Inference

- [ ] KV cache.
- [ ] Efficient batching.
- [ ] Quantization.
- [ ] Safetensors/export path.
- [ ] Production serving hardening.
- [ ] Throughput benchmarks.

### Model scale

Roadmap targets exist in Lapis, but each size must be justified by compute budget, data, evaluation and serving feasibility.

- [ ] Larger development model.
- [ ] Mid-scale model.
- [ ] Larger model.
- [ ] Proprietary model family.

### Exit criteria

- Larger Lapis releases have reproducible training and evaluation records.

---

# Phase 18 — Connectors and external actions

## Goal

Connect CHAD to real user workflows.

Initial candidates:

- [ ] GitHub.
- [ ] Notion.
- [ ] Google Drive.
- [ ] Slack.
- [ ] Calendar.
- [ ] Email.

Each integration requires:

- [ ] OAuth/security model.
- [ ] Permission scopes.
- [ ] Read/write separation.
- [ ] User confirmation for side effects.
- [ ] Audit events.
- [ ] Revocation.
- [ ] Error recovery.

---

# Phase 19 — Collaboration and projects

## Goal

Turn conversations into durable workspaces.

- [ ] Projects.
- [ ] Project instructions.
- [ ] Project files.
- [ ] Shared context.
- [ ] Project memory.
- [ ] Artifacts.
- [ ] Activity history.
- [ ] Collaboration roles.
- [ ] Sharing controls.

---

# Phase 20 — Multimodal and new interfaces

Future interfaces:

- [ ] Voice input.
- [ ] Voice output.
- [ ] Mobile client.
- [ ] Desktop client.
- [ ] Rich canvas.
- [ ] Live camera input where justified.

Each interface must reuse the same application/domain contracts.

---

# Phase 21 — Advanced autonomy

Only after the safety, memory, tools and evaluation systems are mature.

- [ ] Long-running task scheduler.
- [ ] Durable agent runs.
- [ ] Background tasks.
- [ ] Progress reporting.
- [ ] Resume after failure.
- [ ] Human checkpoints.
- [ ] Multi-agent collaboration.
- [ ] Agent-to-agent delegation.
- [ ] Cost-aware planning.
- [ ] Reliability-aware planning.

The system must remain bounded and auditable.

---

# Phase 22 — Competitive quality program

## Goal

Measure where CHAD is strong and where it is weak.

### Benchmark dimensions

- [ ] Answer quality.
- [ ] Reasoning reliability.
- [ ] Coding performance.
- [ ] Research quality.
- [ ] Citation quality.
- [ ] Tool reliability.
- [ ] Agent completion.
- [ ] Long-context performance.
- [ ] Vision performance.
- [ ] Latency.
- [ ] Cost.
- [ ] Safety.

### Method

For every comparison:

- [ ] Define task set.
- [ ] Fix versions.
- [ ] Define prompts.
- [ ] Define scoring.
- [ ] Record hardware/provider.
- [ ] Repeat measurements.
- [ ] Publish limitations.

No overall ranking should be inferred from one benchmark.

---

# Phase 23 — Production readiness

## Platform

- [ ] Deployment automation.
- [ ] Infrastructure as code.
- [ ] Secret management.
- [ ] Database migrations.
- [ ] Backups.
- [ ] Restore testing.
- [ ] Disaster recovery.
- [ ] Capacity planning.
- [ ] Autoscaling.
- [ ] CDN where needed.

## Reliability

- [ ] SLOs.
- [ ] Error budgets.
- [ ] Load tests.
- [ ] Chaos/failure tests.
- [ ] Provider outage strategy.
- [ ] Graceful degradation.

## Compliance/product policy

- [ ] Terms.
- [ ] Privacy policy.
- [ ] Data deletion workflow.
- [ ] Abuse reporting.
- [ ] Security disclosure process.
- [ ] Audit requirements.

---

# Phase 24 — Long-term independence

## Goal

Reduce strategic dependency on external model providers without sacrificing user quality.

```text
External frontier models
        +
Open-weight models
        +
LapisLLM
        ↓
Model router
        ↓
CHAD
```

Over time:

```text
External dependency
       ↓
Shared model portfolio
       ↓
More Lapis capability
       ↓
More self-hosted inference
       ↓
Proprietary model family
```

Workstreams:

- [ ] Proprietary data strategy.
- [ ] High-quality training corpus.
- [ ] Post-training pipeline.
- [ ] Tool-use dataset.
- [ ] Preference data.
- [ ] Safety data.
- [ ] Model distillation where legally and technically appropriate.
- [ ] Inference infrastructure.
- [ ] Dedicated evaluation infrastructure.
- [ ] Model release process.

The project must never represent this as achieved until reproducible evidence exists.

---

# Cross-cutting engineering requirements

These apply to every phase.

## Correctness

- [ ] Validate inputs at boundaries.
- [ ] Test failure modes.
- [ ] Add regression tests for meaningful bugs.
- [ ] Keep provider behavior behind adapters.
- [ ] Keep product behavior out of LapisLLM.

## Security

- [ ] Treat external content as untrusted.
- [ ] Never execute model output automatically.
- [ ] Protect credentials.
- [ ] Isolate high-risk execution.
- [ ] Log security events without leaking sensitive content.

## Performance

- [ ] Measure before optimizing.
- [ ] Track p50/p95 latency.
- [ ] Track token usage.
- [ ] Track tool overhead.
- [ ] Track retrieval overhead.
- [ ] Track cache effectiveness.

## Cost

- [ ] Record model/provider usage.
- [ ] Version pricing data.
- [ ] Prefer appropriate model tiers.
- [ ] Compress unnecessary context.
- [ ] Cache stable results.

## Documentation

- [ ] Update docs with behavior changes.
- [ ] Add ADR for architectural decisions.
- [ ] Link implementation issues to roadmap items.
- [ ] Record verification evidence.

## Release discipline

Before release:

```text
tests
  ↓
integration checks
  ↓
security checks
  ↓
evaluation
  ↓
performance/cost review
  ↓
documentation
  ↓
diff/status inspection
  ↓
release
```

---

# Recommended implementation order

The roadmap contains long-term work, but the shortest coherent path to a useful product is:

```text
1. Governance/docs
       ↓
2. Robust conversation core
       ↓
3. Web product shell
       ↓
4. Model gateway
       ↓
5. Streaming/cancellation
       ↓
6. Web research
       ↓
7. Files/RAG
       ↓
8. Tools
       ↓
9. Code sandbox
       ↓
10. Agent orchestration
       ↓
11. Memory
       ↓
12. Evaluation
       ↓
13. Security hardening
       ↓
14. Production infrastructure
       ↓
15. Lapis post-training
       ↓
16. Lapis scale
       ↓
17. Advanced autonomy
```

This order deliberately puts reliability, permissions and evaluation before unrestricted autonomy.
