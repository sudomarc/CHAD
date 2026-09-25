from __future__ import annotations

import ast
import operator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chad.agent.research import (
    EvidenceItem,
    MockFetchProvider,
    MockSearchProvider,
    sanitize_untrusted_content,
)
from chad.tools.schema import ToolDefinition, ToolPermissionLevel

if TYPE_CHECKING:
    from chad.tools.registry import ToolRegistry

# Supported operators for safe calculator
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_expr(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        left = _eval_expr(node.left)
        right = _eval_expr(node.right)
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            return _SAFE_OPERATORS[op_type](left, right)  # type: ignore[no-any-return]
        raise ValueError(f"Unsupported operator: {op_type.__name__}")
    if isinstance(node, ast.UnaryOp):
        operand = _eval_expr(node.operand)
        op_type = type(node.op)
        if op_type in _SAFE_OPERATORS:
            return _SAFE_OPERATORS[op_type](operand)  # type: ignore[no-any-return]
        raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


def safe_calculator(expression: str) -> float | int:
    """Evaluates a basic mathematical expression safely using AST."""
    try:
        parsed = ast.parse(expression.strip(), mode="eval")
        return _eval_expr(parsed.body)
    except Exception as exc:
        raise ValueError(f"Invalid or unsafe math expression: {exc}") from exc


CALCULATOR_TOOL = ToolDefinition(
    id="calculator",
    name="Safe Calculator",
    description="Evaluates mathematical expressions safely (addition, subtraction, multiplication, division, powers).",
    input_schema={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
    output_schema={"type": "number"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=5.0,
    side_effect_level="READ_ONLY",
)


def datetime_now() -> str:
    """Returns current UTC ISO timestamp."""
    return datetime.now(UTC).isoformat()


DATETIME_TOOL = ToolDefinition(
    id="datetime_now",
    name="Current Date & Time",
    description="Returns current date and time in UTC ISO-8601 format.",
    input_schema={"type": "object", "properties": {}},
    output_schema={"type": "string"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=5.0,
    side_effect_level="READ_ONLY",
)


def safe_read_file(filepath: str, max_bytes: int = 100_000) -> str:
    """Reads content from a specified file safely."""
    path = Path(filepath).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found or is not a regular file: {filepath}")
    content = path.read_text(encoding="utf-8")
    if len(content.encode("utf-8")) > max_bytes:
        return content[:max_bytes] + "\n...[truncated]"
    return content


FILE_READ_TOOL = ToolDefinition(
    id="read_file",
    name="Read File",
    description="Reads text content from a specified local file.",
    input_schema={
        "type": "object",
        "properties": {
            "filepath": {"type": "string"},
            "max_bytes": {"type": "integer", "default": 100000},
        },
        "required": ["filepath"],
    },
    output_schema={"type": "string"},
    permission_level=ToolPermissionLevel.USER_APPROVAL,
    timeout_seconds=10.0,
    side_effect_level="READ_ONLY",
)


def web_search(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Searches web sources for information regarding a query."""
    provider = MockSearchProvider()
    results = provider.search(query, limit=limit)
    return [
        {
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "score": r.score,
        }
        for r in results
    ]


WEB_SEARCH_TOOL = ToolDefinition(
    id="web_search",
    name="Web Search",
    description="Searches web sources for information regarding a query.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
    output_schema={"type": "array"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=10.0,
    side_effect_level="READ_ONLY",
)


def fetch_page(url: str) -> dict[str, Any]:
    """Fetches text content from a specified URL and applies safety sanitization."""
    provider = MockFetchProvider()
    doc = provider.fetch(url)
    return {
        "url": doc.url,
        "title": doc.title,
        "content": doc.content,
        "sanitized_content": sanitize_untrusted_content(doc.content),
    }


FETCH_PAGE_TOOL = ToolDefinition(
    id="fetch_page",
    name="Fetch Web Page",
    description="Fetches text content from a specified URL and applies safety sanitization.",
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
    output_schema={"type": "object"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=10.0,
    side_effect_level="READ_ONLY",
)


def extract_evidence(text: str, source_url: str, title: str = "Extracted Source", score: float = 1.0) -> dict[str, Any]:
    """Extracts structured evidence items with relevance scoring from text content."""
    item = EvidenceItem(
        id="EV-EXTRACTED",
        source_url=source_url,
        title=title,
        text=text,
        relevance_score=score,
    )
    return {
        "id": item.id,
        "source_url": item.source_url,
        "title": item.title,
        "text": item.text,
        "relevance_score": item.relevance_score,
        "sanitized_text": item.sanitized_text,
    }


EXTRACT_EVIDENCE_TOOL = ToolDefinition(
    id="extract_evidence",
    name="Extract Evidence",
    description="Extracts structured evidence items with relevance scoring from text content.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "source_url": {"type": "string"},
            "title": {"type": "string", "default": "Extracted Source"},
            "score": {"type": "number", "default": 1.0},
        },
        "required": ["text", "source_url"],
    },
    output_schema={"type": "object"},
    permission_level=ToolPermissionLevel.ALWAYS_ALLOW,
    timeout_seconds=5.0,
    side_effect_level="READ_ONLY",
)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Registers all built-in tools into a ToolRegistry instance."""
    registry.register(CALCULATOR_TOOL, safe_calculator)
    registry.register(DATETIME_TOOL, datetime_now)
    registry.register(FILE_READ_TOOL, safe_read_file)
    registry.register(WEB_SEARCH_TOOL, web_search)
    registry.register(FETCH_PAGE_TOOL, fetch_page)
    registry.register(EXTRACT_EVIDENCE_TOOL, extract_evidence)
