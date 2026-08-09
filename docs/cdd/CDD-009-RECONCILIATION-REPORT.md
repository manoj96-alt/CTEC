# CDD-009 — Published Baseline Reconciliation Report

Status: APPROVED — PASS

Baseline release commit: `834582b754157a87a1924fa2b592ed9cbfcc3ee9`

Baseline evidence commit: `ce9fcfedd1d013e7bd88e7cf0b54885ba69737d1`

Source implementation commit: `5fa51e7`

Reconciled candidate commit: `16b3912`

## Authority review

CDD-009 is reconciled against CDD Template v2.2, GRM-001 v1.2, GEM-001 v1.1, RFC-013 v1.1, RFC-011 v1.0, PMM-001 v1.0 and the finalized Baseline v1.1 Registry. The business scope is unchanged from the approved work order. Governance Authority remains outside the implementation. Governance Attestation remains derived and unpersisted. The canonical `governances` table remains read-only.

The authorized append-only `governance_evaluation_records` table is a capability-owned immutable source record under PMM-001. It does not modify or replace the frozen Physical Model and does not authorize a canonical outcome writer.

## Authorization-boundary result

The exact file/action matrix is recorded in `docs/cdd/CDD-009-AUTHORIZATION.md`. Every source-commit change maps to one authorized business, persistence, configuration, test or documentation artifact. No DELETE and no external contract are present. Files added solely by reconciliation are governance evidence and do not change governed runtime behavior.

## Validation evidence

Executed 2026-08-08 from `agent/cdd-009-reconcile`:

| Gate | Result |
|---|---|
| Architecture registry, checksum, manifest and dependency validation | PASS — 102 registry entries, 50 v1.0 artifacts, 41 v1.1 artifacts, 77 dependency relationships and 91 release artifacts verified. |
| Ruff | PASS — all checks passed. |
| Black | PASS — 164 files unchanged. |
| isort | PASS — 3 intentionally skipped files; all checked files passed. |
| mypy | PASS — no issues in 163 source files. |
| Unit suite without database | PASS — 97 passed, 9 PostgreSQL tests skipped, 89.79% coverage. |
| Full PostgreSQL integration suite | PASS — 106 passed, 0 skipped, 94.81% coverage, using an isolated PostgreSQL 15.17 database and the Alembic migration chain through `0007_governance_eval`. |
| Governance migration and immutability | PASS — migration head and mutation-rejection trigger verified by integration test. |
| Authorization boundary | PASS — every changed runtime, persistence, configuration, test and documentation path is enumerated in `CDD-009-AUTHORIZATION.md`; no deletion or external API exists. |

## Architecture drift result

PASS. No business entity was introduced or modified; no canonical relationship or attribute changed; no RFC or BCS changed; no layer was bypassed; and no technology outside TAS-001 was introduced. The only new table is the work-order-authorized, capability-owned immutable Governance Evaluation source-record table. The canonical Physical Model and its `governances` outcome table are unchanged and receive no writer. Configuration examples were normalized so a BCS document version is not represented as a governed policy version.

No unauthorized artifacts changed. Reconciliation added only the authorization and evidence documents and updated stale authority references in CDD-009 documentation plus neutral governance configuration examples.

## Reviewer decision

APPROVED. P0 findings: zero. P1 findings: zero. The source implementation may be committed as a reconciled candidate, merged to `main`, and registered with its resulting reconciliation and merge SHAs. The Registry is the location for the final self-referential commit evidence that cannot be embedded atomically in this report.
