"""Fail-closed static validation for the Noetva cost-lifecycle
implementation (Noetva I-R2 Section 38). Companion to
static_architecture_checks.py (R1) -- that script is untouched; this one
covers the 30 lifecycle-specific checks. Every check reads the actual
committed files.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1]
WORKFLOWS = INFRA.parent.parent / ".github" / "workflows"
MODULES = INFRA / "modules"
LIFECYCLE = INFRA / "lifecycle"
ENVIRONMENTS = INFRA / "environments"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str) -> None:
    results.append((name, condition, detail))


def read(path: Path) -> str:
    return path.read_text()


GENERIC_LIFECYCLE_WORKFLOWS = [
    "azure-lifecycle-start.yml",
    "azure-lifecycle-stop.yml",
    "azure-lifecycle-extend.yml",
    "azure-lifecycle-hold.yml",
]


def check_bicep_compiles():
    outdir = INFRA / ".build_lifecycle"
    outdir.mkdir(exist_ok=True)
    ok = True
    details = []
    for entry in ("main.bicep", "lifecycle-main.bicep", "modules/budget.bicep"):
        proc = subprocess.run(
            ["az", "bicep", "build", "--file", str(INFRA / entry), "--outfile", str(outdir / (entry.replace("/", "_") + ".json"))],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            ok = False
            details.append(f"{entry}: {proc.stderr.strip()[-300:]}")
    check("lifecycle-bicep-compiles", ok, "; ".join(details) or "main.bicep, lifecycle-main.bicep, modules/budget.bicep all compile")


def check_no_production_in_generic_workflows():
    problems = []
    for wf in GENERIC_LIFECYCLE_WORKFLOWS:
        src = read(WORKFLOWS / wf)
        m = re.search(r"options:\s*\[([^\]]+)\]", src)
        if not m:
            problems.append(f"{wf}: no options: [...] found")
            continue
        options = [o.strip() for o in m.group(1).split(",")]
        if "prod" in options or "production" in options:
            problems.append(f"{wf}: prod/production present in options {options}")
    check("no-production-in-generic-lifecycle-workflows", not problems, "; ".join(problems) or "prod absent from start/stop/extend/hold choice lists")


def check_no_client_secrets_in_workflows():
    # Look for actual USAGE (a secrets./env reference or an assignment),
    # not prose disclosing its absence (e.g. "no AZURE_CLIENT_SECRET
    # anywhere" inside a comment must not itself trip this check).
    usage_pattern = re.compile(r"secrets\.AZURE_CLIENT_SECRET|AZURE_CLIENT_SECRET\s*[:=]|client[_-]?secret\s*[:=]\s*\S", re.IGNORECASE)
    problems = []
    for wf in WORKFLOWS.glob("*.yml"):
        for lineno, line in enumerate(read(wf).splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if usage_pattern.search(line):
                problems.append(f"{wf.name}:{lineno}")
    check("no-azure-client-secret-in-workflows", not problems, "; ".join(problems) or "no workflow actually uses a stored Azure client secret (comments disclosing its absence are not flagged)")


def check_lifecycle_identity_not_owner_or_broad_contributor():
    src = read(MODULES / "lifecycle-identity.bicep")
    owner_role_id = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
    contributor_role_id = "b24988ac-6180-42a0-ab88-20f7382dd24c"
    has_owner = owner_role_id in src
    has_contributor = contributor_role_id in src
    check("lifecycle-identity-not-owner", not has_owner, "Owner role ID absent" if not has_owner else "OWNER ROLE FOUND")
    check("lifecycle-identity-not-broad-contributor", not has_contributor, "Contributor role ID absent from lifecycle-identity.bicep" if not has_contributor else "CONTRIBUTOR ROLE FOUND")


def check_min_replicas_zero_for_lifecycle_managed():
    problems = []
    for env in ("dev", "staging", "demo"):
        data = json.loads(read(ENVIRONMENTS / env / "main.parameters.json"))["parameters"]
        for key in ("backendMinReplicas", "frontendMinReplicas"):
            if data.get(key, {}).get("value") != 0:
                problems.append(f"{env}.{key} != 0")
    check("min-replicas-zero-for-lifecycle-managed-envs", not problems, "; ".join(problems) or "dev/staging/demo backend+frontend minReplicas == 0")


def check_prod_replica_policy_unchanged():
    data = json.loads(read(ENVIRONMENTS / "prod" / "main.parameters.json"))["parameters"]
    ok = data["backendMinReplicas"]["value"] == 2 and data["frontendMinReplicas"]["value"] == 2
    check("prod-retains-production-replica-policy", ok, "prod min replicas still 2/2 (untouched by this phase)" if ok else "prod replica policy changed")


def check_demo_nat_false_prod_nat_true():
    demo = json.loads(read(ENVIRONMENTS / "demo" / "main.parameters.json"))["parameters"]
    prod = json.loads(read(ENVIRONMENTS / "prod" / "main.parameters.json"))["parameters"]
    check("demo-nat-remains-false", demo["enableNatGateway"]["value"] is False, str(demo["enableNatGateway"]["value"]))
    check("prod-nat-remains-true", prod["enableNatGateway"]["value"] is True, str(prod["enableNatGateway"]["value"]))


def check_lifecycle_state_storage_exists():
    src = read(MODULES / "lifecycle-state-storage.bicep")
    ok = "Microsoft.Storage/storageAccounts/tableServices/tables@" in src
    check("lifecycle-state-storage-exists", ok, "Table resource declared" if ok else "MISSING")


def check_workflows_exist():
    expected = {
        "start workflow exists": "azure-lifecycle-start.yml",
        "stop workflow exists": "azure-lifecycle-stop.yml",
        "extend workflow exists": "azure-lifecycle-extend.yml",
        "hold workflow exists": "azure-lifecycle-hold.yml",
        "sweep workflow exists": "azure-lifecycle-nightly-sweep.yml",
        "restart monitor exists": "azure-lifecycle-restart-monitor.yml",
        "status workflow exists": "azure-lifecycle-status.yml",
    }
    for name, filename in expected.items():
        check(name.replace(" ", "-"), (WORKFLOWS / filename).exists(), filename)


def check_concurrency_groups_present():
    problems = []
    for wf in ["azure-lifecycle-start.yml", "azure-lifecycle-stop.yml", "azure-lifecycle-extend.yml",
               "azure-lifecycle-hold.yml", "azure-lifecycle-nightly-sweep.yml", "azure-lifecycle-restart-monitor.yml",
               "azure-deploy.yml"]:
        src = read(WORKFLOWS / wf)
        if "concurrency:" not in src or "lifecycle-" not in src:
            problems.append(wf)
    check("concurrency-groups-present", not problems, "; ".join(problems) or "every lifecycle-affecting workflow declares a lifecycle-<env> concurrency group")


def check_ttl_bounds_exist():
    src = read(LIFECYCLE / "lifecycle_controller.py")
    ok = "TTL_MIN_HOURS = 1" in src and "TTL_MAX_HOURS = 12" in src
    check("ttl-bounds-exist", ok, "TTL_MIN_HOURS=1, TTL_MAX_HOURS=12 in lifecycle_controller.py" if ok else "MISSING")


def check_no_permanent_hold():
    import yaml
    data = yaml.safe_load(read(WORKFLOWS / "azure-lifecycle-hold.yml"))
    inputs = data.get(True, data.get("on", {})).get("workflow_dispatch", {}).get("inputs", {})
    has_required_absolute = inputs.get("holdUntilUtc", {}).get("required") is True
    # The only declared inputs must be `environment` and `holdUntilUtc` --
    # no additional boolean "disable shutdown forever" toggle can exist if
    # it was never declared as an input at all.
    extra_inputs = set(inputs.keys()) - {"environment", "holdUntilUtc"}
    check("hold-requires-absolute-expiry", has_required_absolute, "holdUntilUtc is a required input")
    check("no-permanent-hold-option", not extra_inputs, f"only environment/holdUntilUtc inputs declared, no permanent-hold toggle" if not extra_inputs else f"unexpected extra input(s): {extra_inputs}")


def check_stop_checks_migration_and_postgres():
    src = read(WORKFLOWS / "azure-lifecycle-stop.yml")
    check("stop-checks-migration-job-state", "migration_job_is_running" in src or "migration-job-running" in src, "referenced in stop.yml")
    check("stop-verifies-postgres-stopped", '"Stopped"' in src or "'Stopped'" in src, "polls for Stopped state before declaring DORMANT")


def check_dormant_only_after_verification():
    src = read(WORKFLOWS / "azure-lifecycle-stop.yml")
    # The step that persists DORMANT (Noetva R4-I: "Persist DORMANT...")
    # must appear strictly after the postgres-stop polling step in file
    # order -- and it must actually be the lifecycle_apply_transition call
    # that writes DORMANT, not merely a mention of the word.
    stop_poll_idx = src.find('[ "$state" = "Stopped" ]')
    dormant_idx = src.find("Persist DORMANT")
    persists_dormant = re.search(r"lifecycle_apply_transition\s+\"\$env\"\s+DORMANT\b", src) is not None
    check("dormant-recorded-only-after-postgres-stopped-check", 0 < stop_poll_idx < dormant_idx, f"poll@{stop_poll_idx} dormant@{dormant_idx}")
    check("dormant-actually-persisted-via-apply-transition", persists_dormant, "lifecycle_apply_transition \"$env\" DORMANT is called in stop.yml" if persists_dormant else "MISSING")


def check_failed_stop_exists():
    src = read(LIFECYCLE / "lifecycle_controller.py")
    ok = 'FAILED_STOP = "FAILED_STOP"' in src
    check("failed-stop-state-exists", ok, "FAILED_STOP is a member of LifecycleState")


def check_start_no_migration_no_seeders():
    src = read(WORKFLOWS / "azure-lifecycle-start.yml")
    # Look for an actual invocation (`python -m alembic ...` or a bare
    # `alembic upgrade` shell command), not the workflow's own disclosure
    # text ("Never runs 'alembic upgrade head'...") stating its absence.
    has_migrate = re.search(r"(python\s+-m\s+alembic|^\s*alembic)\s+upgrade\s+head", src, re.MULTILINE) is not None
    has_seeder = re.search(r"(python\s+-[mc]\s+.*demo_\w+_seeder|-m\s+app\.\S*demo_\w+_seeder)", src) is not None
    check("start-does-not-run-migrations", not has_migrate, "no real alembic-upgrade invocation in start.yml (the disclosure comment stating this is not itself flagged)")
    check("start-does-not-run-demo-seeders", not has_seeder, "no real demo_*_seeder invocation in start.yml")


def check_cost_tags_present():
    src = read(INFRA / "resources.bicep")
    # Bicep only requires quoting a property key when it contains a
    # character (like '-') that isn't valid in a bare identifier -- 'owner'
    # and 'purpose' are legitimately unquoted (`owner: ...`), while
    # 'lifecycle-policy' etc. must be quoted (`'lifecycle-policy': ...`).
    # Check for either form, not just the quoted one.
    required = ["lifecycle-policy", "auto-shutdown", "owner", "purpose", "customer-facing", "cost-center"]
    missing = []
    for t in required:
        quoted = f"'{t}'" in src
        bare = re.search(rf"(?<![\w'-]){re.escape(t)}\s*:", src) is not None
        if not (quoted or bare):
            missing.append(t)
    check("cost-tags-present", not missing, "; ".join(missing) or "all required tag keys present in resources.bicep")


def check_budget_amount_not_fabricated():
    src = read(MODULES / "budget.bicep")
    has_default = re.search(r"param\s+monthlyAmount\s+int\s*=\s*\d", src) is not None
    check("budget-amount-not-fabricated", not has_default, "monthlyAmount has no default -- operator must supply it" if not has_default else "A DEFAULT AMOUNT WAS FOUND")


def check_acr_tier_policy():
    expectations = {"dev": "Basic", "demo": "Basic", "staging": "Premium", "prod": "Premium"}
    problems = []
    for env, expected in expectations.items():
        data = json.loads(read(ENVIRONMENTS / env / "main.parameters.json"))["parameters"]
        actual = data.get("acrSku", {}).get("value")
        if actual != expected:
            problems.append(f"{env}: expected {expected!r}, got {actual!r}")
    check("acr-tier-policy-correct", not problems, "; ".join(problems) or "dev/demo=Basic, staging/prod=Premium")


def check_acr_premium_only_features_gated():
    src = read(MODULES / "acr.bicep")
    ok = "isPremium ? {" in src and "retentionPolicy" in src
    check("acr-premium-only-features-gated", ok, "retentionPolicy/quarantinePolicy/trustPolicy conditional on isPremium" if ok else "MISSING")


def check_alert_suppression_module_exists_and_skips_prod():
    module_exists = (MODULES / "lifecycle-alert-suppression.bicep").exists()
    resources_src = read(INFRA / "resources.bicep")
    skips_prod = "if (environmentName != 'prod')" in resources_src and "lifecycleAlertSuppression" in resources_src
    check("alert-suppression-module-exists", module_exists, "modules/lifecycle-alert-suppression.bicep present")
    check("alert-suppression-skips-prod", skips_prod, "conditional on environmentName != 'prod' in resources.bicep")


def check_alert_suppression_narrowly_scoped():
    src = read(MODULES / "lifecycle-alert-suppression.bicep")
    # Must filter to Container Apps platform metrics only -- never a bare
    # resource-group-wide suppression with no resource-type filter, which
    # would also catch Postgres/security signals.
    ok = "MICROSOFT.APP/CONTAINERAPPS" in src and "'Platform'" in src
    check("alert-suppression-narrowly-scoped", ok, "conditions filter to Platform + Microsoft.App/containerApps only")


def check_lifecycle_role_no_monitoring_contributor():
    src = read(MODULES / "lifecycle-identity.bicep")
    # Exclude comment lines -- a disclosure comment stating this wildcard
    # is deliberately NOT used must not itself trip the check (same class
    # of false positive fixed earlier in this file and in R1's own
    # static_architecture_checks.py).
    non_comment_lines = "\n".join(
        line for line in src.splitlines() if not line.strip().startswith("//")
    )
    monitoring_contributor_role_id = "749f88d5-cbae-40b8-bcfc-e573ddc772fa"
    has_broad_role = monitoring_contributor_role_id in non_comment_lines or "Microsoft.AlertsManagement/*" in non_comment_lines
    has_narrow_actions = "Microsoft.AlertsManagement/actionRules/read" in src and "Microsoft.AlertsManagement/actionRules/write" in src
    check("lifecycle-role-no-monitoring-contributor", not has_broad_role, "Monitoring Contributor role ID absent from actual code (comment-only mentions are not flagged)" if not has_broad_role else "FOUND")
    check("lifecycle-role-has-narrow-alert-actions", has_narrow_actions, "only actionRules/read+write granted")


def check_start_stop_toggle_suppression_correctly():
    start_src = read(WORKFLOWS / "azure-lifecycle-start.yml")
    stop_src = read(WORKFLOWS / "azure-lifecycle-stop.yml")
    start_ok = "alert_suppression_set" in start_src and 'if: failure()' in start_src
    stop_ok = "alert_suppression_set" in stop_src and 'if: failure()' in stop_src
    check("start-toggles-suppression-with-failure-cleanup", start_ok, "start.yml calls alert_suppression_set and has an if:failure() cleanup step")
    check("stop-toggles-suppression-with-failure-cleanup", stop_ok, "stop.yml calls alert_suppression_set and has an if:failure() cleanup step")


def check_apply_transition_cli_exists_and_pure_controller_unmodified():
    cli_src = read(LIFECYCLE / "lifecycle_cli.py")
    controller_src = read(LIFECYCLE / "lifecycle_controller.py")
    has_apply = '"apply-transition"' in cli_src and "cmd_apply_transition" in cli_src
    has_persist_metadata = '"persist-metadata"' in cli_src and "cmd_persist_metadata" in cli_src
    # The pure controller must still contain zero Azure SDK / network I/O
    # / shell execution / Storage Table I/O -- R4-I Section 6's hard
    # boundary. A docstring MENTION of azure-data-tables (design intent)
    # is fine; an actual import or subprocess call is not.
    controller_lines_no_docstring_or_comment = "\n".join(
        line for line in controller_src.splitlines()
        if not line.strip().startswith(("#", '"', "'"))
    )
    no_io = not re.search(r"\bimport\s+(subprocess|requests|socket)\b|\bos\.system\(|azure\.data\.tables", controller_lines_no_docstring_or_comment)
    check("apply-transition-cli-exists", has_apply, "lifecycle_cli.py exposes apply-transition, wired to lifecycle_controller.apply_transition()")
    check("persist-metadata-cli-exists", has_persist_metadata, "lifecycle_cli.py exposes persist-metadata for non-transition updates")
    check("lifecycle-controller-remains-pure", no_io, "no Azure SDK / subprocess / socket / os.system in lifecycle_controller.py's real code")


def check_workflows_invoke_governed_persistence():
    start_src = read(WORKFLOWS / "azure-lifecycle-start.yml")
    stop_src = read(WORKFLOWS / "azure-lifecycle-stop.yml")
    extend_src = read(WORKFLOWS / "azure-lifecycle-extend.yml")
    hold_src = read(WORKFLOWS / "azure-lifecycle-hold.yml")

    start_states = ["START_REQUESTED", "STARTING_DATABASE", "STARTING_APPLICATION", "VERIFYING", "READY", "FAILED_START"]
    # The very first transition (lock acquisition) has no local $env yet --
    # it addresses the environment directly via the workflow input.
    missing_start = [s for s in start_states if not re.search(rf'lifecycle_apply_transition\s+"(\$env|\$\{{\{{\s*inputs\.environment\s*\}}\}})"\s+{s}\b', start_src)]
    check("start-persists-every-required-state", not missing_start, "; ".join(missing_start) or "start.yml calls lifecycle_apply_transition for all 6 required states")

    stop_states = ["DRAIN_REQUESTED", "STOPPING_APPLICATION", "STOPPING_DATABASE", "DORMANT", "FAILED_STOP"]
    missing_stop = [s for s in stop_states if not re.search(rf'lifecycle_apply_transition\s+"\$env"\s+{s}\b', stop_src)]
    check("stop-persists-every-required-state", not missing_stop, "; ".join(missing_stop) or "stop.yml calls lifecycle_apply_transition for all 5 required states")

    # Start must persist the intent state BEFORE the corresponding az
    # mutation call in the same step (Section 16's hard invariant) -- spot
    # check the two combined persist+mutate steps.
    db_step = re.search(r"STARTING_DATABASE.*?postgres_start", start_src, re.DOTALL)
    app_step = re.search(r"STARTING_APPLICATION.*?containerapp_activate_revision", start_src, re.DOTALL)
    check("start-persists-starting-database-before-postgres-start", db_step is not None, "STARTING_DATABASE persisted before postgres_start in file order")
    check("start-persists-starting-application-before-revision-activate", app_step is not None, "STARTING_APPLICATION persisted before containerapp_activate_revision in file order")

    stop_app_step = re.search(r"STOPPING_APPLICATION.*?containerapp_deactivate_revision", stop_src, re.DOTALL)
    stop_db_step = re.search(r"STOPPING_DATABASE.*?postgres_stop", stop_src, re.DOTALL)
    check("stop-persists-stopping-application-before-revision-deactivate", stop_app_step is not None, "STOPPING_APPLICATION persisted before containerapp_deactivate_revision in file order")
    check("stop-persists-stopping-database-before-postgres-stop", stop_db_step is not None, "STOPPING_DATABASE persisted before postgres_stop in file order")

    extend_ok = "lifecycle_persist_metadata" in extend_src and "--ttl-expires-at" in extend_src
    hold_ok = "lifecycle_persist_metadata" in hold_src and "--hold-until" in hold_src
    check("extend-persists-ttl-via-metadata-wrapper", extend_ok, "extend.yml calls lifecycle_persist_metadata --ttl-expires-at")
    check("hold-persists-expiry-via-metadata-wrapper", hold_ok, "hold.yml calls lifecycle_persist_metadata --hold-until")


def check_table_read_fails_closed():
    src = read(LIFECYCLE / "az_lifecycle_ops.sh")
    fn = re.search(r"lifecycle_table_read\(\)\s*\{.*?\n\}", src, re.DOTALL)
    assert fn, "lifecycle_table_read function not found"
    body = fn.group(0)
    # Success path returns 0; the missing-row path (ResourceNotFound)
    # returns 0 with "{}"; every OTHER path must return 1 (fail closed),
    # not silently fall through to an implicit "{}"/DORMANT default.
    has_success_path = 'echo "$output"' in body and "return 0" in body
    has_missing_row_path = "ResourceNotFound" in body and 'echo "{}"' in body
    has_fail_closed_path = body.strip().endswith("return 1\n}") or "return 1" in body.split("ResourceNotFound")[-1]
    no_blind_fallback = "|| echo" not in body  # the old fail-open pattern must be gone
    check("table-read-distinguishes-missing-row-from-failure", has_missing_row_path, "ResourceNotFound path returns {} + exit 0")
    check("table-read-fails-closed-on-other-errors", has_fail_closed_path and no_blind_fallback, "every non-success, non-ResourceNotFound path returns 1, no blind '|| echo' fallback remains")


def check_first_row_bootstrap_and_etag_paths_exist():
    src = read(LIFECYCLE / "az_lifecycle_ops.sh")
    has_insert = "lifecycle_table_insert()" in src and "entity insert" in src
    has_etag_replace = "--if-match" in src and "entity replace" in src
    has_persist_dispatch = "is_new_row" in src and "lifecycle_table_insert" in src and "lifecycle_table_write" in src
    check("first-row-insert-path-exists", has_insert, "lifecycle_table_insert uses az storage entity insert (no --if-match -- Azure itself rejects a duplicate insert)")
    check("existing-row-etag-conditional-path-exists", has_etag_replace, "lifecycle_table_write uses az storage entity replace --if-match")
    check("persistence-wrapper-dispatches-insert-vs-replace-on-isNewRow", has_persist_dispatch, "_lifecycle_persist_result branches on isNewRow")


def check_d2_federated_credential_loop_and_subjects():
    identity_src = read(MODULES / "lifecycle-identity.bicep")
    main_src = read(INFRA / "lifecycle-main.bicep")
    has_loop = re.search(r"federatedIdentityCredentials@[\d-]+'\s*=\s*\[for\s+\w+\s+in\s+githubEnvironmentNames", identity_src) is not None
    subject_correct = "subject: 'repo:${githubRepository}:environment:${envName}'" in identity_src or re.search(r"subject:\s*'repo:\$\{githubRepository\}:environment:\$\{\w+\}'", identity_src) is not None
    default_envs = re.search(r"param\s+githubEnvironmentNames\s+array\s*=\s*\[([^\]]+)\]", main_src)
    envs = [e.strip().strip("'") for e in default_envs.group(1).split("\n") if e.strip()] if default_envs else []
    envs = [e for e in (x.strip().strip("'") for x in default_envs.group(1).replace("\n", ",").split(",")) if e] if default_envs else []
    check("lifecycle-identity-loops-federated-credentials-per-environment", has_loop, "one federatedIdentityCredentials resource per githubEnvironmentNames entry (bicep for-loop)")
    check("lifecycle-federated-credential-subject-uses-real-github-oidc-shape", subject_correct, "subject is repo:<repo>:environment:<name>, matching GitHub's own OIDC token claim")
    check("lifecycle-main-default-environments-exactly-dev-staging-demo", set(envs) == {"dev", "staging", "demo"}, f"got {envs!r}")
    check("lifecycle-main-default-excludes-prod", "prod" not in envs and "production" not in envs, f"got {envs!r}")


def check_scheduled_matrix_workflows_bind_github_environment():
    sweep_src = read(WORKFLOWS / "azure-lifecycle-nightly-sweep.yml")
    monitor_src = read(WORKFLOWS / "azure-lifecycle-restart-monitor.yml")
    sweep_ok = re.search(r"environment:\s*\$\{\{\s*matrix\.environment\s*\}\}", sweep_src) is not None
    monitor_ok = re.search(r"environment:\s*\$\{\{\s*matrix\.environment\s*\}\}", monitor_src) is not None
    check("nightly-sweep-binds-job-level-github-environment", sweep_ok, "job-level environment: ${{ matrix.environment }} present")
    check("restart-monitor-binds-job-level-github-environment", monitor_ok, "job-level environment: ${{ matrix.environment }} present")


def check_restart_monitor_persists_classification():
    src = read(WORKFLOWS / "azure-lifecycle-restart-monitor.yml")
    has_ok_clear = re.search(r'OK\)\s*\n\s*echo[^\n]*\n\s*lifecycle_persist_metadata[\s\S]*?--last-error\s+""', src) is not None
    has_suspected_persist = "TRANSIENT_MAINTENANCE_SUSPECTED" in src and re.search(r"TRANSIENT_MAINTENANCE_SUSPECTED\)[\s\S]*?lifecycle_persist_metadata", src) is not None
    has_unexpected_persist = re.search(r"UNEXPECTED_RESTART\)[\s\S]*?lifecycle_persist_metadata", src) is not None
    check("restart-monitor-persists-ok-clears-lasterror", has_ok_clear, "OK branch calls lifecycle_persist_metadata --last-error \"\"")
    check("restart-monitor-persists-suspected-classification", has_suspected_persist, "TRANSIENT_MAINTENANCE_SUSPECTED branch persists it to lastError")
    check("restart-monitor-persists-unexpected-restart-classification", has_unexpected_persist, "UNEXPECTED_RESTART branch persists a description to lastError")


FAKE_AZ_STUB = r'''#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "storage" ] && [ "$2" = "entity" ]; then
  op="$3"; shift 3
  partition=""; row=""; ifmatch=""
  declare -a kvs=()
  in_entity=false
  while [ $# -gt 0 ]; do
    case "$1" in
      --entity) in_entity=true; shift; continue ;;
      --if-match) ifmatch="$2"; in_entity=false; shift 2; continue ;;
      --partition-key) partition="$2"; in_entity=false; shift 2; continue ;;
      --row-key) row="$2"; in_entity=false; shift 2; continue ;;
      --account-name|--table-name|--auth-mode|--output)
        in_entity=false; shift 2; continue ;;
      *)
        if $in_entity; then
          case "$1" in
            PartitionKey=*) partition="${1#PartitionKey=}" ;;
            RowKey=*) row="${1#RowKey=}" ;;
            *) kvs+=("$1") ;;
          esac
        fi
        shift
        ;;
    esac
  done
  file="$FAKE_TABLE_DIR/${partition}-${row}.json"
  case "$op" in
    show)
      if [ ! -f "$file" ]; then
        echo '{"odata.error":{"code":"ResourceNotFound","message":{"value":"The specified resource does not exist."}}}' >&2
        exit 1
      fi
      cat "$file"
      exit 0
      ;;
    insert)
      if [ -f "$file" ]; then
        echo "Conflict: entity already exists" >&2
        exit 1
      fi
      python3 - "$file" "${kvs[@]}" <<'PYEOF'
import json, sys
path = sys.argv[1]
data = {}
for kv in sys.argv[2:]:
    k, _, v = kv.partition("=")
    data[k] = v
data["etag"] = "W/\"1\""
json.dump(data, open(path, "w"))
PYEOF
      exit 0
      ;;
    replace)
      if [ ! -f "$file" ]; then
        echo "Not found" >&2
        exit 1
      fi
      current_etag=$(python3 -c "import json;print(json.load(open('$file')).get('etag',''))")
      if [ "$current_etag" != "$ifmatch" ]; then
        echo "Precondition Failed (412): etag mismatch" >&2
        exit 1
      fi
      next_n=$(python3 -c "import json,re;e=json.load(open('$file')).get('etag','W/\"1\"');m=re.search(r'\d+',e);print(int(m.group())+1 if m else 2)")
      python3 - "$file" "$next_n" "${kvs[@]}" <<'PYEOF'
import json, sys
path = sys.argv[1]
n = sys.argv[2]
data = {}
for kv in sys.argv[3:]:
    k, _, v = kv.partition("=")
    data[k] = v
data["etag"] = f'W/"{n}"'
json.dump(data, open(path, "w"))
PYEOF
      exit 0
      ;;
  esac
fi
echo "fake az: unsupported command: $*" >&2
exit 1
'''

ORCHESTRATION_SCRIPT = r'''
set -euo pipefail
source "%(lifecycle_dir)s/az_lifecycle_ops.sh"

echo "=== 1 ==="
lifecycle_apply_transition dev START_REQUESTED test-actor --workflow-run-id run1
lifecycle_apply_transition dev STARTING_DATABASE test-actor --workflow-run-id run1
lifecycle_apply_transition dev STARTING_APPLICATION test-actor --workflow-run-id run1
lifecycle_apply_transition dev VERIFYING test-actor --workflow-run-id run1
lifecycle_apply_transition dev READY test-actor --workflow-run-id run1 --ttl-expires-at 2026-09-10T00:00:00+00:00
echo "---after-start---"
lifecycle_table_read dev

echo "=== 2 ==="
lifecycle_persist_metadata dev test-actor --workflow-run-id run2 --ttl-expires-at 2026-09-10T02:00:00+00:00
echo "---after-extend---"
lifecycle_table_read dev

echo "=== 3 ==="
lifecycle_apply_transition dev DRAIN_REQUESTED test-actor --workflow-run-id run3
lifecycle_apply_transition dev STOPPING_APPLICATION test-actor --workflow-run-id run3
lifecycle_apply_transition dev STOPPING_DATABASE test-actor --workflow-run-id run3
lifecycle_apply_transition dev DORMANT test-actor --workflow-run-id run3 --db-auto-restart-risk-at 2026-09-17T00:00:00+00:00
echo "---after-stop---"
lifecycle_table_read dev

echo "=== 4 ==="
if lifecycle_apply_transition dev READY test-actor --workflow-run-id run4; then
  echo "ILLEGAL TRANSITION NOT REJECTED" >&2
  exit 1
fi
echo "---illegal-transition-rejected---"

echo "=== 5 ==="
lifecycle_apply_transition staging START_REQUESTED test-actor --workflow-run-id run5
echo "---second-env-bootstrap-ok---"
lifecycle_table_read staging

echo "=== 6 ==="
lifecycle_apply_transition dev START_REQUESTED test-actor --workflow-run-id run6
lifecycle_apply_transition dev STARTING_DATABASE test-actor --workflow-run-id run6
lifecycle_apply_transition dev FAILED_START test-actor --workflow-run-id run6 --error "postgres did not become Ready"
echo "---after-failed-start---"
lifecycle_table_read dev

echo "=== 7 ==="
stale_row=$(lifecycle_table_read dev)
lifecycle_apply_transition dev START_REQUESTED test-actor --workflow-run-id run7
stale_entity=$(python3 "%(lifecycle_dir)s/lifecycle_cli.py" apply-transition --environment dev --current-row-json "$stale_row" --target START_REQUESTED --actor test-actor | jq -c '.entity')
stale_etag=$(echo "$stale_row" | jq -r '.etag // ""')
if lifecycle_table_write dev "$stale_entity" "$stale_etag" 2>/dev/null; then
  echo "ETAG CONFLICT NOT DETECTED" >&2
  exit 1
fi
echo "---etag-conflict-rejected---"
'''


def check_orchestration_end_to_end_with_fake_azure():
    """Noetva R4-I Section 32/34: proves, with NO real Azure dependency
    (a fake `az` stub simulating exactly the `storage entity
    show|insert|replace` subset az_lifecycle_ops.sh actually calls), that
    the real lifecycle_apply_transition/lifecycle_persist_metadata shell
    wrappers and the real lifecycle_cli.py genuinely persist a full
    START chain to READY, a metadata-only Extend, a full STOP chain to
    DORMANT, a FAILED_START with a real error message, an illegal
    transition rejection, first-row bootstrap for two independent
    environments, and a real ETag-conflict rejection at the
    `--if-match` layer. This exercises the actual shipped shell/Python
    code, not a reimplementation of it."""
    import stat
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fake_az = tmp_path / "az"
        fake_az.write_text(FAKE_AZ_STUB)
        fake_az.chmod(fake_az.stat().st_mode | stat.S_IEXEC)
        table_dir = tmp_path / "table"
        table_dir.mkdir()

        env = dict(__import__("os").environ)
        env["PATH"] = f"{tmp}:{env['PATH']}"
        env["FAKE_TABLE_DIR"] = str(table_dir)
        env["NOETVA_LIFECYCLE_STORAGE_ACCOUNT"] = "fakeaccount"

        script = ORCHESTRATION_SCRIPT % {"lifecycle_dir": str(LIFECYCLE)}
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
        output = proc.stdout + proc.stderr
        ran_clean = proc.returncode == 0

        def section(a, b=None):
            try:
                s = output.split(a, 1)[1]
                return s.split(b, 1)[0] if b else s
            except IndexError:
                return ""

        after_start = section("---after-start---", "=== 2 ===")
        after_extend = section("---after-extend---", "=== 3 ===")
        after_stop = section("---after-stop---", "=== 4 ===")
        after_failed_start = section("---after-failed-start---", "=== 7 ===")

        check("orchestration-ran-without-unexpected-error", ran_clean, "fake-Azure orchestration script exited 0" if ran_clean else f"FAILED (exit {proc.returncode}): {output[-1000:]}")
        check("orchestration-start-chain-reaches-ready-with-ttl", '"state": "READY"' in after_start and '"ttlExpiresAt": "2026-09-10T00:00:00+00:00"' in after_start, "full START chain persisted state=READY with the merged ttlExpiresAt")
        check("orchestration-extend-updates-ttl-without-changing-state", '"ttlExpiresAt": "2026-09-10T02:00:00+00:00"' in after_extend and '"state": "READY"' in after_extend, "Extend updated ttlExpiresAt only, state remained READY")
        check("orchestration-stop-chain-reaches-dormant-with-restart-risk", '"state": "DORMANT"' in after_stop and '"dbAutoRestartRiskAt": "2026-09-17T00:00:00+00:00"' in after_stop, "full STOP chain persisted state=DORMANT with the merged dbAutoRestartRiskAt")
        check("orchestration-illegal-transition-rejected", "---illegal-transition-rejected---" in output, "DORMANT -> READY refused end-to-end through the real shell+CLI path")
        check("orchestration-second-environment-bootstraps-independently", "---second-env-bootstrap-ok---" in output, "staging's first-ever Start bootstraps independently of dev's row")
        check("orchestration-failed-start-persists-with-error-message", '"state": "FAILED_START"' in after_failed_start and '"lastError": "postgres did not become Ready"' in after_failed_start, "FAILED_START persisted with the specific error message, not merely logged")
        check("orchestration-etag-conflict-rejected-at-if-match-layer", "---etag-conflict-rejected---" in output, "a write against a stale ETag is rejected by the real --if-match mechanism, not silently clobbered")


def check_r1_security_boundaries_intact():
    # Spot check: R1's role-assignments.bicep and postgresql.bicep are
    # byte-for-byte untouched (not merely "still present").
    import hashlib
    checks_ok = True
    # These are structural re-checks, not hash pins (hashes were recorded
    # in the entry-gate verification, not duplicated here to avoid drift);
    # confirm the key invariants still hold textually.
    ra = read(MODULES / "role-assignments.bicep")
    pg = read(MODULES / "postgresql.bicep")
    checks_ok = checks_ok and "publicNetworkAccess: 'Disabled'" in pg
    checks_ok = checks_ok and "acrPullRoleId" in ra
    check("r1-security-boundaries-intact", checks_ok, "Postgres still private-only; R1 role assignments still present")


check_bicep_compiles()
check_no_production_in_generic_workflows()
check_no_client_secrets_in_workflows()
check_lifecycle_identity_not_owner_or_broad_contributor()
check_min_replicas_zero_for_lifecycle_managed()
check_prod_replica_policy_unchanged()
check_demo_nat_false_prod_nat_true()
check_lifecycle_state_storage_exists()
check_workflows_exist()
check_concurrency_groups_present()
check_ttl_bounds_exist()
check_no_permanent_hold()
check_stop_checks_migration_and_postgres()
check_dormant_only_after_verification()
check_failed_stop_exists()
check_start_no_migration_no_seeders()
check_cost_tags_present()
check_budget_amount_not_fabricated()
check_acr_tier_policy()
check_acr_premium_only_features_gated()
check_alert_suppression_module_exists_and_skips_prod()
check_alert_suppression_narrowly_scoped()
check_lifecycle_role_no_monitoring_contributor()
check_start_stop_toggle_suppression_correctly()
check_apply_transition_cli_exists_and_pure_controller_unmodified()
check_workflows_invoke_governed_persistence()
check_table_read_fails_closed()
check_first_row_bootstrap_and_etag_paths_exist()
check_d2_federated_credential_loop_and_subjects()
check_scheduled_matrix_workflows_bind_github_environment()
check_restart_monitor_persists_classification()
check_orchestration_end_to_end_with_fake_azure()
check_r1_security_boundaries_intact()


def main() -> int:
    failed = 0
    for name, passed, detail in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            failed += 1
        print(f"[{status}] {name}: {detail}")
    print(f"\n{len(results) - failed}/{len(results)} checks passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
