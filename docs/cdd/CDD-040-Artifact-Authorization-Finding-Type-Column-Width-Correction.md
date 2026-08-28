# CDD-040 Artifact Authorization Amendment — Finding-Type Column Width Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-040 §52 (`quality_comparison_findings` schema) and its Artifact Authorization §4 (row 6, `models/oqi_cross_source_finding.py`) — narrowly, mechanically, without reopening the Finding taxonomy (§31), any identity formula, or any other persistence-schema decision
**Precedent:** same class of correction as `CDD-040-Artifact-Authorization-Migration-Revision-Length-Correction.md`, published moments earlier in this same implementation phase

## 1. Discovered defect

During OQI2-I implementation, inserting a `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` Finding against real PostgreSQL failed:

```
psycopg.errors.StringDataRightTruncation: value too long for type character varying(32)
INSERT INTO quality_comparison_findings (..., finding_type, ...) VALUES (...)
```

CDD-040 §52 froze `quality_comparison_findings.finding_type` as `String(32)`, mirroring OQI1's own `quality_findings.finding_type` column width. But CDD-040 §14/§31 also froze the literal Finding-type name `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` — **39 characters** — which does not fit in that width. The shorter sibling type, `CROSS_SOURCE_VALUE_CONFLICT` (27 characters), fits without issue.

## 2. Why this cannot affect any existing OQI1 table

`quality_rules.finding_type` (OQI1's own, unmodified, frozen `VARCHAR(32)` column) can **never** be asked to store this value: `CDD-040 §14`'s `_ALLOWED_COMBINATIONS` closed coupling table admits exactly one row for `QualityDimension.CONSISTENCY` — `(CONSISTENCY, CROSS_SOURCE_VALUE_CONFLICT, None)` — and `validate_rule_shape` rejects any other combination before construction or persistence. `CROSS_SOURCE_PARTICIPANT_VALUE_MISSING` is computed only at evaluation time (CDD-040 §29) and is only ever written to the new `quality_comparison_findings.finding_type` column. This correction therefore touches **only** a table this same CDD-040 document introduces — no OQI1 table, column, or constraint is affected.

## 3. Exact correction

```
CDD-040 §52, quality_comparison_findings:

finding_type   String(32)   (INFEASIBLE for CROSS_SOURCE_PARTICIPANT_VALUE_MISSING, 39 chars)
             →  String(64)   (CORRECTED -- matches this table's own participant_role
                              precedent already frozen at 64 in the sibling
                              quality_comparison_evaluation_participants table, §52)
```

No other column, table, index, or constraint changes.

## 4. Scope of this correction (binding)

Changes only the declared width of `quality_comparison_findings.finding_type` (migration column definition and its ORM `Mapped[str] = mapped_column(String(64), ...)`). Does not change: the Finding taxonomy names themselves (§31), any identity formula, any other table in §52, or the exact 25-file CREATE/MODIFY/DELETE accounting in the Artifact Authorization (only the internal content of already-authorized path `models/oqi_cross_source_finding.py` and the migration file changes -- no new or removed file).

## 5. Authorization

`quality_comparison_findings.finding_type` is corrected to `String(64)` effective immediately. OQI2-I implementation resumes using this corrected width.
