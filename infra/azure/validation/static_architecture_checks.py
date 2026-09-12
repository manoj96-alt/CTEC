"""Fail-closed static validation of the Noetva Azure infrastructure code
(Noetva I0-R1 Section 45). Every check reads the actual committed files --
none of them trust design intent. A check that cannot be positively
confirmed is reported FAIL, never silently skipped.

Usage: python static_architecture_checks.py
Exit code 0 only if every check passes.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1]
MODULES = INFRA / "modules"
ENVIRONMENTS = INFRA / "environments"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str) -> None:
    results.append((name, condition, detail))


def read(path: Path) -> str:
    return path.read_text()


# ---- 1. Bicep compiles -------------------------------------------------
def check_bicep_compiles() -> None:
    out = INFRA / ".build" / "main.json"
    out.parent.mkdir(exist_ok=True)
    proc = subprocess.run(
        ["az", "bicep", "build", "--file", str(INFRA / "main.bicep"), "--outfile", str(out)],
        capture_output=True,
        text=True,
    )
    check("bicep-compiles", proc.returncode == 0, proc.stderr.strip()[-500:] or "compiled cleanly")


# ---- 2. No secret leakage in parameter files ---------------------------
def check_no_secret_leakage() -> None:
    suspicious_ok_placeholders = ("REPLACE_", "")
    leaked = []
    for pf in ENVIRONMENTS.rglob("main.parameters.json"):
        data = json.loads(read(pf))
        for key, entry in data.get("parameters", {}).items():
            if "password" in key.lower() or "secret" in key.lower():
                value = str(entry.get("value", ""))
                if not value.startswith("REPLACE_"):
                    leaked.append(f"{pf.relative_to(INFRA)}::{key}")
    check("no-secret-leakage-in-parameter-files", not leaked, "; ".join(leaked) or "all password/secret params are REPLACE_ placeholders")


# ---- 3. `latest` never authorized as production image reference -------
def check_no_latest_tag() -> None:
    hits = []
    for pf in ENVIRONMENTS.rglob("main.parameters.json"):
        data = json.loads(read(pf))
        for key in ("backendImageReference", "frontendImageReference"):
            value = str(data.get("parameters", {}).get(key, {}).get("value", ""))
            if value.endswith(":latest") or value == "latest":
                hits.append(f"{pf.relative_to(INFRA)}::{key}={value}")
    check("no-latest-tag-authorized", not hits, "; ".join(hits) or "no parameter file authorizes `latest`")


# ---- 4. Public DB exposure ---------------------------------------------
def check_postgres_not_public() -> None:
    src = read(MODULES / "postgresql.bicep")
    check(
        "postgres-public-network-access-disabled",
        "publicNetworkAccess: 'Disabled'" in src,
        "postgresql.bicep sets publicNetworkAccess: 'Disabled'" if "publicNetworkAccess: 'Disabled'" in src else "NOT FOUND",
    )


# ---- 5. Private connectivity present -----------------------------------
def check_postgres_private_connectivity() -> None:
    src = read(MODULES / "postgresql.bicep")
    ok = "delegatedSubnetResourceId" in src and "privateDnsZoneArmResourceId" in src
    check("postgres-private-connectivity-configured", ok, "delegated subnet + private DNS zone both referenced" if ok else "MISSING")


# ---- 6. Key Vault references wired to the backend/migration apps ------
def check_keyvault_references_wired() -> None:
    src = read(INFRA / "resources.bicep")
    ok = "backendSecretRefs" in src and "keyVaultSecretRefs: backendSecretRefs" in src and "keyVaultUrl:" in src
    check("keyvault-secret-refs-wired-to-backend", ok, "backend/migration container apps reference Key Vault secrets" if ok else "MISSING")


# ---- 7. No Owner role assigned to any runtime identity -----------------
def check_no_owner_role() -> None:
    src = read(MODULES / "role-assignments.bicep") + read(INFRA / "resources.bicep")
    owner_role_id = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"  # built-in Owner role definition ID
    check("no-owner-role-assigned", owner_role_id not in src, "Owner role ID not referenced anywhere" if owner_role_id not in src else "OWNER ROLE FOUND")


# ---- 8. Migration Job exists and is wired -------------------------------
def check_migration_job_exists() -> None:
    job_module = MODULES / "container-apps-job-migration.bicep"
    src = read(job_module) if job_module.exists() else ""
    resources_src = read(INFRA / "resources.bicep")
    ok = "Microsoft.App/jobs@" in src and "migrationJob" in resources_src
    check("migration-job-exists-and-wired", ok, "container-apps-job-migration.bicep declares Microsoft.App/jobs and resources.bicep wires it" if ok else "MISSING")


# ---- 9. Backend Container App bypasses docker-entrypoint.sh's migration path
def check_backend_migration_bypass() -> None:
    src = read(INFRA / "resources.bicep")
    m = re.search(r"module backendApp[\s\S]*?commandOverride:\s*\[([\s\S]*?)\]", src)
    ok = bool(m) and "uvicorn" in m.group(1) and "alembic" not in m.group(1)
    check(
        "backend-app-skips-migration-on-startup",
        ok,
        "backendApp commandOverride starts uvicorn directly, no alembic/entrypoint reference" if ok else "MISSING or references alembic",
    )


# ---- 10/11. Per-environment NAT/HA policy -------------------------------
def check_environment_policy() -> None:
    expectations = {
        "dev": {"enableNatGateway": False, "postgresHaMode": "Disabled"},
        "staging": {"enableNatGateway": True, "postgresHaMode": "Disabled"},
        "prod": {"enableNatGateway": True, "postgresHaMode": "ZoneRedundant"},
        "demo": {"enableNatGateway": False, "postgresHaMode": "Disabled"},
    }
    problems = []
    for env, expected in expectations.items():
        pf = ENVIRONMENTS / env / "main.parameters.json"
        if not pf.exists():
            problems.append(f"{env}: parameter file missing")
            continue
        data = json.loads(read(pf))["parameters"]
        for key, expected_value in expected.items():
            actual = data.get(key, {}).get("value")
            if actual != expected_value:
                problems.append(f"{env}.{key}: expected {expected_value!r}, got {actual!r}")
    check("per-environment-nat-ha-policy-correct", not problems, "; ".join(problems) or "dev/demo=no NAT+no HA, staging=NAT+no HA, prod=NAT+ZoneRedundant")


# ---- 12. Demo/prod isolation: separate resource group per environment --
def check_environment_isolation() -> None:
    src = read(INFRA / "main.bicep")
    ok = "'rg-noetva-${environmentName}'" in src
    check("isolated-resource-group-per-environment", ok, "main.bicep names the RG from environmentName" if ok else "MISSING")


# ---- 13. Diagnostic settings present on Key Vault / ACR / CAE ----------
def check_diagnostics_wired() -> None:
    missing = []
    for mod in ("keyvault.bicep", "acr.bicep", "container-apps-environment.bicep"):
        src = read(MODULES / mod)
        if "Microsoft.Insights/diagnosticSettings@" not in src:
            missing.append(mod)
    check("diagnostic-settings-present", not missing, "; ".join(missing) or "keyvault/acr/container-apps-environment all wire diagnosticSettings")


# ---- 14. Backup retention >= 7 days everywhere -------------------------
def check_backup_retention() -> None:
    problems = []
    for pf in ENVIRONMENTS.rglob("main.parameters.json"):
        data = json.loads(read(pf))["parameters"]
        days = data.get("postgresBackupRetentionDays", {}).get("value")
        if not isinstance(days, int) or days < 7:
            problems.append(f"{pf.relative_to(INFRA)}: {days!r}")
    check("backup-retention-at-least-7-days", not problems, "; ".join(problems) or "every environment >= 7 days")


# ---- 15. Environment separation: distinct namePrefix per environment ---
def check_distinct_name_prefixes() -> None:
    prefixes = {}
    for pf in ENVIRONMENTS.rglob("main.parameters.json"):
        data = json.loads(read(pf))["parameters"]
        prefixes[str(pf.relative_to(INFRA))] = data.get("namePrefix", {}).get("value")
    ok = len(set(prefixes.values())) == len(prefixes)
    check("distinct-name-prefix-per-environment", ok, str(prefixes))


# ---- 16. Migration-Job metric alert uses the real Microsoft.App/jobs
# metric surface (CDD-069), never the invalid guessed pair it replaces.
#
# NOTE (disclosed, not hidden, matching connector_security_check.py's own
# local-vs-real-Azure split): this check ONLY proves the literal string
# pair committed here is the CDD-069-governed one. It CANNOT prove Azure
# itself still accepts `Executions`/`state` -- that is exactly the class
# of defect that shipped originally (Bicep's compiler does not validate
# metric-name strings, only ARM does, at deployment time). Real-Azure
# re-verification (`az monitor metrics list-definitions` against the real
# deployed migration Job, then a real deployment succeeding with the
# alert created) remains mandatory before any PASS -- see CDD-069 SS13/SS14.
def check_migration_job_alert_uses_real_metric() -> None:
    src = read(MODULES / "monitoring-alerts-only.bicep")
    m = re.search(r"resource migrationJobFailureAlert[\s\S]*?^\}", src, re.MULTILINE)
    block = m.group(0) if m else ""
    no_invalid = "JobExecutionCount" not in block and "executionStatus" not in block
    has_valid = "metricName: 'Executions'" in block and "name: 'state'" in block and "'Failed'" in block
    ok = bool(m) and no_invalid and has_valid
    check(
        "migration-job-alert-uses-real-azure-metric",
        ok,
        "migrationJobFailureAlert uses the CDD-069-governed real metric (Executions/state=Failed), not the invalid JobExecutionCount/executionStatus pair"
        if ok
        else "MISSING or still references the invalid JobExecutionCount/executionStatus pair -- this is a literal-string check only, real-Azure re-verification is separately mandatory (CDD-069 SS13)",
    )


def main() -> int:
    check_bicep_compiles()
    check_no_secret_leakage()
    check_no_latest_tag()
    check_postgres_not_public()
    check_postgres_private_connectivity()
    check_keyvault_references_wired()
    check_no_owner_role()
    check_migration_job_exists()
    check_backend_migration_bypass()
    check_environment_policy()
    check_environment_isolation()
    check_diagnostics_wired()
    check_backup_retention()
    check_distinct_name_prefixes()
    check_migration_job_alert_uses_real_metric()

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
