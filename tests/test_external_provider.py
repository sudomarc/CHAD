from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from chad.core.conversation import ChatRequest, Message, MessageRole
from chad.llm.external import ExternalProviderClient
from chad.llm.gateway import (
    AuthenticationError,
    InvalidRequestError,
    MalformedResponseError,
    ModelCapabilities,
    ModelGateway,
    ModelResponse,
    ProviderServerError,
    RateLimitError,
    TimeoutError,
)
from chad.multimodal.image import ImageConverter, ImageDetail, ImageFormat


def test_external_provider_initialization() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-secret-key",
        model="gpt-4o",
        provider_name="openai",
    )
    model = client.current_model()
    assert model.id == "gpt-4o"
    assert model.backend == "openai"
    assert model.supports_streaming is True
    assert model.capabilities is not None
    assert model.capabilities.vision is True
    client.close()


def test_external_provider_list_models_success() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
        ]
    }

    with patch.object(client._client, "get", return_value=mock_response):
        models = client.list_models()
        assert len(models) == 2
        assert {m.id for m in models} == {"gpt-4o", "gpt-4o-mini"}

    client.close()


def test_external_provider_list_models_fallback() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="custom-model",
    )

    with patch.object(client._client, "get", side_effect=httpx.HTTPError("Network error")):
        models = client.list_models()
        assert len(models) == 1
        assert models[0].id == "custom-model"

    client.close()


def test_external_provider_generate_response_success() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-4o",
        provider_name="openai",
    )

    req = ChatRequest(
        messages=(Message(role=MessageRole.USER, content="Hello GPT"),),
        max_new_tokens=100,
        temperature=0.7,
    )

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "id": "chatcmpl-123",
        "model": "gpt-4o",
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": "Hello user!"},
            }
        ],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 5,
            "total_tokens": 17,
        },
    }

    with patch.object(client._client, "post", return_value=mock_res) as mock_post:
        res = client.generate_response(req)
        assert isinstance(res, ModelResponse)
        assert res.content == "Hello user!"
        assert res.model_id == "gpt-4o"
        assert res.provider == "openai"
        assert res.request_id == "chatcmpl-123"
        assert res.finish_reason == "stop"
        assert res.usage is not None
        assert res.usage.prompt_tokens == 12
        assert res.usage.completion_tokens == 5
        assert res.usage.total_tokens == 17
        assert res.latency_ms is not None and res.latency_ms >= 0

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["model"] == "gpt-4o"
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello GPT"

    client.close()


def test_external_provider_generate_with_multimodal_vision() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
        model="gpt-4o",
    )

    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    img = ImageConverter.from_bytes(
        data=png_bytes,
        format=ImageFormat.PNG,
        detail=ImageDetail.AUTO,
    )

    req = ChatRequest(
        messages=(Message(role=MessageRole.USER, content="What is in this image?", images=(img,)),)
    )

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [{"message": {"content": "It is a PNG image."}}],
    }

    with patch.object(client._client, "post", return_value=mock_res) as mock_post:
        res = client.generate_response(req)
        assert res.content == "It is a PNG image."

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        content_parts = payload["messages"][0]["content"]
        assert isinstance(content_parts, list)
        assert content_parts[0]["type"] == "text"
        assert content_parts[1]["type"] == "image_url"

    client.close()


def test_external_provider_error_mapping() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Test"),))

    # Test 401 Authentication error
    with patch.object(client._client, "post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 401
        mock_res.text = "Invalid API key"
        mock_res.reason_phrase = "Unauthorized"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(AuthenticationError):
            client.generate_response(req)

    # Test 429 Rate limit error
    with patch.object(client._client, "post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 429
        mock_res.text = "Quota exceeded"
        mock_res.reason_phrase = "Too Many Requests"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Rate Limit", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(RateLimitError):
            client.generate_response(req)

    # Test 400 Invalid Request error
    with patch.object(client._client, "post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 400
        mock_res.text = "Invalid parameter"
        mock_res.reason_phrase = "Bad Request"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(InvalidRequestError):
            client.generate_response(req)

    # Test 500 Provider Server error
    with patch.object(client._client, "post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 500
        mock_res.text = "Internal error"
        mock_res.reason_phrase = "Internal Server Error"
        mock_res.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500 Internal Error", request=MagicMock(), response=mock_res
        )
        mock_post.return_value = mock_res

        with pytest.raises(ProviderServerError):
            client.generate_response(req)

    # Test Timeout
    with (
        patch.object(client._client, "post", side_effect=httpx.TimeoutException("Timeout")),
        pytest.raises(TimeoutError),
    ):
        client.generate_response(req)

    # Test Malformed Response
    with patch.object(client._client, "post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.json.return_value = {"unexpected": "payload"}
        mock_post.return_value = mock_res

        with pytest.raises(MalformedResponseError):
            client.generate_response(req)

    client.close()


def test_external_provider_streaming() -> None:
    client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="test-key",
    )
    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Stream test"),))

    mock_lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        'data: {"choices": [{"delta": {"content": " world"}}]}',
        "data: [DONE]",
    ]

    mock_stream_res = MagicMock()
    mock_stream_res.status_code = 200
    mock_stream_res.iter_lines.return_value = iter(mock_lines)

    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_stream_res

    with patch.object(client._client, "stream", return_value=mock_cm):
        tokens = list(client.stream_generate(req))
        assert tokens == ["Hello", " world"]

    client.close()


def test_model_gateway_with_external_provider() -> None:
    ext_client = ExternalProviderClient(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        model="gpt-4o",
        provider_name="openai",
    )

    gateway = ModelGateway()
    gateway.register_provider("openai", ext_client, is_default=True)

    model = gateway.get_model("gpt-4o")
    assert model.id == "gpt-4o"

    caps = gateway.capabilities("gpt-4o")
    assert caps.vision is True
    assert caps.streaming is True

    req = ChatRequest(messages=(Message(role=MessageRole.USER, content="Hi gateway"),))

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "id": "cmpl-gateway-1",
        "model": "gpt-4o",
        "choices": [{"message": {"content": "Response via gateway"}}],
    }

    with patch.object(ext_client._client, "post", return_value=mock_res):
        res = gateway.generate(req)
        assert res.content == "Response via gateway"
        assert res.provider == "openai"

    ext_client.close()
