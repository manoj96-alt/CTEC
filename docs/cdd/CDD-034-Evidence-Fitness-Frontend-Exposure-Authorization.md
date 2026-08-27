# CDD-034 — Evidence Fitness Frontend Exposure Authorization

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Classification: Companion narrow-supersession authorization — an explicit Product Owner
architecture decision under CDD-034 §35. This is NOT a replacement for CDD-031 or CDD-034, and
it is NOT a broad Gate X amendment.
Authority: fulfills CDD-034 §35's requirement for "a separate, subsequent Product Owner
implementation authorization" and "its own, separate, explicit Product Owner architecture
decision" for Gate X frontend wiring.

## 1. Purpose

This authorization permits the smallest safe live Evidence Fitness frontend capability at
`frontend/app/quality/evidence-fitness/page.tsx`, consuming CDD-034's existing, complete, unmodified
`POST /api/v1/information-element-evidence-fitness/resolve` endpoint. It does not redefine any Gate T,
Gate O, Gate I, or H4 semantic, and it does not create any new backend capability.

## 2. Historical context

CDD-034 (FROZEN) deliberately and explicitly kept Gate X frontend consumption of its own endpoint
out of scope (§29, §33), while explicitly anticipating that a future, separate Product Owner
decision could authorize it (§35). The Gate X Artifact Authorization independently kept
`/quality/evidence-fitness` as capability/governance/status presentation only (§12), permitting
truthful explanation of the FIT/STALE/CONFLICTING vocabulary while visibly disclosing that live
evaluation was not yet exposed. Both decisions were correct and deliberate at the time; this
document is their anticipated, explicitly-permitted next step, not a correction of an error.

## 3. Decision

The Product Owner authorizes exactly one live frontend capability: a user-invoked "Check Evidence
Fitness" action on `/quality/evidence-fitness` that calls the existing CDD-034 endpoint and renders
its governed response honestly. Nothing else is authorized.

## 4. Precedence (binding)

CDD-031 remains FROZEN and fully authoritative over every Evidence Fitness semantic
(`FIT`/`STALE`/`CONFLICTING`/`null`, 7-day staleness, conflict comparison, tenant isolation,
determinism, zero persistence). This document does not reopen, reinterpret, or supersede any part
of CDD-031.

CDD-034 remains FROZEN and fully authoritative over the REST exposure contract (§7-§23) **except**
for the narrow supersession in §5 below. CDD-034 §35 is FULFILLED by this document, not superseded.

The Gate X Artifact Authorization remains FROZEN and fully authoritative over every page and every
UX convention **except** for the narrow supersession in §5 below.

## 5. Narrow supersession (binding — exact scope, nothing else)

- **CDD-034 §29** is narrowly superseded ONLY to permit creation/modification of the exact five
  files in §11, for the sole purpose of live Evidence Fitness frontend consumption. No other Gate X
  file, and no broader Gate X Artifact Authorization reopening, is implied or permitted.
- **CDD-034 §33** is narrowly superseded ONLY for the clause "Gate X frontend wiring or any new
  frontend functionality." Every other non-goal in §33 remains fully binding without exception.
- **CDD-034 §35 is NOT superseded** — this document is its fulfillment.
- **Gate X Artifact Authorization §12** is narrowly superseded ONLY for the prohibition on live
  query results specifically for `/quality/evidence-fitness`. Every other constraint in §12 (no
  Gate T runtime-internals query, no new Gate T API, no fabricated records, no generalized-DQ
  implication, no DQ rules/findings/remediation/scoring) remains fully binding.

No other clause of CDD-034, the Gate X Artifact Authorization, or any other frozen document is
superseded, reopened, or reinterpreted by this document.

## 6. CDD-031 semantic firewall (binding)

CDD-031 remains the sole authority for `FIT`, `STALE`, `CONFLICTING`, `null`, the 7-day staleness
threshold, conflict semantics, tenant isolation, determinism, and zero persistence. The frontend
MUST consume and render the API's returned values ONLY. The frontend MUST NOT independently
compute, infer, or approximate a fitness/staleness/conflict determination from timestamps, raw
evidence values, source counts, source disagreement, or mapping state under any circumstance.

## 7. CDD-034 endpoint firewall (binding)

The frontend consumes exactly `POST /api/v1/information-element-evidence-fitness/resolve` with
exactly the request contract `{blueprint_name: string, information_element_name: string}` and
exactly the response contract `{information_element_requirement_id, source_field_id, fitness_status,
evaluated_at}` per CDD-034 §8-§9, verbatim. No `as_of` field, no `tenant_id` field, no new request or
response field, and no frontend-only semantic extension of any kind is authorized. No backend API
modification of any kind is authorized by this document.

## 8. Product / UX contract (binding)

The user provides `blueprint_name` and `information_element_name`, then invokes an action labeled
**"Check Evidence Fitness"** (not "Run," "Evaluate," or "Refresh" — the underlying operation is
read-only and deterministic, and MUST NOT be described in mutating or workflow-implying language).
The frontend calls the endpoint in §7 and renders EXACTLY one of the following nine states, and no
other:

1. `UNMAPPED` — no `SourceField` mapped to this Information Element at all.
2. `MAPPED` / no evaluable evidence — a `SourceField` is mapped but `fitness_status` is `null`.
3. `FIT`
4. `STALE`
5. `CONFLICTING`
6. Authorization failure (HTTP 401/403)
7. Not found (HTTP 404 — blueprint or information element)
8. Validation / ambiguous name (HTTP 422)
9. Network / server failure (HTTP 500 or transport error)

States 1 and 2 MUST be rendered as explicitly, visibly distinct states. The UI MUST NOT fabricate,
imply, or default to any fitness result when `fitness_status` is `null`.

## 9. Claims contract (binding)

The frontend MAY claim only: whether the Information Element is mapped; whether evaluable evidence
exists; the returned fitness status; whether evidence is stale; whether evidence conflicts. The
frontend MUST NOT claim: generalized data quality; a numeric or independently-computed confidence
score; a causal supplier-risk explanation; risk or evidence remediation; simulation; forecasting;
autonomous decision-making; or AI-generated evidence. Any reference to a human's confidence in the
underlying input MUST be phrased strictly as human interpretation of the governed status returned by
the API — never as a computed or numeric value the frontend produces.

## 10. Security contract (binding)

`information-element-evidence-fitness:read` remains exactly as already provisioned: DEFINED = YES,
DEFAULT = YES, OPTIONAL = NO. No Keycloak modification of any kind is authorized by this document —
no new scope, no change to `defaultClientScopes` or `optionalClientScopes` membership, no persona,
role, or group change. `frontend/lib/auth/config.ts` is NOT authorized for modification — the scope
is already default-granted and requires no explicit frontend request to be issued.

## 11. Exact implementation allowlist (binding)

| Path | Operation | Permitted change |
|---|---|---|
| `frontend/lib/evidence-fitness/api-client.ts` | CREATE | Typed invocation of the §7 endpoint ONLY. No business-semantic evaluation. |
| `frontend/lib/evidence-fitness/contracts.ts` | CREATE | TypeScript types mirroring CDD-034 §8-§9 EXACTLY. No semantic extension. |
| `frontend/tests/evidence-fitness-workspace.test.tsx` | CREATE | Tests per §13. No backend-semantic duplication. |
| `frontend/app/quality/evidence-fitness/page.tsx` | MODIFY | Replace disconnected presentation with the §8 live interaction contract. Preserve truthful governed vocabulary. No generalized-DQ or Simulation functionality. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add ONLY the four paths above to `AUTHORIZED_CHANGED_PATHS`. No unrelated allowlist widening. |

```
AUTHORIZED_NEW    = 3
AUTHORIZED_CHANGE = 2
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 5
```

No sixth file is authorized. If implementation discovery determines a sixth file is mechanically
required, implementation MUST STOP and return to the Product Owner rather than silently widening
this surface.

## 12. Backend / Keycloak / persistence firewall (binding)

NOT authorized under any circumstance: modification of `backend/app/api/information_element_evidence_fitness/*`;
any backend application/service code; Gate T evaluation code; Gate O resolution code; Gate I
coverage code; H4 evidence code; backend schemas; backend persistence; backend migrations;
`keycloak/ctec-realm.json`. No persistence, evaluation history, snapshot, cache, write API, or
audit-history expansion of any kind beyond what the existing endpoint already inherently and
unchangedly produces.

## 13. Testing requirements (binding, minimum set, all within the single authorized test file)

The future implementation MUST prove, at minimum: (1) the correct endpoint is called; (2) the exact
request payload is sent; (3) `UNMAPPED` renders correctly; (4) `MAPPED`/no-evidence renders
correctly; (5) `FIT` renders correctly; (6) `STALE` renders correctly; (7) `CONFLICTING` renders
correctly; (8) 401/403 handled honestly; (9) 404 handled honestly; (10) 422 handled honestly; (11)
500/network failure handled honestly; (12) a loading state is shown during the request; (13) no
fitness value is ever rendered except one traceable directly to the mocked API response (no frontend
semantic computation); (14) the page never claims generalized Data Quality or Simulation coupling.

## 14. Validation contract

Before this future implementation may be accepted: frontend format/lint/typecheck/tests/build pass;
`test_runtime_architecture.py` passes; the existing backend Evidence Fitness test suite passes
unmodified; the full backend regression suite passes; `docker compose config --quiet` passes;
`scripts/verify_architecture_release.py` passes; the exact file accounting in §11 is verified; CDD-031,
CDD-034, the Gate X Artifact Authorization, and this document remain byte-identical; exact-head CI
passes before merge; post-merge CI passes.

## 15. Explicit non-goals (binding)

This document does NOT authorize: GAP-11 changes; GAP-11-FOLLOWUP-1 changes; POST-U/X-DEBT-6 changes;
POST-X-TEST-DEBT-1 changes; Gate R; Gate S; Gate U/Simulation integration; Gate V; Gate W; MCP;
generalized Data Quality; the Gate F↔H-U bridge; Evidence Fitness history, replay, or as-of
evaluation; trend visualization; provenance/evidence-ID expansion; evidence or source-field editing;
remediation; risk-score integration; automated decisions; any new authentication mechanism; any new
persona, role, or group.

## 16. Cross-gate firewall (restated)

This document does not touch or authorize: GAP-8's own broader roadmap beyond §8's exact capability;
GAP-11; GAP-11-FOLLOWUP-1; POST-U/X-DEBT-6; POST-X-TEST-DEBT-1; Gate R; Gate S; Gate U/Simulation;
Gate V; Gate W; MCP; generalized DQ; Gate F↔H-U bridge.

## 17. Future-extension boundary (restated from CDD-034 §35, unchanged)

Evidence Fitness history, replay/as-of evaluation, trend visualization, provenance expansion,
evidence editing, remediation, generalized DQ, Simulation integration, risk-score integration, and
automated decisions all remain explicitly deferred to their own, separate, future Product Owner
architecture decisions. This document does not pre-authorize, imply, or streamline approval for any
of them.

## 18. Rollback / closure semantics

Reverting this document's eventual implementation requires exactly: removing the three CREATE files
in §11; reverting the `page.tsx` modification to its prior disconnected-presentation content; and
reverting the `test_runtime_architecture.py` allowlist addition. No frozen CDD-031, CDD-034, or Gate
X Artifact Authorization file is ever modified, so none requires restoration.

## 19. Publication / implementation boundary

**Publication/freeze of this document does NOT itself authorize implementation.** A separate,
subsequent Product Owner implementation authorization is required before any of the five listed
files may be modified — matching every prior companion's identical binding precondition in this
lineage.

## 20. Authorization

This companion authorization is approved for publication, reached via GAP-8 R0 (discovery) → R1
(governance-mechanism selection) → R2 (drafting, Product Owner approval) → this R3 publication turn.
CDD-031, CDD-034, and the Gate X Artifact Authorization remain FROZEN and PUBLISHED, unchanged by
this approval.
