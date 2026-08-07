# CDD-005 Architecture Clarification Report — SRM-001 v2.0 Residuals

Status: BLOCKING  
Authority: SRM-001 v2.0 FROZEN  
Supersedes: the unresolved portions of the original CDD-005 clarification report

## Resolved by SRM-001 v2.0

SRM-001 v2.0 successfully defines governed Institutional Concepts as semantic meanings, governed Context as the record context, minimum evidence, outcome values, confidence applicability, current-record cardinality, external history, and override immutability.

## Residual clarification 1 — immutable Record Status

SRM-001 v2.0 simultaneously requires:

- `Record Status` to be assigned at creation and immutable;
- only one active record for an Enterprise Entity and Business Context;
- a new immutable record when understanding changes; and
- history outside immutable records.

If the original record was created with `Active`, it cannot later become `Archived` without violating immutability. If active/archive state exists only in external history, the meaning and permitted creation values of the record’s own `Record Status` attribute are undefined.

Required decision: define whether `Record Status` is a creation-time snapshot, remove it from the immutable artifact, or define an immutable supersession representation that does not leave multiple records carrying `Active` status.

## Residual clarification 2 — Possible Resolution interpretations

SRM-001 v2.0 says:

- Semantic Interpretation is a reference to one Institutional Concept;
- the record specification requires exactly one concept only when Resolved; and
- Possible Resolution has one or more candidate Institutional Concepts.

The record specification does not identify an attribute that retains those candidate Institutional Concept references, nor whether a Possible Resolution record’s singular Semantic Interpretation contains the leading candidate.

Required decision: define the Semantic Resolution Record representation and cardinality for candidate concepts when outcome is `Possible Resolution`.

## Architecture drift check

- No canonical entity, attribute, or relationship was introduced or modified.
- No EAH, RFC, EAD, ERM, SRM, Logical Model, or Physical Model was modified.
- No architecture layer was bypassed.
- No technology was introduced.
- No CDD-005 implementation code was created.

CDD-005 implementation remains stopped until a frozen SRM revision resolves these two business-artifact semantics.
