# CDD-010 — Cognitive Engine Runtime

Version: 1.3 DRAFT

CDD Gate: ARCHITECTURE REVIEW — READY FOR APPROVAL

Implementation State: NOT STARTED  
Architecture Baseline: v1.1  
Mandatory Template: CDD Template v2.2  
Effective Review Date: 2026-08-08

This is a non-authorizing draft. It supersedes Draft v1.2 after resolution of the runtime-shell Architecture Clarification Report. Do not implement, create production artifacts, or modify any file listed in the authorization sections until explicit implementation approval is recorded.

## 1. Implementation objective and business outcome

Implement the technology-neutral Cognitive Engine runtime shell defined by EIC-001, coordinate six ordered and injected capability-step ports in the fixed EOM-001 sequence, and expose execution state exactly as defined by ESM-001.

The outcome is an orchestration foundation that admits an opaque invocation, coordinates injected step ports representing ERM → SRM → ASM → KRM → DRM → GRM, and reports process-local execution state without exposing or interpreting capability semantics.

CDD-010 does not deliver an externally callable, fully integrated CTEC capability pipeline. It introduces no business semantics, creates no business artifact, implements no production capability adapter, and performs no domain-specific input or output translation. Production adapters and semantic handoff mappings require a future governed work order.

## 2. Gate history

| Gate | Date | Result | Evidence |
|---|---|---|---|
| DRAFT v1.0 | 2026-08-08 | Superseded before approval | Initial draft contained a superseded Baseline Record reference and used TAS-001 in one authorization source. It never reached APPROVED or IMPLEMENTATION. |
| DRAFT v1.1 | 2026-08-08 | Superseded after blocked review | Corrected release authorities but left production capability handoffs and concurrent idempotency underspecified. The accepted preimplementation report classified one P0 and one P1 finding. |
| DRAFT v1.2 | 2026-08-08 | Superseded after clarification | Narrowed delivery to a runtime shell but retained two unresolved replay-response questions. |
| DRAFT v1.3 | 2026-08-08 | Current draft | Incorporates the approved runtime-shell, sequencing, failure, replay, conflict, and process-local concurrency clarification. |
| P0 prerequisite verification | 2026-08-08 | Closed, remote evidence verified | Baseline release `834582b` and CDD-009 merge/evidence commits `16b96a8` / `0211634` are present on remote `main`; CDD-009 is registered as IMPLEMENTED / FROZEN. Closure does not approve this draft. |
| ARCHITECTURE REVIEW | 2026-08-08 | Ready for approval | Prerequisites, exhaustive authorization, runtime-shell scope, contract, idempotency, failure, testability, security, persistence, configuration, rollback, traceability, and drift review pass with zero P0/P1 findings. |
| APPROVED | — | Not reached | Requires closure of every stop condition and an explicit approval record. |
| IMPLEMENTATION | — | Prohibited | No code or product artifact may be created or modified under CDD-010 before approval. |

## 3. Authoritative dependencies

- Enterprise Constitution v1.0
- EAH-001 v1.4
- RFC-010 v1.0
- RFC-011 v1.0
- RFC-013 v1.1
- CDS-001 v1.3
- CDD Template v2.2
- CTEC Architecture Baseline Record v1.3 — `architecture/released/v1.1/BASELINE-RECORD-v1.3_FROZEN.md`
- ACR-001 v1.2 — Architecture Consistency Report — `architecture/released/v1.1/ARCHITECTURE-CONSISTENCY-REPORT-v1.2_FROZEN.md`
- ADR-001 v1.2 — Architecture Drift Report — `architecture/released/v1.1/ARCHITECTURE-DRIFT-REPORT-v1.2_FROZEN.md`
- RRR-001 v1.2 — Release Readiness Report — `architecture/released/v1.1/RELEASE-READINESS-REPORT-v1.2_FROZEN.md`
- RND-001 v1.0 — Architecture Registry Normalization Decision — `architecture/released/v1.1/RND-001_Architecture_Registry_Normalization_v1.0_FROZEN.md`
- EIC-001 v1.2
- EOM-001 v1.2
- ESM-001 v1.2
- PAD-001 v1.4
- ERM-001 v2.2
- SRM-001 v2.2
- ASM-001 v2.2
- AEM-001 v1.1
- KRM-001 v1.4
- DRM-001 v1.2
- GEM-001 v1.1
- GRM-001 v1.2
- CAM-001 v1.1
- Architecture Dependency Matrix v1.1

TAS-001 is `DEVELOPMENT + NO + NON-AUTHORITATIVE`. It is not a governing dependency, constraint, or authorization source for CDD-010. The Logical Model and EAD-001 are likewise Development and non-binding. None of these artifacts may authorize implementation. This draft does not rely on them and does not list them as informational dependencies.

## 4. In scope

- One in-process Cognitive Engine invocation boundary.
- Invocation receipt, structural validation, admission, rejection, and handoff.
- Opaque request and response contracts containing only EIC-authorized protocol and correlation fields.
- Six injected internal `CapabilityStepPort` instances representing ERM, SRM, ASM, KRM, DRM, and GRM.
- Deterministic invocation of those ports in the EOM-defined order.
- A neutral internal `CapabilityStepInput` and `CapabilityStepOutput` envelope carrying only governed runtime identifiers, Protocol Version, and opaque payload bytes.
- Pass-through of opaque step output to the next injected step without inspection, semantic interpretation, or domain transformation by the runtime shell.
- ESM states: Accepted, Executing, Completed, and Failed.
- Immutable execution transition history held within the runtime process.
- EOM-owned internal retry within one execution.
- External retry as a new invocation and new Execution Identifier.
- Process-local PAD idempotency keyed by `(protocol_version, request_identifier)` with atomic first admission.
- Identical active or terminal replay returning the existing Execution Identifier and current ESM state without starting new work.
- Different-payload replay for the same idempotency key returning EIC `Invocation Rejection` with reason `Idempotency Conflict`, creating no Execution Identifier, and starting no work.
- Retry after Failed requiring a new Request Identifier and therefore a new Execution Identifier.
- Read-only execution-state observation through an opaque execution reference.

## 5. Out of scope

- New or modified business semantics, BCS artifacts, CEO entities, canonical attributes, or canonical relationships.
- Direct consumer access to any cognitive capability.
- Capability skipping, alternate ordering, cancellation, partial-completion state, or compensation API.
- Product REST APIs, UI, upload workflow, authentication, authorization, or session management.
- Database tables, ORM models, migrations, durable queues, schedulers, message brokers, distributed execution, or runtime-state persistence.
- Changes to existing cognitive-capability behavior.
- Production adapters to existing ERM, SRM, ASM, KRM, DRM, or GRM services.
- Domain-specific payload parsing, validation, translation, mapping, enrichment, or result interpretation.
- Semantic handoff mapping between capability-specific inputs and outputs.
- Claims of complete production capability integration or end-to-end enterprise cognition.
- Cross-process, distributed, or durable idempotency and execution coordination.
- New third-party dependencies or technology.

## 6. Authorized Business Artifacts

None authorized.

## 7. Authorized External Contracts

| Exact artifact name | Repository path | Permitted action | Governing architecture authority | Implementation purpose | Prohibited or excluded changes | Required validation evidence |
|---|---|---|---|---|---|---|
| `CognitiveEngineInvocationPort.invoke(InvocationRequest) -> InvocationResponse` | `backend/app/runtime/contracts.py` | CREATE | EIC-001 v1.2; EOM-001 v1.2; PAD-001 v1.4; CDD-010 Architecture Clarification | Provide the single opaque engine invocation boundary, including the governed process-local replay and conflict results. | No REST route, transport binding, product protocol, business semantics, capability-specific method, or direct capability exposure. | Contract-field, replay-state, conflict, architecture-boundary, and invocation-sequence tests. |
| `ExecutionObservationPort.get_execution(ExecutionIdentifier) -> ExecutionSnapshot` | `backend/app/runtime/contracts.py` | CREATE | EIC-001 v1.2; ESM-001 v1.2; PAD-001 v1.4 | Permit read-only observation of an authorized execution reference. | No mutation, cancellation, business payload exposure, product session ownership, or additional execution state. | Contract tests; ESM transition tests; external-surface allowlist review. |

No other external contract is authorized.

## 8. Authorized Persistence Artifacts

None authorized.

Execution state and transition history are non-durable runtime-process implementation data. No table, ORM model, migration, repository, database schema, index, currentness projection, history projection, or durable store is authorized.

Idempotency keys, payload fingerprints, execution snapshots, and atomic-admission coordination are process-local implementation state only. They must not be persisted or represented as business lifecycle state.

## 9. Authorized Configuration Artifacts

None authorized.

No configuration file, schema, loader, validator, environment key, policy configuration, or runtime default may be created or modified under this CDD.

## 10. Authorized Test Artifacts

| Exact artifact name | Repository path | Permitted action | Governing architecture authority | Implementation purpose | Prohibited or excluded changes | Required validation evidence |
|---|---|---|---|---|---|---|
| Runtime contract tests | `backend/app/tests/test_runtime_contracts.py` | CREATE | CDD-010; EIC-001 v1.2; PAD-001 v1.4 | Verify the two authorized external contracts and their opaque fields. | No production definitions, transport routes, or new contract fields. | Passing pytest result and contract-field allowlist. |
| Runtime invocation tests | `backend/app/tests/test_runtime_invocation.py` | CREATE | CDD-010; EIC-001 v1.2; PAD-001 v1.4 | Verify admission, rejection, identifier ownership, atomic concurrent admission, identical active/terminal replay, conflicting replay, and retry-after-failure identity. | No direct capability invocation, distributed guarantee, or unapproved state. | Passing pytest result, concurrent-admission trace, and replay/conflict matrix. |
| Runtime orchestration tests | `backend/app/tests/test_runtime_orchestration.py` | CREATE | CDD-010; EOM-001 v1.2 | Verify six injected ports execute in the complete deterministic order, opaque payloads pass without runtime interpretation, and retry ownership remains internal. | No production adapter, alternate order, bypass, domain transformation, or business decision. | Passing pytest result, ordered call trace, and opaque-envelope equality assertions. |
| Runtime execution-state tests | `backend/app/tests/test_runtime_execution_state.py` | CREATE | CDD-010; ESM-001 v1.2; RFC-011 v1.0 | Verify authorized transitions, immutable history, terminality, and retry identifiers. | No mutable business lifecycle or unapproved state. | Passing pytest result and state-transition matrix. |
| Runtime architecture tests | `backend/app/tests/test_runtime_architecture.py` | CREATE | CDS-001 v1.3; CDD Template v2.2; CDD-010 | Enforce dependency direction, file allowlist, no persistence, and no direct consumer access. | No relaxation of architecture checks or creation of production artifacts. | Passing pytest result and changed-file allowlist comparison. |

No other test artifact is authorized.

## 11. Authorized implementation files and components

These internal implementation files are exhaustive. They do not expand the five authorization categories above.

| Exact artifact name | Repository path | Permitted action | Governing architecture authority | Implementation purpose | Prohibited or excluded changes | Required validation evidence |
|---|---|---|---|---|---|---|
| Runtime package marker | `backend/app/runtime/__init__.py` | CREATE | CDD-010 | Define the internal runtime package. | No exported product API or business object. | Import test and file allowlist. |
| Runtime contracts module | `backend/app/runtime/contracts.py` | CREATE | EIC-001 v1.2; ESM-001 v1.2 | Implement only the authorized external ports and opaque contract models. | No unlisted external contract, capability DTO, production adapter, or business field. | Contract and architecture tests. |
| Invocation admission component | `backend/app/runtime/invocation.py` | CREATE | EIC-001 v1.2; PAD-001 v1.4 | Validate, atomically admit, reject, and hand off an invocation using the process-local idempotency rules in Section 12. | No orchestration, business interpretation, authentication, persistence, or distributed guarantee. | Invocation, concurrency, replay, and conflict tests. |
| Orchestration component and internal capability-step contracts | `backend/app/runtime/orchestration.py` | CREATE | EOM-001 v1.2; CDD-010 | Define `CapabilityStepPort`, `CapabilityStepInput`, and `CapabilityStepOutput`; coordinate exactly six injected ports in the governed order. | No production adapters, domain DTOs, semantic translation, alternate order, bypass, policy decision, or external API. | Orchestration tests, exact port-order trace, opaque-envelope equality assertions, and architecture import check. |
| Execution-state component | `backend/app/runtime/execution_state.py` | CREATE | ESM-001 v1.2; RFC-011 v1.0 | Enforce authorized states, transitions, and immutable transition history. | No business lifecycle state or extra runtime state. | State-transition tests. |
| In-memory execution store | `backend/app/runtime/execution_store.py` | CREATE | ESM-001 v1.2; CDD-010 | Hold non-durable execution snapshots and append-only transitions within one process. | No database, filesystem persistence, durable queue, or canonical outcome storage. | Persistence-prohibition architecture test. |
| Cognitive Engine runtime facade | `backend/app/runtime/engine.py` | CREATE | EIC-001 v1.2; EOM-001 v1.2; ESM-001 v1.2 | Compose admission, the injected runtime-shell orchestrator, and process-local state ownership behind one facade. | No product route, business semantics, production capability integration, or direct capability exposure. | Runtime-shell integration tests. |
| Developer documentation | `README.md` | MODIFY | CDD-010 | Document internal runtime setup and validation commands. | No business-semantic or architecture-authority changes. | Documentation review against CDD-010. |

No composition-root, application-startup, API, existing capability, project-metadata, dependency, configuration, or persistence modification is authorized. Construction of the runtime shell with six caller-supplied ports occurs through the authorized runtime facade and does not register production capability adapters. No other source, documentation, or repository file is authorized for implementation.

## 12. Process-local idempotency and concurrency

The idempotency key is exactly `(protocol_version, request_identifier)`.

- First admission is atomic within one runtime process. Concurrent callers for the same key must observe one winning admission, one Execution Identifier, and one execution.
- The runtime stores an exact fingerprint of the opaque payload bytes without parsing or interpreting the payload.
- A replay with the same key and identical opaque payload returns the existing Execution Identifier and current ESM state and starts no work, whether the execution is Accepted, Executing, Completed, or Failed.
- A replay with the same key and different opaque payload returns EIC `Invocation Rejection` with reason `Idempotency Conflict`, returns no new Execution Identifier, and starts no work.
- Retry after Failed requires a new Request Identifier and therefore a new idempotency key and Execution Identifier.
- Idempotency metadata, atomic admission, execution state, and transition history are process-local. No guarantee survives process restart or coordinates across processes, hosts, or workers.

These rules govern the in-process CDD-010 shell contract only. They do not modify PAD, create a product transport, or authorize an Engine Access Facade.

## 13. Internal capability-step envelope

`CapabilityStepInput` contains only:

- Protocol Version
- Correlation Identifier
- Request Identifier
- Session Identifier
- Execution Identifier
- Opaque Payload

`CapabilityStepOutput` contains the same governed runtime metadata and an Opaque Payload. A step output must preserve all runtime metadata exactly. The orchestrator passes the opaque output payload to the next injected step without reading, validating, mapping, enriching, or interpreting it.

Exactly six `CapabilityStepPort` instances are required at shell construction and are assigned to the fixed roles ERM, SRM, ASM, KRM, DRM, and GRM. The roles determine order only. They do not expose the ports externally and do not authorize production adapters or capability-specific contracts.

Each port is invoked once and only after its predecessor succeeds. `CapabilityStepError` is an internal shell failure: remaining ports are not invoked, the execution transitions to Failed, and no partial-capability state is exposed. All six successful returns transition the execution to Completed. No automatic internal retry policy, compensation, alternate order, or partial-completion state is authorized.

## 14. Security and authorization boundary

Authentication and authorization are owned outside the Cognitive Engine. CDD-010 accepts only an invocation already authorized by its caller. The runtime must not authenticate users, grant access, interpret identity, or create an authorization policy.

Opaque identifiers carry no business meaning. Logs must not emit opaque payload contents or secrets.

## 15. Acceptance criteria and testing scope

Implementation approval will require evidence that:

1. every invocation enters through exactly one boundary;
2. rejected invocations create no Execution Identifier;
3. accepted invocations receive one engine-owned Execution Identifier;
4. exactly six injected capability-step ports execute as ERM → SRM → ASM → KRM → DRM → GRM with no bypass;
5. the runtime shell never imports or constructs existing capability services and never interprets or transforms opaque payload semantics;
6. only ESM-authorized transitions occur;
7. terminal states never transition;
8. internal retry retains the Execution Identifier;
9. external retry creates a new Execution Identifier;
10. atomic concurrent admission for one idempotency key creates exactly one execution;
11. identical active or terminal replay returns the existing Execution Identifier and current ESM state and starts no work;
12. different-payload replay returns EIC Invocation Rejection with Idempotency Conflict reason and starts no work;
13. retry after Failed requires a new Request Identifier and Execution Identifier;
14. runtime consumers cannot invoke individual capabilities;
15. no persistence, distributed guarantee, production adapter, semantic handoff, or external product API is introduced;
16. architecture tests enforce imports, dependency direction, and the authorized file allowlist;
17. unit and runtime-shell integration tests pass with repository coverage at or above 80%; and
18. architecture manifest verification remains successful.

## 16. Architecture-drift checklist

- No business entity introduced.
- No existing entity modified.
- No canonical relationship changed.
- No canonical attribute invented.
- No RFC violated.
- No architecture layer bypassed.
- No technology or dependency introduced.
- No direct capability invocation exposed.
- No product contract duplicated from PAD.
- No persistence artifact introduced.
- No production capability adapter or domain-specific handoff introduced.
- No claim of complete production capability integration introduced.
- No file or artifact outside the exhaustive authorization records created, modified, or deleted.

Any affirmative answer stops implementation.

## 17. Traceability

| Requirement | Authority | Authorized implementation | Authorized tests |
|---|---|---|---|
| Single opaque invocation boundary | EIC-001 v1.2 | `contracts.py`, `invocation.py`, `engine.py` | `test_runtime_contracts.py`, `test_runtime_invocation.py` |
| Six ordered injected capability-step ports | EOM-001 v1.2 | `orchestration.py`, `engine.py` | `test_runtime_orchestration.py`, `test_runtime_architecture.py` |
| Opaque internal step envelopes | EIC-001 v1.2; EOM-001 v1.2; CDD-010 v1.2 | `orchestration.py` | `test_runtime_orchestration.py`, `test_runtime_architecture.py` |
| Accepted, Executing, Completed, Failed | ESM-001 v1.2 | `execution_state.py`, `execution_store.py`, `engine.py` | `test_runtime_execution_state.py` |
| Atomic process-local replay and conflict rules | PAD-001 v1.4; CDD-010 Architecture Clarification; CDD-010 v1.3 | `invocation.py`, `execution_store.py`, `engine.py` | `test_runtime_invocation.py` |
| No persistence, adapters, semantic mappings, or direct capability access | Baseline Record v1.3; EIC/EOM/ESM v1.2; CDD-010 v1.3 | Entire authorized runtime package | `test_runtime_architecture.py` |

## 18. Implementation completion evidence

The completion package must contain:

- changed-file allowlist comparison;
- unit, integration, architecture, state-transition, retry, replay, and security-boundary test results;
- coverage report;
- dependency diff proving no added dependency;
- architecture drift report;
- runtime-shell sequence trace proving the six injected port roles and order;
- concurrent-admission and replay/conflict matrix;
- proof that runtime modules do not import existing capability services;
- rollback rehearsal result; and
- CDD-010 implementation review record.

## 19. Rollback and migration expectations

None authorized for persistence or data migration.

Implementation rollback consists only of reverting the approved CDD-010 runtime-shell implementation commit. No composition-root integration is authorized. Because execution state is in memory and non-durable, rollback must not transform or delete canonical or business data.

No compatibility shim, dual-write path, schema rollback, or persisted-state conversion is authorized.

## 20. Stop conditions

Before any transition to APPROVED or IMPLEMENTATION, Codex must verify both P0 closure conditions against remote `main`. Local branches, local commits, local working-tree files, or unpushed evidence are insufficient:

- the remediated Architecture Baseline v1.1 release is committed and pushed to remote `main`, including Baseline Record v1.3 and its mandatory release authorities; and
- CDD-009 is reconciled, tested, merged to remote `main`, and registered with its implementation evidence.

Remote prerequisite evidence was observed while preparing Draft v1.1, but it must be reverified at the approval gate. Implementation must also not begin until:

- the changed-file plan is verified against every v2.2 authorization record; and
- CDD-010 receives an explicit APPROVED gate entry.

Any ambiguity requiring new business semantics, ontology, canonical structure, persistence, external API, security policy, or technology requires an Architecture Clarification Report.

While this document remains DRAFT or ARCHITECTURE REVIEW — BLOCKED, Codex shall not implement CDD-010, create production artifacts, or modify any authorized implementation file.

The Architecture Clarification Report is resolved. The remaining gate is explicit implementation approval; `READY FOR APPROVAL` is not approval.
