from __future__ import annotations

import pytest

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest, Message, MessageRole
from chad.llm.client import LapisClient, ModelInfo
from chad.llm.external import ExternalProviderClient
from chad.llm.gateway import (
    CancellationError,
    CancellationToken,
    ModelCapabilities,
    ModelGateway,
    ModelResponse,
)


class MockStreamingClient(LapisClient):
    def __init__(self, model_id: str = "mock-model") -> None:
        self._model = ModelInfo(
            id=model_id,
            display_name=model_id,
            backend="mock",
            supports_streaming=True,
            supports_cancellation=True,
            capabilities=ModelCapabilities(
                text_generation=True,
                streaming=True,
            ),
        )

    def current_model(self) -> ModelInfo:
        return self._model

    def generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> str:
        if cancellation_token is not None:
            cancellation_token.raise_if_cancelled()
        return f"Generated response to {request.messages[-1].content}"

    def generate_response(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> ModelResponse:
        content = self.generate(request, cancellation_token=cancellation_token)
        return ModelResponse(
            content=content,
            model_id=self._model.id,
            provider=self._model.backend,
        )

    def stream_generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ):
        for part in ["Chunk 1", "Chunk 2", "Chunk 3"]:
            if cancellation_token is not None:
                cancellation_token.raise_if_cancelled()
            yield part


def test_cancellation_token_basics() -> None:
    token = CancellationToken()
    assert not token.is_cancelled
    token.raise_if_cancelled()  # should not raise

    token.cancel(reason="User cancelled")
    assert token.is_cancelled
    assert token.reason == "User cancelled"

    with pytest.raises(CancellationError, match="User cancelled"):
        token.raise_if_cancelled()


def test_gateway_generate_cancellation() -> None:
    client = MockStreamingClient()
    gateway = ModelGateway(default_client=client)
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))

    token = CancellationToken()
    token.cancel("Cancelled before generate")

    with pytest.raises(CancellationError, match="Cancelled before generate"):
        gateway.generate(req, cancellation_token=token)


def test_gateway_stream_cancellation_before_start() -> None:
    client = MockStreamingClient()
    gateway = ModelGateway(default_client=client)
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))

    token = CancellationToken()
    token.cancel("Cancelled before stream")

    with pytest.raises(CancellationError, match="Cancelled before stream"):
        list(gateway.stream(req, cancellation_token=token))


def test_gateway_stream_cancellation_mid_stream() -> None:
    client = MockStreamingClient()
    gateway = ModelGateway(default_client=client)
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))

    token = CancellationToken()
    stream_iter = gateway.stream(req, cancellation_token=token)

    first = next(stream_iter)
    assert first == "Chunk 1"

    token.cancel("Cancelled mid-stream")
    with pytest.raises(CancellationError, match="Cancelled mid-stream"):
        next(stream_iter)


def test_chad_app_send_cancellation_cleans_up_state(tmp_path) -> None:
    config = AppConfig(storage_dir=tmp_path)
    client = MockStreamingClient()
    app = ChadApp.create(config, client)

    token = CancellationToken()
    token.cancel("Cancelled send")

    with pytest.raises(CancellationError):
        app.send("This should be cancelled", cancellation_token=token)

    # User message should be popped on failure/cancellation
    assert len(app.conversation.messages) == 0


def test_chad_app_stream_cancellation_cleans_up_state(tmp_path) -> None:
    config = AppConfig(storage_dir=tmp_path)
    client = MockStreamingClient()
    app = ChadApp.create(config, client)

    token = CancellationToken()
    stream_iter = app.stream("Stream prompt", cancellation_token=token)

    first_chunk = next(stream_iter)
    assert first_chunk == "Chunk 1"

    token.cancel("Cancelled mid app stream")
    with pytest.raises(CancellationError):
        list(stream_iter)

    assert len(app.conversation.messages) == 0


def test_chad_app_stream_success(tmp_path) -> None:
    config = AppConfig(storage_dir=tmp_path)
    client = MockStreamingClient()
    app = ChadApp.create(config, client)

    chunks = list(app.stream("Stream prompt"))
    assert "".join(chunks) == "Chunk 1Chunk 2Chunk 3"
    assert len(app.conversation.messages) == 2
    assert app.conversation.messages[0].role == MessageRole.USER
    assert app.conversation.messages[1].role == MessageRole.ASSISTANT
    assert app.conversation.messages[1].content == "Chunk 1Chunk 2Chunk 3"


def test_external_provider_cancellation() -> None:
    client = ExternalProviderClient(
        base_url="https://mock.api/v1",
        api_key="test-key",
        model="gpt-4o",
    )
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Test external"),))

    token = CancellationToken()
    token.cancel("Pre-empted external")

    with pytest.raises(CancellationError, match="Pre-empted external"):
        client.generate_response(req, cancellation_token=token)

    with pytest.raises(CancellationError, match="Pre-empted external"):
        list(client.stream_generate(req, cancellation_token=token))
