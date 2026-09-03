# CDD-049 OQI-H3 Governed Conformity and Canonical Standards — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-049-OQI-H3-Governed-Conformity-and-Canonical-Standards.md` only. No
wildcard, no directory-level grant, no "related files" language. Any path not named below is
unauthorized; if implementation discovers a genuine need to touch an unnamed path, implementation must
STOP and return for an amendment, exactly as the `OQI-H1-I-R1`/`OQI-H1-CI`/`OQI-H2-I-R1` precedents did.

## 1. Accounting

```
CREATE = 10
MODIFY = 18
DELETE = 0
TOTAL  = 28
```

## 2. CREATE (10)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_canonical_standard/standard.py` | `CanonicalStandard`/`CanonicalValue`/`CanonicalAlias` domain shapes, versioning/activation logic (CDD-049 §9-§12); `CanonicalizationResult` value object and the pure, deterministic resolver function (CDD-049 §13) — zero import from `identity_resolution/normalization.py` or any ER-internal module (CDD-049 §35 STOP condition 4). |
| 2 | `backend/app/infrastructure/persistence/models/oqi_canonical_standard.py` | ORM: `oqi_canonical_standards`, `oqi_canonical_standard_values`, `oqi_canonical_standard_aliases`, `oqi_quality_evaluation_canonical_standard`, `oqi_comparison_participant_canonical_projection` (CDD-049 §10-§11, §15, §17) — exactly the five tables named in §27, no more. |
| 3 | `backend/app/infrastructure/persistence/oqi_canonical_standard_repository.py` | Repository: CRUD/versioning for `CanonicalStandard`/value/alias, the deterministic resolution query (Information Element → ACTIVE standard, CDD-049 §8), the canonicalization lookup (CDD-049 §11-§13). |
| 4 | `backend/app/infrastructure/persistence/oqi_conformity_evaluation_repository.py` | Repository for Conformity evaluation persistence (reusing `quality_evaluations`/`quality_findings`, CDD-049 §14), pinning the consulted `CanonicalStandard` version via `oqi_quality_evaluation_canonical_standard` (CDD-049 §15), mirroring `oqi_accuracy_evaluation_repository.py`'s exact structural shape. |
| 5 | `backend/app/application/oqi_conformity_evaluation_service.py` | Conformity evaluator: `evaluate_current_state`, mirroring `OqiAccuracyEvaluationService`'s exact ordering discipline (CDD-049 §14): derive Finding identity → acquire advisory authority → select evidence → resolve `information_element_requirement_id` → resolve ACTIVE `CanonicalStandard` → canonicalize → compare → persist idempotently. |
| 6 | `backend/app/infrastructure/persistence/migrations/versions/0031_oqi_h3_canonical_standard.py` | Migration: `oqi_canonical_standards`, `oqi_canonical_standard_values`, `oqi_canonical_standard_aliases` (CDD-049 §10-§11, §28). |
| 7 | `backend/app/infrastructure/persistence/migrations/versions/0032_oqi_h3_conformity_evidence.py` | Migration: `oqi_quality_evaluation_canonical_standard` (CDD-049 §15, §28). |
| 8 | `backend/app/infrastructure/persistence/migrations/versions/0033_oqi_h3_consistency_projection.py` | Migration: `oqi_comparison_participant_canonical_projection` (CDD-049 §17, §28). |
| 9 | `backend/app/tests/test_oqi_h3_conformity_crown.py` | Crown suite: Conformity (C1-C10), Consistency/canonicalization (K1-K10), Validity interaction (V1-V3), Accuracy non-interference (A1-A3, live), origin/downstream (F1-F5), coverage (CV1-CV5), remediation (R1-R4), ER boundary (E1-E2), H2 non-regression crown, H3 crown scenario (CDD-049 §30-§33). |
| 10 | `backend/app/tests/test_oqi_h3_authorization_and_tenant_isolation.py` | Authorization-separation and tenant-isolation adversarial tests for `oqi-canonical-standard:configure` and shared-standard read access (CDD-049 §9, §25, §32 T1-T3), mirroring `test_oqi_h2_authorization_and_tenant_isolation.py`'s established pattern. |

## 3. MODIFY (18) — narrow, additive only

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/domain/oqi/quality_rule.py` | Add `CONFORMITY` to `QualityDimension` (CDD-049 §4); add `NON_CANONICAL_REPRESENTATION` to `QualityFindingType`; add the one `(CONFORMITY, NON_CANONICAL_REPRESENTATION, None)` row to `_ALLOWED_COMBINATIONS`; add `_validate_conformity_parameters` following `_validate_accuracy_parameters`'s exact shape (rule_parameters must be empty, CDD-049 §6). No change to `COMPLETENESS`/`VALIDITY`/`CONSISTENCY`/`ACCURACY` rows, no change to `information_element_requirement_id`'s existing field shape or validation. |
| 2 | `backend/app/domain/oqi_finding_origin/origin.py` | Add exactly one entry to `_OQI1_FINDING_TYPE_TO_DIMENSION`: `NON_CANONICAL_REPRESENTATION -> CONFORMITY` (CDD-049 §14, §20). No change to `FindingStorageFamily`, `storage_family_from_finding_family`/`finding_family_from_storage_family`, or any other mapping entry. |
| 3 | `backend/app/application/oqi_cross_source_evaluation_service.py` | `_select_participant_evidence_and_evaluate` gains the G0 canonicalization-gate algorithm exactly as frozen (CDD-049 §16): resolve the applicable `CanonicalStandard` for the comparison's Information Element; Case A (no standard) unchanged; Case B canonicalizes every known participant and either compares canonical projections or produces the `NOT_EVALUABLE`-for-value-agreement outcome per §16.1-§16.2, never suppressing the existing, independent missingness computation. No change to authority acquisition ordering, idempotent-insert discipline, or Finding-identity derivation. |
| 4 | `backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py` | Add a narrow, additive method persisting `oqi_comparison_participant_canonical_projection` rows (CDD-049 §17) alongside an evaluation insert, invoked only when Case B's canonical projection was actually used. No change to any existing method's behavior or return shape. |
| 5 | `backend/app/domain/oqi_remediation/candidate.py` | Add exactly one new `RemediationCandidateBasis` member: `CONFORMITY_CANONICAL_STANDARD` (CDD-049 §24). Add `extract_conformity_candidates`, mirroring `extract_accuracy_candidates`'s exact signature shape. No change to the existing six members or `__post_init__` validation shape. |
| 6 | `backend/app/application/oqi_remediation_service.py` | `extract_candidates` gains one additional `quality_dimension == "CONFORMITY"` dispatch branch calling `_extract_conformity_candidates` (mirroring the existing `_extract_accuracy_candidates` branch exactly, CDD-049 §24). No change to any other branch. |
| 7 | `backend/app/infrastructure/persistence/oqi_remediation_repository.py` | Add `get_conformity_candidate_support`, a narrow, additive, read-only method (explicitly not on the `OqiRemediationRepository` Protocol, mirroring the established `get_accuracy_candidate_support` precedent). No change to any existing method. |
| 8 | `backend/app/infrastructure/persistence/oqi_quality_coverage_policy_repository.py` | `has_qualifying_coverage_for_dimension` gains exactly one new branch, `CONFORMITY`, an existence-only qualifying-evaluation query mirroring the `ACCURACY` branch exactly (CDD-049 §21). No change to any other branch or the unconditional-`False` fallback for `UNIQUENESS`/`TIMELINESS`/`INTEGRITY`. |
| 9 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | Add the H3 crown scenario (CDD-049 §30): seed the `CanonicalStandard` (canonical `USA`, alias `US`), the PLM `"USA"` observation, invoke the new Conformity/canonical-projection-aware Consistency evaluators. No change to any existing seeded OQI1/OQI2/OQI3/Accuracy/Reasonableness fixture, invocation, or the H2 crown scenario's own raw values (CDD-049 §31 — SAP `"US"`/PLM `"MX"`/Reference `"US"` unchanged). |
| 10 | `keycloak/ctec-realm.json` | Add exactly one new `clientScope` entry, `oqi-canonical-standard:configure` (description ≤255 chars, verified before commit — CDD-049 §25), plus its one `optionalClientScopes` reference. No other realm/client configuration may change; no scope becomes `default`. |
| 11 | `.github/workflows/ci.yml` | Exactly two changes (CDD-049 §29, Option A, frozen — no `oqi-reference-evidence:*` scope-proof addition authorized): (a) the table-count assertion, `109` → `114` (message text included); (b) one new scope-check line proving `oqi-canonical-standard:configure` is present and `optional` (never `default`), mirroring the existing `oqi-remediation:*` lines exactly. No other CI change. |
| 12 | `backend/app/tests/test_oqi_api_postgres.py` | Mechanical only: table-count literal, `109` → `114`. |
| 13 | `backend/app/tests/test_oqi_business_impact.py` | Mechanical only: table-count literal, `109` → `114`. |
| 14 | `backend/app/tests/test_oqi_business_rule_postgres.py` | Mechanical only: table-count literal, `109` → `114`. |
| 15 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | Mechanical only: table-count literal, `109` → `114`. |
| 16 | `backend/app/tests/test_oqi_remediation_agent_i2.py` | Mechanical only: table-count literal, `109` → `114`. |
| 17 | `backend/app/tests/test_oqi_remediation_i1.py` | Mechanical only: table-count literal, `109` → `114`. |
| 18 | `backend/app/tests/test_persistence_integration.py` | Mechanical only: table-count literal, `109` → `114`. |

**Pre-authorization rationale for rows 12-18 (binding disclosure)**: independently re-verified this
phase via fresh `grep` against merged main — these seven files, and only these seven, currently hardcode
the literal `109`. This Artifact Authorization pre-authorizes their mechanical re-pin now, specifically
to avoid repeating the exact discovery-after-implementation pattern that required the
`OQI-H1-I-R1`/`OQI-H2-I-R1` retroactive-authorization amendments — the governing prompt for this phase
explicitly instructed against repeating that pattern for CI, and the identical reasoning applies to these
structurally identical table-count literals. **Authorization is strictly limited to the bare numeric
literal change (`109`→`114`) and any adjoining message text** — no other line in any of these seven files
may change under this authorization; a genuine semantic/behavioral change discovered in any of them
during implementation requires its own STOP and amendment, exactly as any other unnamed path would.

## 4. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized, called out because a reasonable implementer might assume
otherwise: `backend/app/api/oqi/router.py` or `backend/app/api/oqi/schemas.py` (no CanonicalStandard API
of any kind is authorized, CDD-049 §26); any frontend file, including
`frontend/app/quality/findings/page.tsx`'s family-filter dropdown label (CDD-049 §26, explicitly
deferred cosmetic item); `backend/app/domain/identity_resolution/normalization.py` or any other ER
module (CDD-049 §35 STOP condition 4 — any need to touch it is itself a STOP, not a MODIFY);
`backend/app/domain/oqi_business_rule/rule.py` or `BusinessRulePurpose` (Conformity joins
`QualityDimension`, never `BusinessRulePurpose`, CDD-049 §4); `backend/app/application/oqi_accuracy_evaluation_service.py`
or any file in Accuracy's own comparison path (CDD-049 §18 — PO-H3-02, absolute); `backend/app/domain/integration/field_value_evidence.py`
or its repository (CDD-049 §35 STOP condition 3 — no mutation path of any kind); any file implementing
`UNIQUENESS`, `TIMELINESS`, or `INTEGRITY`; any tenant-CanonicalStandard-override mechanism (PO-H3-03);
any semantic/unit-conversion logic; `oqi-reference-evidence:*` CI scope-proof addition (CDD-049 §29,
explicitly deferred, not H3's to repair); `oqi-coverage:configure`/`oqi-quality-rule:configure` wiring
(pre-existing, unrelated); any production orchestration/scheduler/event-trigger file; any Command Center
or dashboard file; `architecture/INDEX.md` or any release-manifest file (this OQI CDD track has never
registered there, confirmed precedent — CDD-044 through CDD-048 are likewise absent); `docs/product/`
(explicitly out of scope, untouched throughout H3-DR and H3-G).

**Advisory lock seed registry**: `OqiConformityEvaluationService` reuses the existing OQI1 advisory-lock
discipline (Conformity, being OQI1-shaped, uses the existing seed `1`, identical to Completeness/Validity/
Accuracy) — no new advisory-lock seed is authorized or required for Conformity evaluation itself. The
Consistency canonical-projection provenance write (row 4, §3) participates in OQI2's own existing
transaction/authority scope — no new seed is authorized or required there either.

## 5. Migration

```
Expected revision (0031): 0031_oqi_h3_canonical_standard      (30 chars)
Expected down_revision:    0030_oqi_h2_reasonableness
Expected revision (0032): 0032_oqi_h3_conformity_evidence      (32 chars)
Expected down_revision:    0031_oqi_h3_canonical_standard
Expected revision (0033): 0033_oqi_h3_consistency_projection    (33 chars — EXCEEDS the 32-char Alembic
                                                                  limit. IMPLEMENTATION MUST SHORTEN
                                                                  this exact revision id before use —
                                                                  e.g. "0033_oqi_h3_consistency_proj"
                                                                  (29 chars) — following the identical
                                                                  precedent CDD-048's own 0030 migration
                                                                  required (H2-I shortened
                                                                  "0030_oqi_h2_reasonableness_dimension"
                                                                  to "0030_oqi_h2_reasonableness" for
                                                                  the same reason). This document
                                                                  authorizes the shortened form; the
                                                                  exact final string is an
                                                                  implementation-time mechanical
                                                                  detail, not a fresh governance
                                                                  decision, exactly as CDD-048's own
                                                                  precedent establishes.)

Pre-H3 table count:   109 (VERIFIED FRESH this phase — real-PostgreSQL-confirmed against
                            e42ee7987bb862e55b150d29eeb727c93ec9ac47)
Post-0031 table count: pre-count + 3   (oqi_canonical_standards, oqi_canonical_standard_values,
                                        oqi_canonical_standard_aliases)
Post-0032 table count: post-0031 + 1   (oqi_quality_evaluation_canonical_standard)
Post-0033 table count: post-0032 + 1   (oqi_comparison_participant_canonical_projection)
Final expected table count: 114
```

Required round-trip: `109 → 112 → 113 → 114 → 113 → 112 → 109` (each migration's own upgrade/downgrade/
re-upgrade proven independently, then the full three-migration chain proven together per CDD-049 §28).
Single Alembic head required at all times. No migration beyond the three named here is authorized.

## 6. Implementation shape

Single implementation phase (`OQI-H3-I`) is expected, mirroring H2-I's shape. A split is permitted only
if each sub-phase independently satisfies this Artifact Authorization's exact path list and migration
ordering — introducing a genuinely new intermediate migration revision to accommodate a split is itself a
STOP-worthy governance return, not a decision implementation may make unilaterally.

## 7. API / Frontend

**None authorized.** CDD-049 §26 is explicit and absolute: no CanonicalStandard read/configure route, no
Finding-detail schema change (the existing `dimension: str` field already accepts the new value with zero
change), no frontend file of any kind, including the one named, explicitly-deferred cosmetic label item.

## 8. Mandatory test matrix (binding on the 2 new test files, rows 9-10)

Every category named in CDD-049 §33 must be proven, tied to the exact CDD section it verifies: Conformity
C1-C10; Consistency/canonicalization K1-K10 (including the mixed-participant-state resolution, §16.2, and
the historical-Finding-lifecycle resolution, §16.5 — both adversarially proven, not merely asserted);
Validity independence V1-V3; Accuracy non-interference A1-A3 (A1 specifically proven **live**, against a
database state where an H3 `CanonicalStandard` genuinely exists for the same Information Element H2's own
crown evaluates); origin/downstream F1-F5; coverage CV1-CV5; remediation R1-R4; tenancy/authority T1-T3;
ER boundary E1-E2 (E1 via static AST import-firewall, mirroring CDD-048's own CY3-CY5 precedent exactly;
E2 via an adversarial construction proving no live code path can substitute ER normalization for
Conformity's own resolver); full regression suite (all pre-existing OQI1-H2 tests) must still pass
unmodified; the H2 non-regression crown (CDD-049 §31) proven live in the same database state as the H3
crown scenario; Docker/Compose/demo-seeder runtime proof (CDD-049 §33 D1-D10) required before any claim
of H3-I completion.
