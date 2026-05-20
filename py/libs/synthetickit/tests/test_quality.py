"""Tests for quality gates."""

from synthetickit import GeneratedRecord, detect_duplicates, validate_record
from synthetickit.quality import compute_quality_metrics


class TestValidateRecord:
    def test_valid_organic_record(self):
        record = GeneratedRecord(source="organic", content={"text": "hello"}, label="product")
        errors = validate_record(record)
        assert errors == []

    def test_valid_synthetic_record(self):
        record = GeneratedRecord(source="synthetic", content={"text": "hi"}, scenario_id="S-1")
        errors = validate_record(record)
        assert errors == []

    def test_empty_content(self):
        record = GeneratedRecord(source="organic", content={})
        errors = validate_record(record)
        assert any("empty" in e for e in errors)

    def test_invalid_source(self):
        record = GeneratedRecord(source="unknown", content={"text": "x"})
        errors = validate_record(record)
        assert any("Invalid source" in e for e in errors)

    def test_synthetic_missing_scenario(self):
        record = GeneratedRecord(source="synthetic", content={"text": "x"})
        errors = validate_record(record)
        assert any("scenario_id" in e for e in errors)

    def test_required_fields(self):
        record = GeneratedRecord(source="organic", content={"text": "x"})
        errors = validate_record(record, required_fields=["text", "category"])
        assert any("category" in e for e in errors)


class TestDetectDuplicates:
    def test_no_duplicates(self):
        records = [
            GeneratedRecord(record_id="1", source="organic", content={"text": "hello world"}, label="a"),
            GeneratedRecord(record_id="2", source="organic", content={"text": "completely different"}, label="a"),
        ]
        dups = detect_duplicates(records)
        assert len(dups) == 0

    def test_exact_duplicate(self):
        records = [
            GeneratedRecord(record_id="1", source="organic", content={"text": "hello world foo"}, label="a"),
            GeneratedRecord(record_id="2", source="organic", content={"text": "hello world foo"}, label="a"),
        ]
        dups = detect_duplicates(records)
        assert "2" in dups

    def test_different_labels_not_compared(self):
        records = [
            GeneratedRecord(record_id="1", source="organic", content={"text": "hello world"}, label="a"),
            GeneratedRecord(record_id="2", source="organic", content={"text": "hello world"}, label="b"),
        ]
        dups = detect_duplicates(records)
        assert len(dups) == 0


class TestQualityMetrics:
    def test_basic_metrics(self, sample_records):
        metrics = compute_quality_metrics(sample_records)
        assert metrics.total_records == 3
        assert "sales" in metrics.label_distribution
        assert "support" in metrics.label_distribution
        assert "organic" in metrics.source_distribution
        assert "synthetic" in metrics.source_distribution

    def test_duplicate_rate(self):
        records = [
            GeneratedRecord(record_id="1", source="organic", content={"text": "same text here"}, label="a"),
            GeneratedRecord(record_id="2", source="organic", content={"text": "same text here"}, label="a"),
        ]
        metrics = compute_quality_metrics(records)
        assert metrics.duplicate_count == 1
        assert metrics.duplicate_rate == 0.5
