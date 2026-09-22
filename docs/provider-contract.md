# Model and provider contract

## Purpose

This document defines the internal boundary between CHAD and any model backend.

The contract exists so CHAD can use LapisLLM, external APIs, and future local/open models without rewriting application logic.

## Capabilities

A backend advertises capabilities rather than forcing the application to guess:

- text generation;
- streaming;
- vision;
- tool calling;
- structured output;
- embeddings;
- long context;
- cancellation;
- usage accounting.

## Model metadata

Required fields:

- stable model id;
- provider/backend id;
- human-readable display name;
- context limit when known;
- supported input modalities;
- supported capabilities;
- availability state.

Optional fields:

- pricing metadata;
- quality tier;
- latency tier;
- region;
- privacy mode.

## Request

A normalized request should contain:

- model;
- messages;
- generation parameters;
- optional tools;
- optional response format;
- request metadata;
- cancellation signal.

The gateway, not the UI, validates provider-specific constraints.

## Response

A normalized response should preserve:

- text;
- structured content where supported;
- tool calls;
- finish reason;
- usage;
- model id;
- provider request id;
- errors;
- warnings.

Provider-specific metadata may be attached without leaking provider-specific concepts into the application core.

## Error taxonomy

At minimum:

- authentication failure;
- model unavailable;
- request invalid;
- context limit exceeded;
- rate limited;
- provider timeout;
- provider server failure;
- malformed provider response;
- cancellation;
- policy denial.

Errors should map to user-facing messages separately from diagnostic details.

## Streaming

Streaming is valid only when the backend sends incremental generation events.

CHAD must never manufacture fake streaming by splitting a completed response.

The stream contract should support:

- delta text;
- tool-call deltas where supported;
- completion;
- error;
- cancellation acknowledgement;
- usage metadata where available.

## Routing policy

Routing may consider:

- task type;
- required capability;
- context length;
- latency target;
- cost budget;
- privacy requirement;
- availability;
- user preference.

Routing decisions must be observable and reproducible from recorded request metadata.

## LapisLLM integration

Current verified Lapis integration is HTTP-based.

CHAD currently discovers models through `/v1/models` and sends chat requests through `/v1/chat/completions`.

The Lapis README currently describes non-streaming API behavior. CHAD must not claim streaming over Lapis until Lapis exposes and CHAD verifies a real streaming path.

## External providers

Provider adapters are optional implementation modules.

They must not be imported from:

- conversation models;
- storage;
- UI components;
- command parsing;
- agent definitions.

Only the model gateway should know provider SDK details.
