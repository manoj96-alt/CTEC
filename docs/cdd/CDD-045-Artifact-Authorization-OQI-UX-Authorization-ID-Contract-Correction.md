# CDD-045 Artifact Authorization Companion — OQI-UX Authorization-ID Contract Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION
**Version:** 1.0
**Extends:** `CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md` — a narrow, mechanical completion of
the remediation-authorization read/action contract that governance document already authorized, discovered
mid-implementation, not a reopening of it.
**Precedent:** same class of narrow, disclosed, companion-document governance artifact as
`CDD-045-Artifact-Authorization-OQI7-I2-Test-Path-Correction.md`,
`CDD-033-Artifact-Authorization-Gate-X-Runtime-Architecture-Findings-Route-Correction.md`, and
`CDD-045-Artifact-Authorization-I2-Accounting-Correction.md` — new file, zero in-place edit of any frozen
document. Governed via OQI-UX-DR → OQI-UX-G → OQI-UX-I (halted) → OQI-UX-G1 (this correction, frozen) →
OQI-UX-I-R (resumed implementation).

## 1. Why the original OQI-UX-I implementation stopped

OQI-UX-I built the three components its governance authorized (`decide-authorization-dialog.tsx`,
`report-execution-dialog.tsx`, `remediation-stepper.tsx`) plus the independent, unblocked changes
(`browser-session.ts`'s `principalId()`, `config.ts`'s scope string, `command-center.tsx`'s tile links), then
halted before wiring the two dialogs into `remediation-panel.tsx`: both `POST
/api/v1/oqi/remediation/authorizations/{authorization_id}/decide` and `.../report-execution` require an
`authorization_id` path parameter that `GET /api/v1/oqi/findings/{finding_id}/remediation`'s response does
not expose anywhere. No workaround was implemented; implementation stopped and returned to the Product Owner
per the governing phase's own backend-firewall STOP instruction.

## 2. `authorization_id` already exists

`backend/app/infrastructure/persistence/models/oqi_remediation.py:114` —
`OqiRemediationAuthorizationORM.authorization_id: Mapped[UUID]`, the table's own primary key, already
persisted by an existing (OQI5-I1) migration, `server_default=text("gen_random_uuid()")`.
`backend/app/domain/oqi_remediation/authorization.py:151` — the `RemediationAuthorization` domain dataclass
already carries and validates `authorization_id: UUID`. Both layers have always had it.

## 3. Where it was dropped

`backend/app/application/oqi_product_experience_service.py::get_remediation` (lines ~826-857) fetches the
real `OqiRemediationAuthorizationORM` row (with its `authorization_id`) into a local variable, then
constructs `RemediationAuthorizationRow(...)` — a 7-field dataclass (`principal, decided_on, instruction,
authorized_against_state_revision, is_stale, status`) — without passing `authorization_id` through, even
though it is in scope at that exact line. `backend/app/api/oqi/schemas.py`'s `RemediationAuthorizationView`
(the Pydantic response model) mirrors the same 6-field omission. `backend/app/api/oqi/router.py`'s one
construction site for that view (inside the `GET .../remediation` handler) therefore has nothing to pass.
`frontend/lib/oqi/contracts.ts`'s `RemediationAuthorizationView` TypeScript interface mirrors the same gap on
the browser side.

## 4. Cannot be synthesized

`RemediationAuthorization.authorization_id` is assigned `uuid4()` at creation
(`oqi_remediation_service.py::request_authorization`) — a random value, unlike `RemediationCase.case_id`
(deterministic `uuid5` of `tenant_id + finding_family + finding_id`). No combination of `finding_id`,
`tenant_id`, `candidate_id`, `instruction_id`, `principal`, or `state_revision` — all already exposed
elsewhere in the same response — can honestly reconstruct it. It must be returned by the API or the two
action routes cannot be called at all.

## 5. `authorization_id ≠ authority` (frozen)

Direct, existing precedent found in this exact codebase: Gate S's own `ApprovalResponse`
(`backend/app/api/gate_s/schemas.py:23-35`) already publicly exposes `approval_id: UUID` as its first field —
the same class of governed-approval resource, already following the pattern this correction restores to OQI.
Exposing `authorization_id` conveys zero authority on its own: `GET .../remediation` is already tenant-scoped
end-to-end via `_resolve_finding`, so a caller can only ever see IDs for authorizations tied to Findings
within their own tenant; both POST routes independently re-verify scope (`oqi-remediation:authorize` /
`oqi-remediation:report-execution`), tenant match, and authorization state on every call regardless of how the
caller obtained the ID — none of that enforcement is touched by this correction.

## 6. No domain change, no migration, no new route, no scope/tenant/source-write change

The domain class already has the field (§2) — no domain file is touched. The database column already exists
and is already populated — no migration is authorized or required. No route is added; both existing POST
routes' signatures, bodies, and enforcement are unchanged. No scope is added, removed, or reinterpreted. No
tenant-isolation check is altered. No source-system write capability is introduced or implied.

## 7. Exact authorized paths (Set B — zero overlap with the original 11-path Set A)

```
CREATE = 0

MODIFY = 7
backend/app/application/oqi_product_experience_service.py
  -- add authorization_id: UUID to RemediationAuthorizationRow; pass
     authorization_id=authorization.authorization_id at the existing construction site. No other line.
backend/app/api/oqi/schemas.py
  -- add authorization_id: UUID to RemediationAuthorizationView. No other field, class, or file.
backend/app/api/oqi/router.py
  -- pass authorization_id=row.authorization.authorization_id at the existing RemediationAuthorizationView(...)
     construction site inside get_remediation's handler. No route added, no mutation-route body changed.
frontend/lib/oqi/contracts.ts
  -- add authorization_id: string; to the existing RemediationAuthorizationView interface. No API-client
     change (decideAuthorization/reportExecution already accept an authorizationId argument).
backend/app/tests/test_oqi_product_experience_service.py
  -- additive assertion in the existing test_recommendation_vs_authorization_crown_two_stage: returned
     authorization.authorization_id equals the real value from request_authorization().
backend/app/tests/test_oqi_api_postgres.py
  -- one new test proving real end-to-end continuity: seed a real authorization for tenant A, GET remediation
     returns its real authorization_id, POST decide with that exact ID succeeds for tenant A, and the same
     exact ID cross-tenant still fails closed with REMEDIATION_TENANT_MISMATCH.
backend/app/tests/test_oqi_api_router.py
  -- one new test with a populated fake authorization row (including authorization_id) proving the field
     survives application row -> Pydantic response -> JSON body.

DELETE = 0

TOTAL = 7
```

## 8. Relationship to the original 11-path OQI-UX-I authorization (Set A)

Set A (`CREATE=4, MODIFY=7, DELETE=0, TOTAL=11`, frozen by
`CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md`) is unchanged and unexpanded by this document.
Set A and Set B share zero paths. Combined authorized product surface for OQI-UX-I-R: 18 unique paths
(11 + 7), plus these two governance companions.

## 9. Authorization

The exact 7 paths in §7 are authorized for implementation as part of OQI-UX-I-R, verification by OQI-UX-VM,
and merge to `main` upon independent adversarial confirmation, strictly as a pass-through completion under the
constraints of §5-6 above. This document does not authorize any change to CDD-045, its Artifact Authorization,
the first companion, any OQI1-7 domain class, any migration, `keycloak/ctec-realm.json`, or any Docker-G
artifact.
