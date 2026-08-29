# CDD-042 Ontology Impact Intelligence — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** exact OQI4-I implementation surface. No wildcard authorization. No directory-level grant. Any path not named below is unauthorized — OQI4-I must STOP and return for a governance amendment rather than touch it.

## 1. Accounting

```
CREATE = 12
MODIFY = 9
DELETE = 0
TOTAL  = 21
```

## 2. CREATE (12)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_ontology_impact/__init__.py` | package marker |
| 2 | `backend/app/domain/oqi_ontology_impact/policy.py` | `ImpactPropagationPolicy` domain dataclass, direction enum, validation |
| 3 | `backend/app/domain/oqi_ontology_impact/evaluation.py` | `OntologyImpactEvaluation`, `OntologyImpactObservation`, `OntologyImpactPath`, `CurrentOntologyImpact` domain dataclasses; identity derivation functions (CDD-042 §11); Finding-family adapter type (`FindingFamily` enum + composite reference, CDD-042 §10) |
| 4 | `backend/app/infrastructure/persistence/models/oqi_ontology_impact_policy.py` | `ImpactPropagationPolicyORM` |
| 5 | `backend/app/infrastructure/persistence/models/oqi_ontology_impact_evaluation.py` | `OntologyImpactEvaluationORM`, `OntologyImpactObservationORM`, `OntologyImpactPathORM`, `CurrentOntologyImpactORM` |
| 6 | `backend/app/infrastructure/persistence/oqi_ontology_impact_policy_repository.py` | policy CRUD + ACTIVE-version lookup |
| 7 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | Finding-family adapter lookups; direct-impact resolution-record lookup; the single recursive-CTE propagation statement (CDD-042 §9); parent-gated idempotent Evaluation/Observation/Path insert; current-impact upsert |
| 8 | `backend/app/application/oqi_ontology_impact_evaluation_service.py` | orchestration: load Finding via adapter → resolve direct impact → run recursive-CTE propagation → derive outcome → persist → update current projection |
| 9 | `backend/app/infrastructure/persistence/migrations/versions/0023_oqi4_ontology_impact.py` | creates the 5 tables in CDD-042 §8/§11; `revision="0023_oqi4_ontology_impact"`, `down_revision="0022_oqi3_business_rule"` |
| 10 | `backend/app/tests/test_oqi_ontology_impact_domain.py` | domain construction, identity formulas, validation, Finding-family adapter |
| 11 | `backend/app/tests/test_oqi_ontology_impact_service.py` | fake-repo orchestration: direct impact per Finding family (§4.5/§4.6), IMPACT_UNKNOWN/NO_IMPACT cases, lifecycle (OPEN/RESOLVED/REOPENED), firewalls |
| 12 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | real-Postgres: recursive-CTE traversal (allowed/denied edge, multi-hop, cycle, multi-path, depth cap), release-blocking writer-during-CTE-statement test, policy-in-same-statement test, concurrent replay, tenant/SourceObject isolation, migration round-trip, bounded-graph performance sanity test |

## 3. MODIFY (9) — migration-head-literal mechanical regressions only

Every row below is bounded to exactly one change: updating the file's existing expected-Alembic-head literal (and, for row 4, the expected table-count literal) from `0022_oqi3_business_rule` / `81` to `0023_oqi4_ontology_impact` / `86`. No other line in these files may change. This is the same class of mechanical consequence CDD-041's GA amendment named explicitly after being discovered late during OQI3 — named up front here instead.

| # | Path | Permitted modification |
|---|---|---|
| 13 | `backend/app/tests/test_oqi_business_rule_postgres.py` | migration-head literal only |
| 14 | `backend/app/tests/test_oqi_quality_postgres.py` | migration-head literal only |
| 15 | `backend/app/tests/test_knowledge_engine.py` | migration-head literal only |
| 16 | `backend/app/tests/test_persistence_integration.py` | migration-head literal + table-count literal (81→86) only |
| 17 | `backend/app/tests/test_runtime_architecture.py` | migration-head literal + `AUTHORIZED_CHANGED_PATHS` addition of rows 1-12 above + single-construction-site firewall assertions for the 4 new ORM classes in row 5/4 only |
| 18 | `backend/app/tests/test_oqi_cross_source_postgres.py` | migration-head literal only |
| 19 | `backend/app/tests/test_gate_v_agent_postgres.py` | migration-head literal only |
| 20 | `backend/app/tests/test_governance_engine.py` | migration-head literal only |
| 21 | `backend/app/tests/test_decision_engine.py` | migration-head literal only |

## 4. Unauthorized paths

**ALL OTHERS.** In particular, explicitly unauthorized without a further governance amendment: any change to `assertions`/`Assertion` ORM or its writer path (§4.4 of CDD-042 — that pipeline does not exist and OQI4-I does not create it); any change to `semantic_mappings`, `knowledges`, `information_element_requirements`; any change to `enterprise_entity_resolution_records`/`EntityResolutionStore`/`identity_resolution` domain code (OQI4-I reads this, never writes it); any change to `institutional_relationships`/`relationship_types`/`enterprise_entities` ORM (OQI4-I reads, never writes); any OQI1/OQI2/OQI3 domain/persistence/service file; any API or frontend path; any new advisory-lock seed constant outside the reserved sequence (none is authorized — CDD-042 §14 explicitly requires none).

## 5. Migration

```
Expected revision:      0023_oqi4_ontology_impact
Expected down_revision: 0022_oqi3_business_rule
Pre-OQI4 table count:   81
Post-OQI4 table count:  86
```

Round-trip required: `81 → 86 → 81 → 86`, single Alembic head, no `0024` introduced by this authorization.

## 6. Implementation shape

`SINGLE OQI4-I` (CDD-042 §22). No I1/I2 split authorized under this document.

## 7. API / Frontend

`NONE`. Not authorized by this document under any circumstance.

## 8. Mandatory test matrix (binding on the 3 new test files)

Direct impact per Finding family (OQI1 completeness, OQI1 validity, OQI3 BusinessRule incl. compound, OQI2 N-source incl. entity-disagreement→UNKNOWN); `IMPACTED`/`NO_IMPACT`/`IMPACT_UNKNOWN` including the "no resolution record ≠ NO_IMPACT" proof; propagation allowed/denied edge, forward/reverse direction, multi-hop, cycle, multiple paths with the 3-path cap, depth-cap boundary; the release-blocking real-Postgres writer-commits-during-CTE-statement test (direct architectural analogue of CDD-041's writer-during-frontier-statement test); the policy-read-inside-same-statement proof; lifecycle (OPEN/RESOLVED/REOPENED, ontology-change-while-OPEN, policy-version-change-while-OPEN); concurrent identical-Evaluation replay (parent-gated, no caller-visible IntegrityError, no orphan children); tenant isolation and SourceObject isolation; migration round-trip; one bounded-graph performance sanity test (hundreds of nodes, multiple paths, at least one cycle, at least one denied relationship type); firewall proofs by absence (no Finding mutation, no majority/authority-as-truth, no AI/agent code, no severity/trust-score field anywhere in the new schema).
