# Architecture Consistency Report — v1.9

Version: 1.9
Status: FROZEN
Approval: Product Owner authorization, Increment 3A-0 (RFC-015)

## Scope

This report covers the tenant-foundation architecture release described in
RFC-015: ECOM Physical Data Model v1.6, its dependent registry/dependency-matrix
updates, and the tooling that generated them.

## Consistency findings

- **Canonical boundary is self-consistent.** Physical Model v1.6 contains exactly
  32 canonical `CREATE TABLE` statements before its boundary marker and exactly 7
  bounded-extension `CREATE TABLE` statements after it (39 total, no duplicates).
  Verified programmatically by `tools/generate_physical_model_release.py` at
  generation time and independently re-verified by
  `backend/app/tests/test_canonical_metadata.py` and
  `tools/test_build_persistence_traceability.py` against the generated file on
  disk, not against the generator's own in-memory state.
- **ORM matches the canonical section exactly.** `canonical_metadata` (SQLAlchemy)
  has 32 tables / 373 columns matching physical model v1.6's canonical section
  column-for-column, table-for-table (`test_orm_tables_and_columns_match_frozen_physical_model`).
  Indexes match exactly (`test_indexes_match_frozen_physical_model`).
- **Traceability is complete.** `docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.6.json`
  traces all 373 canonical columns to an Enterprise Attribute Dictionary row; zero
  missing EAD traces (`missing_ead_traces: []`).
- **Bounded extensions are unchanged in substance.** The six CDD-012 runtime
  tables and the one CDD-013 audit table were column-for-column verified
  semantically identical between their two duplicated v1.5 representations before
  being deduplicated into v1.6's single, correctly-positioned copy. No column,
  type, default, constraint, or index was added, removed, or altered for any of
  the seven bounded-extension tables.
- **Migration matches physical model v1.6.** Alembic migration
  `0011_erm_tenant_and_evidence` (backend, applied to a disposable PostgreSQL 17
  instance) produces the identical composite-uniqueness and composite-foreign-key
  structure described by physical model v1.6 for `enterprise_entities`,
  `source_systems`, and `source_objects`, verified by direct `pg_constraint`
  inspection and by the backend's full test suite (224 passed).
- **Prior releases are untouched.** `git status --porcelain` on
  `architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql` and
  `architecture/released/v1.4/ECOM_Physical_Data_Model_v1_5.sql` shows zero
  changes; both retain their original checksums.

## Drift assessment

No unauthorized drift identified. The only content differences between v1.5 and
v1.6 are the two changes RFC-015 explicitly authorizes: tenant ownership on three
canonical tables, and bounded-extension layout deduplication with verified
semantic equivalence. No other capability, API, or runtime behavior is affected by
this release.

## Readiness

Backend verification for the tenant-foundation gate (migration up/down/up
determinism, ORM/canonical-metadata/traceability tests, full backend suite,
black/isort/ruff/mypy) is green at the time of this report. Frontend and Steward
API/UI work for Increment 3A depend on this release and have not yet begun.
