# Model and provider contract

## Purpose

This document defines the internal boundary between CHAD and any model backend.

The contract exists so CHAD can use LapisLLM, external APIs, and future local/open models without rewriting application logic.

## Implementation: Model Gateway

CHAD implements a provider-neutral `ModelGateway` (`chad.llm.gateway.ModelGateway`) that manages provider registration, capability discovery, request routing, normalized metadata responses, and fallback execution.

```text
ChadApp / Agents
      ↓
ModelGateway
   ├── LapisClient (HTTP)
   ├── LocalLapisClient
   └── ExternalProviderClient (OpenAI-compatible)
```

## Capabilities

A backend advertises capabilities via `ModelCapabilities`:

- `text_generation` (bool)
- `streaming` (bool)
- `vision` (bool)
- `tool_calling` (bool)
- `structured_output` (bool)
- `embeddings` (bool)
- `context_length` (int | None)

## Multimodal and Vision Contract

When a request contains messages with `ImageAttachment` instances:

1. `ModelGateway` verifies that the target model advertises `capabilities.vision == True`.
2. If `vision == False`, `ModelGateway` raises `InvalidRequestError`.
3. Vision adapters (`chad.llm.vision.VisionPayloadConverter`) transform multimodal messages into provider-standard image content payloads (e.g. data URLs with configurable detail level `low`, `high`, or `auto`).

## Model metadata

Model metadata is represented via `ModelInfo`:

- `id`: stable model identifier;
- `display_name`: human-readable name;
- `context_length`: maximum token limit when known;
- `backend`: provider identifier (e.g. `lapis`, `lapis_local`, `openai`, `groq`, `mistral`, `external`);
- `supports_streaming`: boolean indicator;
- `supports_cancellation`: boolean indicator;
- `capabilities`: explicit `ModelCapabilities` instance.

## Request

Normalized requests use `ChatRequest` containing:

- `messages`: tuple of `Message` instances (supporting text and optional `images: tuple[ImageAttachment, ...]`);
- `model`: target model id;
- `temperature`, `top_k`, `top_p`, `max_new_tokens`: generation parameters.

## Response

Normalized generation responses return a `ModelResponse`:

- `content`: generated output text;
- `model_id`: model that produced the generation;
- `provider`: provider identifier;
- `request_id`: provider request identifier when supplied;
- `finish_reason`: finish reason string (e.g., `stop`, `length`);
- `usage`: `UsageInfo` (`prompt_tokens`, `completion_tokens`, `total_tokens`);
- `latency_ms`: measured request latency in milliseconds;
- `tool_calls`: tuple of structured tool calls;
- `raw_response`: underlying raw payload.

## Error taxonomy

All model exceptions inherit from `LLMError`:

- `AuthenticationError`: HTTP 401/403 or invalid credentials;
- `ModelUnavailableError`: model checkpoint or service is unavailable;
- `InvalidRequestError`: HTTP 400/422 or malformed request parameters (including attempting vision requests on non-vision models);
- `ContextLimitExceededError`: request exceeds context budget;
- `RateLimitError`: HTTP 429 or provider rate limit;
- `TimeoutError`: network or execution timeout;
- `ProviderServerError`: HTTP 500+ or provider internal error;
- `MalformedResponseError`: provider response missing expected payload structure;
- `CancellationError`: request cancelled by user/runtime;
- `PolicyDenialError`: blocked by safety or permission policy;
- `GenerationError`: general generation failure.

## Streaming

Streaming is valid only when the backend sends incremental generation events.

CHAD must never manufacture fake streaming by splitting a completed response.

## Routing policy and fallback

`ModelGateway.generate()` accepts `model_id` and optional `fallback_models`. If a primary provider encounters a recoverable error (such as `ModelUnavailableError`, `ProviderServerError`, or `TimeoutError`), the gateway automatically routes the request to configured fallback models in sequence.

## LapisLLM integration

Current verified Lapis integration is HTTP-based (`HttpLapisClient`) and local checkpoint-based (`LocalLapisClient`).

CHAD discovers models through `/v1/models` and sends chat requests through `/v1/chat/completions`.

The Lapis README currently describes non-streaming API behavior. CHAD must not claim streaming over Lapis until Lapis exposes and CHAD verifies a real streaming path.

## External provider integration

CHAD provides `ExternalProviderClient` (`chad.llm.external.ExternalProviderClient`) for external OpenAI-compatible inference APIs (e.g., OpenAI, Groq, Mistral, OpenRouter).

Key capabilities:
- Authentication via `api_key` or custom headers;
- Configurable `base_url` and model target;
- Automatic model discovery (`GET /models`);
- Multimodal vision payload formatting (`VisionPayloadConverter`);
- Incremental SSE streaming (`stream_generate`);
- Error taxonomy mapping for 401/403, 429, 400/422, 5xx, timeouts, and malformed JSON payloads.
