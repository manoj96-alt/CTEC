# CDD-022 Artifact Authorization Amendment — OQI2 Evidence Composite Uniqueness

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-022 (Governed Source Field-Value Evidence) — additively, narrowly, without reopening or reinterpreting CDD-022's identity model, immutability guarantees, or non-goals
**Requested by:** CDD-040 (OQI2 Multi-Source Quality Intelligence) §7, §49
**Precedent:** this repository's established discipline of never modifying a frozen governance artifact's authorized surface in place — every correction/extension is published as its own companion document (CDD-039-GR/GC/GM precedent, applied here to CDD-022)

## 1. Why this amendment exists

CDD-040 (OQI2) requires a database-level guarantee that a new cross-source evidence-association row cannot claim evidence belonging to a different `source_field_id` than the one its governed participant snapshot actually recorded (CDD-040 §49, Invariant II/V). This guarantee is achievable via a chained composite foreign key, but it requires the `field_value_evidence` table — currently governed exclusively by CDD-022 — to expose one additional composite uniqueness constraint beyond its existing primary key.

Per this repository's established governance discipline, CDD-040 alone does not have authority to modify CDD-022's persistence surface. This document is the explicit, narrow, separately-reviewable companion that grants it.

## 2. Exact authorized change

```sql
ALTER TABLE field_value_evidence
  ADD CONSTRAINT uq_field_value_evidence_id_source_field
  UNIQUE (field_value_evidence_id, source_field_id);
```

Applied inside migration `0021_oqi2_cross_source_consistency.py` (owned by the OQI2 Artifact Authorization), not a separate migration — the SQL change is authorized here; its execution is tracked there.

## 3. Why this is safe (verified, not assumed)

- **Purely additive.** No column is added, no data is mutated, no row is backfilled. `field_value_evidence_id` is already the table's primary key and therefore already unique on its own; composing it with the existing `source_field_id` column trivially satisfies the new constraint for every existing row with zero validation cost beyond Postgres's standard constraint-add check.
- **No CDD-022 identity change.** `field_value_evidence_id`'s derivation (`uuid5` of `source_field_id` + `source_record_reference` + `observed_representation` + `observed_at`, CDD-022 §6) is untouched. The four-input identity formula, the immutability guarantee (no UPDATE/DELETE path, CDD-022 §12), and the deliberate absence of a `(source_field_id, source_record_reference)` uniqueness constraint (CDD-022's own explicit design choice, §12) are all preserved exactly.
- **No CDD-022 application-code change.** `FieldValueEvidenceRepositoryImpl` retains exactly its three existing methods (`create_or_get_existing`, `get_by_id`, `get_by_source_field`) — this amendment touches only the ORM's `__table_args__`/migration, never the repository or domain model.
- **Precedented pattern.** Directly analogous to migration `0011_entity_resolution_tenant_and_evidence.py`'s own addition of `uq_source_systems_tenant_pk` — a composite unique constraint added purely to enable a future composite foreign key from elsewhere — except this instance is strictly simpler (no new column, no backfill, unlike the `0011` precedent which required adding and backfilling `tenant_id`).

## 4. What this amendment does NOT authorize

- No `tenant_id` column on `field_value_evidence` (CDD-022's transitive-tenant-resolution model is unchanged).
- No change to `FieldValueEvidence`'s Python domain class or its repository.
- No relaxation of immutability.
- No performance index (`(source_field_id, source_record_reference, received_at)` remains explicitly deferred to a future, separate CDD-022 hardening amendment — not this document, CDD-040 §59).

## 5. Verification obligation

OQI2's Artifact Authorization (§8, DB integrity tests) must include a real-Postgres test proving this exact constraint exists, rejects a mismatched `(field_value_evidence_id, source_field_id)` pair, and that all pre-existing OQI1 tests continue passing unmodified against the amended schema.

## 6. Authorization

This amendment is authorized for inclusion in migration `0021_oqi2_cross_source_consistency.py` exactly as specified in §2, and only as specified — no broader CDD-022 change is authorized by this document.
