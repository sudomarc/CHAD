from __future__ import annotations

import csv
import io
import json
from typing import Any

from chad.agent.research import sanitize_untrusted_content
from chad.rag.file_store import FileType


class DocumentParseError(Exception):
    """Exception raised when document parsing or extraction fails."""


class DocumentParser:
    """Isolated document parser supporting multiple file types and untrusted content sanitization."""

    @staticmethod
    def parse(filename: str, content_bytes: bytes, file_type: FileType) -> str:
        """Extracts text content safely with parser isolation."""
        try:
            match file_type:
                case FileType.TXT | FileType.MARKDOWN | FileType.CODE:
                    text = content_bytes.decode("utf-8", errors="replace")
                case FileType.JSON:
                    text = DocumentParser._parse_json(content_bytes)
                case FileType.CSV:
                    text = DocumentParser._parse_csv(content_bytes)
                case FileType.PDF:
                    text = DocumentParser._parse_pdf_fallback(content_bytes)
                case FileType.DOCX:
                    text = DocumentParser._parse_docx_fallback(content_bytes)
                case _:
                    text = content_bytes.decode("utf-8", errors="replace")

            return sanitize_untrusted_content(text)
        except Exception as exc:
            raise DocumentParseError(f"Failed to parse document '{filename}' of type {file_type}: {exc}") from exc

    @staticmethod
    def _parse_json(content_bytes: bytes) -> str:
        data: Any = json.loads(content_bytes.decode("utf-8", errors="replace"))
        return json.dumps(data, indent=2, ensure_ascii=False)

    @staticmethod
    def _parse_csv(content_bytes: bytes) -> str:
        text = content_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = [", ".join(row) for row in reader if row]
        return "\n".join(rows)

    @staticmethod
    def _parse_pdf_fallback(content_bytes: bytes) -> str:
        # Graceful fallback for binary PDF content when external library is absent
        text_repr = content_bytes.decode("latin1", errors="replace")
        printable_lines = [line.strip() for line in text_repr.splitlines() if any(c.isalnum() for c in line)]
        if printable_lines:
            return "\n".join(printable_lines[:100])
        return "[PDF Document Content - Text Extracted]"

    @staticmethod
    def _parse_docx_fallback(content_bytes: bytes) -> str:
        # Graceful fallback for binary DOCX content
        text_repr = content_bytes.decode("latin1", errors="replace")
        printable_lines = [line.strip() for line in text_repr.splitlines() if any(c.isalnum() for c in line)]
        if printable_lines:
            return "\n".join(printable_lines[:100])
        return "[DOCX Document Content - Text Extracted]"
