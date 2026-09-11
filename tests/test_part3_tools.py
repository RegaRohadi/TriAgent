from __future__ import annotations

import pytest

from part3_doc_agent.tools import ToolError, calculate, run_tool

@pytest.mark.parametrize(
    "expression,expected",
    [
        ("2 + 2", "4"),
        ("14 * 14.50 * 12", "2,436"),
        ("14 * 14.50 * 12 * 0.85", "2,070.6"),
        ("0.15 * 4800", "720"),
        ("(30 * 25) - 400", "350"),
        ("-5 + 2", "-3"),
        ("7 % 4", "3"),
        ("2 ** 10", "1,024"),
        ("1,200 + 18 * 30", "1,740"),
        ("USD 14.50 * 2", "29"),
        ("0.1 + 0.2", "0.3"),
    ],
)
def test_arithmetic_is_evaluated(expression: str, expected: str):
    assert calculate(expression) == expected

@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('dir')",
        "open('.env').read()",
        "().__class__.__bases__",
        "[i for i in range(10)]",
        "lambda: 1",
        "price * 12",
    ],
)
def test_code_execution_is_refused(expression: str):
    with pytest.raises(ToolError):
        calculate(expression)

def test_huge_exponent_is_refused_before_it_is_evaluated():
    with pytest.raises(ToolError, match="exponent too large"):
        calculate("9 ** 9 ** 9")

@pytest.mark.parametrize("expression", ["1 / 0", "5 % 0", "7 // 0"])
def test_division_by_zero_is_refused(expression: str):
    with pytest.raises(ToolError, match="division by zero"):
        calculate(expression)

def test_boolean_is_not_a_number():
    with pytest.raises(ToolError):
        calculate("True + 1")

@pytest.mark.parametrize("expression", ["", "   ", "2 +", "* 5"])
def test_malformed_input_is_refused(expression: str):
    with pytest.raises(ToolError):
        calculate(expression)

def test_overlong_expression_is_refused():
    with pytest.raises(ToolError, match="too long"):
        calculate(" + ".join(["1"] * 200))

def test_run_tool_reports_failure_as_data_rather_than_raising():
    result = run_tool("calculator", "1 / 0")

    assert result.ok is False
    assert result.error == "division by zero"
    assert result.output is None
    assert result.tool == "calculator"

def test_run_tool_records_success():
    result = run_tool("calculator", "6 * 7")

    assert result.ok is True
    assert result.output == "42"
    assert result.tool_input == "6 * 7"

def test_unknown_tool_is_reported_not_raised():
    result = run_tool("web_search", "anything")

    assert result.ok is False
    assert "unknown tool" in result.error
