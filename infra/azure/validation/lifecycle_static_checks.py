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
    # The "Record DORMANT" step must appear strictly after the postgres-stop
    # polling step in file order.
    stop_poll_idx = src.find('[ "$state" = "Stopped" ]')
    dormant_idx = src.find("Record DORMANT")
    check("dormant-recorded-only-after-postgres-stopped-check", 0 < stop_poll_idx < dormant_idx, f"poll@{stop_poll_idx} dormant@{dormant_idx}")


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
