# CDD-050 OQI-H4 Governed Integrity — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-050-OQI-H4-Governed-Integrity.md` only. No wildcard, no directory-level
grant, no "related files" language. Any path not named below is unauthorized; if implementation discovers a
genuine need to touch an unnamed path, implementation must STOP and return for a narrow amendment, exactly
as the `OQI-H1-I-R1`/`OQI-H2-I-R1`/`OQI-H3-I-R1`/`OQI-H3-VM-R1` precedents established.

## 1. Accounting

```
CREATE = 18
MODIFY = 18
DELETE = 0
TOTAL  = 36
```

## 2. CREATE (18)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_integrity/__init__.py` | Package init. |
| 2 | `backend/app/domain/oqi_integrity/requirement.py` | `IntegrityRelationshipCardinality` domain dataclass, version/activation logic (CDD-050 §7), mirroring `CanonicalStandard`'s own versioning shape (CDD-049 §10). |
| 3 | `backend/app/domain/oqi_integrity/structural.py` | `IntegrityFindingType` StrEnum (shared, both subjects, CDD-050 §14); Structural evaluation/Finding dataclasses; deterministic identity derivation (CDD-050 §15); `apply_structural_finding_transition` (CDD-050 §16). |
| 4 | `backend/app/domain/oqi_integrity/reference.py` | Reference evaluation/Finding dataclasses; deterministic identity derivation; `apply_reference_finding_transition` (CDD-050 §16). |
| 5 | `backend/app/application/oqi_integrity_structural_evaluation_service.py` | Structural evaluator: `evaluate_current_state`, mirroring the existing OQI evaluator ordering discipline (derive identity → acquire advisory authority → select qualifying relationships → count distinct targets → compare against cardinality → persist idempotently → mutate Finding only when genuinely new), CDD-050 §10.1. |
| 6 | `backend/app/application/oqi_integrity_reference_evaluation_service.py` | Reference evaluator: `evaluate_current_state`, consuming a persisted `ResolutionOutcome` read-only, CDD-050 §10.2. Zero import from any ER matching-internal module beyond the read-only outcome lookup. |
| 7 | `backend/app/infrastructure/persistence/models/oqi_integrity.py` | ORM: `oqi_integrity_relationship_cardinalities`, `oqi_integrity_structural_evaluations`, `oqi_integrity_structural_evaluation_relationships`, `oqi_integrity_structural_findings`, `oqi_integrity_reference_evaluations`, `oqi_integrity_reference_findings` — exactly the six tables named in CDD-050 §12, no more. |
| 8 | `backend/app/infrastructure/persistence/oqi_integrity_requirement_repository.py` | Repository: CRUD/versioning for `IntegrityRelationshipCardinality`, dedicated advisory lock (CDD-050 §7). |
| 9 | `backend/app/infrastructure/persistence/oqi_integrity_structural_evaluation_repository.py` | Repository for Structural evaluation/Finding persistence, qualifying-relationship query (CDD-050 §10.1), evaluation-relationship link-table writes. |
| 10 | `backend/app/infrastructure/persistence/oqi_integrity_reference_evaluation_repository.py` | Repository for Reference evaluation/Finding persistence, read-only `ResolutionOutcome` lookup (CDD-050 §10.2). |
| 11 | `backend/app/infrastructure/persistence/migrations/versions/0034_oqi_h4_integrity_policy.py` | Migration: `oqi_integrity_relationship_cardinalities` (CDD-050 §23). |
| 12 | `backend/app/infrastructure/persistence/migrations/versions/0035_oqi_h4_integrity_structural.py` | Migration: `oqi_integrity_structural_evaluations`, `oqi_integrity_structural_evaluation_relationships`, `oqi_integrity_structural_findings` (CDD-050 §23). |
| 13 | `backend/app/infrastructure/persistence/migrations/versions/0036_oqi_h4_integrity_reference.py` | Migration: `oqi_integrity_reference_evaluations`, `oqi_integrity_reference_findings` (CDD-050 §23). |
| 14 | `backend/app/infrastructure/persistence/migrations/versions/0037_oqi_h4_impact_width.py` | Migration: widens `ontology_impact_evaluations.finding_family` and `current_ontology_impacts.finding_family` from `String(8)` to `String(16)` only (CDD-050 §20, §23). No other column, table, or semantic change. |
| 15 | `backend/app/tests/test_oqi_h4_integrity_crown.py` | Crown suite: Structural S1-S12, Reference O1-O8, Policy P1-P8, Dimension independence D1-D6, Origin/downstream F1-F8, H1/H2/H3 non-regression crown, H4 crown scenario (CDD-050 §26, §28). |
| 16 | `backend/app/tests/test_oqi_h4_integrity_authorization_and_tenant_isolation.py` | Tenant-isolation adversarial tests (T1-T5) and remediation/coverage/lifecycle tests (R1-R5, C1-C6, L1-L6) not already covered by row 15, mirroring `test_oqi_h3_authorization_and_tenant_isolation.py`'s established pattern. |
| 17 | `backend/app/tests/test_oqi_integrity_structural_evaluation_domain.py` | Domain-level unit tests for the Structural evaluation/Finding dataclasses, identity derivation, and transition function in isolation (no PostgreSQL), mirroring `test_oqi_cross_source_evaluation_domain.py`'s established precedent. |
| 18 | `backend/app/tests/test_oqi_integrity_reference_evaluation_domain.py` | Domain-level unit tests for the Reference evaluation/Finding dataclasses, identity derivation, and transition function in isolation, same precedent. |

## 3. MODIFY (18) — narrow, additive only

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/domain/oqi/quality_rule.py` | Add `INTEGRITY` to `QualityDimension` (CDD-050 §18). No change to `_ALLOWED_COMBINATIONS`, `QualityFindingType`, or any other member/row. |
| 2 | `backend/app/domain/oqi_finding_origin/origin.py` | Add `INTEGRITY` to `FindingStorageFamily` (CDD-050 §19). No change to `_OQI1_FINDING_TYPE_TO_DIMENSION`, `storage_family_from_finding_family`/`finding_family_from_storage_family`, or `resolve_finding_origin`'s existing dispatch shape (that logic lives in the repository, row 3 below, not here). |
| 3 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | Add exactly two narrow, additive methods, `resolve_integrity_structural_finding_origin`/`_subject` and `resolve_integrity_reference_finding_origin`/`_subject` (CDD-050 §20). No change to the existing `resolve_finding_subject`/`resolve_finding_origin` methods' signatures or behavior for `FindingFamily.OQI1/OQI2/OQI3`. |
| 4 | `backend/app/infrastructure/persistence/models/oqi_ontology_impact_evaluation.py` | Widen `finding_family: Mapped[str] = mapped_column(String(8), ...)` to `String(16)` on both `OntologyImpactEvaluationORM` and `CurrentOntologyImpactORM` (CDD-050 §20). No other column, class, or index change. |
| 5 | `backend/app/infrastructure/persistence/oqi_business_impact_repository.py` | `compute_subject_finding_state` gains exactly two new indirect-path `SELECT` branches (one for `oqi_integrity_structural_findings`, one for `oqi_integrity_reference_findings`), joined through the widened `CurrentOntologyImpactORM.finding_family == 'INTEGRITY'` (CDD-050 §22), mirroring the three existing indirect-path branches' exact shape. No change to the three existing direct-path branches, the three existing indirect-path branches, or any other method. |
| 6 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | `has_qualifying_coverage_for_dimension` gains exactly one new branch, `INTEGRITY`, an existence-only, subject-scoped qualifying-evaluation query across both new evaluation tables (CDD-050 §24). No change to any other branch or the unconditional-`False` fallback for `UNIQUENESS`/`TIMELINESS`. |
| 7 | `backend/app/application/oqi_remediation_service.py` | `extract_candidates` gains one additional `quality_dimension == "INTEGRITY"` dispatch branch returning zero candidates, mirroring the existing `REASONABLENESS` branch exactly (CDD-050 §25). No change to any other branch. |
| 8 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | Add the H4 crown scenario (CDD-050 §28): one `IntegrityRelationshipCardinality` row anchored to the real, existing `assembledAt` `RelationshipRequirement`; real `EnterpriseEntity`/`InstitutionalRelationship` rows for scenarios A/B/C; one `ResolutionOutcome.UNRESOLVED` record for scenario D. No modification to any existing seeded H1/H2/H3 fixture, invocation, or crown scenario's own values. No direct insertion of Integrity evaluation/Finding rows (CDD-050 §34 — must arise through the real services, rows 5-6 above). |
| 9 | `.github/workflows/ci.yml` | Exactly one change: the table-count assertion, `114` → `120` (message text included). No other CI change. |
| 10 | `backend/app/tests/test_oqi_business_rule_postgres.py` | Mechanical only: table-count literal, `114` → `120`. |
| 11 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | Mechanical only: table-count literal, `114` → `120`. |
| 12 | `backend/app/tests/test_persistence_integration.py` | Mechanical only: table-count literal, `114` → `120`. |
| 13 | `backend/app/tests/test_oqi_business_impact.py` | Mechanical only: table-count literal, `114` → `120`. |
| 14 | `backend/app/tests/test_oqi_remediation_agent_i2.py` | Mechanical only: table-count literal, `114` → `120`. |
| 15 | `backend/app/tests/test_oqi_remediation_i1.py` | Mechanical only: table-count literal, `114` → `120`. |

**Pre-authorization rationale for rows 10-15 (binding disclosure)**: independently re-verified this phase
via fresh `grep` against merged main — these six files, and only these six, currently hardcode the literal
`114`. This mirrors the identical, already-established `OQI-H1-I-R1`/`OQI-H2-I-R1`/`OQI-H3` precedent
exactly (the identical six-file set, table-count literal only, each time). **Authorization is strictly
limited to the bare numeric literal change (`114`→`120`) and any adjoining message text** — no other line in
any of these six files may change under this authorization.

**Rows 16-18, closely related to the coverage/architecture-firewall precedent, disclosed here rather than
folded into rows 10-15**: `backend/app/tests/test_oqi_quality_coverage_policy_domain.py`'s exact-
`QualityDimension`-member-count assertion (`5` → `6`, mirroring the identical correction H3-I-R1 already
made for `4` → `5`); `backend/app/tests/test_oqi_quality_coverage_policy_service.py`'s new `INTEGRITY`
coverage-dispatch test (mirroring the existing `CONFORMITY`-dispatch test H3 added); and
`test_runtime_architecture.py`'s construction-site firewall extension.

| 16 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | MODIFY: update the exact `QualityDimension` member-count/value-set assertion from 5 to 6 members including `"INTEGRITY"` (CDD-050 §18). No other test in this file may change. |
| 17 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | MODIFY: add one new test, `test_integrity_dispatches_to_integrity_evaluation_repositories`, mirroring `test_conformity_dispatches_to_conformity_evaluation_repository`'s exact structure (CDD-050 §24). No other test in this file may change. |
| 18 | `backend/app/tests/test_runtime_architecture.py` | MODIFY: add the six new construction sites (`oqi_integrity_requirement_repository.py`, `oqi_integrity_structural_evaluation_repository.py`, `oqi_integrity_reference_evaluation_repository.py`) to the expected construction-site lists for every new ORM class they construct, mirroring H3's own Conformity firewall-extension precedent exactly. No other test in this file may change. |

## 4. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized, called out because a reasonable implementer might assume
otherwise: any Keycloak realm file (no new authority scope is authorized, CDD-050 §26); `backend/app/api/`
or any frontend file (no API/UI change is authorized, CDD-050 §33, unless H4-I discovers a genuine closed-
enum mismatch, which requires its own narrow amendment exactly as this Authorization's own precedent
chain requires); `backend/app/domain/oqi_remediation/candidate.py` (no new `RemediationCandidateBasis`
member — CDD-050 §25 explicitly requires zero change here, mirroring the Reasonableness precedent);
`backend/app/domain/oqi_remediation/authorization.py` (`RemediationActionType` stays closed to
`UPDATE_FIELD`, CDD-050 §25); `backend/app/domain/blueprint/model.py` or any Blueprint/`RelationshipRequirement`
domain/persistence/repository file (reused unmodified, CDD-050 §5-§6); `backend/app/domain/identity_
resolution/` or any ER-internal module (Integrity is read-only against `ResolutionOutcome`, CDD-050 §10.2 —
any need to touch it is itself a STOP, not a MODIFY); `backend/app/domain/integration/field_value_evidence.py`
or its repository (no mutation path of any kind, CDD-050 §29); `backend/app/application/oqi_accuracy_
evaluation_service.py`, `oqi_conformity_evaluation_service.py`, or any file in Accuracy's/Conformity's own
comparison path (CDD-050 §29); any file implementing `UNIQUENESS` or `TIMELINESS`; any production
orchestration/scheduler/event-trigger file; any Command Center or dashboard file; `architecture/INDEX.md`
(this OQI CDD track has never registered there, confirmed precedent — CDD-044 through CDD-049 are likewise
absent); `docs/product/` (explicitly out of scope, untouched throughout every prior phase).

**Advisory lock seed registry**: the new `IntegrityRelationshipCardinality`/Structural/Reference evaluation
repositories each require their own dedicated advisory-lock seed, distinct from every existing OQI1-6/H1-H3
seed — the exact integer is an implementation-time detail (CDD-046 §39's own precedent for exactly this
class of deferral), disclosed in H4-I's own final report, never silently reused.

## 5. Migration

```
Expected revision (0034): 0034_oqi_h4_integrity_policy       (28 chars)
Expected down_revision:    0033_oqi_h3_consistency_proj
Expected revision (0035): 0035_oqi_h4_integrity_structural    (32 chars)
Expected down_revision:    0034_oqi_h4_integrity_policy
Expected revision (0036): 0036_oqi_h4_integrity_reference     (31 chars)
Expected down_revision:    0035_oqi_h4_integrity_structural
Expected revision (0037): 0037_oqi_h4_impact_width            (24 chars)
Expected down_revision:    0036_oqi_h4_integrity_reference

Pre-H4 table count:    114 (VERIFIED FRESH this phase — real-PostgreSQL-confirmed against
                             e87bb29580952ab05b0879100511f70f88523fc4, tree-identical to origin/main
                             5bf3e70a8a0cd2f94b78b262f231d3ffc7d3d9f5)
Post-0034 table count:  115  (+ oqi_integrity_relationship_cardinalities)
Post-0035 table count:  118  (+ oqi_integrity_structural_evaluations,
                                oqi_integrity_structural_evaluation_relationships,
                                oqi_integrity_structural_findings)
Post-0036 table count:  120  (+ oqi_integrity_reference_evaluations, oqi_integrity_reference_findings)
Post-0037 table count:  120  (column-width change only, zero new tables)
Final expected table count: 120
```

Required round-trip: `114 → 115 → 118 → 120 → 120 → 118 → 115 → 114 → 120` (each migration's own
upgrade/downgrade/re-upgrade proven independently, then the full four-migration chain proven together, per
CDD-050 §23). Single Alembic head required at all times. No migration beyond the four named here is
authorized.

## 6. Implementation shape

Single implementation phase (`OQI-H4-I`) is expected, mirroring H1/H2/H3-I's shape. A split is permitted
only if each sub-phase independently satisfies this Artifact Authorization's exact path list and migration
ordering — introducing a genuinely new intermediate migration revision to accommodate a split is itself a
STOP-worthy governance return, not a decision implementation may make unilaterally.

## 7. API / Frontend

**None authorized** (CDD-050 §33). If H4-I discovers a genuine closed-enum/label mismatch in the frontend
that would render Integrity Findings incorrectly, that discovery is itself a STOP requiring a narrow
amendment — not a license to fix it inline under this Authorization.

## 8. Mandatory test matrix (binding on the four new test files, rows 15-18 of §2)

Every category CDD-050 §26 names must be proven, tied to the exact CDD-050 section it verifies: Structural
S1-S12; Reference O1-O8; Policy P1-P8; Dimension independence D1-D6; Origin/downstream F1-F8; Coverage
C1-C6; Finding lifecycle L1-L6; Remediation R1-R5; Tenancy T1-T5; ER boundary E1-E4; Migration M1-M8;
Static/architecture A1-A8; Docker X1-X12; H1/H2/H3 regression G1-G8. Full regression suite (all pre-existing
OQI1-H3 tests) must still pass unmodified. Whole-package `mypy app` must be clean (CDD-050 §32). Docker/
Compose/demo-seeder runtime proof required before any claim of H4-I completion.
