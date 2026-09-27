from __future__ import annotations

from typing import Any

from chad.rag.engine import RAGEngine
from chad.tools.registry import ToolRegistry
from chad.tools.schema import ToolDefinition, ToolPermissionLevel

_GLOBAL_RAG_ENGINE = RAGEngine()


def get_rag_engine() -> RAGEngine:
    return _GLOBAL_RAG_ENGINE


def rag_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """Searches indexed RAG knowledge base for relevant document chunks and source citations."""
    response = get_rag_engine().query(query, top_k=top_k)
    return response.to_dict()


RAG_SEARCH_TOOL = ToolDefinition(
    id="rag_search",
    name="RAG Knowledge Search",
    description="Searches indexed knowledge base for relevant document chunks, context, and citations.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    output_schema={"type": "object"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=10.0,
    side_effect_level="READ_ONLY",
)


def rag_index_file(file_id: str, filename: str, content: str) -> dict[str, Any]:
    """Indexes a text file document into the RAG knowledge store."""
    doc = get_rag_engine().ingest_text(file_id=file_id, filename=filename, text_content=content)
    return doc.to_dict()


RAG_INDEX_TOOL = ToolDefinition(
    id="rag_index_file",
    name="RAG Index File",
    description="Indexes a document/file into the RAG knowledge store for semantic search.",
    input_schema={
        "type": "object",
        "properties": {
            "file_id": {"type": "string"},
            "filename": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["file_id", "filename", "content"],
    },
    output_schema={"type": "object"},
    permission_level=ToolPermissionLevel.USER_APPROVAL,
    timeout_seconds=15.0,
    side_effect_level="MODIFIES_STATE",
)


def register_rag_tools(registry: ToolRegistry) -> None:
    """Registers RAG search and file indexing tools with a ToolRegistry instance."""
    registry.register(RAG_SEARCH_TOOL, rag_search)
    registry.register(RAG_INDEX_TOOL, rag_index_file)
