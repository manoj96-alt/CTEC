# CDD-039 — Ontology Quality Intelligence Deterministic Foundation — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION (implementation NOT yet Product-Owner authorized)
Authority base: 37e4be61f0ce96d29f2e3e78968c6f5bfe2aeb5b

## 1. Purpose

Enumerates exactly which repository artifacts a future OQI1 implementation phase may create or
modify to prove the deterministic quality foundation defined by CDD-039 — and nothing more.

## 2. Governing authorities

CDD-039 remains the sole semantic authority for every decision enumerated here. CDD-022, CDD-031,
CDD-019, CDD-036, CDD-037, and CDD-038 remain FROZEN and untouched — this authorization does not
permit any file governed by them to change, except the four exact mechanical migration-head literal
corrections named in Sec4.

## 3. Implementation objective

Prove CDD-039's exact deterministic-evaluation, honest-lineage-identity, evaluation-authority-safe
pipeline via the smallest file surface consistent with existing repository layering conventions
(domain / persistence model / repository / application service / tests), with **no API and no
frontend of any kind** — OQI1 is proven entirely by direct construction and test, matching CDD-039
Sec8's explicit non-goal.

## 4. Exact authorized allowlist

| Path | Operation | Purpose |
|---|---|---|
| `backend/app/domain/oqi/__init__.py` | CREATE | Package marker for the new OQI domain package (capability-scoped, not gate-scoped, mirroring `app/domain/integration/`'s multi-gate precedent). |
| `backend/app/domain/oqi/quality_rule.py` | CREATE | `QualityDimension`, `QualityFindingType`, `ValidityPrimitive`, `QualityRuleStatus` (closed StrEnums, CDD-039 Sec9-10), the dimension/finding-type/primitive coupling table (Sec10), `QualityRule` frozen dataclass, the shared rule-shape validation function used at construction/persistence/evaluation (Sec33), `OQI_NAMESPACE` (Sec20). |
| `backend/app/domain/oqi/evaluation.py` | CREATE | `EvaluationMode`, `EvaluationOutcome`, `EvaluationOrigin` (closed StrEnums, Sec19), `SourceRecordLineageIdentity` and `EvaluationSubject` frozen value objects (Sec12/14), `QualityEvaluation` frozen dataclass, the deterministic `canonical_subject_identity`/`evaluation_id` functions (Sec20), the Completeness and Validity deterministic evaluation functions (Sec12, Sec31-32). |
| `backend/app/domain/oqi/finding.py` | CREATE | `QualityFinding` dataclass, the deterministic `quality_finding_id` function (Sec28), and the pure Finding-transition function implementing Sec30's exhaustive transition table. |
| `backend/app/infrastructure/persistence/models/oqi_quality_rule.py` | CREATE | `QualityRuleORM` (`quality_rules`), exactly the columns and constraints in CDD-039 Sec39. |
| `backend/app/infrastructure/persistence/models/oqi_quality_evaluation.py` | CREATE | `QualityEvaluationORM` (`quality_evaluations`) and `QualityEvaluationEvidenceORM` (`quality_evaluation_evidence`), exactly the columns/constraints/indexes in CDD-039 Sec39. |
| `backend/app/infrastructure/persistence/models/oqi_quality_finding.py` | CREATE | `QualityFindingORM` (`quality_findings`), exactly the columns/indexes in CDD-039 Sec39. |
| `backend/app/infrastructure/persistence/migrations/versions/0020_oqi1_quality_foundation.py` | CREATE | Alembic migration creating exactly the four Sec39 tables; `down_revision = "0019_gate_v_agent_resolution"`. No modification to any existing table. |
| `backend/app/infrastructure/persistence/oqi_quality_rule_repository.py` | CREATE | `OqiQualityRuleRepository`: `create()`, `get_active(quality_condition_id)`, `activate_new_version()` (implementing Sec34's retire-then-activate ordering). |
| `backend/app/infrastructure/persistence/oqi_quality_evaluation_repository.py` | CREATE | `OqiQualityEvaluationRepository`: `acquire_evaluation_authority(quality_finding_id)` (the Sec12 advisory-lock mechanism, below), `get_finding()`, `insert_evaluation_idempotent()`, `upsert_finding()` — all evaluation-ledger and Finding-mutation writes for CURRENT_STATE evaluations occur inside one transaction coordinated by this repository, mirroring Gate S's own lock-then-mutate-in-one-transaction precedent (CDD-036 Sec20) at the *principle* level only, using the mechanism frozen in this document's Sec12 (not `SELECT ... FOR UPDATE`, which cannot lock a not-yet-existing row). The sole authorized construction site for `QualityEvaluationORM`, `QualityEvaluationEvidenceORM`, and `QualityFindingORM`. |
| `backend/app/application/oqi_quality_evaluation_service.py` | CREATE | `OqiQualityEvaluationService`: `evaluate_historical()` (Sec22, never touches Finding) and `evaluate_current_state()` (Sec23-25, full authority/lock/evaluate/persist/mutate/commit flow). Defines its own narrow repository Protocols (not imported from Gate S/Gate V, mirroring their own zero-shared-code precedent). |
| `backend/app/tests/test_oqi_quality_rule_domain.py` | CREATE | Pure domain unit tests: rule construction validation (Sec10/31/33), dimension/finding-type/primitive coupling enforcement, malformed `rule_parameters` rejection for all three Validity primitives, rule-version identity determinism. |
| `backend/app/tests/test_oqi_quality_evaluation_domain.py` | CREATE | Pure domain unit tests: `SourceRecordLineageIdentity`/`EvaluationSubject`/`evaluation_id`/`quality_finding_id` determinism and tenant/SourceObject/SourceField isolation (Sec12/14/20/28); Completeness known-lineage/unknown-lineage/zero-target-evidence/other-field-establishes-lineage logic (Sec12); Validity enum/format/range evaluation including boundary values and the missing-value-never-double-counted-as-Validity rule (Sec31-32); Finding transition table exhaustiveness (Sec30). |
| `backend/app/tests/test_oqi_quality_evaluation_service.py` | CREATE | Fake-repository application-service tests: HISTORICAL never mutates a Finding and always persists its own ledger row (Sec22); full CURRENT_STATE transition matrix end-to-end (Sec30); rule retirement never mutates an existing Finding (Sec18); malformed persisted rule fails closed at evaluation time (Sec33 point 3); replay idempotency (Sec20). |
| `backend/app/tests/test_oqi_quality_postgres.py` | CREATE | Real-Postgres tests: migration schema correctness (tables/constraints/indexes match Sec39 exactly); concurrent first-violation race (two concurrent CURRENT_STATE evaluations for a subject with no prior Finding — exactly one creates the Finding); concurrent violation/satisfied race; evidence arrival during contention; lock acquisition before evidence selection (Sec25); `state_revision` monotonicity under concurrency; no duplicate Finding; no duplicate identical `QualityEvaluation` row; different tenants do not block each other; different subjects do not incorrectly block each other (CDD-039 Sec24, this document's Sec12). |
| `backend/app/tests/test_oqi_provenance.py` | CREATE | Reconstructs the full `QualityFinding -> QualityEvaluation -> exact QualityRule version -> exact FieldValueEvidence ids -> SourceField -> SourceObject -> SourceSystem` chain (Sec21/35) and verifies tenant identity holds throughout; proves `QualityEvaluation`/`QualityFinding` never persist a duplicate raw `observed_representation` value (Sec36, the raw-value-leak obligation). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add the 14 new paths above to `AUTHORIZED_CHANGED_PATHS`; add one new firewall test `test_oqi1_quality_foundation_respects_every_firewall()` proving: no Gate T (`CDD-031`/evidence-fitness) import; no Entity Resolution import; no agent/Gate V import; no API route registration anywhere in `main.py` for any OQI path (confirmed by `main.py` remaining absent from this authorization's changed-path list); no frontend dependency; and that `QualityRuleORM`, `QualityEvaluationORM`, `QualityEvaluationEvidenceORM`, and `QualityFindingORM` are each constructed in exactly one authorized repository file, mirroring the exact `test_gate_v_governed_agent_resolution_respects_every_firewall` pattern (source-inspection via `ast`, forbidden-import-prefix list, single-construction-site assertion). |
| `backend/app/tests/test_decision_engine.py` | MODIFY | Update exactly the migration-head literal: `"0019_gate_v_agent_resolution"` → `"0020_oqi1_quality_foundation"`. No other change. |
| `backend/app/tests/test_governance_engine.py` | MODIFY | Update exactly the migration-head literal: `"0019_gate_v_agent_resolution"` → `"0020_oqi1_quality_foundation"`. No other change. |
| `backend/app/tests/test_knowledge_engine.py` | MODIFY | Update exactly the migration-head literal: `"0019_gate_v_agent_resolution"` → `"0020_oqi1_quality_foundation"`. No other change. |
| `backend/app/tests/test_persistence_integration.py` | MODIFY | Update exactly two literals: migration-head `"0019_gate_v_agent_resolution"` → `"0020_oqi1_quality_foundation"`; table-count `64` → `68`. No other change. |

```
AUTHORIZED_NEW    = 15
AUTHORIZED_CHANGE = 5
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 20
```

No 21st path is authorized. If implementation discovery determines a further new/modified file is
mechanically necessary, implementation MUST STOP and return to the Product Owner rather than
silently widening this surface.

## 5. Read-only dependencies

Consumed, by query/call only, entirely unmodified: `app.infrastructure.persistence.models.
field_value_evidence.FieldValueEvidenceORM` (read-only query: `source_field_id`,
`source_record_reference`, `observed_representation`, `observed_at`, `received_at`,
`field_value_evidence_id`); `app.infrastructure.persistence.models.source_field.SourceFieldORM`
(read-only: `source_object_id`); `app.infrastructure.persistence.models.source_object.
SourceObject` (read-only: `tenant_id`); `Container.ontology_sessions` (existing session factory —
no `dependency_container.py` change).

## 6. Explicitly forbidden files/domains (binding)

NOT authorized under any circumstance:
- `backend/app/infrastructure/persistence/models/field_value_evidence.py`
- `backend/app/infrastructure/persistence/models/source_field.py`,
  `backend/app/infrastructure/persistence/models/source_object.py`,
  `backend/app/infrastructure/persistence/models/source_system.py`
- any migration other than `0020_oqi1_quality_foundation.py`
- any file under `backend/app/domain/gate_q`, `gate_r`, `gate_s`, `gate_v`, or their API/
  application/persistence counterparts
- `backend/app/application/mcp_client.py`, `mcp_connector_catalog.py`, `governed_tool_executor.py`,
  `gate_s_approval_service.py`, `gate_v_agent_service.py`, and their repositories
- any file under `backend/app/api/` (no API of any kind is authorized for OQI1)
- `backend/app/main.py` (no route registration — OQI1 has no API to register)
- `backend/app/core/dependency_container.py`
- `keycloak/ctec-realm.json` (no new scope — no API to gate)
- any file under `frontend/`
- any file governing Simulation, Evidence Fitness, or remediation
- any Entity Resolution domain/persistence file
- CDD-019, CDD-022, CDD-031, CDD-036, CDD-037, CDD-038, CDD-039, this Artifact Authorization, or any
  other frozen governance document
- `architecture/INDEX.md` (not updated by Gate S, Gate V, or Gate W governance publication; this
  authorization follows the same, now three-times-confirmed, precedent)

## 7. No-API / no-frontend discipline (binding, load-bearing)

OQI1 introduces zero HTTP routes, zero Keycloak scopes, zero frontend files, and zero
`dependency_container.py` changes. This is a deliberate, binding scope boundary (CDD-039 Sec8), not
an oversight — a future Gate (most naturally an extension of Gate W's own reserved production-API
surface, CDD-038) would introduce API exposure under its own, separate governance cycle.

## 8. Persistence / migration discipline (binding)

Exactly one migration, exactly four new tables (CDD-039 Sec39). No existing table is altered. No
Keycloak change. No new scope.

## 9. Dependency-container discipline (binding)

`backend/app/core/dependency_container.py` is NOT modified. `OqiQualityEvaluationService` and its
repositories are constructed directly by whatever future caller needs them (currently: only tests),
exactly mirroring how a domain/persistence-only capability without an API layer is wired.

## 10. Gate T / Entity Resolution / Gate S / Gate V / Gate W firewall (binding, restated)

No file under `backend/app/domain/gate_s`, `gate_v`, any Entity Resolution package, or any Gate T
evidence-fitness module is imported, called, referenced, or modified by any authorized file. No Gate
W production-API pattern is consumed (OQI1 has no API to register against it).

## 11. Single-write-site discipline (binding, load-bearing)

`QualityRuleORM` may be constructed only in `oqi_quality_rule_repository.py`.
`QualityEvaluationORM`, `QualityEvaluationEvidenceORM`, and `QualityFindingORM` may each be
constructed only in `oqi_quality_evaluation_repository.py`. No test fixture, no other service, may
construct any of these ORM classes directly. The Sec4 architecture test enforces this via source
inspection, mirroring `test_gate_v_governed_agent_resolution_respects_every_firewall` exactly.

## 12. Concurrency implementation mechanism (binding, frozen here — this is the exact answer to
CDD-039 Sec42)

`OqiQualityEvaluationRepository.acquire_evaluation_authority(quality_finding_id: UUID)` issues
`SELECT pg_advisory_xact_lock(%s)` with a single signed-64-bit integer key derived deterministically
as:

```
key_bytes = bytes(a ^ b for a, b in zip(quality_finding_id.bytes[0:8], quality_finding_id.bytes[8:16]))
lock_key  = struct.unpack(">q", key_bytes)[0]   -- signed big-endian 64-bit integer
```

This is a **transaction-scoped** advisory lock: it auto-releases on `COMMIT`/`ROLLBACK`, requires no
explicit unlock call, works before any `QualityFinding` row exists (the key is computed from the
deterministic identity formula, not from an existing row's primary key), and is keyed exactly on
`tenant_id + quality_condition_id + subject_type + canonical_subject_identity` (because
`quality_finding_id` is itself a `uuid5` over precisely those inputs, CDD-039 Sec28) — satisfying
tenant-safety and subject-safety without a separate lock-target table. The XOR-fold over the full
128-bit UUID uses all available entropy in the 64-bit advisory-lock key space; at OQI1's realistic
concurrent-distinct-subject cardinality, the residual collision probability is negligible and is
explicitly, honestly accepted here rather than silently ignored — a materially higher-cardinality
future need would warrant revisiting this choice under its own governance, not a silent tightening.

Historical evaluations never call `acquire_evaluation_authority` (CDD-039 Sec22) and therefore never
contend for this lock.

## 13. Test obligations (binding, minimum set)

Per CDD-039 Sec43, distributed across the six new test files exactly as enumerated in Sec4.

## 14. Migration-regression discipline (binding, load-bearing — the exact Gate S/Gate V lesson,
applied proactively this time)

The four MODIFY rows in Sec4 targeting `test_decision_engine.py`/`test_governance_engine.py`/
`test_knowledge_engine.py`/`test_persistence_integration.py` authorize **exactly** the literal
corrections named — the migration-head string in all four, plus the table-count integer in the last
— and nothing else. No test weakening, deletion, skip, xfail, refactor, or generalized
migration-agnostic mechanism is authorized in any of these four files.

## 15. Implementation stop conditions

Implementation MUST STOP and return to the Product Owner if: a 21st file becomes mechanically
necessary; `Container.ontology_sessions` is found unsuitable; `test_runtime_architecture.py`'s
allowlist differs from the state assumed here; any forbidden path (Sec6) is found mechanically
required; a fifth migration-regression file is discovered beyond the four named; the Sec12 advisory-
lock mechanism is found unsuitable for any reason (e.g., a connection-pooling mode incompatible with
session-level/transaction-level advisory locks); any API, frontend, or Keycloak change is found
necessary.

## 16. Acceptance criteria

1. Exact 20-file diff: CREATE=15, MODIFY=5, DELETE=0.
2. `GET`-free, route-free: zero new entries in `main.py`, zero new Keycloak scopes.
3. All CDD-039 Sec43 test obligations pass, distributed per Sec4/Sec13.
4. `test_runtime_architecture.py`'s own existing tests (Gate Q/R/S/V untouched, no seventh
   cognitive-engine stage, exhaustive changed-path allowlist) pass unmodified.
5. The four migration-regression tests pass with the corrected literal values.
6. Full backend regression suite passes with zero unexplained failures.
7. `docker compose config --quiet` passes.
8. CDD-039, this Artifact Authorization, CDD-019, CDD-022, CDD-031, CDD-036, CDD-037, and CDD-038
   remain byte-identical.
9. `keycloak/ctec-realm.json` remains byte-identical (no change authorized).
10. `field_value_evidence`, `source_fields`, `source_objects`, `source_systems` tables remain
    schema-unchanged (no migration touches them).
11. Exact-head CI passes before merge; post-merge CI passes.

## 17. Implementation PR strategy

One dedicated implementation branch/worktree under `/Users/manojvelayudhannair/Developer/`, from
exact authoritative main. One commit (or the minimum CI-driven fixup commits) containing exactly the
20 authorized files. One PR against main. No merge within this same phase.

## 18. Merge requirements

Exact-head CI green; `mergeable = MERGEABLE`; `mergeStateStatus = CLEAN`; frozen-governance
byte-integrity reconfirmed immediately pre-merge.

## 19. Closure criteria

OQI1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is confirmed as
new authoritative main via both git and the GitHub API; the post-merge diff from pre-merge main
contains exactly the 20 authorized files; all Sec16 acceptance criteria are reconfirmed directly
from the merge commit's own content.

## 20. Authorization

This Artifact Authorization is approved for publication alongside CDD-039, reached via the OQI0
lineage and Product-Owner-approved OQI Foundation Contract v1.2. A further, separate Product Owner
implementation authorization remains required before any authorized file may be created or
modified.
