"""Core data models for the evaluation framework."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvalDimension(StrEnum):
    """Built-in evaluation dimensions. Users can extend with custom values."""

    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    GROUNDEDNESS = "groundedness"
    LATENCY = "latency"
    TOOL_UTILIZATION = "tool_utilization"
    SAFETY = "safety"
    COST_EFFICIENCY = "cost_efficiency"
    STRUCTURED_OUTPUT = "structured_output"


class Finding(BaseModel, frozen=True):
    """A single evaluation finding — issue, warning, or strength."""

    severity: str = Field(description="critical | warning | info | strength")
    message: str = Field(description="Human-readable finding description")
    location: str = Field(default="", description="Where in the output the finding was detected")
    suggestion: str = Field(default="", description="Suggested improvement")


class EvalResult(BaseModel, frozen=True):
    """Result of evaluating a single dimension."""

    dimension: str = Field(description="The dimension being evaluated")
    score: float = Field(ge=0.0, le=1.0, description="Normalized score (0.0–1.0)")
    max_score: float = Field(default=1.0, description="Maximum possible score")
    findings: tuple[Finding, ...] = Field(default=(), description="Detailed findings")
    summary: str = Field(default="", description="Brief summary of the evaluation")

    @property
    def normalized_score(self) -> float:
        """Score normalized to max_score."""
        return self.score / self.max_score if self.max_score > 0 else 0.0


class EvalContext(BaseModel):
    """Base evaluation context — users subclass for their domain.

    Contains the inputs needed to evaluate an agent's output. Override
    with domain-specific fields.

    Example::

        class ChatEvalContext(EvalContext):
            user_query: str
            agent_response: str
            context_documents: list[str] = []
            tool_calls: list[dict] = []
    """

    query: str = Field(default="", description="The user's input query")
    response: str = Field(default="", description="The agent's response")
    context: str = Field(default="", description="Retrieved context or grounding data")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, description="Tool calls made by the agent")
    expected_output: str = Field(default="", description="Expected/reference output for comparison")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds")
    tokens_in: int = Field(default=0, description="Input tokens consumed")
    tokens_out: int = Field(default=0, description="Output tokens produced")
    cost_usd: float = Field(default=0.0, description="Cost in USD")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional domain-specific data")


class GateThreshold(BaseModel, frozen=True):
    """Quality gate configuration."""

    global_minimum: float = Field(default=0.6, description="Minimum aggregate score to pass")
    dimension_minimums: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension minimum scores",
    )
    auto_fail_dimensions: tuple[str, ...] = Field(
        default=(),
        description="Dimensions that cause auto-fail if below threshold",
    )


class GateResult(BaseModel, frozen=True):
    """Result of applying a quality gate to evaluation scores."""

    passed: bool = Field(description="Whether the gate passed")
    aggregate_score: float = Field(description="Weighted aggregate score")
    failing_dimensions: tuple[str, ...] = Field(default=(), description="Dimensions that failed")
    gate_message: str = Field(default="", description="Human-readable gate result")


class DimensionWeight(BaseModel, frozen=True):
    """Weight for a single evaluation dimension."""

    dimension: str
    weight: float = Field(default=1.0, ge=0.0)


class QualityReport(BaseModel, frozen=True):
    """Full evaluation report with scores, gate result, and recommendations."""

    dimension_results: tuple[EvalResult, ...] = Field(default=())
    aggregate_score: float = Field(default=0.0)
    gate: GateResult = Field(default_factory=lambda: GateResult(passed=False, aggregate_score=0.0))
    critical_findings: tuple[Finding, ...] = Field(default=())
    top_recommendations: tuple[str, ...] = Field(default=())
    readiness_label: str = Field(default="not_ready")

    @property
    def dimension_scores(self) -> dict[str, float]:
        """Map of dimension → score for quick lookup."""
        return {r.dimension: r.score for r in self.dimension_results}
