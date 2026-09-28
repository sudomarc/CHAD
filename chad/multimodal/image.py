from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from chad.core.messages import ImageAttachment, ImageDetail, ImageFormat


class ImageValidationError(ValueError):
    """Raised when image validation fails."""


class ImageValidator:
    """Validator for image attachments in CHAD."""

    ALLOWED_FORMATS: ClassVar[set[ImageFormat]] = {
        ImageFormat.PNG,
        ImageFormat.JPEG,
        ImageFormat.WEBP,
        ImageFormat.GIF,
    }

    def __init__(self, max_bytes: int = 20_000_000) -> None:
        self.max_bytes = max_bytes

    def validate(self, attachment: ImageAttachment) -> None:
        if attachment.format not in self.ALLOWED_FORMATS:
            raise ImageValidationError(f"Unsupported image format: {attachment.format}")

        if attachment.width is not None and attachment.width <= 0:
            raise ImageValidationError("Image width must be greater than 0")
        if attachment.height is not None and attachment.height <= 0:
            raise ImageValidationError("Image height must be greater than 0")

        if attachment.data_base64:
            self._validate_base64(attachment.data_base64)

        if attachment.url:
            self._validate_url(attachment.url)

        if attachment.file_path:
            self._validate_file_path(attachment.file_path)

    def _validate_base64(self, data_base64: str) -> None:
        raw_b64 = data_base64
        if "," in data_base64:
            raw_b64 = data_base64.split(",", 1)[1]

        try:
            decoded = base64.b64decode(raw_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ImageValidationError("Invalid base64 encoding for image data") from exc

        if len(decoded) > self.max_bytes:
            raise ImageValidationError(
                f"Image size ({len(decoded)} bytes) exceeds maximum limit of {self.max_bytes} bytes"
            )

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https", "data"):
            raise ImageValidationError(f"Invalid URL scheme for image: {parsed.scheme}")

    def _validate_file_path(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            raise ImageValidationError(f"Image file does not exist: {file_path}")
        if path.is_file():
            file_size = path.stat().st_size
            if file_size > self.max_bytes:
                raise ImageValidationError(
                    f"Image file size ({file_size} bytes) exceeds maximum limit of {self.max_bytes} bytes"
                )


class ImageConverter:
    """Converter utilities for image formatting and conversions."""

    @staticmethod
    def to_data_url(attachment: ImageAttachment) -> str:
        if attachment.data_base64:
            if attachment.data_base64.startswith("data:"):
                return attachment.data_base64
            mime = attachment.mime_type or f"image/{attachment.format.value}"
            return f"data:{mime};base64,{attachment.data_base64}"
        if attachment.url and attachment.url.startswith("data:"):
            return attachment.url
        if attachment.file_path:
            path = Path(attachment.file_path)
            if not path.exists():
                raise ImageValidationError(f"Image file not found: {attachment.file_path}")
            data = path.read_bytes()
            b64_str = base64.b64encode(data).decode("utf-8")
            mime = attachment.mime_type or f"image/{attachment.format.value}"
            return f"data:{mime};base64,{b64_str}"
        if attachment.url:
            return attachment.url
        raise ImageValidationError("Unable to convert image attachment to data URL: missing source data")

    @staticmethod
    def from_bytes(
        data: bytes,
        format: ImageFormat,
        detail: ImageDetail = ImageDetail.AUTO,
        width: int | None = None,
        height: int | None = None,
    ) -> ImageAttachment:
        b64_str = base64.b64encode(data).decode("utf-8")
        return ImageAttachment(
            format=format,
            data_base64=b64_str,
            detail=detail,
            width=width,
            height=height,
            mime_type=f"image/{format.value}",
        )

    @staticmethod
    def from_file(
        file_path: str,
        format: ImageFormat | None = None,
        detail: ImageDetail = ImageDetail.AUTO,
    ) -> ImageAttachment:
        path = Path(file_path)
        if not path.exists():
            raise ImageValidationError(f"File not found: {file_path}")

        ext = path.suffix.lstrip(".").lower()
        resolved_format = format
        if resolved_format is None:
            if ext in ("png",):
                resolved_format = ImageFormat.PNG
            elif ext in ("jpg", "jpeg"):
                resolved_format = ImageFormat.JPEG
            elif ext in ("webp",):
                resolved_format = ImageFormat.WEBP
            elif ext in ("gif",):
                resolved_format = ImageFormat.GIF
            else:
                raise ImageValidationError(f"Cannot infer image format from file extension: {ext}")

        data = path.read_bytes()
        return ImageConverter.from_bytes(data=data, format=resolved_format, detail=detail)
