# CDD-086 Generic Finding Detail Parity — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-086-Generic-Finding-Detail-Parity.md` only. No wildcard, no
directory-level grant, no "and related files" language. Any path not named below is unauthorized; if
implementation discovers a genuine need to touch an unnamed path, implementation must STOP and return for a
narrow amendment, exactly as every prior phase in this program requires.

## 1. Accounting

```
CREATE = 1
MODIFY = 1
DELETE = 0
TOTAL  = 2
```

## 2. CREATE (1)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/tests/test_generic_finding_detail_parity.py` | The P1-P30 crown suite (§5 below) proving list->detail parity for Integrity, Timeliness, and Uniqueness, honest degradation of every downstream tab, and zero regression to OQI1/OQI2/OQI3 or the dedicated Uniqueness pair-detail endpoint. |

## 3. MODIFY (1)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/application/oqi_product_experience_service.py` | (a) Extend `_resolve_finding()` with four new branches — `IntegrityStructuralFindingORM`, `IntegrityReferenceFindingORM`, `TimelinessFindingORM`, `UniquenessFindingORM` — mirroring `list_findings()`'s own existing query and `condition_label` logic for each, each branch tenant-scoped exactly as the three existing branches already are (CDD-086 §8-§9). (b) Extend entity/subject resolution feeding `get_business_impact`/`get_reliance` for these same four branches to route through the already-existing `resolve_integrity_structural_finding_subject`/`resolve_integrity_reference_finding_subject`/`resolve_timeliness_finding_subject`/`resolve_uniqueness_finding_subject` methods on `OqiBusinessImpactRepositoryImpl` — the existing `FindingFamily`-typed `_resolve_entity`/`resolve_finding_subject` path is never called with a non-`FindingFamily` value (CDD-086 §10). (c) Guard the three existing `RemediationFindingFamily(finding.family.value)` call sites (`get_evidence`, `get_agent_investigation`, `get_remediation`) to skip that construction and the dependent case/candidate lookup when the resolved family is not `OQI1`/`OQI2`/`OQI3`, returning each method's own already-existing empty/unsupported result type instead (CDD-086 §11/§15/§16/§18). No change to `get_ontology_impact()` (CDD-086 §12). No change to `get_uniqueness_candidate_detail()` (CDD-086 §19). No change to `list_findings()`'s own logic, to any of the three original `_resolve_finding()` branches, to any router, model, migration, or frontend file. No formatting churn outside the necessary local edits. |

## 4. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized: `backend/app/api/oqi/router.py` or any router file (the route
handler purely delegates to the service; no per-family dispatch exists there and none is authorized to be
added); any frontend file (CDD-086 §20 — zero frontend change required or authorized); any migration file
(CDD-086 §21); any model file under `backend/app/infrastructure/persistence/models/` (the fix is dispatch
logic only, never a schema or mapped-class change); `app/domain/oqi_ontology_impact/evaluation.py` or
`app/domain/oqi_remediation/case.py` (their `FindingFamily` enums remain closed, CDD-086 §17 — no broadening
authorized); `app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` (`resolve_finding_subject`
remains unmodified, closed to OQI1-3, CDD-086 §10); `app/infrastructure/persistence/oqi_business_impact_repository.py`
(its existing per-family resolvers are consumed, not modified); any H1-H6/Integrity/Timeliness/Uniqueness
evaluator, domain, or persistence file (CDD-086 §22 — zero OQI semantic change); `docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md`
or any path under `product/noetva-demo-readiness-i` (CDD-086 §29-§30 — that candidate is untouched by this
independent correction); any file under `docs/product/` whatsoever — zero exception.

## 5. Migration

**None authorized.** CDD-086 §21/§24 requires a STOP if any migration is found necessary. Table count and
migration head (`0047_oqi_h6_uniqueness`) remain unchanged by this phase.

## 6. Test matrix — P1-P30 (binding)

Binding on `backend/app/tests/test_generic_finding_detail_parity.py` (§2 row 1):

```
P1   ORPHAN_REFERENCE is returned by generic list.
P2   The exact ORPHAN_REFERENCE finding_id opens through generic detail.
P3   RELATIONSHIP_CARDINALITY_VIOLATION is returned by generic list.
P4   Its exact finding_id opens through generic detail.
P5   MISSING_REQUIRED_RELATIONSHIP is returned by generic list.
P6   Its exact finding_id opens through generic detail.
P7   STALE_SOURCE_EVIDENCE (Timeliness) is returned by generic list.
P8   Its exact finding_id opens through generic detail.
P9   DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE (Uniqueness) is returned by generic list.
P10  Its exact finding_id opens through generic detail.
P11  Wrong-tenant lookup for each newly-supported storage family returns not-found (404 at the API layer /
     None at the service layer) -- no cross-tenant leak.
P12  An unknown random UUID remains not-found for every newly-supported family's lookup path.
P13  Existing OQI1 detail remains unchanged (byte-identical ResolvedFinding shape/values to pre-correction).
P14  Existing OQI2 detail remains unchanged.
P15  Existing OQI3 detail remains unchanged.
P16  Integrity Evidence does not crash (no RemediationFindingFamily ValueError); returns empty participants,
     candidate=None.
P17  Integrity Ontology Impact honestly returns IMPACT_UNKNOWN (no OQI4 evaluation exists for this family;
     never reinterpreted as NO_IMPACT).
P18  Integrity Business Impact does not crash; returns real dependency data if one resolves, else the
     existing honest BUSINESS_IMPACT_UNKNOWN -- never fabricated.
P19  Integrity Reliance does not crash; returns real Reliance data if it resolves, else the existing honest
     RELIANCE_UNKNOWN -- never fabricated, never hardcoded to AT_RISK.
P20  Integrity Agent Investigation is honestly empty (specialists=(), recommendation=None) -- no
     RemediationFindingFamily crash, no seeded output.
P21  Integrity Remediation returns the honest no-case result (case_status=None, candidate=None, ...) -- no
     fabricated case.
P22  Timeliness Evidence/Ontology-Impact/Business-Impact/Reliance/Agent/Remediation do not crash (mirrors
     P16-P21 for the Timeliness family).
P23  A real Timeliness Finding whose entity has a genuine governed dependency shows real
     BUSINESS_IMPACT_IDENTIFIED/RELIANCE_AT_RISK data (reproducing the DR's own empirical result) -- proving
     the extension surfaces real data, not just avoids crashing.
P24  Timeliness Agent/Remediation return the honest empty/no-case result -- no fabricated capability.
P25  Uniqueness generic detail (GET /findings/{finding_id}) opens successfully.
P26  The dedicated Uniqueness pair-detail endpoint (get_uniqueness_candidate_detail /
     /api/v1/oqi/uniqueness-candidates/{finding_id}) is unaffected -- byte-identical behavior to
     pre-correction.
P27  Uniqueness generic Agent/Remediation return the honest empty/no-case result -- no fabricated capability,
     no interference with H6's own separate adjudication semantics.
P28  list_findings()'s own result set and per-row semantics (finding_id, condition_label, status,
     affected_entity_id, highest_criticality, reliance_state) are byte-identical before and after this
     correction for every family.
P29  No migration/schema drift -- table count and migration head unchanged.
P30  A genuinely fresh Docker environment (fresh Postgres, fresh migrate, real seed, real API calls through
     GET /api/v1/oqi/findings then GET /api/v1/oqi/findings/{finding_id}) reproduces list->detail parity for
     Integrity, Timeliness, and Uniqueness identically to the host-level proof.
```

## 7. API-level and downstream-tab verification (binding, restated)

Implementation/VM must verify through the actual HTTP API (`GET /api/v1/oqi/findings` then
`GET /api/v1/oqi/findings/{finding_id}`), not only direct service-method calls, for at least one Finding of
each of: Integrity reference, Integrity structural, Timeliness, Uniqueness. For at least one representative
newer-family Finding, every downstream tab's actual API/service call (`evidence`, `ontology impact`,
`business impact`, `reliance`, `agent investigation`, `remediation`) must be exercised directly — zero 500,
zero enum-conversion crash, zero fabricated state.

## 8. Acceptance criteria (binding)

Implementation is acceptable only if: it touches no path outside §2-§3; P1-P29 pass against real PostgreSQL;
P30 passes in a genuinely fresh Docker environment; every existing OQI1-6/H1-H6/Timeliness/Uniqueness test
remains green, unmodified in count or outcome beyond this new file; whole-package `mypy`/`black`/`isort`/`ruff`
are clean; zero migration is introduced; the full backend and frontend regression suites are run and reported
honestly (the pre-existing whole-suite isolation characteristic, DR-classified UNRELATED, must not be
silently called "green" if still present — report actual counts).

## 9. Authorization

This document is approved and published as the exact, binding path/schema/test authorization for Generic
Finding Detail Parity implementation, companion to `CDD-086-Generic-Finding-Detail-Parity.md`. Implementation
may proceed against exactly the paths, schema, and test matrix authorized above; any deviation requires a
narrow governance amendment, never a unilateral implementation-time decision.
