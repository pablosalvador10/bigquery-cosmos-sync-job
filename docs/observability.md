# observability

Three signals from the app, plus first-class infra telemetry:

| signal | where | what it tells you |
| --- | --- | --- |
| structured logs | Log Analytics (`ContainerAppConsoleLogs_CL`) | per-row failures, per-pipeline summaries, request ids |
| traces | Application Insights | spans per pipeline + per batch upsert |
| checkpoints | Cosmos `sync_metadata` | source of truth for run status, counts, watermark |
| Cosmos diagnostics | Log Analytics (`AzureDiagnostics` / `CDB*` tables) | data-plane requests, query runtime stats, partition-key RU consumption |

Cosmos diagnostic settings ship out of the box: `DataPlaneRequests`,
`QueryRuntimeStatistics`, `PartitionKeyStatistics`,
`PartitionKeyRUConsumption`, `ControlPlaneRequests` plus the `Requests`
metric all stream to the workspace. KQL examples below.

## `sync_metadata` shape

PK `/pipeline`. One doc per (run, pipeline).

```jsonc
{
  "id": "<run_id>::<pipeline>",
  "run_id": "2026-05-19T08:00:00Z--abcd",
  "pipeline": "learners",
  "status": "success",          // success | partial | failure
  "rows_read": 4231,
  "rows_upserted": 4229,
  "rows_failed": 2,
  "duration_ms": 18234,
  "watermark": "2026-05-19T07:59:42+00:00",
  "started_at": "...",
  "finished_at": "...",
  "error": null
}
```

## KQL — last 24 h

```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s startswith "bq-cosmos-sync"
| where Log_s has "pipeline_summary"
| extend p = parse_json(Log_s)
| project TimeGenerated,
          run_id   = tostring(p.run_id),
          pipeline = tostring(p.pipeline),
          status   = tostring(p.status),
          read     = tolong(p.rows_read),
          upserted = tolong(p.rows_upserted),
          failed   = tolong(p.rows_failed),
          ms       = tolong(p.duration_ms)
| order by TimeGenerated desc
```

## KQL — failure rate by pipeline, last 7 d

```kusto
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(7d)
| where Log_s has "pipeline_summary"
| extend p = parse_json(Log_s)
| extend pipeline = tostring(p.pipeline),
         failed   = tolong(p.rows_failed),
         read     = tolong(p.rows_read)
| summarize fail_rate = 100.0 * sum(failed) / sum(read) by pipeline
```

## Alerts (provisioned)

| alert | trigger | severity |
| --- | --- | --- |
| job execution failed | `ContainerAppJobExecutionStatus_CL` status = Failed | 2 |
| pipeline marked failure | `pipeline_summary` log with `status="failure"` | 2 |
| high row failure rate | `rows_failed / rows_read > 0.05` per pipeline | 3 |
| job hasn't run | no `pipeline_summary` in 26 h | 2 |

Thresholds in [`infra/main.tf`](../infra/main.tf).

## Tracing

`azure-monitor-opentelemetry` is initialised in `cli.py`. The runner adds
two manual spans:

- `pipeline.run` — attrs `pipeline.name`, `refresh.mode`, `run.id`
- `pipeline.batch` — attrs `batch.size`, `batch.index`

Follow a pipeline end-to-end: `traces | where customDimensions.pipeline_name == "learners"`.

## Cosmos KQL — top RU consumers and hot partitions

```kusto
// Most-expensive operations in the last hour
CDBDataPlaneRequests
| where TimeGenerated > ago(1h)
| project TimeGenerated, OperationName, DatabaseName, CollectionName,
          RequestCharge, DurationMs, StatusCode
| top 50 by RequestCharge desc
```

```kusto
// Partition-key RU consumption — find the hot key
CDBPartitionKeyRUConsumption
| where TimeGenerated > ago(1h)
| summarize total_ru = sum(RequestCharge) by PartitionKey, CollectionName
| top 10 by total_ru desc
```

## Healthy looks like

- One `success` doc per pipeline per day in `sync_metadata`.
- `learners.watermark` advances monotonically.
- `rows_failed / rows_read < 0.001`.
- Cron-completion alert silent.
- Job duration within ±2× of baseline.
