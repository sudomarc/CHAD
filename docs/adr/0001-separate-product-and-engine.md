# ADR 0001: Separate the AI product from the model engine

## Context

CHAD needs to evolve from a small conversational application into a general-purpose AI product with routing, tools, memory and agents.

LapisLLM already owns the model architecture, training and inference runtime. CHAD already consumes Lapis through an application-facing HTTP boundary.

Putting user-facing orchestration or persistence into Lapis would create a coupled system and weaken the existing dependency direction.

## Decision

Keep two explicit repositories and two responsibilities:

- **LapisLLM:** model, tokenizer, training, evaluation, inference/runtime and serving primitives.
- **CHAD:** user-facing product, application state, model/provider gateway, orchestration, tools, agents, memory, files, UX and application security.

Dependency direction remains:

```text
CHAD → LapisLLM
```

CHAD may also use external model providers through provider adapters behind a normalized gateway.

## Alternatives considered

### Merge product and engine

Rejected because application concerns would leak into model infrastructure and reduce replaceability.

### Build a separate third product repository

Rejected for now because CHAD already serves as the documented user-facing application and has the correct responsibility boundary.

### Couple CHAD directly to one external provider

Rejected because provider replacement, Lapis integration and cost-aware routing are strategic requirements.

## Consequences

Positive:

- model and product can evolve independently;
- Lapis can remain focused on model engineering;
- CHAD can route between Lapis and external/open models;
- UI changes do not require model-engine changes;
- agent/tool/memory features remain application capabilities.

Costs:

- two repositories must maintain compatible contracts;
- API compatibility and integration testing become explicit responsibilities;
- duplicated domain adapters may be needed at the boundary.

## Verification / follow-up

- Keep the model gateway provider-neutral.
- Keep Lapis-specific code behind an adapter.
- Add contract tests between CHAD and Lapis.
- Record major boundary changes as subsequent ADRs.
