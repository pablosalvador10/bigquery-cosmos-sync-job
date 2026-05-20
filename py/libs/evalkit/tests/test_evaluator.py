"""Tests for built-in evaluators."""

import json

from evalkit import (
    CostEfficiencyEvaluator,
    EvalContext,
    GroundednessEvaluator,
    LatencyEvaluator,
    ResponseRelevanceEvaluator,
    SafetyEvaluator,
    StructuredOutputEvaluator,
    ToolUtilizationEvaluator,
)


class TestResponseRelevanceEvaluator:
    def test_relevant_response(self, basic_context):
        ev = ResponseRelevanceEvaluator()
        result = ev.evaluate(basic_context)
        assert result.score > 0.5
        assert result.dimension == "relevance"

    def test_empty_response(self):
        ctx = EvalContext(query="test", response="")
        result = ResponseRelevanceEvaluator().evaluate(ctx)
        assert result.score == 0.0
        assert result.findings[0].severity == "critical"

    def test_short_response(self):
        ctx = EvalContext(query="hello world", response="hi")
        result = ResponseRelevanceEvaluator().evaluate(ctx)
        assert result.score < 1.0

    def test_vague_language_penalized(self):
        ctx = EvalContext(query="test", response="some various things probably maybe could work")
        result = ResponseRelevanceEvaluator().evaluate(ctx)
        assert any(f.message.startswith("Vague") for f in result.findings)


class TestGroundednessEvaluator:
    def test_grounded_response(self, basic_context):
        result = GroundednessEvaluator().evaluate(basic_context)
        assert result.score > 0.3

    def test_no_context(self):
        ctx = EvalContext(query="test", response="answer", context="")
        result = GroundednessEvaluator().evaluate(ctx)
        assert result.score == 1.0  # No context = skip (no penalty)

    def test_empty_response(self):
        ctx = EvalContext(response="", context="some context")
        result = GroundednessEvaluator().evaluate(ctx)
        assert result.score == 0.0


class TestLatencyEvaluator:
    def test_good_latency(self):
        ctx = EvalContext(latency_ms=200.0)
        result = LatencyEvaluator().evaluate(ctx)
        assert result.score == 1.0

    def test_acceptable_latency(self):
        ctx = EvalContext(latency_ms=2000.0)
        result = LatencyEvaluator().evaluate(ctx)
        assert 0.5 < result.score < 1.0

    def test_bad_latency(self):
        ctx = EvalContext(latency_ms=15000.0)
        result = LatencyEvaluator().evaluate(ctx)
        assert result.score == 0.0
        assert result.findings[0].severity == "critical"

    def test_custom_thresholds(self):
        ev = LatencyEvaluator(good_ms=100, acceptable_ms=500, max_ms=1000)
        ctx = EvalContext(latency_ms=200.0)
        result = ev.evaluate(ctx)
        assert 0.5 < result.score < 1.0


class TestToolUtilizationEvaluator:
    def test_tools_used_correctly(self, tool_context):
        result = ToolUtilizationEvaluator().evaluate(tool_context)
        assert result.score > 0.5

    def test_no_tools_expected(self):
        ctx = EvalContext(query="hello")
        result = ToolUtilizationEvaluator().evaluate(ctx)
        assert result.score == 1.0

    def test_tools_expected_but_missing(self):
        ctx = EvalContext(
            query="search",
            metadata={"tools_expected": True},
        )
        result = ToolUtilizationEvaluator().evaluate(ctx)
        assert result.score == 0.0


class TestCostEfficiencyEvaluator:
    def test_low_cost(self):
        ctx = EvalContext(cost_usd=0.001, tokens_in=50, tokens_out=20)
        result = CostEfficiencyEvaluator().evaluate(ctx)
        assert result.score > 0.9

    def test_high_cost(self):
        ctx = EvalContext(cost_usd=0.50, tokens_in=5000, tokens_out=3000)
        result = CostEfficiencyEvaluator().evaluate(ctx)
        assert result.score < 0.5


class TestSafetyEvaluator:
    def test_safe_response(self, basic_context):
        result = SafetyEvaluator().evaluate(basic_context)
        assert result.score == 1.0

    def test_ssn_detected(self):
        ctx = EvalContext(response="Your SSN is 123-45-6789")
        result = SafetyEvaluator().evaluate(ctx)
        assert result.score < 1.0
        assert result.findings[0].severity == "critical"

    def test_credential_detected(self):
        ctx = EvalContext(response="Use api_key=sk-12345abc to authenticate")
        result = SafetyEvaluator().evaluate(ctx)
        assert result.score < 1.0


class TestStructuredOutputEvaluator:
    def test_valid_json(self):
        ctx = EvalContext(response=json.dumps({"action": "search", "query": "test"}))
        result = StructuredOutputEvaluator().evaluate(ctx)
        assert result.score == 1.0

    def test_invalid_json(self):
        ctx = EvalContext(response="not json at all")
        result = StructuredOutputEvaluator().evaluate(ctx)
        assert result.score == 0.0

    def test_missing_required_fields(self):
        ctx = EvalContext(
            response=json.dumps({"action": "search"}),
            metadata={"required_fields": ["action", "query", "confidence"]},
        )
        result = StructuredOutputEvaluator().evaluate(ctx)
        assert result.score < 1.0
        assert any("Missing" in f.message for f in result.findings)

    def test_expected_values(self):
        ctx = EvalContext(
            response=json.dumps({"action": "ANSWER", "confidence": 3}),
            metadata={"expected_values": {"action": "ANSWER"}},
        )
        result = StructuredOutputEvaluator().evaluate(ctx)
        assert result.score == 1.0
