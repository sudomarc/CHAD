from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    start_line: int
    end_line: int
    metadata: dict[str, Any] = field(default_factory=dict)


class TextChunker:
    """Splits document text into overlapping chunks with character and line position tracking."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(
        self,
        document_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[DocumentChunk]:
        if not text or not text.strip():
            return []

        base_metadata = metadata or {}
        chunks: list[DocumentChunk] = []

        line_starts = self._compute_line_starts(text)

        text_len = len(text)
        start = 0
        chunk_index = 0

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # Try to break at a word boundary/newline if not at the end of the text
            if end < text_len:
                break_point = self._find_break_point(text, start, end)
                if break_point > start:
                    end = break_point

            chunk_text = text[start:end]
            if chunk_text.strip():
                start_line = self._char_to_line(start, line_starts)
                end_line = self._char_to_line(end - 1 if end > start else start, line_starts)

                chunk_id = f"{document_id}-C{chunk_index:04d}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        text=chunk_text,
                        chunk_index=chunk_index,
                        start_char=start,
                        end_char=end,
                        start_line=start_line,
                        end_line=end_line,
                        metadata=base_metadata,
                    )
                )
                chunk_index += 1

            if end >= text_len:
                break

            # Move start forward with overlap, ensuring forward progress
            next_start = end - self.chunk_overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start

        return chunks

    def _compute_line_starts(self, text: str) -> list[int]:
        line_starts = [0]
        for idx, char in enumerate(text):
            if char == "\n":
                line_starts.append(idx + 1)
        return line_starts

    def _char_to_line(self, char_idx: int, line_starts: list[int]) -> int:
        # 1-based line number lookup
        left, right = 0, len(line_starts) - 1
        line = 0
        while left <= right:
            mid = (left + right) // 2
            if line_starts[mid] <= char_idx:
                line = mid
                left = mid + 1
            else:
                right = mid - 1
        return line + 1

    def _find_break_point(self, text: str, start: int, end: int) -> int:
        # Search backwards from end for space or newline within the chunk window
        lookback_min = max(start + (self.chunk_size // 2), start + 1)
        for idx in range(end, lookback_min - 1, -1):
            if idx < len(text) and text[idx] in ("\n", " ", "\t", ".", ";"):
                return idx + 1
        return end
