# CDD-012 — Authenticated Replay Clarification

Version: 1.3
Status: FROZEN
Supersedes: CDD-012 v1.2 recovery contract only
Approval: Closure Gate 4 replay remediation decision

CDD-012 owns authenticated handoff recovery, checkpoint validation, atomic linked-attempt creation,
and replay identity concurrency. It uses the existing six runtime records. No new table or column
is required: recovery linkage already records logical/original/replay execution, checkpoint,
tenant, principal, authority references, reason, correlation, and time. A transaction-scoped
advisory lock serializes one replay identity; validation and both new rows commit together or not
at all. Resume stage is derived from the verified checkpoint and is never caller state.

Protection and recovery comply with RCP-001. A started record without committed outcome is
uncertain. Completed reused stages never execute again. Original attempts remain immutable.

