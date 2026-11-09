from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest, Message, MessageRole
from chad.llm.cancellation import CancellationToken
from chad.llm.client import LapisClient, ModelInfo
from chad.llm.external import ExternalProviderClient
from chad.llm.gateway import (
    CancellationError,
    ModelGateway,
    ModelResponse,
)


class DummyClient(LapisClient):
    def __init__(self, model_id: str = "dummy-1", backend: str = "dummy_backend") -> None:
        self._model = ModelInfo(
            id=model_id,
            display_name=f"Dummy {model_id}",
            context_length=4096,
            backend=backend,
            supports_streaming=True,
            supports_cancellation=True,
        )

    def current_model(self) -> ModelInfo:
        return self._model

    def generate(self, request: ChatRequest, cancellation_token: CancellationToken | None = None) -> str:
        if cancellation_token:
            cancellation_token.throw_if_cancelled()
        return f"Response to: {request.messages[-1].content}"

    def generate_response(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ) -> ModelResponse:
        if cancellation_token:
            cancellation_token.throw_if_cancelled()
        return ModelResponse(
            content=f"Response to: {request.messages[-1].content}",
            model_id=self._model.id,
            provider=self._model.backend,
        )

    def stream_generate(
        self,
        request: ChatRequest,
        cancellation_token: CancellationToken | None = None,
    ):
        if cancellation_token:
            cancellation_token.throw_if_cancelled()
        yield "Chunk 1"
        if cancellation_token:
            cancellation_token.throw_if_cancelled()
        yield "Chunk 2"


def test_cancellation_token_basics() -> None:
    token = CancellationToken()
    assert not token.is_cancelled
    assert token.reason is None

    # Should not throw when not cancelled
    token.throw_if_cancelled()

    # Cancel token
    token.cancel("User cancelled operation")
    assert token.is_cancelled
    assert token.reason == "User cancelled operation"

    with pytest.raises(CancellationError, match="User cancelled operation"):
        token.throw_if_cancelled()


def test_cancellation_token_callbacks() -> None:
    token = CancellationToken()
    called_with = []

    def on_cancel(reason: str) -> None:
        called_with.append(reason)

    token.register_callback(on_cancel)
    token.cancel("Cancelled by timeout")

    assert called_with == ["Cancelled by timeout"]

    # Registering callback after cancellation executes immediately
    called_late = []
    token.register_callback(lambda r: called_late.append(r))
    assert called_late == ["Cancelled by timeout"]


def test_gateway_generate_cancellation() -> None:
    client = DummyClient("dummy-1")
    gateway = ModelGateway(default_client=client)

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))
    token = CancellationToken()
    token.cancel("Operation aborted")

    with pytest.raises(CancellationError, match="Operation aborted"):
        gateway.generate(req, cancellation_token=token)


def test_gateway_stream_cancellation_pre_run() -> None:
    client = DummyClient("dummy-1")
    gateway = ModelGateway(default_client=client)

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))
    token = CancellationToken()
    token.cancel("Stream cancelled before start")

    with pytest.raises(CancellationError, match="Stream cancelled before start"):
        list(gateway.stream(req, cancellation_token=token))


def test_gateway_stream_cancellation_mid_stream() -> None:
    client = DummyClient("dummy-1")
    gateway = ModelGateway(default_client=client)

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))
    token = CancellationToken()

    stream_iter = gateway.stream(req, cancellation_token=token)
    chunk1 = next(stream_iter)
    assert chunk1 == "Chunk 1"

    # Cancel mid-stream
    token.cancel("Stopped mid-stream")

    with pytest.raises(CancellationError, match="Stopped mid-stream"):
        next(stream_iter)


def test_external_provider_cancellation() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-4o",
    )
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))
    token = CancellationToken()
    token.cancel("External request cancelled")

    with pytest.raises(CancellationError, match="External request cancelled"):
        client.generate_response(req, cancellation_token=token)

    with pytest.raises(CancellationError, match="External request cancelled"):
        list(client.stream_generate(req, cancellation_token=token))

    client.close()


def test_external_provider_stream_mid_cancellation() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-4o",
    )
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Stream test"),))
    token = CancellationToken()

    mock_lines = [
        'data: {"choices": [{"delta": {"content": "First"}}]}',
        'data: {"choices": [{"delta": {"content": "Second"}}]}',
        "data: [DONE]",
    ]

    mock_stream_res = MagicMock()
    mock_stream_res.status_code = 200
    mock_stream_res.iter_lines.return_value = iter(mock_lines)

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_stream_res

    with patch.object(client._client, "stream", return_value=mock_cm):
        stream_iter = client.stream_generate(req, cancellation_token=token)
        first_chunk = next(stream_iter)
        assert first_chunk == "First"

        token.cancel("User pressed stop button")
        with pytest.raises(CancellationError, match="User pressed stop button"):
            next(stream_iter)

    client.close()


def test_chad_app_send_cancellation(tmp_path) -> None:
    config = AppConfig(storage_dir=tmp_path)
    client = DummyClient("test-model")
    app = ChadApp.create(config, client)

    token = CancellationToken()
    token.cancel("User aborted")

    with pytest.raises(CancellationError, match="User aborted"):
        app.send("Hello world", cancellation_token=token)
