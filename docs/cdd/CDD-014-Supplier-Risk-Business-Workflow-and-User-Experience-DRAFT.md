# CDD-014 — Supplier Risk Business Workflow and User Experience

Version: 1.0 DRAFT

Status: ARCHITECTURE REVIEW — BLOCKED

Reviewed baseline: remote main `9d2ab3042f22e69b9d41d01fd0905cbb7cd73ec7`

Mandatory template: CDD Template v2.2

## 1. Objective and business outcome

Provide a secure, accessible, role-aware business interface that consumes only the frozen CDD-013
supplier-risk API. Authorized users can submit an assessment, observe its logical execution and
attempts, understand stage progress and the governed recommendation, inspect permitted references,
and request eligible retry or privileged replay. The interface transports server authority; it does
not orchestrate capabilities, evaluate policy, persist business records, or reinterpret outcomes.

## 2. Governing authorities

- Architecture Registry and current frozen baseline authorities at the reviewed commit.
- PAS-001 v1.0 and IDP-001 v1.0.
- CDD-013 v1.0, IMPLEMENTED / VERIFIED / FROZEN.
- CDD-010 through CDD-012 only through their CDD-013 representations.
- Current frozen PAD, EIC, EOM, ESM, RFC-011, RFC-014, CIM, CVR, PMM, RSP, RCP, GRM, and DRM
  authorities referenced by CDD-013.
- CDS-001 v1.3 and CDD Template v2.2.

The canonical PAS-001 scopes are `supplier-risk:submit`, `supplier-risk:read`,
`supplier-risk:retry`, and `execution:replay`. The uppercase names in the initiating request are
treated only as human-readable capability labels and do not replace the frozen scope strings.

## 3. In scope

- The route, screen, component, state, accessibility, and security boundaries specified by the
  CDD-014 package.
- A browser application consuming `/api/v1/supplier-risk` through one version-aware API boundary.
- Server-authoritative submission, status, attempts, stages, result, retry, and replay behavior.
- Presentation-only authorization awareness; CDD-013 remains the enforcement authority.
- Responsive WCAG 2.2 AA behavior and unit, component, contract, accessibility, and end-to-end tests.

## 4. Out of scope

- Changes to CDD-010 through CDD-013 semantics or capability behavior.
- Business rules, recommendation derivation, policy interpretation, orchestration, backend
  persistence, direct database access, alternate APIs, UI-driven AuthorityContext, or checkpoint
  construction.
- Production deployment, analytics, notifications, enterprise integrations, unrestricted
  administration, or CDD-015 production-readiness work.

## 5. Required contract remediation

Implementation remains blocked by the consolidated P0 findings in the preimplementation report:

1. publish a tenant-safe work-queue/list contract or remove that journey from CDD-014;
2. make the external submission schema explicit and closed in CDD-013 OpenAPI;
3. expose terminal classification, safe diagnostic, conditional-verification, evidence,
   provenance, and policy-traceability fields already promised by PAS-001;
4. expose server-authoritative retry eligibility and replayable checkpoint options;
5. govern browser OIDC session establishment, renewal, logout, and token handling.

No frontend may infer these values from recommendation text, stage data, HTTP status, hidden
controls, or caller-supplied identity information.

## 6. Authorized business artifacts

None authorized. CDD-014 presents existing governed records and outcomes only.

## 7. Authorized external contracts

READ-ONLY until the P0 remediation is frozen: CDD-013 OpenAPI, PAS-001, and IDP-001. CDD-014 may
generate or implement a client only after the corrected contract is published. No API field,
endpoint, enum, scope, or authentication behavior may be invented in frontend code.

## 8. Authorized persistence artifacts

None authorized. Browser storage of bearer tokens, complete API responses, sensitive evidence, or
trusted authority data is prohibited. Only non-sensitive presentation preferences may be retained
after security review.

## 9. Authorized configuration artifacts

After approval, only public frontend configuration for API origin, API version, and governed OIDC
client settings is authorized. Secrets, client credentials, tenant selectors, trusted roles/scopes,
or AuthorityContext configuration are prohibited.

## 10. Authorized implementation and test artifacts

The exhaustive proposed boundary is defined in
`CDD-014-EXACT-CHANGED-FILE-AUTHORIZATION.md`. It grants no implementation authority while this CDD
is blocked. All unlisted repository paths are READ-ONLY.

## 11. Acceptance criteria

1. Every required journey in the business-journey specification is covered without client-side
   business inference.
2. Every operation maps to the corrected frozen CDD-013 contract and canonical PAS scope.
3. The interface distinctly presents execution state, business outcome, stage state, technical
   failure, recommendation actionability, and permitted next action.
4. Retry and replay remain distinct, idempotent, deliberate, and server-authoritative.
5. Cross-tenant existence is never disclosed; authentication and authorization failures are safe.
6. No token, sensitive evidence, complete response, or authority context enters persistent browser
   storage, URLs, logs, analytics, or unsafe rendered HTML.
7. WCAG 2.2 AA automated checks and the specified manual keyboard/screen-reader checks pass.
8. Frontend unit, component, contract, integration, and end-to-end tests pass together with all
   existing protected checks.
9. Changed-file authorization, dependency, secret, API-schema, and architecture-drift checks pass.

## 12. Rollback

Rollback is frontend-only: revert the CDD-014 implementation merge and restore the preceding route
and shell files. No backend data rollback, API downgrade, or destructive action is authorized.

## 13. Architecture drift check

The proposed UI introduces no business entity, canonical attribute, canonical relationship,
business rule, RFC exception, architecture bypass, or unapproved technology. Implementation must
stop if satisfying the UI requires any such change.

## 14. Gate

**BLOCKED — ADDITIONAL GOVERNANCE DECISION REQUIRED.** The package is complete, but the five
contract/security gaps in Section 5 must be resolved as one bounded CDD-013/PAS/IDP clarification
before CDD-014 can be approved for implementation.
