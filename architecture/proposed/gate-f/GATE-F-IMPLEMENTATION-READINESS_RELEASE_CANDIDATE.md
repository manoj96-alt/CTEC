# Gate F — Implementation Readiness (Release Candidate)

Status: RELEASE CANDIDATE PLANNING ARTIFACT — NON-AUTHORITATIVE — NOT
IMPLEMENTATION AUTHORITY. This document identifies likely implementation
workstreams implied by the frozen candidate architecture, for Product Owner
planning purposes only. No implementation is authorized by this document or
by F3.

## Workstream map

| Architecture requirement | Likely implementation area | Acceptance-test obligation (CDD-015 §29) | Dependency |
|---|---|---|---|
| 3 new relationship types + ratification of 10 concepts/7 types | Semantic seed change: extend `ontology_seed.py`-equivalent (or its successor) with `assembledAt`/`coveredBy`/`candidateFor`, under explicit RFC-017 citation this time (not silently, unlike Increment 2A) | Ontology seed test (idempotency, correct domain/range bindings) | RFC-017 authorization |
| `decision_evaluations` table + `decision_evaluation_records.decision_evaluation_id` column | Persistence migration: new Alembic migration, new SQLAlchemy model, following the `decision_evaluation.py`/migration-0006 pattern | Migration test; model test | CDD-015 authorization |
| Per-(candidate, material) fact attachment | Persistence adapters: new adapter code writing `institutional_relationships` (`candidateFor`) + `institutional_relationship_assertions` rows, CDD-011-adapter-shaped | Cardinality test (CDD-015 §29) constructing the multi-material/multi-candidate case | RFC-017 vocabulary, CDD-015 persistence extension |
| Qualification/capacity/lead-time/cost derivation | KRM/knowledge derivation: new bounded adapter(s) feeding SRM/ASM/KRM ports, replacing caller-supplied scores | Domain unit tests, CDD-011 adapter pattern | CDD-015 §9 |
| Mitigation recommendation | DRM recommendation: new adapter feeding `DecisionRecommendationService`, policy-configured materiality threshold | DRM adapter tests | CDD-015 §11 |
| `HUMAN_APPROVAL_REQUIRED` standing | GRM standing: new adapter producing `governance_evaluation_records` with the group reference | GRM adapter tests; negative test confirming no `APPROVED`/`REJECTED` code path exists | CDD-015 §12 |
| One new read API surface | Gate F API: new FastAPI router under `supply-chain-impact:read`, following the `api/supplier_risk/router.py` pattern | Security/scope-enforcement tests (CDD-015 §29) | PAD-003 scope authorization |
| `supply-chain-impact:read` | Authorization scope: Keycloak/IDP scope registration + `_authorize()` wiring, following `supplier-risk:read`'s pattern | Scope-enforcement negative tests | PAD-003 authorization |
| Frontend governed experience | New, authenticated production frontend surface consuming the Gate F API — explicitly NOT `/demo/supplier-risk` (CDD-015 §22-23) | Frontend component/accessibility tests, following existing `supplier-risk-*.test.tsx` pattern | CDD-015 §21 API, PAD-003 scope |
| Replay/recovery participation | Runtime integration: Gate F adapters plug into the existing six-stage checkpoint/replay model unmodified; `decision_evaluation_id` lifecycle (CDD-015 §20) implemented at capability-start, reused across replay | Replay/recovery tests confirming decision identity stability across a simulated replay | CDD-010/012 unmodified reuse |
| Tenant isolation invariant | Persistence adapter validation: application-layer check that every child `decision_evaluation_records` row's resolved tenant matches its group's `tenant_id` | Tenant-isolation test asserting rejection on violation (CDD-015 §29) | `decision_evaluations.tenant_id` |
| Demo transition | Demo runbook: eventual update to `DEMO_RUNBOOK.md` narrating the governed Gate F flow — explicitly NOT part of this package or F3 | N/A (documentation) | Frontend governed experience |
| Architecture-drift guard | Test: a Gate-F equivalent of `test_runtime_architecture.py`'s six-stage allowlist assertions, confirming no seventh stage was ever introduced | Architecture-drift test (CDD-015 §29) | CDD-010 unmodified |

## Sequencing note (informational, not authorized here)

The dependency column above suggests a natural order: RFC-017/PAD-003/CDD-015
authorization → semantic seed change → persistence migration → derivation
adapters → DRM/GRM adapters → API → scope wiring → frontend → demo runbook
update. This is a planning observation only; no implementation sequencing is
authorized by F3.
