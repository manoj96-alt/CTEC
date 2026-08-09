# CDD-010 — Trusted Admission Identity Clarification

Version: 1.5
Status: FROZEN

Supersedes CDD-010 v1.4 only for trusted admission identity.

The runtime distinguishes the canonical client request payload from its admitted runtime payload. Atomic idempotency compares the canonical validated client bytes under the existing tenant, protocol-version, and request-identifier key. A neutral trusted admission builder may add server-owned metadata exactly once using the committed admission timestamp. The runtime does not interpret either payload. Identical duplicates recover the original protected admitted payload and timestamp; changed client bytes conflict. Legacy invocations without a builder retain their prior byte-identical behavior.

No orchestration order, capability meaning, business rule, external protocol, or persistence entity changes.
