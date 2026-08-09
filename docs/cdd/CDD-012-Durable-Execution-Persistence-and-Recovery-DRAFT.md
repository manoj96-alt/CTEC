# CDD-012 — Durable Execution Persistence and Recovery

Version: 1.0 DRAFT

Status: APPROVED FOR IMPLEMENTATION

Implementation authorization: GRANTED — CDD-012 governance decision

Architecture Baseline: v1.3

Mandatory template: CDD Template v2.2

## 1. Objective and bounded outcome

Persist and recover the existing CDD-010/CDD-011 supplier-risk execution without redesigning runtime state, capability order, handoff semantics, or supplier-risk policy. The bounded outcome is an application-neutral durable execution record that can survive process restart, resume only from an authorized committed checkpoint, suppress duplicate capability side effects, and return the existing governed final result.

The work order does not authorize implementation until the P0 authorities in the accompanying impact assessment and gate report are released.

## 2. Governing authorities

- Architecture Baseline v1.2 and Architecture Registry v1.2.
- Enterprise Constitution v1.0; EAH-001 v1.5; RFC-010 v1.0; RFC-011 v1.0; RFC-013 v1.2; RFC-014 v1.1.
- CIM-001 v1.1; CVR-001 v1.0; CAM-001 v1.2; PMM-001 v1.0.
- EIC-001 v1.3; EOM-001 v1.3; ESM-001 v1.3; PAD-001 v1.5.
- CDD-010 v1.3 FROZEN / IMPLEMENTED; CDD-011 v1.0 IMPLEMENTED / VERIFIED / FROZEN.
- Frozen ERM, SRM, ASM, AEM, KRM, DRM, GEM, and GRM versions registered in Baseline v1.2.
- CDS-001 v1.3 and CDD Template v2.2.

TAS-001, the Logical Model, and EAD-001 remain non-authoritative Development artifacts and grant no authority.

## 3. Required prerequisite authorities

Before approval, a governed clarification release must:

1. supersede RFC-014 §§3.4–3.5 and §4 only for durable execution persistence and recovery of the CDD-011 supplier-risk slice;
2. govern durable admission, checkpoint, replay, recovery, failure, and side-effect suppression semantics without changing CDD-010 states or CDD-011 business rules;
3. authorize and classify the exact non-canonical runtime persistence structures in the Physical Model and PMM-001;
4. govern persistence of opaque handoff content, AuthorityContext-derived metadata, encryption/data classification, retention, deletion/legal-hold behavior, and safe diagnostics; and
5. resolve whether replay resumes the same Execution Identifier or creates a linked recovery attempt while preserving ESM terminality and the existing idempotency key.

Until those authorities are current, frozen, and registered, every implementation path below remains prohibited.

## 4. In scope after prerequisite closure

- PostgreSQL-backed execution admission and idempotency.
- Durable execution transition history and externally derived current snapshot.
- Exactly six durable stage checkpoints in ERM → SRM → ASM → KRM → DRM → GRM order.
- Durable opaque handoff storage or governed handoff references, with integrity protection.
- Durable references to evidence, provenance, capability records, the Decision record, and the final Governance result; no duplicated business meaning.
- Capability-local atomic commit of the capability record, stage checkpoint, outbound handoff, and produced-record references.
- Recovery after process interruption from the last committed stage only.
- Deterministic duplicate, conflict, active replay, terminal replay, retryable failure, and terminal failure behavior.
- Optimistic concurrency through a governed monotonic revision or an equivalent database-enforced compare-and-swap mechanism.
- Safe structured audit and observability records.
- Migration and rollback limited to the authorized runtime persistence structures.

## 5. Out of scope

- New or changed supplier-risk, identity, semantic, assertion, knowledge, decision, or governance business rules.
- New canonical entities, relationships, attributes, or vocabulary.
- Reordering, bypassing, or reimplementing ERM through GRM.
- External API, UI, product transport, deployment, queue, broker, distributed scheduler, or universal workflow platform.
- Cross-capability distributed transactions, compensation, deletion, or mutation of committed immutable capability records.
- Direct operational supplier, sourcing, contractual, or financial action.
- Authentication provider, credential storage, key-management implementation, or tenant administration.
- Canonical outcome-table writes.

## 6. Persisted record contracts requiring authority

These are proposed non-canonical infrastructure records, not new business entities. Exact columns, types, nullability, encryption, indexes, and retention remain prohibited until the prerequisite physical/security authorities approve them.

| Record | Required governed content | Lifecycle |
|---|---|---|
| Execution Admission Record | Execution/reference identifiers; protocol, integration-contract, request, correlation, and session identifiers; request classification; opaque-payload and trusted-control fingerprints; admission timestamp; safe disposition; concurrency revision. | Created atomically once per `(protocol_version, request_identifier)`; immutable identity and fingerprints. |
| Execution Transition Record | Execution identifier; ordered sequence; from/to ESM states; trusted transition timestamp; safe reason/error code; writer revision. | Append-only. Current state is derived from ordered transitions. |
| Execution Stage Checkpoint | Execution identifier; governed stage and ordinal; attempt/reference; started/completed timestamps; checkpoint disposition; input/output handoff references; produced-record references; safe failure classification; concurrency revision. | One committed result per execution/stage; attempts are append-only and never overwrite capability results. |
| Handoff Record | Execution/stage references; integration-contract version; opaque protected content or governed external reference; content hash; creation timestamp; source/target stage. | Immutable after commit; content remains semantically opaque to persistence. |
| Artifact Reference Record | Execution/stage; artifact role (`evidence`, `provenance`, `capability_record`, `decision`, `governance_result`); governed identifier/reference; source capability. | Append-only reference only; no duplicated evidence or business narrative. |
| Final Result Record | Execution identifier; terminal integration disposition; terminal capability; governed recommendation/standing references; actionability; produced-record references; safe result/error code; completion timestamp. | Exactly one terminal result per execution; immutable. |

## 7. Transaction and atomicity requirements

1. Admission uses a database uniqueness constraint on the governed idempotency key and atomic insert-if-absent semantics.
2. Identical duplicate admission returns the existing execution. A conflicting payload or trusted-control fingerprint returns deterministic idempotency conflict and starts no work.
3. Each capability owns one local transaction. Its immutable capability record, evidence/reference rows, completed stage checkpoint, outbound handoff, and artifact references commit together.
4. A technical failure rolls back only the current uncommitted capability transaction. Earlier checkpoints and immutable capability records remain unchanged.
5. Final result creation and the terminal execution transition commit atomically.
6. No cross-capability transaction, compensation, mutation, or deletion is permitted.
7. Every state/stage write requires the expected concurrency revision; stale writers fail deterministically without side effects.

## 8. Recovery, replay, and duplicate-side-effect rules

- Recovery reads the ordered durable transition and stage histories and verifies all hashes/references before selecting a checkpoint.
- A stage is reusable only when its capability record, checkpoint, handoff, and required references committed atomically and pass contract/version validation.
- Recovery never re-invokes a committed stage. It begins at the first stage with no valid committed checkpoint.
- A stage with an uncertain commit outcome is not retried until database reconciliation proves whether the capability record and checkpoint exist.
- Identical replay of an active or terminal execution returns its durable state/result and starts no work.
- Conflicting replay returns idempotency conflict.
- Replay after a retryable technical failure requires explicit replay authorization and the governed recovery identity rule.
- Business-gated completion and terminal business results are never replayed into later capabilities.
- Terminal security, contract-version, integrity, or non-retryable failures cannot resume.
- Database constraints and checkpoint verification are the primary duplicate-side-effect safeguards; application locks alone are insufficient.

The identity of a recovery attempt and the required replay authorization remain P0 decisions; this draft does not choose them.

## 9. Failure classification

| Class | Required behavior |
|---|---|
| Business-gated completion | Durable successful terminal result; never a technical failure and never resumed. |
| Retryable technical failure | Durable safe failure plus last valid checkpoint; eligible only after governed replay authorization. |
| Terminal technical failure | Durable safe failure; no resume. Includes integrity, unsupported contract/version, authority, or non-recoverable persistence violations. |
| Uncertain commit | Quarantine from automatic replay until reconciliation establishes whether the atomic unit committed. |
| Concurrency conflict | No side effect; refresh durable revision and return/re-evaluate under the governed retry rule. |

## 10. Security and AuthorityContext

- AuthorityContext remains immutable trusted control metadata, separate from opaque business payload.
- Persistence may retain only fields or protected bytes explicitly authorized by the prerequisite security contract.
- Credentials, tokens, secrets, evidence contents, source rows, and business narratives must not appear in logs or safe diagnostic records.
- Replay requires a currently valid trusted authority decision for the replay operation and must preserve the original authority/provenance reference; caller payload claims confer no authority.
- Every read/write is tenant/organization scoped and correlation preserving.
- Encryption, key ownership, rotation, data classification, retention, deletion, and legal hold require explicit authority before implementation.

## 11. Retention assumptions

No retention period or purge behavior is authorized today. Until a frozen retention authority exists, CDD-012 may not implement automated deletion, expiry, archival, or legal-hold behavior. Indefinite retention is not silently assumed; this is a P0 gate.

## 12. Migration and rollback

- Use one forward Alembic migration after a governed physical model assigns every new table and column.
- The migration must be additive and preserve all existing canonical and capability data.
- Rollback before first production use may drop only empty CDD-012 runtime tables through the governed downgrade.
- After durable execution records exist, destructive downgrade is prohibited. Rollback disables new durable admission, preserves records read-only, and requires a separately approved data disposition/migration plan.
- No existing migration, canonical table, capability table, or immutable record may be rewritten.

## 13. Authorized Business Artifacts

None authorized.

## 14. Authorized External Contracts

No product-facing external contract is authorized. Subject to prerequisite approval, the following internal contracts may be modified:

| Path | Action | Purpose | Exclusions | Evidence |
|---|---|---|---|---|
| `backend/app/runtime/contracts.py` | MODIFY | Add durable recovery, checkpoint, and safe result-reference contracts authorized by the amended runtime authorities. | No API transport or business payload meaning. | Field allowlists and compatibility tests. |
| `backend/app/runtime/execution_state.py` | READ-ONLY | Preserve the released CDD-010/ESM state machine. If prerequisite governance requires a state change, CDD-012 must be revised and reviewed before implementation. | No ungoverned state or terminality change. | Unchanged-file assertion and state-machine regression matrix. |

## 15. Authorized Implementation Artifacts

| Path | Action | Purpose |
|---|---|---|
| `backend/app/runtime/persistence/__init__.py` | CREATE | Bounded durable-runtime persistence package. |
| `backend/app/runtime/persistence/contracts.py` | CREATE | Repository, transaction, checkpoint, replay-authorization, and clock ports. |
| `backend/app/runtime/persistence/models.py` | CREATE | SQLAlchemy mappings for only the governed runtime tables. |
| `backend/app/runtime/persistence/repository.py` | CREATE | Atomic admission, transition, checkpoint, artifact-reference, result, and reconciliation operations. |
| `backend/app/runtime/recovery.py` | CREATE | Validate checkpoints and select the next governed stage without business interpretation. |
| `backend/app/runtime/execution_store.py` | MODIFY | Preserve the store contract and support injected durable implementation without changing in-memory compatibility. |
| `backend/app/runtime/invocation.py` | MODIFY | Use the store port for atomic durable admission and replay results. |
| `backend/app/runtime/orchestration.py` | MODIFY | Invoke transaction/checkpoint hooks around the existing six ordered ports. |
| `backend/app/runtime/engine.py` | MODIFY | Inject durable store/recovery ports and coordinate authorized recovery; no business rules. |
| `backend/app/integration/dependencies.py` | MODIFY | Inject the shared capability transaction/checkpoint port. |
| `backend/app/integration/adapters/erm.py` | MODIFY | Atomically persist ERM record and checkpoint through the governed port. |
| `backend/app/integration/adapters/srm.py` | MODIFY | Atomically persist SRM record and checkpoint through the governed port. |
| `backend/app/integration/adapters/asm.py` | MODIFY | Atomically persist ASM record and checkpoint through the governed port. |
| `backend/app/integration/adapters/krm.py` | MODIFY | Atomically persist KRM record and checkpoint through the governed port. |
| `backend/app/integration/adapters/drm.py` | MODIFY | Atomically persist DRM record, traceability references, and checkpoint. |
| `backend/app/integration/adapters/grm.py` | MODIFY | Atomically persist GRM record, final result, and checkpoint. |
| `backend/app/infrastructure/persistence/models/__init__.py` | MODIFY | Register only approved runtime ORM mappings. |
| `README.md` | MODIFY | Document application-neutral durable runtime construction, recovery, and validation. |

All domain models/services, business policies, API/startup/composition-root files, dependencies, and deployment files are READ-ONLY.

## 16. Authorized Persistence Artifacts

| Path | Action | Purpose |
|---|---|---|
| `backend/app/infrastructure/persistence/migrations/versions/0008_durable_execution.py` | CREATE | Add only the governed runtime execution tables, constraints, indexes, and downgrade safeguards. |

No other migration, canonical SQL, ORM model, repository, schema, or database configuration is authorized. This authorization is inactive until the Physical Model and PMM-001 assign exact structures and roles.

## 17. Authorized Configuration Artifacts

None authorized. Database session factories, clocks, replay-authority validators, retention policy, and encryption providers must be injected. If configuration is required, the CDD must be revised and reviewed before implementation.

## 18. Authorized Test Artifacts

| Path | Action | Required coverage |
|---|---|---|
| `backend/app/tests/test_execution_persistence_contracts.py` | CREATE | Exact record/field allowlists, immutability, UTC, fingerprints, safe diagnostics. |
| `backend/app/tests/test_durable_execution_store.py` | CREATE | Admission, transitions, checkpoints, final results, artifact references. |
| `backend/app/tests/test_execution_recovery.py` | CREATE | Restart, checkpoint validation, next-stage selection, uncertain commit. |
| `backend/app/tests/test_execution_replay.py` | CREATE | Replay authorization, active/terminal/failed behavior, conflict handling. |
| `backend/app/tests/test_execution_concurrency.py` | CREATE | Concurrent first admission, stale revision, duplicate-stage suppression. |
| `backend/app/tests/test_execution_persistence_integration.py` | CREATE | PostgreSQL migration, transactions, partial failure, recovery, rollback protection. |
| `backend/app/tests/test_execution_persistence_architecture.py` | CREATE | Exact changed-file and dependency boundaries; no API/UI/deployment/business-rule drift. |
| `backend/app/tests/test_runtime_invocation.py` | MODIFY | Durable admission and legacy behavior regression. |
| `backend/app/tests/test_runtime_orchestration.py` | MODIFY | Checkpoint hooks, ordering, business gates, failure behavior. |
| `backend/app/tests/test_supplier_risk_pipeline.py` | MODIFY | Full six-stage durable success/gated/restart scenarios. |
| `backend/app/tests/test_integration_transactions.py` | MODIFY | Atomic capability-record/checkpoint/handoff behavior. |

No other test artifact is authorized.

## 19. Acceptance criteria

1. Process restart loses no admitted execution, committed checkpoint, produced reference, or terminal result.
2. Atomic duplicate admission is correct under concurrent PostgreSQL transactions.
3. Identical replay starts no duplicate work; conflicting replay deterministically rejects.
4. Recovery selects only the first stage after the last verified committed checkpoint.
5. No committed capability stage is invoked twice for the same governed execution/recovery identity.
6. Capability record, checkpoint, handoff, and references share one local atomic transaction.
7. Business-gated completion remains `Completed`; technical failure remains `Failed` under ESM.
8. Retryable, terminal, uncertain-commit, and concurrency failures follow the approved matrices.
9. AuthorityContext and replay authorization cannot be inferred from opaque payload.
10. Evidence/provenance/decision/result meaning is referenced, not duplicated or reinterpreted.
11. All runtime tables and columns match the approved physical/security authorities and PMM role assignments.
12. Migration upgrade/downgrade safeguards and non-destructive rollback pass on PostgreSQL.
13. Existing CDD-010 and CDD-011 regression suites pass unchanged except explicitly authorized additions.
14. Architecture, Registry, dependency, checksum, manifest, boundary, secret, and changed-file checks pass.

## 20. Architecture-drift checklist

Before implementation closure verify: no new business entity; no canonical entity/attribute/relationship modification; no business-rule duplication; no RFC/BCS conflict; no layer bypass; no unapproved technology; no canonical-table writer; no unauthorized retention/security choice; and only enumerated files changed.

## 21. Implementation completion evidence

An implementation report must record base, implementation, PR, and merge SHAs; exact paths; migration revision; PostgreSQL version; schema checksum; transaction/recovery traces; concurrency/replay/security tests; full regression and coverage; architecture validations; residual risks; and rollback evidence.

## 22. Gate

**APPROVED FOR IMPLEMENTATION.** The Baseline v1.3 authorities resolve persistence, replay, security, and retention prerequisites.
