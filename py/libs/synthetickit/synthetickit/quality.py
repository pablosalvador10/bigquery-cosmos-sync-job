"""Quality gates: structural validation, duplicate detection, consistency."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .models import GeneratedRecord, QualityMetrics


def validate_record(
    record: GeneratedRecord,
    *,
    required_fields: list[str] | None = None,
) -> list[str]:
    """Validate structural requirements of a generated record.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    if not record.content:
        errors.append("Record content is empty")

    if not record.source:
        errors.append("Record source is missing")

    if record.source not in ("organic", "synthetic"):
        errors.append(f"Invalid source '{record.source}' — must be 'organic' or 'synthetic'")

    if required_fields:
        for field_name in required_fields:
            if field_name not in record.content:
                errors.append(f"Missing required field: {field_name}")

    if record.source == "synthetic" and not record.scenario_id:
        errors.append("Synthetic records must have a scenario_id")

    return errors


def detect_duplicates(
    records: list[GeneratedRecord],
    *,
    threshold: float = 0.80,
) -> set[str]:
    """Detect near-duplicate records by token overlap.

    Returns a set of record IDs that are duplicates (keeping the first
    occurrence of each cluster).
    """
    duplicate_ids: set[str] = set()

    # Group by label for efficiency — only compare within same label.
    by_label: dict[str, list[GeneratedRecord]] = {}
    for record in records:
        by_label.setdefault(record.label, []).append(record)

    for label_records in by_label.values():
        tokens_list = [_tokenize(r) for r in label_records]

        for i in range(len(label_records)):
            if label_records[i].record_id in duplicate_ids:
                continue
            for j in range(i + 1, len(label_records)):
                if label_records[j].record_id in duplicate_ids:
                    continue
                overlap = _token_overlap(tokens_list[i], tokens_list[j])
                if overlap >= threshold:
                    duplicate_ids.add(label_records[j].record_id)

    return duplicate_ids


def compute_quality_metrics(
    records: list[GeneratedRecord],
    *,
    confidence_threshold: float = 0.5,
    required_fields: list[str] | None = None,
) -> QualityMetrics:
    """Compute quality metrics for a dataset."""
    structural_errors = 0
    low_confidence = 0
    label_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for record in records:
        errors = validate_record(record, required_fields=required_fields)
        if errors:
            structural_errors += 1
        if record.confidence < confidence_threshold:
            low_confidence += 1
        label_counts[record.label] += 1
        source_counts[record.source] += 1

    duplicates = detect_duplicates(records)

    return QualityMetrics(
        total_records=len(records),
        duplicate_count=len(duplicates),
        structural_errors=structural_errors,
        low_confidence_count=low_confidence,
        label_distribution=dict(label_counts),
        source_distribution=dict(source_counts),
    )


def _tokenize(record: GeneratedRecord) -> set[str]:
    """Extract a set of tokens from record content."""
    text = " ".join(str(v) for v in record.content.values())
    return set(text.lower().split())


def _token_overlap(tokens_a: set[str], tokens_b: set[str]) -> float:
    """Compute token overlap ratio between two token sets."""
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    smaller = min(len(tokens_a), len(tokens_b))
    return intersection / smaller if smaller > 0 else 0.0
