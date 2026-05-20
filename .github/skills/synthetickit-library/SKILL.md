---
name: synthetickit-library
description: 'Reference for using and extending synthetickit — 3-stage synthetic data generation with scenarios, quality gates, and provenance tracking. Use when generating evaluation datasets, defining scenarios, writing custom generators/classifiers, or extending the pipeline.'
argument-hint: 'Describe what you need (e.g., "custom LLM-based generator", "add quality gate for field coverage")'
---

## Purpose

Synthetickit is a **domain-agnostic synthetic data generation pipeline** with 3 stages: prepare → synthesize → annotate. It produces golden evaluation datasets with full provenance tracking, quality gates, and JSONL export.

## Public API Summary

| Export | Type | Purpose |
|--------|------|---------|
| `Scenario` | Pydantic model | Edge case / test scenario definition |
| `GeneratedRecord` | Pydantic model | Single data record with full provenance |
| `QualityMetrics` | Pydantic model (frozen) | Dataset quality statistics |
| `DatasetManifest` | Pydantic model (frozen) | Run metadata + quality summary |
| `PipelineConfig` | Pydantic model | Pipeline stage configuration |
| `run_pipeline()` | Function | Execute the 3-stage pipeline |
| `load_scenarios()` | Function | Load scenarios from YAML or defaults |
| `validate_record()` | Function | Validate a single record |
| `detect_duplicates()` | Function | Find near-duplicate records |

**Location:** `py/libs/synthetickit/synthetickit/`

## Core Data Flow

```
Scenarios → generate_fn → GeneratedRecord[] → quality gates → JSONL export
                                                ├── dedup
                                                ├── validate
                                                └── compute_quality_metrics
```

## Scenario — Test Case Definition

```python
from synthetickit import Scenario

scenario = Scenario(
    scenario_id="S-pricing-01",       # Auto-generated if omitted
    description="User asks about enterprise pricing with budget constraints",
    expected_label="sales",
    variant_count=3,                   # How many variants to generate
    category="boundary",              # For grouping
    constraints=["mention budget"],    # Optional generation guidance
    metadata={"priority": "high"},
)
```

### Loading scenarios from YAML:
```yaml
# scenarios.yaml
scenarios:
  - description: "Customer asks about enterprise pricing"
    expected_label: "sales"
    variant_count: 3
    category: "boundary"
  - description: "User reports a production outage"
    expected_label: "escalation"
    variant_count: 2
    category: "edge_case"
```

```python
from synthetickit import load_scenarios

scenarios = load_scenarios("scenarios.yaml")  # From file
scenarios = load_scenarios()                   # 5 built-in defaults
```

### Built-in default scenarios:
| ID | Description | Label | Variants |
|----|-------------|-------|----------|
| S-default-01 | Straightforward product question | product | 2 |
| S-default-02 | Ambiguous intent between categories | ambiguous | 2 |
| S-default-03 | Frustration + escalation needed | escalation | 2 |
| S-default-04 | Very short query | clarification | 2 |
| S-default-05 | Multi-turn follow-up | multi_turn | 2 |

## GeneratedRecord — Data with Provenance

```python
from synthetickit import GeneratedRecord

record = GeneratedRecord(
    record_id="auto-uuid",           # Auto-generated
    source="synthetic",              # "organic" or "synthetic"
    content={"text": "How much?", "turns": [...]},  # The actual data
    label="sales",
    confidence=0.95,                 # 0.0–1.0
    rationale="Generated from scenario S-pricing-01",
    scenario_id="S-pricing-01",      # Required for synthetic
    expected_label="sales",
    classifier_model="gpt-4",
    created_at="2026-01-01T...",     # Auto-generated ISO
    metadata={"variant": 1},
)
```

## PipelineConfig — Pipeline Configuration

```python
from synthetickit import PipelineConfig

config = PipelineConfig(
    output_dir="data/golden",
    run_id="my-run-001",              # Auto-generated if empty
    categories=["product", "sales", "support", "escalation"],
    prepare={"skip": True},           # Skip organic data loading
    synthesize={"scenarios_path": "scenarios.yaml"},
    annotate={"skip": False},
)
```

### Stage configuration:
Each stage accepts a `StageConfig` (or dict):
```python
class StageConfig(BaseModel):
    skip: bool = False           # Skip this stage entirely
    input_path: str = ""         # Input file (for prepare stage)
    output_path: str = ""        # Custom output path
    scenarios_path: str | None   # Custom scenarios YAML (for synthesize)
    metadata: dict = {}          # Extra config
```

## run_pipeline — Pipeline Execution

```python
from synthetickit import run_pipeline

manifest = run_pipeline(
    config,
    generate_fn=my_generator,     # Custom record generator
    classify_fn=my_classifier,    # Custom annotator
    prepare_fn=my_loader,         # Custom data loader
)
```

### Hook functions:

| Hook | Signature | Default behavior |
|------|-----------|-----------------|
| `generate_fn` | `(Scenario) → list[GeneratedRecord]` | Creates placeholder records from scenario description |
| `classify_fn` | `(GeneratedRecord) → GeneratedRecord` | Returns record unchanged |
| `prepare_fn` | `(StageConfig) → list[GeneratedRecord]` | Loads from `input_path` JSONL |

### Custom LLM-based generator:
```python
from synthetickit import Scenario, GeneratedRecord

def llm_generator(scenario: Scenario) -> list[GeneratedRecord]:
    records = []
    for i in range(scenario.variant_count):
        # Call your LLM to generate realistic data
        response = call_llm(f"Generate a {scenario.expected_label} query: {scenario.description}")
        records.append(GeneratedRecord(
            source="synthetic",
            content={"text": response, "scenario": scenario.description},
            label=scenario.expected_label,
            confidence=1.0,
            scenario_id=scenario.scenario_id,
            expected_label=scenario.expected_label,
            classifier_model="gpt-4.1-mini",
        ))
    return records
```

### Custom classifier:
```python
def llm_classifier(record: GeneratedRecord) -> GeneratedRecord:
    label = call_llm(f"Classify: {record.content['text']}")
    return record.model_copy(update={
        "label": label,
        "classifier_model": "gpt-4.1-mini",
        "confidence": 0.9,
    })
```

## Quality Gates

```python
from synthetickit import validate_record, detect_duplicates
from synthetickit.quality import compute_quality_metrics

# Validate single record
errors = validate_record(record, required_fields=["text"])
# Returns: [] (valid) or ["empty content", "missing field: text", ...]

# Detect near-duplicates
dup_ids = detect_duplicates(records, threshold=0.80)
# Returns set of record_ids to remove

# Compute dataset metrics
metrics = compute_quality_metrics(records, confidence_threshold=0.5)
print(metrics.total_records)          # 100
print(metrics.duplicate_count)        # 3
print(metrics.duplicate_rate)         # 0.03
print(metrics.low_confidence_count)   # 5
print(metrics.label_distribution)     # {"sales": 30, "support": 40, ...}
print(metrics.source_distribution)    # {"organic": 20, "synthetic": 80}
```

### Validation rules:
- Content must not be empty
- Source must be "organic" or "synthetic"
- Synthetic records must have `scenario_id`
- Custom `required_fields` checked against `content` dict

### Dedup algorithm:
- Token overlap within same label group
- Default threshold: 80% overlap → marked as duplicate
- Higher record_id is marked (keeps earlier record)

## Pipeline Output

```
output_dir/
  {run_id}/
    prepared.jsonl        # Stage 1 output (if not skipped)
    synthetic.jsonl       # Stage 2 output (after dedup)
    golden_set.jsonl      # Stage 3 output (annotated)
    records.jsonl         # All records (if annotate skipped)
```

### DatasetManifest:
```python
manifest.run_id              # "2026-01-01T12-00-00_abc123"
manifest.record_count        # 50
manifest.quality             # QualityMetrics
manifest.output_path         # "data/golden/run-id/golden_set.jsonl"
manifest.stages_completed    # ["prepare", "synthesize", "annotate"]
manifest.created_at          # ISO timestamp
```

## Extension Points

### Add a quality gate stage:
```python
def run_pipeline_with_extra_gate(config, **kwargs):
    manifest = run_pipeline(config, **kwargs)

    # Post-pipeline quality gate
    records = load_jsonl(manifest.output_path)
    metrics = compute_quality_metrics(records)

    if metrics.duplicate_rate > 0.1:
        raise ValueError(f"Too many duplicates: {metrics.duplicate_rate:.1%}")
    if metrics.low_confidence_rate > 0.2:
        raise ValueError(f"Too many low-confidence: {metrics.low_confidence_rate:.1%}")

    return manifest
```

### Add new fields to GeneratedRecord:
```python
class DomainRecord(GeneratedRecord):
    """Extended record with domain-specific fields."""
    conversation_turns: list[dict] = []
    expected_routing: str = ""
```

## File Map

| File | Contains |
|------|----------|
| `models.py` | `Scenario`, `GeneratedRecord`, `QualityMetrics`, `DatasetManifest` |
| `pipeline.py` | `PipelineConfig`, `StageConfig`, `run_pipeline()` |
| `quality.py` | `validate_record()`, `detect_duplicates()`, `compute_quality_metrics()` |
| `scenarios.py` | `load_scenarios()`, default scenario definitions |

## Checklist
- [ ] Scenarios cover happy paths, edge cases, and boundary conditions
- [ ] Generator function returns well-formed `GeneratedRecord` objects
- [ ] Records have `scenario_id` and `expected_label` for synthetic source
- [ ] Quality metrics reviewed after generation
- [ ] Output JSONL checked for completeness
- [ ] Tests use `tmp_path` for output directory
