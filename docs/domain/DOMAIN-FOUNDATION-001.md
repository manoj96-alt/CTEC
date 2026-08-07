# DOMAIN-FOUNDATION-001 — Foundation Reference Model

Version: 1.0  
Status: Development under CDD-003

## Purpose

The Foundation Reference Model expresses the stable enterprise vocabulary authorized by CDD-003. It is a business ontology implemented in pure Python and is independent of persistence, APIs, frameworks, datasets, and deployment technology.

## Authorized entities

| Entity | Enterprise meaning | Canonical relationships |
| --- | --- | --- |
| Enterprise | The institution whose reference model is represented | Classified by Enterprise Type; associated with Country |
| Enterprise Type | Reference classification for an Enterprise | Referenced by Enterprise |
| Business Domain | An enterprise-owned area of business responsibility | Belongs to Enterprise |
| Country | Jurisdiction reference identified by ISO codes | Referenced by Enterprise |
| Institutional Concept | An enterprise-owned canonical concept | Belongs to Enterprise |
| Entity Type | Governed classification under an Institutional Concept | References Institutional Concept |
| Relationship Type | Governed vocabulary for relationships | Referenced by later operational layers |

No other entity is implemented.

## Value objects

- Identifier represents a UUID identity or reference.
- Canonical Name represents a required canonical term.
- Business Name represents a required business-facing name when present.
- Description represents required descriptive text when used.
- Reference Code represents a required external reference code.

Value objects are immutable and contain only generic structural validation.

## Enumerations

- Lifecycle State: Draft, Active, Suspended, Archived.
- Governance Status: Proposed, Approved, Retired, Archived.

These values are copied exactly from EAD-001 v1.3. The model records the values but does not perform lifecycle transitions or governance decisions.

## Structural rules

- Required identifiers must be Identifier values backed by UUIDs.
- Required names must be non-empty and respect EAD maximum lengths.
- ISO2 and ISO3 codes must contain exactly two and three characters respectively.
- Required references must be Identifier values.
- Datetimes must be timezone-aware.
- Version Number must be an integer.

These checks establish valid structure only. They do not evaluate business meaning or institutional standing.

## Dependency rules

The domain imports only the Python standard library and its own authorized shared artifacts. It contains no FastAPI, SQLAlchemy, Alembic, PostgreSQL, CSV, configuration, logging, repository, DTO, or REST dependency.

## Design decisions

### Persistence-independent entities

Reason: institutional concepts should outlive any technology stack.  
Alternative: reuse SQLAlchemy models.  
Rejected because: it would make the ontology depend on persistence and bypass the architecture boundary.

### Immutable dataclasses

Reason: reference values should be explicit, typed, and unable to mutate accidentally after construction.  
Alternative: mutable application objects.  
Rejected because: mutation would permit structurally invalid intermediate state.

### Generic value objects

Reason: identifiers, names, descriptions, and reference codes have stable structural meaning across the authorized slice.  
Alternative: unvalidated primitives.  
Rejected because: invalid primitive values could enter canonical objects.

### No services or domain events

Reason: neither category is authorized by CDD-003.  
Alternative: introduce behavior in anticipation of later CDDs.  
Rejected because: it would cross the assigned layer.

## Future extensions

Future CDDs may authorize additional slices. They must depend on this canonical language without changing it unless an approved model revision and RFC explicitly permit the change.

## Out of scope

Business rules, workflows, lifecycle transitions, governance decisions, identity resolution, semantic interpretation, assertions, knowledge, reasoning, persistence, repositories, DTOs, APIs, and CDD-004 are excluded.

## Enterprise language validation

| Entity | Supply Chain Director | Chief Data Officer | Constitutional terminology | Implementation leakage |
| --- | --- | --- | --- | --- |
| Enterprise | Recognizable as the institution | Recognizable ownership boundary | Exact canonical term | None |
| Enterprise Type | Recognizable enterprise classification | Recognizable reference classification | Exact EAD term | None |
| Business Domain | Recognizable area such as Supply Chain | Recognizable data and accountability boundary | Exact canonical term | None |
| Country | Recognizable jurisdiction | Recognizable reference-data concept | Exact EAD term | None |
| Institutional Concept | Understandable as institutionally defined meaning | Recognizable governed semantic concept | Exact constitutional term | None |
| Entity Type | Understandable classification of enterprise things | Recognizable canonical classification | Exact canonical term | None |
| Relationship Type | Understandable governed relationship vocabulary | Recognizable semantic relationship definition | Exact canonical term | None |

The canonical names are retained because clearer substitutes would weaken alignment with the Constitution, Logical Model, and EAD. Python-specific terminology is confined to implementation mechanics and does not enter entity names or attributes.
