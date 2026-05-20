---
name: evaluation-pipeline
description: 'Creates a domain evaluation pipeline using evalkit. Use when setting up evaluations, defining quality metrics, creating evaluators, or building eval rubrics for an agentic app.'
argument-hint: 'Describe what you want to evaluate (e.g., "routing accuracy for customer support agent")'
---

## Purpose
Step-by-step guide for creating a domain-specific evaluation pipeline using the evalkit library.

## When to Use
- Setting up evaluations for a new agentic app.
- Defining quality metrics and pass/fail thresholds.
- Building custom evaluators for domain-specific dimensions.
- Creating an eval configuration for batch evaluation runs.

## Flow

1. **Define your EvalContext subclass** in your app:
   ```python
   from evalkit import EvalContext

   class RouterEvalContext(EvalContext):
       conversation_turns: list[dict] = []
       expected_action: str = ""
       actual_action: str = ""
   ```

2. **Create domain evaluators** implementing the `Evaluator` protocol:
   ```python
   from evalkit import Evaluator, EvalResult, EvalContext, Finding

   class RoutingAccuracyEvaluator:
       @property
       def dimension(self) -> str:
           return "routing_accuracy"

       def evaluate(self, ctx: EvalContext) -> EvalResult:
           expected = ctx.metadata.get("expected_action", "")
           actual = ctx.metadata.get("actual_action", "")
           score = 1.0 if expected == actual else 0.0
           findings = []
           if score == 0.0:
               findings.append(Finding(
                   severity="critical",
                   message=f"Expected '{expected}', got '{actual}'",
               ))
           return EvalResult(dimension=self.dimension, score=score, findings=tuple(findings))
   ```

3. **Configure the rubric** with weights and gate thresholds:
   ```python
   from evalkit import EvalRubric, GateThreshold
   from evalkit.models import DimensionWeight

   rubric = EvalRubric(
       evaluators=[
           RoutingAccuracyEvaluator(),
           ResponseRelevanceEvaluator(),
           LatencyEvaluator(good_ms=500, acceptable_ms=2000),
       ],
       weights=[
           DimensionWeight(dimension="routing_accuracy", weight=3.0),
           DimensionWeight(dimension="relevance", weight=1.5),
           DimensionWeight(dimension="latency", weight=1.0),
       ],
       gate_threshold=GateThreshold(
           global_minimum=0.7,
           auto_fail_dimensions=("routing_accuracy",),
       ),
   )
   ```

4. **Run evaluation** and inspect the report:
   ```python
   ctx = RouterEvalContext(
       query="How much does it cost?",
       response="Let me connect you with sales.",
       metadata={"expected_action": "OFFER_HANDOFF_SALES", "actual_action": "OFFER_HANDOFF_SALES"},
       latency_ms=350,
   )
   report = rubric.evaluate(ctx)
   print(f"Score: {report.aggregate_score}, Passed: {report.gate.passed}")
   ```

5. **Add coaching moment detection** (optional):
   ```python
   from evalkit import detect_coaching_moments
   moments = detect_coaching_moments(ctx)
   for m in moments:
       print(f"[{m.moment_id}] {m.trigger_label}: {m.reframe}")
   ```

## Built-in Evaluators

| Evaluator | Dimension | What It Checks |
|-----------|-----------|----------------|
| `ResponseRelevanceEvaluator` | relevance | Word overlap, response length, vague language |
| `GroundednessEvaluator` | groundedness | N-gram overlap with provided context |
| `LatencyEvaluator` | latency | Response time against configurable thresholds |
| `ToolUtilizationEvaluator` | tool_utilization | Tool call presence and structure |
| `CostEfficiencyEvaluator` | cost_efficiency | Token usage and cost against budgets |
| `SafetyEvaluator` | safety | PII, credentials, harmful content detection |
| `StructuredOutputEvaluator` | structured_output | JSON validity, required fields, expected values |

## Checklist
- [ ] EvalContext subclass defined with domain fields
- [ ] Custom evaluators implement `dimension` property + `evaluate()` method
- [ ] Rubric configured with weights and gate threshold
- [ ] Evaluation tested against known good/bad cases
- [ ] Coaching moments reviewed for strategic anti-patterns
