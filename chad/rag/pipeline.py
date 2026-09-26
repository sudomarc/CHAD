from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chad.agent.research import sanitize_untrusted_content
from chad.rag.chunker import DocumentChunk, TextChunker
from chad.rag.document import DocumentExtractor, DocumentValidator, FileDocument
from chad.rag.retrieval import EmbeddingProvider, HybridRetriever, VectorStore


@dataclass(frozen=True, slots=True)
class ChunkLocation:
    document_id: str
    chunk_id: str
    filename: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int

    def to_citation_label(self) -> str:
        return f"{self.filename} (lines {self.start_line}-{self.end_line})"


@dataclass(frozen=True, slots=True)
class RAGSearchResult:
    query: str
    chunk: DocumentChunk
    score: float
    location: ChunkLocation
    sanitized_text: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "sanitized_text",
            sanitize_untrusted_content(self.chunk.text),
        )


class RAGPipeline:
    """Orchestrates file document ingestion, text extraction, chunking, indexing, and RAG retrieval."""

    def __init__(
        self,
        validator: DocumentValidator | None = None,
        extractor: DocumentExtractor | None = None,
        chunker: TextChunker | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.validator = validator or DocumentValidator()
        self.extractor = extractor or DocumentExtractor()
        self.chunker = chunker or TextChunker()
        self.vector_store = VectorStore(embedding_provider=embedding_provider)
        self.retriever = HybridRetriever(self.vector_store)
        self._documents: dict[str, FileDocument] = {}

    def ingest_file(
        self,
        filename: str,
        content_bytes: bytes,
        metadata: dict[str, Any] | None = None,
    ) -> FileDocument:
        is_valid, msg = self.validator.validate(filename, content_bytes)
        if not is_valid:
            raise ValueError(f"File validation failed for '{filename}': {msg}")

        doc = FileDocument.create(filename, content_bytes, metadata)
        extracted_text = self.extractor.extract_text(doc)

        doc_metadata = {"filename": doc.filename, "file_type": doc.file_type, **doc.metadata}
        chunks = self.chunker.chunk(doc.id, extracted_text, metadata=doc_metadata)

        self.vector_store.add_chunks(chunks)
        self._documents[doc.id] = doc
        return doc

    def search(
        self,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
    ) -> list[RAGSearchResult]:
        raw_results = self.retriever.search(query, top_k=top_k, alpha=alpha)
        rag_results: list[RAGSearchResult] = []

        for chunk, score in raw_results:
            doc = self._documents.get(chunk.document_id)
            filename = doc.filename if doc else chunk.metadata.get("filename", "unknown")

            location = ChunkLocation(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                filename=filename,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                start_char=chunk.start_char,
                end_char=chunk.end_char,
            )

            rag_results.append(
                RAGSearchResult(
                    query=query,
                    chunk=chunk,
                    score=score,
                    location=location,
                )
            )

        return rag_results

    def get_document(self, document_id: str) -> FileDocument | None:
        return self._documents.get(document_id)

    def list_documents(self) -> list[FileDocument]:
        return list(self._documents.values())

    def clear(self) -> None:
        self._documents.clear()
        self.vector_store.clear()
