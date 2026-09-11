from __future__ import annotations

import ast
import operator
import re
import time
from dataclasses import dataclass
from typing import Callable

from core.logging_config import get_logger
from part3_doc_agent.models import ToolResult

log = get_logger(__name__)

class ToolError(ValueError):
    pass

_ALLOWED_BINOPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

MAX_EXPRESSION_CHARS = 200
MAX_NODES = 100
MAX_EXPONENT = 64
MAX_POW_BASE = 1_000_000

_STRIP_PATTERN = re.compile(
    r"(?<=\d),(?=\d{3}\b)"
    r"|[$€£]"
    r"|\b(?:USD|SGD|MYR|IDR|EUR|GBP)\b",
    re.I,
)

def _format_number(value: float) -> str:
    rounded = round(float(value), 10)
    if abs(rounded - round(rounded)) < 1e-9 and abs(rounded) < 1e15:
        return f"{int(round(rounded)):,}"
    return f"{rounded:,.4f}".rstrip("0").rstrip(".")

def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError(f"only numbers are allowed, got {type(node.value).__name__}")
        return float(node.value)

    if isinstance(node, ast.UnaryOp):
        handler = _ALLOWED_UNARY.get(type(node.op))
        if handler is None:
            raise ToolError(f"unsupported unary operator: {type(node.op).__name__}")
        return handler(_eval_node(node.operand))

    if isinstance(node, ast.BinOp):
        handler = _ALLOWED_BINOPS.get(type(node.op))
        if handler is None:
            raise ToolError(f"unsupported operator: {type(node.op).__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > MAX_EXPONENT or abs(left) > MAX_POW_BASE):
            raise ToolError(f"exponent too large (limit: base {MAX_POW_BASE}, power {MAX_EXPONENT})")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ToolError("division by zero")
        return handler(left, right)

    raise ToolError(f"expression contains something that is not arithmetic: {type(node).__name__}")

def calculate(expression: str) -> str:
    cleaned = _STRIP_PATTERN.sub("", expression or "").strip()
    if not cleaned:
        raise ToolError("empty expression")
    if len(cleaned) > MAX_EXPRESSION_CHARS:
        raise ToolError(f"expression too long ({len(cleaned)} chars, limit {MAX_EXPRESSION_CHARS})")

    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"not a valid arithmetic expression: {exc.msg}") from exc

    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > MAX_NODES:
        raise ToolError(f"expression too complex ({node_count} nodes, limit {MAX_NODES})")

    try:
        value = _eval_node(tree.body)
    except OverflowError as exc:
        raise ToolError("result is too large to represent") from exc

    if value != value or value in (float("inf"), float("-inf")):
        raise ToolError("result is not a finite number")
    return _format_number(value)

@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    run: Callable[[str], str]

TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec(
        name="calculator",
        description=(
            "Evaluates one arithmetic expression using + - * / % ** and parentheses. "
            "Use it for actual computation, never for recalling a number that is already stated."
        ),
        run=calculate,
    ),
}

def run_tool(name: str, tool_input: str) -> ToolResult:
    started = time.perf_counter()
    spec = TOOLS.get(name)
    if spec is None:
        return ToolResult(tool=name, tool_input=tool_input, ok=False, error=f"unknown tool: {name}")

    try:
        output = spec.run(tool_input)
    except ToolError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        log.warning("tool_refused", tool=name, tool_input=tool_input[:120], error=str(exc))
        return ToolResult(tool=name, tool_input=tool_input, ok=False, error=str(exc), elapsed_ms=elapsed_ms)
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        log.error("tool_failed", tool=name, error=f"{type(exc).__name__}: {exc}")
        return ToolResult(
            tool=name,
            tool_input=tool_input,
            ok=False,
            error=f"{type(exc).__name__}: {exc}",
            elapsed_ms=elapsed_ms,
        )

    elapsed_ms = round((time.perf_counter() - started) * 1000)
    log.info("tool_called", tool=name, tool_input=tool_input[:120], output=output[:120], elapsed_ms=elapsed_ms)
    return ToolResult(tool=name, tool_input=tool_input, output=output, ok=True, elapsed_ms=elapsed_ms)
