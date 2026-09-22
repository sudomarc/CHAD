from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from chad.app import ChadApp
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest, Message, MessageRole
from chad.llm.client import LapisClient, ModelInfo
from chad.llm.gateway import (
    AuthenticationError,
    InvalidRequestError,
    ModelCapabilities,
    ModelGateway,
    ModelResponse,
    ProviderServerError,
    RateLimitError,
    TimeoutError,
    UsageInfo,
)
from chad.llm.http import HttpLapisClient


class DummyClient(LapisClient):

    def __init__(self, model_id: str = "dummy-1", backend: str = "dummy_backend") -> None:
        self._model = ModelInfo(
            id=model_id,
            display_name=f"Dummy {model_id}",
            context_length=4096,
            backend=backend,
            supports_streaming=True,
            capabilities=ModelCapabilities(
                text_generation=True,
                streaming=True,
                context_length=4096,
            ),
        )

    def current_model(self) -> ModelInfo:
        return self._model

    def generate(self, request: ChatRequest) -> str:
        return f"Response to: {request.messages[-1].content}"

    def generate_response(self, request: ChatRequest) -> ModelResponse:
        return ModelResponse(
            content=f"Response to: {request.messages[-1].content}",
            model_id=self._model.id,
            provider=self._model.backend,
            usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            latency_ms=12.5,
        )


class FailingClient(LapisClient):

    def __init__(self, model_id: str, exc_to_raise: Exception) -> None:
        self._model = ModelInfo(id=model_id, display_name=model_id, backend="failing")
        self._exc = exc_to_raise

    def current_model(self) -> ModelInfo:
        return self._model

    def generate(self, request: ChatRequest) -> str:
        raise self._exc

    def generate_response(self, request: ChatRequest) -> ModelResponse:
        raise self._exc


def test_gateway_registration_and_models() -> None:
    client1 = DummyClient("model-a", "backend-1")
    client2 = DummyClient("model-b", "backend-2")

    gateway = ModelGateway()
    gateway.register_provider("b1", client1, is_default=True)
    gateway.register_provider("b2", client2)

    models = gateway.list_models()
    assert len(models) == 2
    assert {m.id for m in models} == {"model-a", "model-b"}

    model = gateway.get_model("model-b")
    assert model.id == "model-b"

    caps = gateway.capabilities("model-a")
    assert caps.text_generation is True
    assert caps.streaming is True
    assert caps.context_length == 4096


def test_gateway_generate_returns_model_response() -> None:
    client = DummyClient("dummy-1")
    gateway = ModelGateway(default_client=client)

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hello"),))
    res = gateway.generate(req)

    assert isinstance(res, ModelResponse)
    assert res.content == "Response to: Hello"
    assert res.model_id == "dummy-1"
    assert res.provider == "dummy_backend"
    assert res.usage is not None
    assert res.usage.total_tokens == 15
    assert res.latency_ms == 12.5


def test_gateway_fallback_routing() -> None:
    primary = FailingClient("primary-model", ProviderServerError("Server down"))
    fallback = DummyClient("backup-model", "backup-provider")

    gateway = ModelGateway()
    gateway.register_provider("p1", primary, is_default=True)
    gateway.register_provider("p2", fallback)

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Test fallback"),))
    res = gateway.generate(req, model_id="primary-model", fallback_models=("backup-model",))

    assert res.content == "Response to: Test fallback"
    assert res.model_id == "backup-model"


def test_http_client_error_normalization() -> None:
    with patch("httpx.Client.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": [{"id": "test-lapis", "context_length": 2048}]
        }
        client = HttpLapisClient(base_url="http://test-server")

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Test"),))

    # Test 401 Authentication Error
    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 401
        mock_res.text = "Unauthorized"
        mock_res.reason_phrase = "Unauthorized"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(AuthenticationError):
            client.generate_response(req)

    # Test 429 Rate Limit Error
    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 429
        mock_res.text = "Rate limit exceeded"
        mock_res.reason_phrase = "Too Many Requests"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Rate Limit", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(RateLimitError):
            client.generate_response(req)

    # Test 400 Invalid Request Error
    with patch("httpx.Client.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 400
        mock_res.text = "Bad Request"
        mock_res.reason_phrase = "Bad Request"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(InvalidRequestError):
            client.generate_response(req)

    # Test Timeout
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timed out")):
        with pytest.raises(TimeoutError):
            client.generate_response(req)


def test_chad_app_with_gateway(tmp_path) -> None:
    config = AppConfig(storage_dir=tmp_path)
    client = DummyClient("test-model")
    app = ChadApp.create(config, client)

    reply = app.send("Hello world")
    assert reply == "Response to: Hello world"
    assert app.conversation.messages[-1].content == "Response to: Hello world"
