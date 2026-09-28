import base64

import pytest

from chad.core.context import ContextBudget, estimate_image_tokens, estimate_message_tokens
from chad.core.conversation import ChatRequest
from chad.core.messages import ImageAttachment, ImageDetail, ImageFormat, Message, MessageRole
from chad.llm.client import LapisClient, ModelInfo
from chad.llm.gateway import InvalidRequestError, ModelCapabilities, ModelGateway
from chad.llm.vision import VisionPayloadConverter
from chad.multimodal.evaluator import ImageType, ScreenshotDiagramEvaluator
from chad.multimodal.image import ImageConverter, ImageValidationError, ImageValidator


def test_image_attachment_contract() -> None:
    attachment = ImageAttachment(
        format=ImageFormat.PNG,
        data_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        detail=ImageDetail.HIGH,
        width=100,
        height=100,
    )
    data = attachment.to_dict()
    assert data["format"] == "png"
    assert data["detail"] == "high"
    assert data["width"] == 100

    reconstructed = ImageAttachment.from_dict(data)
    assert reconstructed.format == ImageFormat.PNG
    assert reconstructed.detail == ImageDetail.HIGH
    assert reconstructed.width == 100


def test_message_with_image_attachment() -> None:
    img = ImageAttachment(
        format=ImageFormat.JPEG,
        url="https://example.com/test.jpg",
    )
    msg = Message(
        role=MessageRole.USER,
        content="Describe this diagram",
        images=(img,),
    )
    d = msg.to_dict()
    assert len(d["images"]) == 1
    assert d["images"][0]["url"] == "https://example.com/test.jpg"

    reconstructed = Message.from_dict(d)
    assert len(reconstructed.images) == 1
    assert reconstructed.images[0].url == "https://example.com/test.jpg"


def test_image_validator() -> None:
    validator = ImageValidator(max_bytes=1000)

    # Valid base64
    valid_b64 = base64.b64encode(b"hello world").decode()
    valid_img = ImageAttachment(format=ImageFormat.PNG, data_base64=valid_b64)
    validator.validate(valid_img)

    # Invalid base64
    invalid_img = ImageAttachment(format=ImageFormat.PNG, data_base64="!!!invalid_b64!!!")
    with pytest.raises(ImageValidationError, match="Invalid base64"):
        validator.validate(invalid_img)

    # Invalid dimension
    bad_dim = ImageAttachment(format=ImageFormat.PNG, data_base64=valid_b64, width=-10)
    with pytest.raises(ImageValidationError, match="greater than 0"):
        validator.validate(bad_dim)


def test_image_converter() -> None:
    b64 = base64.b64encode(b"sample image content").decode()
    attachment = ImageAttachment(format=ImageFormat.WEBP, data_base64=b64)
    data_url = ImageConverter.to_data_url(attachment)
    assert data_url.startswith("data:image/webp;base64,")

    from_bytes = ImageConverter.from_bytes(b"test data", format=ImageFormat.PNG)
    assert from_bytes.format == ImageFormat.PNG
    assert from_bytes.data_base64 is not None


def test_multimodal_context_token_estimation() -> None:
    low_img = ImageAttachment(format=ImageFormat.PNG, url="https://example.com/img.png", detail=ImageDetail.LOW)
    assert estimate_image_tokens(low_img) == 85

    high_img = ImageAttachment(
        format=ImageFormat.PNG,
        url="https://example.com/img.png",
        detail=ImageDetail.HIGH,
        width=1024,
        height=1024,
    )
    # tiles: 2x2 = 4 tiles -> 85 + 170*4 = 765 tokens
    assert estimate_image_tokens(high_img) == 765

    msg = Message(role=MessageRole.USER, content="Look", images=(low_img,))
    # text: "Look" = 1 token, image: 85 tokens -> 86 tokens
    tokens = estimate_message_tokens(msg)
    assert tokens == 86

    budget = ContextBudget(max_input_tokens=100)
    trimmed = budget.trim([msg])
    assert len(trimmed) == 1


def test_vision_payload_converter() -> None:
    b64 = base64.b64encode(b"test image").decode()
    img = ImageAttachment(format=ImageFormat.PNG, data_base64=b64)
    msg = Message(role=MessageRole.USER, content="Analyze screenshot", images=(img,))

    converter = VisionPayloadConverter()
    payload = converter.format_message(msg)
    assert payload["role"] == "user"
    assert isinstance(payload["content"], list)
    assert len(payload["content"]) == 2
    assert payload["content"][0]["type"] == "text"
    assert payload["content"][1]["type"] == "image_url"


class DummyVisionClient(LapisClient):
    def __init__(self, model_id: str, supports_vision: bool) -> None:
        self._model = ModelInfo(
            id=model_id,
            display_name=model_id,
            backend="test",
            capabilities=ModelCapabilities(text_generation=True, vision=supports_vision),
        )

    def current_model(self) -> ModelInfo:
        return self._model

    def list_models(self) -> list[ModelInfo]:
        return [self._model]

    def generate(self, request: ChatRequest) -> str:
        return "vision response"


def test_gateway_vision_capability_enforcement() -> None:
    non_vision_client = DummyVisionClient("text-model", supports_vision=False)
    vision_client = DummyVisionClient("vision-model", supports_vision=True)

    gateway = ModelGateway(non_vision_client)
    gateway.register_provider("vision_prov", vision_client)

    b64 = base64.b64encode(b"image bytes").decode()
    img = ImageAttachment(format=ImageFormat.PNG, data_base64=b64)
    multimodal_msg = Message(role=MessageRole.USER, content="What is this?", images=(img,))
    request = ChatRequest(messages=(multimodal_msg,), model="text-model")

    # Should raise InvalidRequestError on text-model because vision is False
    with pytest.raises(InvalidRequestError, match="does not support vision capabilities"):
        gateway.generate(request)

    # Should succeed on vision-model
    request_vision = ChatRequest(messages=(multimodal_msg,), model="vision-model")
    resp = gateway.generate(request_vision)
    assert resp.content == "vision response"


def test_screenshot_diagram_evaluator() -> None:
    evaluator = ScreenshotDiagramEvaluator()

    img = ImageAttachment(
        format=ImageFormat.PNG,
        url="https://example.com/screenshot.png",
        width=1920,
        height=1080,
    )
    result = evaluator.evaluate(img, hint_type=ImageType.SCREENSHOT)
    assert result.image_type == ImageType.SCREENSHOT
    assert len(result.elements) > 0
    assert result.confidence_score > 0.8
    assert "header_bar" in [el.element_type for el in result.elements]

    d_dict = result.to_dict()
    assert d_dict["image_type"] == "screenshot"
