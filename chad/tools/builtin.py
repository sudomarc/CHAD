from __future__ import annotations

import ast
import operator
from datetime import UTC, datetime
from pathlib import Path

from chad.tools.schema import ToolDefinition, ToolPermissionLevel

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
