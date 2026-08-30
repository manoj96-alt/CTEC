# CDD-044 Artifact Authorization — Criticality, Business Impact & Explainable Reliance (OQI6)

Version: 1.0 FROZEN
Status: FROZEN
Governs: CDD-044 (FROZEN)

## 1. Authorization structure

One implementation phase (OQI6-I), named now, gated behind a separate, future, explicit Product
Owner implementation-start authorization — mirroring the precedent established for every prior OQI
governance freeze (CDD-041/042/043) publishing before implementation begins.

## 2. Exact authorized path set

```
CREATE = 10
MODIFY = 16
  SEMANTIC MODIFY   = 4
  MECHANICAL MODIFY = 12
DELETE = 0
TOTAL  = 26
```

### 2.1 CREATE (10)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/domain/oqi_business_impact/__init__.py` | package marker |
| 2 | `backend/app/domain/oqi_business_impact/process.py` | `BusinessProcess`, lifecycle, versioning |
| 3 | `backend/app/domain/oqi_business_impact/dependency.py` | `BusinessDependency`, `Criticality`, versioning |
| 4 | `backend/app/domain/oqi_business_impact/impact.py` | `BusinessImpactEvaluation`, `CurrentBusinessImpact`, business-impact decision logic (CDD-044 §59) |
| 5 | `backend/app/domain/oqi_business_impact/reliance.py` | `RelianceEvaluation`, `CurrentReliance`, closed reason-code vocabulary, reliance decision logic (CDD-044 §58) |
| 6 | `backend/app/infrastructure/persistence/models/oqi_business_impact.py` | ORM: `OqiBusinessProcessORM`, `OqiBusinessDependencyORM`, `OqiBusinessImpactEvaluationORM`, `OqiCurrentBusinessImpactORM`, `OqiRelianceEvaluationORM`, `OqiCurrentRelianceORM` |
| 7 | `backend/app/infrastructure/persistence/oqi_business_impact_repository.py` | repository: process/dependency/evaluation/current-projection persistence; single-statement/snapshot current-state reads per CDD-044 §41; dedicated advisory-lock seed per CDD-044 §41 |
| 8 | `backend/app/application/oqi_business_impact_service.py` | orchestration: dependency-scoped business-impact derivation, subject-scoped reliance derivation, re-evaluation-triggered current-state refresh |
| 9 | `backend/app/infrastructure/persistence/migrations/versions/0026_oqi6_criticality_business_impact_reliance.py` | migration creating the 6 OQI6 tables |
| 10 | `backend/app/tests/test_oqi_business_impact.py` | OQI6 test suite (domain, service, real-Postgres per CDD-044 §61-62) |

### 2.2 MODIFY — semantic (4, narrow additive-only, per CDD-044 §49/§49.1)

| # | Path | Exact authorized change |
|---|---|---|
| 11 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | add exactly one new read-only method returning `CurrentOntologyImpact` rows by `(tenant_id, ontology_element_type, ontology_element_id)`; no existing method's behavior changes; no write method added |
| 12 | `backend/app/infrastructure/persistence/oqi_quality_evaluation_repository.py` | add exactly one new read-only method reporting whether ≥1 OQI1 evaluation row exists for a given ontology subject's resolved evidence; no other change |
| 13 | `backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py` | add exactly one new read-only method reporting whether ≥1 OQI2 evaluation row exists for a given ontology subject's resolved evidence; no other change |
| 14 | `backend/app/infrastructure/persistence/oqi_business_rule_evaluation_repository.py` | add exactly one new read-only method reporting whether ≥1 OQI3 evaluation row exists for a given ontology subject's resolved evidence (an OQI3 `NOT_EVALUABLE` non-row does not count, per CDD-044 §18); no other change |

No other file under `backend/app/domain/`, `backend/app/infrastructure/persistence/models/`,
`backend/app/infrastructure/persistence/*_repository.py`, or `backend/app/application/` belonging to
OQI1, OQI2, OQI3, OQI4, OQI5, Gate S, Gate V, or Gate F may be created, modified, or deleted.

### 2.3 MODIFY — mechanical migration-head (12, exact, no wildcard)

Adding migration `0026_oqi6_criticality_business_impact_reliance` requires the identical mechanical
Alembic-head-literal/table-count-literal bump exercised at every prior OQI transition, discovered by
direct inspection of the current repository (not assumed) — 9 files carrying the literal revision
string `"0025_oqi5_agent_reasoning"`, plus 3 files carrying a numeric table-count literal (`94`) that
`test_persistence_integration.py`'s and `test_runtime_architecture.py`'s own literal-string files do
not already cover:

| # | Path | Literal changed |
|---|---|---|
| 15 | `backend/app/tests/test_decision_engine.py` | migration-head revision string |
| 16 | `backend/app/tests/test_gate_v_agent_postgres.py` | migration-head revision string |
| 17 | `backend/app/tests/test_governance_engine.py` | migration-head revision string |
| 18 | `backend/app/tests/test_knowledge_engine.py` | migration-head revision string |
| 19 | `backend/app/tests/test_oqi_business_rule_postgres.py` | migration-head revision string |
| 20 | `backend/app/tests/test_oqi_cross_source_postgres.py` | migration-head revision string |
| 21 | `backend/app/tests/test_oqi_quality_postgres.py` | migration-head revision string |
| 22 | `backend/app/tests/test_persistence_integration.py` | migration-head revision string + table-count literal (`94` → `100`) |
| 23 | `backend/app/tests/test_runtime_architecture.py` | migration-head revision string + firewall-list additions for the 6 new OQI6 ORM classes |
| 24 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | table-count literal only (`94` → `100`, both round-trip assertions) |
| 25 | `backend/app/tests/test_oqi_remediation_i1.py` | table-count literal only (`94` → `100`) |
| 26 | `backend/app/tests/test_oqi_remediation_agent_i2.py` | table-count literal only (`94` → `100`, all three round-trip assertions) |

No other test file may be touched for migration-head/table-count reasons — any file discovered at
implementation time to require a similar bump beyond this exact 12-file list is an unauthorized path
requiring a governance amendment, not a silent addition.

## 3. Independent double-count reconciliation (binding, per CDD-044/OQI6-G's own discipline)

**Count derivation A** (summary arithmetic): `10 CREATE + 4 semantic MODIFY + 12 mechanical MODIFY +
0 DELETE = 26`.

**Count derivation B** (literal table-row enumeration): §2.1 lists 10 numbered rows; §2.2 lists 4
numbered rows (11-14); §2.3 lists 12 numbered rows (15-26). `10 + 4 + 12 = 26`. Highest row number in
the combined table is `26`, matching the total exactly.

Both derivations agree at **26**. No discrepancy exists; this document is safe to publish under
CDD-044 §66's own requirement that authorization counts be independently reconciled before freeze
(the exact discipline CDD-043's own I2 accounting defect, corrected via
`CDD-043-Artifact-Authorization-I2-Accounting-Correction.md`, established as mandatory going forward).

## 4. Explicit prohibitions

No path outside §2's exact 26-path set may be created or modified for OQI6 purposes. No file under
`backend/app/domain/gate_s/`, `backend/app/domain/gate_v/`, `backend/app/domain/oqi/`,
`backend/app/domain/oqi_cross_source/`, `backend/app/domain/oqi_business_rule/`,
`backend/app/domain/oqi_ontology_impact/`, `backend/app/domain/oqi_remediation/`,
`backend/app/domain/oqi_remediation_agent/`, `backend/app/domain/ontology_copilot/`,
`backend/app/integration/adapters/gate_f/`, or their corresponding ORM/application files (beyond the
four narrow §2.2 exceptions) may be created, modified, or deleted. No API router file. No frontend
file. No `CDD-015`/`CDD-036`/`CDD-037`/`CDD-039`/`CDD-040`/`CDD-041`/`CDD-042`/`CDD-043` or any of
their Artifact Authorizations.

## 5. Table count expectations

```
Pre-OQI6:  94  (verified against real migrated schema, this document's own preflight)
Post-OQI6: 100 (94 + 6)
```

## 6. Enum-width verification (performed at governance time, per OQI2/OQI3/OQI5 lesson)

`Criticality` values `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`, longest 8 chars → `String(16)` safe.
`BusinessProcess.status`/`BusinessDependency.status` values `ACTIVE`/`RETIRED`, longest 7 chars →
`String(16)` safe. `BusinessImpactEvaluation` outcome values `BUSINESS_IMPACT_IDENTIFIED` (26 chars),
`NO_KNOWN_BUSINESS_IMPACT` (25 chars), `BUSINESS_IMPACT_UNKNOWN` (23 chars) → `String(32)` safe.
`RelianceEvaluation` outcome values `RELIANCE_SUPPORTED` (18 chars), `RELIANCE_AT_RISK` (16 chars),
`RELIANCE_UNKNOWN` (16 chars) → `String(32)` safe. Reason codes, longest
`INSUFFICIENT_QUALITY_COVERAGE` = 29 chars → `String(32)` safe per code, stored as an array/child-row
structure (OQI6-I's own elaboration) never a single delimited string.

## 7. Revision-identifier length verification

`0026_oqi6_reliance` = 18 characters, safe (well under the 32-character
`alembic_version.version_num` constraint that caused the OQI2 and OQI5-I1 defects). Filename
`0026_oqi6_criticality_business_impact_reliance.py` (filenames unconstrained, per established
precedent). `down_revision = "0025_oqi5_agent_reasoning"` (current verified head).

## 8. Migration strategy

New migration, not an amendment to any existing migration (unlike the OQI2/OQI3 in-flight-PR
amendment precedent — `0025_oqi5_agent_reasoning` is already merged to main, so `0026` must be a new
file). `upgrade()` creates exactly 6 tables; `downgrade()` drops them in FK-safe dependency order
(current-projection tables before their evaluation-ledger parents; `oqi_business_dependencies` before
`oqi_business_processes`).

## 9. Required real-PostgreSQL round trip

`94 → 100 → 94 → 100`, exact table-count assertions at each step, mirroring the identical discipline
already proven at OQI4-VM and OQI5-VM.

## 10. Final accounting

```
OQI6-I (named now, gated behind separate implementation-start authorization):
  CREATE = 10
  MODIFY = 16  (4 semantic narrow-additive + 12 mechanical migration-head/table-count)
  DELETE = 0
  TOTAL  = 26
```

## 11. Acceptance criteria (for the future OQI6-I implementation phase)

All 26 paths present exactly as named (no 27th path); table count 100 confirmed on real PostgreSQL;
CDD-044 §57-59's exact decision tables and all ten §62 crown tests passing; §49/§49.1's four semantic
modifications each verified as a single narrow additive read-only method with zero behavioral change
to any existing method; zero regression in OQI1-5/Gate S/Gate V/Gate F suites; static quality clean;
exact-head CI green; CDD-044 and this Artifact Authorization byte-identical pre- and post-
implementation.

## 12. STOP conditions (fail-closed, unchanged discipline)

STOP and report — do not improvise — if: an implementation need requires touching any path outside
§2's exact 26-path set; any previously-frozen governance file requires editing in place; the two
independent counts in §3 ever disagree at implementation time; the verified table count differs from
100; any firewall boundary (§4, CDD-044 §49-53) would be crossed beyond the four named narrow
exceptions; any of the four semantic-MODIFY files requires more than one new method or any change to
an existing method's behavior.
