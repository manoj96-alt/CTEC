# CDD-041 Artifact Authorization — Business-Rule Quality Intelligence

Version: 1.0 FROZEN
Status: FROZEN
Governs: exact implementation surface for CDD-041 (companion document, frozen simultaneously)
Reference point: this authorization governs the delta from clean authoritative `main`
(`cec029270bcade338875e014c8d50ade7c60c51a`) — there is no held implementation branch/PR yet.

## 1. Scope boundary (binding)

No API, no frontend, no `main.py` wiring, no auth files, no Gate T/V/S runtime modification, no
Entity Resolution matching/scoring runtime, no OQI4/5/6/7 code, no `SourceField`/`FieldValueEvidence`
modification, no `QualityRule`/OQI1/OQI2 table modification, no performance-only index migration
beyond what §7 requires for the new tables themselves. Any need to cross these boundaries requires a
separate governance amendment — implementation must STOP and report, never improvise.

## 2. Exact authorized file set (authoritative)

| # | Action | Exact path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/domain/oqi_business_rule/__init__.py` | package marker, mirrors `domain/oqi_cross_source/__init__.py` |
| 2 | CREATE | `backend/app/domain/oqi_business_rule/rule.py` | `BusinessRule`, `BusinessRuleInputBinding`, closed AST node dataclasses (comparators, AND/OR/NOT/IMPLIES), `RuleFamily`, `ExpectedType`, `validate_business_rule_shape()` (publication-time validator per CDD-041 §26) |
| 3 | CREATE | `backend/app/domain/oqi_business_rule/evaluation.py` | `BusinessRuleEvaluation` (immutable), `EvaluationOutcome` (SATISFIED/VIOLATED/NOT_APPLICABLE), `derive_business_rule_evaluation_id()`, input-evidence digest function (CDD-041 §16-17) |
| 4 | CREATE | `backend/app/domain/oqi_business_rule/finding.py` | `BusinessRuleFinding`, `ResolutionBasis`, `derive_business_rule_finding_id()`, `apply_business_rule_finding_transition()` (CDD-041 §14-15) |
| 5 | CREATE | `backend/app/infrastructure/persistence/models/oqi_business_rule.py` | `BusinessRuleORM`, `BusinessRuleInputBindingORM` |
| 6 | CREATE | `backend/app/infrastructure/persistence/models/oqi_business_rule_evaluation.py` | `BusinessRuleEvaluationORM`, `BusinessRuleEvaluationInputORM`, `BusinessRuleEvaluationObservationORM` |
| 7 | CREATE | `backend/app/infrastructure/persistence/models/oqi_business_rule_finding.py` | `BusinessRuleFindingORM` |
| 8 | CREATE | `backend/app/infrastructure/persistence/oqi_business_rule_repository.py` | governed CRUD/publication-validation persistence for `BusinessRule`/bindings (ACTIVE/RETIRED lifecycle, one-ACTIVE-per-condition enforcement) |
| 9 | CREATE | `backend/app/infrastructure/persistence/oqi_business_rule_evaluation_repository.py` | CURRENT_STATE/HISTORICAL persistence: advisory-lock authority (seed=3), atomic Evaluation+input+observation insert, Finding transition mutation |
| 10 | CREATE | `backend/app/application/oqi_business_rule_evaluation_service.py` | orchestrates the 18-step algorithm in CDD-041 §21: load rule, resolve subject, lock, select evidence, parse, evaluate applicability/AST, derive observations/outcome, persist, mutate Finding |
| 11 | CREATE | `backend/app/infrastructure/persistence/migrations/versions/0022_oqi3_business_rule.py` | creates the 6 tables in §7 below; `down_revision="0021_oqi2_cross_source"` |
| 12 | CREATE | `backend/app/tests/test_oqi_business_rule_domain.py` | `BusinessRule`/binding/AST construction, publication-shape validation, immutability, versioning invariants |
| 13 | CREATE | `backend/app/tests/test_oqi_business_rule_evaluation_domain.py` | Evaluation/Observation domain construction, identity exclusion of observations, digest order-invariance/role-sensitivity |
| 14 | CREATE | `backend/app/tests/test_oqi_business_rule_evaluation_service.py` | full outcome/applicability matrix, simultaneous-observation preservation, Finding lifecycle 7-arm table, NOT_EVALUABLE non-persistence |
| 15 | CREATE | `backend/app/tests/test_oqi_business_rule_postgres.py` | real-Postgres schema shape, migration round-trip, composite-FK attacks, advisory-lock concurrency, idempotent replay, rollback atomicity |
| 16 | CREATE | `backend/app/tests/test_oqi_business_rule_provenance.py` | full evidence-chain reconstruction (Finding→Evaluation→Observation→input snapshot→FieldValueEvidence→SourceField→SourceObject→SourceSystem) |
| 17 | MODIFY | `backend/app/tests/test_runtime_architecture.py` | add the 6 new ORMs to firewall/single-construction-site assertions; add `AUTHORIZED_CHANGED_PATHS` entries for this gate |
| 18 | MODIFY | `backend/app/tests/test_persistence_integration.py` | table-count literal `75` → `81` |

## 3. Mechanically derived accounting

```
CREATE = 16
MODIFY = 2
DELETE = 0
TOTAL  = 18
```

Independent second count: rows 1-16 are CREATE, rows 17-18 are MODIFY, zero DELETE.
`16 + 2 + 0 = 18`. Counts agree — no arithmetic discrepancy.

## 4. File-count safety rule (binding, restated)

The exact named path set in §2 is authoritative. Any path not present there is unauthorized and
requires a further governance amendment before modification. No 19th path without one. This
authorization may be implemented across OQI3-I1/I2/I3 as separate sub-phases (per CDD-041 §33); each
sub-phase's actual touched paths must be a subset of §2 — never a superset.

## 5. Proposed persistence schema (conceptual, no migration executed by this document)

```
business_rules
  PK rule_id (uuid)
  business_condition_id      VARCHAR(200)   -- matches QualityRule.quality_condition_id precedent
  version                    INTEGER
  tenant_id                  VARCHAR(200)
  rule_family                VARCHAR(32)    -- longest value 22 chars (CONDITIONAL_PROHIBITED)
  applicability              JSON           -- closed AST, mirrors QualityRule.rule_parameters JSON
  predicate                  JSON           -- closed AST
  status                     VARCHAR(16)    -- ACTIVE | RETIRED, longest value 7 chars
  created_by                 VARCHAR(200)
  created_on                 TIMESTAMPTZ
  retired_on                 TIMESTAMPTZ NULL
  UNIQUE(business_condition_id, version)
  PARTIAL UNIQUE INDEX (tenant_id, business_condition_id) WHERE status = 'ACTIVE'

business_rule_input_bindings
  PK (rule_id, input_role)
  rule_id                    FK -> business_rules.rule_id
  input_role                 VARCHAR(64)    -- matches participant_role precedent width
  source_field_id            FK -> source_fields.source_field_id
  required                   BOOLEAN
  expected_type              VARCHAR(16)    -- STRING|DECIMAL|BOOLEAN|DATE, longest value 7 chars

business_rule_evaluations
  PK evaluation_id (uuid)
  tenant_id                  VARCHAR(200)
  business_condition_id      VARCHAR(200)
  rule_id                    FK -> business_rules.rule_id  (pins rule_version, per CDD-041 §8/§20)
  subject_type               VARCHAR(32)    -- SINGLE_RECORD only, initial scope
  source_record_reference    VARCHAR(1000)  -- matches oqi_quality_finding precedent width
  evaluation_mode            VARCHAR(16)    -- CURRENT_STATE | HISTORICAL
  evaluation_horizon         TIMESTAMPTZ
  input_evidence_digest      VARCHAR(64)    -- matches participant_evidence_digest precedent width
  outcome                    VARCHAR(16)    -- SATISFIED|VIOLATED|NOT_APPLICABLE, longest 14 chars
  evaluated_at                TIMESTAMPTZ

business_rule_evaluation_inputs
  PK (evaluation_id, input_role)
  evaluation_id               FK -> business_rule_evaluations.evaluation_id
  input_role                  VARCHAR(64)
  field_value_evidence_id     FK -> field_value_evidence.field_value_evidence_id, NULLABLE
                               (NULL represents zero qualifying evidence for a known subject,
                                per CDD-041 §18 -- never a manufactured evidence row)

business_rule_evaluation_observations
  PK (evaluation_id, clause_id, observation_type, input_role)
  evaluation_id                FK -> business_rule_evaluations.evaluation_id
  clause_id                    VARCHAR(64)
  observation_type             VARCHAR(64)   -- REQUIRED_INPUT_MISSING|CLAUSE_VIOLATED, longest 22
  input_role                   VARCHAR(64)
  CHAINED COMPOSITE FK (evaluation_id, input_role) -> business_rule_evaluation_inputs
    (evaluation_id, input_role)   -- same chained-FK provenance-integrity pattern as OQI2 CDD-040 §49,
                                     requires an additive UNIQUE(evaluation_id, input_role) on
                                     business_rule_evaluation_inputs (already its own PK, so no
                                     further constraint needed)

business_rule_findings
  PK finding_id (uuid)
  tenant_id                    VARCHAR(200)
  business_condition_id        VARCHAR(200)
  subject_type                 VARCHAR(32)
  subject_identity              VARCHAR(1000)  -- source_record_reference-equivalent
  status                        VARCHAR(16)    -- OPEN|RESOLVED, longest value 8 chars
  resolution_basis              VARCHAR(16) NULL  -- SATISFIED|NOT_APPLICABLE, longest 14 chars
  latest_evaluation_id           FK -> business_rule_evaluations.evaluation_id
  occurrence_count               INTEGER
  reopen_count                   INTEGER
  state_revision                  INTEGER
  first_seen_at                   TIMESTAMPTZ
  last_seen_at                    TIMESTAMPTZ
  UNIQUE(tenant_id, business_condition_id, subject_type, subject_identity)
  CHECK (status = 'OPEN' AND resolution_basis IS NULL)
     OR (status = 'RESOLVED' AND resolution_basis IS NOT NULL)
```

All column widths above were checked against their longest authorized enum value (§8 below) — none
repeats the OQI2 `finding_type`-width defect. `expected_type VARCHAR(16)` comfortably exceeds its
longest value (`DECIMAL`, 7 chars); `rule_family VARCHAR(32)` comfortably exceeds its longest value
(`CONDITIONAL_PROHIBITED`, 22 chars); `outcome`/`resolution_basis VARCHAR(16)` exactly matches the
existing OQI2 `outcome` column width precedent and comfortably fits `NOT_APPLICABLE` (14 chars).

## 6. Table count verification

```
Current authoritative main (verified): 75 tables
New tables authorized by this document: 6
  (business_rules, business_rule_input_bindings, business_rule_evaluations,
   business_rule_evaluation_inputs, business_rule_evaluation_observations, business_rule_findings)
Expected post-OQI3 table count: 81
```

Must be mechanically re-verified against the real migrated schema during OQI3-I1 implementation —
this document freezes the *expected* count, not a substitute for that verification.

## 7. Migration authorization

```
revision      = "0022_oqi3_business_rule"     (23 characters -- verified well under the
                                                 VARCHAR(32) alembic_version.version_num
                                                 constraint that caused the OQI2 defect;
                                                 verified via direct character count, not assumed)
down_revision = "0021_oqi2_cross_source"        (unchanged, current single head)
filename      = backend/app/infrastructure/persistence/migrations/versions/0022_oqi3_business_rule.py
```

This authorizes the exact revision id and filename only; the migration file itself is created during
OQI3-I1, not by this governance document. No `0023` or any other identifier is authorized.

## 8. Enum-width verification (mechanical, exhaustive)

```
rule_family        max value length 22 ("CONDITIONAL_PROHIBITED")   column width 32   MARGIN OK
expected_type       max value length  7 ("DECIMAL")                  column width 16   MARGIN OK
status (rule)        max value length  7 ("RETIRED")                  column width 16   MARGIN OK
status (finding)      max value length  8 ("RESOLVED")                 column width 16   MARGIN OK
outcome                max value length 14 ("NOT_APPLICABLE")           column width 16   MARGIN OK
resolution_basis        max value length 14 ("NOT_APPLICABLE")           column width 16   MARGIN OK
observation_type         max value length 22 ("REQUIRED_INPUT_MISSING")   column width 64   MARGIN OK
evaluation_mode            max value length  ≤16 (CURRENT_STATE=14, HISTORICAL=10)  width 16  MARGIN OK
subject_type                 max value length ≤32 (SINGLE_RECORD=13, deferred types longer but
                              not authorized for persistence in this document)        width 32  MARGIN OK
```

Every authorized string/enum column has verified headroom. No implementation-discovered width
correction is anticipated, but if evaluation-time evidence proves otherwise, the established
narrow-companion-correction precedent (CDD-040's two corrections) applies unchanged.

## 9. Mandatory adversarial test matrix (binding on OQI3-I2/I3/V, not exhaustive of what a verification
   gate may add)

**Governance**: one ACTIVE version per condition enforced; immutable version meaning (mutation
attempt rejected); duplicate input_role within a rule rejected; duplicate clause_id within a rule
rejected; cross-tenant input binding rejected.

**AST**: unsupported operator rejected at publication; malformed AST schema rejected; AST depth bound
enforced; AST node-count bound enforced; arbitrary-code payload rejected (e.g. attempted `eval`
string in a node field).

**Types**: DECIMAL ordering correct; DATE ordering correct; BOOLEAN equality exact; STRING equality
exact; invalid DATE representation → `NOT_EVALUABLE`; invalid DECIMAL representation →
`NOT_EVALUABLE`; no implicit coercion (STRING "10" never compares equal/ordered against DECIMAL 10);
incompatible operator/type combination (e.g. `LT` on STRING) rejected at publication, never at
runtime.

**CONDITIONAL_REQUIRED**: applicability false → `NOT_APPLICABLE`; applicability true + target exists
→ `SATISFIED`; applicability true + target missing → `VIOLATED` with `REQUIRED_INPUT_MISSING`
observation.

**CONDITIONAL_PROHIBITED**: applicability false → `NOT_APPLICABLE`; applicability true + prohibited
state absent → `SATISFIED`; applicability true + prohibited state present → `VIOLATED` with
`CLAUSE_VIOLATED` observation.

**FIELD_COMPARISON**: each authorized comparator satisfied/violated case; missing input →
`NOT_EVALUABLE` if it prevents deterministic comparison, or `VIOLATED`/`REQUIRED_INPUT_MISSING` if
the binding is independently `required`; invalid typed input → `NOT_EVALUABLE` (CDD-041 §10).

**Simultaneous observations**: single clause failure; multiple simultaneous clause failures (at
least 3, mirroring OQI2's N-source discipline generalized to N-clause); all deterministic failures
preserved; no first-failure short-circuit (must be proven by an assertion that would fail under a
reintroduced short-circuit, mirroring the OQI2-I-R2 mutation-sensitivity discipline).

**Lifecycle**: first violation → OPEN; repeated violation → OPEN, state_revision increments;
satisfied → RESOLVED/resolution_basis=SATISFIED; not-applicable → RESOLVED/resolution_basis=
NOT_APPLICABLE; reopen after SATISFIED; reopen after NOT_APPLICABLE; NOT_EVALUABLE leaves an existing
Finding completely unchanged (no Evaluation persisted); retirement leaves an existing OPEN Finding
unchanged.

**Historical**: historical VIOLATED, SATISFIED, NOT_APPLICABLE all persist Evaluation+Observations;
zero Finding creation/mutation in any historical case.

**Concurrency**: first-Finding race (two workers, one Finding survives); evidence arrival for
multiple input roles while a worker waits for lock (post-lock frontier coherent); coherent
multi-field frontier (no field selected before lock, none selected in a second unlocked pass);
identical replay (sequential and concurrent) produces no duplicate Evaluation/Observation rows;
forced mid-transaction rollback leaves zero orphan Evaluation/input/observation/Finding-mutation
rows.

**Security/tenant**: cross-tenant field binding rejected; advisory-lock seed=3 verified to not
collide with seed=1 (OQI1) or seed=2 (OQI2) in any test exercising all three simultaneously.

## 10. Acceptance criteria

All 18 paths present exactly as named (no 19th path, per sub-phase or in aggregate); table count 81
confirmed on real Postgres; single Alembic head `0022_oqi3_business_rule`; §9's exact scenarios all
present and passing on real PostgreSQL where marked as such; zero raw-value duplication in
`business_rule_evaluation_observations`; `SourceField`/`FieldValueEvidence`/every OQI1/OQI2 table
byte-unchanged; zero regression in the full backend suite beyond the established environmental
baseline; firewalls (§27 of the CDD) clear; static quality (`black`/`isort`/`ruff`/`mypy`) clean;
exact-head CI green.

## 11. STOP conditions (fail-closed, unchanged discipline)

STOP and report — do not improvise — if: an implementation need requires touching any path outside
§2's exact set; any previously-frozen governance file requires editing in place; the two independent
counts in §3 ever disagree; the verified table count differs from 81; any firewall boundary (CDD-041
§27) would be crossed; any enum value discovered during implementation exceeds its frozen column
width (§8); the migration revision id or filename needs to differ from §7; advisory-lock seed=3 is
found to collide with an existing seed.
