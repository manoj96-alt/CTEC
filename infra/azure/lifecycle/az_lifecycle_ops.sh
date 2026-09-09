#!/usr/bin/env bash
# Shared Azure-facing operations for every Noetva lifecycle workflow
# (Noetva I-R2 Section 22: "Do not duplicate lifecycle logic across
# multiple YAML files if a reusable helper/action/script can safely
# centralize it"). This is the ONLY place that invokes `az` for lifecycle
# purposes; lifecycle_controller.py holds the decision logic, this file
# holds the mechanism. Sourced (`source az_lifecycle_ops.sh`) by every
# lifecycle-*.yml workflow step and by azure-deploy.yml's interlock step.
#
# NOTHING in this file has been executed against a real Azure subscription
# in this phase -- no Azure login exists. It is reviewed for correctness
# and referenced by workflow YAML that itself only runs under GitHub
# Actions with real OIDC federation, later, in the controlled execution
# phase.
set -euo pipefail

# ---- Table Storage (lifecycle state) ----------------------------------

# Reads one environment's lifecycle row. Returns JSON on stdout (or empty
# if no row exists yet, which the caller treats as an implicit DORMANT/
# never-started row). Never assumes PostgreSQL is reachable to determine
# this (Noetva I-R2 Section 9's core requirement).
lifecycle_table_read() {
  local environment="$1"
  az storage entity show \
    --account-name "$NOETVA_LIFECYCLE_STORAGE_ACCOUNT" \
    --table-name "noetvalifecyclestate" \
    --partition-key "noetva" \
    --row-key "$environment" \
    --auth-mode login \
    --output json 2>/dev/null || echo "{}"
}

# Writes one environment's lifecycle row with ETag-conditional replace
# (optimistic-lock layer 2, Noetva I-R2 Section 10). Fails loudly (non-zero
# exit) on an ETag mismatch -- the caller must treat that as a LockConflict
# and abort the workflow run, never retry blindly.
lifecycle_table_write() {
  local environment="$1"
  local entity_json="$2"
  local expected_etag="$3"
  az storage entity replace \
    --account-name "$NOETVA_LIFECYCLE_STORAGE_ACCOUNT" \
    --table-name "noetvalifecyclestate" \
    --entity "PartitionKey=noetva" "RowKey=$environment" "$entity_json" \
    --if-match "$expected_etag" \
    --auth-mode login
}

# ---- PostgreSQL Flexible Server -----------------------------------------

postgres_start() {
  local resource_group="$1" server_name="$2"
  az postgres flexible-server start --resource-group "$resource_group" --name "$server_name"
}

postgres_stop() {
  local resource_group="$1" server_name="$2"
  az postgres flexible-server stop --resource-group "$resource_group" --name "$server_name"
}

postgres_state() {
  local resource_group="$1" server_name="$2"
  az postgres flexible-server show --resource-group "$resource_group" --name "$server_name" --query "state" -o tsv
}

# ---- Alert suppression (Noetva G-R3 Section 10-14) ----------------------
# Real Azure Monitor mechanism, verified against Microsoft's own
# documentation (not the fabricated "Storage-Table-lookup condition" a
# prior phase merely speculated about): a `Microsoft.AlertsManagement/
# actionRules` (Suppression type) resource whose `enabled` boolean is
# toggled directly. DISCLOSED LIMITATION: Microsoft's own docs state a
# just-toggled rule can take up to 30 minutes to actually start/stop
# affecting newly fired alerts -- this is not instantaneous, and the
# calling workflow must not assume it is.

alert_suppression_set() {
  local resource_group="$1" rule_name="$2" enabled="$3"
  az monitor alert-processing-rule update \
    --resource-group "$resource_group" --name "$rule_name" --enabled "$enabled"
}

# ---- Container Apps revisions -------------------------------------------
# Governed DORMANT uses revision deactivation, never bare minReplicas=0
# (Noetva G-R2 Section 9 / I-R2 Section 7/8) -- a deactivated revision will
# not scale back up on inbound traffic; only an explicit `activate` call
# (below) brings it back.

containerapp_active_revision_name() {
  local resource_group="$1" app_name="$2"
  az containerapp revision list --resource-group "$resource_group" --name "$app_name" \
    --query "[?properties.active].name | [0]" -o tsv
}

containerapp_activate_revision() {
  local resource_group="$1" app_name="$2" revision_name="$3"
  az containerapp revision activate --resource-group "$resource_group" --revision "$revision_name"
}

containerapp_deactivate_revision() {
  local resource_group="$1" app_name="$2" revision_name="$3"
  az containerapp revision deactivate --resource-group "$resource_group" --revision "$revision_name"
}

containerapp_revision_active() {
  local resource_group="$1" revision_name="$2"
  az containerapp revision show --resource-group "$resource_group" --revision "$revision_name" --query "properties.active" -o tsv
}

# ---- Migration Job status (Noetva I-R2 Section 23) ----------------------

migration_job_is_running() {
  local resource_group="$1" job_name="$2"
  local status
  status=$(az containerapp job execution list --resource-group "$resource_group" --name "$job_name" \
    --query "[0].properties.status" -o tsv 2>/dev/null || echo "None")
  [ "$status" = "Running" ]
}

# ---- Deployment-in-progress check (Noetva I-R2 Section 22/AA) -----------
# Queries this repository's own azure-deploy.yml runs via the GitHub API
# (not an Azure call) -- requires GH_TOKEN in the environment.

deployment_in_progress_for_environment() {
  local environment="$1"
  gh run list --workflow=azure-deploy.yml --status=in_progress --json displayTitle,status \
    --jq ".[] | select(.displayTitle | contains(\"$environment\"))" | grep -q . && return 0 || return 1
}

# ---- DB session safety (Noetva I-R2 Section 24) --------------------------
# Uses the ADMIN authority ONLY for this one narrow diagnostic query -- never
# to terminate a session automatically (not authorized by R2).

postgres_has_unsafe_long_running_session() {
  local host="$1" admin_user="$2" threshold_minutes="${3:-15}"
  local count
  count=$(PGPASSWORD="$NOETVA_PG_ADMIN_PASSWORD" psql -h "$host" -U "$admin_user" -d ctec -tAc \
    "SELECT count(*) FROM pg_stat_activity WHERE state != 'idle' AND usename NOT IN ('$admin_user') AND now() - query_start > interval '$threshold_minutes minutes'")
  [ "${count:-0}" -gt 0 ]
}
