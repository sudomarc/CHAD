from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".pdf",
    ".docx",
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".yaml",
    ".yml",
    ".c",
    ".cpp",
    ".rs",
    ".go",
    ".java",
    ".sh",
}

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@dataclass(frozen=True, slots=True)
class FileDocument:
    id: str
    filename: str
    file_type: str
    content_bytes: bytes
    size: int
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        filename: str,
        content_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> FileDocument:
        ext = os.path.splitext(filename)[1].lower()
        file_type = ext.lstrip(".") or "unknown"
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        doc_id = f"DOC-{content_hash[:12]}"
        size = len(content_bytes)
        return cls(
            id=doc_id,
            filename=filename,
            file_type=file_type,
            content_bytes=content_bytes,
            size=size,
            content_hash=content_hash,
            metadata=metadata or {},
        )


class DocumentValidator:
    def __init__(
        self,
        allowed_extensions: set[str] | None = None,
        max_file_size_bytes: int = MAX_FILE_SIZE_BYTES,
    ) -> None:
        self.allowed_extensions = allowed_extensions or ALLOWED_EXTENSIONS
        self.max_file_size_bytes = max_file_size_bytes

    def validate(self, filename: str, content_bytes: bytes) -> tuple[bool, str]:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.allowed_extensions:
            return False, f"Unsupported file extension '{ext}'. Allowed extensions: {sorted(self.allowed_extensions)}"

        if len(content_bytes) > self.max_file_size_bytes:
            return False, f"File size {len(content_bytes)} bytes exceeds maximum allowed limit of {self.max_file_size_bytes} bytes."

        if len(content_bytes) == 0:
            return False, "File content is empty."

        return True, "Valid"


class DocumentExtractor:
    """Extracts structured plain text from various file formats."""

    def extract_text(self, doc: FileDocument) -> str:
        ext = f".{doc.file_type.lower()}"

        if ext in {".txt", ".md", ".markdown", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".yaml", ".yml", ".c", ".cpp", ".rs", ".go", ".java", ".sh"}:
            return self._decode_text(doc.content_bytes)

        if ext == ".json":
            return self._extract_json(doc.content_bytes)

        if ext == ".csv":
            return self._extract_csv(doc.content_bytes)

        if ext == ".pdf":
            return self._extract_pdf(doc.content_bytes, doc.filename)

        if ext == ".docx":
            return self._extract_docx(doc.content_bytes, doc.filename)

        return self._decode_text(doc.content_bytes)

    def _decode_text(self, raw: bytes) -> str:
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="replace")

    def _extract_json(self, raw: bytes) -> str:
        text = self._decode_text(raw)
        try:
            data = json.loads(text)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            return text

    def _extract_csv(self, raw: bytes) -> str:
        text = self._decode_text(raw)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)

    def _extract_pdf(self, raw: bytes, filename: str) -> str:
        # Basic PDF stream text extraction fallback without heavy binary dependencies
        text = self._decode_text(raw)
        # Extract printable text blocks from PDF stream objects
        printable = []
        in_text_block = False
        for line in text.splitlines():
            if "BT" in line:
                in_text_block = True
            elif "ET" in line:
                in_text_block = False
            elif in_text_block or line.startswith("(") or "Tj" in line or "TJ" in line:
                cleaned = line.replace("(", "").replace(")", "").replace("Tj", "").replace("TJ", "").strip()
                if cleaned:
                    printable.append(cleaned)

        if printable:
            return "\n".join(printable)

        # Fallback to plain readable ASCII strings
        raw_str = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13) else " " for b in raw)
        lines = [line.strip() for line in raw_str.splitlines() if len(line.strip()) > 3]
        return f"[PDF Document: {filename}]\n" + "\n".join(lines)

    def _extract_docx(self, raw: bytes, filename: str) -> str:
        # Basic DOCX document xml text extraction fallback
        raw_str = "".join(chr(b) if 32 <= b <= 126 or b in (10, 13) else " " for b in raw)
        lines = [line.strip() for line in raw_str.splitlines() if len(line.strip()) > 3]
        return f"[DOCX Document: {filename}]\n" + "\n".join(lines)
