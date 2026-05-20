"""Tests for the pipeline orchestrator."""

from synthetickit import PipelineConfig, GeneratedRecord, Scenario, run_pipeline


class TestPipeline:
    def test_default_pipeline(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
        )
        manifest = run_pipeline(config)
        assert manifest.record_count > 0
        assert "synthesize" in manifest.stages_completed

    def test_skip_all_stages(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
            synthesize={"skip": True},
            annotate={"skip": True},
        )
        manifest = run_pipeline(config)
        assert manifest.record_count == 0
        assert manifest.stages_completed == []

    def test_custom_generate_fn(self, tmp_path):
        def my_generator(scenario: Scenario) -> list[GeneratedRecord]:
            return [
                GeneratedRecord(
                    source="synthetic",
                    content={"query": f"test for {scenario.expected_label}"},
                    label=scenario.expected_label,
                    confidence=0.99,
                    scenario_id=scenario.scenario_id,
                )
            ]

        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
        )
        manifest = run_pipeline(config, generate_fn=my_generator)
        assert manifest.record_count > 0

    def test_custom_classify_fn(self, tmp_path):
        def my_classifier(record: GeneratedRecord) -> GeneratedRecord:
            return record.model_copy(update={"label": "classified", "classifier_model": "test-model"})

        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
        )
        manifest = run_pipeline(config, classify_fn=my_classifier)
        assert "annotate" in manifest.stages_completed

    def test_custom_run_id(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path),
            run_id="my-test-run",
            prepare={"skip": True},
        )
        manifest = run_pipeline(config)
        assert manifest.run_id == "my-test-run"

    def test_output_files_created(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
        )
        manifest = run_pipeline(config)
        assert (tmp_path / manifest.run_id / "synthetic.jsonl").exists()

    def test_quality_metrics_populated(self, tmp_path):
        config = PipelineConfig(
            output_dir=str(tmp_path),
            prepare={"skip": True},
        )
        manifest = run_pipeline(config)
        assert manifest.quality.total_records > 0
        assert len(manifest.quality.label_distribution) > 0
