# CDD-084 OQI-H6 Governed Enterprise-Entity Uniqueness — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness.md` only. No wildcard,
no directory-level grant, no "and related files" language. Any path not named below is unauthorized; if
implementation discovers a genuine need to touch an unnamed path, implementation must STOP and return for a
narrow amendment, exactly as the `OQI-H1`/`H2`/`H3`/`H4`/`H4-R1`/`H5`/`H5`-amendments precedent establishes.

## 1. Accounting

```
I1: CREATE = 13   MODIFY = 3    DELETE = 0   SUBTOTAL = 16
I2: CREATE = 0    MODIFY = 15   DELETE = 0   SUBTOTAL = 15
TOTAL:  CREATE = 13   MODIFY = 18   DELETE = 0   TOTAL = 31
```

## 2. I1 — CREATE (13)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_uniqueness/__init__.py` | Package init. |
| 2 | `backend/app/domain/oqi_uniqueness/policy.py` | `UniquenessPolicy` domain dataclass: `policy_id`, `version`, `tenant_id`, `entity_type_id`, `bucket_max_size` (`> 0`), `status` (ACTIVE/RETIRED), `created_by`, `created_on`. Mirrors `TimelinessPolicy`'s domain-dataclass shape exactly. |
| 3 | `backend/app/domain/oqi_uniqueness/candidate.py` | `UniquenessCandidate` domain dataclass (canonical pair, policy reference, matched normalized name, created_on); `UniquenessAdjudication` domain dataclass (`REJECT_NOT_DUPLICATE`/`CONFIRM_DUPLICATE`, actor, rationale, timestamp); pair-canonicalization helper enforcing `member_a_id < member_b_id` at construction (raises `ValidationException` otherwise, mirroring every existing domain `__post_init__` discipline). |
| 4 | `backend/app/domain/oqi_uniqueness/evaluation.py` | `UniquenessOutcome` (`SATISFIED`/`VIOLATED`/`NOT_EVALUABLE`) and `UniquenessNotEvaluableReason` (`BUCKET_EXCEEDED_CAP`) StrEnums; `UniquenessEvaluation`/`UniquenessFinding` dataclasses; `derive_uniqueness_finding_id` (CDD-084 §24 formula); `apply_uniqueness_finding_transition` (CDD-084 §25's four-branch lifecycle). |
| 5 | `backend/app/application/oqi_uniqueness_evaluation_service.py` | Evaluator/candidate-generation service: `generate_candidates_for_entity_type` (tenant + entity_type scoped, `canonical_name()`-bucketed, bounded by `bucket_max_size`, CDD-084 §16-§18); `evaluate_current_state` (per-entity, produces `UniquenessEvaluation` + opens/reopens `UniquenessFinding` per CDD-084 §20/§25); injected `clock`, no direct DB query inside pure comparison logic (bucket contents supplied by the repository layer). |
| 6 | `backend/app/infrastructure/persistence/models/oqi_uniqueness.py` | ORM: `oqi_uniqueness_policies`, `oqi_uniqueness_evaluations`, `oqi_uniqueness_candidates`, `oqi_uniqueness_adjudications`, `oqi_uniqueness_findings` — exactly the five tables named in §7 below, no more. |
| 7 | `backend/app/infrastructure/persistence/oqi_uniqueness_policy_repository.py` | Repository: CRUD/versioning for `UniquenessPolicy`, dedicated advisory-lock seed distinct from every existing OQI1-6/H1-H5 seed (integer disclosed in H6-I1's own final report, never silently reused, mirroring CDD-046 §39/CDD-051 §39's identical deferral). |
| 8 | `backend/app/infrastructure/persistence/oqi_uniqueness_candidate_repository.py` | Repository: bucket query (`tenant_id, entity_type_id, canonical_name → EnterpriseEntity rows`, bounded fetch for bucket-cap detection), idempotent candidate insert, append-only adjudication insert, latest-adjudication-per-candidate lookup, its own dedicated advisory-lock seed. |
| 9 | `backend/app/infrastructure/persistence/oqi_uniqueness_evaluation_repository.py` | Repository: evaluation-ledger insert, qualifying-evaluation existence lookup (feeds Coverage, §16 of the main document), Finding upsert/transition, its own dedicated advisory-lock seed. |
| 10 | `backend/app/infrastructure/persistence/migrations/versions/0047_oqi_h6_uniqueness.py` | Migration: CREATE all five tables named in §7 below. No modification to any existing table (`EnterpriseEntity`'s candidate key already exists, CDD-084 §13). `revision = "0047_oqi_h6_uniqueness"` (22 chars), `down_revision = "0046_oqi5_remediation_tenancy"` (29 chars, exact string re-verified against current `0046` migration's own `revision =` literal, not its filename) — both independently re-verified `< 32` chars before this document's own publication, applying the CDD-040/CDD-051 revision-length-defect lesson proactively rather than discovering it during implementation. |
| 11 | `backend/app/tests/test_oqi_h6_uniqueness_crown.py` | Crown suite: CDD-084's full I1 crown matrix (§13 below) — U1-U20. |
| 12 | `backend/app/tests/test_oqi_h6_uniqueness_authorization_and_tenant_isolation.py` | Real-PostgreSQL adversarial tenant-isolation tests for every composite FK named in §9 below (direct `session.add()`+`flush()` bypass, `IntegrityError` expected, both directions of every pair-member FK), plus positive same-tenant controls, mirroring `test_oqi_h5_timeliness_authorization_and_tenant_isolation.py`'s exact structure. |
| 13 | `backend/app/tests/test_oqi_uniqueness_domain.py` | Domain-level unit tests: pair-canonicalization construction discipline (`member_a_id < member_b_id` enforced, self-pair rejected); `UniquenessOutcome`/`UniquenessNotEvaluableReason` shape; `derive_uniqueness_finding_id` stability across policy-version churn; `apply_uniqueness_finding_transition`'s four branches in isolation (no PostgreSQL), mirroring `test_oqi_timeliness_evaluation_domain.py`'s established precedent. |

## 3. I1 — MODIFY (3)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/domain/oqi/quality_rule.py` | Add `UNIQUENESS` to `QualityDimension` (CDD-084 §8). No change to any other member, to `_ALLOWED_COMBINATIONS`, or to `QualityFindingType`. |
| 2 | `backend/app/domain/oqi_finding_origin/origin.py` | Add `UNIQUENESS` to `FindingStorageFamily` (CDD-084 §9). Add exactly two narrow, additive methods on `OqiOntologyImpactEvaluationRepositoryImpl` — `resolve_uniqueness_finding_origin`/`resolve_uniqueness_finding_subject` (CDD-084 §26) — mirroring `resolve_timeliness_finding_origin`/`resolve_timeliness_finding_subject`'s exact shape, returning per-member `DirectImpactResult`s (called once per pair member, never a new pair-specific return type). No change to `_VALID_QUALITY_DIMENSION_VALUES`'s auto-derivation, `storage_family_from_finding_family`/`finding_family_from_storage_family`, or any existing `resolve_*` method's signature/behavior. |
| 3 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | The concrete implementation of the two new methods added to the Protocol in row 2 above (same CDD-084 §26 authorization; listed separately because the Protocol and its implementation live in different files per this repository's established `origin.py`-Protocol / `*_repository.py`-implementation split, mirroring H4/H5's identical two-file pattern for their own `resolve_integrity_*`/`resolve_timeliness_*` additions). |

## 4. I2 — MODIFY (15)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | `has_qualifying_coverage_for_dimension`'s existing unconditional `return False` (currently the function's final line, immediately following the `TIMELINESS` branch) is replaced by an `if dimension is CoverageDimension.UNIQUENESS:` branch delegating to the new evaluation repository's qualifying-evaluation lookup (CDD-084 §28), followed by a final unconditional `return False` retained for any future, still-unsupported `CoverageDimension` member. No change to any other branch. |
| 2 | `backend/app/application/oqi_remediation_service.py` | `extract_candidates` gains one additional `elif quality_dimension == "UNIQUENESS": candidates = extract_reasonableness_candidates()` branch, mirroring the existing `TIMELINESS`/`INTEGRITY` branches exactly (CDD-084 §29). No change to any other branch. |
| 3 | `backend/app/infrastructure/persistence/oqi_business_impact_repository.py` | `compute_subject_finding_state` gains one new indirect-path `SELECT` branch for `oqi_uniqueness_findings`, joined through `CurrentOntologyImpactORM.finding_family == 'UNIQUENESS'` (CDD-084 §27), mirroring the `INTEGRITY`/`TIMELINESS` branches' exact shape. No change to any existing branch. |
| 4 | `backend/app/application/oqi_evaluation_orchestration_service.py` | `evaluate()` gains one new dispatch stage, reusing the already-resolved `enterprise_entity_id` from the existing Integrity Structural stage, own transaction/commit (CDD-084 §29). No change to any existing stage's resolution logic, transaction boundary, or the method's public signature. |
| 5 | `backend/app/application/oqi_product_experience_service.py` | `list_findings` gains exactly one new branch, `UNIQUENESS`, mirroring the `TIMELINESS` branch's exact shape, with `entity_id = member_a_id` per CDD-084 §30's documented display-anchor exception. No change to the existing `OQI1`/`OQI2`/`OQI3`/`INTEGRITY`/`TIMELINESS` branches. |
| 6 | `backend/app/api/oqi/router.py` | Add exactly one new read-only route, `GET /oqi/uniqueness-candidates/{finding_id}`, returning both pair members' identity/name/matched-evidence/adjudication-history/per-member impact (CDD-084 §30). Tenant-scoped via the existing authenticated-request tenant resolution, identical pattern to every other read route in this file. No write route. No change to any existing route. |
| 7 | `backend/app/api/oqi/schemas.py` | Add the response schema(s) for the new route in row 6 (`UniquenessCandidateDetailResponse` and its nested member/evidence/adjudication shapes). No change to any existing schema. |
| 8 | `frontend/app/quality/findings/page.tsx` | The family-filter `<select>` gains exactly one new `<option value="UNIQUENESS">Uniqueness</option>` entry, and `FAMILY_LABEL` gains the matching `UNIQUENESS: "Uniqueness"` entry (CDD-084 §30). No other markup, styling, component, or page change. |
| 9 | `frontend/app/quality/findings/[id]/page.tsx` (or this repository's current equivalent Finding-detail route — implementation must re-verify the exact current path before touching it, since the WOW track has relocated Finding-facing routes before, e.g. CDD-081) | Render a pair-candidate detail view when `family === "UNIQUENESS"`: both entities' identity/name, matched evidence, adjudication state, impact — consuming row 6's new endpoint. No change to any other family's existing rendering path. |
| 10 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | Add one new test, `test_uniqueness_dispatches_to_uniqueness_evaluation_repository`, mirroring `test_timeliness_dispatches_to_timeliness_evaluation_repository`'s exact structure (CDD-084 §28). No other test in this file may change. |
| 11 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | Update the exact `QualityDimension` member-count/value-set assertion from 7 to 8 members including `"UNIQUENESS"` (CDD-084 §8; current assertion re-verified this phase at line 57, `assert len(list(QualityDimension)) == 7`). No other test in this file may change. |
| 12 | `backend/app/tests/test_runtime_architecture.py` | Add the new construction sites for `oqi_uniqueness_policy_repository.py`, `oqi_uniqueness_candidate_repository.py`, `oqi_uniqueness_evaluation_repository.py`, and the five ORM classes in `models/oqi_uniqueness.py` to the expected construction-site lists, mirroring H4's/H5's own firewall-extension precedent exactly. No other test in this file may change. |
| 13 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | Add the H6 crown scenario (CDD-084 §12 of this Authorization / main document §6): two new demo `EnterpriseEntity` rows of the existing `Product` type sharing an identical `canonical_name()` value (→ candidate + Finding), a third distinct `Product` entity (→ no candidate), one `UniquenessPolicy` row anchored to the existing `Product` `entity_type_id`. No modification to any existing seeded H1-H5 fixture, invocation, or crown scenario's own values. No direct insertion of Uniqueness evaluation/candidate/Finding rows — must arise through the real services (rows 5/7-9 of §2), mirroring CDD-051 §27's identical precedent. |
| 14 | `backend/app/tests/test_oqi_h6_uniqueness_platform_integration.py` | New file (I2-scoped): U21-U35 (§14 below) — Coverage dispatch, OQI6 visibility, zero-remediation dispatch, production-orchestration reachability, ingestion non-side-effect, generic Finding API, frontend-adjacent contract shape, H1-H5/OQI4/5/6 tenant-isolation crown non-regression, Docker-equals-host proof hook. |
| 15 | `.github/workflows/ci.yml` plus the nine table-count test files re-verified this phase (`test_oqi_business_impact.py`, `test_oqi_business_rule_postgres.py`, `test_oqi_connector_ingestion_postgres.py`, `test_oqi_evaluation_orchestration_postgres.py`, `test_oqi_ontology_impact_postgres.py`, `test_oqi_remediation_agent_i2.py`, `test_oqi_remediation_i1.py`, `test_persistence_integration.py`, `test_production_remediation_orchestration_postgres.py`) | Mechanical only: the table-count literal, `126` → `131`, at every occurrence listed in §11 below (message text included where present). No other line in any of these ten files may change. This is **I2-scoped**, not I1-scoped, because CDD-051's own precedent (table count changes "within I1, not I2" there) applied specifically because H5's table count changed at I1; H6's table count also changes at I1 (5 new tables land in the I1 migration, row 10 of §2) — **implementation must therefore apply this correction at the I1 boundary, matching CDD-051's own stated rule, not this row's I2 grouping**; this row is listed under I2 only for this Authorization's own accounting-table adjacency to the other mechanical/product-integration rows and does not override CDD-084 §33's STOP discipline — do not defer the ten-file numeric correction past I1. |

## 5. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized: any Keycloak realm file; `backend/app/domain/identity_resolution/`
or any file therein (ER stays read-only-consumed, unmodified — `canonical_name()` is *called*, never edited);
`backend/app/infrastructure/persistence/models/enterprise_entity.py` (its existing candidate key already
suffices, CDD-084 §13 — no schema change); `backend/app/domain/oqi_remediation/authorization.py`
(`RemediationActionType` stays closed to `UPDATE_FIELD`); `backend/app/domain/oqi_remediation/candidate.py`
(no new `RemediationCandidateBasis` member); any file implementing `DUPLICATE_SOURCE_RECORD_CANDIDATE`,
source-record identity, or any grouping of `FieldValueEvidence.source_record_reference` (CDD-084 §3);
`backend/app/domain/oqi_ontology_impact/evaluation.py`'s `FindingFamily` (stays permanently closed);
`backend/app/infrastructure/connectors/rest_connector.py` or any Enterprise REST ingestion file (CDD-084
§29's ingestion boundary — no synchronous Uniqueness invocation); any Blueprint/`InformationElementRequirement`
file (unrelated to this dimension); `architecture/INDEX.md` (this OQI CDD track has never registered there,
precedent confirmed through CDD-050/051); `docs/product/` (explicitly out of scope, untouched throughout
every prior phase and this one).

**Advisory lock seed registry**: `oqi_uniqueness_policy_repository.py`, `oqi_uniqueness_candidate_repository.py`,
and `oqi_uniqueness_evaluation_repository.py` each require their own dedicated advisory-lock seed, distinct
from every existing OQI1-6/H1-H5 seed — the exact integers are implementation-time details (CDD-046 §39's own
precedent for exactly this class of deferral), disclosed in H6-I1's own final report, never silently reused.

## 6. Migration

```
Expected revision (0047): "0047_oqi_h6_uniqueness"          (22 chars)
Expected down_revision:    "0046_oqi5_remediation_tenancy"   (29 chars — the exact revision string inside
                                                                the current 0046 migration file, re-verified
                                                                against current source this phase, NOT its
                                                                longer filename)
Filename:                  0047_oqi_h6_uniqueness.py

Pre-H6 table count:    126 (RE-VERIFY FRESH at I1 start against the real merged main baseline — do not
                             trust this document's figure without a live count, per every prior OQI phase's
                             own established discipline)
Post-0047 table count:  131  (+ oqi_uniqueness_policies, oqi_uniqueness_evaluations,
                              oqi_uniqueness_candidates, oqi_uniqueness_adjudications,
                              oqi_uniqueness_findings)
Final expected table count: 131
```

Required round-trip: `126 → 131 → 126 → 131` (the single migration's own upgrade/downgrade/re-upgrade proven
independently, per CDD-051 §28's identical discipline). Single Alembic head required at all times. No
migration beyond the one named here is authorized in I1; I2 authorizes no migration at all.

## 7. Exact table schemas (binding)

### 7.1 `oqi_uniqueness_policies`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `policy_id` | `Uuid()` | NOT NULL | PK part 1 |
| `version` | `Integer()` | NOT NULL | PK part 2 |
| `tenant_id` | `String(200)` | NOT NULL | |
| `entity_type_id` | `Uuid()` | NOT NULL | plain FK → `entity_types.entity_type_id` (shared platform, no `tenant_id` column on that table) |
| `bucket_max_size` | `Integer()` | NOT NULL | `CHECK (bucket_max_size > 0)` |
| `status` | `String(16)` | NOT NULL | `CHECK (status IN ('ACTIVE','RETIRED'))` |
| `created_by` | `String(200)` | NOT NULL | |
| `created_on` | `DateTime(timezone=True)` | NOT NULL | |

Constraints/indexes: `PRIMARY KEY (policy_id, version)`; `UNIQUE (tenant_id, policy_id, version)` (composite
candidate key for downstream FKs, mirrors `uq_oqi_timeliness_policies_tenant_pk`); partial unique index
`uq_oqi_uniqueness_policies_one_active_per_type` on `(tenant_id, entity_type_id)` `WHERE status = 'ACTIVE'`;
`Index("idx_oqi_uniqueness_policies_tenant_id", "tenant_id")`.

### 7.2 `oqi_uniqueness_evaluations`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `evaluation_id` | `Uuid()` | NOT NULL | PK |
| `tenant_id` | `String(200)` | NOT NULL | |
| `policy_id` | `Uuid()` | NOT NULL | with `policy_version`, tenant-qualified composite FK → `oqi_uniqueness_policies(tenant_id, policy_id, version)` |
| `policy_version` | `Integer()` | NOT NULL | see above |
| `enterprise_entity_id` | `Uuid()` | NOT NULL | tenant-qualified composite FK → `enterprise_entities(tenant_id, enterprise_entity_id)` |
| `outcome` | `String(16)` | NOT NULL | `CHECK (outcome IN ('SATISFIED','VIOLATED','NOT_EVALUABLE'))` |
| `not_evaluable_reason` | `String(32)` | NULL | `CHECK ((outcome = 'NOT_EVALUABLE' AND not_evaluable_reason = 'BUCKET_EXCEEDED_CAP') OR (outcome != 'NOT_EVALUABLE' AND not_evaluable_reason IS NULL))` |
| `candidate_count` | `Integer()` | NOT NULL | `CHECK (candidate_count >= 0)`; server default `0` |
| `evaluated_on` | `DateTime(timezone=True)` | NOT NULL | |

Constraints/indexes: `ForeignKeyConstraint(["tenant_id","policy_id","policy_version"], [...])`;
`ForeignKeyConstraint(["tenant_id","enterprise_entity_id"], ["enterprise_entities.tenant_id",
"enterprise_entities.enterprise_entity_id"])`; `Index("idx_oqi_uniqueness_evaluations_subject", "tenant_id",
"enterprise_entity_id")` (feeds Coverage §28 and subject evaluation history); `Index("idx_oqi_uniqueness_
evaluations_policy", "tenant_id", "policy_id")`.

### 7.3 `oqi_uniqueness_candidates`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `candidate_id` | `Uuid()` | NOT NULL | PK |
| `tenant_id` | `String(200)` | NOT NULL | |
| `member_a_id` | `Uuid()` | NOT NULL | tenant-qualified composite FK → `enterprise_entities(tenant_id, enterprise_entity_id)` |
| `member_b_id` | `Uuid()` | NOT NULL | tenant-qualified composite FK → `enterprise_entities(tenant_id, enterprise_entity_id)` |
| `policy_id` | `Uuid()` | NOT NULL | with `policy_version`, tenant-qualified composite FK → `oqi_uniqueness_policies(tenant_id, policy_id, version)` |
| `policy_version` | `Integer()` | NOT NULL | see above |
| `matched_normalized_name` | `String(200)` | NOT NULL | the shared `canonical_name()` bucket value that qualified this pair (CDD-084 §18 evidentiary basis) |
| `created_on` | `DateTime(timezone=True)` | NOT NULL | |

Constraints/indexes: `CHECK (member_a_id < member_b_id)` (`ck_oqi_uniqueness_candidates_canonical_pair`);
`UNIQUE (tenant_id, member_a_id, member_b_id, policy_id, policy_version)`
(`uq_oqi_uniqueness_candidates_idempotent`); `UNIQUE (tenant_id, candidate_id)`
(`uq_oqi_uniqueness_candidates_tenant_pk` — composite candidate key so `oqi_uniqueness_adjudications` and
`oqi_uniqueness_findings` can each carry a tenant-qualified composite FK back to this table, mirroring
`EnterpriseEntity`'s own `uq_..._tenant_pk` pattern); two separate `ForeignKeyConstraint`s, one per member,
each against `enterprise_entities(tenant_id, enterprise_entity_id)`; `Index("idx_oqi_uniqueness_candidates_
tenant_id", "tenant_id")`; `Index("idx_oqi_uniqueness_candidates_pair", "tenant_id", "member_a_id",
"member_b_id")`.

### 7.4 `oqi_uniqueness_adjudications`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `adjudication_id` | `Uuid()` | NOT NULL | PK |
| `tenant_id` | `String(200)` | NOT NULL | |
| `candidate_id` | `Uuid()` | NOT NULL | tenant-qualified composite FK → `oqi_uniqueness_candidates(tenant_id, candidate_id)` |
| `action` | `String(24)` | NOT NULL | `CHECK (action IN ('REJECT_NOT_DUPLICATE','CONFIRM_DUPLICATE'))` — no `MERGE`, no `DEACTIVATE` (CDD-084 §21) |
| `actor_id` | `String(200)` | NOT NULL | |
| `rationale` | `String(2000)` | NOT NULL | |
| `decided_on` | `DateTime(timezone=True)` | NOT NULL | |

Constraints/indexes: `ForeignKeyConstraint(["tenant_id","candidate_id"], ["oqi_uniqueness_candidates.
tenant_id","oqi_uniqueness_candidates.candidate_id"])`; `Index("idx_oqi_uniqueness_adjudications_candidate",
"tenant_id", "candidate_id", "decided_on")` (feeds "latest adjudication per candidate" lookup). Append-only:
**no UPDATE, no DELETE authorized on this table by any implementation code.**

### 7.5 `oqi_uniqueness_findings`

| Column | Type | Nullable | Notes |
|---|---|---|---|
| `finding_id` | `Uuid()` | NOT NULL | PK; identity per CDD-084 §24 |
| `tenant_id` | `String(200)` | NOT NULL | |
| `finding_type` | `String(40)` | NOT NULL | `CHECK (finding_type = 'DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE')` |
| `candidate_id` | `Uuid()` | NOT NULL | tenant-qualified composite FK → `oqi_uniqueness_candidates(tenant_id, candidate_id)` |
| `member_a_id` | `Uuid()` | NOT NULL | denormalized from the candidate for direct query access (mirrors `TimelinessFindingORM.source_object_id`'s own denormalization-from-evaluation precedent); tenant-qualified composite FK → `enterprise_entities(tenant_id, enterprise_entity_id)` |
| `member_b_id` | `Uuid()` | NOT NULL | as above; tenant-qualified composite FK → `enterprise_entities(tenant_id, enterprise_entity_id)` |
| `status` | `String(16)` | NOT NULL | `CHECK (status IN ('OPEN','RESOLVED'))` |
| `state_revision` | `Integer()` | NOT NULL | |
| `first_seen_at` | `DateTime(timezone=True)` | NOT NULL | |
| `last_seen_at` | `DateTime(timezone=True)` | NOT NULL | |
| `occurrence_count` | `Integer()` | NOT NULL | |
| `reopen_count` | `Integer()` | NOT NULL | |

Constraints/indexes: `CHECK (member_a_id < member_b_id)`; `ForeignKeyConstraint(["tenant_id","candidate_id"],
[...])`; two per-member `ForeignKeyConstraint`s against `enterprise_entities`; `Index("idx_oqi_uniqueness_
findings_tenant_id", "tenant_id")`; `Index("idx_oqi_uniqueness_findings_status", "status")`;
`Index("idx_oqi_uniqueness_findings_pair", "tenant_id", "member_a_id", "member_b_id")`. No DELETE ever
authorized on this table — immutable current-state lineage, mirroring every other OQI Finding table.

## 8. Implementation shape

Two implementation phases are authorized: `OQI-H6-I1` and `OQI-H6-I2`, exactly as CDD-084 §33 and this
Authorization's §2-§4 split define the boundary. I1 must independently pass its own full test matrix (§13
below) against real PostgreSQL before I2 begins. **The table-count mechanical correction (§4 row 15) is
authorized for I2's path list but must be applied within the I1 phase**, exactly as CDD-051's own precedent
requires and as §4 row 15 itself states — this Authorization does not create a contradiction: the row's
*path list membership* is I2 for accounting-table adjacency only; its *timing* is I1, per CDD-084 §33.

## 9. Tenant isolation — exact composite FK list (binding, exhaustive)

```
oqi_uniqueness_evaluations.(tenant_id, enterprise_entity_id)  → enterprise_entities(tenant_id, enterprise_entity_id)
oqi_uniqueness_evaluations.(tenant_id, policy_id, policy_version) → oqi_uniqueness_policies(tenant_id, policy_id, version)
oqi_uniqueness_candidates.(tenant_id, member_a_id)             → enterprise_entities(tenant_id, enterprise_entity_id)
oqi_uniqueness_candidates.(tenant_id, member_b_id)             → enterprise_entities(tenant_id, enterprise_entity_id)
oqi_uniqueness_candidates.(tenant_id, policy_id, policy_version) → oqi_uniqueness_policies(tenant_id, policy_id, version)
oqi_uniqueness_adjudications.(tenant_id, candidate_id)         → oqi_uniqueness_candidates(tenant_id, candidate_id)
oqi_uniqueness_findings.(tenant_id, candidate_id)               → oqi_uniqueness_candidates(tenant_id, candidate_id)
oqi_uniqueness_findings.(tenant_id, member_a_id)                → enterprise_entities(tenant_id, enterprise_entity_id)
oqi_uniqueness_findings.(tenant_id, member_b_id)                → enterprise_entities(tenant_id, enterprise_entity_id)
```
Every one of the nine composite FKs above must be independently, adversarially proven in
`test_oqi_h6_uniqueness_authorization_and_tenant_isolation.py` (direct `session.add()`+`flush()` bypass,
cross-tenant, `IntegrityError` expected; same-tenant, accepted).

## 10. API / Frontend

**I1: none authorized.** **I2: exactly the four rows named in §4 (rows 5-9, minus the test file) — the
generic findings service gains a `UNIQUENESS` branch, one new read-only candidate-detail route + its
schemas, the family-filter dropdown gains the one matching option, and the Finding-detail route renders the
pair. No other API route, schema, or frontend page/component is authorized in either phase.**

## 11. Table-count mechanical correction — exact file list (binding, restated from §4 row 15)

```
.github/workflows/ci.yml                                    (1 occurrence, message text included)
backend/app/tests/test_oqi_business_impact.py                (4 occurrences)
backend/app/tests/test_oqi_business_rule_postgres.py          (1 occurrence)
backend/app/tests/test_oqi_connector_ingestion_postgres.py    (1 occurrence)
backend/app/tests/test_oqi_evaluation_orchestration_postgres.py (1 occurrence)
backend/app/tests/test_oqi_ontology_impact_postgres.py        (4 occurrences)
backend/app/tests/test_oqi_remediation_agent_i2.py            (2 occurrences)
backend/app/tests/test_oqi_remediation_i1.py                  (2 occurrences)
backend/app/tests/test_persistence_integration.py             (1 occurrence)
backend/app/tests/test_production_remediation_orchestration_postgres.py (1 occurrence)
```
Ten files, eighteen occurrences total, each re-verified directly against current `origin/main` this phase
(§CG of the preceding Discover+Resolve report). Authorization is strictly limited to the bare numeric literal
change (`126`→`131`) and any adjoining message text — no other line in any of these ten files may change.
Implementation must re-verify this exact file/occurrence list fresh via `grep` immediately before applying
the correction, per every prior OQI phase's own established discipline (CDD-051 AA §"Pre-authorization
rationale" restated).

## 12. Mandatory test matrix — I1

Binding on the three new test files (rows 11-13 of §2):

```
U1  strong governed evidence (identical canonical_name() match) → candidate persisted
U2  candidate → DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE Finding opens
U3  {A,B} and {B,A} generation order → exactly one canonical candidate row (member_a_id < member_b_id)
U4  A,A (self) → DB CHECK rejects (never reachable via the real service, proven adversarially at the DB layer)
U5  cross-tenant member_a/member_b → DB IntegrityError (both directions independently)
U6  incompatible entity_type_id → no candidate generated (excluded before comparison, not merely unqualified)
U7  no ACTIVE UniquenessPolicy for the entity's entity_type_id → NOT_EVALUABLE, zero persisted evaluation row
U8  bounded search completes, zero qualifying candidates → SATISFIED, persisted evaluation row
U9  bucket exceeds bucket_max_size → NOT_EVALUABLE, not_evaluable_reason='BUCKET_EXCEEDED_CAP', PERSISTED row
U10 identical evidence/policy version re-run → idempotent (no duplicate candidate/evaluation row)
U11 steward REJECT_NOT_DUPLICATE → durable adjudication row, Finding closes (status='RESOLVED')
U12 unchanged re-run after REJECT_NOT_DUPLICATE, same policy version → candidate not regenerated as a new
    logical row, Finding stays RESOLVED (does not reopen)
U13 policy version change, underlying names unchanged → CDD-084 §22's exact non-reopening behavior verified
U14 steward CONFIRM_DUPLICATE → zero EnterpriseEntity/relationship mutation of any kind
U15 CONFIRM_DUPLICATE → Finding remains status='OPEN'
U16 policy version change alone (no new candidate) → does not close or fabricate a Finding
U17 both candidate members independently resolve through OQI4 (resolve_uniqueness_finding_subject called once
    per member)
U18 both members' CurrentOntologyImpact rows reference the identical finding_id
U19 agent-role investigation of a candidate → zero graph/entity mutation (mirrors CDD-046 §34 test precedent)
U20 every composite FK in §9 fails structurally under direct adversarial DB insertion (cross-tenant)
```

## 13. Mandatory test matrix — I2

Binding on `test_oqi_quality_coverage_policy_service.py`'s new test (row 10 of §4) and the new file (row 14):

```
U21 CoverageDimension.UNIQUENESS dispatches to the new evaluation repository (no longer unconditional False)
U22 a qualifying SATISFIED or VIOLATED evaluation row → coverage true for that subject
U23 candidate existence with no evaluation row → coverage false
U24 a NOT_EVALUABLE (bucket-exceeded) persisted row → coverage true (CDD-084 §28's frozen "yes")
U25 required UNIQUENESS coverage absent (policy declares it, zero evaluation) → RELIANCE_UNKNOWN via existing
    H1 generalized predicate, zero new Reliance logic
U26 open UNIQUENESS Finding → AT_RISK via the existing dimension-agnostic any_open_finding input
U27 FindingStorageFamily.UNIQUENESS visible through compute_subject_finding_state's new branch
U28 extract_candidates(quality_dimension="UNIQUENESS") → zero remediation candidates, STEWARD_INVESTIGATION
U29 production orchestration's evaluate() reaches the Uniqueness stage using the already-resolved
    enterprise_entity_id, own transaction, non-fatal to any other stage on failure
U30 Enterprise REST ingestion path does not invoke Uniqueness candidate generation synchronously
U31 generic list_findings API returns UNIQUENESS Findings correctly, tenant-scoped, existing families
    unaffected
U32 new candidate-detail route returns both members' identity/evidence/adjudication/impact, tenant-scoped,
    zero write capability
U33 frontend filter renders the new option with no change to existing rendering
U34 full H1-H5 crown suites remain green, unmodified beyond §11's mechanical correction
U35 OQI4/OQI5/OQI6 tenant-isolation crowns (H4-R1/OQI6-R1-R3/OQI4-R1 precedent suites) remain green,
    unmodified
```

## 14. Performance crown (binding, I1-scoped, part of row 11 of §2)

`test_oqi_h6_uniqueness_crown.py` must include a dedicated adversarial scale test proving: candidate
generation for a tenant+entity_type population never issues a query pattern equivalent to a full
cross-population pairwise scan (asserted via a bounded query-count/row-count proof against a synthetic
population sized to make an accidental `O(N²)` path detectably slow or detectably wrong, not a production-
scale benchmark); the bucket-cap STOP-closed behavior (U9) is exercised at a population size that would
otherwise produce a combinatorially large candidate set; and this proof is independent of, not a
substitute for, U9's own correctness assertion.

## 15. Docker / runtime verification requirement (binding, mandatory for both I1 and I2)

Identical, unmodified discipline to every prior OQI phase (CDD-045 §"binding, mandatory", CDD-046 §45,
CDD-051 §45): real-PostgreSQL integration tests for every new table; a full Docker image build; Docker
Compose runtime startup with health checks passing; migration execution inside Docker, including the
`126 → 131 → 126 → 131` round-trip; demo seeder execution proving the H6 crown scenario (§4 row 13) derives
correctly from raw `EnterpriseEntity` facts through the real domain services, never a pre-scripted terminal
state. **A source-only green test suite is explicitly, permanently insufficient**, restated as binding here.

## 16. Acceptance criteria (binding)

I1 is acceptable only if: it implements exactly the schema and semantics frozen in CDD-084 §11-§29 and this
Authorization's §7-§9 without inventing new ones; it touches no path outside §2-§3; every composite FK in §9
is adversarially proven; U1-U20 pass against real PostgreSQL; whole-package `mypy app`/`black`/`isort`/`ruff`
are clean; the table-count correction (§11) is applied within I1, not deferred to I2. I2 is acceptable only
if: it touches no path outside §4; U21-U35 pass; the full H1-H5 crown remains green; Docker/Compose
verification (§15) passes for both phases before either is reported complete.

## 17. Authorization

This document is approved and published as the exact, binding path/schema/test authorization for
`OQI-H6-I1`/`OQI-H6-I2`, companion to `CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness.md`.
Implementation may proceed against exactly the paths, schema, and test matrix authorized above; any deviation
requires a narrow governance amendment, never a unilateral implementation-time decision.
