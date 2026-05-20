# --- Variables ---
variable "resource_group_name" {
  description = "Resource group name"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "job_name" {
  description = "Container App Job name (used in alert display names and KQL filters)"
  type        = string
}

variable "job_resource_id" {
  description = "Container App Job ARM resource ID (scope for activity-log alert)"
  type        = string
}

variable "cosmos_account_id" {
  description = "Cosmos DB account ARM resource ID (scope for throttling metric alert)"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace where the sync emits structured logs"
  type        = string
}

variable "action_group_id" {
  description = "Action Group ID notified when alerts fire"
  type        = string
}

variable "expected_min_rows" {
  description = "Volume-anomaly threshold — alert fires below this rowsRead total"
  type        = number
  default     = 1
}

variable "expected_max_rows" {
  description = "Volume-anomaly threshold — alert fires above this rowsRead total"
  type        = number
  default     = 10000000
}

variable "cosmos_throttle_threshold" {
  description = "Cosmos 429 (throttle) count over a 15-minute window that triggers the alert. Sustained throttling means it's time to consider autoscale."
  type        = number
  default     = 100
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}

# ---------------------------------------------------------------------------
# Alert 1 — Job execution failed
# Source: ContainerAppConsoleLogs_CL with status="failed" run summary.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "job_failed" {
  name                = "${var.job_name}-execution-failed"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  severity                         = 1
  evaluation_frequency             = "PT5M"
  window_duration                  = "PT10M"
  scopes                           = [var.log_analytics_workspace_id]
  auto_mitigation_enabled          = true
  workspace_alerts_storage_enabled = false

  criteria {
    query                   = <<-KQL
      ContainerAppConsoleLogs_CL
      | where ContainerAppName_s == "${var.job_name}"
      | where Log_s has "\"event\":\"sync.run.completed\""
      | where Log_s has "\"status\":\"failed\""
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [var.action_group_id]
  }
}

# ---------------------------------------------------------------------------
# Alert 2 — Partial data failure (rowsFailed > 0)
# ---------------------------------------------------------------------------
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "partial_failure" {
  name                = "${var.job_name}-partial-failure"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  severity                = 2
  evaluation_frequency    = "PT15M"
  window_duration         = "PT1H"
  scopes                  = [var.log_analytics_workspace_id]
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      ContainerAppConsoleLogs_CL
      | where ContainerAppName_s == "${var.job_name}"
      | where Log_s has "\"event\":\"sync.pipeline.completed\""
      | extend payload = parse_json(Log_s)
      | extend rowsFailed = toint(payload.rowsFailed)
      | where rowsFailed > 0
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [var.action_group_id]
  }
}

# ---------------------------------------------------------------------------
# Alert 3 — Missing daily success (no success log in last 26h)
# ---------------------------------------------------------------------------
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "missing_success" {
  name                = "${var.job_name}-missing-success"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  severity                = 1
  evaluation_frequency    = "PT1H"
  window_duration         = "PT2H"
  scopes                  = [var.log_analytics_workspace_id]
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      let lookback = 26h;
      let successCount = toscalar(
        ContainerAppConsoleLogs_CL
        | where TimeGenerated > ago(lookback)
        | where ContainerAppName_s == "${var.job_name}"
        | where Log_s has "\"event\":\"sync.run.completed\""
        | where Log_s has "\"status\":\"success\""
        | count
      );
      print missingRuns = iff(successCount == 0, 1, 0)
      | where missingRuns == 1
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [var.action_group_id]
  }
}

# ---------------------------------------------------------------------------
# Alert 4 — Abnormal volume (rowsRead outside expected envelope)
# ---------------------------------------------------------------------------
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "abnormal_volume" {
  name                = "${var.job_name}-abnormal-volume"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  severity                = 3
  evaluation_frequency    = "PT1H"
  window_duration         = "P1D"
  scopes                  = [var.log_analytics_workspace_id]
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      ContainerAppConsoleLogs_CL
      | where ContainerAppName_s == "${var.job_name}"
      | where Log_s has "\"event\":\"sync.run.completed\""
      | extend payload = parse_json(Log_s)
      | extend rowsRead = toint(payload.rowsRead)
      | where rowsRead < ${var.expected_min_rows} or rowsRead > ${var.expected_max_rows}
    KQL
    time_aggregation_method = "Count"
    threshold               = 0
    operator                = "GreaterThan"
  }

  action {
    action_groups = [var.action_group_id]
  }
}

# ---------------------------------------------------------------------------
# Alert 5 — Cosmos throttling (HTTP 429 / RU saturation)
# Metric alert on the Cosmos account, filtered to StatusCode=429.
# Fires on sustained throttling — the canary that says "you've outgrown the
# current capacity mode and should consider autoscale or higher RU/s".
# Transient single 429s are normal under burst; the SDK retries them.
# ---------------------------------------------------------------------------
resource "azurerm_monitor_metric_alert" "cosmos_throttled" {
  name                = "${var.job_name}-cosmos-throttled"
  resource_group_name = var.resource_group_name
  scopes              = [var.cosmos_account_id]
  tags                = var.tags

  severity             = 2
  frequency            = "PT5M"
  window_size          = "PT15M"
  auto_mitigate        = true
  target_resource_type = "Microsoft.DocumentDB/databaseAccounts"

  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "TotalRequests"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = var.cosmos_throttle_threshold

    dimension {
      name     = "StatusCode"
      operator = "Include"
      values   = ["429"]
    }
  }

  action {
    action_group_id = var.action_group_id
  }
}

# --- Outputs ---
output "alert_ids" {
  value = {
    job_failed       = azurerm_monitor_scheduled_query_rules_alert_v2.job_failed.id
    partial_failure  = azurerm_monitor_scheduled_query_rules_alert_v2.partial_failure.id
    missing_success  = azurerm_monitor_scheduled_query_rules_alert_v2.missing_success.id
    abnormal_volume  = azurerm_monitor_scheduled_query_rules_alert_v2.abnormal_volume.id
    cosmos_throttled = azurerm_monitor_metric_alert.cosmos_throttled.id
  }
}
