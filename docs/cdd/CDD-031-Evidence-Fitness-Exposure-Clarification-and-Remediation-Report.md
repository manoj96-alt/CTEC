# CDD-031 — Evidence Fitness Exposure Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Governing CDD: CDD-031 (Governed Source-Evidence Fitness Evaluation and Ontology Impact), FROZEN
Authority base: `24a3eeae7ba9aa8568808f761d5dd7e22fe5bdd6`

## 1. Problem being clarified

CDD-031 §22 ("API/frontend boundary," binding) states, verbatim:

> "No new REST API endpoint. No frontend artifact. No Ask CTEC modification. Proof lives entirely
> at the application-service/test layer, mirroring Gate Q's own precedent."

Gate T's `SourceEvidenceFitnessEvaluationApplicationService` is real, deterministic, fully tested
(unit and PostgreSQL integration), and governed — but is unreachable by any product surface. A new,
separately governed capability (CDD-034, "Governed Evidence Fitness Exposure") requires exactly one
new REST endpoint to make Gate T's existing computation reachable. §22 as written prohibits this
absolutely. This report exists solely to narrow §22 to the minimum extent required to authorize that
one endpoint, without disturbing any other CDD-031 decision.

## 2. Exact clarification (binding)

§22 is superseded **solely** to the following extent:

> Exactly one new REST API endpoint — `POST /api/v1/information-element-evidence-fitness/resolve`,
> the endpoint defined by CDD-034 ("Governed Evidence Fitness Exposure") and no other — is authorized
> to expose Gate T's existing, unmodified `SourceEvidenceFitnessEvaluationApplicationService.evaluate
> (...)` computation, subject to every boundary stated in CDD-034 itself. No other REST endpoint
> exposing any Gate T capability is authorized by this clarification. No frontend artifact of any
> kind is authorized by this clarification — that portion of §22 remains fully binding and
> unmodified.

## 3. What is now permitted

- The creation of a new, thin, additive application-service file whose sole responsibility is to
  compose already-existing, unmodified upstream services (Blueprint resolution, Gate I, H4) and
  invoke Gate T's existing `evaluate(...)` method unchanged, then shape the result into a governed
  API response — exactly as specified by CDD-034.
- The creation of a new API router, schema, and dependency-wiring file exposing that composition,
  exactly as specified by CDD-034.
- The narrow, precisely-scoped registration this new router requires in order to become reachable
  (see §3a) and the narrow scope-configuration entry it requires in order to be authorizable (see
  §3b) — both described here for accuracy, not expanded in scope.

### 3a. Router registration (corrected — not purely additive)

Per independent implementation-feasibility review, a new FastAPI router cannot become reachable
without being registered with the application. This requires a narrow, mechanical modification to
the existing `backend/app/main.py` file: one new import statement and one new
`app.include_router(...)` call, identical in shape to every existing router's own registration in
that file. This clarification explicitly authorizes exactly this narrow modification, and no other
change to `backend/app/main.py`.

### 3b. Authorization-scope registration (corrected — not purely additive)

The new endpoint requires a new OIDC client scope, `information-element-evidence-fitness:read`, to
be authorizable. Per independent implementation-feasibility review, this requires a narrow
modification to the existing `keycloak/ctec-realm.json` realm configuration: one new client-scope
object and one client-scope assignment entry, mirroring the shape of the existing
`entity-resolution:read` scope entry exactly. This clarification explicitly authorizes exactly this
narrow modification, and no other change to `keycloak/ctec-realm.json` — specifically, it does NOT
authorize repairing the separately-tracked, pre-existing absence of `information-element-context
:read` from that same file (POST-U/X-DEBT-6), which remains explicitly out of scope for this
clarification and for CDD-034.

## 4. What remains prohibited (restated, unchanged, binding)

- **No frontend artifact of any kind.** §22's frontend prohibition is untouched by this
  clarification.
- **No Ask CTEC modification.** Untouched.
- **No Gate X Artifact Authorization is reopened or amended.** Gate X's frozen 29-item allowlist
  is wholly unaffected; no Gate X file may be created or modified under this clarification or under
  CDD-034.
- **No modification of Gate T's own application-service file.** `source_evidence_fitness_evaluation
  .py` remains byte-unchanged; this clarification authorizes a new *caller*, never a change to the
  callee.
- **No modification of Gate O, Gate I, or H4's own application-service files.** All three remain
  byte-unchanged; this clarification authorizes only a new, independent *caller* of their existing
  public methods.
- **No second or future Gate T REST endpoint** is pre-authorized by this document. Any additional
  endpoint (e.g., historical/replay evaluation, provenance exposure) requires its own, separate,
  future governance decision and, if it requires touching §22 again, its own clarification.
- **No generalized Data Quality capability** is authorized, referenced, or implied.
- **No new persistence, migration, or schema change** of any kind, beyond the two narrow
  configuration changes in §3a-§3b.
- **No new authentication mechanism.** Only the existing OIDC/`TrustedPrincipal` mechanism may be
  used; §3b's scope addition is a configuration entry, not a new mechanism.
- **No repair of the pre-existing Gate O Keycloak scope gap** (POST-U/X-DEBT-6). That gap is
  independent of, and not remediated by, this clarification.

## 5. Compatibility statement

Every CDD-031 section other than §22 remains **byte-identical, unchanged, and fully binding**,
specifically including but not limited to: §6-§9 (owned concepts, contract, eligibility), §10-§14
(staleness, threshold, `as_of` determinism, conflict semantics, roll-up), §15-§16 (structural
impact/remediation — untouched; CDD-034 does not use or expose these), §17 (determinism), §18
(failure semantics), §19 (tenant isolation), §20 (persistence boundary — "zero new persistence"
remains absolute for Gate T's own domain result; the narrow registration/scope-configuration changes
in §3a-§3b are not "persistence" in this sense), §21 (migration boundary), §23 (Gate I/H4/N/J
firewall), §24-§26 (deferrals), §27 (explicit non-goals), §28 (Future Gate U compatibility), §29-§31
(testable invariants, acceptance criteria, governance firewall).

## 6. Gate T semantic preservation (binding)

`EvidenceFitnessStatus` (`FIT`/`STALE`/`CONFLICTING`) and the `None` (no-fitness) result remain
exactly as CDD-031 §7-§8, §14, §18, §29 define them. CDD-034 may not reinterpret, rename, extend, or
add a member to this enum. The exposure layer authorized by this clarification passes these values
through verbatim. `UNMAPPED` is never represented as a fourth `EvidenceFitnessStatus` value — it is
represented, per CDD-034, as `source_field_id: null` and `fitness_status: null` together, which is a
distinct, structurally-recognizable state from `MAPPED` null-fitness states (which carry a real
`source_field_id`).

## 7. Gate T persistence preservation (binding)

CDD-031 §20's "zero new persistence... no table, column, cache, or durable fitness/remediation
result of any kind" remains absolute. The new exposure layer computes on demand and stores nothing.

## 8. Determinism preservation (binding)

CDD-031 §17's determinism guarantee is preserved: for identical persisted evidence and an identical
`as_of` value, Gate T's result is value-equal. The new exposure layer generates exactly one real UTC
timestamp per request, used both as Gate T's `as_of` input (when Gate T is invoked) and as the
response's `evaluated_at` — this does not alter Gate T's own internal determinism contract, it only
supplies the external input Gate T's own §12 already requires from a caller.

## 9. Tenant-boundary preservation (binding)

CDD-031 §19's tenant-isolation mechanism (`tenant_id` flowing exclusively through
`get_by_source_field(tenant_id=...)`) is unchanged. The new exposure layer must derive `tenant_id`
only from the authenticated `TrustedPrincipal`, never from request input, exactly as every comparable
existing router already does.

## 10. Frontend remains prohibited (restated)

This clarification authorizes **zero** frontend change of any kind. Gate X's existing
`/quality/evidence-fitness` page and its existing truthful disclosure text are unaffected and remain
exactly as implemented; any future frontend wiring to the new endpoint requires its own, separate,
explicitly authorized governance increment amending Gate X's own frozen Artifact Authorization — not
this clarification, and not CDD-034.

## 11. Ask CTEC remains prohibited (restated)

Unchanged from CDD-031 §22's original text — no Ask CTEC modification is authorized by this document.

## 12. Generalized DQ remains prohibited (restated)

Unchanged from CDD-031 §27 — this clarification does not authorize, reference, or preempt a future
generalized Data Quality capability in any way.

## 13. Rollback / reversal semantics (corrected)

Reverting this clarification and CDD-034's eventual implementation is expected to require:

1. Removing the newly-created Evidence Fitness exposure artifacts and their tests (application
   service, router, schema, dependency-wiring file).
2. Reverting the narrow router registration in `backend/app/main.py` (the one import and one
   `include_router` call added under §3a).
3. Reverting the narrow client-scope registration/assignment in `keycloak/ctec-realm.json` (added
   under §3b).
4. Reverting any other existing-file modification only if such a modification is later explicitly
   authorized by the CDD-034 Artifact Authorization and proves necessary.

No frozen Gate T, Gate O, Gate I, H4, or Gate X production file is ever modified by this
clarification or by CDD-034, so none requires restoration.

## 14. Validation requirements

Before CDD-034's eventual implementation may be accepted: the complete existing Gate T unit and
PostgreSQL integration test suite must pass unmodified; the complete existing Gate O test suite must
pass unmodified (proving zero Gate O modification); the complete existing Gate X test suite must pass
unmodified (proving zero Gate X modification); every CDD-031 testable invariant (§29) must continue
to hold against the new exposure layer's own test suite.

## 15. Authorization

This clarification is scoped **exclusively** to authorizing CDD-034's single endpoint, including the
two narrow existing-file changes in §3a-§3b that endpoint mechanically requires to exist and be
reachable. It does not reopen CDD-031 for any other purpose and does not authorize remediation of
POST-U/X-DEBT-6. Publication and freeze of this clarification alone does not itself authorize
implementation — a separate, subsequent Artifact Authorization and implementation-authorization step
remain required, matching this repository's established multi-step discipline for every prior Gate.

This clarification reached approved status via: Post-Gate-U/X cross-gate architecture and capability
audit (A0) → Product Owner architecture decisions (A1) → Governed Evidence Fitness Exposure
discovery and architecture definition (A2) → governance drafting (A3) → independent final governance
review (A4, finding two P1 contract-accuracy defects) → governance correction (A5, resolving both
P1s, P0=0/P1=0 after resolution) → this A6 publication turn.
