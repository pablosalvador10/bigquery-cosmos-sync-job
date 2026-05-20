"""Tests for coaching moment detection."""

from evalkit import EvalContext, detect_coaching_moments


class TestCoachingMoments:
    def test_verbose_response(self):
        ctx = EvalContext(response=" ".join(["word"] * 600))
        moments = detect_coaching_moments(ctx)
        assert any(m.moment_id == "CM-01" for m in moments)

    def test_missing_tool_usage(self):
        ctx = EvalContext(query="Search for the latest data", response="Here it is.")
        moments = detect_coaching_moments(ctx)
        assert any(m.moment_id == "CM-02" for m in moments)

    def test_cost_quality_mismatch(self):
        ctx = EvalContext(response="Short.", cost_usd=0.10)
        moments = detect_coaching_moments(ctx)
        assert any(m.moment_id == "CM-03" for m in moments)

    def test_ungrounded_claims(self):
        ctx = EvalContext(response="According to the data, sales increased by 50%.")
        moments = detect_coaching_moments(ctx)
        assert any(m.moment_id == "CM-04" for m in moments)

    def test_tool_overuse(self):
        ctx = EvalContext(
            tool_calls=[{"name": f"tool_{i}"} for i in range(7)],
            response="Done.",
        )
        moments = detect_coaching_moments(ctx)
        assert any(m.moment_id == "CM-05" for m in moments)

    def test_no_moments_for_clean_context(self, basic_context):
        moments = detect_coaching_moments(basic_context)
        assert len(moments) == 0
