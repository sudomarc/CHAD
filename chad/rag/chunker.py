from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    doc_id: str
    filename: str
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "chunk_index": self.chunk_index,
            "text": self.text,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocumentChunk:
        return cls(
            chunk_id=str(data["chunk_id"]),
            doc_id=str(data["doc_id"]),
            filename=str(data["filename"]),
            chunk_index=int(data["chunk_index"]),
            text=str(data["text"]),
            start_offset=int(data["start_offset"]),
            end_offset=int(data["end_offset"]),
            metadata=dict(data.get("metadata", {})),
        )


class DocumentChunker:
    """Splits document text into overlapping chunks with source offset tracking."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size.")

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, doc_id: str, filename: str, text: str, extra_metadata: dict[str, Any] | None = None) -> list[DocumentChunk]:
        if not text.strip():
            return []

        chunks: list[DocumentChunk] = []
        extra_meta = extra_metadata or {}

        # Split into paragraphs or line blocks
        paragraphs = re.split(r"\n\s*\n", text)

        current_text = ""
        start_offset = 0
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_text) + len(para) + 1 <= self.chunk_size:
                if current_text:
                    current_text += "\n\n" + para
                else:
                    current_text = para
            else:
                if current_text:
                    end_offset = start_offset + len(current_text)
                    chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            filename=filename,
                            chunk_index=chunk_idx,
                            text=current_text,
                            start_offset=start_offset,
                            end_offset=end_offset,
                            metadata=extra_meta,
                        )
                    )
                    chunk_idx += 1
                    # advance offset considering overlap
                    step = max(1, len(current_text) - self.chunk_overlap)
                    start_offset += step

                # If paragraph itself is larger than chunk_size, hard-split
                while len(para) > self.chunk_size:
                    slice_text = para[: self.chunk_size]
                    end_offset = start_offset + len(slice_text)
                    chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_id,
                            filename=filename,
                            chunk_index=chunk_idx,
                            text=slice_text,
                            start_offset=start_offset,
                            end_offset=end_offset,
                            metadata=extra_meta,
                        )
                    )
                    chunk_idx += 1
                    para = para[self.chunk_size - self.chunk_overlap :]
                    start_offset += self.chunk_size - self.chunk_overlap

                current_text = para

        if current_text:
            end_offset = start_offset + len(current_text)
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    filename=filename,
                    chunk_index=chunk_idx,
                    text=current_text,
                    start_offset=start_offset,
                    end_offset=end_offset,
                    metadata=extra_meta,
                )
            )

        return chunks
