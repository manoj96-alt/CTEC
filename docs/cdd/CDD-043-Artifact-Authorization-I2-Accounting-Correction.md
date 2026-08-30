# CDD-043 Artifact Authorization Amendment — OQI5-I2 Accounting Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-043 Artifact Authorization §3 (header) and §10 (final accounting), OQI5-I2 row
only — narrowly, mechanically, without adding, removing, or renaming any path, and without
reopening any architecture, invariant, or scope decision
**Precedent:** same class of correction as
`CDD-040-Artifact-Authorization-Migration-Revision-Length-Correction.md` and
`CDD-040-Artifact-Authorization-Finding-Type-Column-Width-Correction.md` — a narrow,
implementation-discovered arithmetic defect in an already-frozen governance document, corrected
via companion document rather than in-place edit

## 1. Discovered defect

At OQI5-I2 implementation-start, direct enumeration of the Artifact Authorization §3 OQI5-I2
table found it lists 9 *numbered* CREATE rows, then two *unnumbered* ("—") rows: one MODIFY
(`backend/app/application/oqi_remediation_service.py`, semantic/additive) and one CREATE
(`backend/app/tests/test_oqi_remediation_agent_i2.py`). Independent count of the table's own
rows: **CREATE = 10, MODIFY = 1, TOTAL = 11**.

The §3 header instead states:

```
CREATE = 9
MODIFY = 1
DELETE = 0
TOTAL  = 10
```

This undercounts CREATE by 1 — the unnumbered `test_oqi_remediation_agent_i2.py` CREATE row was
omitted from the header tally even though it is present in the table body.

§10's "Final accounting" repeats the same undercount for I2 (`CREATE 9 / MODIFY 1 / DELETE 0 /
TOTAL 10`) and additionally uses the shorthand "(+1 MODIFY at actual I2 implementation time, same
class)" for the mechanical migration-head bump. Read against §5's own explicit text, this
shorthand is misleading as a literal file count: §5 states I2's migration (`0025`) requires the
mechanical bump applied "to the same file set [as I1's own bump] plus
`test_oqi_remediation_i1.py`" — and "the same file set" is the **10-file list §5 itself names for
I1's own bump**, not one file. Adding `test_oqi_remediation_i1.py` makes the actual mechanical-bump
count **11 files**, not 1 — exactly the same pattern §5 already used for I1 itself, where "+1
MODIFY" in §10 stood for the 10-file mechanical class §5 spells out in full, not a literal single
file.

## 2. Independent re-verification against the real I1 merge commit

`git show --stat 432470a0838e4a8b61e70a41360d5dd58bafec73` (the real, merged OQI5-I1 commit)
confirms exactly the 10 mechanical migration-head files §5 names were the ones actually touched at
I1: `test_decision_engine.py`, `test_gate_v_agent_postgres.py`, `test_governance_engine.py`,
`test_knowledge_engine.py`, `test_oqi_business_rule_postgres.py`,
`test_oqi_cross_source_postgres.py`, `test_oqi_ontology_impact_postgres.py`,
`test_oqi_quality_postgres.py`, `test_persistence_integration.py`,
`test_runtime_architecture.py` — plus the new `test_oqi_remediation_i1.py` test file itself
(created, not mechanically bumped, at I1). This confirms both the defect and the derivation of
I2's 11-file mechanical set (the same 10 files, now already containing a bumped literal from I1,
plus `test_oqi_remediation_i1.py` itself needing its own bump when `0025` is added).

## 3. Semantic/mechanical overlap check

The single semantic MODIFY path, `backend/app/application/oqi_remediation_service.py`, is not a
member of the 11-file mechanical set (which is exclusively `backend/app/tests/*.py` files). No
overlap. The unique authorized path count is therefore a plain sum, not a deduplicated count.

## 4. Exact correction

```
§3 header, OQI5-I2 table:

CREATE = 9    → CREATE = 10   (includes the unnumbered test_oqi_remediation_agent_i2.py row)
MODIFY = 1    → MODIFY = 1    (unchanged — the single semantic/additive MODIFY row)
DELETE = 0    → DELETE = 0    (unchanged)
TOTAL  = 10   → TOTAL  = 11   (10 + 1)
```

```
§10 Final accounting, I2 line:

I2 (named, gated behind I1 closure): CREATE 9 / MODIFY 1 / DELETE 0 / TOTAL 10
                                       (+1 MODIFY at actual I2 implementation time, same class)

              →

I2 (named, gated behind I1 closure): CREATE 10 / MODIFY 1 / DELETE 0 / TOTAL 11
                                       (+11 MODIFY at actual I2 implementation time for the
                                        mechanical migration-head bump — the 10-file set §5
                                        names for I1's own bump, plus test_oqi_remediation_i1.py —
                                        same class as I1's own "+1 MODIFY" shorthand in this same
                                        section, which likewise expands to the 10-file list §5
                                        spells out, not a literal single file)
```

**Fully-realized, corrected I2 implementation-time accounting** (named-planning figure §3/§10
corrected, plus the mechanical bump already contemplated by §5 made arithmetically explicit, with
the overlap check in §3 above confirming no deduplication is needed):

```
CREATE = 10
MODIFY = 12   (1 semantic + 11 mechanical)
DELETE = 0
TOTAL  = 22   (unique authorized paths)
```

**Exact 11 mechanical migration-head paths** (each changes only its literal Alembic head-revision
string reference; no semantic behavior change is authorized in any of these 11 files under this
correction):

| # | Path | Why it changes mechanically |
|---|---|---|
| 1 | `backend/app/tests/test_decision_engine.py` | asserts/uses the current Alembic head revision literal; must track `0025_oqi5_agent_reasoning` |
| 2 | `backend/app/tests/test_gate_v_agent_postgres.py` | same — head-revision literal dependency |
| 3 | `backend/app/tests/test_governance_engine.py` | same |
| 4 | `backend/app/tests/test_knowledge_engine.py` | same |
| 5 | `backend/app/tests/test_oqi_business_rule_postgres.py` | same |
| 6 | `backend/app/tests/test_oqi_cross_source_postgres.py` | same |
| 7 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | same |
| 8 | `backend/app/tests/test_oqi_quality_postgres.py` | same |
| 9 | `backend/app/tests/test_persistence_integration.py` | same, plus the table-count literal bump `90 → 94` |
| 10 | `backend/app/tests/test_runtime_architecture.py` | same, plus `AUTHORIZED_CHANGED_PATHS`/firewall-list additions for the new I2 ORM classes |
| 11 | `backend/app/tests/test_oqi_remediation_i1.py` | created at I1 with a head-revision literal of its own; must track `0025_oqi5_agent_reasoning` exactly like its 10 siblings |

## 5. Scope of this correction (binding)

Changes only the *counted totals* in §3's header and §10's final-accounting line for OQI5-I2, and
makes explicit (rather than ambiguous shorthand) the mechanical-bump file count §5 already
specifies in full. It does **not** change:

- any path named in §3's table (no path added, removed, or renamed — the table body was already
  correct; only the header/summary arithmetic was wrong);
- §5's own file list or its "pre-authorized under the same mechanical migration-head consequence
  precedent" status — this correction only makes explicit the count that list already implies;
- §6's table-count expectations (`90 → 94`) — unaffected, since table count is derived from the 4
  new ORM tables named in §3 row 6, not from the file-row arithmetic corrected here;
- §7's enum-width verification, §8's revision-identifier correction, or §9's CDD-043 amendment —
  all unrelated and unaffected;
- any OQI5 architecture, invariant, firewall, human-authority boundary, source-write prohibition,
  or scope decision in CDD-043 or this Artifact Authorization;
- CDD-043 itself, or the original Artifact Authorization document — both remain byte-identical and
  unmodified; this is a companion correction only.

## 6. Why this is safe

Purely an arithmetic/summary correction reconciling a header total against its own table body and
against this same document's own explicit file-list text in §5, independently re-verified against
the real merged I1 commit. No new implementation surface is authorized beyond what §3's table and
§5's file list already, individually, specified — this correction only makes the *summary numbers*
agree with content that was already present and already authorized. No file is added to or removed
from the authorized set; no architecture or functional scope changes.

## 7. Effective governance semantics

Future OQI5-I2 implementation verification uses **CDD-043 + the original frozen Artifact
Authorization + this companion accounting correction** as the effective authorization set. The
original historical document is not rewritten: its table body already contained the tenth CREATE
artifact and the full 10-file mechanical precedent; the defect was in the summarized
arithmetic/counting, not in the underlying intended I2 functional scope.

## 8. Authorization

CDD-043 Artifact Authorization §3's OQI5-I2 header is corrected to `CREATE = 10 / MODIFY = 1 /
DELETE = 0 / TOTAL = 11`, and §10's I2 final-accounting line is corrected to `CREATE 10 / MODIFY 1
/ DELETE 0 / TOTAL 11 (+11 MODIFY at actual I2 implementation time for the mechanical
migration-head bump, per §5's own file list)`, effective immediately. OQI5-I2 implementation
proceeds using this corrected accounting: **CREATE = 10, MODIFY = 12 (1 semantic + 11 mechanical),
DELETE = 0, TOTAL = 22 unique authorized paths** at actual implementation time. No other file,
table, or decision in CDD-043 or its Artifact Authorization is affected. OQI5-I2 implementation
itself is not started by this document — it remains a governance-only correction.
