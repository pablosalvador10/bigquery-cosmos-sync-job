"""Evaluator protocol and built-in evaluator implementations."""

from __future__ import annotations

import json
import re
from typing import Any, Protocol, runtime_checkable

from .models import EvalContext, EvalResult, Finding


@runtime_checkable
class Evaluator(Protocol):
    """Protocol for synchronous evaluators.

    Implement this to create custom evaluation dimensions::

        class MyEvaluator:
            @property
            def dimension(self) -> str:
                return "my_dimension"

            def evaluate(self, ctx: EvalContext) -> EvalResult:
                ...
    """

    @property
    def dimension(self) -> str: ...

    def evaluate(self, ctx: EvalContext) -> EvalResult: ...


@runtime_checkable
class AsyncEvaluator(Protocol):
    """Protocol for asynchronous evaluators (e.g., LLM-based)."""

    @property
    def dimension(self) -> str: ...

    async def evaluate_async(self, ctx: EvalContext) -> EvalResult: ...


# ── Vague-word detection ─────────────────────────────────────────── #

_VAGUE_WORDS = frozenset({
    "some", "many", "various", "several", "appropriate",
    "adequate", "reasonable", "suitable", "properly", "correctly",
    "efficiently", "effectively", "etc", "things", "stuff",
    "maybe", "probably", "might", "could", "perhaps",
})

_UNSAFE_PATTERNS = [
    re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),  # SSN-like
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email
    re.compile(r"\b(?:password|secret|api.?key|token)\s*[:=]\s*\S+", re.IGNORECASE),  # credentials
]


def _count_vague_words(text: str) -> list[str]:
    """Find vague/weasel words in text."""
    words = text.lower().split()
    return [w for w in words if w in _VAGUE_WORDS]


# ── Built-in Evaluators ─────────────────────────────────────────── #


class ResponseRelevanceEvaluator:
    """Evaluates whether the agent's response addresses the user's query.

    Scoring:
    - Checks word overlap between query and response
    - Penalizes empty or very short responses
    - Penalizes vague language
    """

    @property
    def dimension(self) -> str:
        return "relevance"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []

        if not ctx.response.strip():
            return EvalResult(
                dimension=self.dimension,
                score=0.0,
                findings=(Finding(severity="critical", message="Response is empty"),),
                summary="Empty response — no relevance possible",
            )

        # Word overlap scoring.
        query_words = set(ctx.query.lower().split())
        response_words = set(ctx.response.lower().split())
        if query_words:
            overlap = len(query_words & response_words) / len(query_words)
        else:
            overlap = 0.5  # No query means we can't measure relevance

        score = min(overlap * 1.5, 1.0)  # Scale up: 67% overlap = 1.0

        # Penalize very short responses.
        word_count = len(ctx.response.split())
        if word_count < 5:
            score *= 0.5
            findings.append(Finding(
                severity="warning",
                message=f"Response is very short ({word_count} words)",
                suggestion="Provide a more detailed response",
            ))

        # Penalize vague language.
        vague = _count_vague_words(ctx.response)
        if vague:
            penalty = min(len(vague) * 0.05, 0.3)
            score = max(score - penalty, 0.0)
            findings.append(Finding(
                severity="info",
                message=f"Vague language detected: {', '.join(vague[:5])}",
            ))

        return EvalResult(
            dimension=self.dimension,
            score=round(score, 3),
            findings=tuple(findings),
            summary=f"Relevance score: {score:.2f} (word overlap + quality checks)",
        )


class GroundednessEvaluator:
    """Evaluates whether the response is grounded in the provided context.

    Scoring:
    - Checks what fraction of response claims appear in context
    - Penalizes responses that introduce information not in context
    """

    @property
    def dimension(self) -> str:
        return "groundedness"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []

        if not ctx.context.strip():
            return EvalResult(
                dimension=self.dimension,
                score=1.0,
                findings=(Finding(severity="info", message="No grounding context provided — skipping"),),
                summary="No context to ground against",
            )

        if not ctx.response.strip():
            return EvalResult(
                dimension=self.dimension,
                score=0.0,
                findings=(Finding(severity="critical", message="Empty response"),),
                summary="Empty response",
            )

        # N-gram overlap scoring.
        context_lower = ctx.context.lower()
        response_words = ctx.response.lower().split()

        # Bigram overlap.
        if len(response_words) >= 2:
            bigrams = [f"{response_words[i]} {response_words[i+1]}" for i in range(len(response_words) - 1)]
            grounded = sum(1 for bg in bigrams if bg in context_lower)
            score = grounded / len(bigrams) if bigrams else 0.0
        else:
            score = 1.0 if response_words[0] in context_lower else 0.0

        score = min(score * 2.0, 1.0)  # Scale: 50% bigram match = 1.0

        if score < 0.3:
            findings.append(Finding(
                severity="warning",
                message="Response appears poorly grounded in the provided context",
                suggestion="Ensure the response draws from the supplied context",
            ))

        return EvalResult(
            dimension=self.dimension,
            score=round(score, 3),
            findings=tuple(findings),
            summary=f"Groundedness: {score:.2f}",
        )


class LatencyEvaluator:
    """Evaluates response latency against configurable thresholds.

    Args:
        good_ms: Latency below this is scored 1.0 (default: 1000ms).
        acceptable_ms: Latency below this is scored 0.5–1.0 (default: 3000ms).
        max_ms: Latency above this is scored 0.0 (default: 10000ms).
    """

    def __init__(
        self,
        good_ms: float = 1000.0,
        acceptable_ms: float = 3000.0,
        max_ms: float = 10000.0,
    ) -> None:
        self._good = good_ms
        self._acceptable = acceptable_ms
        self._max = max_ms

    @property
    def dimension(self) -> str:
        return "latency"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []
        latency = ctx.latency_ms

        if latency <= self._good:
            score = 1.0
        elif latency <= self._acceptable:
            score = 1.0 - 0.5 * ((latency - self._good) / (self._acceptable - self._good))
        elif latency <= self._max:
            score = 0.5 * (1.0 - (latency - self._acceptable) / (self._max - self._acceptable))
        else:
            score = 0.0
            findings.append(Finding(
                severity="critical",
                message=f"Latency {latency:.0f}ms exceeds maximum {self._max:.0f}ms",
            ))

        if latency > self._acceptable:
            findings.append(Finding(
                severity="warning",
                message=f"Latency {latency:.0f}ms exceeds acceptable threshold {self._acceptable:.0f}ms",
            ))

        return EvalResult(
            dimension=self.dimension,
            score=round(max(score, 0.0), 3),
            findings=tuple(findings),
            summary=f"Latency: {latency:.0f}ms (score: {score:.2f})",
        )


class ToolUtilizationEvaluator:
    """Evaluates whether the agent used tools appropriately.

    Scoring:
    - Checks if tools were called when expected
    - Validates tool call structure
    """

    @property
    def dimension(self) -> str:
        return "tool_utilization"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []

        if not ctx.tool_calls:
            if ctx.metadata.get("tools_expected", False):
                return EvalResult(
                    dimension=self.dimension,
                    score=0.0,
                    findings=(Finding(severity="critical", message="Expected tool calls but none were made"),),
                    summary="No tool calls when tools were expected",
                )
            return EvalResult(
                dimension=self.dimension,
                score=1.0,
                findings=(Finding(severity="info", message="No tool calls — none expected"),),
                summary="No tools expected or used",
            )

        # Validate tool call structure.
        valid_calls = 0
        for call in ctx.tool_calls:
            if "name" not in call:
                findings.append(Finding(severity="warning", message="Tool call missing 'name' field"))
                continue
            valid_calls += 1

        score = valid_calls / len(ctx.tool_calls) if ctx.tool_calls else 0.0

        # Check for expected tools.
        expected_tools = ctx.metadata.get("expected_tools", [])
        if expected_tools:
            called_names = {c.get("name", "") for c in ctx.tool_calls}
            missing = set(expected_tools) - called_names
            if missing:
                score *= 0.5
                findings.append(Finding(
                    severity="warning",
                    message=f"Expected tools not called: {', '.join(missing)}",
                ))

        return EvalResult(
            dimension=self.dimension,
            score=round(score, 3),
            findings=tuple(findings),
            summary=f"Tool utilization: {valid_calls}/{len(ctx.tool_calls)} valid calls",
        )


class CostEfficiencyEvaluator:
    """Evaluates token usage and cost against budgets.

    Args:
        max_cost_usd: Maximum acceptable cost per evaluation (default: $0.10).
        max_tokens: Maximum acceptable total tokens (default: 4000).
    """

    def __init__(
        self,
        max_cost_usd: float = 0.10,
        max_tokens: int = 4000,
    ) -> None:
        self._max_cost = max_cost_usd
        self._max_tokens = max_tokens

    @property
    def dimension(self) -> str:
        return "cost_efficiency"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []
        total_tokens = ctx.tokens_in + ctx.tokens_out

        # Cost scoring.
        if ctx.cost_usd <= 0:
            cost_score = 1.0
        elif ctx.cost_usd <= self._max_cost:
            cost_score = 1.0 - (ctx.cost_usd / self._max_cost) * 0.5
        else:
            cost_score = max(0.0, 0.5 - (ctx.cost_usd - self._max_cost) / self._max_cost)
            findings.append(Finding(
                severity="warning",
                message=f"Cost ${ctx.cost_usd:.4f} exceeds budget ${self._max_cost:.4f}",
            ))

        # Token scoring.
        if total_tokens <= 0:
            token_score = 1.0
        elif total_tokens <= self._max_tokens:
            token_score = 1.0 - (total_tokens / self._max_tokens) * 0.3
        else:
            token_score = max(0.0, 0.7 - (total_tokens - self._max_tokens) / self._max_tokens)
            findings.append(Finding(
                severity="info",
                message=f"Token count {total_tokens} exceeds target {self._max_tokens}",
            ))

        score = (cost_score * 0.6 + token_score * 0.4)

        return EvalResult(
            dimension=self.dimension,
            score=round(score, 3),
            findings=tuple(findings),
            summary=f"Cost: ${ctx.cost_usd:.4f}, Tokens: {total_tokens}",
        )


class SafetyEvaluator:
    """Evaluates response for safety issues (PII, harmful content patterns)."""

    @property
    def dimension(self) -> str:
        return "safety"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []
        score = 1.0

        for pattern in _UNSAFE_PATTERNS:
            matches = pattern.findall(ctx.response)
            if matches:
                score = max(score - 0.3, 0.0)
                findings.append(Finding(
                    severity="critical",
                    message=f"Potential sensitive data detected ({len(matches)} matches)",
                    suggestion="Remove PII, credentials, or sensitive data from responses",
                ))

        return EvalResult(
            dimension=self.dimension,
            score=round(score, 3),
            findings=tuple(findings),
            summary=f"Safety score: {score:.2f}",
        )


class StructuredOutputEvaluator:
    """Evaluates whether the response is valid structured output (JSON).

    Checks:
    - Valid JSON parsing
    - Required fields presence (via ``metadata["required_fields"]``)
    - Expected values (via ``metadata["expected_values"]``)
    """

    @property
    def dimension(self) -> str:
        return "structured_output"

    def evaluate(self, ctx: EvalContext) -> EvalResult:
        findings: list[Finding] = []

        # Try parsing as JSON.
        try:
            parsed = json.loads(ctx.response)
        except (json.JSONDecodeError, TypeError):
            return EvalResult(
                dimension=self.dimension,
                score=0.0,
                findings=(Finding(severity="critical", message="Response is not valid JSON"),),
                summary="Invalid JSON",
            )

        score = 1.0

        # Check required fields.
        required = ctx.metadata.get("required_fields", [])
        if required and isinstance(parsed, dict):
            missing = [f for f in required if f not in parsed]
            if missing:
                score -= len(missing) * 0.2
                findings.append(Finding(
                    severity="warning",
                    message=f"Missing required fields: {', '.join(missing)}",
                ))

        # Check expected values.
        expected = ctx.metadata.get("expected_values", {})
        if expected and isinstance(parsed, dict):
            for key, exp_val in expected.items():
                actual = parsed.get(key)
                if actual != exp_val:
                    score -= 0.15
                    findings.append(Finding(
                        severity="info",
                        message=f"Field '{key}': expected {exp_val!r}, got {actual!r}",
                    ))

        return EvalResult(
            dimension=self.dimension,
            score=round(max(score, 0.0), 3),
            findings=tuple(findings),
            summary=f"Structured output score: {score:.2f}",
        )
