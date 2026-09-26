from __future__ import annotations

import math
import re
from collections import Counter
from typing import Protocol, Sequence

from chad.rag.chunker import DocumentChunk


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class MockEmbeddingProvider:
    """Deterministic mock embedding provider generating normalized 64-dimensional dense vectors."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            words = re.findall(r"\w+", text.lower())
            if not words:
                results.append(vec)
                continue

            for word in words:
                hash_val = hash(word)
                idx = abs(hash_val) % self.dim
                vec[idx] += 1.0

            # L2 normalize
            norm = math.sqrt(sum(v * v for v in vec))
            if norm > 0:
                vec = [v / norm for v in vec]
            results.append(vec)
        return results


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class VectorStore:
    """In-memory vector store supporting cosine similarity search over chunks."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or MockEmbeddingProvider()
        self._chunks: dict[str, DocumentChunk] = {}
        self._vectors: dict[str, list[float]] = {}

    def add_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]] | None = None,
    ) -> None:
        if not chunks:
            return

        if embeddings is None:
            texts = [c.text for c in chunks]
            embeddings = self.embedding_provider.embed(texts)

        for chunk, vec in zip(chunks, embeddings):
            self._chunks[chunk.chunk_id] = chunk
            self._vectors[chunk.chunk_id] = vec

    def search_vector(self, query: str, top_k: int = 5) -> list[tuple[DocumentChunk, float]]:
        if not self._chunks:
            return []

        query_vec = self.embedding_provider.embed([query])[0]
        results: list[tuple[DocumentChunk, float]] = []

        for chunk_id, chunk in self._chunks.items():
            vec = self._vectors[chunk_id]
            score = cosine_similarity(query_vec, vec)
            results.append((chunk, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        return self._chunks.get(chunk_id)

    def get_all_chunks(self) -> list[DocumentChunk]:
        return list(self._chunks.values())

    def clear(self) -> None:
        self._chunks.clear()
        self._vectors.clear()


class HybridRetriever:
    """Combines vector similarity search with BM25/keyword term matching for hybrid RAG retrieval."""

    def __init__(self, vector_store: VectorStore) -> None:
        self.vector_store = vector_store

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[tuple[DocumentChunk, float]]:
        all_chunks = self.vector_store.get_all_chunks()
        if not all_chunks:
            return []

        # Vector scores keyed by chunk_id
        vector_results = {
            chunk.chunk_id: score
            for chunk, score in self.vector_store.search_vector(query, top_k=len(all_chunks))
        }

        # Keyword scores (TF-IDF / Overlap)
        query_words = set(re.findall(r"\w+", query.lower()))
        keyword_scores: dict[str, float] = {}

        if query_words:
            doc_counts = Counter()
            for chunk in all_chunks:
                words = set(re.findall(r"\w+", chunk.text.lower()))
                for qw in query_words:
                    if qw in words:
                        doc_counts[qw] += 1

            num_docs = len(all_chunks)
            idf = {
                qw: math.log((num_docs + 1) / (count + 1)) + 1
                for qw, count in doc_counts.items()
            }

            for chunk in all_chunks:
                chunk_words = re.findall(r"\w+", chunk.text.lower())
                chunk_counts = Counter(chunk_words)
                score = 0.0
                for qw in query_words:
                    if qw in chunk_counts:
                        tf = chunk_counts[qw] / max(len(chunk_words), 1)
                        score += tf * idf.get(qw, 1.0)
                keyword_scores[chunk.chunk_id] = score

            # Normalize keyword scores
            max_kw = max(keyword_scores.values()) if keyword_scores and max(keyword_scores.values()) > 0 else 1.0
            for cid in keyword_scores:
                keyword_scores[cid] /= max_kw

        # Combine scores
        combined: list[tuple[DocumentChunk, float]] = []
        for chunk in all_chunks:
            v_score = vector_results.get(chunk.chunk_id, 0.0)
            k_score = keyword_scores.get(chunk.chunk_id, 0.0)
            final_score = (alpha * v_score) + ((1.0 - alpha) * k_score)
            combined.append((chunk, final_score))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]
