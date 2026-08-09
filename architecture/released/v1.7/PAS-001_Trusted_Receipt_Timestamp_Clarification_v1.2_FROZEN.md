# PAS-001 — Trusted Receipt Timestamp Clarification

Version: 1.2
Status: FROZEN

Supersedes PAS-001 v1.1 only for supplier-risk receipt timestamp ownership.

`SourceObservation.received_at` is prohibited in every browser-controlled submission form. Unknown, aliased, nested, or equivalent trusted timestamp claims are rejected. After authentication, tenant authorization, and closed-schema validation, the trusted admission boundary assigns the timezone-aware UTC timestamp exactly once from its governed clock. The timestamp is carried into ERM input, persisted with the original admission, and reused unchanged for duplicate, restart, retry, and replay. Replay and attempt timestamps remain separate.

This clarification introduces no new supplier-risk semantics or authority.
