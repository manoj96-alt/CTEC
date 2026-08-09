# ARCH-003 — Persistence Bootstrap and Metadata Policy

Version: 1.0  
Status: Frozen  
Applies from: CDD-002 onward  
Related decision: ARCH-001 — Persistence Bootstrap and Canonical Mapping

## Purpose

This decision defines the constitutional policy for deferred bootstrap references, deterministic persistence metadata, the bootstrap system actor, and candidate assertion data. It preserves the separation between storage, meaning, institutional assertion, knowledge, and governance.

## Governing principle

> Persistence records facts. Cognition assigns meaning. Governance grants standing.

The responsibilities remain separate:

```text
Persistence
    ↓ stores data
Semantic Layer
    ↓ creates meaning
Assertion Layer
    ↓ creates assertions
Knowledge Layer
    ↓ institutionalizes knowledge
Governance Layer
    ↓ approves institutional standing
```

ARCH-003 is subordinate to the architectural precedence frozen by ARCH-001. It does not introduce a column or relationship, relax a frozen `NOT NULL`, or alter the Logical Model, Physical Model, or EAD-001.

## Resolution 1 — deferred bootstrap foreign keys

The persistence layer must never fabricate a business relationship merely to satisfy referential integrity during bootstrap.

When a canonical foreign key is nullable in the frozen Physical Model and depends on a future cognitive capability, it remains `NULL` until the CDD responsible for that capability supplies a truthful reference. When the frozen Physical Model makes a relationship mandatory, persistence must not create the record until all required canonical dependencies exist.

Examples of capability-owned references include:

| Reference role | Bootstrap state when nullable | Owning capability |
| --- | --- | --- |
| Approval actor | `NULL` | Governance layer |
| Institutionalization actor | `NULL` | Knowledge layer |
| Reason graph | `NULL` only where the frozen model permits it | Reasoning layer |
| Experience | `NULL` only where the frozen model permits it | Experience layer |

These role names are architectural examples, not authorization to add similarly named columns. Implementations must use only attributes present in EAD-001 and the Physical Model.

The canonical `created_by` attribute follows ARCH-001: bootstrap-generated canonical records reference the ECOM Bootstrap System Enterprise Entity when the record is authorized to exist.

## Resolution 2 — deterministic metadata defaults

All bootstrap metadata is deterministic.

### Bootstrap system entity

| Property | Frozen value |
| --- | --- |
| Canonical name | `ECOM Bootstrap System` |
| Entity type | `System Actor` |
| Status | `Active` |
| Identifier | Fixed UUID stored as a version-controlled constant |

The bootstrap entity is created exactly once, is immutable, and is never deleted.

### Seed timestamp

Bootstrap-generated records use the fixed timestamp:

```text
2026-01-01T00:00:00Z
```

The implementation exposes this value as `SEED_TIMESTAMP`. It must not derive bootstrap timestamps from wall-clock time.

### Determinism requirements

- Repeated seed runs produce the same canonical state.
- Foreign key references remain stable across environments.
- Automated tests can assert exact identifiers and timestamps.
- Random UUID generation is prohibited outside the approved bootstrap process.
- Dataset ordering does not affect the result.

## Resolution 3 — candidate assertions remain source data

Rows that represent candidate assertions remain Source Objects until validated and transformed by the Assertion Service.

CDD-002 may import and persist source provenance. It must not interpret free text, resolve identities, choose a governed predicate, construct an Assertion, or grant institutional standing.

```text
Candidate assertion CSV row
    ↓
Source Object
    ↓
Stored
    ↓
STOP for CDD-002
```

The future authorized flow is:

```text
Source Object
    ↓
Identity Resolution
    ↓
Semantic Resolution
    ↓
Assertion Service
    ↓
Knowledge Service
```

Not every source row becomes an institutional Assertion. A source value such as `SupplierName = TSMC` remains source data until later capabilities establish identity, meaning, predication, evidence, and standing.

## Persistence boundary

CDD-002 may:

- Persist and retrieve records defined by the canonical Physical Model
- Preserve source provenance without semantic interpretation
- Apply deterministic, approved bootstrap metadata
- Leave nullable capability-owned references unresolved
- Enforce database constraints and transaction boundaries

CDD-002 must not:

- Relax frozen nullability or foreign key constraints
- Invent placeholder business entities or relationships
- Parse candidate assertions into canonical Assertions
- Perform identity or semantic resolution
- Infer or institutionalize Knowledge
- Assemble Decisions or Reasons
- Execute Governance or Learning behavior

## Consequences

- The ontology remains truthful even when optional references are intentionally unresolved.
- Mandatory canonical relationships remain mandatory.
- Bootstrap state is reproducible and testable.
- Candidate assertions remain provenance-bearing source data.
- Later cognitive layers—not persistence—own transformation into meaning and institutional standing.
