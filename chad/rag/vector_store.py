from __future__ import annotations

import math
import re
from typing import Protocol

from chad.rag.chunker import DocumentChunk


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two numeric vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class EmbeddingProvider(Protocol):
    def embed_text(self, text: str) -> list[float]:
        ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...


class MockEmbeddingProvider:
    """Deterministic hashing embedding provider using standard term frequency features."""

    def __init__(self, dim: int = 128) -> None:
        self.dim = dim

    def embed_text(self, text: str) -> list[float]:
        tokens = re.findall(r"\w+", text.lower())
        if not tokens:
            return [0.0] * self.dim

        vec = [0.0] * self.dim
        for token in tokens:
            idx = sum(ord(c) for c in token) % self.dim
            vec[idx] += 1.0

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class VectorStore:
    """In-memory vector store for DocumentChunk items with cosine similarity search."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self._chunks: dict[str, DocumentChunk] = {}
        self._vectors: dict[str, list[float]] = {}

    def add_chunk(self, chunk: DocumentChunk) -> None:
        vec = self.embedding_provider.embed_text(chunk.text)
        self._chunks[chunk.chunk_id] = chunk
        self._vectors[chunk.chunk_id] = vec

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        for chunk in chunks:
            self.add_chunk(chunk)

    def search(self, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
        if not self._chunks:
            return []

        query_vec = self.embedding_provider.embed_text(query)
        scores: list[tuple[DocumentChunk, float]] = []

        for chunk_id, vec in self._vectors.items():
            sim = cosine_similarity(query_vec, vec)
            scores.append((self._chunks[chunk_id], sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def delete_document_chunks(self, doc_id: str) -> int:
        to_delete = [cid for cid, chunk in self._chunks.items() if chunk.doc_id == doc_id]
        for cid in to_delete:
            del self._chunks[cid]
            del self._vectors[cid]
        return len(to_delete)

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
        self._vectors.clear()
