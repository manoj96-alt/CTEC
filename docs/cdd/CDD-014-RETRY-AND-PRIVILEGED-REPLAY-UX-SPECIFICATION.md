# CDD-014 — Retry and Privileged Replay UX Specification

Version: 1.0

## Retry

- Offered only when CDD-013 explicitly reports eligibility and the user has `supplier-risk:retry`.
- The dialog identifies the logical execution and failed attempt, explains that history is retained,
  requires a bounded reason, and uses a newly generated request ID as Idempotency-Key.
- Submission is single-flight. Identical browser retransmission preserves key and body; the returned
  existing/new attempt is authoritative. A stale `409`, `403`, or changed eligibility closes or
  refreshes the action without client override.

## Privileged replay

- Offered only with `execution:replay`, `EXECUTION_RECOVERY_OPERATOR`, and server-returned replay
  options. Hidden controls do not grant authority.
- The user selects only a server-issued opaque option, supplies an explicit reason, reviews original
  execution/attempt and expected new attempt behavior, then deliberately confirms.
- The browser never creates or edits checkpoint payload, resume ordinal, handoff, recovery metadata,
  AuthorityContext, or authorization decision. The original attempt is never shown as overwritten.
- A denial or conflict is rendered as authoritative and audit-sensitive; safe codes only.

## Current blocker

CDD-013 exposes neither retry eligibility nor replay option identifiers. Its replay request has only
request/correlation IDs and reason. These workflows cannot be implemented by inference from Failed
state or stage order; the server contract must be clarified first.
