"""3-stage pipeline orchestrator for synthetic data generation."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from .models import DatasetManifest, GeneratedRecord, Scenario
from .quality import compute_quality_metrics, detect_duplicates, validate_record
from .scenarios import load_scenarios


class StageConfig(BaseModel):
    """Configuration for a single pipeline stage."""

    skip: bool = Field(default=False, description="Skip this stage")
    input_path: str = Field(default="", description="Input file path")
    output_path: str = Field(default="", description="Output file path")
    scenarios_path: str | None = Field(default=None, description="Custom scenarios YAML path")
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Configuration for the full 3-stage pipeline."""

    output_dir: str = Field(default="output", description="Base output directory")
    run_id: str = Field(default="", description="Custom run ID (auto-generated if empty)")
    categories: list[str] = Field(
        default_factory=lambda: ["product", "sales", "support", "ambiguous"],
        description="Label taxonomy",
    )
    prepare: StageConfig = Field(default_factory=StageConfig)
    synthesize: StageConfig = Field(default_factory=StageConfig)
    annotate: StageConfig = Field(default_factory=StageConfig)


def _generate_run_id(config: PipelineConfig) -> str:
    """Generate a run ID from timestamp."""
    if config.run_id:
        return config.run_id
    ts = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%S")
    return f"{ts}_{uuid4().hex[:6]}"


def run_pipeline(
    config: PipelineConfig,
    *,
    generate_fn: Callable[[Scenario], list[GeneratedRecord]] | None = None,
    classify_fn: Callable[[GeneratedRecord], GeneratedRecord] | None = None,
    prepare_fn: Callable[[StageConfig], list[GeneratedRecord]] | None = None,
) -> DatasetManifest:
    """Run the 3-stage synthetic data pipeline.

    Args:
        config: Pipeline configuration.
        generate_fn: Custom function to generate records from a scenario.
            If None, default placeholder generation is used.
        classify_fn: Custom function to classify/annotate a record.
            If None, records keep their existing labels.
        prepare_fn: Custom function for stage 1 (prepare).
            If None, loads from ``config.prepare.input_path``.

    Returns:
        A ``DatasetManifest`` describing the generated dataset.
    """
    run_id = _generate_run_id(config)
    output_dir = Path(config.output_dir) / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    stages_completed: list[str] = []
    all_records: list[GeneratedRecord] = []

    # ── Stage 1: Prepare ──────────────────────────────────────── #
    if not config.prepare.skip:
        if prepare_fn:
            prepared = prepare_fn(config.prepare)
        elif config.prepare.input_path:
            prepared = _load_jsonl(config.prepare.input_path)
        else:
            prepared = []

        _export_jsonl(prepared, output_dir / "prepared.jsonl")
        all_records.extend(prepared)
        stages_completed.append("prepare")

    # ── Stage 2: Synthesize ───────────────────────────────────── #
    if not config.synthesize.skip:
        scenarios = load_scenarios(config.synthesize.scenarios_path)
        synthetic = _run_synthesis(scenarios, generate_fn)

        # Quality gate: remove duplicates.
        dup_ids = detect_duplicates(synthetic)
        synthetic = [r for r in synthetic if r.record_id not in dup_ids]

        _export_jsonl(synthetic, output_dir / "synthetic.jsonl")
        all_records.extend(synthetic)
        stages_completed.append("synthesize")

    # ── Stage 3: Annotate ─────────────────────────────────────── #
    if not config.annotate.skip:
        annotated = _run_annotation(all_records, classify_fn)
        output_path = output_dir / "golden_set.jsonl"
        _export_jsonl(annotated, output_path)
        stages_completed.append("annotate")
    else:
        output_path = output_dir / "records.jsonl"
        _export_jsonl(all_records, output_path)

    # ── Quality metrics ────────────────────────────────────────── #
    quality = compute_quality_metrics(all_records)

    return DatasetManifest(
        run_id=run_id,
        record_count=len(all_records),
        quality=quality,
        output_path=str(output_path),
        stages_completed=stages_completed,
    )


def _run_synthesis(
    scenarios: list[Scenario],
    generate_fn: Callable[[Scenario], list[GeneratedRecord]] | None,
) -> list[GeneratedRecord]:
    """Generate synthetic records from scenarios."""
    records: list[GeneratedRecord] = []

    for scenario in scenarios:
        if generate_fn:
            generated = generate_fn(scenario)
        else:
            generated = _default_generate(scenario)

        for record in generated:
            errors = validate_record(record)
            if not errors:
                records.append(record)

    return records


def _run_annotation(
    records: list[GeneratedRecord],
    classify_fn: Callable[[GeneratedRecord], GeneratedRecord] | None,
) -> list[GeneratedRecord]:
    """Annotate records with labels."""
    if classify_fn is None:
        return records
    return [classify_fn(r) for r in records]


def _default_generate(scenario: Scenario) -> list[GeneratedRecord]:
    """Default placeholder generator — creates records from scenario descriptions."""
    records: list[GeneratedRecord] = []
    for i in range(scenario.variant_count):
        records.append(GeneratedRecord(
            source="synthetic",
            content={"text": f"{scenario.description} (variant {i + 1})", "scenario": scenario.description},
            label=scenario.expected_label,
            confidence=1.0,
            rationale=f"Generated from scenario {scenario.scenario_id}",
            scenario_id=scenario.scenario_id,
            expected_label=scenario.expected_label,
        ))
    return records


def _load_jsonl(path: str) -> list[GeneratedRecord]:
    """Load records from a JSONL file."""
    records: list[GeneratedRecord] = []
    file_path = Path(path)
    if not file_path.exists():
        return records
    for line in file_path.read_text(encoding="utf-8").strip().split("\n"):
        line = line.strip()
        if line:
            records.append(GeneratedRecord.model_validate_json(line))
    return records


def _export_jsonl(records: list[GeneratedRecord], path: Path) -> None:
    """Export records to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(record.model_dump_json() + "\n")
