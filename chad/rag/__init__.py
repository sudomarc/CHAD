"""RAG (Retrieval-Augmented Generation) & File Processing Subsystem for CHAD."""

from chad.rag.chunker import DocumentChunk, TextChunker
from chad.rag.document import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    DocumentExtractor,
    DocumentValidator,
    FileDocument,
)
from chad.rag.pipeline import ChunkLocation, RAGPipeline, RAGSearchResult
from chad.rag.retrieval import (
    EmbeddingProvider,
    HybridRetriever,
    MockEmbeddingProvider,
    VectorStore,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "MAX_FILE_SIZE_BYTES",
    "ChunkLocation",
    "DocumentChunk",
    "DocumentExtractor",
    "DocumentValidator",
    "EmbeddingProvider",
    "FileDocument",
    "HybridRetriever",
    "MockEmbeddingProvider",
    "RAGPipeline",
    "RAGSearchResult",
    "TextChunker",
    "VectorStore",
]
