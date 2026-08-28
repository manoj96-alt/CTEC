# CDD-039 — Artifact Authorization Count Correction (OQI1-GC)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md` (separate-companion-
document correction pattern; an already-approved Artifact Authorization is never silently rewritten
in place), `CDD-028-Ontology-Modeling-Read-Authority-Artifact-Authorization-Amendment.md`,
`CDD-036-Migration-Head-Regression-Assertion-Defect-Authorization.md`
Classification: GOVERNANCE ARITHMETIC / TRANSCRIPTION DEFECT (mechanical correction only; no
architectural, semantic, or scope change of any kind)

## 1. Purpose

Corrects a self-contradiction discovered inside the already-approved `CDD-039-...-Artifact-
Authorization.md` (v1.0) between its own named-path allowlist table (§4) and its own summary
arithmetic beneath that table: the table names **21** distinct implementation paths; the summary
block beneath it states `TOTAL = 20`. This document establishes, with independent mechanical proof,
that the table is authoritative and the arithmetic was a transcription error, and supersedes every
numeric restatement of that error across both the original Artifact Authorization and the
Concurrency Hardening Amendment. It changes no named path, no semantics, and no implementation
scope.

## 2. Context

OQI1-I, authorized to begin implementation, halted before creating a branch or touching any file
upon mechanically extracting the original Artifact Authorization's §4 table and finding 21 named
rows (16 `CREATE`, 5 `MODIFY`) against a summary block reading `AUTHORIZED_NEW = 15, ... TOTAL
IMPLEMENTATION SURFACE = 20`. This is exactly the correct, disciplined response required by that
document's own §15 stop conditions and by the governing standard applied throughout this entire OQI
lineage: an internal contradiction in frozen governance blocks implementation until resolved, and is
never silently worked around.

## 3. Independent mechanical re-verification

Re-extracted directly from `docs/cdd/CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-
Artifact-Authorization.md` §4, by machine parse of every `| \`path\` | OPERATION |` table row
(not transcribed from any prior report):

```
01. CREATE backend/app/domain/oqi/__init__.py
02. CREATE backend/app/domain/oqi/quality_rule.py
03. CREATE backend/app/domain/oqi/evaluation.py
04. CREATE backend/app/domain/oqi/finding.py
05. CREATE backend/app/infrastructure/persistence/models/oqi_quality_rule.py
06. CREATE backend/app/infrastructure/persistence/models/oqi_quality_evaluation.py
07. CREATE backend/app/infrastructure/persistence/models/oqi_quality_finding.py
08. CREATE backend/app/infrastructure/persistence/migrations/versions/0020_oqi1_quality_foundation.py
09. CREATE backend/app/infrastructure/persistence/oqi_quality_rule_repository.py
10. CREATE backend/app/infrastructure/persistence/oqi_quality_evaluation_repository.py
11. CREATE backend/app/application/oqi_quality_evaluation_service.py
12. CREATE backend/app/tests/test_oqi_quality_rule_domain.py
13. CREATE backend/app/tests/test_oqi_quality_evaluation_domain.py
14. CREATE backend/app/tests/test_oqi_quality_evaluation_service.py
15. CREATE backend/app/tests/test_oqi_quality_postgres.py
16. CREATE backend/app/tests/test_oqi_provenance.py
17. MODIFY backend/app/tests/test_runtime_architecture.py
18. MODIFY backend/app/tests/test_decision_engine.py
19. MODIFY backend/app/tests/test_governance_engine.py
20. MODIFY backend/app/tests/test_knowledge_engine.py
21. MODIFY backend/app/tests/test_persistence_integration.py
```

Verified: 21 rows, 21 unique paths (zero duplicates), 16 `CREATE`, 5 `MODIFY`, 0 `DELETE`. Every
`CREATE` path is confirmed absent from current authoritative main; every `MODIFY` path is confirmed
present on current authoritative main — exactly the expected shape for a not-yet-implemented CREATE
set and a pre-existing MODIFY set.

## 4. Root cause

The original summary arithmetic (`AUTHORIZED_NEW = 15`) undercounts the table by exactly one. The
most likely mechanical origin: `backend/app/domain/oqi/quality_rule.py`, `evaluation.py`, and
`finding.py` were mentally grouped as "the three domain files" while drafting the summary, silently
dropping `backend/app/domain/oqi/__init__.py` — the package-marker file — from that mental count
even though it is, correctly, its own separate, necessary, named row in the table. A second,
independent instance of the same class of error was found in the table itself: the
`test_runtime_architecture.py` row's own prose says "Add the **14** new paths above to
`AUTHORIZED_CHANGED_PATHS`" — also wrong; the correct count of CREATE rows preceding it (rows 1–16)
is **16**, matching the direct precedent set by CDD-037's own Artifact Authorization, whose
equivalent row reads "Add the 13 new/changed paths above," where 13 exactly equals that document's
own `AUTHORIZED_NEW`. Both errors are simple, independent arithmetic slips made while summarizing an
already-correct, already-complete table — not evidence of a missing or extra named path.

## 5. Package-marker precedent (decisive)

Direct inspection of CDD-037's (Gate V's) own Artifact Authorization confirms `backend/app/domain/
gate_v/__init__.py` and `backend/app/api/gate_v/__init__.py` are each counted as full, independent
members of that document's own `AUTHORIZED_NEW = 13`. There is no repository convention, in this
document or any precedent, that excludes package-marker files from the authorized-artifact count.
`backend/app/domain/oqi/__init__.py` is, and was always intended to be, a genuine, load-bearing,
counted member of the authorized `CREATE` set — the `backend/app/domain/oqi/` package cannot exist
or be importable without it.

## 6. Intent determination — Interpretation A confirmed, Interpretation B refuted

**Interpretation A** (the named 21-path table is authoritative; the 15/20 summary is a transcription
error) is confirmed. **Interpretation B** (a 20-path authorization was intended and one path was
accidentally added to the table) is refuted:

- Every one of the 16 named `CREATE` paths serves a distinct, non-redundant, independently necessary
  purpose already justified in CDD-039's own governance (domain package marker; three cohesive
  domain files grouped deliberately to avoid "unnecessary one-class-per-file fragmentation," per the
  original OQI1-G mandate; three persistence-model files; one migration; two repositories; one
  application service; six test files each covering a distinct obligation named in CDD-039 §43).
- No candidate path is redundant with, or mergeable into, another without violating that same
  already-approved cohesion reasoning.
- `__init__.py` cannot be dropped without leaving `backend/app/domain/oqi/` an invalid, unimportable
  Python package — mechanically required, not optional.
- No repository precedent (Gate S, Gate V, Gate W) ever treats a package-marker file as excluded
  from its own authorized-artifact count.

Therefore the correction is arithmetic-only: the named path set is unchanged and complete at 21
paths; only the numbers describing it were wrong.

## 7. Architectural impact

**NONE.** No OQI domain, persistence, service, repository, test-obligation, migration design,
concurrency mechanism, firewall, or non-goal is touched, reopened, or reinterpreted by this
document.

## 8. Scope impact

**NONE.** No 22nd path is introduced. No named path is removed, renamed, or reassigned between
`CREATE`/`MODIFY`/`DELETE`. The complete and exclusive OQI1 implementation authorization remains
**exactly** the 21 paths enumerated in §3 above.

## 9. Exact correction (binding, supersedes every prior numeric restatement)

```
Superseded (transcription error, both documents below):
    AUTHORIZED_NEW    = 15
    AUTHORIZED_CHANGE = 5
    AUTHORIZED_DELETE = 0
    TOTAL IMPLEMENTATION SURFACE = 20

Corrected (binding):
    AUTHORIZED_NEW    = 16
    AUTHORIZED_CHANGE = 5
    AUTHORIZED_DELETE = 0
    TOTAL IMPLEMENTATION SURFACE = 21
```

This corrected accounting supersedes, without editing them, every one of the following locations
where the erroneous arithmetic appears:

**In `CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-Artifact-Authorization.md`
(v1.0, byte-identical, not edited):**
- §4 summary block: `AUTHORIZED_NEW = 15` / `TOTAL IMPLEMENTATION SURFACE = 20` → read as `16` / `21`.
- §4, `test_runtime_architecture.py` row: "Add the 14 new paths above" → read as "the 16 new paths
  above" (rows 1–16 of §3's list).
- §16 (Acceptance criteria) item 1: "Exact 20-file diff: CREATE=15, MODIFY=5, DELETE=0." → read as
  "Exact 21-file diff: CREATE=16, MODIFY=5, DELETE=0."
- §17 (Implementation PR strategy): "containing exactly the 20 authorized files" → read as "21
  authorized files."
- §19 (Closure criteria): "contains exactly the 20 authorized files" → read as "21 authorized
  files."

**In `CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md` (v1.0, byte-identical, not
edited):**
- §15 (Implementation file budget): `CREATE = 15` / `TOTAL = 20` → read as `CREATE = 16` / `TOTAL =
  21`.
- §17 (Authorization, closing sentence): "any of the 20 authorized files" → read as "any of the 21
  authorized files."
- §10 (Comparison matrix, Option D row) contains one narrative, non-normative mention of "widens
  20-file budget" as color explaining why Option D was rejected; this is descriptive prose about a
  now-superseded baseline number, not a live authorization statement, and required no correction to
  preserve its meaning — Option D remains rejected for the same reasons regardless of the exact
  baseline count.

## 10. GR amendment interaction

This correction does not alter, reopen, or in any way affect the concurrency mechanism OQI1-GR
selected and froze:

```
SELECT pg_advisory_xact_lock(hashtextextended(:identity, 1))
```

`oqi_quality_evaluation_repository.py` (path 10 in §3) remains the exact same authorized path,
implementing the exact same mechanism; only the document-wide file-count arithmetic referencing it
is corrected here.

## 11. Governance byte-integrity

`CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation.md`, `CDD-039-Ontology-Quality-
Intelligence-Deterministic-Foundation-Artifact-Authorization.md`, and `CDD-039-Artifact-
Authorization-Concurrency-Hardening-Amendment.md` all remain byte-identical to their prior
publication state. This document is the sole new artifact.

## 12. Twenty adversarial accounting checks

1. Exactly 21 unique named paths? — Yes (§3, verified by machine dedup).
2. Exactly 16 CREATE? — Yes.
3. Exactly 5 MODIFY? — Yes.
4. Exactly 0 DELETE? — Yes.
5. Is `__init__.py` explicitly counted? — Yes, row 1, always was.
6. Does Gate V precedent count package markers? — Yes, confirmed directly (§5).
7. Is every CREATE path currently absent on main? — Yes, verified by direct filesystem check.
8. Does every MODIFY path currently exist on main? — Yes, verified by direct filesystem check.
9. Is any path duplicated? — No.
10. Is any wildcard present? — No; every path is named exactly.
11. Is any implementation path implied but unnamed? — No.
12. Does migration 0020 have exactly one authorized path? — Yes, row 8.
13. Are all six OQI test files counted? — Yes, rows 12–16 plus row 8's migration is separate; the
    six test files are rows 12, 13, 14, 15, 16, and the MODIFY row 17 (architecture regression) —
    matching CDD-039 §43's full test-obligation set.
14. Are all persistence/domain/service/repository files counted? — Yes: 4 domain (rows 1–4), 3
    persistence models (rows 5–7), 1 migration (row 8), 2 repositories (rows 9–10), 1 application
    service (row 11).
15. Does the correction change concurrency? — No.
16. Does the correction change schema? — No.
17. Does the correction change test obligations? — No.
18. Does the correction change architecture? — No.
19. Does the correction expand scope beyond the already-named table? — No; the named set is
    unchanged, only its arithmetic description is corrected.
20. Could a future implementer unambiguously determine the exact authorized path set and count from
    this document plus the original AA? — Yes: 21 named paths, 16 CREATE / 5 MODIFY / 0 DELETE,
    with every prior contradictory number explicitly superseded above.

No ambiguity found.

## 13. P0/P1/P2/P3

```
Before this correction: P1 = 1 (contradictory authorization blocking implementation)
After this correction:  P0 = 0, P1 = 0, P2 = 0, P3 = 1
```

The retained P3 is unchanged and unrelated to this correction: the already-accepted, already-
documented theoretical 64-bit `pg_advisory_xact_lock` collision characteristic frozen in the
Concurrency Hardening Amendment §16. This correction neither eliminates nor reclassifies it.

## 14. Implementation readiness

```
OQI1 implementation authorization is now internally consistent: YES

AUTHORIZED CREATE = 16
AUTHORIZED MODIFY = 5
AUTHORIZED DELETE = 0
AUTHORIZED TOTAL  = 21
```

The correction from 20 to 21 does **not** represent a new implementation artifact. It corrects the
arithmetic describing the already-authorized 21-path named set that existed, unchanged, in the
original Artifact Authorization's own table since OQI1-G.

## 15. Authorization

This correction is approved and published as a standalone governance artifact, following the
established repository precedent of never silently rewriting an already-approved Artifact
Authorization in place. OQI1 implementation may resume against the corrected 21-path, 16-CREATE/
5-MODIFY/0-DELETE authorization once the Product Owner separately re-authorizes resumption of
OQI1-I.
