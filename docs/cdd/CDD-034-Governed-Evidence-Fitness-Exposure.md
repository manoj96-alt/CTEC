# CDD-034 — Governed Evidence Fitness Exposure

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-031 (FROZEN, Governed Source-Evidence Fitness Evaluation and Ontology
Impact — the sole semantic authority for everything this CDD exposes), CDD-031 Evidence Fitness
Exposure Clarification and Remediation Report (APPROVED CLARIFICATION — the sole permission authority
narrowing CDD-031 §22 to permit this CDD's one endpoint), CDD-029 (FROZEN, Gate O, unchanged — read-
only precedent for router/schema/auth shape and for the Information-Element name-matching pattern
this CDD independently reimplements, §14), CDD-020 (FROZEN, Gate I, unchanged), CDD-023 (FROZEN, H4,
unchanged)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via the Post-Gate-U/X cross-gate
architecture and capability audit (A0) → Product Owner architecture decisions (A1) → Governed
Evidence Fitness Exposure discovery and architecture definition (A2) → governance drafting (A3) →
independent final governance review (A4, finding two P1 contract-accuracy defects: a non-nullable
`source_field_id` structurally incompatible with the real `UNMAPPED` path, and a false additive-only/
CREATE-only implementation and rollback claim) → governance correction (A5, resolving both P1s,
P0=0/P1=0 after resolution) → this A6 publication turn. No implementation exists, and none is
authorized by this frozen document — a separate, subsequent Artifact Authorization companion remains
required before any file is created or modified.

## 1. Purpose

Expose Gate T's existing, real, deterministic Evidence Fitness computation through exactly one new,
narrow, read-only REST API endpoint, making a previously internal-only capability reachable by
authorized callers without modifying Gate T, Gate O, Gate I, H4, or Gate X.

## 2. Problem statement

Gate T (`source_evidence_fitness_evaluation.py`, CDD-031) computes `FIT`/`STALE`/`CONFLICTING`/`None`
for a resolved Information Element's evidence, fully tested and correct, but has zero API and zero
caller in production. This blocks (a) truthful future Gate X frontend wiring and (b) real signal
availability for future SAP S/4HANA Cloud master-data readiness testing.

## 3. Governing authorities

- CDD-031 (Governed Source-Evidence Fitness Evaluation and Ontology Impact) — FROZEN, the sole
  semantic authority for everything this CDD exposes. This CDD does not own, and must not
  reinterpret, any Gate T semantic.
- CDD-031-Evidence-Fitness-Exposure-Clarification-and-Remediation-Report — the sole permission
  authority narrowing CDD-031 §22 to permit this CDD's one endpoint, including the two narrow
  existing-file changes in its own §3a-§3b. This CDD is inert without that clarification's prior
  approval and freeze.
- CDD-029 (Governed Blueprint Information-Element Context-as-a-Service) — read-only precedent for
  router/schema/auth shape and for the Information-Element name-matching pattern this CDD
  independently reimplements (§14). Not modified, not extended, not depended upon at runtime.
- CDD-020 (Semantic Coverage Evaluation, Gate I) and CDD-023 (Evidence Availability, H4) — consumed,
  unmodified, exactly as Gate O already consumes them.

This CDD is **exposure/API contract authority only**. It exposes existing semantics; it does not own
them. It must not redefine: `FIT`/`STALE`/`CONFLICTING`, the 7-day staleness threshold, conflict
comparison semantics, evidence eligibility, Gate I coverage semantics, H4 evidence semantics, tenant
semantics, determinism, persistence behavior, or Gate T failure semantics. All of these remain
exclusively defined by CDD-031, CDD-020, and CDD-023.

## 4. Dependency on the CDD-031 clarification

This CDD may not be implemented, and no Artifact Authorization for it may be published, until the
CDD-031 Evidence Fitness Exposure Clarification and Remediation Report is itself approved, published,
and frozen.

## 5. Existing Gate T authority (restated, binding)

`SourceEvidenceFitnessEvaluationApplicationService.evaluate(...)` remains the sole, unmodified
authority for `EvidenceFitnessStatus` (`FIT`/`STALE`/`CONFLICTING`) and the `None` no-fitness result.
This CDD introduces no new classification logic and reinterprets none of Gate T's existing logic.

## 6. Capability boundary

Exactly one new REST endpoint; one new thin application-service file composing existing, unmodified
upstream services; one new router file; one new schema file; one new dependency-wiring file; their
tests; and the two narrow existing-file changes described in the Clarification Report §3a-§3b.
Nothing else.

## 7. Exact endpoint

`POST /api/v1/information-element-evidence-fitness/resolve`

## 8. Exact request contract

```json
{
  "blueprint_name": "string, required, non-empty",
  "information_element_name": "string, required, non-empty"
}
```

A closed model (`extra="forbid"`), mirroring Gate O's `ResolveRequest` exactly. No `as_of` field, no
`tenant_id` field. Neither may ever be added without a new, separate governance decision (§30).

## 9. Exact response contract (binding)

```json
{
  "information_element_requirement_id": "UUID",
  "source_field_id": "UUID | null",
  "fitness_status": "FIT | STALE | CONFLICTING | null",
  "evaluated_at": "string, ISO-8601 UTC datetime"
}
```

`source_field_id` is nullable. It is `null` if and only if the resolved Information Element
Requirement is `UNMAPPED` (Gate I) — the only real, reachable state in which no `SourceField` has
been resolved at all. For every `MAPPED` state (including `MAPPED` + `NO_EVIDENCE`/`EVIDENCE_EMPTY`,
where `fitness_status` is also `null`), `source_field_id` is a real, non-null UUID. `null` for
`source_field_id` and `null` for `fitness_status` are never fabricated independently of each other —
they are only ever both `null` together (`UNMAPPED`) or `fitness_status` alone is `null` with a real
`source_field_id` (`MAPPED` + `NO_EVIDENCE`/`EVIDENCE_EMPTY`). No combination where `source_field_id`
is `null` but `fitness_status` is non-`null` can ever occur, and no implementation may construct one.

## 10. `fitness_status` semantics (binding, restated from CDD-031)

Exactly Gate T's own four possible outcomes, passed through verbatim: `FIT`, `STALE`, `CONFLICTING`,
or `null`. No fifth value may ever be introduced by this CDD or its implementation. `UNMAPPED`,
`NO_EVIDENCE`, and `EVIDENCE_EMPTY` are never represented as `EvidenceFitnessStatus` values — they
remain, respectively, the absence of a resolved `SourceField` (`source_field_id: null`) or the
presence of one without evaluable evidence (`fitness_status: null` with a real `source_field_id`).

## 11. `null` semantics (binding — three distinct legitimate null-adjacent states)

| State | `source_field_id` | `fitness_status` | Meaning |
|---|---|---|---|
| `UNMAPPED` | `null` | `null` | No `SourceField` is mapped to this requirement at all; Gate T is never reached. |
| `MAPPED` + `NO_EVIDENCE` | real UUID | `null` | A `SourceField` is mapped, but zero `FieldValueEvidence` rows exist for it. |
| `MAPPED` + `EVIDENCE_EMPTY` | real UUID | `null` | A `SourceField` is mapped and evidence rows exist, but all have an empty observed value. |

All three are legitimate, successful (HTTP 200) results. None is ever rendered as an HTTP error, and
none is ever conflated with `UNKNOWN`, `ERROR`, or `NOT_EVALUATED` — no such states exist in Gate T's
closed enum, and none may be invented. Consumers requiring the `MAPPED`/`UNMAPPED` distinction must
inspect `source_field_id`, not invent a status the enum does not have.

## 12. `evaluated_at` semantics (binding)

The exposure/application layer generates exactly one real UTC timestamp (via `datetime.now(UTC)`,
the same real-clock pattern H4 already uses) **once, at the very start of request handling, before
Blueprint resolution and before the pipeline can short-circuit on `UNMAPPED`**. That single timestamp
is used, unmodified, in every branch: it is always returned as `evaluated_at` (including the
`UNMAPPED` branch, where Gate T is never invoked), and it is additionally passed to Gate T's
`evaluate(...)` as its `as_of` parameter whenever Gate T is actually invoked (i.e., every `MAPPED`
branch). There is exactly one meaning for `evaluated_at` in every branch: the wall-clock time basis
used for that request's evaluation. It is never a caller-supplied value and never implies a persisted
or historical record (§19).

## 13. Computation pipeline (binding — explicit sequence)

By call only, reusing existing unmodified services exactly as Gate O's own resolver does for its
comparable steps:

1. Generate the single UTC evaluation timestamp (§12).
2. Resolve the Blueprint by name using the existing `BlueprintApplicationService.get_approved_by_name`
   method, unmodified. If not found, return `BLUEPRINT_NOT_FOUND` (§18).
3. Evaluate Gate I semantic coverage for the entire resolved Blueprint via
   `SemanticCoverageEvaluationApplicationService.evaluate(blueprint_name=..., tenant_id=...)`,
   unmodified.
4. Identify exactly one `InformationElementCoverageResult` whose `element_name` matches the requested
   `information_element_name`, using the minimal mechanical name-matching this endpoint independently
   implements (§14) — never by importing or invoking Gate O.
5. If zero matches: return `INFORMATION_ELEMENT_NOT_FOUND` (§18).
6. If more than one match: return `INFORMATION_ELEMENT_NAME_AMBIGUOUS` (§18).
7. If exactly one match and its `status` is `CoverageStatus.UNMAPPED`: return HTTP 200 with
   `information_element_requirement_id` = that match's real requirement ID, `source_field_id: null`,
   `fitness_status: null`, `evaluated_at` = the timestamp from step 1. **STOP.** Do not call H4. Do
   not call Gate T.
8. If exactly one match and its `status` is `CoverageStatus.MAPPED`: continue.
9. Invoke `InformationElementEvidenceAvailabilityApplicationService.evaluate(coverage_result=...)`
   (H4), unmodified, to obtain the real `source_field_id` and `evidence_availability_status`.
10. Invoke `SourceEvidenceFitnessEvaluationApplicationService.evaluate(evidence_availability_results
    =..., tenant_id=..., as_of=<the timestamp from step 1>)` (Gate T), unmodified.
11. Return `information_element_requirement_id`, the real `source_field_id` from step 9,
    `fitness_status` from Gate T's result, and `evaluated_at` = the timestamp from step 1.

This CDD does not redefine any Gate I, H4, or Gate T semantic — it only sequences already-existing,
unmodified public methods.

## 14. Application-service boundary and Gate O duplication (binding)

A new, thin composition/exposure application service is authorized. Its responsibility is
**exclusively**: resolve the pipeline in §13, and shape the result into the response contract in §9.
It is explicitly **not**: a new semantic authority, a new Evidence authority, a DQ engine, an
orchestration layer for Gate F, a decision engine, or a persistence authority.

**Accepted trade-off (explicitly recorded)**: Gate O performs Information-Element name matching
(step 4 above) inline within its own file and exposes no shared, importable helper for it. This
CDD's exposure service **independently reimplements the identical minimal mechanical matching**
(iterate the resolved Blueprint's requirements, compare `element_name` to the requested name,
`NOT_FOUND` on zero matches, `AMBIGUOUS` on more than one) — this is accepted, mechanical composition
duplication, not semantic duplication, and is not an architecture violation. This CDD's implementation
must NOT: import Gate O's application service, invoke Gate O's endpoint, modify Gate O, or extract/
refactor Gate O into a shared helper. Gate O's own `NOT_FOUND`/`AMBIGUOUS` behavior is not changed by
this CDD in any way — this CDD merely reproduces the identical decision logic independently, over the
same Blueprint data, for its own separate endpoint.

If implementation discovery determines that Gate T's, Gate O's, Gate I's, or H4's own file requires
any modification to support this pipeline, implementation must STOP and return to the Product Owner
before proceeding — this CDD does not pre-authorize any such modification.

## 15. Authentication (binding)

`TrustedPrincipal`, resolved from the existing OIDC bearer-token mechanism, identical to every
comparable existing router. No new authentication mechanism.

## 16. Authorization / scope (binding)

New scope: `information-element-evidence-fitness:read`, following the repository's existing,
consistent `<router-path-name>:<verb>` naming convention. No broader or reused scope. This scope
requires a narrow, explicitly-scoped addition to `keycloak/ctec-realm.json` (Clarification Report
§3b) — it does not exist by declaration in this CDD alone.

## 17. Tenant isolation (binding)

`tenant_id` is derived **exclusively** from the authenticated `TrustedPrincipal`. It is never
accepted from the request body — §8's request schema has no `tenant_id` field, and none may be
added.

## 18. Error behavior (binding)

| Condition | Response |
|---|---|
| `UNMAPPED` (real, successful, non-error state) | HTTP 200, `source_field_id: null`, `fitness_status: null` |
| `MAPPED` + `NO_EVIDENCE`/`EVIDENCE_EMPTY` (real, successful, non-error state) | HTTP 200, real `source_field_id`, `fitness_status: null` |
| `MAPPED` + `EVIDENCE_PRESENT` (`FIT`/`STALE`/`CONFLICTING`) | HTTP 200, real `source_field_id`, real `fitness_status` |
| Blueprint not found | HTTP 404, `{"detail":{"code":"BLUEPRINT_NOT_FOUND"}}` |
| Information Element not found | HTTP 404, `{"detail":{"code":"INFORMATION_ELEMENT_NOT_FOUND"}}` |
| Ambiguous Information Element name | HTTP 422, `{"detail":{"code":"INFORMATION_ELEMENT_NAME_AMBIGUOUS"}}` |
| Authentication failure | HTTP 401 |
| Authorization/scope failure | HTTP 403, `{"detail":{"code":"AUTHORIZATION_SCOPE_REQUIRED"}}` |
| Request validation failure | HTTP 422 (closed-model rejection) |
| Evidence-repository/application failure | Existing `FieldValueEvidenceRepositoryImpl`/`ValidationException` behavior, unchanged |
| Unexpected server failure | HTTP 500, no new taxonomy |

`UNMAPPED` is never an error under any circumstance. No new error taxonomy is introduced anywhere in
this table beyond codes that already exist verbatim in Gate O's own router.

## 19. Persistence prohibition (binding, restated from CDD-031 §20)

Zero new persistence of Gate T's or this endpoint's own domain result. No table, column, cache, or
durable result of any kind. No migration.

## 20. Determinism (binding)

Fully deterministic for a given `(blueprint_name, information_element_name, the single real
evaluation timestamp, current persisted evidence state)` — inherits Gate T's own determinism exactly
for every `MAPPED` branch, and is trivially deterministic for `UNMAPPED` (a pure function of Gate I's
own already-deterministic coverage result).

## 21. Idempotency / read-only behavior (binding)

Zero writes of any kind; safe to retry. Two calls at different real times may legitimately return
different results only if the underlying evidence or mapping state has changed between calls — never
due to any nondeterminism in the endpoint itself.

## 22. Observability (binding)

Reuses the existing `correlation_id` dependency and `SecurityAuditService` audit pattern, via a new,
locally-defined endpoint-classification constant (mirroring Gate O's own local
`_ENDPOINT_CLASSIFICATION` pattern) — no shared registry file requires modification for this.

## 23. Provenance boundary (binding)

The response contains **no** evidence-record identifiers, no source-record identifiers, no evidence
history, and no lineage object of any kind. `evaluated_at` is the only temporal field. `field_value_
evidence_ids` (real, available on H4's own result) are explicitly **not** surfaced by this CDD; any
future provenance extension requires its own, separate governance decision.

## 24. Gate O firewall (binding)

`POST /api/v1/information-element-context/resolve` and its `ResolveRequest`/`ResolveResponse`
schemas are not modified in any way. CDD-029 is not reopened. This CDD's own separate remediation of
Gate O's pre-existing Keycloak scope gap (POST-U/X-DEBT-6) is explicitly out of scope (§29a).

## 25. Gate F firewall (binding)

No Gate F file is imported, called, or referenced anywhere in this CDD's implementation. No Supplier
identifier appears in the request or response contract.

## 26. Gate U firewall (binding)

`what_if_simulation.py` is not modified, called, or depended upon.

## 27. Generalized-DQ firewall (binding, restated from CDD-031 §27)

No DQ Rule, Finding, Impact, or Remediation type, component, route, or persisted record is authorized
by this CDD.

## 28. Gate S / Gate V / MCP firewall (binding)

No approval workflow, no durable human-approval state, no agent execution, and no MCP invocation of
any kind is authorized, referenced, or implied by this CDD.

## 29. Gate X frontend firewall (binding)

No Gate X file is created or modified by this CDD. Gate X's own Artifact Authorization is not
reopened. Gate X's existing `/quality/evidence-fitness` page and its existing disclosure text remain
fully accurate after this CDD's implementation, since no Gate X frontend contract is created by this
CDD.

### 29a. Pre-existing Gate O Keycloak gap firewall (binding)

The pre-existing absence of `information-element-context:read` from `keycloak/ctec-realm.json`
(POST-U/X-DEBT-6) is explicitly **out of scope** for this CDD. This CDD's implementation must not
repair, reference, or bundle a fix for that gap under any circumstance — it is tracked and remediated,
if ever, only by its own separate, future governance decision.

## 30. Historical / replay evaluation deferral (binding)

Caller-controlled `as_of` (historical or replay Evidence Fitness evaluation) is explicitly deferred.
This CDD's endpoint always evaluates at the single real current instant generated per request (§12).
A future, separately governed CDD may introduce a caller-controlled `as_of` capability; this CDD
neither authorizes nor precludes that future work.

## 31. Tests (binding, minimum set)

A. `UNMAPPED` → HTTP 200, real `information_element_requirement_id`, `source_field_id: null`,
   `fitness_status: null`, `evaluated_at` populated, H4 NOT invoked, Gate T NOT invoked (assert via
   mock/spy that neither service was called).
B. `MAPPED` + `NO_EVIDENCE` → HTTP 200, real requirement ID, real `source_field_id`, `fitness_status
   : null`, H4 invoked, Gate T invoked.
C. `MAPPED` + `EVIDENCE_EMPTY` → HTTP 200, real requirement ID, real `source_field_id`,
   `fitness_status: null`, H4 invoked, Gate T invoked.
D. `MAPPED` + `EVIDENCE_PRESENT` / `FIT`.
E. `MAPPED` + `EVIDENCE_PRESENT` / `STALE`.
F. `MAPPED` + `EVIDENCE_PRESENT` / `CONFLICTING`.
G. Zero Information Element matches → `INFORMATION_ELEMENT_NOT_FOUND`.
H. Multiple Information Element matches → `INFORMATION_ELEMENT_NAME_AMBIGUOUS`.
I. Missing required scope → `AUTHORIZATION_SCOPE_REQUIRED` (403).
J. Request body containing a `tenant_id` field is rejected by the closed-model schema (422) — caller
   cannot provide `tenant_id`.
K. Request body containing an `as_of` field is rejected by the closed-model schema (422) — caller
   cannot provide `as_of`.
L. Request body containing an `evaluated_at` field is rejected by the closed-model schema (422) —
   caller cannot provide `evaluated_at`.
M. For every `MAPPED` branch (B-F), assert the exact same timestamp value appears both as the
   response's `evaluated_at` and as the `as_of` argument passed to Gate T's `evaluate(...)` (via
   spy/mock assertion).
N. Zero-write-side-effect assertion (mirroring CDD-031's own invariant).
O. Retry/idempotency (repeated identical calls, unchanged data, produce value-equal results).
P. Full existing Gate T regression suite green.
Q. Full existing Gate O regression suite green.
R. Full existing Gate X regression suite green.

## 32. Acceptance criteria

1. `source_field_id` is nullable in the response schema.
2. `UNMAPPED` is representable and returns HTTP 200.
3. `UNMAPPED` does not invoke H4.
4. `UNMAPPED` does not invoke Gate T.
5. `null` fitness never creates a new `EvidenceFitnessStatus` enum member.
6. `MAPPED` null-fitness states (`NO_EVIDENCE`/`EVIDENCE_EMPTY`) retain a real, non-null
   `source_field_id`.
7. Exactly one real UTC timestamp is generated per request, used as both `evaluated_at` and (when
   applicable) Gate T's `as_of`.
8. The caller cannot control `as_of`, `evaluated_at`, or `tenant_id` through the request.
9. Gate T remains byte-unchanged.
10. Gate O remains byte-unchanged.
11. Gate I and H4 remain byte-unchanged.
12. Gate X remains byte-unchanged.
13. No generalized DQ capability is created.
14. No Gate F ↔ H–U bridge is created.
15. No frontend exposure is authorized or implemented.
16. Router registration in `backend/app/main.py` is truthfully accounted for as a MODIFY item in the
    eventual Artifact Authorization, not omitted or mischaracterized as additive.
17. Keycloak scope registration in `keycloak/ctec-realm.json` is truthfully accounted for as a MODIFY
    item in the eventual Artifact Authorization.
18. Rollback documentation explicitly includes reverting both existing-file modifications, not a
    CREATE-only claim.
19. POST-U/X-DEBT-6 (the pre-existing Gate O Keycloak gap) is not repaired, referenced as in-scope,
    or bundled into this CDD's implementation.

## 33. Explicit non-goals

This CDD does not authorize: Gate O modification (beyond zero); Gate F integration; Gate F↔H–U
composition; Supplier↔Blueprint mapping; generalized Data Quality; Simulation execution; Gate U
frontend execution; Gate S durable approval; MCP execution; Gate V agent execution; Evidence Fitness
persistence or history; historical/replay Evidence Fitness evaluation; Gate X frontend wiring or any
new frontend functionality; any new authentication mechanism; any broader Keycloak/token-semantics/
tenant-semantics redesign; remediation of POST-U/X-DEBT-6.

## 34. Rollback

Reverting this CDD's eventual implementation is expected to require:

1. Removing the new application-service, router, schema, and dependency-wiring files (and their
   tests).
2. Reverting the narrow router-registration modification to `backend/app/main.py`.
3. Reverting the narrow scope-registration modification to `keycloak/ctec-realm.json`.

No frozen Gate T, Gate O, Gate I, H4, or Gate X file is ever modified, so none requires restoration.

## 35. Future extension boundaries

Any future work building on this CDD — historical/replay evaluation, provenance/evidence-ID
exposure, Gate X frontend wiring, folding fitness into Gate O's response, or remediating
POST-U/X-DEBT-6 — requires its own, separate, explicit Product Owner architecture decision. This CDD
does not pre-authorize, imply, or streamline approval for any of them.

## 36. Frozen decisions

Upon approval, this CDD freezes: the exact endpoint path (§7), the exact request/response contracts
including `source_field_id` nullability (§8-§9), the `evaluated_at`/`as_of` single-timestamp rule
(§12), the explicit UNMAPPED short-circuit pipeline (§13), the persistence prohibition (§19), and
every firewall in §24-§29a. Any change to these requires a new Product Owner decision.

## 37. Authorization

This Artifact Authorization companion document remains required before implementation. Publication
and freeze of this CDD does not itself authorize implementation.
