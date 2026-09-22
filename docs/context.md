# Conversation context

CHAD keeps conversation context separate from provider-specific tokenization.

## Limits

Optional environment variables:

- `CHAD_MAX_CONTEXT_MESSAGES`: maximum number of recent conversation messages kept.
- `CHAD_MAX_CONTEXT_TOKENS`: maximum estimated input tokens kept before a model call.

When `CHAD_MAX_CONTEXT_TOKENS` is unset, CHAD uses the backend-advertised context length when available and reserves the configured `max_new_tokens` for generation.

The current Lapis HTTP API does not advertise a context length in its `/v1/models` response, so no provider-specific context size is invented by CHAD. Until Lapis exposes that metadata, configure `CHAD_MAX_CONTEXT_TOKENS` explicitly when proactive truncation is required.

## Token estimation

The application currently estimates tokens using a simple character-based heuristic:

```text
estimated_tokens = ceil(character_count / chars_per_token)
```

The default is four characters per estimated token.

This is a **budgeting heuristic, not exact provider tokenization**. It is intentionally provider-neutral. A provider can still reject a request because its actual tokenizer produces more tokens than the estimate.

## Truncation behavior

- The system instruction is preserved when it can fit.
- The oldest non-system messages are removed first.
- The newest conversation suffix is preserved.
- If the system instruction plus the newest message cannot fit, CHAD raises `ContextLimitError` instead of silently sending an oversized request.
- A context-limit failure does not persist the rejected user message.

## Why this exists

The context layer prevents unbounded conversation growth from silently reaching a backend with an oversized request. Exact provider token counting and model-specific context metadata belong behind the model gateway contract.
