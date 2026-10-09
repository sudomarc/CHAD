from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ImageFormat(StrEnum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    GIF = "gif"


class ImageDetail(StrEnum):
    LOW = "low"
    HIGH = "high"
    AUTO = "auto"


@dataclass(frozen=True, slots=True)
class ImageAttachment:
    format: ImageFormat
    data_base64: str | None = None
    url: str | None = None
    file_path: str | None = None
    detail: ImageDetail = ImageDetail.AUTO
    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if not self.data_base64 and not self.url and not self.file_path:
            raise ValueError(
                "ImageAttachment must provide at least one source: data_base64, url, or file_path"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "format": self.format.value,
            "data_base64": self.data_base64,
            "url": self.url,
            "file_path": self.file_path,
            "detail": self.detail.value,
            "width": self.width,
            "height": self.height,
            "mime_type": self.mime_type or f"image/{self.format.value}",
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ImageAttachment:
        return cls(
            id=str(data.get("id") or uuid4()),
            format=ImageFormat(str(data["format"])),
            data_base64=str(data["data_base64"])
            if isinstance(data.get("data_base64"), str)
            else None,
            url=str(data["url"]) if isinstance(data.get("url"), str) else None,
            file_path=str(data["file_path"])
            if isinstance(data.get("file_path"), str)
            else None,
            detail=ImageDetail(str(data.get("detail", "auto"))),
            width=int(data["width"]) if data.get("width") is not None else None,
            height=int(data["height"]) if data.get("height") is not None else None,
            mime_type=str(data["mime_type"]) if data.get("mime_type") else None,
        )


@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    images: tuple[ImageAttachment, ...] = field(default_factory=tuple)
    parent_id: str | None = None
    edited_from_id: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None

    def __post_init__(self) -> None:
        if not self.content.strip() and not self.images:
            raise ValueError("message content or images must not be empty")
        if not self.id.strip():
            raise ValueError("message id must not be empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at,
            "images": [img.to_dict() for img in self.images],
            "parent_id": self.parent_id,
            "edited_from_id": self.edited_from_id,
            "correlation_id": self.correlation_id,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Message:
        if not isinstance(data.get("role"), str):
            raise TypeError("message role must be a string")
        if not isinstance(data.get("content"), str):
            raise TypeError("message content must be a string")

        raw_images = data.get("images") or []
        images: tuple[ImageAttachment, ...] = ()
        if isinstance(raw_images, (list, tuple)):
            images = tuple(
                ImageAttachment.from_dict(img)
                for img in raw_images
                if isinstance(img, dict)
            )

        parent_id = data.get("parent_id")
        edited_from_id = data.get("edited_from_id")
        correlation_id = data.get("correlation_id")
        idempotency_key = data.get("idempotency_key")

        return cls(
            id=str(data.get("id") or uuid4()),
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            images=images,
            parent_id=str(parent_id) if isinstance(parent_id, str) else None,
            edited_from_id=str(edited_from_id) if isinstance(edited_from_id, str) else None,
            correlation_id=str(correlation_id) if isinstance(correlation_id, str) else None,
            idempotency_key=str(idempotency_key) if isinstance(idempotency_key, str) else None,
        )
