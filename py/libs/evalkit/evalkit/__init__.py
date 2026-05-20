"""evalkit — Domain-agnostic evaluation framework for agentic AI apps.

Provides protocol-based evaluators, weighted rubric scoring, quality
gates, coaching moment detection, and config-driven batch evaluation.

Usage::

    from evalkit import EvalRubric, EvalResult, Finding, QualityReport
    from evalkit import ResponseRelevanceEvaluator, GroundednessEvaluator

    rubric = EvalRubric(evaluators=[ResponseRelevanceEvaluator(), ...])
    report = rubric.evaluate(context)
"""

from .coaching import CoachingMoment as CoachingMoment, detect_coaching_moments as detect_coaching_moments
from .evaluator import (
    AsyncEvaluator as AsyncEvaluator,
    CostEfficiencyEvaluator as CostEfficiencyEvaluator,
    Evaluator as Evaluator,
    GroundednessEvaluator as GroundednessEvaluator,
    LatencyEvaluator as LatencyEvaluator,
    ResponseRelevanceEvaluator as ResponseRelevanceEvaluator,
    SafetyEvaluator as SafetyEvaluator,
    StructuredOutputEvaluator as StructuredOutputEvaluator,
    ToolUtilizationEvaluator as ToolUtilizationEvaluator,
)
from .models import (
    EvalContext as EvalContext,
    EvalDimension as EvalDimension,
    EvalResult as EvalResult,
    Finding as Finding,
    GateResult as GateResult,
    GateThreshold as GateThreshold,
    QualityReport as QualityReport,
)
from .rubric import EvalRubric as EvalRubric
