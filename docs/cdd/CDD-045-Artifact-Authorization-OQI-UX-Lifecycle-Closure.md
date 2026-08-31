# CDD-045 Artifact Authorization Companion — OQI-UX Governed Remediation Lifecycle Closure

**Status:** APPROVED ARTIFACT AUTHORIZATION
**Version:** 1.0
**Extends:** CDD-045 §19 (Human Authority experience), §20 (Remediation / Re-evaluation experience), §22
(API architecture — `oqi-remediation:authorize`/`oqi-remediation:report-execution`), §28 (Test requirements —
"remediation stepper never collapses execution into resolution") — completing already-frozen requirements
that OQI7-I2's merged implementation did not fully build (the two action endpoints were exposed by OQI7-I1
but never wired to any browser control; `case_status` was fetched by OQI7-I2 but never rendered). Does not
reopen CDD-045's architecture, its read-model contracts, its UI Truth Table (§29), or any OQI1-6 semantics.
**Precedent:** same class of narrow, disclosed, companion-document governance artifact as
`CDD-045-Artifact-Authorization-OQI7-I2-Test-Path-Correction.md` and
`CDD-033-Artifact-Authorization-Gate-X-Runtime-Architecture-Findings-Route-Correction.md` — new file, zero
in-place edit of any frozen document. Governed via the OQI-UX-DR → OQI-UX-G → OQI-UX-I → OQI-UX-VM sequence
(a discovery/governance/implementation/verification cycle applied to a UX-completion scope, not a new CDD
number, per the OQI-UX-G Product Owner decision that this work is completion of already-frozen CDD-045 scope).

## 1. What this authorizes

CDD-045 §19-20 and §28 already required a "human authority experience," a "remediation / re-evaluation
experience" rendered as "an explicit stepper," and a test proving "remediation stepper never collapses
execution into resolution." OQI7-I1 (closed, merged) built both action endpoints
(`POST /api/v1/oqi/remediation/authorizations/{id}/decide`, `POST .../report-execution`) and the
`case_status` field on `GET /api/v1/oqi/findings/{id}/remediation`. OQI7-I2 (closed, merged) rendered every
other field of that response but never called either action endpoint from the browser and never rendered
`case_status`. OQI-UX-DR (complete) and OQI-UX-G (complete) traced this precisely from source and froze the
exact completion boundary this document authorizes.

## 2. Zero backend/Keycloak/Docker change

Re-verified directly against `backend/app/application/oqi_remediation_service.py` and
`backend/app/api/oqi/router.py`: both action endpoints, their scopes, the self-approval prohibition, the
pending/approved/consumed/staleness checks, and the 8-value `RemediationCaseStatus` enum already exist and
are already sufficient. This document authorizes zero backend file, zero migration, zero `keycloak/
ctec-realm.json` change, and zero Docker artifact change (`backend/app/infrastructure/persistence/
demo_oqi_seeder.py`, `.github/workflows/ci.yml`, `DOCKER_SMOKE_TEST.md`, Dockerfiles, `docker-compose.yml`
all remain untouched and outside this authorization).

## 3. Exact authorized product paths (frozen)

```
CREATE (4)
frontend/app/quality/findings/[findingId]/_components/decide-authorization-dialog.tsx
frontend/app/quality/findings/[findingId]/_components/report-execution-dialog.tsx
frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
frontend/tests/oqi-remediation-actions.test.tsx

MODIFY (7)
frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx
frontend/app/quality/findings/[findingId]/page.tsx
frontend/lib/auth/config.ts
frontend/lib/auth/browser-session.ts
frontend/app/quality/_components/command-center.tsx
frontend/tests/oqi-command-center.test.tsx
frontend/tests/oqi-finding-detail.test.tsx

DELETE (0)

TOTAL = 11
```

**Accounting note (disclosed, not silently fixed):** the OQI-UX-G report delivered to the Product Owner
stated `MODIFY=8, TOTAL=12` in its summary line, while its own fully-itemized §AF table listed exactly the 7
MODIFY paths above and no others. Direct re-reading of that report at OQI-UX-I start found no eighth file
named anywhere in it. This is resolved as a plain arithmetic miscount against the report's own itemized
table — not a hidden authorized path, not an invented ninth file. The itemized table, not the summary
arithmetic, is authoritative: **MODIFY=7, TOTAL=11** is the correct and binding count for this
implementation. `frontend/lib/oqi/api-client.ts` and `frontend/lib/oqi/contracts.ts` are explicitly confirmed
already sufficient and are not modified.

## 4. `decided_by` identity contract (frozen)

`decided_by` is the authenticated OIDC session's own `sub` claim, obtained via a new, minimal
`frontend/lib/auth/browser-session.ts` export (conceptually `principalId()`), never free text, never
`preferred_username`/`email`/`name`. This mirrors `backend/app/core/config.py`'s `oidc_subject_claim = "sub"`
(the exact claim `TrustedPrincipal.principal_id` is derived from) and Gate S's own existing precedent
(`gate_s_approval_service.py`: `requested_by=principal.principal_id`). If the authenticated session has no
`sub`, the frontend must fail closed (no decide call, no substituted identity string).

## 5. Exact `RemediationCaseStatus` set and stepper mapping (frozen)

Re-derived directly from `backend/app/domain/oqi_remediation/case.py`, closed at exactly 8 values:
`CANDIDATE_READY, AWAITING_AUTHORITY, AUTHORIZED, EXTERNAL_EXECUTION_REPORTED, AWAITING_REEVALUATION,
RESOLVED, STEWARD_INVESTIGATION, NO_REMEDIATION`.

Primary linear stepper (6 steps): Candidate Ready → Awaiting Human Authorization → Authorized → Externally
Reported → Awaiting Re-evaluation → Resolved. Non-linear side states, never rendered as a point on the linear
track: Steward Investigation, No Remediation.

**Rejection composite-state rule (load-bearing):** `RemediationAuthorizationStatus` (`PENDING | APPROVED |
REJECTED`) is a separate enum living on `remediation.authorization.status`, not on `case_status` — verified
directly: `reject()` in `oqi_remediation_service.py` never mutates `case.status`. When
`case_status == AWAITING_AUTHORITY` and `authorization.status == REJECTED`, the stepper must render
"Rejected," never "Awaiting Human Authorization." This is a presentation rule combining two existing
authoritative server fields — it creates no new domain state.

## 6. Semantic firewall (binding, unchanged from CDD-045)

`MAJORITY ≠ TRUTH`, `AUTHORITY ≠ TRUTH`, `CANDIDATE ≠ TRUTH`, `AGENT ≠ FACT`, `RECOMMENDATION ≠
AUTHORIZATION`, `AUTHORIZATION ≠ REMEDIATION`, `REMEDIATION ≠ RESOLUTION`, `UNKNOWN ≠ LOW`, `NO FINDINGS ≠
TRUSTED`. Additional frontend-specific invariants frozen by OQI-UX-G: frontend visibility ≠ authority; button
click ≠ authorization until HTTP success; report execution ≠ source write; report execution ≠ resolution; UI
state ≠ governed state unless server-confirmed; fresh evidence required for resolution. The existing copy
"External remediation reported — awaiting fresh evidence... This does not by itself resolve the underlying
quality condition" is load-bearing and preserved verbatim.

## 7. Gate X and existing OQI test firewall

`frontend/tests/gate-x-navigation.test.tsx`, `gate-x-honesty.test.tsx`, `gate-x-runtime-architecture.test.tsx`
are not modified by this authorization. `frontend/tests/oqi-findings-workspace.test.tsx` and
`oqi-product-truth.test.tsx` are not modified. `oqi-command-center.test.tsx` and `oqi-finding-detail.test.tsx`
receive only narrow, additive assertions in their existing conceptual surface (two new tile links; tab
deep-linking), with no existing assertion weakened or removed.

## 8. Two P3 navigation improvements (in scope)

Command Center: `Active Agent Investigations` and `Pending Human Authorization` tiles become
`<Link href="/quality/findings">`, mirroring the already-shipped, unfiltered `Critical Dependencies At Risk`
tile precedent exactly — no new query parameter, no new route. Finding-detail tab selection becomes
addressable via `?tab=` on the existing `/quality/findings/{findingId}` route, defaulting/falling back to
`evidence` for any missing/invalid value; no new route.

## 9. Authorization

The exact 11 paths in §3, under the constraints of §4-§8 above, are authorized for OQI-UX-I implementation,
verification by OQI-UX-VM, and merge to `main` upon independent adversarial confirmation. This document does
not authorize any change to CDD-045 itself, its Artifact Authorization, any OQI1-7 backend/domain class, any
migration, `keycloak/ctec-realm.json`, or any Docker-G artifact — all remain byte-identical and frozen.
