from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from chad.rag.chunker import DocumentChunk, DocumentChunker
from chad.rag.file_store import FileDocument, FileStore
from chad.rag.parsers import DocumentParser
from chad.rag.vector_store import VectorStore


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float
    retrieval_type: str = "hybrid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "retrieval_type": self.retrieval_type,
        }


@dataclass(frozen=True, slots=True)
class SourceCitation:
    citation_id: str
    doc_id: str
    filename: str
    chunk_index: int
    score: float
    excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "citation_id": self.citation_id,
            "doc_id": self.doc_id,
            "filename": self.filename,
            "chunk_index": self.chunk_index,
            "score": self.score,
            "excerpt": self.excerpt,
        }


class HybridRetriever:
    """Hybrid retriever combining keyword frequency and vector semantic similarity via Reciprocal Rank Fusion (RRF)."""

    def __init__(self, vector_store: VectorStore, k_rrf: int = 60) -> None:
        self.vector_store = vector_store
        self.k_rrf = k_rrf

    def _keyword_search(self, query: str, top_k: int = 10) -> list[tuple[DocumentChunk, float]]:
        query_words = set(re.findall(r"\w+", query.lower()))
        if not query_words:
            return []

        results: list[tuple[DocumentChunk, float]] = []
        for chunk in self.vector_store._chunks.values():
            text_words = re.findall(r"\w+", chunk.text.lower())
            if not text_words:
                continue
            matches = sum(1 for w in query_words if w in text_words)
            if matches > 0:
                score = matches / len(query_words)
                results.append((chunk, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        vector_results = self.vector_store.search(query, top_k=top_k * 2)
        keyword_results = self._keyword_search(query, top_k=top_k * 2)

        rrf_scores: dict[str, float] = {}
        chunk_map: dict[str, DocumentChunk] = {}

        for rank, (chunk, _score) in enumerate(vector_results, start=1):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k_rrf + rank))

        for rank, (chunk, _score) in enumerate(keyword_results, start=1):
            cid = chunk.chunk_id
            chunk_map[cid] = chunk
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k_rrf + rank))

        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        return [
            RetrievalResult(
                chunk=chunk_map[cid],
                score=rrf_scores[cid],
                retrieval_type="hybrid",
            )
            for cid in sorted_cids[:top_k]
        ]


@dataclass(slots=True)
class RAGQueryResponse:
    query: str
    results: list[RetrievalResult]
    citations: list[SourceCitation]
    formatted_context: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "citations": [c.to_dict() for c in self.citations],
            "formatted_context": self.formatted_context,
        }


class RAGEngine:
    """End-to-end RAG Engine orchestrating file storage, extraction, chunking, indexing, and hybrid retrieval."""

    def __init__(
        self,
        file_store: FileStore | None = None,
        chunker: DocumentChunker | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.file_store = file_store or FileStore()
        self.chunker = chunker or DocumentChunker()
        self.vector_store = vector_store or VectorStore()
        self.retriever = HybridRetriever(self.vector_store)

    def ingest_file(
        self,
        file_id: str,
        filename: str,
        content_bytes: bytes,
        extra_metadata: dict[str, Any] | None = None,
    ) -> FileDocument:
        file_type = self.file_store.validate_file(filename, content_bytes)
        parsed_text = DocumentParser.parse(filename, content_bytes, file_type)

        doc = FileDocument(
            file_id=file_id,
            filename=filename,
            file_type=file_type,
            text_content=parsed_text,
            metadata=extra_metadata or {},
        )

        self.file_store.add_document(doc)

        chunks = self.chunker.chunk_text(
            doc_id=doc.file_id,
            filename=doc.filename,
            text=parsed_text,
            extra_metadata={"file_type": file_type.value},
        )

        self.vector_store.add_chunks(chunks)
        return doc

    def ingest_text(
        self,
        file_id: str,
        filename: str,
        text_content: str,
        extra_metadata: dict[str, Any] | None = None,
    ) -> FileDocument:
        return self.ingest_file(
            file_id=file_id,
            filename=filename,
            content_bytes=text_content.encode("utf-8"),
            extra_metadata=extra_metadata,
        )

    def remove_file(self, file_id: str) -> bool:
        doc_deleted = self.file_store.delete_document(file_id)
        self.vector_store.delete_document_chunks(file_id)
        return doc_deleted

    def query(self, query: str, top_k: int = 5) -> RAGQueryResponse:
        retrieved = self.retriever.retrieve(query, top_k=top_k)

        citations: list[SourceCitation] = []
        context_blocks: list[str] = []

        for idx, res in enumerate(retrieved, start=1):
            citation_id = f"CIT-{idx:02d}"
            excerpt = res.chunk.text[:200].replace("\n", " ").strip()
            citation = SourceCitation(
                citation_id=citation_id,
                doc_id=res.chunk.doc_id,
                filename=res.chunk.filename,
                chunk_index=res.chunk.chunk_index,
                score=res.score,
                excerpt=excerpt,
            )
            citations.append(citation)

            context_blocks.append(
                f"[{citation_id}] Source: {res.chunk.filename} (Chunk #{res.chunk.chunk_index})\n"
                f"{res.chunk.text}\n"
            )

        formatted_context = "\n---\n".join(context_blocks) if context_blocks else "No relevant documents found."

        return RAGQueryResponse(
            query=query,
            results=retrieved,
            citations=citations,
            formatted_context=formatted_context,
        )
