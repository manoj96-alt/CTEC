# CDD-051 OQI-H5 Governed Timeliness — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-051-OQI-H5-Governed-Timeliness.md` only. No wildcard, no directory-level
grant, no "and related files" language. Any path not named below is unauthorized; if implementation
discovers a genuine need to touch an unnamed path, implementation must STOP and return for a narrow
amendment, exactly as the `OQI-H1-I-R1`/`OQI-H2-I-R1`/`OQI-H3-I-R1`/`OQI-H3-VM-R1`/`OQI-H4-R1` precedents
established.

## 1. Accounting

```
I1: CREATE = 12   MODIFY = 4    DELETE = 0   SUBTOTAL = 16
I2: CREATE = 0    MODIFY = 6    DELETE = 0   SUBTOTAL = 6
TOTAL:  CREATE = 12   MODIFY = 10   DELETE = 0   TOTAL = 22
```

## 2. I1 — CREATE (12)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_timeliness/__init__.py` | Package init. |
| 2 | `backend/app/domain/oqi_timeliness/policy.py` | `TimelinessPolicy` domain dataclass, version/activation logic, threshold validation (CDD-051 §8), mirroring `OqiBusinessProcessORM`'s `(id, version)` versioning shape and `QualityCoveragePolicy`'s immutable-row discipline. |
| 3 | `backend/app/domain/oqi_timeliness/evaluation.py` | `TimelinessFindingType` StrEnum (`STALE_SOURCE_EVIDENCE`, `INGESTION_LATENCY_EXCEEDED`, CDD-051 §4); `TimelinessEvaluation`/`TimelinessFinding` dataclasses; `derive_timeliness_evaluation_id`/`derive_timeliness_finding_id` (CDD-051 §17-§18); `apply_timeliness_finding_transition` (CDD-051 §19). |
| 4 | `backend/app/application/oqi_timeliness_evaluation_service.py` | Evaluator: `evaluate_current_state`, injected `clock` (CDD-051 §12), resolves qualifying `FieldValueEvidence` via the read-only H1 semantic-mapping lookup (CDD-051 §33), computes age against `evaluation_horizon` (never wall-clock, CDD-051 §13), applies the threshold boundary (CDD-051 §4), persists idempotently, mutates Finding only when genuinely new. |
| 5 | `backend/app/infrastructure/persistence/models/oqi_timeliness.py` | ORM: `oqi_timeliness_policies`, `oqi_timeliness_evaluations`, `oqi_timeliness_findings` — exactly the three tables named in CDD-051 §8/§28, no more. |
| 6 | `backend/app/infrastructure/persistence/oqi_timeliness_policy_repository.py` | Repository: CRUD/versioning for `TimelinessPolicy`, dedicated advisory lock seed (CDD-051 §8, CDD-046 §39 discipline). |
| 7 | `backend/app/infrastructure/persistence/oqi_timeliness_evaluation_repository.py` | Repository for Evaluation/Finding persistence, qualifying-evidence lookup (CDD-051 §33), dedicated advisory lock seed distinct from every existing OQI1-H4 seed. |
| 8 | `backend/app/infrastructure/persistence/migrations/versions/0039_oqi_h5_timeliness_policy.py` | Migration: CREATE `oqi_timeliness_policies`; MODIFY `oqi_business_processes` to add `UniqueConstraint(tenant_id, process_id, version)` only (CDD-051 §9, §28). No other DDL. |
| 9 | `backend/app/infrastructure/persistence/migrations/versions/0040_oqi_h5_timeliness_evaluation.py` | Migration: CREATE `oqi_timeliness_evaluations`, `oqi_timeliness_findings` (CDD-051 §28). |
| 10 | `backend/app/tests/test_oqi_h5_timeliness_crown.py` | Crown suite: the CDD-051 §27 scenarios A-G; both Finding types; threshold-boundary equality case; NOT_EVALUABLE cases (§6); historical/as-of evaluation (§13); re-ingestion laundering-resistance proof; H1/H2/H3/H4 crown non-regression. |
| 11 | `backend/app/tests/test_oqi_h5_timeliness_authorization_and_tenant_isolation.py` | Real-PostgreSQL adversarial tenant-isolation tests for every composite FK named in CDD-051 §29 (direct `session.add()`+`flush()` bypass, `IntegrityError` expected), plus positive same-tenant controls, plus the pre-existing service-layer validation check (mirroring `test_oqi_h4_integrity_authorization_and_tenant_isolation.py`'s R1 series exactly). |
| 12 | `backend/app/tests/test_oqi_timeliness_evaluation_domain.py` | Domain-level unit tests for the Evaluation/Finding dataclasses, identity derivation (§17-§18), threshold boundary (§4), and transition function in isolation (no PostgreSQL), mirroring `test_oqi_integrity_structural_evaluation_domain.py`'s established precedent. |

## 3. I1 — MODIFY (4)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/domain/oqi/quality_rule.py` | Add `TIMELINESS` to `QualityDimension` (CDD-051 §3). No change to `_ALLOWED_COMBINATIONS`, `QualityFindingType`, or any other member/row. |
| 2 | `backend/app/domain/oqi_finding_origin/origin.py` | Add `TIMELINESS` to `FindingStorageFamily` (CDD-051 §4). No change to `_VALID_QUALITY_DIMENSION_VALUES`'s auto-derivation, `storage_family_from_finding_family`/`finding_family_from_storage_family`, or any dispatch shape. |
| 3 | `backend/app/infrastructure/persistence/models/oqi_business_impact.py` | Add exactly one `UniqueConstraint("tenant_id", "process_id", "version", name="uq_oqi_business_processes_tenant_pk")` to `OqiBusinessProcessORM.__table_args__` (CDD-051 §9). No change to `OqiBusinessDependencyORM`, any other class in this file, any column, or any existing index. |
| 4 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | Add exactly two narrow, additive methods, `resolve_timeliness_finding_origin`/`resolve_timeliness_finding_subject` (CDD-051 §22). No change to the existing `resolve_finding_subject`/`resolve_finding_origin` methods' signatures or behavior, and no change to the existing `resolve_integrity_*` methods added by H4. |

## 4. I2 — MODIFY (6)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | `has_qualifying_coverage_for_dimension` gains exactly one new branch, `TIMELINESS`, an existence-only, subject-scoped qualifying-evaluation query against `oqi_timeliness_evaluations` (CDD-051 §25). No change to any other branch; the `UNIQUENESS` half of the existing fallthrough comment/behavior is untouched. |
| 2 | `backend/app/application/oqi_remediation_service.py` | `extract_candidates` gains one additional `quality_dimension == "TIMELINESS"` dispatch branch returning zero candidates, mirroring the existing `INTEGRITY`/`REASONABLENESS` branches exactly (CDD-051 §23). No change to any other branch. |
| 3 | `backend/app/infrastructure/persistence/oqi_business_impact_repository.py` | `compute_subject_finding_state` gains one or two new indirect-path `SELECT` branches for `oqi_timeliness_findings`, joined through `CurrentOntologyImpactORM.finding_family == 'TIMELINESS'` (CDD-051 §24), mirroring the existing branches' exact shape. No change to any existing branch. |
| 4 | `backend/app/application/oqi_product_experience_service.py` | `list_findings` gains exactly two new branches, `INTEGRITY` and `TIMELINESS` (CDD-051 §26). No change to the existing `OQI1`/`OQI2`/`OQI3` branches or any other method. |
| 5 | `frontend/app/quality/findings/page.tsx` | The family-filter `<select>` gains exactly two new `<option>` entries, `INTEGRITY` and `TIMELINESS` (CDD-051 §26). No other markup, styling, component, or page change. |
| 6 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | Add one new test, `test_timeliness_dispatches_to_timeliness_evaluation_repository`, mirroring `test_conformity_dispatches_to_conformity_evaluation_repository`'s exact structure (CDD-051 §25). No other test in this file may change. |

**Pre-authorization rationale for the table-count and enum-count mechanical corrections (binding
disclosure, required at both I1 and I2 boundaries)**: independently re-verify via fresh `grep` against the
merged I1 candidate before I2 begins — the same six files that hardcoded `120` at H4 closure
(`test_oqi_business_rule_postgres.py`, `test_oqi_ontology_impact_postgres.py`,
`test_persistence_integration.py`, `test_oqi_business_impact.py`, `test_oqi_remediation_agent_i2.py`,
`test_oqi_remediation_i1.py`) plus `.github/workflows/ci.yml` must have their literal updated to `123`
(CDD-051 §28) as part of I1 (since the table count changes within I1, not I2). This mirrors the identical
`OQI-H1-I-R1`/`OQI-H2-I-R1`/`OQI-H3`/`OQI-H4` precedent exactly: **authorization is strictly limited to the
bare numeric literal change (`120`→`123`) and any adjoining message text** — no other line in any of these
seven files may change under this authorization. These seven mechanical corrections are **I1-scoped**
(listed in §5 below, not §3, since they are a distinct accounting category from both the new-file CREATE
set and the four semantic MODIFY rows).

`backend/app/tests/test_oqi_quality_coverage_policy_domain.py`'s exact `QualityDimension`
member-count/value-set assertion must move from 6 to 7 members including `"TIMELINESS"` (CDD-051 §3),
mirroring the identical correction H4-I made for `5` → `6`. `backend/app/tests/test_runtime_architecture.py`
must gain the three new construction sites (`oqi_timeliness_policy_repository.py`,
`oqi_timeliness_evaluation_repository.py`, and the ORM classes in `models/oqi_timeliness.py`), mirroring
H4's own firewall-extension precedent exactly. `backend/app/infrastructure/persistence/demo_oqi_seeder.py`
gains the H5 crown scenario (CDD-051 §27) — no modification to any existing H1-H4 fixture, invocation, or
crown scenario's own values, and no direct insertion of Timeliness evaluation/Finding rows (must arise
through the real services, mirroring CDD-050 §34's precedent).

## 5. I1 — MODIFY, mechanical-only (7)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `.github/workflows/ci.yml` | Exactly one change: the table-count assertion, `120` → `123` (message text included). No other CI change. |
| 2 | `backend/app/tests/test_oqi_business_rule_postgres.py` | Mechanical only: table-count literal, `120` → `123`. |
| 3 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | Mechanical only: table-count literal, `120` → `123` (both occurrences). |
| 4 | `backend/app/tests/test_persistence_integration.py` | Mechanical only: table-count literal, `120` → `123`. |
| 5 | `backend/app/tests/test_oqi_business_impact.py` | Mechanical only: table-count literal, `120` → `123` (both occurrences). |
| 6 | `backend/app/tests/test_oqi_remediation_agent_i2.py` | Mechanical only: table-count literal, `120` → `123` (both occurrences). |
| 7 | `backend/app/tests/test_oqi_remediation_i1.py` | Mechanical only: table-count literal, `120` → `123` (both occurrences). |

| # | Path | Permitted modification |
|---|---|---|
| 8 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | MODIFY: update the exact `QualityDimension` member-count/value-set assertion from 6 to 7 members including `"TIMELINESS"` (CDD-051 §3). No other test in this file may change. |
| 9 | `backend/app/tests/test_runtime_architecture.py` | MODIFY: add the new construction sites for `oqi_timeliness_policy_repository.py`, `oqi_timeliness_evaluation_repository.py`, and the ORM classes in `models/oqi_timeliness.py` to the expected construction-site lists, mirroring H4's own precedent exactly. No other test in this file may change. |
| 10 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | Add the H5 crown scenario (CDD-051 §27): new demo-only `EnterpriseEntity`/source-system fixtures (e.g. `Shipment`, `Carrier`), one or two `TimelinessPolicy` rows anchored to a real, existing (or newly-seeded, within this same authorization) `InformationElementRequirement`/`BusinessProcess` pair. No modification to any existing seeded H1-H4 fixture, invocation, or crown scenario's own values. No direct insertion of Timeliness evaluation/Finding rows — must arise through the real services (rows 4/6-7 of §2). |

**Renumbering note**: rows 1-7 above are the mechanical table-count set (7 files, one more than H4's six,
because this document additionally requires `.github/workflows/ci.yml` in the same accounting row set
rather than split across two lists as CDD-050's Authorization did — a purely presentational simplification,
not a scope change). Rows 8-10 are the enum-count/architecture-firewall/seeder set, mirroring CDD-050 §3
rows 16-18 exactly in kind. **Total I1 MODIFY, including this mechanical set: 4 (§3) + 10 (§5) = 14.**
Combined with I2's 6 (§4), the accounting in §1 is restated precisely as:

```
I1: CREATE = 12   MODIFY = 4 (semantic, §3) + 10 (mechanical, §5) = 14   DELETE = 0   SUBTOTAL = 26
I2: CREATE = 0    MODIFY = 6 (semantic, §4)                              DELETE = 0   SUBTOTAL = 6
TOTAL:  CREATE = 12   MODIFY = 20   DELETE = 0   TOTAL = 32
```

This restated accounting in §5 supersedes the summary in §1, which undercounted the mechanical set — §1 is
retained above only for the initial category breakdown and must be read together with this correction. (No
implementation is authorized to treat §1's smaller number as the binding total; §5's restated total is
authoritative.)

## 6. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized, called out because a reasonable implementer might assume
otherwise: any Keycloak realm file (no new authority scope is authorized); any frontend file other than the
single named row in §4 (no redesign, no new page, no new component); `backend/app/domain/oqi_remediation/
candidate.py` (no new `RemediationCandidateBasis` member); `backend/app/domain/oqi_remediation/
authorization.py` (`RemediationActionType` stays closed to `UPDATE_FIELD`); `backend/app/infrastructure/
persistence/models/oqi_business_impact.py`'s `OqiBusinessDependencyORM` class specifically (only
`OqiBusinessProcessORM`'s `__table_args__` may change, CDD-051 §9); any file implementing `UNIQUENESS`,
`ACCURACY`'s or `CONFORMITY`'s own comparison path, or any other dimension; `backend/app/domain/
identity_resolution/` or any ER-internal module; `backend/app/domain/integration/field_value_evidence.py`
or its repository (no mutation path of any kind); `backend/app/domain/blueprint/model.py` or any
Blueprint/`InformationElementRequirement`/`RelationshipRequirement` domain/persistence/repository file
(reused unmodified, read-only); any production orchestration/scheduler/event-trigger file; any Command
Center or dashboard file beyond §4 row 5; `architecture/INDEX.md` (this OQI CDD track has never registered
there, precedent confirmed through CDD-050); `docs/product/` (explicitly out of scope, untouched throughout
every prior phase).

**Advisory lock seed registry**: `oqi_timeliness_policy_repository.py` and
`oqi_timeliness_evaluation_repository.py` each require their own dedicated advisory-lock seed, distinct
from every existing OQI1-6/H1-H4 seed — the exact integer is an implementation-time detail (CDD-046 §39's
own precedent for exactly this class of deferral), disclosed in H5-I1's own final report, never silently
reused.

## 7. Migration

```
Expected revision (0039): 0039_oqi_h5_timeliness_policy       (29 chars)
Expected down_revision:    0038_oqi_h4_reference_tenancy
Expected revision (0040): 0040_oqi_h5_timeliness_evaluation   (33 chars)
Expected down_revision:    0039_oqi_h5_timeliness_policy

Pre-H5 table count:    120 (RE-VERIFY FRESH at I1 start against the real merged H4 baseline — do not trust
                             this document's figure without a live count, per every prior OQI phase's own
                             established discipline)
Post-0039 table count:  121  (+ oqi_timeliness_policies; the oqi_business_processes MODIFY adds zero tables)
Post-0040 table count:  123  (+ oqi_timeliness_evaluations, oqi_timeliness_findings)
Final expected table count: 123
```

Required round-trip: `120 → 121 → 123 → 121 → 120 → 123` (each migration's own upgrade/downgrade/re-upgrade
proven independently, then the full two-migration chain proven together, per CDD-051 §28). Single Alembic
head required at all times. No migration beyond the two named here is authorized in I1; I2 authorizes no
migration at all.

## 8. Implementation shape

Two implementation phases are authorized: `OQI-H5-I1` and `OQI-H5-I2`, exactly as CDD-051 §32 defines the
boundary. I1 must independently pass its own full test matrix (§9 below) against real PostgreSQL before I2
begins. A further split within I1 or I2 is permitted only if each sub-phase independently satisfies this
Authorization's exact path list and migration ordering — introducing a genuinely new intermediate migration
revision to accommodate a split is itself a STOP-worthy governance return, not a decision implementation
may make unilaterally.

## 9. API / Frontend

**I1: none authorized.** **I2: exactly the two rows named in §4 (rows 4-5) — the generic findings service
gains `INTEGRITY`/`TIMELINESS` branches, and the family-filter dropdown gains the two matching options. No
other API route, schema, or frontend page/component is authorized in either phase.**

## 10. Mandatory test matrix

**I1** (binding on the three new test files, rows 10-12 of §2): both Finding types independently; the
exact threshold-boundary equality case (§4 of CDD-051); every `NOT_EVALUABLE` case (§6); historical/as-of
evaluation using a caller-supplied `evaluation_horizon` distinct from wall-clock (§13); a re-ingestion
laundering-resistance proof (identical `FieldValueEvidence` re-observed does not create a duplicate
Evaluation); Finding-identity stability across advancing age and across a policy version change (§17);
Evaluation-identity idempotence (§18); the full six-branch lifecycle (§19); every composite tenant FK named
in §29 of CDD-051, adversarially, against real PostgreSQL, both negative (cross-tenant, `IntegrityError`
expected) and positive (same-tenant, accepted) cases; the OQI4 resolver-method pair; H1/H2/H3/H4 crown
non-regression.

**I2**: `TIMELINESS` Coverage dispatch (qualifying-evaluation-exists and no-evaluation-exists cases);
`TIMELINESS` presence in `compute_subject_finding_state`'s `union_all` correctly influencing
`RelianceState` with no change to the state vocabulary itself; `TIMELINESS` producing zero remediation
candidates via `extract_candidates`; `list_findings` returning `INTEGRITY` and `TIMELINESS` findings
correctly, tenant-scoped, with `OQI1`/`OQI2`/`OQI3` behavior unchanged; frontend filter rendering the two
new options with no change to existing rendering.

Full regression suite (all pre-existing OQI1-H4 tests) must still pass unmodified at both I1 and I2
boundaries. Whole-package `mypy app` must be clean. Docker/Compose/demo-seeder runtime proof required
before any claim of completion at either boundary, per CDD-051 §28's Docker/table-count discipline and
CDD-046 §45's binding, unmodified requirement.
