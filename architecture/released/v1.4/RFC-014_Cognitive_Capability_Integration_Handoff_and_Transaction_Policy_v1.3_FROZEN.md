# RFC-014 — Application Security Audit Clarification

Version: 1.3
Status: FROZEN
Supersedes: RFC-014 v1.2
Approval: CDD-013 bounded governance decision

RFC-014 v1.2 remains controlling. This clarification adds one application-boundary audit record
without changing runtime or capability semantics.

## Bounded persistence authorization

CDD-012 may persist exactly six non-canonical infrastructure records: execution admission, execution transition/stage checkpoint, protected handoff, artifact reference, final result, and recovery-attempt state. These records support runtime recovery, replay, provenance, auditability, and governed final-result delivery only. They do not create canonical entities, replace capability persistence, duplicate business meaning, or authorize a general integration platform. Original evidence and provenance references remain immutable.

Each capability record, its evidence/reference rows, completed checkpoint, outbound handoff, and produced references commit in one capability-local transaction. There is no cross-capability transaction or compensation. Previously committed immutable records are never changed or deleted by recovery.

## Attempts, retry, and replay

An execution attempt is immutable and terminal after terminal state. Failed attempts never return to running. Retry or replay creates a new attempt under the same logical execution, linked to its predecessor and—when replayed—to the authorized checkpoint. Identical invocation returns or continues the existing logical execution; conflicting fingerprints reject without work.

Completed stages may be reused only after contract-version, integrity, evidence, authority, and commit verification. The next attempt begins at the first uncommitted valid stage. Uncertain or non-idempotent side effects prohibit automatic replay. Business-gated completion remains successful. Attempt history never overwrites prior history.

Replay requires authenticated trusted AuthorityContext, tenant equality, `EXECUTION_RECOVERY_OPERATOR` role, `execution:replay` scope, reason, correlation identifier, and authorization decision/reference. The ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`) is the bounded security owner for this role/scope only. Original and replay authority references are both retained.

## Security and retention

Runtime data uses platform-standard encrypted PostgreSQL transport and encrypted storage controls. Credentials, tokens, secrets, and full authentication material are prohibited. Persist the minimum authority evidence and prefer governed references over replicated evidence or payloads. Tenant identifiers, evidence, diagnostics, and replay metadata require least-privilege access and safe logging.

Execution, stage, handoff, artifact-reference, decision/result, replay, and audit records retain for seven years after terminal completion. Transient payload material not required for evidence, audit, or replay is removed within 30 days. Idempotency records retain for the execution period where needed to prevent side effects. Authorized tenant-scoped deletion is audited; legal hold suspends deletion of linked records. This bounded default yields to stricter law, contract, or enterprise policy.

All v1.1 prohibitions remain in force outside this exact scope.

## Supplier-risk API security audit

CDD-013 may persist exactly one additional non-canonical `API_SECURITY_AUDIT_EVENT`. It records
immutable admission, authentication, authorization, protected disclosure, abuse-control,
retry/replay, and safe failure evidence only. It is not business data, analytics, an execution
record, a decision source, or an application-log substitute. It stores no tokens, signatures,
credentials, complete claims, bodies, sensitive evidence, or stack traces.

The CDD-013 audit repository is the only application writer. Each event inserts in an isolated
transaction so rejected requests can be recorded. A security-sensitive mutation fails closed if
its required audit insert fails. Successful protected mutations link the audit event to execution
or attempt identifiers. Events are append-only and database-protected against ordinary update or
delete. Tenant-scoped auditable disposition is permitted only after seven years and only when no
legal hold applies.
