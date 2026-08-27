# CDD-038 — Governed API Version Declaration

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-033 (FROZEN, Gate X — §42: "Gate W (production API expansion/
versioning/management)" — this CDD is the first to define, not merely name, Gate W), CDD-029
(FROZEN — GAP-5: "Gate W, production API expansion/versioning/management, MISSING/
UNDERSPECIFIED" — independently corroborates CDD-033's naming)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via a single combined
discovery-decide-govern phase (Gate W0), per the compressed small-gate process established for
Gate R/S/V: exhaustive repository discovery of CTEC's actual `/api/v1` route surface (38 routes
across 10 families), the current API-management capability matrix, and this freeze-ready text —
pending Product Owner publication authorization (Gate W1).

## 1. Title

Governed API Version Declaration — the first implementation of Gate W (production API
expansion/versioning/management).

## 2. Capability statement (exact, binding)

CTEC publishes a single, authoritative, mechanically route-verified declaration of its currently
supported API version(s) through one governed, read-only endpoint.

## 3. Problem

CTEC has 38 `/api/v1/*` routes across 10 independently-governed route families, each hardcoding
its own `"v1"` path prefix, plus one further hardcoded `"v1"` literal in `/api/config`'s response.
No single source of truth ties these together. CDD-033 §42 named "Gate W (production API
expansion/versioning/management)" as the future owner of this gap; CDD-029's GAP-5 confirms it as
"MISSING/UNDERSPECIFIED." No prior CDD defines what "version management" concretely means for
CTEC.

## 4. Why now

Gate V (CLOSED) was the last capability-bearing gate in the Q→R→S→T→V lineage. Before any further
business capability expands the `/api/v1` surface further, establishing a single authoritative
version declaration — however small — closes CDD-033's own forward-declared gap and gives future
gates a place to register, rather than each independently inventing version semantics.

## 5. Dependencies (binding)

None. Gate W v1 has zero functional coupling to Gate Q, Gate R, Gate S, Gate T, or Gate V. It reads
FastAPI's own route table (already-existing, unmodified `create_app()`), not any gate-specific
service.

## 6. Scope

Exactly one read-only endpoint declaring CTEC's currently supported API version(s), backed by a
fixed, code-level registry, with a mechanical test proving the registry cannot drift from the real
route surface.

## 7. Non-goals (binding)

No API gateway integration. No distributed rate limiting (already exists per-capability,
unrelated to this CDD). No quotas/billing. No developer portal. No frontend/UI of any kind (Gate
X/CDD-033 owns frontend; nothing assigns further UI to Gate W). No API-key issuance. No new
authentication system or security principal. No dynamic route creation or runtime route mutation.
No arbitrary lifecycle administration (registry is a frozen constant, not a mutable table). No
support for multiple simultaneous major versions (CTEC has only ever had "v1"). No automatic
compatibility analysis or schema-diff engine. No client SDK generation. No webhooks. No absorption
of Gate V's own accepted, separately-governed idempotency deferral (CDD-037 §6/§36). No DQ
capability of any kind. No OpenAPI governance (unrelated pre-existing gap, not assigned to this
CDD). No unification of the existing, inconsistent per-family error envelopes — that would be a
large, disruptive, separately-governed change. No deprecation or sunset semantics in v1 — nothing
has ever been deprecated; a single `SUPPORTED` state is the honest v1 model.

## 8. Predecessor dependencies (binding, restated)

Gate Q, Gate R, Gate S, Gate T, and Gate V remain byte-unchanged, unimported, uncalled by any Gate
W file.

## 9. Domain/version model (binding, frozen)

```
ApiVersionState (closed StrEnum, exactly one member in v1):
  SUPPORTED = "SUPPORTED"

SupportedApiVersion (frozen value object -- no identity, no lifecycle, no tenant ownership):
  version: str
  state:   ApiVersionState

SUPPORTED_API_VERSIONS: tuple[SupportedApiVersion, ...] =
  (SupportedApiVersion(version="v1", state=ApiVersionState.SUPPORTED),)
```

This is a fixed, code-level constant, not durable state. Adding a second version requires its own,
separate, future governance cycle.

## 10. Authority model (binding, frozen)

```
GET /api/versions   AUTHENTICATED = NO   SCOPES = none   TENANT = none   MUTATING = NO   AUDITED = NO
```

No new Keycloak scope. No new security principal. No confused-deputy surface exists (no write
authority anywhere in this design).

## 11. Tenant model (binding)

Global platform metadata, identical for every tenant. No `tenant_id` is read, derived, or exposed
anywhere in this capability.

## 12. Persistence decision (binding, frozen)

```
New durable state: NONE
Migration:         NONE
```

The truth is derived deterministically from the Section 9 code constant. No table, no migration.

## 13. Application service

None. The router reads `SUPPORTED_API_VERSIONS` directly, exactly matching the existing
`app.api.config.router`/`app.api.version.router` precedent (both have no separate service layer).

## 14. API contract (binding, frozen)

```
GET /api/versions
  request:  none
  response: { "versions": [ { "version": "v1", "state": "SUPPORTED" } ] }
  status:   200
```

No other route. No PUT/PATCH/DELETE/POST. No per-version detail route.

## 15. Failure contract (binding, frozen)

No custom diagnostic code. No failure mode exists beyond FastAPI's own default routing behavior.

## 16. Audit contract (binding, frozen)

No audit record for this endpoint, matching the existing, identical-shape `/api/config` and
`/api/version` precedent (both currently audit-free).

## 17. Version-authority / route-registry consistency invariant (binding, load-bearing)

`SUPPORTED_API_VERSIONS` in `backend/app/api/api_versions/router.py` is the single source of
truth. A dedicated test introspects the real, running `create_app()` route table (not a static
file scan) and proves: (a) every entry in `SUPPORTED_API_VERSIONS` has at least one real route
under `/api/{version}/`; (b) no route exists under `/api/v{N}/` for any `{N}` absent from
`SUPPORTED_API_VERSIONS`.

## 18. OpenAPI boundary (binding, restated)

Gate W does not govern `/docs`, `/redoc`, or `/openapi.json` exposure, security-scheme accuracy,
or authentication. These remain exactly as they exist today, unmodified by this CDD.

## 19. Keycloak impact (binding)

None. No scope is created or modified.

## 20. main.py impact (binding)

Exactly one import and one `app.include_router(api_versions_router, prefix=API_PREFIX)` line,
mirroring the existing `config_router`/`version_router` registration pattern. No other change.

## 21. dependency_container.py impact (binding)

None. The router requires zero injected dependencies.

## 22. Frontend boundary (binding)

No frontend file of any kind is created or modified by this CDD.

## 23. Gate Q/R/S/T/V firewalls (binding, restated)

`mcp_client.py`, `mcp_connector_catalog.py`, `governed_tool_executor.py`,
`gate_s_approval_service.py`, `gate_s_approval_repository.py`,
`gate_v_agent_service.py`, `gate_v_agent_resolution_repository.py`, and every Gate Q/R/S/T/V
domain/API/test file remain byte-unchanged, unimported, uncalled.

## 24. Gate V P3 firewall (binding, restated)

Gate V's accepted, CDD-037-deferred absence of proposal idempotency/deduplication is not
addressed, generalized, or absorbed by this CDD.

## 25. Gate W / DQ boundary (binding)

No DQ rule authoring, scoring, dashboard, issue management, remediation, certification, or
observability capability of any kind appears in this CDD. Health/status metadata (if any future
Gate W increment adds it) is not DQ and must never be relabeled as such.

## 26. Test requirements (binding, minimum set)

Endpoint returns the exact frozen response shape and status; the endpoint is reachable without
authentication; the route/registry-consistency invariant (Sec17) holds against the real route
table; `test_runtime_architecture.py`'s existing allowlist/test suite continues to pass unmodified.

## 27. Architecture invariants (binding, restated)

Sec17's route/registry-consistency invariant is the sole architecture invariant this CDD
introduces. No single-write-site invariant applies (no ORM is introduced).

## 28. Artifact Authorization linkage

A separate Artifact Authorization enumerates the exact, closed 4-file implementation surface
(CREATE=2, MODIFY=2, DELETE=0). Publication and freeze of this CDD does NOT itself authorize
implementation.

## 29. Future extensions (non-binding, informational)

A second API version, deprecation/sunset semantics, generalized error-envelope unification,
OpenAPI governance, or generalized rate-limiting/idempotency each require their own, separate,
explicit Product Owner architecture decision and CDD. The unassigned approval/agent-resolution UI
promise from CDD-036 §31 / CDD-037 §29 is not claimed, scheduled, or addressed by this CDD.

## 30. Closure criteria

Gate W v1 may be classified RESOLVED/MERGED/VERIFIED/CLOSED only after: the merge commit is
confirmed as new authoritative main via both git and the GitHub API; the post-merge diff from
pre-merge main contains exactly the 4 authorized files; the route/registry-consistency invariant
passes against the real merged route table; Gate Q/R/S/T/V remain byte-identical.

## 31. Explicit closure claim permitted by Gate W v1

Upon successful implementation and merge, CTEC may truthfully claim: "CTEC publishes a single,
authoritative, mechanically route-verified declaration of its currently supported API version(s)
— closing CDD-033's forward-declared production-API-versioning gap — without introducing
deprecation/sunset semantics, a mutable lifecycle registry, a new security authority, or any
change to Gate Q, Gate R, Gate S, Gate T, or Gate V." No broader claim (API gateway, rate limiting
platform, developer portal, DQ, frontend) is authorized.

## 32. Authorization

This CDD is approved for publication, reached via Gate W0 (combined discovery, architecture
decision, and drafting). Pending Product Owner review before W1 publication. CDD-033 and CDD-029
remain FROZEN and PUBLISHED, unchanged by this document.
