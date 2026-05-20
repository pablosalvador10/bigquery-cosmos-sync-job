"""Scenario definition and loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import Scenario


def load_scenarios(path: str | Path | None = None) -> list[Scenario]:
    """Load scenarios from a YAML file or return defaults.

    YAML format::

        scenarios:
          - description: "Customer asks about pricing"
            expected_label: "sales"
            variant_count: 3
            category: "boundary"
          - description: "User has a technical question"
            expected_label: "product"
            variant_count: 2
    """
    if path is None:
        return _default_scenarios()

    file_path = Path(path)
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    raw_scenarios = data.get("scenarios", [])
    return [Scenario.model_validate(s) for s in raw_scenarios]


def _default_scenarios() -> list[Scenario]:
    """Built-in example scenarios for template apps."""
    return [
        Scenario(
            scenario_id="S-default-01",
            description="User asks a straightforward product question",
            expected_label="product",
            variant_count=2,
            category="happy_path",
        ),
        Scenario(
            scenario_id="S-default-02",
            description="User's intent is genuinely ambiguous between two categories",
            expected_label="ambiguous",
            variant_count=2,
            category="boundary",
        ),
        Scenario(
            scenario_id="S-default-03",
            description="User expresses frustration and needs escalation",
            expected_label="escalation",
            variant_count=2,
            category="edge_case",
        ),
        Scenario(
            scenario_id="S-default-04",
            description="User provides a very short, one-word query",
            expected_label="ambiguous",
            variant_count=2,
            category="edge_case",
        ),
        Scenario(
            scenario_id="S-default-05",
            description="User asks a multi-turn follow-up question",
            expected_label="product",
            variant_count=2,
            category="multi_turn",
        ),
    ]
