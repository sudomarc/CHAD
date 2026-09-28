from __future__ import annotations

from typing import Any, Protocol

from chad.core.messages import Message
from chad.multimodal.image import ImageConverter, ImageValidator


class VisionAdapter(Protocol):
    """Protocol for vision adapters converting multimodal CHAD messages to provider requests."""

    def format_message(self, message: Message) -> dict[str, Any]:
        ...


class VisionPayloadConverter:
    """Utility for converting CHAD Message objects into standardized vision payloads."""

    def __init__(self, validator: ImageValidator | None = None) -> None:
        self.validator = validator or ImageValidator()

    def convert_message_content(self, message: Message) -> list[dict[str, Any]] | str:
        if not message.images:
            return message.content

        content_parts: list[dict[str, Any]] = []

        if message.content:
            content_parts.append({
                "type": "text",
                "text": message.content,
            })

        for image in message.images:
            self.validator.validate(image)
            data_url = ImageConverter.to_data_url(image)
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": data_url,
                    "detail": image.detail.value,
                },
            })

        return content_parts

    def format_message(self, message: Message) -> dict[str, Any]:
        return {
            "role": message.role.value,
            "content": self.convert_message_content(message),
        }
