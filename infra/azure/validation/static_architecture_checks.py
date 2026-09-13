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
REPO_ROOT = INFRA.parents[1]

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


def _backend_settings_fields() -> set[str]:
    src = read(REPO_ROOT / "backend" / "app" / "core" / "config.py")
    return {
        m.group(1)
        for m in re.finditer(r"^    ([a-z][a-z0-9_]*):\s", src, re.MULTILINE)
        if m.group(1) != "model_config"
    }


# ---- 17. Secret/env contract (CDD-070): every Key-Vault-backed secret
# reference in resources.bicep must carry an explicit `envName`, distinct
# from its Key Vault/Container-Apps secret `name`, and that envName must
# correspond to a real field on backend/app/core/config.py's Settings class
# under its real env_prefix ("CTEC_"). This is a structural, cross-file
# check -- not a fixed-string grep -- so it fails on a REGRESSION even if
# the specific secret/env names involved change in the future.
def check_secret_env_contract_explicit_and_valid() -> None:
    resources_src = read(INFRA / "resources.bicep")
    # Each secret-ref entry is authored as one line, e.g.
    # { name: 'x', envName: 'CTEC_X', keyVaultUrl: '${...}secrets/x' } --
    # matched per-line (not brace-balanced) because the keyVaultUrl value
    # itself legitimately contains Bicep string-interpolation braces.
    entries = [line for line in resources_src.splitlines() if "keyVaultUrl:" in line]
    backend_fields = _backend_settings_fields()
    problems: list[str] = []
    if not entries:
        problems.append("no keyVaultUrl-bearing secret-ref entries found")
    for entry in entries:
        name_m = re.search(r"name:\s*'([^']+)'", entry)
        env_m = re.search(r"envName:\s*'([^']+)'", entry)
        if not env_m:
            problems.append(f"entry missing envName (CDD-070 regression): {entry.strip()}")
            continue
        env_name = env_m.group(1)
        if name_m and env_name == name_m.group(1):
            problems.append(f"envName equals raw secret name, original defect reintroduced: {env_name}")
            continue
        if not re.fullmatch(r"CTEC_[A-Z0-9_]+", env_name):
            problems.append(f"envName not CTEC_-prefixed uppercase: {env_name}")
            continue
        field = env_name[len("CTEC_"):].lower()
        if field not in backend_fields:
            problems.append(f"envName {env_name} has no matching Settings field ({field}) in backend/app/core/config.py")
    check(
        "secret-env-contract-explicit-and-valid",
        not problems,
        "; ".join(problems) or f"{len(entries)} secret-ref entries all carry an explicit envName, distinct from name, matching a real backend Settings field",
    )


# ---- 18. Health probe contract (CDD-070): container-app.bicep must not
# hardcode any consumer's health path -- healthProbePath must be an
# explicit, required parameter, and every module call site (backendApp,
# frontendApp) in resources.bicep must supply it explicitly. This fails if
# a shared module again silently assumes one workload's route is correct
# for every consumer, regardless of what the actual path strings are.
def check_health_probe_path_parameterized() -> None:
    module_src = read(MODULES / "container-app.bicep")
    no_hardcoded_path = not re.search(r"path:\s*'/[^']*'", module_src)
    has_required_param = bool(re.search(r"^param healthProbePath string\s*$", module_src, re.MULTILINE))
    resources_src = read(INFRA / "resources.bicep")
    backend_block_m = re.search(r"module backendApp[\s\S]*?\n\}\n", resources_src)
    frontend_block_m = re.search(r"module frontendApp[\s\S]*?\n\}\n", resources_src)
    backend_ok = bool(backend_block_m) and "healthProbePath:" in backend_block_m.group(0)
    frontend_ok = bool(frontend_block_m) and "healthProbePath:" in frontend_block_m.group(0)
    ok = no_hardcoded_path and has_required_param and backend_ok and frontend_ok
    problems = []
    if not no_hardcoded_path:
        problems.append("container-app.bicep still hardcodes a literal path in a probe")
    if not has_required_param:
        problems.append("container-app.bicep missing required healthProbePath parameter")
    if not backend_ok:
        problems.append("backendApp call site does not explicitly pass healthProbePath")
    if not frontend_ok:
        problems.append("frontendApp call site does not explicitly pass healthProbePath")
    check(
        "health-probe-path-explicit-per-consumer",
        ok,
        "; ".join(problems) or "container-app.bicep has no hardcoded probe path; backendApp and frontendApp each explicitly declare healthProbePath",
    )


# ---- 19. Azure PostgreSQL DSN producer contract (CDD-071): the deployment
# guide's own example `az keyvault secret set` commands for
# `ctec-database-url`/`ctec-migration-database-url` must instruct operators
# to use the canonical, driver-qualified `postgresql+psycopg://` scheme,
# never a bare `postgresql://` -- a real Azure migration execution proved
# SQLAlchemy resolves the bare scheme to the legacy, not-installed
# `psycopg2` DBAPI. This is a documentation-content check (the "producer"
# here is text, not executable logic, per CDD-071 SS25) -- it prevents a
# future edit of the guide from reintroducing the exact defect this
# artifact corrects.
def check_azure_dsn_guide_uses_canonical_driver_scheme() -> None:
    guide = read(REPO_ROOT / "docs" / "deployment" / "azure" / "NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md")
    problems: list[str] = []
    found_any = False
    for line in guide.splitlines():
        if "keyvault secret set" not in line:
            continue
        if "--name ctec-database-url" not in line and "--name ctec-migration-database-url" not in line:
            continue
        found_any = True
        if "postgresql+psycopg://" not in line:
            problems.append(f"guide command missing canonical scheme: {line.strip()}")
        if re.search(r"postgresql://(?!\S*\+psycopg)", line) and "postgresql+psycopg://" not in line:
            problems.append(f"guide command uses bare scheme: {line.strip()}")
    if not found_any:
        problems.append("no ctec-database-url/ctec-migration-database-url keyvault secret set example found in the guide")
    check(
        "azure-dsn-guide-uses-canonical-driver-scheme",
        not problems,
        "; ".join(problems) or "deployment guide's ctec-database-url/ctec-migration-database-url examples both use postgresql+psycopg://",
    )


# ---- 20. Azure frontend build guide includes the resource-qualified scope
# build arg (CDD-074): the deployment guide's frontend `docker build`
# example must pass NEXT_PUBLIC_OIDC_API_RESOURCE_URI set to the real,
# governed backend Application ID URI -- omitting it reproduces the real
# AADSTS650053 defect this artifact closed (bare custom scopes resolve
# against Microsoft Graph instead of the Noetva backend resource).
def check_azure_frontend_guide_includes_resource_scope_arg() -> None:
    guide = read(REPO_ROOT / "docs" / "deployment" / "azure" / "NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md")
    # The frontend build example spans multiple backslash-continued lines;
    # match the whole block between "docker build \" and the final
    # "./frontend" invocation target.
    block_m = re.search(r"docker build \\[\s\S]*?\./frontend\n", guide)
    block = block_m.group(0) if block_m else ""
    problems: list[str] = []
    if not block_m:
        problems.append("no frontend docker build example found in the guide")
    elif "NEXT_PUBLIC_OIDC_API_RESOURCE_URI" not in block:
        problems.append("frontend docker build example is missing --build-arg NEXT_PUBLIC_OIDC_API_RESOURCE_URI")
    elif "api://3a880f13-985d-4a71-be05-20f97b9bcfa3" not in block:
        problems.append("frontend docker build example's NEXT_PUBLIC_OIDC_API_RESOURCE_URI is not set to the real governed backend Application ID URI")
    check(
        "azure-frontend-guide-includes-resource-scope-arg",
        not problems,
        "; ".join(problems) or "frontend build example passes NEXT_PUBLIC_OIDC_API_RESOURCE_URI=api://3a880f13-985d-4a71-be05-20f97b9bcfa3",
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
    check_secret_env_contract_explicit_and_valid()
    check_health_probe_path_parameterized()
    check_azure_dsn_guide_uses_canonical_driver_scheme()
    check_azure_frontend_guide_includes_resource_scope_arg()

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
