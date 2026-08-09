# CDD-010 — Architecture Clarification Report

Status: RESOLVED — APPROVED FOR CDD-010

Scope: Invocation replay response only

Architecture reviewed: EIC-001 v1.2, ESM-001 v1.2, PAD-001 v1.4, Baseline Record v1.3, and CDD-010 Draft v1.2

## 1. Approved scope decision

The following CDD-010 runtime-shell constraints are consistent with current architecture and require no architecture change:

- six ordered injected internal capability-step ports representing ERM → SRM → ASM → KRM → DRM → GRM;
- neutral internal step input/output envelopes containing only governed runtime metadata and opaque payload bytes;
- no production capability adapters, semantic handoff mappings, domain translation, or claim of complete production integration;
- process-local atomic first admission keyed by `(protocol_version, request_identifier)`;
- identical payload replay starts no work;
- different-payload replay starts no work;
- retry after Failed requires a new Request Identifier;
- no persistent or distributed idempotency guarantee.

These are runtime-shell implementation constraints within EIC/EOM/ESM boundaries and introduce no business semantics, canonical entity, relationship, attribute, persistence structure, or technology.

CDD-010 implements Option A: a runtime orchestration shell. It coordinates six injected internal capability-step ports and does not implement or claim production integration of ERM, SRM, ASM, KRM, DRM, or GRM.

Production capability adapters, capability-specific contracts, and semantic handoff mappings are explicitly deferred to a future governed work order.

## 2. Generic capability-step contract

`CapabilityStepPort` is an internal runtime-shell contract. Exactly six instances are injected at shell construction and assigned, in order, to ERM, SRM, ASM, KRM, DRM, and GRM.

`CapabilityStepInput` contains only Protocol Version, Correlation Identifier, Request Identifier, Session Identifier, Execution Identifier, and Opaque Payload.

`CapabilityStepOutput` contains exactly the same runtime metadata and an Opaque Payload. Every step must preserve the metadata exactly. The shell passes the returned opaque payload to the next step without parsing, validating, translating, enriching, mapping, or interpreting it.

The step-role names govern order only. They do not create external capability contracts or authorize adapters to existing capability services.

## 3. Sequencing and failure behavior

- The shell invokes exactly six ports sequentially in the frozen EOM order.
- A step is invoked only after the preceding step returns successfully.
- Each step is attempted once. CDD-010 defines no automatic internal retry policy; EOM retains retry authority, but a retry strategy requires a later governed work order.
- If a step raises the shell's internal `CapabilityStepError`, remaining steps are not invoked, the execution transitions from Executing to Failed, and no partial-capability state is exposed.
- If all six steps return successfully, the execution transitions from Executing to Completed.
- Compensation, rollback of capability effects, partial completion state, alternate order, and capability skipping are not authorized.

## 4. Idempotency and concurrent admission

- The idempotency key is exactly `(protocol_version, request_identifier)`.
- First admission is an atomic process-local create-if-absent operation.
- Concurrent identical admissions produce exactly one execution and one Execution Identifier.
- Same key and byte-identical opaque payload returns the existing Execution Identifier and current ESM execution state and starts no work.
- Same key and different opaque payload returns an `Idempotency Conflict` result, creates no Execution Identifier, and starts no work.
- Replay while Accepted or Executing returns the existing identifier and active state.
- Replay after Completed or Failed returns the existing identifier and terminal state.
- Retry after Failed requires a new Request Identifier and therefore a new Execution Identifier.
- These guarantees apply only within one runtime process. Restart, multiple processes, multiple workers, multiple hosts, persistence, and distributed coordination are outside scope.

For CDD-010, `Idempotency Conflict` is an authorized invocation-rejection result, not a new EIC top-level category and not a PAD product protocol. The response carries EIC `Invocation Rejection` with the governed reason `Idempotency Conflict`.

The CDD-010 shell replay result may include the already-governed ESM current state together with the existing Execution Identifier. This is an in-process shell contract only. It does not modify PAC-002 or PAC-006, create a product transport, or authorize an Engine Access Facade.

## 5. Resolution of prior ambiguity

The architecture authority approved the runtime-shell scope and the idempotency rules in this report. The prior replay-state and rejection-representation ambiguities are closed for the in-process CDD-010 shell. No EIC, ESM, EOM, PAD, BCS, CEO, EAD, Logical Model, Physical Model, persistence, security, or technology authority is modified.

## Drift and modification statement

No frozen architecture artifact, production source file, test file, configuration file, persistence artifact, or external contract implementation was modified. This report authorizes correction of the non-authorizing CDD-010 draft only. Implementation still requires a separate explicit approval after a `READY FOR APPROVAL` gate report.
