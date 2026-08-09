# RND-001 — Architecture Registry Normalization Decision

Version: 1.0  
Status: FROZEN  
Current: YES  
Authority: AUTHORITATIVE  
Release type: Governance clarification  
Effective date: 2026-08-08

## Decision

The Architecture Registry SHALL represent governance using three independent fields: Status, Current, and Authority. Composite lifecycle values are prohibited.

The only valid combinations are:

| Status | Current | Authority | Meaning |
|---|---|---|---|
| FROZEN | YES | AUTHORITATIVE | Active governing artifact |
| DEVELOPMENT | NO | NON-AUTHORITATIVE | Work in progress |
| SUPERSEDED | NO | NON-AUTHORITATIVE | Replaced artifact |
| HISTORICAL | NO | NON-AUTHORITATIVE | Audit history only |

Every SUPERSEDED artifact SHALL identify its replacement. Exactly one current authoritative version SHALL exist for each governed artifact identifier unless the Registry explicitly states that no approved version exists.

An authoritative artifact SHALL NOT depend on a DEVELOPMENT, SUPERSEDED, HISTORICAL, missing, or unapproved artifact.

## Approval workflow

| Gate | Date | Result |
|---|---|---|
| DRAFT | 2026-08-08 | Complete |
| ARCHITECTURE REVIEW | 2026-08-08 | Approved |
| APPROVED | 2026-08-08 | Approved |
| RELEASED | 2026-08-08 | Frozen in Architecture Baseline v1.1 |

## Validation evidence

The governed release validator enforces allowed field values, valid combinations, mandatory replacements, current-authority uniqueness, and authoritative dependency eligibility. The Architecture Release Manifest and Architecture Registry were regenerated atomically with this decision.

Release-gate results:

- Registry entries evaluated: 102.
- `FROZEN + YES + AUTHORITATIVE`: 37 entries, comprising 36 current authoritative artifacts and this Registry control record.
- `DEVELOPMENT + NO + NON-AUTHORITATIVE`: 3 entries.
- `SUPERSEDED + NO + NON-AUTHORITATIVE`: 49 entries, all with identified replacements.
- `HISTORICAL + NO + NON-AUTHORITATIVE`: 13 entries.
- Composite lifecycle status values: 0.
- Missing Status, Current, or Authority fields: 0.
- Invalid field values or combinations: 0.
- Artifact identifiers with more or fewer than one required current authoritative version: 0.
- Authoritative dependencies on Development, Superseded, Historical, missing, or unapproved artifacts: 0.

## Architecture drift

This decision introduces no business entity, canonical attribute, relationship, business semantic, implementation layer, or technology. It governs architecture-release metadata only.
