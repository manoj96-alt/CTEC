# Architecture Consistency Report — v1.10

Version: 1.10
Status: FROZEN
Approval: Product Owner authorization, Gate D0/D1 (RFC-016)

## Scope

This report covers the Gate D1 architecture release described in RFC-016:
ECOM Physical Data Model v1.7, its dependent registry/dependency-matrix
updates, the PAD-001 Product-Internal Deterministic Capability Boundary
Clarification, and the tooling that generated them.

## Consistency findings

- **Canonical boundary is self-consistent.** Physical Model v1.7 contains
  exactly 32 canonical `CREATE TABLE` statements before its boundary marker
  and exactly 7 bounded-extension `CREATE TABLE` statements after it (39
  total, no duplicates) — table count unchanged from v1.6; canonical column
  count is 374 (373 + the one new `institutional_relationships.tenant_id`
  column). Verified programmatically by
  `tools/generate_v1_9_physical_model_release.py` at generation time and
  independently re-verified by `backend/app/tests/test_canonical_metadata.py`
  against the generated file on disk, not against the generator's own
  in-memory state.
- **The generated diff is exactly the RFC-016 §2b invariant, nothing else.**
  A byte-level diff between v1.6 and v1.7 shows only: the `tenant_id` column
  on `institutional_relationships`; its two existing plain foreign keys
  (`fk_institutional_relationships_from_entity_id`,
  `fk_institutional_relationships_to_entity_id`) becoming tenant-qualified
  composite foreign keys under the same constraint names; the two new
  tenant-scoped unique constraints; and the one new tenant_id index. No other
  table, column, or constraint changed.
- **ORM matches the canonical section exactly.** `canonical_metadata`
  (SQLAlchemy) has 32 tables / 374 columns matching physical model v1.7's
  canonical section column-for-column, table-for-table
  (`test_orm_tables_and_columns_match_frozen_physical_model`). Indexes match
  exactly (`test_indexes_match_frozen_physical_model`), including the new
  `idx_institutional_relationships_tenant_id`.
- **Traceability is complete.** `docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.7.json`
  traces all 374 canonical columns to an Enterprise Attribute Dictionary row;
  zero missing EAD traces (`missing_ead_traces: []`).
- **Migration matches physical model v1.7 and enforces RFC-016 §5a.** Alembic
  migration `0012_institutional_relationship_tenant_ownership` (backend,
  applied to a disposable PostgreSQL 17 instance) produces the identical
  composite-uniqueness and composite-foreign-key structure described by
  physical model v1.7 for `institutional_relationships`, verified by direct
  `pg_constraint` inspection. Six migration scenarios were exercised against a
  real PostgreSQL database: an empty table (succeeds, no backfill), a
  pre-existing same-tenant relationship (tenant deterministically resolved,
  succeeds), a pre-existing cross-tenant relationship (fails closed before any
  schema change), a pre-existing relationship with an unresolvable endpoint
  (fails closed), a post-migration attempt to insert a cross-tenant
  relationship (rejected by the composite foreign key), and a post-migration
  same-tenant relationship (accepted).
- **Prior releases are untouched.** `git status --porcelain` on
  `architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql` and every
  earlier physical model file shows zero changes; all retain their original
  checksums.

## Drift assessment

No unauthorized drift identified. The only content difference between v1.6
and v1.7 is the single change RFC-016 explicitly authorizes: tenant ownership
on `institutional_relationships`. No other capability, API, or runtime
behavior is affected by this release. No Priority 6 (Ask CTEC) capability —
API, intent parser, traversal engine, answer composer, frontend workspace, or
demo data — is introduced by this release.

## Readiness

Backend verification for the Gate D1 tenant-foundation extension (migration
upgrade determinism across six scenarios, ORM/canonical-metadata/traceability
tests, full backend suite, black/isort/ruff/mypy, architecture release
verification) is green at the time of this report. Priority 6 / Ask CTEC
product implementation has not yet begun.
