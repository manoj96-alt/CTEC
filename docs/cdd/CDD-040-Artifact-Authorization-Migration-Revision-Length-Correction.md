# CDD-040 Artifact Authorization Amendment — Migration Revision Length Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-040 §53 (Migration) and its Artifact Authorization §4 (row 11) and §7 — narrowly, mechanically, without reopening any architecture, identity formula, or persistence-schema decision
**Precedent:** this repository's established discipline of never modifying a frozen governance artifact's authorized surface in place — every correction is published as its own companion document (CDD-039-GC's arithmetic correction is the direct precedent for this class of narrow, mechanical, implementation-discovered correction)

## 1. Discovered defect

During OQI2-I implementation, running the authorized migration against real PostgreSQL failed:

```
psycopg.errors.StringDataRightTruncation: value too long for type character varying(32)
UPDATE alembic_version SET version_num='0021_oqi2_cross_source_consistency' ...
```

CDD-040 §53 and its Artifact Authorization §4/§7 froze the migration revision identifier as `"0021_oqi2_cross_source_consistency"` — **34 characters**. Alembic's `alembic_version.version_num` column is `VARCHAR(32)` (pre-existing, unmodified schema — every prior revision id in this repository is ≤29 characters for exactly this reason, e.g. `0019_gate_v_agent_resolution`, `0020_oqi1_quality_foundation`). The frozen identifier is therefore technically infeasible as written.

## 2. Exact correction

```
CDD-040 §53, Artifact Authorization §4 row 11, §7:

revision      = "0021_oqi2_cross_source_consistency"   (34 chars, INFEASIBLE)
              →  "0021_oqi2_cross_source"               (22 chars, CORRECTED)

down_revision = "0020_oqi1_quality_foundation"          (unchanged)
```

## 3. Scope of this correction (binding)

This amendment changes **only** the literal revision-id string, everywhere it appears as a value (the migration file's `revision` assignment and every test assertion comparing against it). It does **not** change:

- the migration **filename** (`0021_oqi2_cross_source_consistency.py` — unchanged, still exactly the path named in the Artifact Authorization's file table);
- `down_revision`, table names, column names, constraints, or any persistence schema decision in CDD-040 §52;
- any identity formula, concurrency ordering, epistemic rule, or firewall in CDD-040;
- the exact 25-file CREATE/MODIFY/DELETE accounting in the Artifact Authorization (§4–§6 remain otherwise unchanged — only the literal string value asserted/assigned in rows 11 and 20–25 changes).

## 4. Why this is safe

Purely a string-literal rename of an internal, opaque, deterministic identifier. No semantic content, no persisted data, no identity derivation, and no other governance decision depends on the identifier's exact characters — only its uniqueness and its role as the head-chain link, both preserved exactly.

## 5. Authorization

CDD-040's migration revision identifier is corrected to `"0021_oqi2_cross_source"` effective immediately. OQI2-I implementation resumes using this corrected identifier. No other file, table, or decision in CDD-040 or its Artifact Authorization is affected.
