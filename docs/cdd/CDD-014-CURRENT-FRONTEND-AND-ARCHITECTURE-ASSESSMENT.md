# CDD-014 — Current Frontend and Architecture Assessment

Version: 1.0

Reviewed commit: `9d2ab3042f22e69b9d41d01fd0905cbb7cd73ec7`

## Current frontend

- Next.js 16.3, React 19.1, TypeScript 5.8, Tailwind CSS 4, ESLint, Prettier, Vitest, jsdom, and
  Testing Library are already present.
- The frontend is a five-page informational shell with `SiteShell`, `ContentPage`, global CSS, and
  two component tests. It has no supplier-risk route, API client, OIDC session, application state,
  workflow components, or committed product-design assets.
- No existing component library, form library, data-fetching library, router abstraction beyond
  Next.js App Router, accessibility test package, browser end-to-end runner, or OpenAPI generator is
  established.
- `cognitive-engine/` contains ignored local build/coverage residue, not tracked frontend source.
  The tracked product frontend is `/frontend`.

## Frozen boundary

CDD-013 exposes seven routes under `/api/v1/supplier-risk`; controllers and frontend must not access
runtime tables. PAS-001 makes CDD-013 the authorization and tenant-isolation authority. IDP-001
governs backend bearer validation but does not define a browser login/session protocol.

## Contract-to-implementation findings

The findings below describe the original baseline assessment. All P0 rows are **CLOSED** by
Baseline v1.6 and CDD-013 remediation merge `021cd1e5bd7062f3e2042e691fa48b5b1a346efb`.

| Finding | Severity | Evidence | Impact |
|---|---|---|---|
| No work-queue/list endpoint | P0 | CDD-013 router and OpenAPI contain submit and execution-by-ID only | Required assessment list cannot be implemented without a new external contract. |
| Submission payload is `dict[str, Any]` | P0 | `SupplierRiskSubmission.supplier_risk` | UI cannot know governed required fields or validate without duplicating CIM semantics. |
| Result omits evidence, provenance, policy trace, conditions verified, and safe diagnostic | P0 | `GovernedResultResponse` | Required views and conditional-action explanation cannot be truthful. |
| Execution response lacks PAS terminal classification | P0 | `ExecutionResponse` exposes free-form `state` and `result_code` | UI cannot safely separate rejection, gating, indeterminate, and failure. |
| Retry eligibility and replay options are not queryable | P0 | retry/replay are command-only; replay body contains reason only | UI would have to infer eligibility or fabricate checkpoint choices. |
| Browser OIDC lifecycle is not governed | P0 | IDP-001 defines resource-server validation only | Secure login, renewal, logout, redirect, and token storage cannot be selected safely. |
| No committed OpenAPI artifact or client generator | P1 | OpenAPI is generated at runtime in backend tests | A contract snapshot/generation or conformance strategy must be selected after remediation. |
| Requested uppercase scope labels differ from PAS strings | Resolved by precedence | PAS-001 canonical strings are lower-case colon-delimited | UI uses PAS strings; labels remain documentation only. |

## Technology recommendation after remediation

Retain Next.js, React, TypeScript, Tailwind, Vitest, and Testing Library. Prefer platform primitives
and small local components. Any OIDC library, OpenAPI generator, accessibility runner, or E2E tool
is a dependency change and must be explicitly authorized after its contract and security purpose is
known. Do not add a general state-management library unless implementation evidence shows React and
URL/server state are insufficient.
