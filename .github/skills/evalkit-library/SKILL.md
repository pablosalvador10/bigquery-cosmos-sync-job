---
name: evalkit-library
description: 'Reference for using and extending evalkit — evaluation framework with protocol-based evaluators, weighted rubric scoring, quality gates, and coaching moments. Use when creating custom evaluators, configuring rubrics, understanding scoring, or extending the evaluation framework.'
argument-hint: 'Describe what you need (e.g., "create custom evaluator for citation accuracy", "tune quality gate thresholds")'
---

## Purpose

Evalkit is a **domain-agnostic evaluation framework** for agentic AI apps. It provides protocol-based evaluators, weighted scoring via rubrics, pass/fail quality gates, and coaching moment detection. You use built-in evaluators or write your own.

## Public API Summary

| Export | Type | Purpose |
|--------|------|---------|
| `EvalContext` | Pydantic model | Input data for evaluation |
| `EvalResult` | Pydantic model (frozen) | Score + findings for one dimension |
| `Finding` | Pydantic model (frozen) | Single issue with severity/suggestion |
| `QualityReport` | Pydantic model (frozen) | Full report with scores, gate, recommendations |
| `GateThreshold` | Pydantic model (frozen) | Quality gate configuration |
| `GateResult` | Pydantic model (frozen) | Pass/fail result + failing dimensions |
| `DimensionWeight` | Pydantic model (frozen) | Weight for a scoring dimension |
| `EvalDimension` | StrEnum | Standard dimension names |
| `Evaluator` | Protocol | Sync evaluator interface |
| `AsyncEvaluator` | Protocol | Async evaluator interface |
| `EvalRubric` | Class | Scoring engine: runs evaluators + aggregates |
| `CoachingMoment` | Pydantic model | Strategic anti-pattern detected |
| `detect_coaching_moments()` | Function | Find coaching moments in context |
| 7 built-in evaluators | Classes | Ready-to-use evaluators |

**Location:** `py/libs/evalkit/evalkit/`

## Core Data Flow

```
EvalContext → Evaluators → EvalResult[] → EvalRubric → QualityReport
                                                         ├── aggregate_score
                                                         ├── gate (passed/failed)
                                                         ├── critical_findings
                                                         ├── top_recommendations
                                                         └── readiness_label
```

## EvalContext — Evaluation Input

```python
from evalkit import EvalContext

ctx = EvalContext(
    query="What is the capital of France?",        # User question
    response="The capital of France is Paris.",      # Agent response
    context="France is a country. Paris is its capital.",  # Grounding data
    tool_calls=[{"name": "search", "arguments": {"q": "France"}}],
    expected_output="Paris",                         # Ground truth
    latency_ms=350.0,
    tokens_in=100,
    tokens_out=50,
    cost_usd=0.002,
    metadata={"tools_expected": True, "expected_tools": ["search"]},
)
```

### Extension — Domain-specific context:
```python
class RouterEvalContext(EvalContext):
    """Custom context for routing evaluation."""
    conversation_turns: list[dict] = []
    expected_action: str = ""
    actual_action: str = ""
```

## Built-in Evaluators

| Evaluator | Dimension | What It Scores | Key Config |
|-----------|-----------|----------------|------------|
| `ResponseRelevanceEvaluator` | `relevance` | Word overlap, response length, vague words | — |
| `GroundednessEvaluator` | `groundedness` | Bigram overlap with context | — |
| `LatencyEvaluator` | `latency` | Response time vs thresholds | `good_ms`, `acceptable_ms`, `max_ms` |
| `ToolUtilizationEvaluator` | `tool_utilization` | Tool usage correctness | Via `metadata.tools_expected` |
| `CostEfficiencyEvaluator` | `cost_efficiency` | Cost + tokens vs budgets | `max_cost_usd`, `max_tokens` |
| `SafetyEvaluator` | `safety` | PII, credentials, patterns | — |
| `StructuredOutputEvaluator` | `structured_output` | JSON validity + fields | Via `metadata.required_fields` |

### Using built-in evaluators:
```python
from evalkit import (
    ResponseRelevanceEvaluator,
    LatencyEvaluator,
    SafetyEvaluator,
)

# Default config
relevance = ResponseRelevanceEvaluator()

# Custom thresholds
latency = LatencyEvaluator(good_ms=200, acceptable_ms=1000, max_ms=5000)
```

## Creating Custom Evaluators

Implement the `Evaluator` protocol (two requirements: `dimension` property + `evaluate` method):

```python
from evalkit import Evaluator, EvalContext, EvalResult, Finding

class RoutingAccuracyEvaluator:
    """Evaluates whether the agent routed to the correct department."""

    @property
    def dimension(self) -> str:
        return "routing_accuracy"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        expected = ctx.metadata.get("expected_action", "")
        actual = ctx.metadata.get("actual_action", "")

        if not expected:
            return EvalResult(dimension=self.dimension, score=1.0,
                              summary="No expected action — skipping")

        score = 1.0 if expected == actual else 0.0
        findings = []
        if score == 0.0:
            findings.append(Finding(
                severity="critical",
                message=f"Routed to '{actual}', expected '{expected}'",
                suggestion="Review routing logic for this query type",
            ))

        return EvalResult(
            dimension=self.dimension,
            score=score,
            findings=tuple(findings),
            summary=f"Routing: {'correct' if score == 1.0 else 'incorrect'}",
        )
```

### Async evaluators (for LLM-based evaluation):
```python
from evalkit import AsyncEvaluator

class LLMJudgeEvaluator:
    @property
    def dimension(self) -> str:
        return "llm_judge"

    async def evaluate_async(self, ctx: EvalContext) -> EvalResult:
        # Call an LLM to judge quality
        score = await self._call_judge(ctx.query, ctx.response)
        return EvalResult(dimension=self.dimension, score=score)
```

## EvalRubric — Scoring Engine

```python
from evalkit import EvalRubric, GateThreshold
from evalkit.models import DimensionWeight

rubric = EvalRubric(
    evaluators=[
        ResponseRelevanceEvaluator(),
        GroundednessEvaluator(),
        SafetyEvaluator(),
        RoutingAccuracyEvaluator(),
    ],
    weights=[
        DimensionWeight(dimension="relevance", weight=2.0),
        DimensionWeight(dimension="groundedness", weight=2.0),
        DimensionWeight(dimension="safety", weight=3.0),
        DimensionWeight(dimension="routing_accuracy", weight=3.0),
    ],
    gate_threshold=GateThreshold(
        global_minimum=0.7,                          # Overall score must be ≥ 0.7
        auto_fail_dimensions=("safety",),            # Safety < threshold → auto-fail
        dimension_minimums={"routing_accuracy": 0.5}, # Per-dimension floors
    ),
)
```

### Running evaluation:
```python
report = rubric.evaluate(ctx)

print(report.aggregate_score)     # 0.0–1.0 weighted average
print(report.gate.passed)         # True/False
print(report.readiness_label)     # "strong" | "good_enough" | "draft" | "not_ready"
print(report.dimension_scores)    # {"relevance": 0.85, "safety": 1.0, ...}
print(report.critical_findings)   # Tuple of critical Finding objects
print(report.top_recommendations) # Tuple of suggestion strings
```

### Scoring mechanics:
- **Weighted average**: `sum(score × weight) / sum(weights)`
- **Quality gate**: checks global minimum + per-dimension minimums + auto-fail dimensions
- **Auto-fail threshold**: `max(global_minimum, 0.1)`
- **Readiness labels**: ≥0.85 "strong", ≥0.7 "good_enough", ≥0.5 "draft", <0.5 "not_ready"

## Coaching Moments

Separate from scoring — strategic anti-pattern detection:

```python
from evalkit import detect_coaching_moments

moments = detect_coaching_moments(ctx)
for m in moments:
    print(f"[{m.moment_id}] {m.trigger_label}: {m.reframe}")
```

| ID | Trigger | Condition |
|----|---------|-----------|
| CM-01 | `verbose_response` | Response > 500 words |
| CM-02 | `missing_tool_usage` | Query has tool keywords but no tool calls |
| CM-03 | `cost_quality_mismatch` | Cost > $0.05 with response < 50 words |
| CM-04 | `ungrounded_claims` | Claims without grounding context |
| CM-05 | `tool_overuse` | > 5 tool calls in a single turn |

## EvalResult & Finding Models

```python
# EvalResult fields
result.dimension        # str — dimension name
result.score            # float — 0.0 to 1.0
result.max_score        # float — default 1.0
result.normalized_score # property — score / max_score
result.findings         # tuple[Finding, ...] — issues found
result.summary          # str — human-readable summary

# Finding fields
finding.severity    # "critical" | "warning" | "info" | "strength"
finding.message     # What was found
finding.location    # Where (optional)
finding.suggestion  # How to fix (optional)
```

## Integration with synthetickit

Generate test data → evaluate agent responses:
```python
from synthetickit import run_pipeline, PipelineConfig
from evalkit import EvalRubric, EvalContext

# Generate golden set
manifest = run_pipeline(PipelineConfig(output_dir="data/golden", prepare={"skip": True}))

# Evaluate each record
for record in load_records(manifest.output_path):
    response = my_agent.respond(record.content["text"])
    ctx = EvalContext(query=record.content["text"], response=response)
    report = rubric.evaluate(ctx)
```

## File Map

| File | Contains |
|------|----------|
| `models.py` | `EvalContext`, `EvalResult`, `Finding`, `QualityReport`, `GateThreshold`, `GateResult`, `DimensionWeight`, `EvalDimension` |
| `evaluator.py` | `Evaluator` protocol, `AsyncEvaluator` protocol, 7 built-in evaluators |
| `rubric.py` | `EvalRubric` scoring engine, `DEFAULT_WEIGHTS` |
| `coaching.py` | `CoachingMoment`, `detect_coaching_moments()` |

## Checklist
- [ ] Custom evaluators implement `dimension` property + `evaluate()` method
- [ ] EvalResult scores are 0.0–1.0
- [ ] Findings have appropriate severity levels
- [ ] Rubric weights sum to meaningful proportions
- [ ] Gate thresholds set for your quality requirements
- [ ] Critical dimensions listed in `auto_fail_dimensions`
- [ ] Tests cover known-good and known-bad cases
