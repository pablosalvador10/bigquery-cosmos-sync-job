"""End-to-end pipeline: synthetic data generation → simulated agent → evaluation.

This sample demonstrates how synthetickit, evalkit, and testkit work together
to create a complete quality assurance pipeline for an agentic application.

Run with:
    cd py && uv run python apps/sample-eval-e2e/main.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from evalkit import (
    CostEfficiencyEvaluator,
    EvalContext,
    EvalRubric,
    GateThreshold,
    GroundednessEvaluator,
    LatencyEvaluator,
    ResponseRelevanceEvaluator,
    SafetyEvaluator,
    ToolUtilizationEvaluator,
    detect_coaching_moments,
)
from evalkit.models import DimensionWeight, QualityReport
from synthetickit import (
    DatasetManifest,
    GeneratedRecord,
    PipelineConfig,
    Scenario,
    run_pipeline,
)
from testkit import FakeLLMClient


# ── Simulated Agent ──────────────────────────────────────────────────── #


def _simulate_agent_response(record: GeneratedRecord) -> tuple[str, str]:
    """Simulate an agent answering a query from a synthetic record.

    Returns (response, grounding_context) to feed into evaluation.
    """
    query = record.content.get("text", record.content.get("query", ""))
    label = record.label or record.expected_label or "general"

    # Simulate grounding context the agent would have retrieved
    context = (
        f"This category covers {label} related inquiries. "
        f"Standard procedures apply for {label} requests. "
        f"Our team handles {label} related questions promptly."
    )

    # Response deliberately reuses phrasing from context (simulating a grounded agent)
    # and echoes key query terms for relevance scoring
    query_snippet = " ".join(query.split()[:6])
    response = (
        f"Regarding your question about {query_snippet}, "
        f"this category covers {label} related inquiries. "
        f"Standard procedures apply for {label} requests. "
        f"Our team handles {label} related questions promptly and will follow up."
    )

    return response, context


# ── Pipeline Stages ──────────────────────────────────────────────────── #


def stage_1_generate_data(output_dir: Path) -> DatasetManifest:
    """Stage 1: Generate synthetic evaluation dataset using synthetickit."""
    print("\n" + "=" * 60)
    print("STAGE 1: Synthetic Data Generation")
    print("=" * 60)

    # Define custom scenarios that exercise edge cases
    scenarios = [
        Scenario(
            scenario_id="S-product-01",
            description="User asks about product pricing and availability",
            expected_label="product",
            variant_count=3,
            category="product",
        ),
        Scenario(
            scenario_id="S-support-01",
            description="User reports a critical bug blocking their work",
            expected_label="support",
            variant_count=2,
            category="support",
        ),
        Scenario(
            scenario_id="S-sales-01",
            description="User wants to upgrade their subscription plan",
            expected_label="sales",
            variant_count=2,
            category="sales",
        ),
        Scenario(
            scenario_id="S-ambiguous-01",
            description="User sends a very short unclear message",
            expected_label="ambiguous",
            variant_count=2,
            category="ambiguous",
        ),
    ]

    def custom_generate(scenario: Scenario) -> list[GeneratedRecord]:
        """Custom generator that creates realistic synthetic queries."""
        records: list[GeneratedRecord] = []
        for i in range(scenario.variant_count):
            records.append(
                GeneratedRecord(
                    source="synthetic",
                    content={
                        "text": f"{scenario.description} (variant {i + 1})",
                        "scenario": scenario.description,
                        "category": scenario.category,
                    },
                    label=scenario.expected_label,
                    confidence=0.95,
                    rationale=f"Generated from scenario {scenario.scenario_id}",
                    scenario_id=scenario.scenario_id,
                    expected_label=scenario.expected_label,
                    classifier_model="custom-generator-v1",
                )
            )
        return records

    def custom_classify(record: GeneratedRecord) -> GeneratedRecord:
        """Custom annotation that simulates a classifier."""
        return record.model_copy(
            update={"classifier_model": "simulated-classifier-v1"}
        )

    config = PipelineConfig(
        output_dir=str(output_dir),
        run_id="sample-e2e-run",
        categories=["product", "sales", "support", "ambiguous"],
        prepare={"skip": True},
        synthesize={"scenarios_path": None},
    )

    manifest = run_pipeline(
        config, generate_fn=custom_generate, classify_fn=custom_classify
    )

    print(f"  Records generated: {manifest.record_count}")
    print(f"  Stages completed:  {manifest.stages_completed}")
    print(f"  Output path:       {manifest.output_path}")
    print(f"  Labels:            {dict(manifest.quality.label_distribution)}")
    print(f"  Duplicates:        {manifest.quality.duplicate_count}")

    return manifest


def stage_2_evaluate(manifest: DatasetManifest) -> list[QualityReport]:
    """Stage 2: Run each synthetic record through the agent and evaluate."""
    print("\n" + "=" * 60)
    print("STAGE 2: Agent Evaluation Pipeline")
    print("=" * 60)

    # Load generated records from output
    records = _load_records(manifest.output_path)

    # Configure rubric with all evaluators
    rubric = EvalRubric(
        evaluators=[
            ResponseRelevanceEvaluator(),
            GroundednessEvaluator(),
            LatencyEvaluator(),
            SafetyEvaluator(),
            CostEfficiencyEvaluator(),
            ToolUtilizationEvaluator(),
        ],
        weights=[
            DimensionWeight(dimension="relevance", weight=2.0),
            DimensionWeight(dimension="groundedness", weight=2.0),
            DimensionWeight(dimension="safety", weight=3.0),
            DimensionWeight(dimension="latency", weight=1.0),
            DimensionWeight(dimension="cost_efficiency", weight=1.0),
            DimensionWeight(dimension="tool_utilization", weight=1.0),
        ],
        gate_threshold=GateThreshold(
            global_minimum=0.6,
            auto_fail_dimensions=("safety",),
            dimension_minimums={"relevance": 0.4, "groundedness": 0.3},
        ),
    )

    reports: list[QualityReport] = []

    for i, record in enumerate(records):
        query = record.content.get("text", "")
        response, context = _simulate_agent_response(record)

        # Build evaluation context
        ctx = EvalContext(
            query=query,
            response=response,
            context=context,
            latency_ms=150.0 + (i * 50),  # Simulate varying latency
            tokens_in=len(query.split()) * 3,
            tokens_out=len(response.split()) * 3,
            cost_usd=0.001 + (i * 0.0005),
        )

        report = rubric.evaluate(ctx)
        reports.append(report)

        # Check for coaching moments
        coaching = detect_coaching_moments(ctx)

        status = "PASS" if report.gate.passed else "FAIL"
        print(
            f"  [{status}] Record {i + 1}/{len(records)}: "
            f"score={report.aggregate_score:.2f} "
            f"label={record.label} "
            f"readiness={report.readiness_label}"
        )

        if coaching:
            for moment in coaching:
                print(f"         Coaching {moment.moment_id}: {moment.trigger_label}")

    return reports


def stage_3_report(reports: list[QualityReport]) -> bool:
    """Stage 3: Aggregate results and produce final report."""
    print("\n" + "=" * 60)
    print("STAGE 3: Quality Report Summary")
    print("=" * 60)

    if not reports:
        print("  No reports to summarize.")
        return False

    total = len(reports)
    passed = sum(1 for r in reports if r.gate.passed)
    failed = total - passed
    avg_score = sum(r.aggregate_score for r in reports) / total

    # Collect dimension-level stats
    dimension_scores: dict[str, list[float]] = {}
    for report in reports:
        for result in report.dimension_results:
            dimension_scores.setdefault(result.dimension, []).append(
                result.normalized_score
            )

    # Collect all critical findings
    all_critical = []
    for report in reports:
        all_critical.extend(report.critical_findings)

    # Collect all recommendations
    all_recommendations: set[str] = set()
    for report in reports:
        all_recommendations.update(report.top_recommendations)

    print(f"\n  Total evaluations:   {total}")
    print(f"  Passed:              {passed} ({passed / total * 100:.0f}%)")
    print(f"  Failed:              {failed} ({failed / total * 100:.0f}%)")
    print(f"  Average score:       {avg_score:.3f}")
    print(f"\n  Readiness distribution:")

    readiness_counts: dict[str, int] = {}
    for r in reports:
        readiness_counts[r.readiness_label] = (
            readiness_counts.get(r.readiness_label, 0) + 1
        )
    for label, count in sorted(readiness_counts.items()):
        print(f"    {label}: {count}")

    print(f"\n  Dimension averages:")
    for dim, scores in sorted(dimension_scores.items()):
        avg = sum(scores) / len(scores)
        print(f"    {dim}: {avg:.3f}")

    if all_critical:
        print(f"\n  Critical findings ({len(all_critical)}):")
        for finding in all_critical[:5]:
            print(f"    - [{finding.severity}] {finding.message}")

    if all_recommendations:
        print(f"\n  Top recommendations:")
        for rec in sorted(all_recommendations)[:5]:
            print(f"    - {rec}")

    overall_pass = passed == total and avg_score >= 0.6
    print(f"\n  {'OVERALL: PASS' if overall_pass else 'OVERALL: NEEDS IMPROVEMENT'}")
    print("=" * 60)

    return overall_pass


def _load_records(output_path: str) -> list[GeneratedRecord]:
    """Load generated records from a JSONL file."""
    records: list[GeneratedRecord] = []
    path = Path(output_path)
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if line:
            records.append(GeneratedRecord.model_validate_json(line))
    return records


# ── Main ─────────────────────────────────────────────────────────────── #


def main() -> int:
    """Run the full end-to-end pipeline."""
    print("Sample End-to-End Pipeline: Synthetic Generation → Evaluation")
    print("Using: synthetickit + evalkit + testkit")

    output_dir = Path("output/sample-e2e")

    # Stage 1: Generate synthetic data
    manifest = stage_1_generate_data(output_dir)

    # Stage 2: Evaluate agent responses
    reports = stage_2_evaluate(manifest)

    # Stage 3: Aggregate and report
    overall_pass = stage_3_report(reports)

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
