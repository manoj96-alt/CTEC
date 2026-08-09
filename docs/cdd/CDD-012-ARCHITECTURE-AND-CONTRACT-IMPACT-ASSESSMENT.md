# CDD-012 — Architecture and Contract-Impact Assessment

Version: 1.0

Status: RESOLVED — BASELINE v1.3

Reviewed remote main: `699709cc87003572e13bf34096d4a2e9518fbb50`

## 1. Outcome

CDD-012 cannot be approved under Architecture Baseline v1.2. Durable execution persistence is a useful bounded capability, but four frozen-authority gaps must be closed before schema or code exists.

## 2. P0 findings

### P0-1 — RFC-014 expressly prohibits the requested structures and recovery

RFC-014 v1.1 §3.4 states that no integration-level persistence table, saga, outbox, compensation record, or distributed transaction is authorized. Section 3.5 states that failed executions are not resumed, retries require a new Request Identifier and Execution Identifier, and durable resumption/process-restart recovery are outside scope. Section 4 prohibits durable orchestration and new persistence structures.

**Minimum remediation:** issue RFC-014 v1.2 or RFC-015 with a narrow durable-execution policy for the CDD-011 supplier-risk slice. Preserve capability-local commits, prohibit cross-capability transactions/compensation, and govern recovery identity, replay authorization, uncertain commits, and duplicate-side-effect prevention.

### P0-2 — The frozen Physical Model and PMM-001 authorize no runtime tables

The Physical Model v1.3 contains only the registered canonical/capability structures. PMM-001 assigns every currently persisted table one role and says new runtime writers/structures require governance. CDD-012 would require six non-canonical infrastructure tables or an approved equivalent.

**Minimum remediation:** issue a governed Physical Model clarification/version and PMM-001 v1.1 assigning each runtime table the `immutable source record` or `externally determined currentness projection` role as appropriate. Explicitly state that the structures are implementation metadata and not CEO entities or canonical outcome projections. Register exact columns, constraints, indexes, ownership, and permitted writes.

### P0-3 — Replay identity and ESM terminality are unresolved

The requested replay-from-stage behavior conflicts with the current rule that `Failed` is terminal and retry uses a new request/execution identity. Reusing an Execution Identifier could violate terminality; creating a new identifier could violate the existing idempotency key unless a governed attempt/link contract exists.

**Minimum remediation:** govern one model explicitly:

- linked recovery attempt with a new Execution Identifier and immutable predecessor/root references; or
- same execution with a separately governed non-terminal recoverable state/attempt history.

The authority must define idempotency, terminality, authorization, maximum attempts, current attempt determination, and final-result uniqueness. CDD-012 does not select a model.

### P0-4 — Security and retention authority is absent

Durable replay needs enough trusted input/handoff material to reproduce execution. Existing authorities prohibit leaking opaque payload, AuthorityContext, evidence contents, and narratives, but do not define encryption, data classification, key ownership, retention, deletion, legal hold, or authorization to replay historical authority.

**Minimum remediation:** approve a bounded runtime-data security and retention contract defining protected fields versus hashes/references, encryption requirements, key authority, tenant isolation, replay authorization, audit access, retention duration, deletion/legal-hold behavior, and breach-safe diagnostics. No indefinite-retention or plaintext-storage default may be inferred.

## 3. P1 findings

### P1-1 — Atomic capability record plus checkpoint requires a shared persistence contract

CDD-011 adapters currently call capability persistence operations that own and commit their own sessions. A later checkpoint write cannot prove exactly-once behavior if it uses a different transaction.

**Required contract impact:** authorize a capability transaction/checkpoint port that writes the immutable capability record, required evidence/reference rows, stage checkpoint, outbound handoff, and produced references in one database transaction. Existing domain services and business policies remain unchanged.

### P1-2 — Current CDD-010 stores are concrete and process-local

`InvocationAdmissionService` depends on `InMemoryExecutionStore`; `CognitiveEngineRuntime` constructs the store internally and holds trusted-control fingerprints/final-result overlays in memory.

**Required implementation impact:** introduce injected store/recovery ports while preserving the in-memory implementation and all CDD-010 compatibility tests. This is an implementation refactor only after P0 closure; it must not alter runtime semantics.

### P1-3 — Observability lacks a durable audit contract

RFC-014 defines safe diagnostic categories but not durable audit event fields, retention, or access control.

**Required contract impact:** the prerequisite authority must define the exact safe audit fields and prohibit payloads, secrets, evidence contents, and narratives.

## 4. Proposed physical roles

| Proposed structure | PMM role | Reason |
|---|---|---|
| execution admissions | Immutable source record | One governed admission identity/fingerprint. |
| execution transitions | Immutable source record | Append-only ESM transition history. |
| execution stages | Immutable source record with externally derived current-attempt projection if needed | Append-only attempts/checkpoints; currentness derived. |
| execution handoffs | Immutable source record | Protected opaque content/reference and integrity hash. |
| execution artifact references | Immutable source record | Append-only references; no duplicated business meaning. |
| execution results | Immutable source record | Exactly one terminal result per execution. |

No proposed structure is a canonical outcome projection. Exact names and roles remain proposals until frozen.

## 5. Contract compatibility

- CDD-010: additive injection/persistence only; protocol v1 and v2 admission meaning must remain compatible.
- CDD-011: business rules, adapter order, gates, recommendations, standing, and AuthorityContext semantics remain unchanged.
- RFC-011: execution histories should be append-only; any current snapshot/cache must be externally derived and rebuildable.
- RFC-014: requires normative amendment because current text explicitly excludes the work.
- Physical Model/PMM: requires normative extension because the structures do not exist.
- BCS/CEO/EAD/Logical Model: no business-semantic change is proposed.
- PAD/API: no contract impact; product transport remains out of scope.

## 6. Minimum governance package

1. Durable execution/recovery RFC clarification (RFC-014 v1.2 or RFC-015).
2. Runtime persistence physical model authority with exact DDL semantics.
3. PMM-001 v1.1 role mapping for every new table.
4. ESM/EIC clarification only if the chosen recovery identity changes terminality or invocation identity.
5. Runtime-data security, retention, and replay-authorization specification.
6. Registry, dependency matrix, checksums, manifests, consistency/drift/readiness reports, and baseline release decision.
7. Revised CDD-012 and replacement gate report.

## 7. Recommendation

**RESOLVED.** Baseline v1.3 publishes RFC-014 v1.2, EOM-001 v1.4, PMM-001 v1.1, Physical Model v1.4, and RSP-001 v1.0.
