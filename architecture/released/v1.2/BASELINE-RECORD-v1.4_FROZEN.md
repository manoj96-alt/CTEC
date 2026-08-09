# Architecture Baseline Record v1.4

Status: FROZEN
Baseline: Architecture Baseline v1.2
Effective date: 2026-08-08
Approval: Closure Gate 1 clarification release decision

## Scope

Baseline v1.2 is the cumulative current architecture baseline. It preserves every unchanged Baseline v1.1 authority and releases only the bounded supplier-risk integration amendments approved at Closure Gate 1.

Added authorities: RFC-014 v1.1, CIM-001 v1.1, CVR-001 v1.0, ARCH-005 v1.0, CDD-010 Trusted Runtime Control Metadata Clarification v1.0, and PAD/EIC Legacy Invocation Compatibility Clarification v1.0.

Clarification releases: ASM-001 v2.3, DRM-001 v1.3, GRM-001 v1.3, EIC-001 v1.3, EOM-001 v1.3, and PAD-001 v1.5.

The baseline adds exactly two canonical vocabulary values and no schema structure. CDD-010 remains FROZEN / IMPLEMENTED; no runtime implementation is changed.

## Integrity

`architecture/INDEX.md` is the authoritative Registry. `RELEASE-MANIFEST-v1.2.xlsx` is the cumulative integrity register. `DEPENDENCY-MATRIX-v1.2.csv` records approved current dependencies.

## Implementation gate

This baseline closes Architecture Remediation Gate 1. It does not approve CDD-011 implementation. CDD-011 requires its own approved work order and preimplementation gate.
