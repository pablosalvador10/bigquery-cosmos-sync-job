"""Coaching moment detection — strategic anti-pattern analysis."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .models import EvalContext


class CoachingMoment(BaseModel, frozen=True):
    """A strategic anti-pattern detected during evaluation."""

    moment_id: str = Field(description="Unique identifier (e.g. CM-01)")
    trigger_label: str = Field(description="Short trigger name")
    trigger_description: str = Field(description="What was detected")
    reframe: str = Field(description="Suggested reframing of the approach")
    category: str = Field(description="Category: safety | quality | cost | scope | design")


def detect_coaching_moments(ctx: EvalContext) -> list[CoachingMoment]:
    """Detect strategic anti-patterns in the evaluation context.

    These are separate from scoring — coaching moments flag design-level
    issues without penalizing the numeric score.
    """
    moments: list[CoachingMoment] = []

    # CM-01: Response much longer than needed.
    if ctx.response and len(ctx.response.split()) > 500:
        moments.append(CoachingMoment(
            moment_id="CM-01",
            trigger_label="verbose_response",
            trigger_description="Response exceeds 500 words — may be over-explaining",
            reframe="Consider more concise responses focused on the user's specific question",
            category="quality",
        ))

    # CM-02: No tools used when context suggests tool usage would help.
    tool_keywords = {"search", "lookup", "find", "calculate", "check", "verify"}
    if ctx.query and any(kw in ctx.query.lower() for kw in tool_keywords) and not ctx.tool_calls:
        moments.append(CoachingMoment(
            moment_id="CM-02",
            trigger_label="missing_tool_usage",
            trigger_description="Query suggests tool usage but no tools were called",
            reframe="Consider whether a tool call would provide more accurate results",
            category="design",
        ))

    # CM-03: High cost without proportional quality.
    if ctx.cost_usd > 0.05 and len(ctx.response.split()) < 50:
        moments.append(CoachingMoment(
            moment_id="CM-03",
            trigger_label="cost_quality_mismatch",
            trigger_description="High cost ($%.4f) with short response" % ctx.cost_usd,
            reframe="Consider using a smaller model or reducing token usage for simple responses",
            category="cost",
        ))

    # CM-04: Empty context when response makes specific claims.
    if not ctx.context and ctx.response:
        claim_indicators = {"according to", "the data shows", "based on", "the report"}
        if any(phrase in ctx.response.lower() for phrase in claim_indicators):
            moments.append(CoachingMoment(
                moment_id="CM-04",
                trigger_label="ungrounded_claims",
                trigger_description="Response makes specific claims without grounding context",
                reframe="Ensure claims are backed by retrieved context or acknowledge uncertainty",
                category="quality",
            ))

    # CM-05: Excessive tool calls.
    if len(ctx.tool_calls) > 5:
        moments.append(CoachingMoment(
            moment_id="CM-05",
            trigger_label="tool_overuse",
            trigger_description=f"{len(ctx.tool_calls)} tool calls in a single turn",
            reframe="Consider batching tool calls or using a more targeted query strategy",
            category="design",
        ))

    return moments
