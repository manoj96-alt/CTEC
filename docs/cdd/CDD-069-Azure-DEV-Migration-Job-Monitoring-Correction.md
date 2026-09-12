# CDD-069 — Azure DEV Migration Job Monitoring Correction

**Status:** FROZEN
**Originating phase:** AZURE-DEV-MIGRATION-JOB-MONITORING-R7 (DRG only in this artifact; implementation and real-Azure VM remain future phases)
**Amends:** nothing frozen in place. Complements CDD-067 and CDD-068 (both still open, PRs #213/#214/#215/#216) by correcting one Azure Monitor defect discovered during the real AZURE-DEV-APPLICATION-TIER-R7-EXECUTION deployment. Neither CDD-067 nor CDD-068 is reopened, edited, or superseded.

**Scope:** the exact metric name/dimension used by `noetva-dev-eus2-alert-migration-job-failed` in `infra/azure/modules/monitoring-alerts-only.bicep`, and the residual-risk disclosure in `infra/azure/README.md` and the reference table in the deployment guide that describe it. No other alert, module, or resource is in scope.

---

## 1. Authoritative baseline at freeze

Main SHA: `09acfeb77a258ff8a83a48a8fc4105279456f50a` — independently re-verified against `origin/main` and GitHub `main` (this artifact's own branch is cut directly from this commit, matching the CDD-067/CDD-068 governance-branch precedent).

Open PR stack, every head re-derived live from GitHub (never trusted from a prior report):

| PR | Branch | Head SHA | State |
|---|---|---|---|
| #213 | `azure/bootstrap-r5-g` | `14402751a596c2845e5c65c4c1db6d33c0466ab7` | OPEN, not merged |
| #214 | `azure/bootstrap-r5-i` | `6e2185b1dddc69364ad4520063fb3416296eafb4` | OPEN, not merged |
| #215 | `azure/private-db-bootstrap-r6-g` | `3263bca340df9af9582fa267f53455f428ca65da` | OPEN, not merged |
| #216 | `azure/private-db-bootstrap-r6-i` | `0e041403dcea8c42eec01175b6377bded41bbb59` | OPEN, not merged |

CDD-067 SHA-256 (re-hashed from PR #213's exact commit): `5b2b19e86122f8db896012d97e5f08214773a7699da31b25c08c8833634e1e23` — matches frozen value. CDD-068 SHA-256 (re-hashed from PR #215's exact commit): `5f98c59ee4992ba80fad7e1dee6f20d27f1b27931f4adbefafcae597a5817b3c` — matches frozen value.

Cumulative implementation candidate: `merge-base(azure/bootstrap-r5-i, origin/main) == origin/main` (R5 implementation branches directly off this exact main commit, main has not advanced since), and R5-I is a direct ancestor of R6-I. So commit `0e041403dcea8c42eec01175b6377bded41bbb59` (R6-I) already **is** main + R5 implementation + R6 implementation in one linear chain — the same candidate used for the real AZURE-DEV-APPLICATION-TIER-R7-EXECUTION deployment.

## 2. Real failure evidence

The real application-tier deployment (`az deployment sub create`, `deployApplicationTier=true`, real digest-pinned `linux/amd64` backend/frontend images) converged the backend Container App, frontend Container App, and the normal migration Job (`noetva-dev-eus2-migrate`) successfully. The top-level ARM deployment nonetheless reported `Failed`, because the nested `monitoring-alerts-only` deployment failed on exactly one resource:

```
Microsoft.Insights/metricAlerts/noetva-dev-eus2-alert-migration-job-failed
BadRequest: Couldn't find a metric named JobExecutionCount.
```

Source location: `infra/azure/modules/monitoring-alerts-only.bicep:133` (`metricName: 'JobExecutionCount'`, dimension `name: 'executionStatus'`). The other two metric alerts in the same module (`noetva-dev-eus2-alert-pg-storage` using `storage_percent`, `noetva-dev-eus2-alert-pg-connections` using `active_connections`, both against `Microsoft.DBforPostgreSQL/flexibleServers`) deployed successfully in this same real attempt — this is now **real-Azure empirical proof** that those two PostgreSQL metric names are correct, closing that half of the residual risk the module's own header comment had flagged. Only the `Microsoft.App/jobs` metric name/dimension pair was wrong.

The module's own pre-existing header comment (unmodified, written before any real deployment existed to check against) had explicitly disclosed this exact possibility: *"were NOT independently re-verified against `az monitor metrics list-definitions` against a real deployed resource in this phase (no Azure resource exists yet to query). This is flagged as a residual risk... to confirm at first real deployment."* This is precisely that confirmation, and it found the flagged risk was real for the Jobs metric.

No ad-hoc repair was applied when this was discovered; the deployment phase stopped and reported the exact defect, per its own governing instructions.

## 3. Original monitoring intent

Re-derived from source (`monitoring-alerts-only.bicep`'s own resource name, dimension filter, and severity) and the deployment guide's Part 33/reference-table entry: **alert an on-call operator when a real execution of the normal database migration Job (`noetva-dev-eus2-migrate`) reaches a failed terminal state**, at severity 0 (highest), evaluated on a 5-minute window, routed through the existing `noetva-dev-eus2-ag-oncall` action group. The intent was never "alert on Job dormancy" or "alert on absence of executions" — the manually-triggered Job is expected to sit idle almost all the time; only a genuine failed execution should page anyone. This artifact preserves that intent exactly; it corrects only the technical mechanism, which was invalid and could never have fired or resolved correctly as written (Azure rejects the metric name outright at alert-creation time, so the original alert could never even be created, let alone evaluate).

## 4. Actual `Microsoft.App/jobs` metric surface (real-Azure evidence)

Queried directly against the real deployed resource (`az monitor metrics list-definitions --resource <noetva-dev-eus2-migrate resource ID>`, read-only, no mutation). Full result, eight metrics, all under namespace `Microsoft.App/jobs`:

| Metric (canonical name) | Display name | Unit | Supported aggregations |
|---|---|---|---|
| `Executions` | Job Executions | Count | Average, Total, Maximum, Minimum |
| `UsageNanoCores` | CPU Usage | NanoCores | Average |
| `UsageBytes` | Usage Bytes | Bytes | Average |
| `RequestedBytes` | Requested Bytes | Bytes | Average |
| `RequestedCores` | Requested Cores | Cores | Average |
| `RestartCount` | Total Job Execution Restart Count | Count | Maximum |
| `TxBytes` | Network Out Bytes | Bytes | Total |
| `RxBytes` | Network In Bytes | Bytes | Total |

No metric named `JobExecutionCount` exists. `Executions` is the only metric describing execution counts.

`Executions`' full definition (captured via the same query) declares exactly three dimensions: `state`, `jobName`, `executionName` (`isDimensionRequired: false`), time grains from `PT1M` through `P1D`, 93-day retention.

**Dimension-name validation (real-Azure, adversarial control test):** querying `Executions` filtered on the wrong dimension name (`executionStatus`, the original Bicep's guess) was rejected outright: `BadRequest: Metric: Executions does not support requested dimension combination: executionstatus, supported ones are: state,jobName,executionName`. Querying with the correct dimension name `state` (values `Failed` and, as a control, `Succeeded`) was accepted (`errorCode: Success`) — empty time series only because the Job has never been triggered (governed: it must remain untriggered during this DRG).

**Dimension-value authority (independent, non-Azure-CLI source):** Microsoft's own published ARM REST API reference for `JobExecution` (`properties.status`, type `JobExecutionRunningState`) enumerates the complete, authoritative set of values: `Running | Processing | Stopped | Degraded | Failed | Unknown | Succeeded`. `Failed` and `Succeeded` are both real, documented terminal states. This independently corroborates (not merely assumes) that filtering the `state` dimension to `Failed` expresses exactly the intended condition.

## 5. Answer to the primary discovery question

`Microsoft.App/jobs` **does** expose a suitable platform metric capable of distinguishing failed migration Job executions: `Executions`, filtered on dimension `state = Failed`, `Total` aggregation, threshold `> 0`. No renamed-metric guess was assumed — the real metric surface was queried first (§4), and only after confirming `Executions`/`state` were real and dimension-name-validated was this option selected. No metric invention was required.

## 6. Options evaluated

- **Option A — corrected platform metric alert (`Executions`, dimension `state = Failed`, same `Microsoft.Insights/metricAlerts` resource type already used for the two working PostgreSQL alerts):** **SELECTED.** Real, dimension-name-validated (§4), zero new resource type, zero new cost (same alert-resource count and type as already budgeted), zero new permissions, zero Log Analytics dependency, uses only the platform metric pipeline every Container Apps Job already emits to with no diagnostic-setting export required.
- **Option B — Log Analytics / scheduled-query alert over Container Apps Job execution logs:** rejected as unnecessary. Would require Container Apps system-logs diagnostic export to be enabled and ingested (an additional, ongoing Log Analytics ingestion cost, however small) and a scheduled query rule (its own small recurring cost, typically evaluated on a schedule rather than the platform-metric pipeline's near-real-time evaluation) to detect a condition the platform metric already expresses natively and for free. Would only be justified if no valid platform metric existed (§4 proves one does).
- **Option C — Azure Resource Graph / Activity Log based detection:** rejected. The Activity Log records the *control-plane* operation of triggering/managing the Job, not the *data-plane* outcome (whether the migration inside the container actually succeeded or failed) — it cannot truthfully distinguish a Job execution that started fine but whose `alembic upgrade head` failed inside the container, which is exactly the condition of concern.
- **Option D — application-level custom metric emitted by the migration Job:** rejected as unnecessary and disproportionate. Would require modifying the migration Job's own script/image to emit a custom metric via the Azure Monitor custom-metrics API, adding source surface, a new permission (`Monitoring Metrics Publisher` or equivalent on the identity), and operational complexity, to detect a condition the existing platform metric (§4) already expresses natively.
- **Option E — another Azure-native mechanism:** none identified as more direct than Option A once §4 confirmed a truthful platform metric exists.

## 7. Selected monitoring mechanism

Correct exactly two identifiers in the existing `migrationJobFailureAlert` resource in `infra/azure/modules/monitoring-alerts-only.bicep`, changing nothing else about its shape (same resource type, same scope, same action group, same severity):

- `metricName: 'JobExecutionCount'` → `metricName: 'Executions'`
- dimension `name: 'executionStatus'` → `name: 'state'`
- dimension `values: ['Failed']` — unchanged (already correct, independently confirmed against the real `JobExecutionRunningState` enum, §4)
- `timeAggregation: 'Total'`, `operator: 'GreaterThan'`, `threshold: 0` — unchanged (correct semantics for "at least one failed execution in this window," §8)

The module's own header comment (the one that had disclosed this as a residual risk) is updated to record that the PostgreSQL metrics are now real-Azure-verified (by the real deployment's own success) and that the Jobs metric has been corrected and re-verified (§4), removing the "not yet re-verified" disclosure for both, since both are now closed.

## 8. Exact alert semantics (frozen)

- **Evaluation period:** unchanged, `evaluationFrequency: PT5M`, `windowSize: PT5M` (5-minute window, evaluated every 5 minutes).
- **Threshold meaning:** the `Executions` metric, filtered to `state = Failed`, summed (`Total`) over the window, `> 0` — i.e., at least one execution reached the `Failed` terminal state inside this window. Because `replicaRetryLimit: 0` on this Job (confirmed in `container-apps-job-migration.bicep`), each manual trigger produces exactly one execution and one terminal state — no internal-retry double-counting is possible.
- **Absence of executions is never alertable.** A dormant Job (the expected, default state — manually triggered, no schedule) produces zero data points for `state = Failed` in every window; `0 > 0` is false; the alert never fires. This is a structural property of `GreaterThan`-over-`Total` semantics, not a separate suppression mechanism — dormancy and "no failures" are indistinguishable from each other and both correctly produce silence.
- **Distinguishing success from failure:** a `Succeeded` execution contributes to the `state = Succeeded` series, never to the `state = Failed` series the alert filters on — the two are disjoint dimension values on the same metric (confirmed real, §4), so a successful migration run never contributes to this alert's condition.
- **Retry/duplicate-alert behavior:** none possible from this Job's own retries (`replicaRetryLimit: 0`, §above). Azure Metric Alerts are themselves stateful (fire once when the threshold is breached, auto-resolve once a subsequent window is not breached) — a single failed execution produces one qualifying window and one notification, not a repeating page, exactly matching the alert's pre-existing (unchanged) evaluation cadence.
- **Scope boundary, disclosed:** this alert fires only on `state = Failed`. The enum also includes `Degraded`, `Stopped`, and `Unknown` (§4) — states this alert deliberately does not treat as equivalent to a failed migration, since they are not the same condition and conflating them was never the governed intent (§3). This is an explicit, disclosed scope boundary, not an oversight.

## 9. Dormancy and lifecycle-suppression compatibility

Independently re-inspected `infra/azure/modules/lifecycle-alert-suppression.bicep` (unmodified by this correction, out of scope). Its `Suppression`-type alert-processing rule filters `TargetResourceType Contains MICROSOFT.APP/CONTAINERAPPS` — a Container **Apps** (not Container Apps **Jobs**) resource-type filter, by the module's own explicit, pre-existing design intent ("it structurally cannot match... the migration-Job-failure alert"). `Microsoft.App/jobs` and `Microsoft.App/containerApps` are distinct ARM resource types; the suppression rule never has and never will match this alert, regardless of which metric name it uses. This correction changes nothing about that relationship — the migration-Job-failure alert was never suppressed by the lifecycle mechanism before this fix and remains not suppressed by it after. No incompatibility exists to resolve.

## 10. Cost

Zero incremental cost. The corrected mechanism is the exact same Azure resource type (`Microsoft.Insights/metricAlerts@2018-03-01`), same count (one alert, already budgeted in CDD-067/068's cost accounting), reading a platform metric every Container Apps Job already emits natively with no diagnostic-setting export, no Log Analytics ingestion, and no new resource of any kind. This is strictly cheaper than every rejected alternative in §6 that involves Log Analytics (Option B) or a custom-metrics publishing path (Option D), both of which would introduce a small but real recurring cost this correction avoids entirely.

## 11. Security

The correction requires: no database credential, no Key Vault secret value, no PostgreSQL public-network change, no new network ingress, no application ADMIN authority, and no broadened managed-identity authority. It reads a platform metric Azure already collects for every Container Apps Job; no identity, role assignment, or credential of any kind is created, read, or modified by this correction.

## 12. Exact implementation paths (ceiling)

| # | Path | Change |
|---|---|---|
| 1 | `infra/azure/modules/monitoring-alerts-only.bicep` | MODIFY — correct `metricName`/dimension `name` on `migrationJobFailureAlert`; update header comment to close the now-verified residual risk |
| 2 | `infra/azure/README.md` | MODIFY — update the "Known residual risks" entry to record real-Azure verification evidence for both the PostgreSQL metrics (verified by the real deployment's own success) and the corrected Jobs metric (verified by this DRG's direct query, §4) |
| 3 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` | MODIFY — correct the reference-table row (currently `JobExecutionCount (executionStatus=Failed)`) and add the mandatory real-Azure verification step (§13) to the application-tier deployment part of the runbook |
| 4 | `infra/azure/validation/static_architecture_checks.py` | MODIFY — add a literal-content check asserting `monitoring-alerts-only.bicep` no longer contains `JobExecutionCount`/`executionStatus` and does contain the corrected `Executions`/`state` pair, explicitly documented (in the check's own message/docstring, matching `connector_security_check.py`'s existing local-vs-real-Azure split pattern) as necessary but insufficient alone — a real-Azure check (§13) remains mandatory before any PASS |

```
CREATE = 0
MODIFY = 4
DELETE = 0
TOTAL  = 4
```

No other path is authorized. In particular: `infra/azure/modules/container-apps-job-migration.bicep`, `main.bicep`, `resources.bicep`, and the environment parameter files are **not** touched — this correction is confined to the monitoring module and its documentation/test surface.

## 13. Regression-test architecture (static + mandatory real-Azure component)

A literal-string static check alone is insufficient — it can only prove the *implementer's typing* matches an expected string, not that Azure actually accepts it (this exact failure mode is what shipped the original defect: Bicep's compiler performs no such validation, only ARM does, at deployment time). Two layers are required, and both must pass before this correction can close as governed-verified:

1. **Static (necessary, not sufficient):** extend `static_architecture_checks.py` with a check that greps `monitoring-alerts-only.bicep` for the corrected literal pair (`metricName: 'Executions'`, dimension `name: 'state'`) and asserts the old, proven-invalid pair (`JobExecutionCount`, `executionStatus`) is absent. This catches accidental regression/typos in future edits but cannot independently prove Azure truth.
2. **Real-Azure (mandatory, this is what actually proves correctness):** during the real-Azure VM phase that implements this correction, re-run exactly the read-only queries this DRG already performed and captured (§4) against the real deployed `noetva-dev-eus2-migrate` resource — `az monitor metrics list-definitions` confirming `Executions`/`state` are still the real surface, then the actual `az deployment sub create` for the corrected application tier succeeding with the alert resource created (no `BadRequest`), then `az resource show` on the created alert confirming its `criteria.allOf[0].metricName == 'Executions'` and `dimensions[0].name == 'state'` exactly as deployed (not merely as authored) — closing the gap between "the Bicep source says the right thing" and "Azure accepted and is evaluating the right thing."

## 14. Real-Azure VM requirements (for the future implementation/VM phase, not satisfied by this DRG)

Before this correction can be declared closed, the implementing phase must produce, as real evidence (not simulated/what-if-only):

- Top-level application-tier deployment (`deployApplicationTier=true`) reaches `provisioningState: Succeeded` with zero errors.
- The corrected `noetva-dev-eus2-alert-migration-job-failed` resource exists, scoped to `noetva-dev-eus2-migrate`, linked to the existing `noetva-dev-eus2-ag-oncall` action group.
- No `BadRequest`/invalid-metric error of any kind.
- Independent read-back (`az resource show` or equivalent) confirming the deployed alert's exact criteria match §7/§8.
- Confirmation that `lifecycle-alert-suppression`'s existing rule still does not match this alert (§9), i.e., no regression to the disclosed scope boundary.
- What-if run first, reviewed for zero unexpected delete/replace, exactly as every prior phase in this arc has required.

## 15. Migration-resume ordering (unchanged from the R7-execution STOP report)

The normal migration Job's first governed execution, and `noetva-dev-tenant`'s bootstrap, remain pending until **after** this monitoring correction is implemented and a clean (`Succeeded`, zero errors) application-tier deployment is achieved. This DRG does not trigger the migration Job and does not bootstrap the tenant — both are explicitly out of scope here and remain PENDING.

## 16. STOP conditions (all evaluated during this DRG; none triggered)

- The intended failed-migration condition **can** be truthfully observed (§4/§5) — not triggered.
- The selected mechanism does **not** alert on normal dormancy (§8) — not triggered.
- The selected mechanism requires **no** database/public-network weakening (§11) — not triggered.
- Cost is **zero incremental**, not materially inconsistent with the nonprod architecture (§10) — not triggered.
- Lifecycle suppression **is** preserved (unaffected either way, §9) — not triggered.
- The source correction **is** boundable (§12, four files, all MODIFY, zero new resource types) — not triggered.
- Real Azure evidence **supports** (does not contradict) the proposed mechanism (§4, direct query plus independent Microsoft REST API documentation, §4 final paragraph) — not triggered.

No STOP condition fired. This correction is safe to freeze and hand to an implementation phase.

---

**Freeze evidence index:** real Azure metric-definition query output and dimension-name control test (§4) were captured directly against the real deployed `noetva-dev-eus2-migrate` resource during this DRG; the `JobExecutionRunningState` enum (§4) was independently retrieved from Microsoft's published ARM REST API reference (`rest-resource-manager-containerapps`, `Job-Execution` operation, `2026-01-01`/`2026-07-01` monikers). No value in this artifact was assumed, guessed, or carried over unverified from the original (defective) Bicep source.
