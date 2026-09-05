# CDD-059 — Artifact Authorization I-R3 CI Migration-Table-Count Closure Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-047-Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md` (OQI-H1-CI — the direct,
structurally identical precedent: a new migration invalidates a stale hardcoded table-count literal in
`.github/workflows/ci.yml`'s `containers` job, discovered only after the capability's own implementation
and verification phases were otherwise complete, corrected via a standalone narrow amendment rather than
folded into an already-verified implementation commit); `CDD-048-Artifact-Authorization-OQI-H2-I-R1-
Governance-Reconciliation-and-Verification-Hardening-Amendment.md` §9 (OQI-H2 — the second occurrence of
this identical defect class, corrected as one line among a broader reconciliation, confirming this is a
recurring, understood pattern rather than a novel problem)
Classification: CI GOVERNANCE-ENUMERATION GAP (mechanical correction only; no architectural, security,
schema, migration, or application-behavior change of any kind)

## 1. Purpose

Authorizes the exact, narrowest possible correction of one stale table-count literal in
`.github/workflows/ci.yml`, discovered by `REAL-ENTERPRISE-INGESTION-VM-R2` after that phase had already
independently verified the complete Production Governed Enterprise REST Ingestion capability — including
the R1 SSRF-boundary and R2 DNS-rebinding/IP-pinning corrections — found it fully sound, and only then
discovered that the repository's own GitHub Actions `containers` job fails on the exact verified
candidate for a reason entirely outside every one of CDD-059's own governance documents (the original
Artifact Authorization, the I-R1 amendment, and the I-R2 amendment). This amendment closes that gap under
its own explicit, narrow authorization, exactly as `CDD-047-Artifact-Authorization-CI-Migration-Head-
Closure-Amendment.md` and `CDD-048`'s own §9 closed the identical defect class for OQI-H1 and OQI-H2.

## 2. Independent re-verification of starting state

Freshly re-verified in this phase, not assumed from VM-R2's report:

```
git fetch origin --prune                     -> no new remote state
git status --short                            -> ?? docs/product/ (pre-existing, untracked, unrelated)
git branch --show-current                     -> real-enterprise-ingestion/rest-connector
git rev-parse HEAD                             -> 1423d93adca37eccbd5bc6d094459ccca2b5dd50
git rev-parse origin/main                      -> 5d59eec14f7248e543b806c840d2199c3f66e131
GitHub main SHA (gh api .../branches/main)     -> 5d59eec14f7248e543b806c840d2199c3f66e131
GitHub branch SHA                              -> 1423d93adca37eccbd5bc6d094459ccca2b5dd50
```

`origin/main` == GitHub main == the authoritative main this entire capability was built against. The
candidate branch head is identical, locally and on GitHub, to the exact commit VM-R2 independently
verified and attempted to merge. Neither moved. No silent rebase, no history rewrite, no drift.

## 3. PR #193 independent re-verification

```
gh pr view 193 --json state,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus

state:            OPEN
baseRefName:      main
headRefName:      real-enterprise-ingestion/rest-connector
headRefOid:       1423d93adca37eccbd5bc6d094459ccca2b5dd50
mergeable:        MERGEABLE
mergeStateStatus: UNSTABLE
```

PR #193 remains open, unmerged, pointed at exactly the VM-R2-verified candidate. It was not force-merged,
closed, or silently altered between VM-R2 and this phase.

## 4. Governance hash chain — independently re-derived

```
CDD-059-Production-Governed-Enterprise-REST-Ingestion.md
    6a8be98707ddf13e5428c2b67b00328eefab1556decc40a7203b12ded5daa055  (unchanged)

CDD-059-Production-Governed-Enterprise-REST-Ingestion-Artifact-Authorization.md
    431300c64689e2eea6fde4e44121bda5b6af25f869a9fa60f3b7ebda8ceb6e37  (unchanged)

CDD-059-Artifact-Authorization-I-R1-SSRF-Test-Boundary-Correction-Amendment.md
    96d319a42df00e38a2b38a3c6f0231c07d35542a9dfc9709c175523e68c1e3c1  (unchanged)

CDD-059-Artifact-Authorization-I-R2-DNS-Rebinding-IP-Pinning-Correction-Amendment.md
    f2bd20dbb77dce9cdff60e7d75bd53d1288aa6b72181371fe6a88b4e368f8e12  (unchanged)
```

All four re-hashed fresh in this phase, byte-identical to every prior phase's own re-verification. No
governance hash drift. This is the sole new artifact this phase creates.

## 5. Independent reproduction of the actual GitHub Actions failure

Not accepted from VM-R2's characterization. Independently re-queried in this phase:

```
gh pr checks 193
  containers  fail  https://github.com/manoj96-alt/CTEC/actions/runs/33949621459/job/101261801990
  containers  fail  https://github.com/manoj96-alt/CTEC/actions/runs/33974313487/job/101328209701
  backend     pass  (both runs)
  frontend    pass  (both runs)

gh run list --branch real-enterprise-ingestion/rest-connector --limit 10
  33974313487  pull_request  1423d93...  failure   <- current PR check run
  33949621459  push          1423d93...  failure   <- push-triggered run, same commit
  33948049109  push          06849c8...  failure   <- I-R2 governance-freeze commit
  33946521750  push          f9ad603...  failure   <- I-R1 implementation commit
  33944768990  push          c4394ed...  failure   <- I-R1 governance-freeze commit
  33940955513  push          14cf0f2...  failure   <- Docker-fixture-binding fix commit
  33940652184  push          3c6e06e...  failure   <- ORIGINAL implementation commit
  33938422327  push          80224fb...  success   <- ORIGINAL governance-freeze commit (pre-migration)

gh run view 33974313487 --log-failed  (the exact current PR check run)
  table count: 126
  unexpected table count: 126 (expected 123)
  ##[error]Process completed with exit code 1.
```

**Independently confirmed causal chain**, from actual logs, not inferred from source alone:

```
migration 0045_oqi_connector_ingestion applies
  -> real PostgreSQL database legitimately contains 126 tables
  -> ci.yml's "Verify the fresh schema has exactly the expected table count" step
     computes count=126
  -> compares against hardcoded literal 123
  -> [ "126" -eq "123" ] is false
  -> exit 1
  -> containers job fails
  -> PR #193 mergeStateStatus = UNSTABLE
```

**Newly disclosed scope**: this is not a fluke or a transient failure. Every push to this branch from the
very first implementation commit (`3c6e06e`, which introduced migration 0045) through the current
candidate (`1423d93`) has failed this identical `containers` check for this identical reason. Only the
original governance-freeze-only commit (`80224fb`, which added no migration) succeeded. This means CI has
been red on this branch throughout the entire DR/G/I/VM/G-R1/I-R1/VM-R1/G-R2/I-R2/VM-R2 pipeline, and no
phase prior to VM-R2 inspected the repository's own GitHub Actions state — each relied on manual local
Docker/pytest verification instead. VM-R2 was the first phase to check `gh pr checks`, and correctly
stopped rather than merging into a red required check.

## 6. Independent verification that 126 is the correct current value

Not assumed from VM-R2's report. Freshly re-derived in this phase against a genuinely clean database:

```
docker exec vmr2-pg psql -U ctec -d postgres -c "CREATE DATABASE ci_r3_check;"

cd <candidate worktree>/backend
CTEC_DATABASE_URL=postgresql+psycopg://ctec:ctec@localhost:5443/ci_r3_check \
  alembic -c alembic.ini upgrade head
  ... (ran all 45 migrations in sequence, ending)
  Running upgrade 0044_oqi4_r1_current_tenancy -> 0045_oqi_connector_ingestion,
  Create Production Governed Enterprise REST Ingestion persistence
  (CDD-059 §12-§14, §40; Artifact Authorization row 7).

alembic -c alembic.ini heads
  0045_oqi_connector_ingestion (head)          <- single head, confirmed

SELECT count(*) FROM information_schema.tables
  WHERE table_schema='public' AND table_type='BASE TABLE'
  AND table_name != 'alembic_version';
  -> 126
```

Confirmed: single Alembic head `0045_oqi_connector_ingestion`; current schema genuinely contains 126
tables when migrated from an empty database with no prior state.

## 7. CI counting-semantics adjudication

The CI query is:

```sql
SELECT count(*) FROM information_schema.tables
WHERE table_schema='public' AND table_type='BASE TABLE' AND table_name != 'alembic_version'
```

Independently checked against the same freshly migrated database for anything this query could be
silently over/under-counting relative to the 126 figure:

```
views in table_schema='public'                                    -> 0
non-catalog, non-information_schema schemas present                -> 0
installed extensions                                                -> pgcrypto (public, functions only,
                                                                        no BASE TABLE), plpgsql (pg_catalog)
```

No views, no additional schemas, no extension-owned tables in `public`. The query's semantics
(public-schema base tables, excluding `alembic_version`) exactly match the methodology VM-R2 itself used
to establish 126, and match the semantics `CDD-047`'s own precedent used to establish 102 for OQI-H1. No
semantic mismatch. 126 is the correct value for this exact CI invariant.

## 8. Historical `123` values — explicitly NOT touched by this amendment

```
grep -rn "\b123\b" backend/app/tests/ .github/workflows/

backend/app/tests/test_oqi_ontology_impact_postgres.py:1930:  assert _table_count() == 123
backend/app/tests/test_oqi_business_impact.py:2004:            assert _table_count() == 123
.github/workflows/ci.yml:153:  [ "$count" -eq 123 ] || { ...; exit 1; }
```

Exactly three occurrences of the literal `123` in scope for this class of check, repository-wide. The two
test-file occurrences were already independently adjudicated during the original VM/G-R1 phases: each
asserts table count immediately after downgrading to a **named historical pre-0044/0045 revision**
boundary, which correctly remains 123 regardless of migration 0045's existence, and must NOT change. This
amendment authorizes correcting **only** the third occurrence — `.github/workflows/ci.yml:153`, which
asserts the count of the **fully, currently migrated** schema, the one value migration 0045 legitimately
changes. No repository-wide `123 -> 126` replacement is authorized or intended.

## 9. Precedent — CDD-047

Independently read in full. `CDD-047-Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md`
governed the structurally identical defect for OQI-H1: PR #182's `containers` job failed because
`.github/workflows/ci.yml` hardcoded both a stale migration-head literal (`0026_oqi6_reliance`) and a
stale table-count literal (`100`, correct value `102`). Its own §3 confirms CI configuration was
explicitly excluded from OQI-H1's original Artifact Authorization and therefore never in scope for any
in-capability sweep — the same structural gap CDD-059's own governance documents share (none of CDD-059's
Artifact Authorization, the I-R1 amendment, or the I-R2 amendment names `.github/workflows/ci.yml`
anywhere).

Its §5 correction design is the direct architectural precedent followed here:

- **Migration head**: resolved **dynamically** (`docker compose exec backend alembic -c alembic.ini
  heads`) rather than re-pinned to a new literal, since Alembic exposes its own current head
  programmatically with zero drift risk. **Independently confirmed already in place** in the current
  `.github/workflows/ci.yml` (lines 139-146): the head check already compares the database's
  `alembic_version` against a dynamically resolved `alembic ... heads` value, not a hardcoded revision
  string. This means CDD-059 already, correctly, requires no correction to the migration-head check —
  only the table-count check remains stale.
- **Table count**: pinned to the freshly verified correct literal, not derived dynamically, because
  Alembic has no equivalent zero-drift API for "total table count." CDD-047 §5 states this explicitly:
  "It will itself become stale the next time a migration is added, at which point this identical,
  disclosed correction class applies again" — precisely the recurrence now observed for CDD-059.

CDD-047 §6 also establishes the binding non-weakening requirement followed here: the corrected assertion
remains a hard failure (`exit 1`), no `continue-on-error`, no step skipped, the `containers` job remains
required.

## 10. Precedent — CDD-048 §9

Independently read. `CDD-048-Artifact-Authorization-OQI-H2-I-R1-Governance-Reconciliation-and-
Verification-Hardening-Amendment.md` §9 documents the **second** occurrence of this identical defect
class, for OQI-H2: a fresh `grep -rn` for the stale literal (`102`) found "exactly one remaining stale,
unauthorized-to-touch location: `.github/workflows/ci.yml` lines 148-153," explicitly noting the
migration-head check "immediately above it... already resolves dynamically" (confirming the pattern in
§9 above is itself precedented at the individual-amendment level, not only across separate documents) and
authorizing the identical one-line correction, `102 -> 109`, as one MODIFY item folded into that phase's
broader reconciliation rather than as a fully standalone document. This confirms the CI table-count
literal has now required this exact treatment on three separate occasions across this repository's
governance history (OQI-H1 via CDD-047, OQI-H2 via CDD-048 §9, and now CDD-059 via this amendment) — a
recurring, well-understood, low-severity class of gap, not a novel or concerning one.

## 11. Root-cause classification

```
Connector implementation defect:         NO
SSRF/DNS-rebinding regression:            NO
Tenant-isolation defect:                  NO
Evidence-integrity defect:                NO
Migration defect:                         NO  (0045 is correct; single head; 126 tables is the true count)
Production-runtime defect:                NO
CI governance-enumeration gap:            YES -- CDD-059's Artifact Authorization, the I-R1 amendment, and
                                           the I-R2 amendment all correctly scoped their own path
                                           authorizations to application/test source; none named
                                           `.github/workflows/ci.yml`, so migration 0045's legitimate
                                           123->126 table-count change was never propagated to CI's own
                                           hardcoded current-schema expectation. Structurally identical to
                                           the CDD-047 (OQI-H1) and CDD-048 §9 (OQI-H2) occurrences.
```

## 12. P0/P1/P2/P3 before this amendment

```
P0 = 0
P1 = 0
P2 = 1  -- .github/workflows/ci.yml:153's stale table-count literal (123), causing a real, reproducible,
          currently-failing required GitHub Actions check on the exact VM-R2-verified candidate. Genuinely
          merge-blocking; not a security or product-correctness defect.
P3 = 1  -- carried forward from VM-R2, non-blocking API-surface wording note.
```

## 13. Exact R3 architectural decision

The current-schema CI invariant for CDD-059 is frozen as:

```
Alembic head:                     0045_oqi_connector_ingestion
Expected current table count:     126
```

The stale current-schema CI expectation of `123` must become `126` in the exact check responsible for
validating the final migrated schema (`.github/workflows/ci.yml:153` and its accompanying diagnostic
text on the same line). This is CI alignment with the already-governed, already-migrated schema. It is
NOT a schema change, NOT a migration change, and does not touch the already-correct dynamic migration-head
check immediately above it.

## 14. Exact I-R3 implementation authorization

```
CREATE = 0
MODIFY = 1
DELETE = 0
TOTAL  = 1
```

The ONLY authorized implementation path:

```
.github/workflows/ci.yml
```

## 15. Exact allowed change (binding, minimum only)

```
.github/workflows/ci.yml:153 (current)
    [ "$count" -eq 123 ] || { echo "unexpected table count: $count (expected 123)"; exit 1; }

.github/workflows/ci.yml:153 (authorized)
    [ "$count" -eq 126 ] || { echo "unexpected table count: $count (expected 126)"; exit 1; }
```

Both occurrences of the literal `123` on this single line (the comparison and its own parenthetical
diagnostic text) become `126`. No other character on this line, no other line in this step (lines 148-152
unchanged), no other step, and no other job in `.github/workflows/ci.yml` may change under this
authorization.

## 16. Prohibited paths

I-R3 must NOT modify: `backend/app/infrastructure/connectors/rest_connector.py`,
`backend/app/tests/test_oqi_connector_ingestion_postgres.py`,
`backend/app/application/connector_ingestion_service.py`, any migration, any ORM model, any repository,
any API route, any schema, any tenant logic, any evidence logic, `docker-compose.yml`, Keycloak
configuration, frontend source, dependency files, lockfiles, Dockerfiles, any existing CDD-059 governance
artifact, the R1 or R2 amendments, or either historical `123` assertion identified in §8.

## 17. Prohibited CI weakenings

Forbidden under this authorization: removing the table-count assertion; adding `|| true`; changing
`exit 1` to any non-failing behavior; marking the step `continue-on-error`; skipping the `containers` job;
changing branch filters to exclude PR #193; hardcoding success; suppressing failure output; removing or
altering the migration-head verification step; changing required-check behavior anywhere in the workflow.
The correction makes the CI invariant accurately reflect the governed current schema — nothing more, and
strictly no reduction in enforcement strength.

## 18. I-R3 required local verification (minimum)

1. governance hashes (all four listed in §4, plus this document once published) verified before write;
2. exactly one implementation path touched (`.github/workflows/ci.yml`);
3. exactly the semantic change in §15, nothing else in the file;
4. YAML remains valid (`docker compose config --quiet` equivalent / a YAML parse check);
5. shell syntax of the modified step remains valid;
6. a clean migration run reaches single head `0045_oqi_connector_ingestion`;
7. a clean current-schema count is 126;
8. the corrected local assertion (`[ "126" -eq "126" ]`) succeeds;
9. no production source changed (`git diff` confirms);
10. no test source changed;
11. no migration changed;
12. no dependency file changed.

Because this is a CI-only correction to an already-fully-verified candidate, I-R3 is NOT required to
repeat CDD-059's own connector-suite (59 tests) or full-backend (2177 tests) regression, nor VM-R2's
Docker/TLS/pinning campaign — per §19 below.

## 19. Actual-GitHub-Actions verification requirement (binding on I-R3/VM-R3)

Local verification alone is insufficient. After I-R3 commits and pushes its corrected candidate head,
PR #193 must be observed to update to that new head, and the actual `containers` job must be independently
re-checked via `gh pr checks 193` / `gh run view`. It must **execute** the table-count check and observe
`table count: 126` succeed — not be skipped, cancelled, or bypassed. `backend` and `frontend` checks
(already passing) must remain passing on the corrected head.

## 20. VM-R2 evidence preservation

VM-R2's complete independent security/correctness verification — real-socket DNS-rebinding closure proof,
TLS SNI/hostname positive and negative crowns, HTTP Host preservation, ambient-proxy neutralization on
host and in Docker, production/fixture policy boundary, metadata absolute-deny, live PostgreSQL structural
FK verification, credential-leak checks, static security search, dependency audit, 59/59 connector tests,
2177/2177 full backend regression, fresh no-cache Docker pinned-transport crown — **remains valid
evidence** for every implementation byte this amendment does not touch. VM-R2 stopped for a CI
governance-enumeration failure, not a capability-verification failure; a one-line, two-literal CI
correction confined to `.github/workflows/ci.yml` does not by itself invalidate that evidence.

**This preservation is conditional**, per §21.

## 21. Conditions that invalidate VM-R2 evidence — binding on VM-R3

VM-R3 MUST escalate back to a broader re-verification (rather than relying on §20) if the actual I-R3
incremental diff contains anything beyond `.github/workflows/ci.yml`, or if the change to that file is
anything beyond the exact literal/diagnostic-text correction authorized in §15. Any production, test, or
migration path appearing in the I-R3 diff; any further CI semantic change; any new dependency; any new
P0/P1; or any need to also modify either historical `123` assertion in §8 — each independently invalidates
this amendment's narrow-scope premise and requires VM-R3 to STOP and re-scope rather than proceed to
merge.

## 22. VM-R3 exact scope

VM-R3 is a narrow final verification/merge gate. It does NOT repeat CDD-059's full security campaign
unless §21 triggers. It MUST independently verify: authoritative main; exact updated candidate head;
governance hash chain including this amendment; the I-R3 incremental diff is exactly one path with exactly
the authorized semantic edit; cumulative candidate path authorization across all of CDD-059's governance
documents plus this one; migration head is still `0045_oqi_connector_ingestion`; current table count is
still 126; the actual GitHub Actions `containers` job is GREEN for the corrected reason (table count: 126
observed and compared successfully); `backend`/`frontend` checks remain GREEN; no production/test/
migration bytes changed during I-R3; candidate head lock; merge via the repository's normal governed
PR-based workflow (no force push, no branch-protection bypass, no disabling of required checks, no
emergency bypass); post-merge main verification; post-merge governance hashes; post-merge migration/
table-count smoke test; capability closure.

## 23. PR #193 continuity

PR #193 is preserved as the correct, already-open, already-reviewed merge artifact. It is not closed or
recreated by this amendment. After I-R3 pushes its corrected head, the same PR (same branch, same base
`main`) will carry a new `headRefOid`; VM-R3 must independently re-verify that exact new head before any
merge.

## 24. Maximum product-claim disposition

Unchanged from VM-R2. This amendment authorizes no capability, security, or scope change; the truthful
maximum product claim established at VM-R2 remains the claim to make once VM-R3 actually merges.

## 25. No merge / no implementation in this phase

This phase (G-R3) creates only this governance artifact. It does not modify `.github/workflows/ci.yml`,
any other file, or PR #193's state. Implementation of the exact change frozen in §15 is deferred to
`REAL-ENTERPRISE-INGESTION-I-R3`.

## 26. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent (`CDD-047`, `CDD-048` §9, and CDD-059's own I-R1/I-R2 amendments) of never silently
rewriting an already-approved Artifact Authorization in place, and never folding an out-of-scope CI
correction into an already-verified implementation commit. CDD-059 closure is formally reauthorized to
resume against this corrected CI-workflow surface, under the identifier CDD-059-CI.

**Exact next phase: `REAL-ENTERPRISE-INGESTION-I-R3`.**
