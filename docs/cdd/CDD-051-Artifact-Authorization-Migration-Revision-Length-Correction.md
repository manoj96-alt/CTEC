# CDD-051 Artifact Authorization Amendment — Migration Revision Length Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-051 §28 (Migration strategy) and its Artifact Authorization §2 (row 9) and §7 — narrowly, mechanically, without reopening any architecture, identity formula, or persistence-schema decision
**Precedent:** this repository's established discipline of never modifying a frozen governance artifact's authorized surface in place — every correction is published as its own companion document. Direct precedent: `CDD-040-Artifact-Authorization-Migration-Revision-Length-Correction.md` (identical defect class, OQI2-I).

## 1. Discovered defect

During OQI-H5-I1 implementation, running the authorized migration chain against real PostgreSQL failed:

```
sqlalchemy.exc.DataError: (psycopg.errors.StringDataRightTruncation) value too long for type character varying(32)
[SQL: UPDATE alembic_version SET version_num='0040_oqi_h5_timeliness_evaluation' WHERE alembic_version.version_num = '0039_oqi_h5_timeliness_policy']
```

CDD-051 §28 and its Artifact Authorization §2 (row 9) / §7 froze the second migration's revision identifier as `"0040_oqi_h5_timeliness_evaluation"` — **34 characters**. Alembic's `alembic_version.version_num` column is `VARCHAR(32)` (pre-existing, unmodified schema — the same constraint CDD-040's own amendment already documented). The frozen identifier is therefore technically infeasible as written, identical in kind to the CDD-040 precedent.

`"0039_oqi_h5_timeliness_policy"` (30 characters) is unaffected and requires no correction.

## 2. Exact correction

```
CDD-051 §28, Artifact Authorization §2 row 9, §7:

revision      = "0040_oqi_h5_timeliness_evaluation"   (34 chars, INFEASIBLE)
              →  "0040_oqi_h5_timeliness_eval"          (27 chars, CORRECTED)

down_revision = "0039_oqi_h5_timeliness_policy"         (unchanged)
```

## 3. Scope of this correction (binding)

This amendment changes **only** the literal revision-id string, everywhere it appears as a value (the migration file's `revision` assignment). It does **not** change:

- the migration **filename** (`0040_oqi_h5_timeliness_evaluation.py` — unchanged, still exactly the path named in the Artifact Authorization's file table, mirroring CDD-040's own precedent exactly);
- `down_revision`, table names, column names, constraints, or any persistence schema decision in CDD-051 §8/§28/§29;
- any identity formula, concurrency ordering, epistemic rule, or firewall in CDD-051;
- the exact CREATE/MODIFY/DELETE accounting in the Artifact Authorization (§1–§5 remain otherwise unchanged — only the literal string value assigned in row 9 and the migration table in §7 changes).

## 4. Why this is safe

Purely a string-literal rename of an internal, opaque, deterministic identifier. No semantic content, no persisted data, no identity derivation, and no other governance decision depends on the identifier's exact characters — only its uniqueness and its role as the head-chain link, both preserved exactly.

## 5. Authorization

CDD-051's second migration revision identifier is corrected to `"0040_oqi_h5_timeliness_eval"` effective immediately. OQI-H5-I1 implementation resumes using this corrected identifier. No other file, table, or decision in CDD-051 or its Artifact Authorization is affected.
