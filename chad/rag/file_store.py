from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class FileType(StrEnum):
    TXT = "txt"
    MARKDOWN = "md"
    JSON = "json"
    CSV = "csv"
    CODE = "code"
    PDF = "pdf"
    DOCX = "docx"
    UNKNOWN = "unknown"


# Supported code extensions
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".rs",
    ".go", ".cpp", ".c", ".h", ".java", ".sh", ".yaml", ".yml", ".toml",
}


@dataclass(slots=True)
class FileDocument:
    file_id: str
    filename: str
    file_type: FileType
    text_content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        raw_hash = hashlib.sha256(f"{self.filename}:{self.text_content}".encode("utf-8")).hexdigest()
        object.__setattr__(self, "content_hash", raw_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "file_type": self.file_type.value,
            "text_content": self.text_content,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FileDocument:
        doc = cls(
            file_id=str(data["file_id"]),
            filename=str(data["filename"]),
            file_type=FileType(data["file_type"]),
            text_content=str(data["text_content"]),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
        )
        return doc


class FileStore:
    """Manages document storage, type detection, and validation."""

    def __init__(self, max_file_size_bytes: int = 10_000_000) -> None:
        self.max_file_size_bytes = max_file_size_bytes
        self._documents: dict[str, FileDocument] = {}

    def detect_file_type(self, filename: str) -> FileType:
        ext = Path(filename).suffix.lower()
        if ext in (".txt", ".text"):
            return FileType.TXT
        if ext in (".md", ".markdown"):
            return FileType.MARKDOWN
        if ext == ".json":
            return FileType.JSON
        if ext == ".csv":
            return FileType.CSV
        if ext in CODE_EXTENSIONS:
            return FileType.CODE
        if ext == ".pdf":
            return FileType.PDF
        if ext in (".docx", ".doc"):
            return FileType.DOCX
        return FileType.UNKNOWN

    def validate_file(self, filename: str, content_bytes: bytes) -> FileType:
        if len(content_bytes) > self.max_file_size_bytes:
            raise ValueError(
                f"File '{filename}' size ({len(content_bytes)} bytes) exceeds max limit of {self.max_file_size_bytes} bytes."
            )
        return self.detect_file_type(filename)

    def add_document(self, doc: FileDocument) -> None:
        if not doc.file_id:
            raise ValueError("Document file_id cannot be empty.")
        self._documents[doc.file_id] = doc

    def get_document(self, file_id: str) -> FileDocument:
        if file_id not in self._documents:
            raise KeyError(f"Document with ID '{file_id}' not found.")
        return self._documents[file_id]

    def delete_document(self, file_id: str) -> bool:
        if file_id in self._documents:
            del self._documents[file_id]
            return True
        return False

    def list_documents(self) -> list[FileDocument]:
        return list(self._documents.values())
