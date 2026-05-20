"""Shared fixtures for evalkit tests."""

import pytest

from evalkit import EvalContext


@pytest.fixture
def basic_context() -> EvalContext:
    """A basic evaluation context with typical fields populated."""
    return EvalContext(
        query="What is the capital of France?",
        response="The capital of France is Paris. It is the largest city in France.",
        context="France is a country in Europe. Paris is the capital and largest city of France.",
        latency_ms=500.0,
        tokens_in=100,
        tokens_out=50,
        cost_usd=0.002,
    )


@pytest.fixture
def empty_context() -> EvalContext:
    return EvalContext()


@pytest.fixture
def tool_context() -> EvalContext:
    """Context with tool calls."""
    return EvalContext(
        query="Search for Python tutorials",
        response="Here are some Python tutorials I found.",
        tool_calls=[
            {"name": "search", "arguments": {"query": "Python tutorials"}},
            {"name": "summarize", "arguments": {"text": "..."}},
        ],
        metadata={"tools_expected": True, "expected_tools": ["search"]},
    )
