# CDD-010 — Trusted Runtime Control Metadata Clarification

Version: 1.0 DRAFT
Status: RELEASE CANDIDATE / NON-AUTHORITATIVE

## Amendment record

| Item | Value |
|---|---|
| Governing implementation work order | CDD-010 v1.3, FROZEN / IMPLEMENTED |
| Exact sections affected | Authorized External Contracts; Runtime Envelope; Acceptance Criteria; Exclusions; Traceability |
| Change type | Normative scope clarification; no implementation authorization |
| Downstream dependency | EIC-001 v1.3 draft, EOM-001 v1.3 draft, RFC-014, CIM-001, future CDD-011 |

## Current authoritative language

CDD-010 authorizes a neutral `CapabilityStepInput` and `CapabilityStepOutput` containing governed runtime identifiers, Protocol Version, and Opaque Payload. Every step preserves metadata; the runtime does not parse, validate, transform, enrich, map, or interpret payload semantics.

## Proposed additive language

Future governed integration may extend the runtime control envelope with immutable AuthorityContext and runtime/capability timestamps defined by approved EIC-001, EOM-001, RFC-014, and CIM-001. These values are separate control metadata, never part of Opaque Payload.

The extension must preserve:

- payload opacity and byte-preserving handoff;
- six ordered injected capability ports;
- process-local idempotency and execution-state semantics;
- runtime ignorance of business meaning; and
- prohibition on production adapters inside CDD-010.

This clarification does not authorize changes to the implemented CDD-010 files. A later approved CDD must enumerate exact modifications and compatibility tests.

## Reason

The trusted metadata channel is required for production integration but must not be smuggled into the business payload or retroactively expand CDD-010 implementation authority.

## Compatibility

CDD-010's existing runtime remains valid. New metadata requires a versioned additive contract and separate implementation authorization. Existing invocations remain supported only if the approved protocol defines compatibility/default rules.

## Governance actions

After approval: register this clarification as a governed CDD-010 companion; do not change CDD-010's frozen implementation status; add dependencies to approved EIC/EOM/RFC/CIM versions; update checksums and manifest.

## Validation and rollback

Validate the original CDD-010 test suite unchanged, plus future metadata propagation, immutability, payload-opacity, and authorization-boundary tests. Rollback disables the new protocol version; never serialize trusted metadata into Opaque Payload.
