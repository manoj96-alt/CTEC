# CDD-056 — Production OQI Explicit Evaluation Orchestration

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-044-Ontology-Quality-Intelligence-Criticality-Business-Impact-Explainable-Reliance.md`,
`CDD-042-Ontology-Quality-Intelligence-Ontology-Impact-Intelligence.md`, `CDD-051` (H5 Timeliness), and this
session's own Production-Orchestration-DR + Production-Ingestion-DR (the exact discovery evidence this
document converts into a frozen governance contract)
Governs: `main` authoritative state `5e1a859df5c8608e7d5cfa0fe6b5b93e94119962` (OQI4-R1-VM's independently
verified merge commit, independently re-confirmed unchanged as of this document's own publication)
Classification: NEW PRODUCTION CAPABILITY — COMPOSITION ONLY (zero new domain logic, zero schema change, one
new narrow API action, one new application-service module)

## 1. Purpose

Freezes the exact architecture, authorization boundary, API contract, implementation-path set, and
verification contract for Noetva's first genuine production-reachable OQI evaluation chain. Discovery
(Production-Orchestration-DR, Production-Ingestion-DR) established that every DQ dimension, OQI4, OQI6, and
Reliance evaluator today has zero production trigger — all are test-only or demo-only. This document
authorizes building the smallest correct trigger: **one explicit, authenticated, tenant-scoped production API
action that composes already-existing, already-verified evaluators in their existing dependency order, with
zero new domain logic and zero schema change.**

## 2. Independent re-verification — authoritative baseline

`origin/main`, local `main`, and GitHub `main` all independently re-confirmed equal to
`5e1a859df5c8608e7d5cfa0fe6b5b93e94119962`. PR #190 independently reconfirmed `MERGED`. Migration head
independently reconfirmed `0044_oqi4_r1_current_tenancy`, single head. Table count independently reconfirmed
`123`. Working tree independently reconfirmed clean except the inherited, pre-existing untracked
`docs/product/`.

## 3. Discovery re-validation (binding)

Independently re-confirmed via direct source inspection during this governance phase (not merely trusted from
the DR reports):
```
Zero connectors are "Demo Connected" -- confirmed directly from
    app/domain/ontology/connector_catalog.py's own docstring and every entry's `maturity` field
    (all "Skeleton Available" or "Roadmap").
POST /api/v1/supplier-risk/assessments accepts observation-shaped payloads but persists them only as
    opaque audit JSON for Gate F's own ERM/SRM/ASM/KRM/DRM/GRM pipeline -- zero writes to
    SourceObjectORM/SourceFieldORM/FieldValueEvidenceORM found anywhere in app/integration/.
All nine DQ dimension evaluators, OQI4, and OQI6 have zero production callers -- confirmed by exhaustive
    grep across app/ excluding /tests/; the sole caller of every one is demo_oqi_seeder.py.
```
The Supplier Risk pipeline remains explicitly out of scope and is NOT reinterpreted as OQI ingestion.

## 4. Governed V1 architecture (binding)

```
OPTION C/E -- EXPLICIT TRIGGER, HYBRID-READY INTERNAL ORCHESTRATOR

Authenticated explicit evaluation action (new, narrow production API)
        |
Production OQI Orchestrator (new, narrow application service -- composition only)
        |
Existing governed evidence/rule/policy state (read-only lookups against already-existing tables)
        |
DQ Evaluation (existing evaluators, called unmodified, in existing dependency order)
        |
OQI4 Ontology Impact (existing evaluator, called unmodified)
        |
OQI6 Business Impact (existing evaluator, called unmodified)
        |
Reliance (existing evaluator, called unmodified, same transaction as Business Impact per existing design)
```
The trigger is explicit today; the internal chain is designed so that a future automatic trigger (real
connector, governed ingestion event) can call the identical orchestrator without internal redesign — the
trigger changes, the governed evaluation chain does not.

## 5. Central governance invariant (binding)

```
A caller may explicitly request governed OQI evaluation for an authorized tenant/context, but the
orchestration layer must never create authority, invent evidence, bypass dimension prerequisites, weaken
tenant isolation, convert NOT_EVALUABLE into success, or change existing domain semantics.
```
The orchestrator is **composition**, never new DQ logic, new impact logic, new Reliance logic, or new
authority.

## 6. Tenant authority (binding)

```
AUTHENTICATED PRINCIPAL (verified OIDC JWT, TrustedPrincipal.tenant_id)
        |
TRUSTED TENANT CONTEXT
        |
Production OQI Orchestrator
        |
the SAME tenant_id threaded through every stage -- DQ, OQI4, OQI6, Reliance
```
The orchestrator never switches tenant context mid-chain. Frozen invariants:
```
REQUESTED SUBJECT ≠ TENANT AUTHORITY
REQUEST BODY ≠ TENANT AUTHORITY
GLOBAL ROW IDENTITY ≠ TENANT AUTHORITY
SERVICE TENANT VALIDATION ≠ DATABASE TENANT ENFORCEMENT
```
Both layers (service-level tenant threading and the already-closed R1-R4 database-level tenant-qualified
FKs) remain independently meaningful and are both exercised by this orchestrator.

## 7. Exact API authorization (binding)

```
Route:          POST /api/v1/oqi/evaluate
Scope:          oqi-evaluation:trigger
```
Independently re-derived from live repository convention (`app/api/oqi/router.py`'s existing action-scope
naming: `oqi-remediation:authorize`, `oqi-remediation:report-execution`, `oqi-reference-evidence:configure`,
`oqi-reference-evidence:verify` — each a narrow `<domain>:<action>` pair, never the broad `oqi:read` scope
reused for a write/action). `oqi-evaluation:trigger` follows this exact convention: a new, narrow domain
segment distinct from `oqi-remediation`/`oqi-reference-evidence`/`oqi:read`.

## 8. Request contract (binding)

```json
{
  "correlation_id": "UUID (optional, caller-supplied, non-authoritative, purely for tracing)",
  "information_element_requirement_id": "UUID (required)",
  "source_record_reference": "string (required, 1-1000 chars, identifies an already-persisted governed
                               record whose evidence is to be evaluated -- never fabricated evidence;
                               absence of matching evidence correctly yields NOT_EVALUABLE, not an error)",
  "business_process_id": "UUID (required)",
  "business_process_version": "integer (required)"
}
```
No `tenant_id` field exists in this contract at all. `information_element_requirement_id` +
`source_record_reference` anchor the record-shaped dimensions (COMPLETENESS, VALIDITY, CONSISTENCY,
ACCURACY, REASONABLENESS, CONFORMITY); `business_process_id`/`business_process_version` anchor H5 Timeliness
policy lookup and OQI6 dependency resolution (both keyed on `business_process_id` in existing schema).
INTEGRITY-STRUCTURAL and INTEGRITY-REFERENCE evaluate relationship/reference state, which is resolved from
the same `information_element_requirement_id`'s already-governed ontology position — no additional field
required. No field in this contract accepts fabricated evidence, fabricated finding state, fabricated
ontology/business impact, fabricated Reliance, human authorization, or agent recommendation.

## 9. Response contract (binding)

```json
{
  "correlation_id": "UUID",
  "evaluated_at": "timestamp",
  "dimensions": [
    {
      "dimension": "COMPLETENESS | VALIDITY | CONSISTENCY | ACCURACY | REASONABLENESS | CONFORMITY |
                     INTEGRITY_STRUCTURAL | INTEGRITY_REFERENCE | TIMELINESS",
      "status": "EVALUATED | NOT_EVALUABLE | FAILED",
      "finding_id": "UUID | null",
      "outcome": "<dimension-native outcome value, e.g. SATISFIED/VIOLATED for H5, or the applicable
                   existing domain vocabulary -- never a fabricated generic outcome> | null"
    }
  ],
  "ontology_impact": {"status": "EVALUATED | NOT_ATTEMPTED | FAILED", "outcome": "ImpactOutcome | null"},
  "business_impact": [{"dependency_id": "UUID", "status": "...", "outcome": "BusinessImpactOutcome | null"}],
  "reliance": {"status": "...", "state": "RelianceState | null"}
}
```
Transport success (`HTTP 202`) and domain/quality success are explicitly distinct concepts: an
`HTTP 202` response containing nine `NOT_EVALUABLE` dimension entries is a **fully successful** orchestration
run, not a failure. No numeric trust score is invented. No single boolean collapses the nine independent
dimension outcomes.

## 10. Authoritative nine-dimension enumeration (binding, re-derived)

Independently re-derived from `app/domain/oqi/quality_rule.py`'s `QualityDimension` enum (7 members:
`COMPLETENESS`, `VALIDITY`, `CONSISTENCY`, `ACCURACY`, `CONFORMITY`, `INTEGRITY`, `TIMELINESS`) plus
`REASONABLENESS` (deliberately excluded from that enum, BusinessRule-shaped, its own governed identity on
`BusinessRule.dimension`) plus the `INTEGRITY` member's own documented split into STRUCTURAL and REFERENCE
sub-families (each with its own dedicated Finding storage family and evaluator):
```
1. COMPLETENESS            OqiQualityEvaluationService
2. VALIDITY                OqiQualityEvaluationService
3. CONSISTENCY              OqiCrossSourceEvaluationService
4. ACCURACY                 OqiAccuracyEvaluationService
5. REASONABLENESS           OqiBusinessRuleEvaluationService
6. CONFORMITY               OqiConformityEvaluationService
7. INTEGRITY-STRUCTURAL     OqiIntegrityStructuralEvaluationService
8. INTEGRITY-REFERENCE      OqiIntegrityReferenceEvaluationService
9. TIMELINESS               OqiTimelinessEvaluationService
```

## 11. OQI1 Completeness + Validity reachability (binding decision)

**Outcome A — preferred, selected.** `OqiQualityEvaluationService.evaluate_current_state(rule, subject)` is
real, fully tested (`test_oqi_quality_postgres.py`, `test_oqi_quality_evaluation_service.py`,
`test_oqi_provenance.py`, `test_oqi_h1_reliance_coverage_crown.py`), and architecturally sound. It was never
production/demo-integrated only because the demo seeder's own coverage happened to start at H2 and never was
extended backward — a scope gap, not a domain defect (Production-Ingestion-DR's Outcome-C investigation
findings). The orchestrator composes it directly: no OQI1 domain-semantic change, no new implementation path
beyond the orchestrator itself. Completeness and Validity are proven through the new orchestration boundary
alongside all other seven dimensions — an eight-of-nine proof is explicitly forbidden by this document.

## 12. Dimension prerequisite model (binding)

```
COMPLETENESS/VALIDITY   -- requires an ACTIVE QualityRule for the subject's dimension; absent -> NOT_EVALUABLE
CONSISTENCY             -- requires an ACTIVE correspondence + ≥2 governed source participants;
                            absent -> NOT_EVALUABLE
ACCURACY                -- requires an ACTIVE QualityRule (dimension=ACCURACY) + qualifying Reference
                            Evidence; absent -> NOT_EVALUABLE
REASONABLENESS          -- requires an ACTIVE BusinessRule; absent -> NOT_EVALUABLE
CONFORMITY              -- requires an ACTIVE QualityRule (dimension=CONFORMITY); absent -> NOT_EVALUABLE
INTEGRITY-STRUCTURAL    -- requires the relevant relationship-cardinality state to exist; absent -> the
                            existing domain's own NOT_EVALUABLE-equivalent
INTEGRITY-REFERENCE     -- requires the relevant reference-resolution state to exist; absent -> the
                            existing domain's own NOT_EVALUABLE-equivalent
TIMELINESS              -- requires an ACTIVE TimelinessPolicy for the (information_element_requirement_id,
                            business_process_id, business_process_version) triple; absent -> NOT_EVALUABLE
                            (already proven exhaustively by test_no_active_policy_is_not_evaluable et al.)
```
The orchestrator performs read-only lookups against each dimension's own already-existing rule/policy
repository (mirroring H5's own established `policy_lookup`/`semantic_mapping_lookup` composition pattern) and
invokes a dimension's `evaluate_current_state` **only** when its prerequisite is genuinely present. The
orchestrator never manufactures a prerequisite. Absent-prerequisite dimensions are reported `NOT_EVALUABLE`
in the response, never omitted silently and never conflated with `FAILED`.

## 13. Multi-source model (binding)

CONSISTENCY's existing `Correspondence`-based multi-source mechanism (`OqiCrossSourceCorrespondenceRepositoryImpl.get_active`)
is reused unmodified. If fewer than the required governed participants exist for the requested subject, the
orchestrator preserves existing domain behavior exactly (`NOT_EVALUABLE`) — it never interprets the absence of
a second source as an inconsistency finding.

## 14. Evaluator invocation model (binding)

```
Independent, evaluated in this fixed order (no dimension mutates another's evidence or Finding state):
  1. COMPLETENESS
  2. VALIDITY
  3. CONSISTENCY (state-dependent: correspondence)
  4. ACCURACY (policy-dependent: Reference Evidence)
  5. REASONABLENESS (policy-dependent: BusinessRule)
  6. CONFORMITY (policy-dependent: QualityRule)
  7. INTEGRITY-STRUCTURAL (state-dependent: relationship cardinality)
  8. INTEGRITY-REFERENCE (state-dependent: reference resolution)
  9. TIMELINESS (policy-dependent: TimelinessPolicy)
```
Every dimension's evaluation is independent of every other's outcome — none is skipped because another
returned `VIOLATED`, and none aggregates another's Finding content. Order is fixed and deterministic purely
for response-shape stability, not because of a genuine data dependency between dimensions.

## 15. Finding lifecycle (binding)

Existing lifecycle semantics preserved exactly and unmodified: new Finding creation, existing-open-Finding
reevaluation, resolution only through a genuine reevaluation outcome, `NOT_EVALUABLE` behavior, stable
deterministic Finding identity, immutable evaluation history, mutable Current*-equivalent projection where
each dimension defines one. `remediation ≠ resolution` is preserved — this orchestrator never resolves a
Finding by any means other than a dimension's own existing reevaluation logic.

## 16. DQ→OQI4 boundary (binding)

Re-derived exact repository method names: `OqiOntologyImpactEvaluationRepositoryImpl.resolve_finding_subject`,
`.resolve_finding_origin`, and `OqiOntologyImpactEvaluationService.evaluate_current_state`. The orchestrator
collects every `(finding_family, finding_id)` pair produced or already-open from step 14, and calls
`OqiOntologyImpactEvaluationService.evaluate_current_state(tenant_id=..., finding_family=..., finding_id=...)`
for each — the exact existing family-agnostic mechanism, unmodified. No dimension-specific ontology-impact
semantics are added.

## 17. OQI4 semantics preservation (binding)

All existing OQI4 rules preserved unmodified: direct impact, propagated impact, `IMPACT_UNKNOWN`, contextual
criticality, the authority firewall, `CurrentOntologyImpact` lifecycle. The orchestrator never hardcodes
business criticality and never reinterprets Finding severity as ontology/business criticality:
```
FINDING SEVERITY ≠ ONTOLOGY/BUSINESS CRITICALITY
```

## 18. OQI4→OQI6 boundary (binding)

Re-derived exact existing chain: `CurrentOntologyImpact → BusinessImpactEvaluation → CurrentBusinessImpact`
via `OqiBusinessImpactService.evaluate_business_impact_for_dependency`, unmodified, called once per ACTIVE
`BusinessDependency` resolved for the requested `business_process_id` via the existing dependency-lookup
mechanism. No Business Impact logic is duplicated inside the orchestrator. The previously observed
`considered_current_impact_id` plain FK remains **NON-BLOCKING / DEFERRED TO OQI-H-VM** — independently
re-confirmed this session that `get_current_impacts_for_subject` performs an explicit
`WHERE tenant_id == tenant_id` filtered query before the plain FK is ever exercised, so the selected
`current_impact_id` is always the requesting tenant's own row. This document does **not** claim the
underlying PostgreSQL structure is tenant-qualified — only that the existing service-level selection path
this orchestrator calls is safe.

## 19. Reliance (binding)

Exactly the existing three states, unmodified, no fourth state, no numeric trust score, no
orchestration-specific state:
```
RELIANCE_SUPPORTED
RELIANCE_AT_RISK
RELIANCE_UNKNOWN
```
The established rule that open findings determine the fundamental supported/at-risk computation before any
pending-remediation reason-code handling affects explanation is preserved exactly; this orchestrator (ending
at Reliance, per §21) never introduces pending-remediation state at all.

## 20. Reliance replay sensitivity (carried forward, not fixed)

The known P3 (`oqi_reliance_evaluations` history-row-per-replay) is carried forward unmodified. Explicit-
trigger V1 materially limits replay frequency compared with continuous automatic evaluation (bounded by how
often an authorized caller explicitly re-triggers), so it is **not** elevated to a correctness blocker by this
architecture. Not fixed in this phase.

## 21. OQI5 explicit exclusion (binding)

Production Orchestration v1 ends at Reliance. It explicitly excludes candidate generation, LLM/agent
reasoning, agent recommendation, human authorization, remediation execution, and post-remediation
reevaluation — all reserved for a separate, later, independently governed
**Production-Remediation-Orchestration** initiative. Preserved: `AGENT REASONING ≠ HUMAN AUTHORITY`,
`RECOMMENDATION ≠ AUTHORIZATION`, `REMEDIATION ≠ RESOLUTION`.

## 22. Transaction boundaries (binding, re-derived)

```
Each DQ dimension evaluation  -> its own existing transaction (unchanged from today's per-dimension
                                  service behavior)
OQI4 evaluation                -> a new, separate transaction per (finding_family, finding_id) pair
                                  (mirrors R1-R4's own independently-transacted evaluation pattern)
OQI6 Business Impact + Reliance -> the existing shared transaction already designed into
                                  OqiBusinessImpactService (unchanged)
```
No single transaction spans the entire chain. The orchestrator's own role is to sequence calls across these
existing transaction boundaries, not to introduce a new enclosing transaction.

## 23. Partial-failure contract (binding)

```
DQ succeeds / OQI4 fails            -> valid DQ Finding/evaluation persisted and returned as EVALUATED;
                                        OQI4 stage reported FAILED (not NOT_EVALUABLE); safely retriable
                                        (idempotent identity unchanged)
OQI4 succeeds / OQI6 fails          -> valid CurrentOntologyImpact state preserved; OQI6 stage reported
                                        FAILED; safely retriable
Business Impact succeeds / Reliance fails -> Business Impact state preserved unmutated; Reliance stage
                                        reported FAILED; safely retriable (existing same-transaction
                                        boundary already prevents partial corruption within this specific
                                        pair)
Dimension NOT_EVALUABLE             -> orchestration continues normally to the next dimension and downstream
                                        stages that have their own real prerequisites; overall HTTP 202
Dimension unexpected technical failure -> reported FAILED, never misrepresented as NOT_EVALUABLE
```
Frozen distinction: `DOMAIN NOT_EVALUABLE ≠ TECHNICAL FAILURE` — these are always reported as distinct
status values in the response contract (§9), never conflated.

## 24. Idempotence (binding, proof basis re-derived)

Every stage the orchestrator calls already has a deterministic tenant-aware UUID5 identity and an idempotent
insert (`insert_evaluation_idempotent`/`ON CONFLICT DO NOTHING`, `upsert_current_impact`/`upsert_finding`),
independently proven this session and across the entire R1-R4/H1-H5 lineage
(`test_replay_is_idempotent`, `test_concurrent_identical_evaluation_converges_without_duplicate`,
`test_repeated_identical_evaluation_is_idempotent`). The orchestrator introduces no new write logic of its
own — it calls only these existing idempotent methods — so explicit retriggering is safe by construction,
proven by re-running the existing suites, not merely assumed from UUID5 usage alone.

## 25. Concurrency (binding)

```
same tenant + same subject + simultaneous evaluation  -> existing advisory-lock serialization
                                                          (test_concurrent_reliance_evaluation_serializes_
                                                          via_advisory_lock) already handles this
same tenant + different subject                        -> existing non-blocking concurrent behavior
                                                          (test_concurrent_different_tenants_do_not_
                                                          block_each_other's same-tenant analog) already
                                                          proven
different tenant + same externally-shaped identifier    -> tenant-qualified natural keys/FKs (R1-R4)
                                                          already prevent collision
```
No orchestrator-level locking is added — unnecessary, since every stage it calls already owns correct
concurrency behavior; adding a redundant lock would be defensive decoration, not a correctness requirement.

## 26. Observability/correlation (binding)

The existing `SecurityAuditService.record` pattern (already used by the Supplier Risk pipeline) plus each
stage's own existing deterministic IDs (`evaluation_id`, `finding_id`, `current_impact_id`,
`business_dependency_id`) are sufficient to correlate one explicit evaluation request across every stage,
keyed by the caller-supplied (non-authoritative) `correlation_id`. **No new database schema is required** for
this — confirmed by design, not merely assumed (§27).

## 27. Database impact (binding)

```
NO SCHEMA CHANGE
NO MIGRATION
NO ORM CHANGE
```
Every table the orchestrator touches already exists and is already correctly structured, including the
just-closed OQI4-R1 correction. Confirmed by design: the orchestrator is read/compose-only against existing
persistence, with zero new persisted state of its own.

## 28. API impact (binding)

Exactly one narrow authenticated POST action:
```
Route:      POST /api/v1/oqi/evaluate
Scope:      oqi-evaluation:trigger
Router:     backend/app/api/oqi/router.py (registration only; no other route touched)
Schemas:    backend/app/api/oqi/schemas.py (new request/response models only)
```

## 29. Frontend impact (binding)

**FRONTEND CHANGE NOT REQUIRED FOR CORRECTNESS.** The existing frontend continues reading persisted OQI state
through the already-existing, already-unmodified read endpoints. An "Evaluate" UX affordance is future,
optional polish, not authorized or required by this document.

## 30. Docker/runtime impact (binding)

```
same backend process
synchronous invocation
no queue, no worker, no scheduler, no cron, no Kafka, no Redis, no Celery
no new container
no new environment variable
```
Confirmed by design: Option C/E's synchronous, in-process composition needs none of the above — independently
re-confirmed this session that zero such infrastructure exists anywhere in this repository today.

## 31. Real connector — explicitly deferred, mandatory before final certification (restated)

Production Orchestration v1 does **not** implement a connector. Before final Noetva Engineering
Certification, at least one genuine production connector must prove the complete chain from a real external
enterprise source through `SourceSystem`/`SourceObject`/`SourceField`/`FieldValueEvidence` into this same
Production OQI Orchestrator and through to Reliance. Preferred first candidate, per current repository
direction (`connector_catalog.py`'s own "REST API — Skeleton Available" entry): a **REST API connector**.
This governance phase does not authorize that work.

## 32. OQI2 deferred observation (restated, unchanged)

```
QualityComparisonFindingORM.latest_evaluation_id
P2 -- NOT A PRODUCTION-ORCHESTRATION BLOCKER -- MANDATORY OQI-H-VM / OQI-FAV TARGET
```
Independently re-confirmed this phase: the selected orchestration path's CONSISTENCY-dimension read never
dereferences this pointer. Not fixed here.

## 33. OQI3 deferred observation (restated, unchanged)

```
BusinessRuleFindingORM.latest_evaluation_id
P2 -- NOT A PRODUCTION-ORCHESTRATION BLOCKER -- MANDATORY OQI-H-VM / OQI-FAV TARGET
```
Independently re-confirmed this phase: `resolve_finding_subject`'s REASONABLENESS/OQI3 branch already fails
closed on tenant mismatch after dereferencing this pointer (a genuine service-level defense-in-depth,
independently re-read from source this session). Not fixed here.

## 34. OQI4→OQI6 deferred structural observation (restated, resolved to non-blocking)

```
considered_current_impact_id (plain FK, oqi_business_impact_evaluations -> current_ontology_impacts)
P2 -- NON-BLOCKING -- MANDATORY FINAL HORIZONTAL AUDIT TARGET
```
Independently re-confirmed this phase (§18): the one production-relevant read path
(`get_current_impacts_for_subject`) is tenant-filtered by an explicit `WHERE tenant_id == tenant_id` clause
before the plain FK target is ever selected. Not fixed here.

## 35. Frontend Docker healthcheck (restated, unchanged)

Inherited internal-loopback discrepancy remains P3. Not investigated or fixed in this phase. Serving-path
proof (`HTTP 200`) remains the authoritative health signal for this phase's own verification (§55 region of
the governing prompt).

## 36. Exact implementation-path authorization (binding — a maximum permitted write set)

```
CREATE = 2
MODIFY = 2
DELETE = 0
TOTAL  = 4
```
```
CREATE  backend/app/application/oqi_evaluation_orchestration_service.py
        The new Production OQI Orchestrator: composes existing dimension evaluators (§14), OQI4 (§16-17),
        OQI6 (§18), and Reliance (§19) in the exact order and transaction boundaries frozen above. Contains
        zero new domain/authority logic -- read-only rule/policy lookups against existing repositories plus
        sequenced calls to existing `evaluate_current_state`/`evaluate_business_impact_for_dependency`/
        `evaluate_reliance_for_subject` methods, unmodified.

CREATE  backend/app/tests/test_oqi_evaluation_orchestration_postgres.py
        The production/adversarial orchestration test file implementing the verification contract frozen in
        SS42-SS50 below.

MODIFY  backend/app/api/oqi/router.py
        Exactly one new route (POST /api/v1/oqi/evaluate) plus one new dependency-provider function
        (mirroring the existing `oqi_service`/`reference_evidence_service` pattern at lines 92-101 of the
        current file). No existing route, provider, or handler modified.

MODIFY  backend/app/api/oqi/schemas.py
        Exactly the new request/response Pydantic models described in SS8-SS9. No existing schema modified.
```
No `dependency_container.py` change is required — independently re-derived from the existing
`oqi_service`/`reference_evidence_service` pattern, which constructs each OQI application service directly
inside `router.py` from the already-available `oqi_session` dependency, never through the central container.
No path beyond the four above is authorized.

## 37. Forbidden implementation paths (binding, exhaustive)

Alembic migrations; ORM models; existing DQ/OQI4/OQI6/Reliance domain semantics; OQI5 implementation; agent
framework; human authorization; remediation execution; the Supplier Risk `RuntimeOrchestrator`/Gate F
adapters; connector implementations; `connector_catalog.py`'s maturity labels; frontend; Docker Compose
topology; database schema; CDD-042, CDD-044, CDD-050, CDD-051, CDD-052, CDD-053, CDD-054, CDD-055, or their
own frozen Artifact Authorizations. No DELETE. No opportunistic cleanup. No refactoring.

## 38. Production-Orchestration-I STOP conditions (binding, exhaustive)

```
 1. authoritative main moves materially.
 2. this document's own governance hash drifts before implementation begins.
 3. any file outside the exact four SS36 paths requires a write.
 4. tenant authority cannot be sourced exclusively from TrustedPrincipal.tenant_id.
 5. the request contract is found to require caller-supplied tenant authority.
 6. OQI1 cannot be composed without modifying OqiQualityEvaluationService's own domain semantics.
 7. any of the nine dimensions cannot be reached without modifying that dimension's own evaluator.
 8. OQI4, OQI6, or Reliance requires semantic modification.
 9. OQI5 becomes necessary for deterministic evaluation to complete.
10. the Supplier Risk pipeline requires modification.
11. any database schema change becomes necessary.
12. any ORM modification becomes necessary.
13. a new queue/worker/scheduler becomes necessary for correctness.
14. the implementation path set exceeds the exact four SS36 paths.
15. OQI2, OQI3, or the OQI4->OQI6 observation is found to require correction for this orchestrator to be
    safe (re-elevating any from P2/non-blocking to blocker).
16. cross-tenant safety cannot be maintained end-to-end through the new orchestration boundary.
17. idempotent retrigger cannot be guaranteed for any composed stage.
18. partial failure at any stage is found to corrupt existing authoritative state.
19. any H1-H5/OQI4/OQI6/Reliance crown/regression value changes semantically as a result.
20. whole-package mypy, black, isort, or ruff fails as a result of this correction (including any
    formatter-only hunk not already exactly authorized -- return to governance rather than
    self-authorize, per this session's own established GA2 precedent).
21. full clean-candidate regression fails as a result of this correction.
22. Docker proof differs materially from host proof.
23. any P0 appears, or any material P1 remains unresolved outside the exact frozen scope.
```

## 39. VM/merge gate (binding, restated)

Production-Orchestration-VM must independently re-derive every item in SS38's proof surface plus: exact
ancestry; governance hash; exact diff; the full all-nine-dimension crown matrix (SS42); cross-dimension,
multi-source, cross-tenant, idempotent-retrigger, partial-failure, and `NOT_EVALUABLE` adversarial proofs
(SS43-SS49); authority-firewall proof (SS50); full backend/static/frontend regression; fresh `--no-cache`
Docker proof; CI exact-head status; confirmation that OQI2/OQI3/the OQI4->OQI6 observation/Reliance
replay-sensitivity/frontend-healthcheck P2/P3 register remain explicitly deferred, not silently solved; and
confirmation that OQI5/remediation orchestration was not accidentally implemented. Merge requires `P0 = 0`
and `P1 = 0`.

## 40. All-nine-dimension verification matrix (binding, mandatory)

For each of the nine dimensions, Production-Orchestration-I/VM must prove through the new orchestration
boundary, using each dimension's own native domain vocabulary (never a forced generic SATISFIED/VIOLATED
where the domain model differs):
```
applicable + satisfied-equivalent outcome
applicable + violated/finding-equivalent outcome, where semantically supported by that dimension
NOT_EVALUABLE where a genuine prerequisite is absent
tenant isolation (cross-tenant attempt through this same boundary rejected)
stable retrigger behavior (idempotent convergence)
```

## 41. Cross-dimension test contract (binding)

At least one end-to-end subject where multiple dimensions are evaluated together must prove: multiple
Findings created/updated, differing dimension outcomes, one subject, one tenant, correct OQI4 impact
aggregation across all contributing Findings, correct OQI6 Business Impact, correct Reliance. No dimension
may overwrite another's evidence or Finding state.

## 42. Multi-source test contract (binding)

At least one test with Source A + Source B evidence under an active `Correspondence` for the same governed
subject, proving CONSISTENCY participates correctly through the orchestration boundary, plus a
missing-correspondence/insufficient-source case proving correct `NOT_EVALUABLE` preservation.

## 43. Cross-tenant adversarial test contract (binding)

A Tenant A authenticated principal attempting to reference Tenant B's subject/evidence identifiers through
this new endpoint must fail closed — not merely rejected by request-schema validation, but genuinely
verified (via direct persistence inspection, matching this session's own established adversarial-proof
standard) that no Tenant B evaluation/Finding/impact/Business-Impact/Reliance data is exposed or mutated.

## 44. Tenant-authority request test contract (binding)

Explicit proof that a caller cannot alter tenant authority through any request-body or query field —
`tenant_id` is absent from the public request contract entirely (§8); this absence itself must be verified,
not merely asserted.

## 45. Idempotent-retrigger test contract (binding)

Calling the same explicit evaluation twice must prove: no uncontrolled duplicate current state, stable
Finding identities, correct (append-only, where that is the existing domain design) evaluation-history
behavior, correct Current* pointers, correct OQI4/OQI6/Reliance state. Domain convergence is the required
proof standard — not byte-identical history rows where the existing domain design is intentionally
append-only (mirroring the already-understood Reliance replay-sensitivity nuance, §20).

## 46. Partial-failure/retry test contract (binding)

At least one deterministic-failure-seam case (minimum: DQ persists successfully, OQI4 stage fails) followed
by retry, proving valid DQ state preserved, no corrupted Current* pointer, retry converges, downstream state
eventually correct.

## 47. NOT_EVALUABLE test contract (binding)

Using sparse but legitimate persisted evidence, prove: the API request succeeds as a transport/action
(`HTTP 202`), the relevant dimension(s) report `NOT_EVALUABLE`, no fabricated Finding is created, and
downstream behavior (OQI4/OQI6/Reliance) remains semantically correct given the absence.

## 48. Authority-firewall test contract (binding)

Prove the orchestrator does not authorize remediation, execute remediation, create human approval, or
convert an agent recommendation into authority — trivially true by construction (§21) but must be proven,
not merely asserted, by confirming zero `RemediationAuthorization`/`AgentRecommendation` row is created by
any orchestrator call.

## 49. Existing crown regressions (binding, exact files re-derived)

```
backend/app/tests/test_oqi_quality_postgres.py                          (OQI1)
backend/app/tests/test_oqi_quality_evaluation_service.py                (OQI1)
backend/app/tests/test_oqi_h1_reliance_coverage_crown.py                (OQI1-adjacent crown)
backend/app/tests/test_oqi_h2_accuracy_reasonableness_crown.py          (OQI2/H2)
backend/app/tests/test_oqi_h3_conformity_crown.py                       (H3)
backend/app/tests/test_oqi_h4_integrity_authorization_and_tenant_isolation.py (H4)
backend/app/tests/test_oqi_h5_timeliness_crown.py                       (H5)
backend/app/tests/test_oqi_ontology_impact_postgres.py                  (OQI4, includes OQI4-R1-TI matrix)
backend/app/tests/test_oqi_business_impact.py                           (OQI6, R1/R2/R3 tenant-isolation)
backend/app/tests/test_oqi_provenance.py                                (cross-cutting provenance)
backend/app/tests/test_runtime_architecture.py                          (single-construction-site firewall,
                                                                           dirty-tree firewall)
```
All must remain fully green, unmodified in their own existing assertions.

## 50. Full backend regression, static quality, frontend regression (binding, restated)

Full `pytest app/tests` with `0` unexplained failures (exact count recorded at I/VM time, not pre-guessed);
`black --check`, `isort --check-only`, `ruff check`, whole-package `mypy app`; frontend `npm test`,
`npm run lint`, `npx tsc --noEmit`, `npm run build` — all mandatory, all using repository-canonical commands,
full relevant package scope, no unexplained exclusions.

```
FORMATTER-ONLY ≠ AUTOMATICALLY AUTHORIZED
```
Restated: any formatter-produced change outside SS36's exact authorization requires its own governance
reconciliation before implementation may rely on it.

## 51. Fresh Docker contract (binding, mandatory)

Fresh `docker compose build --no-cache`, genuinely fresh compose project/database, bound to the exact
implementation candidate SHA (structural file hashes read from inside the built image must match the
candidate's own hashes byte-for-byte, per this session's established binding method). Inside the fresh
runtime prove: backend starts; frontend serves `HTTP 200`; migration head remains `0044_oqi4_r1_current_tenancy`
(no later authorized migration exists); table count remains `123`; the new `POST /api/v1/oqi/evaluate`
endpoint is reachable; authenticated tenant authority is enforced; the full all-nine-dimension orchestration
crown (SS40) passes; cross-dimension (SS41), multi-source (SS42), cross-tenant (SS43), idempotent-retrigger
(SS45), partial-failure/retry (SS46), and `NOT_EVALUABLE` (SS47) cases all pass; OQI4/OQI6/Reliance/H5 crowns
pass; backend `/health` = `HTTP 200`; frontend serving = `HTTP 200`. The inherited frontend internal-loopback
healthcheck discrepancy (P3) is not required to disappear; serving-path proof remains authoritative.

## 52. Host↔Docker equivalence contract (binding)

| Proof | Host | Fresh Docker |
|---|---|---|
| New orchestration crown | required | required |
| All 9 dimensions | required | required |
| Cross-tenant | required | required |
| Multi-source | required | required |
| OQI4 | required | required |
| OQI6 | required | required |
| Reliance | required | required |
| H5 | required | required |
| API endpoint | required | required |
| Backend health | required | required |
| Frontend serving | required | required |

No host-only production claim is permitted.

## 53. Current PostgreSQL model (binding, preserved)

```
migration head = 0044_oqi4_r1_current_tenancy
table count = 123
```
No migration, table, FK correction, index, enum, or ORM change is authorized in this phase. Any discovered
necessity for one during implementation requires an immediate return to governance (SS38 item 11/12), not
self-authorization.

## 54. Future PostgreSQL Data Model & Schema Closure (restated, preserved)

Occurs after `OQI-H7` and `OQI-FAV`/`OQI-H-VM` corrections, before Product-wide Docker Closure. Scope
restated exactly per the governing prompt's own SS58 — not performed now.

## 55. Final OQI-FAV register (binding)

```
OQI2 latest_evaluation_id tenant-pointer observation           -- DEFERRED, unchanged
OQI3 latest_evaluation_id tenant-pointer observation           -- DEFERRED, unchanged
OQI4->OQI6 considered_current_impact_id structural observation -- DEFERRED, NON-BLOCKING, unchanged
Reliance evaluation-history replay sensitivity                  -- DEFERRED, P3, unchanged
frontend Docker internal-loopback healthcheck discrepancy       -- DEFERRED, P3, unchanged
zero working real connectors                                    -- DEFERRED, P2, large separate initiative
```
**OQI1 orchestration coverage must NOT remain on this register after Production-Orchestration-VM** — it is
proven in this phase's own implementation (SS11).

## 56. Roadmap register (restated, preserved)

```
Production-Orchestration-G  (this document)
        |
Production-Orchestration-I
        |
Production-Orchestration-VM
        |
Production-Remediation-Orchestration-DR/G/I/VM
        |
Real Enterprise Ingestion / REST Connector DR/G/I/VM
        |
OQI-H7 Final Integrated Hardening
        |
OQI-FAV / OQI-H-VM
        |
required corrections
        |
rerun OQI-FAV until P0=P1=P2=0
        |
PostgreSQL Data Model & Schema Closure
        |
Product-wide Docker Closure
        |
Noetva Engineering Certification
```

## 57. Final certification principle (restated, binding)

```
Explicit evaluation makes the OQI engine production-reachable. A genuine connector later makes enterprise
evidence ingestion production-reachable. Final Noetva engineering certification requires both.
```

## 58. Allowed claims

```
(after I/VM) "Noetva provides a governed, tenant-scoped production evaluation action that composes its
existing quality, ontology-impact, business-impact, and Reliance capabilities through a production-
reachable orchestration boundary."
(after I/VM, if all nine dimensions pass) "The production orchestration boundary has been verified across
all nine governed OQI data-quality dimensions."
```

## 59. Forbidden claims

```
"Noetva has production connectors."
"Noetva automatically ingests enterprise data."
"Noetva continuously evaluates data quality."
"All OQI tenant relationships are structurally isolated."
"All Current* pointers are structurally safe."
"OQI2 deferred pointer is fixed." / "OQI3 deferred pointer is fixed."
"OQI4->OQI6 deferred structural observation is fixed."
"OQI5 is production orchestrated." / "Remediation is production automated."
"OQI hardening is complete." / "PostgreSQL model is certified." / "Noetva engineering is complete."
```

## 60. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. `CDD-042`,
`CDD-044`, `CDD-050` through `CDD-055` and their respective Artifact Authorizations/amendments are
independently re-hashed immediately before this document's own publication and confirmed byte-identical to
their prior published values; none is modified by this document. `architecture/INDEX.md` independently
confirmed to list none of CDD-053/054/055, matching this repository's established precedent of not indexing
narrow correction/orchestration CDDs there — this document follows the same precedent and requires no index
update.

## 61. Authorization

This document is approved and published as a standalone governance artifact. Implementation against SS36's
exact four-path authorization may proceed under `Production-Orchestration-I`.
