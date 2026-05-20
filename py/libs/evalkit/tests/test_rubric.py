"""Tests for the EvalRubric engine."""

from evalkit import (
    EvalContext,
    EvalRubric,
    GateThreshold,
    GroundednessEvaluator,
    LatencyEvaluator,
    ResponseRelevanceEvaluator,
    SafetyEvaluator,
)
from evalkit.models import DimensionWeight


class TestEvalRubric:
    def test_basic_evaluation(self, basic_context):
        rubric = EvalRubric(
            evaluators=[
                ResponseRelevanceEvaluator(),
                GroundednessEvaluator(),
                LatencyEvaluator(),
                SafetyEvaluator(),
            ]
        )
        report = rubric.evaluate(basic_context)
        assert len(report.dimension_results) == 4
        assert 0.0 <= report.aggregate_score <= 1.0
        assert report.readiness_label in ("strong", "good_enough", "draft", "not_ready")

    def test_gate_passes(self, basic_context):
        rubric = EvalRubric(
            evaluators=[SafetyEvaluator(), LatencyEvaluator()],
            gate_threshold=GateThreshold(global_minimum=0.3),
        )
        report = rubric.evaluate(basic_context)
        assert report.gate.passed

    def test_gate_fails(self):
        ctx = EvalContext(response="", latency_ms=50000)
        rubric = EvalRubric(
            evaluators=[ResponseRelevanceEvaluator(), LatencyEvaluator()],
            gate_threshold=GateThreshold(global_minimum=0.8),
        )
        report = rubric.evaluate(ctx)
        assert not report.gate.passed

    def test_auto_fail_dimension(self, basic_context):
        rubric = EvalRubric(
            evaluators=[ResponseRelevanceEvaluator()],
            gate_threshold=GateThreshold(
                global_minimum=0.0,
                auto_fail_dimensions=("relevance",),
            ),
        )
        ctx = EvalContext(query="test", response="")
        report = rubric.evaluate(ctx)
        assert not report.gate.passed

    def test_custom_weights(self, basic_context):
        rubric = EvalRubric(
            evaluators=[ResponseRelevanceEvaluator(), SafetyEvaluator()],
            weights=[
                DimensionWeight(dimension="relevance", weight=10.0),
                DimensionWeight(dimension="safety", weight=0.1),
            ],
        )
        report = rubric.evaluate(basic_context)
        # Relevance should dominate the score.
        assert report.aggregate_score > 0.0

    def test_empty_evaluators(self, basic_context):
        rubric = EvalRubric(evaluators=[])
        report = rubric.evaluate(basic_context)
        assert report.aggregate_score == 0.0

    def test_readiness_labels(self):
        rubric = EvalRubric()
        assert rubric._readiness_label(0.90) == "strong"
        assert rubric._readiness_label(0.75) == "good_enough"
        assert rubric._readiness_label(0.55) == "draft"
        assert rubric._readiness_label(0.30) == "not_ready"

    def test_critical_findings_extracted(self):
        ctx = EvalContext(response="")
        rubric = EvalRubric(evaluators=[ResponseRelevanceEvaluator()])
        report = rubric.evaluate(ctx)
        assert len(report.critical_findings) > 0

    def test_dimension_scores_property(self, basic_context):
        rubric = EvalRubric(evaluators=[SafetyEvaluator()])
        report = rubric.evaluate(basic_context)
        scores = report.dimension_scores
        assert "safety" in scores
        assert scores["safety"] == 1.0
