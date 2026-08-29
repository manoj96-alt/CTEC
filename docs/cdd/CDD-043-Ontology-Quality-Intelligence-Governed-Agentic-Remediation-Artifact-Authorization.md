# CDD-043 Artifact Authorization — Governed Agentic Remediation (OQI5)

Version: 1.0 FROZEN
Status: FROZEN
Governs: CDD-043 (FROZEN)

## 1. Authorization structure

One combined document, two independently-gated path sets — mirroring the precedent established for
OQI3's multi-phase implementation (one Artifact Authorization spanning I1/I2/I3, each phase
authorized to touch only its own named subset). **OQI5-I2's paths are named now for planning
completeness but are NOT authorized for implementation until OQI5-I1 reaches its own separate,
formal Product Owner closure.** Implementing any OQI5-I2 path before that closure is a governance
violation.

## 2. OQI5-I1 — Deterministic Remediation Foundation (authorized now, pending separate I1
   implementation-start authorization)

```
CREATE = 9
MODIFY = 0
DELETE = 0
TOTAL  = 9
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/domain/oqi_remediation/__init__.py` | package marker |
| 2 | CREATE | `backend/app/domain/oqi_remediation/case.py` | `RemediationCase`, `RemediationCaseStatus` |
| 3 | CREATE | `backend/app/domain/oqi_remediation/candidate.py` | `RemediationCandidate`, deterministic candidate-identity derivation, N-source extraction domain functions (consume OQI1/2/3 read models only) |
| 4 | CREATE | `backend/app/domain/oqi_remediation/authorization.py` | `RemediationInstruction`, `RemediationAuthorization`, `compute_payload_digest` (Gate-S-pattern, structurally independent) |
| 5 | CREATE | `backend/app/infrastructure/persistence/models/oqi_remediation.py` | ORM: `OqiRemediationCaseORM`, `OqiRemediationCandidateORM`, `OqiRemediationInstructionORM`, `OqiRemediationAuthorizationORM` |
| 6 | CREATE | `backend/app/infrastructure/persistence/oqi_remediation_repository.py` | repository: case/candidate/instruction/authorization persistence, row-locked authorization decide/execute |
| 7 | CREATE | `backend/app/application/oqi_remediation_service.py` | orchestration: candidate extraction, instruction construction, authorization request/decide/execute, re-evaluation-linked case refresh |
| 8 | CREATE | `backend/app/infrastructure/persistence/migrations/versions/0024_oqi5_remediation_foundation.py` | migration creating the 4 I1 tables |
| 9 | CREATE | `backend/app/tests/test_oqi_remediation_i1.py` | I1 test suite (domain, service, real-Postgres per CDD-043 Sec25) |

No MODIFY path is authorized for I1 — no existing OQI1/2/3/4, Gate S, or Gate V file may be touched.

## 3. OQI5-I2 — Governed Real Agent Reasoning (named for planning only; NOT authorized to implement
   until OQI5-I1 formally closes)

```
CREATE = 9
MODIFY = 1
DELETE = 0
TOTAL  = 10
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/domain/oqi_remediation_agent/__init__.py` | package marker |
| 2 | CREATE | `backend/app/domain/oqi_remediation_agent/role.py` | `AgentRole`, versioning, closed recommendation-type vocabulary |
| 3 | CREATE | `backend/app/domain/oqi_remediation_agent/run.py` | `AgentRun`, `AgentEvidencePacket`, deterministic packet digest |
| 4 | CREATE | `backend/app/domain/oqi_remediation_agent/recommendation.py` | `AgentAssessment`, `AgentRecommendation`, `AgentRecommendationValidator` |
| 5 | CREATE | `backend/app/infrastructure/model_provider/provider.py` | narrow `ModelProvider` protocol + one initial concrete adapter (OQI5-local, not a generic runtime) |
| 6 | CREATE | `backend/app/infrastructure/persistence/models/oqi_remediation_agent.py` | ORM: `AgentRoleORM`, `AgentRunORM`, `AgentAssessmentORM`, `AgentRecommendationORM` |
| 7 | CREATE | `backend/app/infrastructure/persistence/oqi_remediation_agent_repository.py` | repository: role/run/assessment/recommendation persistence |
| 8 | CREATE | `backend/app/application/oqi_remediation_agent_service.py` | M2 orchestration: parallel specialist runs, deterministic aggregation, synthesizer run, validation, composition into I1's instruction construction |
| 9 | CREATE | `backend/app/infrastructure/persistence/migrations/versions/0025_oqi5_agent_reasoning.py` | migration creating the 4 I2 tables |
| — | MODIFY | `backend/app/application/oqi_remediation_service.py` | narrow, additive-only: accept an optional `agent_recommendation_id` provenance reference when constructing a `RemediationInstruction`; the payload digest computation itself is NOT modified |
| — | CREATE | `backend/app/tests/test_oqi_remediation_agent_i2.py` | I2 test suite (fake-provider domain/service, validator adversarial matrix, real-Postgres per CDD-043 Sec25) |

## 4. Explicit prohibitions (both phases)

No path outside this table may be created or modified for OQI5 purposes. No file under
`backend/app/domain/gate_s/`, `backend/app/domain/gate_v/`, `backend/app/domain/oqi/`,
`backend/app/domain/oqi_cross_source/`, `backend/app/domain/oqi_business_rule/`,
`backend/app/domain/oqi_ontology_impact/`, or their corresponding ORM/repository/migration files may
be created, modified, or deleted. No API router file. No frontend file. No `CDD-036`/`CDD-037`/their
Artifact Authorizations.

## 5. Migration-head mechanical regression files

Per this session's own OQI3-GA precedent (identify these at governance time, not after
implementation starts): adding migration `0024_oqi5_remediation_foundation` will require the same
mechanical Alembic-head literal bump already exercised at every prior OQI transition, in exactly the
files `test_runtime_architecture.py`'s `AUTHORIZED_CHANGED_PATHS` already tracks for this purpose
(the same set bumped at OQI4-I: `test_decision_engine.py`, `test_gate_v_agent_postgres.py`,
`test_governance_engine.py`, `test_knowledge_engine.py`, `test_oqi_business_rule_postgres.py`,
`test_oqi_cross_source_postgres.py`, `test_oqi_quality_postgres.py`,
`test_persistence_integration.py`, `test_runtime_architecture.py` itself, plus the newly-added
`test_oqi_ontology_impact_postgres.py` from OQI4). **This mechanical bump is pre-authorized for I1
under the same "mechanical migration-head consequence" precedent used throughout OQI2-OQI4** — it is
additive to Sec2's 9-path CREATE total as a MODIFY, bringing I1's effective total to `CREATE=9 /
MODIFY=10 / TOTAL=19` at actual implementation time, verified exactly (not assumed) against the
real file list when `0024` is added, exactly as OQI3-GA and OQI4-I both required. I2's own migration
(`0025`) will require the identical mechanical class of update to the same file set plus
`test_oqi_remediation_i1.py`, applied at I2 implementation time under the same precedent.

## 6. Table count expectations

```
Pre-OQI5:        86  (verified, OQI4-VM post-merge proof)
Post-OQI5-I1:    90  (86 + 4)
Post-OQI5-I2:    94  (90 + 4)
```

## 7. Enum-width verification (performed at governance time, per OQI2/OQI3 lesson)

`RemediationCaseStatus` longest value `EXTERNAL_EXECUTION_REPORTED` = 25 chars → `String(32)` safe.
`RemediationCandidate.basis` longest value `OQI2_CONSISTENCY` = 16 chars → `String(32)` safe.
`AgentRecommendation.recommendation_type` longest value `NO_REMEDIATION_RECOMMENDED` = 26 chars →
`String(32)` safe. `AgentRun.result_state` longest value `REJECTED_OUTPUT` = 15 chars → `String(32)`
safe. `RemediationAuthorization.status` values `PENDING`/`APPROVED`/`REJECTED` = max 8 chars →
`String(16)` safe (mirrors `gate_s_approval_requests.status String(16)` exactly).

## 8. Revision-identifier length verification

`0024_oqi5_remediation_foundation` = 33 characters — **exceeds the 32-character
`alembic_version.version_num` constraint** that caused OQI2's own migration-revision defect.
**Corrected identifier, frozen here rather than discovered during I1 implementation:
`0024_oqi5_remediation`** (21 characters, safe), filename remains
`0024_oqi5_remediation_foundation.py` (filenames are unconstrained; only the `revision` string value
is constrained, exactly the OQI2 precedent). `0025_oqi5_agent_reasoning` = 25 characters, safe as
originally stated — no correction needed for I2's revision string.

## 9. Amendment to Sec28 of CDD-043

CDD-043 Sec28 states the I1 revision string as `0024_oqi5_remediation_foundation`; this Artifact
Authorization Sec8 corrects it to `0024_oqi5_remediation` for the `revision` value specifically
(filename unchanged) — the same class of narrow, disclosed, mechanical correction OQI2 applied via
its own migration-revision-length companion amendment, captured here at governance time before any
implementation occurs rather than requiring a separate future correction cycle.

## 10. Final accounting

```
I1 (authorized now):            CREATE 9 / MODIFY 0 / DELETE 0 / TOTAL 9
                                  (+1 MODIFY at actual I1 implementation time for the
                                   mechanical migration-head bump, pre-authorized per Sec5)
I2 (named, gated behind I1 closure): CREATE 9 / MODIFY 1 / DELETE 0 / TOTAL 10
                                  (+1 MODIFY at actual I2 implementation time, same class)
```
