"""Weighted rubric engine — runs evaluators, aggregates scores, applies gate."""

from __future__ import annotations

from .evaluator import Evaluator
from .models import (
    DimensionWeight,
    EvalContext,
    EvalResult,
    Finding,
    GateResult,
    GateThreshold,
    QualityReport,
)

# Default dimension weights — higher = more important.
DEFAULT_WEIGHTS: list[DimensionWeight] = [
    DimensionWeight(dimension="relevance", weight=2.0),
    DimensionWeight(dimension="groundedness", weight=2.0),
    DimensionWeight(dimension="safety", weight=2.0),
    DimensionWeight(dimension="structured_output", weight=1.5),
    DimensionWeight(dimension="tool_utilization", weight=1.5),
    DimensionWeight(dimension="latency", weight=1.0),
    DimensionWeight(dimension="cost_efficiency", weight=1.0),
    DimensionWeight(dimension="accuracy", weight=1.5),
]


class EvalRubric:
    """Runs evaluators and produces a weighted quality report.

    Args:
        evaluators: List of evaluator instances (must satisfy the Evaluator protocol).
        weights: Optional custom dimension weights. Defaults to ``DEFAULT_WEIGHTS``.
        gate_threshold: Quality gate configuration. Defaults to 0.6 global minimum.
    """

    def __init__(
        self,
        evaluators: list[Evaluator] | None = None,
        weights: list[DimensionWeight] | None = None,
        gate_threshold: GateThreshold | None = None,
    ) -> None:
        self._evaluators = evaluators or []
        self._weights = {w.dimension: w.weight for w in (weights or DEFAULT_WEIGHTS)}
        self._gate = gate_threshold or GateThreshold()

    def evaluate(self, ctx: EvalContext) -> QualityReport:
        """Run all evaluators and produce a quality report."""
        results: list[EvalResult] = []
        for evaluator in self._evaluators:
            result = evaluator.evaluate(ctx)
            results.append(result)

        aggregate = self._weighted_score(results)
        gate = self._apply_gate(results, aggregate)
        critical = self._extract_critical(results)
        recommendations = self._top_recommendations(results)
        readiness = self._readiness_label(aggregate)

        return QualityReport(
            dimension_results=tuple(results),
            aggregate_score=round(aggregate, 3),
            gate=gate,
            critical_findings=tuple(critical),
            top_recommendations=tuple(recommendations),
            readiness_label=readiness,
        )

    def _weighted_score(self, results: list[EvalResult]) -> float:
        """Compute weighted average score across dimensions."""
        total_weight = 0.0
        weighted_sum = 0.0

        for result in results:
            weight = self._weights.get(result.dimension, 1.0)
            weighted_sum += result.score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _apply_gate(
        self,
        results: list[EvalResult],
        aggregate: float,
    ) -> GateResult:
        """Check quality gate conditions."""
        failing: list[str] = []

        # Global minimum.
        if aggregate < self._gate.global_minimum:
            failing.append(f"aggregate ({aggregate:.2f} < {self._gate.global_minimum})")

        # Per-dimension minimums.
        for result in results:
            min_score = self._gate.dimension_minimums.get(result.dimension)
            if min_score is not None and result.score < min_score:
                failing.append(f"{result.dimension} ({result.score:.2f} < {min_score})")

        # Auto-fail dimensions — score must be above a meaningful threshold.
        auto_fail_min = max(self._gate.global_minimum, 0.1)
        for result in results:
            if result.dimension in self._gate.auto_fail_dimensions and result.score < auto_fail_min:
                if result.dimension not in str(failing):
                    failing.append(f"{result.dimension} (auto-fail: {result.score:.2f})")

        passed = len(failing) == 0
        message = "All gates passed" if passed else f"Failed: {'; '.join(failing)}"

        return GateResult(
            passed=passed,
            aggregate_score=round(aggregate, 3),
            failing_dimensions=tuple(failing),
            gate_message=message,
        )

    @staticmethod
    def _extract_critical(results: list[EvalResult]) -> list[Finding]:
        """Extract critical findings from all results."""
        return [
            f for r in results for f in r.findings if f.severity == "critical"
        ]

    @staticmethod
    def _top_recommendations(results: list[EvalResult], max_count: int = 5) -> list[str]:
        """Build top recommendations from findings."""
        recs: list[str] = []
        for result in results:
            for finding in result.findings:
                if finding.suggestion and len(recs) < max_count:
                    recs.append(f"[{result.dimension}] {finding.suggestion}")
        return recs

    @staticmethod
    def _readiness_label(score: float) -> str:
        """Map aggregate score to a readiness label."""
        if score >= 0.85:
            return "strong"
        if score >= 0.70:
            return "good_enough"
        if score >= 0.50:
            return "draft"
        return "not_ready"
