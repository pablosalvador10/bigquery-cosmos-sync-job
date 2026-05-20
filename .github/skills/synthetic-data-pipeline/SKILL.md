---
name: synthetic-data-pipeline
description: 'Creates a synthetic data generation pipeline using synthetickit. Use when generating test data, creating golden evaluation sets, building demo datasets, or defining edge-case scenarios.'
argument-hint: 'Describe what data you need (e.g., "customer support conversations for routing evaluation")'
---

## Purpose
Step-by-step guide for setting up synthetic data generation using the synthetickit library.

## When to Use
- Creating golden evaluation datasets for evalkit.
- Generating test fixtures for integration tests.
- Building demo data for UI/backend demonstrations.
- Defining edge-case scenarios for agent testing.

## Flow

1. **Define scenarios** in YAML or code:
   ```yaml
   # scenarios.yaml
   scenarios:
     - description: "Customer asks about enterprise pricing with budget constraints"
       expected_label: "sales"
       variant_count: 3
       category: "boundary"
     - description: "User reports a production outage affecting multiple teams"
       expected_label: "escalation"
       variant_count: 2
       category: "edge_case"
   ```

2. **Configure the pipeline**:
   ```python
   from synthetickit import PipelineConfig

   config = PipelineConfig(
       output_dir="data/golden",
       categories=["product", "sales", "support", "escalation", "ambiguous"],
       prepare={"skip": True},  # Skip if no organic data
       synthesize={"scenarios_path": "scenarios.yaml"},
   )
   ```

3. **Implement a custom generator** (for LLM-based generation):
   ```python
   from synthetickit import Scenario, GeneratedRecord

   async def generate_conversations(scenario: Scenario) -> list[GeneratedRecord]:
       records = []
       for i in range(scenario.variant_count):
           # Call your LLM here to generate realistic data
           content = {"turns": [...], "metadata": {...}}
           records.append(GeneratedRecord(
               source="synthetic",
               content=content,
               label=scenario.expected_label,
               confidence=1.0,
               scenario_id=scenario.scenario_id,
               expected_label=scenario.expected_label,
           ))
       return records
   ```

4. **Run the pipeline**:
   ```python
   from synthetickit import run_pipeline

   manifest = run_pipeline(
       config,
       generate_fn=generate_conversations,
       classify_fn=my_classifier,  # Optional: re-label with a stronger model
   )
   print(f"Generated {manifest.record_count} records")
   print(f"Output: {manifest.output_path}")
   print(f"Quality: {manifest.quality.duplicate_rate:.1%} dupes")
   ```

5. **Validate quality**:
   ```python
   from synthetickit import validate_record, detect_duplicates

   for record in records:
       errors = validate_record(record, required_fields=["turns"])
       if errors:
           print(f"Invalid record: {errors}")

   duplicates = detect_duplicates(records, threshold=0.80)
   print(f"Found {len(duplicates)} near-duplicates")
   ```

## Pipeline Stages

| Stage | Purpose | Output |
|-------|---------|--------|
| **Prepare** | Load and filter organic data, stratified sampling | `prepared.jsonl` |
| **Synthesize** | Generate edge cases from scenarios, quality gate (dedup) | `synthetic.jsonl` |
| **Annotate** | Label all records with a strong classifier model | `golden_set.jsonl` |

Each stage is independently skippable and produces durable JSONL artifacts.

## Integration with evalkit

The golden set produced by synthetickit is the input for evalkit evaluations:
```python
# synthetickit generates golden_set.jsonl
# evalkit evaluates your agent against it
```

## Checklist
- [ ] Scenarios defined covering happy paths, edge cases, and boundary conditions
- [ ] Pipeline config created with correct categories and output directory
- [ ] Generator function implemented (default or custom LLM-based)
- [ ] Quality metrics reviewed (duplicate rate, structural errors, label distribution)
- [ ] Golden set validated for completeness and provenance
