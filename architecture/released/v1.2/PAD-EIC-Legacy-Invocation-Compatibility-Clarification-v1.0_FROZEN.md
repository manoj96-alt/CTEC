# PAD-001 v1.5 / EIC-001 v1.3 — Invocation Compatibility Clarification

Status: FROZEN

## Additive authoritative language

1. Existing invocations valid under the released CDD-010 contract remain valid and retain their original meaning.
2. Absence of AuthorityContext or its version is permitted only for explicitly supported legacy Protocol Versions.
3. A legacy invocation without AuthorityContext may execute only operations already authorized under the legacy contract. It cannot receive new authority through inference or defaults.
4. New invocation versions requiring trusted control metadata must provide a supported AuthorityContext version at the trusted boundary.
5. Missing required metadata, malformed versions, and conflicting version declarations produce deterministic `Validation Failure` before admission and capability execution.
6. Unsupported Protocol Versions produce deterministic `Invalid Invocation` before admission and create no Execution Identifier.
7. AuthorityContext supplied with a legacy Protocol Version is `Validation Failure` and is never ignored.
8. Automatic downgrade, silent coercion, semantic reinterpretation, default-to-latest behavior, and substitution of caller payload claims for trusted authority metadata are prohibited.
9. Version negotiation may select only an explicitly supported compatible version and records requested version, selected version, compatibility rule, and Correlation Identifier.
10. Rejection and compatibility decisions expose only safe diagnostic codes and never credentials, tokens, or sensitive authority details.
11. Version rejection is protocol rejection, not ESM execution failure.

## Supported behavior at this release

The released CDD-010 Protocol Version remains the legacy version and its behavior is unchanged. RFC-014/CIM-001 trusted-control integration requires a future explicitly identified Protocol Version authorized by CDD-011 or a later work order. No new production Protocol Version or default is created by this clarification.

## Traceability

PAD-001 v1.5; EIC-001 v1.3; EOM-001 v1.3; ESM-001 v1.3; CDD-010 v1.3; CDD-010 Trusted Runtime Control Metadata Clarification v1.0; RFC-014 v1.1; CIM-001 v1.1.
