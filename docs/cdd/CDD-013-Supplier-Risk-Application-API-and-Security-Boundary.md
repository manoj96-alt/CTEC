# CDD-013 — Supplier Risk Application API and Security Boundary

Version: 1.0

Status: IMPLEMENTED / VERIFIED / FROZEN

Implementation authority: remote main `ba59931de602e4cd66bb8edf8b2266b718b17073`

Implementation publication: PR #44; merge `bc3dc8b1259df5521b7eb02766d2b752149ad0ad`

Reviewed baseline: remote main `96e5ec10a34b7fbed5b2868330f6e2bb2bc875a4`

Mandatory template: CDD Template v2.2

## 1. Objective and business outcome

Expose the completed CDD-010 runtime, CDD-011 supplier-risk capability chain, and CDD-012 durable
execution/recovery services through one bounded, versioned application API. An authenticated and
authorized tenant caller can submit a supplier-risk assessment, safely observe its logical
execution and attempts, retrieve the governed recommendation and permitted references, request an
idempotent retry, and—only with CDD-012 recovery authority—request privileged replay.

The API transports outcomes; it never derives, changes, or reinterprets them.

## 2. Governing authorities

- Architecture Registry v1.3 and Baseline Record v1.5.
- EAH-001 v1.5; RFC-010 v1.0; RFC-011 v1.0; RFC-013 v1.2; RFC-014 v1.2.
- PAD-001 v1.5; EIC-001 v1.3; EOM-001 v1.4; ESM-001 v1.3; RSP-001 v1.0.
- CIM-001 v1.1; CVR-001 v1.0; PMM-001 v1.1; Physical Model v1.4.
- Current frozen ERM, SRM, ASM, AEM, KRM, DRM, GEM, and GRM specifications.
- CDD-010 v1.3, CDD-011 v1.0, and CDD-012 v1.2, all frozen and implemented.
- CDS-001 v1.3 and CDD Template v2.2.

TAS-001, the Logical Model, and EAD-001 are non-authoritative Development references and grant no
implementation authority. Existing FastAPI and Pydantic usage is an implementation convention,
not a new architectural authority.

## 3. Gate dependencies

Implementation requires one consolidated frozen clarification, provisionally **PAS-001 — Supplier
Risk Product API and Security Contract**, resolving all P0 items in the accompanying assessments:

1. the governing PAD protocol/profile for supplier-risk submission, observation, result,
   retry, and replay;
2. the trusted authentication source and derivation of AuthorityContext;
3. command/read role and scope matrix, tenant-resource binding, and disclosure policy;
4. product API version, compatibility, idempotency, HTTP error, retry, and replay semantics;
5. rate-limit, payload-limit, audit-evidence, and safe-observability minimums.

PAS-001 may be a PAD clarification instead of a new identifier if governance prefers. It must not
change business semantics, add canonical entities, or redesign runtime execution.

## 4. In scope after dependency closure

- One `/api/v1/supplier-risk` API surface implementing the approved PAD profile.
- Trusted-boundary authentication through an injected verifier approved by PAS-001.
- Tenant-scoped authorization for every command and read.
- Translation between external JSON contracts and the existing `SupplierRiskRequest`,
  `InvocationRequest`, `AuthorityContext`, runtime snapshots, and CDD-012 recovery contracts.
- Read-only status, stage, safe-failure, result, evidence/provenance-reference, and policy-reference
  projections through application services/repositories.
- Idempotent submission/retry and separately privileged replay.
- Safe audit events, redaction, request-size enforcement, rate limiting, OpenAPI, and deterministic
  error mapping.

## 5. Out of scope

- New business or canonical semantics, entities, attributes, relationships, recommendations, or
  governance standing.
- A second orchestration or persistence path; direct ORM/table access from controllers.
- UI, production deployment, identity-provider administration, credential/token issuance or
  storage, distributed gateway infrastructure, analytics, webhooks, events, or enterprise
  integrations.
- Executing supplier, sourcing, contractual, financial, or operational actions.
- Returning protected handoff payloads, secrets, credentials, full AuthorityContext, raw evidence,
  or unrestricted narratives.

## 6. API behavior

- Submission invokes only `CognitiveEngineRuntime.invoke` with the CDD-011 ports and CDD-012 store.
- Observation is tenant-scoped and application-service mediated.
- GRM standing and recommendation actionability are transported exactly as persisted.
- `Completed` includes ordinary success and successful business-gated termination. `Failed` means
  technical execution failure. Pre-admission protocol/validation rejection creates no execution.
- Retry creates a new request/attempt only when the frozen retry matrix permits it. Replay creates
  a linked attempt and requires CDD-012 replay authority. Neither operation mutates a terminal
  attempt.

## 7. Authorized Business Artifacts

None authorized. CDD-013 consumes existing supplier-risk and governance outcomes only.

## 8. Authorized External Contracts

All entries are active under PAS-001 v1.0.

| Path | Action | Authority | Purpose | Prohibited changes | Evidence |
|---|---|---|---|---|---|
| `backend/app/api/supplier_risk/schemas.py` | CREATE | PAS-001; PAD-001 | Exact v1 request/response/error schemas. | No business derivation or trusted caller claims. | OpenAPI snapshots and schema tests. |
| `backend/app/api/supplier_risk/router.py` | CREATE | PAS-001; EIC/PAD | Versioned command/read endpoints. | No direct ORM, capability, or policy access. | Route and boundary tests. |
| `backend/app/api/supplier_risk/errors.py` | CREATE | PAS-001; EIC/ESM | Stable safe diagnostic and HTTP mapping. | No stack traces or semantic reinterpretation. | Error matrix tests. |

## 9. Authorized Implementation Artifacts

| Path | Action | Purpose |
|---|---|---|
| `backend/app/api/supplier_risk/__init__.py` | CREATE | Bounded API package. |
| `backend/app/api/supplier_risk/dependencies.py` | CREATE | Inject authenticated principal, application service, rate limiter, and audit ports. |
| `backend/app/api/supplier_risk/security.py` | CREATE | Validate the approved authentication result and derive immutable AuthorityContext. |
| `backend/app/api/supplier_risk/audit.py` | CREATE | Emit allowlisted safe command/read/replay audit events. |
| `backend/app/api/supplier_risk/rate_limit.py` | CREATE | Apply the PAS-001 approved limiter through an injected clock/store boundary. |
| `backend/app/application/supplier_risk_api.py` | CREATE | Orchestrate API use cases over existing runtime/repository ports only. |
| `backend/app/runtime/persistence/repository.py` | MODIFY | Add tenant-scoped logical-execution, attempt, stage, result, and reference queries plus governed retry/replay operations. |
| `backend/app/runtime/persistence/contracts.py` | MODIFY | Add read/retry/replay repository ports and safe projections only. |
| `backend/app/core/dependency_container.py` | MODIFY | Compose existing runtime/integration/persistence with injected API security controls. |
| `backend/app/main.py` | MODIFY | Register the authorized router and boundary middleware only. |
| `README.md` | MODIFY | Document API construction, security assumptions, and validation. |

The additional exact implementation paths authorized by the approved remediation are enumerated
in `CDD-013-EXPANDED-CHANGED-FILE-AUTHORIZATION.md`. All unlisted paths are READ-ONLY.

## 10. Authorized Persistence Artifacts

Exactly one non-canonical `api_security_audit_events` table, its ORM, repository, and migration are
authorized by RFC-014 v1.3, PMM-001 v1.2, and Physical Model v1.5. No other persistence artifact or
canonical writer is authorized.

## 11. Authorized Configuration Artifacts

| Path | Action | Purpose |
|---|---|---|
| `.env.example` | MODIFY | Document non-secret issuer/audience, payload limit, rate-limit, and trusted-boundary settings approved by PAS-001. |
| `backend/app/core/config.py` | MODIFY | Validate those settings; never contain credentials or permissive production defaults. |

## 12. Authorized Test Artifacts

| Path | Action | Required coverage |
|---|---|---|
| `backend/app/tests/test_supplier_risk_api_contracts.py` | CREATE | OpenAPI, fields, enums, validation, compatibility, pagination. |
| `backend/app/tests/test_supplier_risk_api_commands.py` | CREATE | Submit, duplicate, concurrent, retry, replay, actionability. |
| `backend/app/tests/test_supplier_risk_api_queries.py` | CREATE | Logical execution, attempts, stages, results, permitted references. |
| `backend/app/tests/test_supplier_risk_api_security.py` | CREATE | Authentication, tenant isolation, roles/scopes, redaction, limits, audit. |
| `backend/app/tests/test_supplier_risk_api_failures.py` | CREATE | Rejection, gating, failure, unsupported versions, safe diagnostics. |
| `backend/app/tests/test_supplier_risk_api_restart.py` | CREATE | PostgreSQL restart, durable reads, retry/replay recovery. |
| `backend/app/tests/test_supplier_risk_api_architecture.py` | CREATE | Exact file/import/layer/dependency boundary. |
| `backend/app/tests/test_system_api.py` | MODIFY | Router registration and system regression. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Extend the cumulative changed-file allowlist only for CDD-013-authorized paths. |
| Existing CDD-010/011/012 tests | READ-ONLY | Must pass unchanged. |

No other test artifact is authorized.

## 13. Acceptance criteria

1. All acceptance scenarios in the preimplementation report pass on PostgreSQL.
2. No route can construct AuthorityContext from untrusted business payload or caller-controlled
   identity headers.
3. Every lookup is tenant-scoped before existence is disclosed; cross-tenant access returns the
   PAS-001 safe response.
4. Duplicate/concurrent submission, retry, and replay preserve CDD-010/012 idempotency and
   immutable attempt history.
5. Recommendation, standing, actionability, references, and gates are transported without
   reinterpretation.
6. Raw protected payloads, full evidence, authority details, tokens, credentials, stack traces, and
   unsafe database errors never enter API responses or logs.
7. API and control-metadata versions reject deterministically without downgrade or coercion.
8. Controllers depend only on application/security ports and never ORM models or capabilities.
9. Full CDD-010/011/012 regression, ≥80% total coverage, strict typing, formatting, lint,
   architecture, dependency, checksum, manifest, secret, and changed-file checks pass.

## 14. Migration and rollback

Migration `0009_api_security_audit` creates only the authorized append-only record and indexes.
Rollback drops its trigger/function/indexes/table without changing runtime or capability records.

## 15. Architecture-drift checklist

Before closure verify: no new business entity, canonical attribute, or relationship; no BCS/RFC
violation; no layer bypass; no second runtime path; no direct controller persistence; no new
technology/dependency; no untrusted AuthorityContext; no recommendation reinterpretation; no
unauthorized file; and no UI/deployment expansion.

## 16. Gate

**APPROVED FOR IMPLEMENTATION.** PAS-001 v1.0, IDP-001 v1.0, RFC-014 v1.3, PMM-001 v1.2, and
Physical Model v1.5 close the P0 conflicts. Implementation is constrained to the exact expanded
allowlist.
