# Model Provider Gateway

## Objective
Provide one provider-neutral interface while preserving real provider capabilities and useful provider-specific diagnostics.

## Contract
The gateway should define typed request, message, response, tool-call, usage, error, and capability models. Provider adapters translate between those contracts and vendor APIs.

## Capabilities
Capabilities must be explicit per model: streaming, tool calling, vision, structured output, context limit, and supported modalities. Unknown capability values remain unknown; do not assume support.

## Adapters
Initial adapter candidates:
- LapisLLM
- OpenAI
- Anthropic
- Google Gemini

Each adapter is independently testable with mocked HTTP/API responses. Live integration tests are opt-in and require credentials.

## Streaming
Use native provider streaming when available. If unavailable, return a completed response and communicate that limitation. Never split a completed response into fake token events.

## Errors and retries
Normalize authentication, rate-limit, timeout, invalid-request, unavailable-model, and provider-server errors. Retry only transient failures, with bounded backoff and no duplicate tool execution.

## Credentials
Load secrets from environment variables or an OS credential store. Never store them in repository config, session history, telemetry, or logs. Configuration files may contain environment-variable references, not secret values.

## Model selection
Allow provider/model selection at session and task level. Routing by task type is a later capability and must remain transparent to the user.
