# PERSISTENCE-001 — Canonical Persistence Architecture

Version: 1.0  
Status: Development under CDD-002

## Purpose

The CTEC database is a governed implementation of the Enterprise Cognitive Operating Model, not generic application storage. Its schema follows the frozen Physical Model v1.3. ORM classes, migrations, repositories, and seed behavior must preserve that model and the precedence established by ARCH-001, ARCH-003, and ARCH-004.

## Why PostgreSQL?

TAS-001 selects PostgreSQL as the prototype's single ACID source of truth. PostgreSQL provides UUIDs, enums, timestamp-with-time-zone values, constraints, transactions, JSONB for future approved uses, and sufficient indexing and text-search capabilities without introducing another operational system.

## Why SQLAlchemy?

TAS-001 selects SQLAlchemy 2.x. Its typed declarative mapping represents the frozen schema without coupling persistence to API or UI code. SQLAlchemy supplies explicit sessions and transactions while keeping PostgreSQL access behind repository and Unit of Work boundaries.

## Why Repository Pattern?

Repositories centralize persistence operations and prevent callers from embedding SQL or session handling. Every canonical table has a persistence-only repository type. Repositories add, retrieve, list, and delete records; they do not resolve identities, assign meaning, evaluate standing, or enforce business workflows.

## Why Unit of Work?

The Unit of Work owns exactly one SQLAlchemy session for a transaction. All repositories participating in that operation share the session. This provides atomic commit, explicit rollback, deterministic cleanup, and prevents repositories from creating hidden transactions.

## Migration strategy

Alembic is the sole schema-change mechanism. The initial revision executes the frozen Physical Model v1.3 DDL. Deterministic bootstrap support records are inserted after tables exist and before the Physical Model's own foreign-key constraints are attached, allowing the final schema to retain every frozen constraint without disabling or relaxing it.

Future migrations must:

- Reference an approved CDD and architecture decision.
- Preserve constitutional and RFC rules.
- Match approved Physical Model and EAD changes.
- Include reversible downgrade behavior where PostgreSQL permits it.
- Pass schema traceability and migration tests.
- Never use dataset shape to drive canonical schema changes.

Autogeneration is configured as a drift-assistance tool, not an architecture authority. Generated revisions require comparison with the approved canonical sources.

## Transaction strategy

Sessions are short-lived and never global. Unit of Work callers explicitly commit successful operations. Exceptions trigger rollback and every exit closes the session. PostgreSQL connection pooling is configuration-driven and uses pre-ping to reject stale connections.

## Seed loading strategy

EDT-001 v3 is ingestion data, not the canonical model. CDD-002 stores each CSV row as a deterministic Source Object representing provenance. `SourceSystems.csv` also creates deterministic Source System records. Candidate assertion rows remain Source Objects and are never parsed into Assertions.

Seed identifiers use UUIDv5 with a frozen namespace, canonical row serialization, the frozen `SEED_TIMESTAMP`, and `EDT-001-V3`. Repeated loads create no duplicates and produce a count report. Full reset is explicit: Alembic downgrades to base and reapplies the canonical revision before seeding.

See [EDT-001-MAP](EDT-001-MAP.md) for the ingestion contract.

## How this supports future cognitive capabilities

Future identity, semantic, assertion, knowledge, decision, reasoning, memory, learning, and governance services receive stable canonical repositories and transaction boundaries. Source provenance is retained without prematurely assigning meaning. Later services can transform authorized source objects through domain services while persistence remains unchanged and cognitively neutral.

## Traceability

- Every table and column is checked against Physical Model v1.3.
- Canonical entity columns trace to EAD-001.
- Join-table columns trace to Physical Model M:N relationships.
- Foreign keys preserve the Physical Model and Logical Model relationships, with generic audit/version metadata governed by ARCH-001.
- A schema checksum detects unauthorized migration-source changes.

## Explicitly out of scope

- Business logic
- Identity Resolution
- Semantic Resolution
- Assertion interpretation or construction
- Knowledge inference or institutionalization
- Decision Assembly
- Memory
- Reasoning
- Governance decisions
- Learning
- REST business APIs
- Model redesign or convenience columns

