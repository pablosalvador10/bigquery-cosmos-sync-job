"""Core data models for the synthetic data generation framework."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """A scenario definition for synthetic data generation.

    Each scenario describes an edge case, boundary condition, or
    representative example that should be covered in the golden set.
    """

    scenario_id: str = Field(default_factory=lambda: f"S-{uuid4().hex[:6]}")
    description: str = Field(description="What this scenario tests")
    expected_label: str = Field(description="Expected classification/label for generated data")
    variant_count: int = Field(default=2, ge=1, description="Number of variants to generate")
    category: str = Field(default="general", description="Scenario category")
    constraints: list[str] = Field(default_factory=list, description="Generation constraints")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional scenario data")


class GeneratedRecord(BaseModel):
    """A single generated or processed data record with full provenance."""

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str = Field(description="'organic' | 'synthetic'")
    content: dict[str, Any] = Field(description="The actual generated content")
    label: str = Field(default="", description="Assigned or expected label")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Classification confidence")
    rationale: str = Field(default="", description="Why this label was assigned")
    scenario_id: str | None = Field(default=None, description="Source scenario ID (synthetic only)")
    expected_label: str | None = Field(default=None, description="Expected label (synthetic only)")
    classifier_model: str = Field(default="", description="Model used for labeling")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional provenance data")


class QualityMetrics(BaseModel, frozen=True):
    """Quality metrics for a generated dataset."""

    total_records: int = Field(default=0)
    duplicate_count: int = Field(default=0)
    structural_errors: int = Field(default=0)
    low_confidence_count: int = Field(default=0)
    label_distribution: dict[str, int] = Field(default_factory=dict)
    source_distribution: dict[str, int] = Field(default_factory=dict)

    @property
    def duplicate_rate(self) -> float:
        return self.duplicate_count / self.total_records if self.total_records > 0 else 0.0

    @property
    def low_confidence_rate(self) -> float:
        return self.low_confidence_count / self.total_records if self.total_records > 0 else 0.0


class DatasetManifest(BaseModel, frozen=True):
    """Manifest describing a generated dataset."""

    dataset_id: str = Field(default_factory=lambda: f"DS-{uuid4().hex[:8]}")
    run_id: str = Field(default="")
    record_count: int = Field(default=0)
    quality: QualityMetrics = Field(default_factory=QualityMetrics)
    output_path: str = Field(default="")
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    stages_completed: list[str] = Field(default_factory=list)
