"""Decorator-based function tool registry with OpenTelemetry tracing."""

import functools
from collections.abc import Callable
from typing import Any

from azure.ai.agents.models import FunctionTool, ToolSet
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class ToolRegistry:
    """Collects tool functions via decorator and builds a Foundry ToolSet."""

    def __init__(self) -> None:
        self._functions: list[Callable[..., Any]] = []

    def register(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(f"tool.{fn.__name__}") as span:
                span.set_attribute("tool.name", fn.__name__)
                return fn(*args, **kwargs)

        self._functions.append(wrapper)
        return wrapper

    def build_toolset(self) -> ToolSet:
        toolset = ToolSet()
        toolset.add(FunctionTool(self._functions))
        return toolset
