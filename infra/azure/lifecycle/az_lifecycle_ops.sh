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
#
# Noetva R4-DRG/R4-I: the durability invariant is "a lifecycle transition
# is not authoritative until its new state and transition metadata have
# been durably persisted." That requires lifecycle_table_read to FAIL
# CLOSED on any real read failure -- distinct from a genuinely-missing
# row, which is the expected, safe-to-default first-ever-Start case
# (Section O/34) -- so no caller can mistake "the table is unreachable"
# for "this environment has simply never started."

# Reads one environment's lifecycle row. On success, returns the full
# entity JSON (including Azure's own `etag`) on stdout and exits 0. If the
# row genuinely does not exist yet (Azure Table Storage's stable
# ResourceNotFound/404 signal -- confirmed against Microsoft's documented
# Table service error codes; exact wording remains AZURE_RUNTIME_REQUIRED
# to reconfirm against a live account), returns `{}` and exits 0 -- this
# is the ONLY case allowed to default to an implicit DORMANT/never-started
# row. Every OTHER failure (auth/permission, network, throttling, a
# malformed response) prints a diagnostic to stderr and returns non-zero:
# the caller must treat that as "cannot determine lifecycle state" and
# abort BEFORE any Azure infrastructure mutation, never silently proceed
# as if DORMANT (Noetva R4-DRG Section N, R4-I Section 10).
lifecycle_table_read() {
  local environment="$1"
  local output exit_code
  output=$(az storage entity show \
    --account-name "$NOETVA_LIFECYCLE_STORAGE_ACCOUNT" \
    --table-name "noetvalifecyclestate" \
    --partition-key "noetva" \
    --row-key "$environment" \
    --auth-mode login \
    --output json 2>&1)
  exit_code=$?
  if [ "$exit_code" -eq 0 ]; then
    echo "$output"
    return 0
  fi
  if echo "$output" | grep -qi "ResourceNotFound\|does not exist\|(404)\|not found"; then
    echo "{}"
    return 0
  fi
  echo "lifecycle_table_read: FAILED reading '$environment' -- refusing to default to DORMANT (Noetva R4-DRG Section N/AR: exact Azure error text reconfirmed only during Azure-runtime verification)." >&2
  echo "$output" >&2
  return 1
}

# Converts a flat JSON object (as emitted by lifecycle_cli.py's
# apply-transition/persist-metadata `.entity`) into the `Key=Value
# [Key=Value ...]` argument list `az storage entity insert|replace
# --entity` requires. Null-valued keys are omitted entirely -- Azure Table
# Storage has no null; an absent property is the correct representation
# of "not set," matching how every reader in this codebase already
# treats a missing property (`jq -r '.foo // "default"'`).
_lifecycle_entity_args() {
  local entity_json="$1"
  echo "$entity_json" | jq -r 'to_entries | map(select(.value != null)) | map("\(.key)=\(.value|tostring)") | .[]'
}

# Inserts a BRAND-NEW lifecycle row (Noetva R4-DRG Section O/11: the
# first-ever Start for an environment is the bootstrap, not a separate
# initialization step). Azure Table Storage's Insert operation fails
# (HTTP 409 Conflict) if an entity with this PartitionKey+RowKey already
# exists -- a concurrent first writer therefore produces a conflict, never
# a silent clobber (Section 34's "first insert race does not clobber").
lifecycle_table_insert() {
  local environment="$1" entity_json="$2"
  local -a kv_args=()
  local _line
  while IFS= read -r _line; do
    [ -n "$_line" ] && kv_args+=("$_line")
  done < <(_lifecycle_entity_args "$entity_json")
  az storage entity insert \
    --account-name "$NOETVA_LIFECYCLE_STORAGE_ACCOUNT" \
    --table-name "noetvalifecyclestate" \
    --entity "PartitionKey=noetva" "RowKey=$environment" "${kv_args[@]}" \
    --auth-mode login
}

# Writes an EXISTING environment's lifecycle row with ETag-conditional
# replace (optimistic-lock layer 2, Noetva I-R2 Section 10). Fails loudly
# (non-zero exit, HTTP 412 Precondition Failed) on an ETag mismatch -- the
# caller must treat that as a lifecycle concurrency conflict and abort the
# workflow run, never retry blindly (R4-I Section 12).
lifecycle_table_write() {
  local environment="$1"
  local entity_json="$2"
  local expected_etag="$3"
  local -a kv_args=()
  local _line
  while IFS= read -r _line; do
    [ -n "$_line" ] && kv_args+=("$_line")
  done < <(_lifecycle_entity_args "$entity_json")
  az storage entity replace \
    --account-name "$NOETVA_LIFECYCLE_STORAGE_ACCOUNT" \
    --table-name "noetvalifecyclestate" \
    --entity "PartitionKey=noetva" "RowKey=$environment" "${kv_args[@]}" \
    --if-match "$expected_etag" \
    --auth-mode login
}

# Shared insert-vs-replace tail for both governed persistence wrappers
# below: `$current_result` is one `lifecycle_cli.py apply-transition` or
# `persist-metadata` JSON object, `{"entity": {...}, "isNewRow": bool}`.
_lifecycle_persist_result() {
  local environment="$1" row="$2" current_result="$3"
  local entity_json is_new_row expected_etag
  entity_json=$(echo "$current_result" | jq -c '.entity')
  is_new_row=$(echo "$current_result" | jq -r '.isNewRow')
  if [ "$is_new_row" = "true" ]; then
    lifecycle_table_insert "$environment" "$entity_json"
  else
    expected_etag=$(echo "$row" | jq -r '.etag // ""')
    lifecycle_table_write "$environment" "$entity_json" "$expected_etag"
  fi
}

# ---- Governed lifecycle persistence (Noetva R4-DRG Section AA/21-22) ----
# The SOLE authority every lifecycle workflow step uses to move a row
# forward: READ -> (lifecycle_table_read already distinguishes missing vs.
# failure) -> COMPUTE THE VALID NEXT ROW (via lifecycle_controller.py's
# apply_transition(), through lifecycle_cli.py -- never re-implemented
# here) -> CONDITIONAL PERSIST (insert-if-absent for a first-ever row,
# ETag-conditional replace otherwise). No workflow implements its own ad
# hoc lifecycle row-mutation logic; every write in every lifecycle
# workflow goes through one of these two functions.

# Real FSM state transitions (Start/Stop steps). Extra args after the
# required three are forwarded verbatim to `apply-transition` --
# `--workflow-run-id ID`, `--error MSG`, `--ttl-expires-at ISO8601`,
# `--db-auto-restart-risk-at ISO8601`.
lifecycle_apply_transition() {
  local environment="$1" target="$2" actor="$3"
  shift 3
  local row current_result
  row=$(lifecycle_table_read "$environment") || return 1
  if ! current_result=$(python3 "$(dirname "${BASH_SOURCE[0]}")/lifecycle_cli.py" apply-transition \
      --environment "$environment" --current-row-json "$row" --target "$target" --actor "$actor" "$@"); then
    echo "lifecycle_apply_transition: refused ($environment -> $target)" >&2
    echo "$current_result" >&2
    return 1
  fi
  _lifecycle_persist_result "$environment" "$row" "$current_result"
}

# Non-transition metadata updates (Extend's ttlExpiresAt, Hold's
# holdUntil, the restart-monitor's bounded-recheck lastError memory) --
# state itself is never touched. Forwards all args after environment/actor
# to `persist-metadata` -- `--workflow-run-id ID`, `--ttl-expires-at
# ISO8601`, `--hold-until ISO8601`, `--last-error MSG` (empty string
# clears it).
lifecycle_persist_metadata() {
  local environment="$1" actor="$2"
  shift 2
  local row current_result
  row=$(lifecycle_table_read "$environment") || return 1
  if ! current_result=$(python3 "$(dirname "${BASH_SOURCE[0]}")/lifecycle_cli.py" persist-metadata \
      --environment "$environment" --current-row-json "$row" --actor "$actor" "$@"); then
    echo "lifecycle_persist_metadata: refused ($environment)" >&2
    echo "$current_result" >&2
    return 1
  fi
  _lifecycle_persist_result "$environment" "$row" "$current_result"
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
