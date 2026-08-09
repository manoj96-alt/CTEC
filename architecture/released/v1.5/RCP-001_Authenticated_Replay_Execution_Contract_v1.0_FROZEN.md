# RCP-001 — Authenticated Replay Execution Contract

Version: 1.0
Status: FROZEN
Owner: ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`)
Approval: Closure Gate 4 replay remediation decision

Protected handoffs use authenticated encryption and a versioned envelope. Authentication binds
tenant, logical execution, attempt, source stage, target stage, and integration contract version
as associated data. Recovery verifies the envelope version, key identifier, authentication tag,
context equality, content hash, checkpoint status, stage ordering, and contract compatibility
before returning opaque bytes. Missing payload and failed authentication are distinct internal
errors but share safe external diagnostics. Key rotation selects an explicit key identifier;
unknown or retired keys fail closed without downgrade.

Replay authorization, checkpoint selection, protected recovery, linked-attempt creation, and the
recovery record commit atomically under one transaction-scoped replay identity lock. The original
attempt remains terminal and immutable. A valid predecessor checkpoint supplies the selected
stage; all preceding stages are reused without invocation and the selected and downstream stages
execute exactly once under the new attempt. ERM replay uses the original admitted input. Unsafe,
uncommitted, uncertain, cross-tenant, cross-execution, reordered, skipped, or incompatible recovery
is rejected rather than silently restarted.

Only a server-created `ValidatedRecoveryInvocation` may enter the resume boundary. Product callers
cannot provide checkpoint payloads, resume ordinals, protected values, or trusted recovery
metadata.

