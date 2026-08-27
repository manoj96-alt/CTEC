# CDD-028 — Ontology Modeling Read Authority Artifact Authorization Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-028-Governed-Visual-Ontology-Modeling-Keycloak-Scope-Defect-Authorization.md`,
`CDD-015-Optional-Client-Scopes-Regression-Assertion-Defect-Authorization.md`
Classification: ARTIFACT AUTHORIZATION AMENDMENT (Primary: PRODUCT GAP; Secondary: GOVERNANCE GAP; Severity: P2)

## Purpose

This post-freeze amendment introduces a dedicated, non-consequential `ontology-modeling:read`
scope and widens the two Gate M GET endpoints to accept it, so that a viewer of Ontology Modeling
proposals is never required to hold proposal-creation or approval authority merely to see them. It
does not alter CDD-028's MODEL/SUBMIT, APPROVE/REJECT, or PUBLISH lifecycle semantics in any way,
and it does not alter the GAP-11-established DEFINED=YES/OPTIONAL=YES/DEFAULT=NO contract for
`ontology-modeling:propose`, `:approve`, or `:publish`.

## Context / problem statement

GAP-11 correctly registered the three consequential Gate M scopes as optional/not-default. Doing so
made visible a pre-existing, separately-governed condition (GAP-11-FOLLOWUP-1): the Gate M
Artifact Authorization's own §10 endpoint table attaches both GET endpoints to `:propose OR
:approve` rather than to any independent read scope — a deliberate, documented deferral at the
time ("no existing scope or role in the repository maps to any of these actions," CDD-028 §11),
not an implementation defect. Because the demo persona receives neither consequential scope by
design (matching the identical, already-accepted pattern for `entity-resolution:decide` and
`supplier-risk:submit/retry/replay`), it also cannot view the Ontology Modeling Studio's proposal
list at all — the only gate in the system where read authority is entangled with write authority.

## Root cause

CDD-028 §14 defines only `:propose` and `:approve`; no read scope was ever defined at the CDD
level, and the Artifact Authorization resolved the resulting GET-endpoint gap by reusing the two
existing write scopes rather than introducing a third. This is architecturally inconsistent with
every other governed gate in the repository (`entity-resolution:read`/`:decide`,
`supplier-risk:read`/`:submit`), each of which cleanly separates read from write authority.

## Product Owner decision (binding)

Introduce `ontology-modeling:read` as a new, non-consequential, default-granted scope. The three
existing consequential scopes are unaffected. Production personas beyond the current single demo
identity are explicitly NOT authorized by this document (no role/user/group/persona creation).

## Read/write authority model (binding)

- `ontology-modeling:read` — non-consequential list/get authority.
- `ontology-modeling:propose` — consequential creation authority (unchanged).
- `ontology-modeling:approve` — consequential approve/reject authority (unchanged).
- `ontology-modeling:publish` — consequential publication authority (unchanged).

## Endpoint authorization contract (binding, exact)

| Method | Path | Scope |
|---|---|---|
| POST | `/api/v1/ontology-modeling/proposals` | `ontology-modeling:propose` (unchanged) |
| GET | `/api/v1/ontology-modeling/proposals/{id}` | `ontology-modeling:read` OR `:propose` OR `:approve` |
| GET | `/api/v1/ontology-modeling/proposals` | `ontology-modeling:read` OR `:propose` OR `:approve` |
| POST | `/api/v1/ontology-modeling/proposals/{id}/approve` | `ontology-modeling:approve` (unchanged) |
| POST | `/api/v1/ontology-modeling/proposals/{id}/reject` | `ontology-modeling:approve` (unchanged) |
| POST | `/api/v1/ontology-modeling/proposals/{id}/publish` | `ontology-modeling:publish` (unchanged) |

Existing `:propose`/`:approve` GET access is preserved for backward compatibility — no principal
loses any capability it holds today.

## Keycloak provisioning contract (binding, exact)

New `clientScopes` entry:

```json
{
  "name": "ontology-modeling:read",
  "protocol": "openid-connect",
  "description": "CDD-028 canonical scope -- Governed Visual Ontology Modeling read/list/view authority (non-consequential; granted to the primary demo persona).",
  "attributes": {
    "include.in.token.scope": "true",
    "display.on.consent.screen": "false"
  }
}
```

Add `"ontology-modeling:read"` to `ctec-frontend.defaultClientScopes`. Do not add it to
`optionalClientScopes`. `ontology-modeling:propose`/`:approve`/`:publish` remain byte-identical in
`optionalClientScopes`; `defaultClientScopes` gains only this one new entry.

## Frontend authentication contract (binding)

Add `ontology-modeling:read` to `frontend/lib/auth/config.ts`'s canonical default scope string,
matching the established convention of explicitly listing default read scopes
(`supplier-risk:read`, `entity-resolution:read`) rather than relying on implicit Keycloak
default-grant behavior alone.

## Demo model (binding)

The primary demo persona receives `ontology-modeling:read` (via the default-scope mechanism) and
continues to NOT receive `:propose`/`:approve`/`:publish`. VIEW/LIST/GET proposals: authorized.
CREATE/APPROVE/REJECT/PUBLISH: continue to correctly receive `403 AUTHORIZATION_SCOPE_REQUIRED`,
matching PAD-002 §11's established principle that write-action 403 for the demo persona is
correct security behavior, not a defect.

## Production-model boundary (binding)

This document does not create any new persona, role, user, or group. The long-term production
model (Viewer/Proposer/Approver-Rejecter/Publisher) remains compatible with this change and is
explicitly deferred to a future, separate governance phase.

## Exact implementation allowlist (binding)

| Path | Operation |
|---|---|
| `keycloak/ctec-realm.json` | MODIFY |
| `backend/app/api/ontology_modeling/router.py` | MODIFY |
| `backend/app/tests/test_ontology_modeling_router.py` | MODIFY |
| `frontend/lib/auth/config.ts` | MODIFY |
| `frontend/tests/browser-session.test.ts` | MODIFY |

```
AUTHORIZED_NEW    = 0
AUTHORIZED_CHANGE = 5
AUTHORIZED_DELETE = 0
TOTAL IMPLEMENTATION SURFACE = 5
```

`backend/app/tests/test_runtime_architecture.py` requires NO modification — all five paths above
are already members of the existing `AUTHORIZED_CHANGED_PATHS` allowlist. If implementation
discovers this is no longer true at execution time, implementation MUST STOP and report rather
than silently registering a sixth path.

No second implementation surface is authorized. In particular, NOT authorized: any change to
`defaultClientScopes`'s treatment of `:propose`/`:approve`/`:publish`; any new Keycloak
user/role/group; any frontend UI scope-conditional rendering; any change to approve/reject/publish
application logic; any new persistence/migration; any GAP-8 or Gate R/S/V/W work.

## Prohibited changes (security firewall, binding)

This amendment does not authorize: making any of `:propose`/`:approve`/`:publish` default;
treating `:read` as implying any write authority; changing approve/reject/publish semantics; any
authorization bypass; any demo-only backend exception; hardcoding `ctec-demo-user` (or any other
literal identity) in backend authorization logic; role-name checks replacing scope checks; new
personas/users/roles/groups; modification of any unrelated Keycloak scope; modification of any
unrelated Gate; any GAP-8 or Gate R/S/V/W implementation.

## Test / regression contract (binding)

Before this future implementation may be accepted: (1) exact 5-file diff, CREATE=0/MODIFY=5/
DELETE=0; (2) `ontology-modeling:read` exists exactly once in `clientScopes`, exactly once in
`defaultClientScopes`, zero times in `optionalClientScopes`; (3) `:propose`/`:approve`/`:publish`
remain exactly as GAP-11 established (existing test unmodified and passing); (4) a principal
holding only `:read` can GET both endpoints and receives 403 on all four write endpoints; (5) a
principal holding only `:propose` (no `:read`) can still GET both endpoints (backward-compatibility
preserved); (6) `browser-session.test.ts`'s canonical-scope assertion updated and passing, with
explicit negative assertions that the scope string never contains `ontology-modeling:propose`,
`:approve`, or `:publish`; (7) full backend suite passes; (8) full frontend suite (format/lint/
typecheck/tests/build) passes; (9) `docker compose config --quiet` passes; (10)
`scripts/verify_architecture_release.py` passes; (11) CDD-028, its Artifact Authorization, the
GAP-11 Defect Authorization, and every other tracked frozen governance document remain
byte-identical; (12) exact-head CI passes before merge; (13) post-merge CI passes.

## Frozen-governance firewall

CDD-028 (core) remains FROZEN and PUBLISHED, unchanged. The Gate M Artifact Authorization's §10
endpoint table is the only prior text this amendment supersedes, and only to the exact extent of
widening the two GET rows and adding the new scope row above — no other clause is affected. The
GAP-11 Keycloak Scope Defect Authorization remains unchanged and unsuperseded.

## Cross-gate firewall

This document does not touch or authorize: GAP-8; Gate R; Gate S; Gate V; Gate W; generalized DQ;
Simulation; MCP; the Gate F↔H-U bridge; POST-U/X-DEBT-6 (remains CLOSED); POST-X-TEST-DEBT-1
(remains CLOSED); any other Gate's Keycloak scopes.

## Acceptance criteria

All items in the Test/regression contract above, verified fresh at implementation time, plus a
clean adversarial review confirming no consequential scope became default and no existing test was
weakened.

## Rollback / fail-closed conditions

If any authorized file's actual required change differs from what this document specifies, or if a
sixth file is discovered to be required, implementation MUST STOP and return to Product Owner
rather than silently widening scope. If `test_runtime_architecture.py`'s allowlist is found to no
longer contain all five paths at implementation time, implementation MUST STOP.

## Publication / implementation boundary

**Publication/freeze of this document does NOT itself authorize implementation.** A separate,
subsequent Product Owner implementation authorization is required before any of the five listed
files may be modified — matching every prior companion's identical binding precondition in this
lineage.

## Authorization

This Artifact Authorization Amendment is approved for publication, reached via GAP-11-FOLLOWUP-1
R0 (discovery, Product Owner Option-C decision) → R1 (drafting, Product Owner approval) → this R2
publication turn. CDD-028 and the Gate M Artifact Authorization remain FROZEN and PUBLISHED,
unchanged by this approval. GAP-11 remains RESOLVED/MERGED/VERIFIED/CLOSED, unaffected by this
purely additive amendment.
