"""Shared fixtures for synthetickit tests."""

import pytest
from synthetickit import Scenario, GeneratedRecord


@pytest.fixture
def sample_scenarios() -> list[Scenario]:
    return [
        Scenario(
            scenario_id="S-test-01",
            description="User asks about pricing",
            expected_label="sales",
            variant_count=2,
        ),
        Scenario(
            scenario_id="S-test-02",
            description="User reports a bug",
            expected_label="support",
            variant_count=3,
        ),
    ]


@pytest.fixture
def sample_records() -> list[GeneratedRecord]:
    return [
        GeneratedRecord(
            record_id="r1",
            source="organic",
            content={"text": "How much does it cost?"},
            label="sales",
            confidence=0.9,
        ),
        GeneratedRecord(
            record_id="r2",
            source="synthetic",
            content={"text": "I found a bug in the system"},
            label="support",
            confidence=0.95,
            scenario_id="S-test-02",
            expected_label="support",
        ),
        GeneratedRecord(
            record_id="r3",
            source="synthetic",
            content={"text": "I found a bug in the application"},
            label="support",
            confidence=0.85,
            scenario_id="S-test-02",
            expected_label="support",
        ),
    ]
