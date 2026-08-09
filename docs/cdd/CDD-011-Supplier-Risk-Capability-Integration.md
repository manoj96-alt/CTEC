# CDD-011 — Supplier-Risk Capability Integration

Version: 1.0 FROZEN

Status: FROZEN

Implementation state: IMPLEMENTED / VERIFIED

Closure authority: Closure Gate 2 approval at remote main `1f04d0aff3220b5c5c3be9713a1f04bb62fa402a`

Architecture Baseline: v1.2

Mandatory template: CDD Template v2.2

## 1. Objective and business outcome

Implement the production, in-process adapter chain that connects the CDD-010 runtime shell to the existing ERM → SRM → ASM → KRM → DRM → GRM capabilities for exactly one bounded vertical slice:

`Supplier risk event → governed sourcing recommendation`

The business outcome is a traceable governance result for a supplier-risk observation and its material, facility/region, and effective-time context. The result contains the governed recommendation, Governance standing, produced-record references, policy traceability, and safe diagnostic outcome. It never executes a supplier, sourcing, contractual, operational, or financial action.

## 2. Governing authorities

- Architecture Baseline v1.2 and Registry v1.2.
- Enterprise Constitution v1.0; EAH-001 v1.5; RFC-010 v1.0; RFC-011 v1.0; RFC-013 v1.2; RFC-014 v1.1.
- CIM-001 v1.1; CVR-001 v1.0; ARCH-005 v1.0; CAM-001 v1.2.
- ERM-001 v2.2; SRM-001 v2.2; ASM-001 v2.3; AEM-001 v1.1; KRM-001 v1.5; DRM-001 v1.3; GEM-001 v1.2; GRM-001 v1.3.
- EIC-001 v1.3; EOM-001 v1.3; ESM-001 v1.3; PAD-001 v1.5.
- PAD/EIC Legacy Invocation Compatibility Clarification v1.0; CDD-010 Trusted Runtime Control Metadata Clarification v1.0.
- CDS-001 v1.3; CDD Template v2.2; PMM-001 v1.0.
- Architecture Consistency Report v1.3; Architecture Drift Report v1.3; Architecture Remediation Report v1.2; Release Readiness Report v1.3; Dependency Matrix v1.2.

TAS-001, the Logical Model, and EAD-001 remain non-authoritative Development artifacts and grant no implementation authority.

## 3. In scope

- SourceObservation, AuthorityContext, supplier-risk request, capability handoff, final governance result, and safe error contracts exactly as defined by RFC-014/CIM-001.
- Six production adapters injected into the existing `CapabilityStepPorts` in the fixed CDD-010 order.
- Capability-local transaction ownership and immutable partial persistence through existing stores/repositories.
- Outcome gating, business-gated successful termination, and technical fail-fast behavior.
- Bounded sourcing-status and recommendation policy evaluation using only the closed RFC-014/CIM-001 vocabularies.
- Separate trusted control metadata, runtime-owned `admitted_at`, and capability-owned timestamps.
- Existing invocation compatibility and deterministic pre-execution version rejection.
- Record-reference accumulation and final-result retrieval inside the in-process engine boundary.

## 4. Out of scope

- Product REST APIs, user interface, upload workflow, public transport, or direct capability endpoints.
- New canonical entities, attributes, relationships, or vocabulary beyond the two CVR-001 values.
- New database tables, ORM models, migrations, indexes, durable runtime state, distributed coordination, queues, or brokers.
- Changes to existing business outcomes or capability ordering.
- Automatic supplier activation, contracting, purchasing, payment, or other operational execution.
- Multi-use-case integration framework, generic rules engine, or universal adapter platform.
- Authentication provider implementation, credential storage, token handling, or authorization-policy ownership.
- Changes to application startup, composition root, deployment, dependencies, or environment configuration.

## 5. Authorized Business Artifacts

None authorized. CDD-011 implements released contracts and capability semantics; it creates no new business artifact.

## 6. Authorized External Contracts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `InvocationRequest` / trusted control metadata — `backend/app/runtime/contracts.py` | MODIFY | EIC-001 v1.3; PAD-001 v1.5; CDD-010 metadata clarification | Add versioned AuthorityContext and trusted timestamp control metadata without changing opaque payload meaning. | No product API, credentials, domain payload fields, or legacy reinterpretation. | Contract allowlist, compatibility, rejection, and security tests. |
| `ExecutionSnapshot` / final record references — `backend/app/runtime/contracts.py` | MODIFY | EIC-001 v1.3; ESM-001 v1.3; RFC-014 v1.1 | Expose only governed terminal outcome, safe diagnostics, and produced-record references. | No business payload disclosure or mutable lifecycle. | Snapshot and terminal-result tests. |

No other external contract is authorized.

## 7. Authorized Implementation Artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| Integration package marker — `backend/app/integration/__init__.py` | CREATE | CDD-011 | Define the bounded integration package. | No product exports. | Import and file-boundary test. |
| Integration contracts — `backend/app/integration/contracts.py` | CREATE | RFC-014 v1.1; CIM-001 v1.1 | Implement SourceObservation, AuthorityContext, supplier-risk request, handoff, result, record-reference, diagnostic, and gated-outcome models. | No new canonical entity or business vocabulary. | Field allowlists and validation tests. |
| Bounded integration policy — `backend/app/integration/supplier_risk_policy.py` | CREATE | RFC-014 v1.1; CIM-001 v1.1; DRM-001 v1.3; GRM-001 v1.3 | Determine sourcing status, closed recommendation, traceability, and standing. | No operational execution or configuration file. | Complete bounded rule matrix. |
| Adapter package marker — `backend/app/integration/adapters/__init__.py` | CREATE | CDD-011 | Define adapter package. | No direct consumer API. | Import test. |
| ERM adapter — `backend/app/integration/adapters/erm.py` | CREATE | ERM-001 v2.2; CIM-001 v1.1 | Translate governed request data to/from the existing ERM service and persist its immutable record. | No identity-policy changes. | Resolved/possible/unresolved and transaction tests. |
| SRM adapter — `backend/app/integration/adapters/srm.py` | CREATE | SRM-001 v2.2; CIM-001 v1.1 | Translate ERM output and observation provenance to/from the existing SRM service and persist its immutable record. | No vocabulary inference outside governed candidates. | Outcome-gating and provenance tests. |
| ASM adapter — `backend/app/integration/adapters/asm.py` | CREATE | ASM-001 v2.3; CVR-001 v1.0; CIM-001 v1.1 | Apply pre-ASM indeterminate gating; otherwise form the governed active-risk proposition and persist the Assertion Record. | `INDETERMINATE` must not become an Assertion Outcome. | Missing/conflicting evidence and predicate UUID tests. |
| KRM adapter — `backend/app/integration/adapters/krm.py` | CREATE | KRM-001 v1.5; AEM-001 v1.1; RFC-013 v1.2 | Evaluate Assertion standing using authenticated Acceptance Evidence and persist the Knowledge Evaluation Record. | No approval production or inferred authority. | Authority, evidence, and institutionalization tests. |
| DRM adapter — `backend/app/integration/adapters/drm.py` | CREATE | DRM-001 v1.3; CIM-001 v1.1 | Evaluate the closed recommendation vocabulary and carry complete bounded policy traceability into the existing Decision record/explanation contract. | No new knowledge or operational action. | Rule, traceability, and invalid-decision tests. |
| GRM adapter — `backend/app/integration/adapters/grm.py` | CREATE | GRM-001 v1.3; GEM-001 v1.2; RFC-013 v1.2 | Evaluate Governance outcome and derive the exact standing/condition result. | No approval authority; no conditional actionability before verification. | Outcome-standing and condition-evidence tests. |
| Adapter dependencies — `backend/app/integration/dependencies.py` | CREATE | RFC-014 v1.1; PMM-001 v1.0 | Hold injected service, policy, repository/store, and transaction dependencies without importing startup configuration. | No service locator, environment access, or global mutable state. | Construction and dependency-direction tests. |
| Supplier-risk pipeline factory — `backend/app/integration/pipeline.py` | CREATE | EOM-001 v1.3; CIM-001 v1.1; CDD-010 | Construct exactly six adapters as `CapabilityStepPorts` and return the in-process runtime dependency set. | No startup registration, alternate order, bypass, or product API. | Full ordered integration test. |
| Runtime contracts — `backend/app/runtime/contracts.py` | MODIFY | EIC-001 v1.3; PAD-001 v1.5 | Carry approved trusted control metadata and final safe result references. | Preserve legacy CDD-010 behavior. | Compatibility suite. |
| Runtime orchestration — `backend/app/runtime/orchestration.py` | MODIFY | EOM-001 v1.3; RFC-014 v1.1 | Carry separate AuthorityContext/timestamps and recognize business-gated successful termination. | No semantic interpretation or adapter construction. | Order, metadata, and gated-termination tests. |
| Runtime facade — `backend/app/runtime/engine.py` | MODIFY | EIC-001 v1.3; ESM-001 v1.3 | Admit the versioned control envelope and retain final safe result/reference metadata. | No product transport, persistence, or capability wiring. | Legacy/new invocation and observation tests. |
| Developer documentation — `README.md` | MODIFY | CDD-011 | Document internal integration construction and validation. | No claim of product/API availability. | Documentation review. |

All existing domain services and models are READ-ONLY under this CDD. Adapters may call them but may not alter their business behavior.

## 8. Authorized Persistence Artifacts

The following existing persistence artifacts are READ-ONLY implementation dependencies: `backend/app/infrastructure/persistence/entity_resolution_store.py`, `semantic_resolution_store.py`, `assertion_record_store.py`, `knowledge_evaluation_store.py`, `decision_repository.py`, `governance_repository.py`, and `unit_of_work.py`.

Adapters may invoke these existing contracts through injected dependencies. No persistence source file, ORM model, migration, schema, index, projection, or database configuration may be created or modified. Each adapter owns one capability-local transaction: commit only after its capability record is valid; rollback only that capability transaction on technical failure. Previously committed immutable records remain traceable and are never compensated, deleted, or mutated.

## 9. Authorized Configuration Artifacts

None authorized. Policy inputs, candidates, authorized evidence, and repository/session factories must be injected. No file, environment key, default policy, loader, or configuration schema may be created or modified.

## 10. Authorized Test Artifacts

| Path | Action | Required coverage |
|---|---|---|
| `backend/app/tests/test_integration_contracts.py` | CREATE | Exact field sets, provenance, AuthorityContext trust/version/time rules, safe diagnostics. |
| `backend/app/tests/test_supplier_risk_policy.py` | CREATE | Complete sourcing-status, recommendation, standing, condition, and traceability matrices. |
| `backend/app/tests/test_capability_adapters.py` | CREATE | Six adapter mappings, outcome gates, record references, no direct capability bypass. |
| `backend/app/tests/test_supplier_risk_pipeline.py` | CREATE | End-to-end in-process happy path and all business-gated outcomes. |
| `backend/app/tests/test_integration_transactions.py` | CREATE | Capability-local commit/rollback, partial persistence, replay after partial execution. |
| `backend/app/tests/test_integration_architecture.py` | CREATE | Exact file allowlist, dependency direction, no API/startup/schema/dependency changes. |
| `backend/app/tests/test_runtime_contracts.py` | MODIFY | Legacy/new metadata compatibility and deterministic rejection. |
| `backend/app/tests/test_runtime_invocation.py` | MODIFY | Version admission and safe diagnostics. |
| `backend/app/tests/test_runtime_orchestration.py` | MODIFY | AuthorityContext pass-through and business-gated successful termination. |
| `backend/app/tests/test_runtime_execution_state.py` | MODIFY | Business-gated completion versus technical failure. |

No other test artifact is authorized.

## 11. Security boundary

AuthorityContext is accepted only from the trusted invocation boundary, is immutable during execution, and is never sourced from opaque payload claims. Adapters validate required scopes/roles and evidence references without logging credentials, tokens, or sensitive authority details. Authentication, authorization-policy issuance, credential storage, and tenant administration remain outside CDD-011.

## 12. Failure, replay, and observability

- A business gate produces a successful terminal execution with a governed non-actionable/indeterminate result and no later capability calls.
- A technical adapter/runtime failure transitions the execution to Failed and preserves earlier committed immutable records.
- Replay uses the CDD-010 process-local idempotency key. Identical replay returns existing state/result and creates no new records.
- Retry after technical failure requires a new Request Identifier; adapters use the request/correlation and prior record references to avoid unsupported semantic reinterpretation.
- Diagnostics use only CIM-001 safe categories/codes and never expose payloads, credentials, or sensitive authority details.

## 13. Acceptance criteria

1. One trusted invocation produces exactly the fixed six-step sequence unless a governed outcome gate terminates it earlier.
2. Every required field has CIM-001 provenance and no caller payload claim becomes authority.
3. Missing/conflicting risk evidence yields pre-ASM `INDETERMINATE` and no Assertion.
4. Only resolved identity/semantics, established Assertion, Institutionalized Knowledge, valid Decision, and governable recommendation advance.
5. The four sourcing statuses, five recommendation values, and five Governance standings are exhaustive and exact.
6. Every produced record/reference and policy trace is returned safely and remains queryable through existing stores.
7. Capability-local transactions and partial-persistence behavior match RFC-014.
8. Legacy CDD-010 invocations remain byte-for-byte semantically compatible; unsupported new metadata is rejected before execution.
9. No operational action, public API, new persistence model, dependency, startup wiring, or distributed guarantee is introduced.
10. Focused tests, full backend tests, lint, format, strict typing, architecture release verification, changed-file authorization, secret scan, and `git diff --check` pass.

## 14. Rollback and migration

No database migration is authorized. Rollback is code-only: revert the CDD-011 implementation commit and remove the integration package/runtime additions through a governed pull request. Existing immutable capability records created before rollback remain valid historical records. No destructive data rollback or compensation is permitted.

## 15. Architecture drift checklist

- No new business entity.
- No canonical entity or attribute modification.
- Only the two already-approved CVR-001 vocabulary values are used.
- No relationship beyond `HAS_ACTIVE_RISK_CONDITION` is introduced.
- No RFC/BCS semantics are overridden.
- No architecture layer is bypassed.
- No technology, persistence model, product surface, or dependency is introduced.
- Every implementation and test path is exhaustively authorized above; everything else is prohibited.

## 16. Gate

This draft is ready for architecture review only. No production or test implementation may begin until this exact draft is explicitly approved against a verified remote-main commit.
