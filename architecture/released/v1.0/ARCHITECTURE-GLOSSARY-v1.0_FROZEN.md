# CTEC Architecture Glossary

Version: 1.0
Status: FROZEN
Authority: Architecture Governance Terminology
Approval Reference: P2 Documentation and Governance Cleanup

## Business Capability Specification (BCS)

The official term for an approved, technology-neutral specification that owns business vocabulary, semantics, principles, artifacts, lifecycle rules, outcomes, and capability boundaries within one assigned business capability.

`BCS` is the only current abbreviation. **Business Capability Model (BCM)** is deprecated and must not be used in new architecture, CDDs, implementation guidance, or code. Historical occurrences of BCM retain their original audit meaning but confer no current authority.

## EAH-001

The ECOM Architecture Handbook is the versioned constitutional architecture authority. It is not a living, silently mutable document. Clarifications require a versioned clarification release, architecture review approval, an atomic Architecture Registry update, and regeneration of the applicable Architecture Release Manifest.

If EAH-001 conflicts with a lower-order artifact, the authority hierarchy defined by EAH-001 and CDS-001 applies. If two current artifacts at the same authority level conflict, implementation must stop until architecture governance issues a clarification. The Architecture Registry determines which version is current.

## Architecture Registry

`architecture/INDEX.md` is the sole authoritative registry for artifact identity, currentness, governance status, baseline membership, and location. A filename, directory name, embedded status label, or `_FROZEN` suffix is informational only and does not establish authority.

## Architecture Release Manifest

The authoritative integrity register for one Architecture Baseline Release. It records every baseline artifact, document metadata, governance status, and SHA-256 checksum. Its own checksum is pinned in the Architecture Registry.

## Architecture Baseline Release

A governed collection of specific document versions released together, such as Architecture Baseline v1.1. A baseline version describes the collection and does not replace or redefine the semantic version of any document inside it.

## Document Version

The semantic version of one governed artifact, such as ERM-001 v2.2 or PAD-001 v1.3. Document versions evolve independently from Architecture Baseline versions. Baseline membership is determined by the Architecture Registry and Release Manifest.

## Governance statuses

- **CURRENT / FROZEN / AUTHORITATIVE** — current governing artifact explicitly designated by the Architecture Registry.
- **CURRENT / FROZEN** — current frozen governing artifact.
- **CURRENT / DEVELOPMENT** — current registered artifact that has not been frozen; it must not be treated as frozen based on its filename.
- **SUPERSEDED** — replaced artifact retained for audit history; it does not govern new implementation.
- **HISTORICAL — RESOLVED** — review artifact whose findings were resolved by later governing artifacts.
- **HISTORICAL — SUPERSEDED** — non-governing implementation or work-order artifact replaced by a later approved artifact.
- **HISTORICAL — IMPLEMENTED** — completed implementation record retained for traceability; it is not an architecture authority.

Historical and superseded artifacts are excluded from current release-gate blocker evaluation. Any unresolved issue must be represented by a current registered artifact or an explicitly open current review record.
