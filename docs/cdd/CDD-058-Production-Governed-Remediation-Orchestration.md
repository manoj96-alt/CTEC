# CDD-058 — Production Governed Remediation Orchestration

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Governing authorities: CDD-043 (FROZEN, OQI5 — Governed Agentic Remediation; its domain/persistence/service
files are read-only consumed, never modified except the one narrow, explicitly-authorized repository
correction in §14 below), CDD-045 (FROZEN, OQI7 — the existing human-decide/execution-report production API,
consumed unmodified), CDD-056 (FROZEN, Production OQI Explicit Evaluation Orchestration — its individual
per-family/OQI4/OQI6/Reliance entrypoints are reused directly; its own top-level `evaluate()` wrapper is
deliberately NOT reused, per §9 below), CDD-057 (FROZEN, H5 tenant-scoped test-isolation amendment, unrelated,
unchanged)
Precedent: Production-Remediation-Orchestration-DR (discovery; this document freezes its recommended
architecture with one material refinement re-derived independently during this governance phase — see §9)
Classification: NEW PRODUCTION CAPABILITY — COMPOSITION ONLY (zero new domain logic, zero schema change, one
new narrow API action, one new application-service module, one narrow authorized correction to an existing
frozen repository)

## 1. Purpose

Freezes the exact architecture, authorization boundary, API contract, reevaluation composition, transaction
boundaries, implementation-path set, and verification contract that closes OQI5's proven production-
reachability gap: human authorization (`decide`) and execution reporting (`report-execution`) are already
production-reachable (CDD-045); nothing production-side has ever created the `PENDING RemediationAuthorization`
those routes act on. This document authorizes the smallest correct closure: **one new explicit, authenticated,
tenant-scoped "prepare remediation" action that composes already-existing, already-verified OQI5-I1 services
in their existing dependency order, plus a new, narrow, remediation-scoped reevaluation composition that reuses
existing per-dimension/OQI4/OQI6/Reliance entrypoints directly — never CDD-056's own full nine-dimension
wrapper, whose request contract remediation's own persisted state cannot satisfy without fabrication.**

## 2. Independent re-verification — authoritative baseline (binding)

`origin/main`, local `main`, and GitHub `main` all independently re-confirmed equal to
`e705ddfc3572f3d1b655b2efb47eaf81448bee53` (Production-Orchestration-VM-R1's own merge commit). Migration head
independently reconfirmed `0044_oqi4_r1_current_tenancy`, single head. Table count independently reconfirmed
`123`. Working tree independently reconfirmed clean except the inherited, pre-existing, unrelated untracked
`docs/product/`.

## 3. Discovery re-validation (binding)

Independently re-confirmed via direct source inspection during this governance phase (not merely trusted from
the DR report):
```
extract_candidates / construct_instruction / request_authorization / refresh_case -- zero non-test callers
    anywhere in app/, confirmed by exhaustive grep.
OqiRemediationAgentService / reason_about_case -- zero non-test callers anywhere.
decide_authorization / report_execution -- real, production-wired routes with real scopes
    oqi-remediation:authorize / oqi-remediation:report-execution, confirmed directly in router.py.
oqi_product_experience_service.py's own `_resolve_finding` already resolves a bare finding_id to its
    governed FindingFamily across all three OQI1/OQI2/OQI3 storage tables, each independently tenant-checked
    -- confirmed directly, reusable as a pattern (not importable directly, being a private method on an
    unrelated read-service class; the new orchestrator implements the equivalent minimal, side-effect-free
    three-table probe itself rather than modifying oqi_product_experience_service.py, per §9's "composition
    only, no sixth path" discipline).
```
The DR's central finding is independently reconfirmed true, unchanged.

## 4. Governed V1 architecture (binding)

```
Existing production Finding (via CDD-056's Production Evaluation Orchestrator, already closed)
        |
NEW: POST /api/v1/oqi/findings/{finding_id}/remediation/prepare  (ProductionRemediationOrchestrationService)
        |
Existing OQI5-I1 OqiRemediationService (unmodified): extract_candidates -> construct_instruction (per
        candidate) -> request_authorization (per instruction) -- composition only
        |
Zero, one, or many PENDING RemediationAuthorization rows (existing domain semantics, never fabricated)
        |
EXISTING production API (CDD-045, unmodified): POST .../authorizations/{id}/decide
        |
EXISTING production API (CDD-045, unmodified): POST .../authorizations/{id}/report-execution
        |
NEW: remediation-scoped reevaluation, triggered synchronously immediately after a successful
        report_external_execution commit, composing (never duplicating) the affected family's own
        evaluate_current_state, then OQI4's evaluate, then OQI6/Reliance's own entrypoints, then the
        existing, unmodified refresh_case
        |
Finding OPEN or RESOLVED -- exclusively as a fresh reflection of real re-evaluation, never a direct
        consequence of the execution report itself
```
Agent reasoning (OQI5-I2) is explicitly and deliberately **excluded from this phase's production trigger**
(see §11).

## 5. Central governance invariants (binding, restated and extended)

```
AGENT ≠ AUTHORITY               (unchanged, already structurally proven — no code path exists at all)
RECOMMENDATION ≠ AUTHORIZATION  (unchanged, already structurally proven)
AUTHORIZATION ≠ EXECUTION       (unchanged — APPROVED alone never triggers anything; a separate human/
                                 external act, then a separate report, is required)
EXECUTION ≠ RESOLUTION          (unchanged, already structurally proven in existing I1 code)
REMEDIATION ≠ RESOLUTION        (unchanged — only fresh governed reevaluation may resolve a Finding)
```
This document introduces no new authority, no new evaluation logic, no new source-write capability, and no
new agent capability. It is composition of already-governed pieces plus one new, narrow reevaluation
composition built entirely from already-existing entrypoints.

## 6. Tenant authority (binding)

```
AUTHENTICATED PRINCIPAL (TrustedPrincipal.tenant_id)
        |
the SAME tenant_id threaded through: Finding resolution, case, candidate, instruction, authorization
        request, and the new reevaluation composition
```
`PrepareRemediationRequest` carries no `tenant_id` field. `ConfigDict(extra="forbid")` (the exact pattern
`EvaluateRequest` already established, CDD-056 §8) ensures an injected body `tenant_id` is rejected with
`HTTP 422`, never silently ignored.

## 7. Exact API authorization (binding)

```
Route:  POST /api/v1/oqi/findings/{finding_id}/remediation/prepare
Scope:  oqi-remediation:prepare
```
Independently re-derived from the existing convention: the read route `GET /findings/{finding_id}/remediation`
already exists at this exact path shape; the new action route extends it with an action suffix, exactly
mirroring how `oqi-remediation:authorize`/`oqi-remediation:report-execution` already follow the
`<domain>:<action>` convention. `oqi-remediation:prepare` is a new, narrow, third action scope in the same
domain — never reusing or broadening `oqi-remediation:authorize`/`oqi-remediation:report-execution`, and
never the broad `oqi:read` scope for a write/action.

## 8. Request contract (binding)

```json
{
  "correlation_id": "UUID (optional, caller-supplied, non-authoritative, purely for tracing -- identical
                     convention to EvaluateRequest, CDD-056 §8)"
}
```
`finding_id` is a path parameter, never a body field (avoids the exact class of ambiguity a body-supplied ID
could invite). No `tenant_id`, no `finding_family` (resolved internally, see §3), no candidate selection, no
model/provider parameter. `model_config = ConfigDict(extra="forbid")`.

## 9. Reevaluation architecture — material refinement from DR's own hypothesis (binding, load-bearing)

The DR report's own hypothesis (reuse `OqiEvaluationOrchestrationService.evaluate()` verbatim) is **rejected**
by this governance phase, for the exact reason the DR itself surfaced: that method's request contract requires
`source_record_reference`, `business_process_id`, `business_process_version` — none of which is recoverable
from any state remediation persists, and supplying placeholders would risk noisy/incorrect side-evaluation of
unrelated dimensions sharing the same `information_element_requirement_id`.

**Frozen instead**: a new, narrow, remediation-scoped reevaluation composition, living inside
`ProductionRemediationOrchestrationService`, that calls **only** the specific entrypoints CDD-043 §17 itself
already named (never CDD-056's own top-level wrapper):
```
1. The affected family's own evaluate_current_state (OqiCrossSourceEvaluationService for Consistency;
   OqiAccuracyEvaluationService for Accuracy) -- own transaction, commits immediately on success.
2. OqiOntologyImpactEvaluationService.evaluate_current_state(tenant_id, finding_family, finding_id) -- own
   transaction per (finding_family, finding_id) pair, mirroring CDD-056 §22's own proven pattern.
3. OqiBusinessImpactService.evaluate_business_impact_for_dependency / evaluate_reliance_for_subject -- the
   existing shared transaction already designed into that service (unchanged, mirroring CDD-056 §22).
4. OqiRemediationService.refresh_case (existing, unmodified) -- reflects the Finding's own now-current status
   onto the case.
```
This is composition of the identical, already-safety-proven building blocks CDD-056's own orchestrator
composes — reused directly, not through its wrapper — introducing no duplicate semantic logic and no new
domain decision anywhere in the chain.

## 10. Reevaluation family scope (binding)

Reevaluation is attempted **only** for Finding families whose candidate-eligibility matrix (§12) can produce a
real candidate: **Consistency (OQI2) and Accuracy**. Conformity is architecturally candidate-capable per the
existing repository (`get_conformity_candidate_support`) but its own reevaluation entrypoint
(`OqiConformityEvaluationService.evaluate_current_state`) requires a `subject` shaped identically to Accuracy's
own (source_field_id + source_object_id + source_record_reference, the latter recoverable via the same
evidence-lookup path as §13) — included on the identical basis. OQI1/OQI3/Reasonableness/Integrity/Timeliness
Findings never produce a real candidate (§12) and therefore never reach instruction/authorization/execution/
reevaluation at all — this is existing, frozen, deliberate architecture, not narrowed further by this document.

## 11. Agent reasoning — explicitly deferred (binding)

`prepare` composes **only** `OqiRemediationService` (candidate extraction, instruction construction,
authorization request). It never constructs or calls `OqiRemediationAgentService`. Reason, frozen here rather
than left ambiguous: the only agent-reasoning consumer requires a `ModelProvider`; the sole real adapter
(`AnthropicMessagesProvider`) is unwired (no constructor site, no configured credential) and this document does
not authorize wiring it (§20); the sole alternative, `FakeModelProvider`, is a **test double** (CDD-043 §25) —
using it in a real production response would fabricate an AI recommendation no user actually received, which
this document explicitly forbids (mirrors CDD-056 §9's own "never fabricate" discipline). `prepare`'s response
therefore always reports agent reasoning as **not invoked** in this phase — honest, not a placeholder for a
future capability silently pretended to exist today.

## 12. Candidate eligibility matrix (binding, re-derived, unchanged from existing OQI5)

| Finding family/type | Candidate supported | Instruction supported | Human-investigation only |
|---|---:|---:|---:|
| OQI1 Completeness/Validity | No | No | Yes |
| OQI2 Consistency | **Yes** | **Yes** | No |
| OQI3 BusinessRule (generic) | No | No | Yes |
| ACCURACY | Yes, conditional on reference evidence | Yes | Only if no support found |
| CONFORMITY | Yes, conditional on canonical standard | Yes | Only if no support found |
| REASONABLENESS | No | No | Yes |
| INTEGRITY (Structural + Reference) | No | No | Yes |
| TIMELINESS | No | No | Yes |

## 13. Reevaluation input recovery (binding, exact)

```
CONSISTENCY:
    comparison_subject_id  <-  QualityComparisonFindingORM.comparison_subject_id (persisted column, read
                                via the existing get_oqi2_finding_state path)
    rule                   <-  existing active-QualityRule lookup keyed on comparison_subject_id + dimension
    correspondence          <-  existing OqiCrossSourceCorrespondenceRepositoryImpl.get_active(tenant_id,
                                comparison_subject_id)
    -> OqiCrossSourceEvaluationService.evaluate_current_state(rule, correspondence)

ACCURACY / CONFORMITY:
    candidate.supporting_evidence_ids[0]  ->  FieldValueEvidence row  ->  its own persisted
        source_field_id, source_object_id, source_record_reference (never fabricated, never a placeholder)
    -> EvaluationSubject reconstructed exactly as CDD-056's own orchestrator constructs one
    -> OqiAccuracyEvaluationService / OqiConformityEvaluationService.evaluate_current_state(rule, subject)
```
No new persisted mutable state. No request-body-supplied identifier used for any of the above. `tenant_id`
sourced exclusively from the same trusted context the original `report_external_execution` call authenticated.

## 14. The one authorized correction to existing frozen OQI5-I1 code (binding — the sole exception to
    "OQI5-I1 files are read-only consumed")

**Discovery re-confirmed** (independently, in this governance phase): `save_case`, `save_candidates_idempotent`,
and `save_instruction` in `backend/app/infrastructure/persistence/oqi_remediation_repository.py` use a
check-then-insert pattern (`session.get(...)`, then `session.add(...)` if absent) on deterministic IDs. Under
genuine concurrent identical `prepare` calls for the same Finding, the losing request raises an uncaught
`IntegrityError` on the primary key rather than converging idempotently. PostgreSQL's own PK constraint
prevents any duplicate/corrupt row — this is a robustness gap, not a correctness or authority defect — but it
is real, and it will now be exercised for the first time by real production traffic.

**Authorized correction (exact)**: rewrite exactly these three methods to use the identical idempotent-insert
technique already established elsewhere in this codebase (`insert_evaluation_idempotent`'s own
check-then-insert-with-graceful-convergence discipline, or a PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`
where the ORM session pattern makes that cleaner) — such that concurrent identical calls converge to exactly
one durable logical row each, with zero uncaught `IntegrityError` escaping to the caller. Forbidden inside this
correction: weakening any uniqueness constraint, catching and silently suppressing an unrelated
`IntegrityError`, deleting/truncating rows, global serialization (e.g. a table-wide lock), sleeps/retries, or
changing any deterministic ID derivation. This is the **only** MODIFY authorized against any OQI5-I1 file.

## 15. Human authority (binding, restated, unchanged)

`POST /api/v1/oqi/remediation/authorizations/{authorization_id}/decide`, scope `oqi-remediation:authorize` —
independently re-confirmed unmodified, unchanged, byte-identical to its CDD-045-frozen form. Only an
authenticated human principal distinct from the requester may approve or reject. No code anywhere in the
agent, candidate-extraction, instruction-construction, or new orchestrator path has the ability to reach
`approve`/`reject`.

## 16. Authorization states (binding, restated, unchanged)

`PENDING` → `APPROVED` | `REJECTED` — exactly the three closed states CDD-043 §14 already froze. This document
introduces no new state. No `candidate → executed` transition exists or is introduced.

## 17. Staleness/TOCTOU contract (binding, restated, unchanged)

`payload_digest` (computed over tenant, Finding id + state_revision, case_id, candidate_id, target
object/field, action_type) is recomputed from current state at `report_external_execution` time and compared;
mismatch fails closed with `REMEDIATION_ACTION_MISMATCH`, zero state change. Preserved verbatim — no second
staleness mechanism introduced.

## 18. Instruction semantics (binding, restated, unchanged)

`construct_instruction` remains OQI5-I1's own unmodified method. `prepare` calls it once per extracted
candidate (zero, one, or many). An instruction is never itself authorization; an instruction is never itself
execution. A known, disclosed, non-blocking product nuance: if multiple candidates exist for one Finding,
multiple independent `PENDING` authorizations may coexist; approving one does not automatically supersede
sibling authorizations (no such logic exists in frozen OQI5-I1 domain code, and none is added here) — each
remains independently governed by its own tenant/self-approval/staleness checks, and any not consumed before
the Finding's next state_revision change fails closed automatically via the existing digest mechanism. Product
refinement of this UX nuance is explicitly deferred, not a blocker.

## 19. External execution boundary (binding, restated, unchanged)

Noetva does not execute enterprise-system mutations itself, confirmed unchanged by this phase. V1 remains:
governed authorized instruction → external human/system executes → execution is reported via the existing,
unmodified `report_external_execution`.

## 20. Live model provider (binding — explicitly out of scope)

```
0 live-model-provider construction/configuration paths
0 new provider environment variables
0 provider Docker changes
```
`AnthropicMessagesProvider` remains exactly as discovered: real, complete, unwired. A future, separately
governed `Production OQI5 Live Model Provider` phase may wire it. This document explicitly forbids doing so
now.

## 21. Post-execution order (binding)

```
report_external_execution transaction commits
        |
remediation-scoped reevaluation begins (new transaction(s), per §9)
        |
OQI4 (own transaction per finding pair)
        |
OQI6 + Reliance (existing shared transaction)
        |
refresh_case (existing, unmodified)
```
Reevaluation never begins before the execution-report transaction has durably committed. No stage holds a
transaction open across a human-paced boundary.

## 22. Transaction boundaries (binding)

```
prepare (candidate extraction + instruction construction + authorization request) -- its own transaction,
    committed before the HTTP response returns (mirrors CDD-056's own per-stage commit discipline: extract,
    then construct, then request, each already independently persisted by existing OQI5-I1 code)
human decision (decide)          -- separate HTTP request/transaction (existing, unchanged)
execution report                 -- separate HTTP request/transaction (existing, unchanged)
remediation-scoped reevaluation  -- new transaction(s), per §9/§21
OQI4                              -- own transaction per finding pair
OQI6 + Reliance                   -- existing shared transaction
```
No transaction spans more than one of these stages. No transaction spans a human-paced boundary.

## 23. Partial-failure contract (binding)

```
execution report commits / reevaluation fails technically  -> execution history survives; Finding remains its
    prior governed state; reevaluation reported FAILED (never NOT_EVALUABLE); retry possible
DQ reevaluation commits / OQI4 fails                        -> DQ survives; OQI4 reported FAILED; retry
    possible; mirrors CDD-056's own proven OQI4 partial-failure contract exactly
OQI4 commits / OQI6+Reliance fails                          -> DQ/OQI4 survive; OQI6/Reliance reported FAILED,
    never a fabricated partial success; mirrors CDD-056's own proven shared-transaction contract exactly
```
Reuses CDD-056's own now-twice-adversarially-proven transaction/failure-honesty pattern verbatim — no new
mechanism invented.

## 24. Reliance replay-sensitivity (binding — reclassification adopted from DR)

```
Classification: B -- real defect, non-blocking for this human-paced V1, must be corrected before any future
    fully-automated/connector-driven remediation loop.
```
Reevaluation frequency remains bounded by human authorization + external execution + human execution report —
identical bounded-frequency profile CDD-056 §20 already accepted. Not corrected in this phase. Carried
explicitly to OQI-H7/OQI-FAV.

## 25. OQI2/OQI3/OQI4→OQI6 pointer classifications (binding — reclassifications adopted from DR)

```
OQI2 QualityComparisonFindingORM.latest_evaluation_id -- P2, non-blocking. Genuinely dereferenced by
    remediation candidate extraction; Finding is tenant-checked before the pointer is ever read; pointer
    value is written exclusively by the trusted evaluator; no attacker-controlled write path found; no live
    exploit proven. Mandatory OQI-H7/OQI-FAV target.
load_participant_observations() -- lacks its own tenant filter (defense-in-depth gap, not a live exploit).
    NOT corrected in this phase, per explicit instruction -- deferred to OQI-H7/OQI-FAV alongside the pointer
    itself.
OQI3 BusinessRuleFindingORM.latest_evaluation_id -- P2, unchanged, unexercised by this remediation path (OQI3
    generates no real candidates; get_oqi3_finding_state hardcodes latest_evaluation_id=None).
OQI4->OQI6 considered_current_impact_id -- P2, non-blocking. Untouched by existing OQI5 code; the new
    reevaluation composition reuses the identical tenant-filtered entrypoints CDD-056 already adjudicated
    safe, introducing no new exposure.
```
None corrected in this phase.

## 26. Concurrency matrix (binding, mandatory for I/VM)

```
C1  same Finding, concurrent prepare                       -- certifies §14's repository correction
C2  same deterministic candidate/instruction, concurrent    -- certifies §14's repository correction
C3  concurrent human authorization decisions                -- existing row-lock, re-proven
C4  APPROVE vs REJECT race                                   -- existing row-lock, re-proven
C5  duplicate execution reports                              -- existing consumed-state guard, re-proven
C6  execution report followed by reevaluation ordering       -- proves §21's sequencing
C7  Finding drift during pending human decision              -- existing digest staleness, re-proven
C8  Tenant A / Tenant B, identical externally-shaped IDs     -- existing tenant checks, re-proven
```

## 27. OQI5 authority firewall (binding)

`prepare` may create: case, candidate(s), instruction(s), `PENDING` authorization(s). It may **never** create:
`APPROVED` authorization, an execution report, or a Finding resolution. Agent reasoning (not invoked, §11)
could never create approval even if it were invoked, by construction (§5).

## 28. Audit (binding)

Reuse existing `SecurityAuditService` (already wired via `dependencies.security_audit` at the router
boundary, currently only invoked on scope-denial). **Authorized, minimal addition**: add successful-outcome
`audit.record(...)` calls at exactly four points — `prepare` completes, `decide` completes, `report-execution`
completes, remediation-scoped reevaluation completes — reusing the existing service/call shape verbatim. No
new observability infrastructure.

## 29. Frontend (binding)

```
FRONTEND CHANGE NOT REQUIRED FOR CORRECTNESS.
```
Existing read/decide/report UI (`remediation-stepper.tsx`, `decide-authorization-dialog.tsx`,
`report-execution-dialog.tsx`) is unaffected and continues to function unmodified. A "Prepare Remediation"
UX affordance is future, optional product-usability polish, not authorized or required here.

## 30. Database impact (binding)

```
0 migrations
0 ORM modifications
0 new tables
0 new columns
```
Every reevaluation input is recoverable from existing persisted state (§13); the concurrency correction (§14)
is repository logic only.

## 31. Docker/runtime impact (binding)

```
same backend process, synchronous invocation
no queue, no worker, no scheduler, no cron, no Kafka, no Redis, no Celery
no new container, no new environment variable
```
Confirmed by design, mirroring CDD-056 §30 exactly.

## 32. Real connector boundary (restated)

Out of scope. The architecture remains connector-ready: a future connector can replace "external execution +
human report" with "connector executes + connector reports" through the identical `report_external_execution`
call shape, without touching human-authority semantics.

## 33. Exact implementation-path authorization (binding — a maximum permitted write set)

```
CREATE = 2
MODIFY = 3
DELETE = 0
TOTAL  = 5
```
```
CREATE  backend/app/application/production_remediation_orchestration_service.py
        ProductionRemediationOrchestrationService: prepare_remediation(...) (candidate extraction +
        instruction construction + authorization request, per §4/§8/§11/§12) and the remediation-scoped
        reevaluation composition (per §9/§13/§21/§22/§23), invoked from the router's report-execution handler
        immediately after that handler's own existing successful commit.

CREATE  backend/app/tests/test_production_remediation_orchestration_postgres.py
        The production/adversarial remediation-orchestration test file implementing the verification
        contract frozen in §34-§40 below.

MODIFY  backend/app/api/oqi/schemas.py
        Exactly the new PrepareRemediationRequest/Response Pydantic models (§8/§41 shape). No existing schema
        modified. (Corrects the DR report's own misclassification of this path as CREATE.)

MODIFY  backend/app/api/oqi/router.py
        Exactly one new route (POST .../remediation/prepare) plus one new dependency-provider function
        (mirroring the existing evaluation_orchestration_service pattern), plus the narrow addition of a
        post-commit call into the new reevaluation composition inside the existing report_execution handler.
        No existing route deleted; the existing decide/report-execution handlers' own request/response shape
        is unchanged.

MODIFY  backend/app/infrastructure/persistence/oqi_remediation_repository.py
        Exactly the §14 idempotent-insert correction to save_case/save_candidates_idempotent/save_instruction.
        No other line in this file may change.
```
`backend/app/infrastructure/persistence/oqi_remediation_agent_repository.py` is **NOT authorized** — agent
reasoning is not invoked by this phase (§11), so no reason to touch it exists. No path beyond the five above
is authorized. No migration path. No ORM path beyond the one named repository file (which contains no ORM
model changes — model file itself is untouched). No frontend path.

## 34. Forbidden implementation paths (binding, exhaustive)

Any OQI1/OQI2/OQI3/OQI4 domain/persistence file; any Gate S/Gate V file; `oqi_remediation_agent_service.py`,
`oqi_remediation_agent_repository.py`, `model_provider/provider.py`, or any `AgentRole`/`AgentRun`/
`AgentRecommendation` domain file; any migration; any ORM model file; any frontend file; any Docker Compose
topology file; CDD-043, CDD-045, CDD-056, CDD-057, or their own Artifact Authorizations. No DELETE. No
opportunistic cleanup. No refactoring beyond §14's own exact, narrow correction.

## 35. Production-Remediation-Orchestration-I STOP conditions (binding, exhaustive)

```
 1. authoritative main moves materially.
 2. this document's own governance hash drifts before implementation begins.
 3. any file outside the exact five §33 paths requires a write.
 4. tenant authority cannot be sourced exclusively from TrustedPrincipal.tenant_id.
 5. agent reasoning is found necessary for correctness (it must remain optional/absent in this phase).
 6. execution can occur, or Finding resolution can occur, without the exact existing human/reevaluation gates.
 7. the §14 repository correction cannot be made without touching a forbidden file or weakening a constraint.
 8. reevaluation authoritative inputs cannot in fact be recovered as §13 describes for a real fixture.
 9. any database schema change becomes necessary.
10. any ORM modification beyond the named repository file becomes necessary.
11. a new queue/worker/scheduler becomes necessary for correctness.
12. the implementation path set exceeds the exact five §33 paths.
13. OQI2/OQI3/OQI4->OQI6 pointer observations are found to require correction for this orchestrator to be
    safe (re-elevating any from P2/non-blocking to blocker).
14. cross-tenant safety cannot be maintained end-to-end through the new prepare/reevaluation boundary.
15. idempotent/concurrent prepare cannot be guaranteed after the §14 correction.
16. partial failure at any new stage is found to corrupt existing authoritative state.
17. any existing OQI1-6/H1-H5/remediation crown/regression value changes semantically as a result.
18. whole-package mypy, black, isort, or ruff fails as a result of this correction.
19. full clean-candidate regression fails as a result of this correction.
20. Docker proof differs materially from host proof.
21. any P0 appears, or any material P1 remains unresolved outside the exact frozen scope.
```

## 36. VM/merge gate (binding, restated)

Production-Remediation-Orchestration-VM must independently re-derive every item in §35's proof surface plus:
exact ancestry; governance hash; exact diff; the frozen concurrency matrix (§26); cross-tenant, staleness,
authority-firewall, and partial-failure adversarial proofs; full backend/static/frontend regression; fresh
`--no-cache` Docker proof; CI exact-head status; confirmation that the deferred register (§37) remains
explicitly deferred, not silently solved; confirmation that agent reasoning/live-provider work was not
accidentally implemented. Merge requires `P0 = 0` and `P1 = 0`.

## 37. Deferred register (binding, restated)

```
P2 -- OQI2 QualityComparisonFindingORM.latest_evaluation_id tenant-pointer observation
P2 -- load_participant_observations lacks its own tenant filter (defense-in-depth)
P2 -- OQI3 BusinessRuleFindingORM.latest_evaluation_id tenant-pointer observation
P2 -- OQI4->OQI6 considered_current_impact_id structural observation
P3/B -- Reliance evaluation-history replay sensitivity (non-blocking for this human-paced V1; blocker
        candidate before any future automated/connector-driven remediation)
P3 -- frontend Docker internal-loopback healthcheck discrepancy
Capability gap -- zero real production connectors
Capability gap -- live production model-provider reasoning (explicitly out of this phase, §20)
```
None fixed by this document. The §14 concurrency correction is the sole exception, explicitly authorized, not
deferred.

## 38. Frozen verification matrix (binding, mandatory minimum test obligations)

**Preparation**: eligible Finding (Consistency and Accuracy); zero-candidate Finding (e.g. Reasonableness);
repeated preparation converges; concurrent preparation (C1/C2) converges with zero uncaught `IntegrityError`.
**Authority**: human-only approval; agent cannot approve (structural, not merely behavioral); wrong scope
rejected; body-tenant override rejected (`422`); cross-tenant Finding/case/candidate/authorization/instruction
all fail closed, verified by direct PostgreSQL query.
**Staleness**: underlying Finding state changes before decision/execution; stale authorization fails closed
with zero additional machinery.
**Execution**: `PENDING`/`REJECTED`/nonexistent/cross-tenant authorization cannot report execution; only
`APPROVED`, unconsumed can; duplicate report converges/fails honestly.
**Resolution**: execution report alone never resolves a Finding; successful report with no actual underlying
correction leaves the Finding OPEN/VIOLATED and Reliance appropriately AT_RISK/UNKNOWN; a genuine underlying
correction plus SATISFIED reevaluation resolves the same Finding identity.
**Reevaluation**: authoritative input recovery (§13) proven for both Consistency and Accuracy fixtures; OQI4;
OQI6; all three Reliance states reachable through a remediation-driven transition; technical failure reported
`FAILED`, never `NOT_EVALUABLE`.
**Failure durability**: execution report survives reevaluation failure; DQ survives OQI4 failure; DQ/OQI4
survive OQI6/Reliance failure; retry converges in each case, mirroring CDD-056's own proven pattern exactly.
**Concurrency**: C1-C8 (§26).

## 39. Existing crown regressions (binding, exact files re-derived)

```
backend/app/tests/test_oqi_remediation_i1.py                            (OQI5-I1 foundation)
backend/app/tests/test_oqi_remediation_agent_i2.py                       (OQI5-I2 agent reasoning)
backend/app/tests/test_oqi_evaluation_orchestration_postgres.py         (Production Evaluation Orchestration)
backend/app/tests/test_oqi_h5_timeliness_crown.py                       (H5, combined-order per CDD-057)
backend/app/tests/test_oqi_ontology_impact_postgres.py                  (OQI4, includes OQI4-R1-TI matrix)
backend/app/tests/test_oqi_business_impact.py                           (OQI6, R1/R2/R3 tenant isolation)
backend/app/tests/test_oqi_cross_source_postgres.py                     (OQI2, consumed by reevaluation §9/§13)
backend/app/tests/test_oqi_quality_postgres.py                          (OQI1)
backend/app/tests/test_oqi_h2_accuracy_reasonableness_crown.py          (Accuracy, consumed by reevaluation)
backend/app/tests/test_runtime_architecture.py                          (single-construction-site firewall)
```
All must remain fully green, unmodified in their own existing assertions.

## 40. Full backend regression, static quality, frontend regression, fresh Docker (binding, restated)

Identical discipline to CDD-056/CDD-057: full `pytest app/tests` with `0` unexplained failures (the same
class of pre-existing environmental failures already independently baseline-adjudicated in prior phases
remains separately classified, never silently re-attributed to this candidate); `black`/`isort`/`ruff`/
whole-package `mypy`; frontend `npm test`/`lint`/`typecheck`/`build`; fresh `--no-cache` Docker proof of the
complete verification matrix (§38) inside a genuinely fresh runtime, distinct project namespace, structural
byte-binding to the exact candidate.

```
FORMATTER-ONLY ≠ AUTOMATICALLY AUTHORIZED
```

## 41. Response contract (binding)

```json
{
  "correlation_id": "UUID | null",
  "case_id": "UUID",
  "finding_id": "UUID",
  "case_status": "CANDIDATE_READY | AWAITING_AUTHORITY | STEWARD_INVESTIGATION | ... (existing
                  RemediationCaseStatus vocabulary, verbatim, never a new value)",
  "candidates": [{"candidate_id": "UUID", "proposed_value": "string", "basis": "string"}],
  "instructions": [{"instruction_id": "UUID", "candidate_id": "UUID"}],
  "authorizations": [{"authorization_id": "UUID", "instruction_id": "UUID", "status": "PENDING"}],
  "agent_reasoning_status": "NOT_INVOKED"
}
```
`agent_reasoning_status` is always `"NOT_INVOKED"` in this phase (§11) — never fabricated, never omitted.
Zero candidates is a fully successful `HTTP 202` response with empty `candidates`/`instructions`/
`authorizations` arrays and `case_status = "STEWARD_INVESTIGATION"` — transport success and domain outcome
remain distinct, exactly as CDD-056 §9 already established for evaluation.

## 42. Governance byte-integrity

This document and its own content are the sole new governance artifact this phase publishes. CDD-043,
CDD-045, CDD-056, CDD-057, and their respective Artifact Authorizations are independently re-hashed
immediately before this document's own publication and confirmed byte-identical to their prior published
values; none is modified by this document. `architecture/INDEX.md` independently confirmed to list none of
CDD-053 through CDD-057, matching this repository's established precedent of not indexing narrow correction/
orchestration CDDs there — this document follows the same precedent and requires no index update.

## 43. Authorization

This document is approved and published as a standalone governance artifact, building on CDD-043/045/056/057
without modifying any of them. Implementation against §33's exact five-path authorization (plus the one named,
narrow exception in §14) may proceed under `Production-Remediation-Orchestration-I`.
