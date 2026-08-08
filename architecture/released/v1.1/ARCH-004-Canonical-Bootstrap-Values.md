# ARCH-004 — Canonical Bootstrap Values

Version: 1.0  
Status: Frozen  
Applies from: CDD-002 onward

## Constitutional implementation constants

| # | Constant | Frozen value | Rationale |
| --- | --- | --- | --- |
| 1 | Bootstrap Enterprise Entity UUID | `00000000-0000-0000-0000-000000000001` | Deterministic, recognizable, and never regenerated. |
| 2 | Bootstrap canonical name | `ECOM Bootstrap System` | Represents the platform before human Enterprise Entities exist. |
| 3 | Bootstrap business name | `ECOM Bootstrap System` | Matches the canonical name for the prototype. |
| 4 | Bootstrap entity type | `System Actor` | Distinguishes the platform from people and organizations. |
| 5 | Bootstrap lifecycle status | `Active` | The bootstrap entity is always active and never deleted. |
| 6 | Seed timestamp | `2026-01-01T00:00:00Z` | Produces repeatable seeds and tests. |
| 7 | Seed version | `EDT-001-V3` | Records the initialization dataset version. |

## Freeze rules

### Bootstrap entity

Exactly one bootstrap entity exists. It is immutable, never archived, never deleted, and never renamed.

### Fixed identifier

Every environment uses `00000000-0000-0000-0000-000000000001`. Random bootstrap identifiers are prohibited.

### Deterministic timestamp

Bootstrap and seed-generated records use `2026-01-01T00:00:00Z`. Wall-clock functions such as `NOW()` or `datetime.utcnow()` are prohibited from deterministic seed construction.

### Seed version

Seed reports and duplicate-load detection use `EDT-001-V3`.

### Candidate assertions

Rows that appear to describe assertions remain Source Objects until the Assertion Service validates and transforms them. Persistence stores provenance and performs no semantic interpretation.

### Deferred foreign keys

Optional capability-owned references remain `NULL` until their owning CDD supplies truthful values. No reference is fabricated. Frozen Physical Model nullability remains authoritative.

### Determinism

Repeated `reset-db`, `migrate`, and `seed` sequences produce the same canonical contents apart from database-managed technical values explicitly authorized by the canonical model.

## Code authority

The implementation source of truth for these constants is `backend/app/core/bootstrap.py`. An RFC is required to change any frozen value.

