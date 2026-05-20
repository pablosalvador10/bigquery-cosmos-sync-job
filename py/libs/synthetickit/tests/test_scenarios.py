"""Tests for scenario loading."""

from synthetickit import Scenario, load_scenarios


class TestLoadScenarios:
    def test_default_scenarios(self):
        scenarios = load_scenarios()
        assert len(scenarios) == 5
        assert all(isinstance(s, Scenario) for s in scenarios)

    def test_all_defaults_have_labels(self):
        scenarios = load_scenarios()
        for s in scenarios:
            assert s.expected_label
            assert s.variant_count >= 1

    def test_load_from_yaml(self, tmp_path):
        yaml_content = """
scenarios:
  - description: "Custom scenario"
    expected_label: "custom"
    variant_count: 3
    category: "test"
"""
        yaml_file = tmp_path / "scenarios.yaml"
        yaml_file.write_text(yaml_content)
        scenarios = load_scenarios(yaml_file)
        assert len(scenarios) == 1
        assert scenarios[0].expected_label == "custom"
        assert scenarios[0].variant_count == 3
