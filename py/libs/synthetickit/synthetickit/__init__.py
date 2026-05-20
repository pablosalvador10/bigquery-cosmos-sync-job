"""synthetickit — Domain-agnostic synthetic data generation for agentic AI apps.

Provides a 3-stage pipeline (prepare → synthesize → annotate) for
creating golden evaluation datasets with full provenance tracking.

Usage::

    from synthetickit import PipelineConfig, Scenario, run_pipeline
    from synthetickit import GeneratedRecord, DatasetManifest
"""

from .models import (
    DatasetManifest as DatasetManifest,
    GeneratedRecord as GeneratedRecord,
    QualityMetrics as QualityMetrics,
    Scenario as Scenario,
)
from .pipeline import PipelineConfig as PipelineConfig, run_pipeline as run_pipeline
from .quality import detect_duplicates as detect_duplicates, validate_record as validate_record
from .scenarios import load_scenarios as load_scenarios
