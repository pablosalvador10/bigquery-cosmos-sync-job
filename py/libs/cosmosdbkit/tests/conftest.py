"""Pytest configuration for cosmosdbkit tests."""

import pytest


@pytest.fixture
def hackathon_item() -> dict[str, object]:
    return {"id": "fde-fy26", "hackathonId": "fde-fy26", "name": "FDE FY26"}
