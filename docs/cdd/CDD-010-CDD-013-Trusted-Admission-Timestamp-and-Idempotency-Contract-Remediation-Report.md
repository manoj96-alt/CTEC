# CDD-010 / CDD-013 — Trusted Admission Timestamp and Idempotency Contract Remediation Report

Version: 1.0
Status: APPROVED FOR REMEDIATION

## Decision

The external supplier-risk request never contains `SourceObservation.received_at`. The trusted application boundary assigns it exactly once during atomic runtime admission, after authentication, tenant authorization, and closed-schema validation and before ERM execution.

CDD-010 distinguishes:

- **Client request identity:** SHA-256 of the canonical, validated, browser-controlled request envelope, bound by tenant, protocol version, integration-contract version, and request identifier through the existing durable admission key and record.
- **Admitted runtime identity:** the protected ERM input produced by a neutral trusted admission builder using that client request and the committed server admission timestamp.

The runtime treats both byte sequences as opaque. It compares the client identity for duplicate detection and executes only the admitted payload returned by the atomic store operation.

## Atomic and durable behavior

On first admission the existing database transaction creates the execution row and protected initial handoff together. The execution row stores the canonical client fingerprint and `admitted_at`; the initial handoff stores the integrity-protected admitted payload and its content hash. A failed transaction leaves neither record committed.

On identical duplicate or restart, the store recovers the protected initial handoff and returns the original admitted payload and `admitted_at`; it does not invoke the clock or admission builder. A changed client fingerprint or trusted-control fingerprint is rejected as an idempotency conflict. Tenant and protocol remain part of the existing unique key; integration contract remains recorded on the execution and handoff.

Replay and retry reuse protected handoffs and therefore preserve observation `received_at`. Recovery authorization, attempt creation, and capability timestamps remain separate trusted timestamps and never replace the observation receipt timestamp.

## Compatibility and lineage

Existing callers that supplied `received_at` were violating the previously published prohibition on client-controlled server timestamps. The closed request now rejects that field. This is a security and provenance correction, not new business semantics. Existing CDD-010 invocations without a trusted admission builder retain byte-identical legacy behavior.

## Persistence assessment

No migration is required. Existing governed records represent every required value without semantic overloading or a new persistence structure.

## Architecture drift check

- No business entity, canonical attribute, canonical relationship, or vocabulary is introduced.
- No capability business rule or orchestration order changes.
- No architecture layer is bypassed.
- No technology or dependency is introduced.
- Production and test changes are limited by the published exact allowlists.
