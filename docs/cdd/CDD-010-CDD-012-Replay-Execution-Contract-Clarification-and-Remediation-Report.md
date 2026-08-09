# CDD-010/CDD-012 Replay Execution Contract — Clarification and Remediation Report

Version: 1.0  
Status: IMPLEMENTED AND VERIFIED  
Approved governance base: `ba59931de602e4cd66bb8edf8b2266b718b17073`  
Clarification-release merge: `3e764c2d1019bf167e705d522d7803f1942d8d3d`

## Outcome

The bounded replay remediation is complete. Runtime handoffs are authenticated, encrypted,
versioned, and bound to tenant, logical execution, attempt, stage direction, and integration
contract. Admission retains the original opaque ERM input in the existing handoff table. Each
committed stage reuses the preceding governed handoff and persists one authenticated output.

The durable recovery boundary validates replay authority, trusted `AuthorityContext`, terminal
state, contiguous committed stage history, safe-failure state, contract version, authenticated
context, and plaintext content hash. It then creates the replay execution and recovery linkage in
one transaction under a process lock and, on PostgreSQL, a transaction-scoped advisory lock.
Duplicate concurrent admission returns the same linked attempt.

The CDD-010 runtime exposes one server-only `resume` boundary accepting only a marked
`ValidatedRecoveryInvocation`. Ordinary invocation remains unchanged and begins at ERM. Resume
skips reused stages and invokes the selected and downstream injected ports in governed order.

## Changed-file authorization

All changed paths are listed by
`docs/cdd/CDD-010-CDD-012-REPLAY-REMEDIATION-AUTHORIZATION.md` v1.2. Versions 1.1 and 1.2 add only
the pre-existing durable-store regression test and the existing dependency declaration path.
No schema migration, new persistence record, API, UI, capability adapter, business rule,
composition-root wiring, or deployment change was introduced.

## Acceptance traceability

| Requirement | Evidence |
|---|---|
| Authenticated handoff protection and recovery | `AuthenticatedHandoffProtector`; round-trip, tamper, malformed-envelope, unavailable-key, and rotation tests |
| Context binding | `ProtectionContext` authenticates tenant, logical execution, attempt, stage, direction, and contract |
| Integrity-verified checkpoint recovery | Durable recovery validates committed contiguous stages, AEAD tag, compatibility, and SHA-256 content hash |
| Atomic linked replay | Execution and recovery records share one transaction; replay identity is serialized |
| Duplicate/concurrent safety | Concurrent replay test proves one execution and one recovery linkage |
| Original attempt immutability | Recovery performs no mutation of the original execution or stage history |
| Resume from selected stage | Parameterized test covers all six stage ordinals and proves preceding ports are not invoked |
| Server-only recovery | Runtime rejects unvalidated recovery values; the recovery factory is internal to the durable boundary |
| No non-atomic bypass | The obsolete separately committed `authorize_recovery` path was removed |

## Validation evidence

- Complete backend test suite: `146 passed, 9 skipped`; coverage `90.27%` (required `80%`).
- Ruff: passed.
- Black check: passed.
- isort check: passed.
- mypy strict for `app/runtime`: passed.
- Architecture release verifier: `169 artifacts`, `122 approved relationships`, passed.
- Registry combinations: valid; v1.0 through v1.5 manifests verified.
- `git diff --check`: passed.
- Changed-file boundary: enforced by `test_runtime_architecture.py`, passed in the full suite.

## Residual risks

- Cross-process duplicate serialization depends on PostgreSQL advisory locks; SQLite test execution
  uses the documented process lock.
- Key material provisioning and retirement policy remain deployment configuration concerns. The
  runtime fails closed for unknown or retired key identifiers.
- This remediation supplies the governed internal recovery boundary. Product-facing authorization,
  response filtering, and retry/replay HTTP representation remain CDD-013 responsibilities.

Recommendation: **REPLAY REMEDIATION IMPLEMENTED AND VERIFIED — READY FOR GOVERNED PUBLICATION**.
