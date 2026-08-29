# CDD-041 — Artifact Authorization Mechanical Migration-Head Regression Amendment (OQI3-GA)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-036-Migration-Head-Regression-Assertion-Defect-Authorization.md` (original precedent
for authorizing exactly a mechanical migration-head literal correction as its own governance
artifact), `CDD-039-Artifact-Authorization-Migration-Regression-Amendment.md` (OQI1-GM, the direct
precedent for this exact class of gap — a new migration invalidates a fixed set of pre-existing
`SELECT version_num FROM alembic_version` literal assertions scattered outside the new capability's
own Artifact Authorization), `CDD-039-Artifact-Authorization-Concurrency-Hardening-Amendment.md`,
`CDD-039-Artifact-Authorization-Count-Correction.md` (separate-companion-document correction
pattern; an already-approved Artifact Authorization is never silently rewritten in place)
Classification: MIGRATION-REGRESSION AUTHORIZATION GAP (mechanical correction only; no
architectural, semantic, or scope change of any kind)

## 1. Purpose

Authorizes exactly six additional mechanical corrections discovered only at OQI3-I1 implementation
time. Migration `0022_oqi3_business_rule` became the new repository-wide Alembic head, which
invalidated six pre-existing, hardcoded `SELECT version_num FROM alembic_version` literal
assertions in files entirely outside CDD-041's own Artifact Authorization. This document authorizes
the identical class of correction — a single literal string replacement per file — for exactly
those six paths. It changes no architecture, no OQI3 semantic, no migration design, no concurrency
mechanism, and no behavior of any engine those six files test.

## 2. Context

OQI3-I1 implemented the 9-file subset of CDD-041's frozen 18-path Artifact Authorization required
for the BusinessRule foundation (domain, ORM, repository, migration, and I1-scoped tests), passed
every OQI3-I1-scoped test, and then ran the full backend regression suite as required diligence.
That full run surfaced exactly six failures outside the 18-path surface, all of the identical
`assert revision == "<previous-head>"` shape. OQI3-I1 disclosed this explicitly in its final report
as a judgment call rather than silently folding it into the CDD-041-authorized commit or hiding it —
the correct disciplined outcome, mirroring OQI1-GM's own origin story exactly. This amendment
resolves the disclosed gap formally rather than leaving it standing on an implementation report's
own judgment.

## 3. Independent re-verification (performed fresh against `be33a65ab039a8b5521e0eaabd02a0e1d393c432`
and OQI3-I1's actual pushed head `bd07ea453cb4961719eee23f2bc96645673a84fe`, not by trusting the
OQI3-I1 report's prose)

```
git diff --name-status be33a65..bd07ea4
```

produced exactly 15 changed paths, mechanically partitioned:

```
A. CDD-041-authorized (9 of the frozen 18):
   A  backend/app/domain/oqi_business_rule/__init__.py
   A  backend/app/domain/oqi_business_rule/rule.py
   A  backend/app/infrastructure/persistence/migrations/versions/0022_oqi3_business_rule.py
   A  backend/app/infrastructure/persistence/models/oqi_business_rule.py
   A  backend/app/infrastructure/persistence/oqi_business_rule_repository.py
   A  backend/app/tests/test_oqi_business_rule_domain.py
   A  backend/app/tests/test_oqi_business_rule_postgres.py
   M  backend/app/tests/test_persistence_integration.py   (row 18 of CDD-041 AA)
   M  backend/app/tests/test_runtime_architecture.py       (row 17 of CDD-041 AA)

B. The six unauthorized mechanical paths (this amendment's subject):
   M  backend/app/tests/test_decision_engine.py
   M  backend/app/tests/test_gate_v_agent_postgres.py
   M  backend/app/tests/test_governance_engine.py
   M  backend/app/tests/test_knowledge_engine.py
   M  backend/app/tests/test_oqi_cross_source_postgres.py
   M  backend/app/tests/test_oqi_quality_postgres.py

C. Any other unauthorized path: 0
```

Every one of the six Group-B diffs was inspected line-by-line and confirmed to be exactly one
logical-line change of the form:

```
-    assert revision == "0021_oqi2_cross_source"
+    assert revision == "0022_oqi3_business_rule"
```

(`test_oqi_cross_source_postgres.py` additionally updates one `alembic.command.upgrade(alembic_cfg,
"0021_oqi2_cross_source")` call target to `"0022_oqi3_business_rule"` in the same test, on the same
"advance to current head" semantic — two lines of the identical mechanical class, not two separate
concerns.) No assertion was weakened, no test was skipped/xfailed/deleted/renamed, no fixture
behavior changed, and no unrelated import or formatting changed in any of the six files.

## 4. Exhaustive fresh repository search

A parallel, independent search for every file querying the live `alembic_version` table
(`grep -rl "FROM alembic_version" backend/app/tests/`) found exactly the same seven files identified
by OQI1-GM plus the two OQI2-era additions, all now current:

```
test_decision_engine.py                    -> was "0021_oqi2_cross_source", now "0022_oqi3_business_rule" (THE GAP, this doc)
test_gate_v_agent_postgres.py               -> was "0021_oqi2_cross_source", now "0022_oqi3_business_rule" (THE GAP, this doc)
test_governance_engine.py                    -> was "0021_oqi2_cross_source", now "0022_oqi3_business_rule" (THE GAP, this doc)
test_knowledge_engine.py                      -> was "0021_oqi2_cross_source", now "0022_oqi3_business_rule" (THE GAP, this doc)
test_oqi_cross_source_postgres.py              -> was "0021_oqi2_cross_source" (x2), now "0022_oqi3_business_rule" (x2) (THE GAP, this doc)
test_oqi_quality_postgres.py                    -> was "0021_oqi2_cross_source", now "0022_oqi3_business_rule" (THE GAP, this doc)
test_persistence_integration.py                  -> already corrected by CDD-041's own row 18 (table-count literal, not migration-head)
test_institutional_relationship_tenant_migration_postgres.py
    -> asserts `current == PRE_MIGRATION_REVISION`, a symbolic constant scoped to an isolated,
       pinned historical fixture testing a specific historical migration transition in complete
       isolation from the live repository head — confirmed NOT a global-head assertion, NOT
       impacted by migration 0022, requires no correction (identical disposition to OQI1-GM §4).
```

## 5. Migration topology proof

```
backend/app/infrastructure/persistence/migrations/versions/0022_oqi3_business_rule.py:
    revision      = "0022_oqi3_business_rule"
    down_revision = "0021_oqi2_cross_source"
```

Confirmed: exactly one migration file declares `down_revision = "0021_oqi2_cross_source"` (no
competing branch); no migration file declares `down_revision = "0022_oqi3_business_rule"` (0022 is
genuinely the linear tip). The migration chain `0021 -> 0022` is the sole, uncontested topology.
Single Alembic head confirmed.

## 6. Answer required by this phase

> Are these exact six files the complete set of remaining executable test/code locations outside
> the existing authorization that incorrectly assumed `0021` remains the repository migration head
> after `0022`?

**YES**, per Section 3's exhaustive `git diff` partition (Group C = 0) and Section 4's independent
`grep`-based cross-check, which agree exactly.

## 7. Repository precedent for this exact class of gap

`CDD-039-Artifact-Authorization-Migration-Regression-Amendment.md` (OQI1-GM) is the direct
precedent: at OQI1 implementation time, a fifth pre-existing migration-head assertion
(`test_gate_v_agent_postgres.py`) was discovered outside OQI1's own 21-path authorization and
resolved via exactly this pattern — a narrow companion amendment naming the one path and the one
literal change, superseding the file-count accounting, changing nothing else. `CDD-040`'s own
original Artifact Authorization for OQI2 went further and *pre-emptively* enumerated this exact
mechanical-bump class by name in its initial 25-path table (rows 21–25:
`test_oqi_quality_postgres.py`, `test_knowledge_engine.py`, `test_gate_v_agent_postgres.py`,
`test_governance_engine.py`, `test_decision_engine.py` — independently confirmed present in
`docs/cdd/CDD-040-Ontology-Quality-Intelligence-Multi-Source-Quality-Intelligence-Artifact-Authorization.md`
lines 70–74). CDD-041's own Artifact Authorization omitted this pre-emptive enumeration for the
`0021 -> 0022` transition. `test_runtime_architecture.py`'s `AUTHORIZED_CHANGED_PATHS` registry
already lists all six of these files (confirmed present at lines 90–92, 631, 659, 683 of that file)
— this registry documents that these files are *expected to change* across gates in general, but it
is a test-internal allowlist guarding an unrelated "no unexpected file changed" assertion, not a
substitute for CDD Artifact Authorization. Precedent therefore supports both the rationale for this
correction and the conclusion that an explicit amendment — not silent reliance on the registry — is
the correct governance instrument, exactly as OQI1-GM already established.

## 8. Root-cause classification

```
Architectural defect:           NO
OQI3 semantic defect:           NO
Implementation logic defect:    NO
Authorization defect:           YES -- CDD-041's own Artifact Authorization did not enumerate the
                                 six pre-existing global-migration-head assertions that its own
                                 new migration (0022) necessarily invalidated, unlike CDD-040's
                                 original authorization, which did enumerate the equivalent five
                                 for the 0020 -> 0021 transition.
```

## 9. Architecture / product-scope / implementation-artifact impact

```
Product capability scope:  UNCHANGED
Architecture:               UNCHANGED
Schema:                       UNCHANGED
Migration:                     UNCHANGED (0022's own definition is untouched by this amendment)
OQI3 semantics:                   UNCHANGED
BusinessRule/binding/AST design:    UNCHANGED
Concurrency mechanism:                UNCHANGED
OQI1/OQI2/Gate V/Governance/Decision/Knowledge engine behavior: UNCHANGED
Test obligation:                        UNCHANGED IN SUBSTANCE (same assertions, corrected literal)
Regression coverage:                      CORRECTED

Named implementation path set: EXPANDS BY SIX PATHS (18 -> 24) -- an honest, precise statement, not
"unchanged": six additional pre-existing files are now part of the authorized OQI3 implementation
surface, exactly as OQI1-GM expanded 21 -> 22.
```

## 10. Exact new path authorization

```
MODIFY  backend/app/tests/test_decision_engine.py
MODIFY  backend/app/tests/test_gate_v_agent_postgres.py
MODIFY  backend/app/tests/test_governance_engine.py
MODIFY  backend/app/tests/test_knowledge_engine.py
MODIFY  backend/app/tests/test_oqi_cross_source_postgres.py
MODIFY  backend/app/tests/test_oqi_quality_postgres.py
```

## 11. Exact allowed change per path (binding, minimum only)

```
test_decision_engine.py:307
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"

test_gate_v_agent_postgres.py:95
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"

test_governance_engine.py:388
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"

test_knowledge_engine.py:305
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"

test_oqi_cross_source_postgres.py:237,239
    alembic.command.upgrade(alembic_cfg, "0021_oqi2_cross_source")
        -> alembic.command.upgrade(alembic_cfg, "0022_oqi3_business_rule")
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"

test_oqi_quality_postgres.py:190
    assert revision == "0021_oqi2_cross_source"  ->  assert revision == "0022_oqi3_business_rule"
```

No other line in any of these six files may change under this authorization. No engine behavior,
no domain semantics, no other assertion, and no docstring prose may be touched.

## 12. New 24-path accounting (binding, supersedes CDD-041 AA's original 18-path accounting for the
purpose of the OQI3 implementation lineage currently held on PR #167)

```
CREATE = 16   (unchanged -- identical to CDD-041 AA's original count)
MODIFY = 8    (was 2; +6 for the paths named in Section 10)
DELETE = 0
TOTAL  = 24
```

The original 18 named paths (CDD-041 Artifact Authorization §4, unamended) remain completely
unchanged, in the same order, with the same purposes. Paths 19–24 are exactly the six named in
Section 10 above. No wildcard, no implied file, no 25th path.

## 13. Provenance (binding — do not conflate historical authorization states)

```
Original CDD-041 Artifact Authorization (OQI3-G):  18 paths (16 CREATE / 2 MODIFY / 0 DELETE)
This companion amendment (OQI3-GA):                +6 paths (0 CREATE / 6 MODIFY / 0 DELETE)
Effective OQI3 implementation authorization:        24 paths (16 CREATE / 8 MODIFY / 0 DELETE)
```

CDD-041's original Artifact Authorization was not, and never was, a 24-path document. It remains
frozen exactly as published at 18 paths. This amendment is the sole source of the additional six.

## 14. Governance precedent followed

Exactly the same standalone-companion-document pattern as OQI1-GM (Migration Regression Amendment),
OQI1-GR (Concurrency Hardening Amendment), and OQI1-GC (Count Correction): a new, separate
governance file; the original CDD-041 and its Artifact Authorization remain byte-identical; direct
commit to `main` from the clean authoritative branch, with the OQI3 implementation branch
(`oqi3/business-rule-quality-intelligence`, PR #167) left entirely untouched by this governance
publication.

## 15. Governance byte-integrity

`CDD-041-Ontology-Quality-Intelligence-Business-Rule-Quality-Intelligence.md`
(`95536bfeb4039ca8ae166ffcb51ce868a61847af0c46f9c0ceba393977a0b289`) and
`CDD-041-Ontology-Quality-Intelligence-Business-Rule-Quality-Intelligence-Artifact-Authorization.md`
(`13daab67a5e7c9a9ef79f81754254d782c6e68702acabb1c4721d33ba9e61c5c`) were independently re-hashed
immediately before this document was written and confirmed byte-identical to their OQI3-G
publication values. All other pre-existing OQI governance (CDD-039 and its three amendments,
CDD-040 and its Artifact Authorization plus its four companions, CDD-022's OQI2 companion) was
independently re-hashed and confirmed byte-identical. This document is the sole new artifact.

## 16. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 0, P2 = 1 (Artifact Authorization incompleteness -- this gap),
                        P3 = 0 (no OQI3-I1-introduced P3; the four inherited OQI P3s are unaffected
                        by this purely-mechanical correction)
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (unchanged inherited-P3 register carried
                        forward separately, not restated here since this amendment touches none
                        of them)
```

## 17. Implementation readiness / closure

```
OQI3-I1 implementation authorization is now internally consistent and complete: YES

AUTHORIZED CREATE = 16
AUTHORIZED MODIFY = 8
AUTHORIZED DELETE = 0
AUTHORIZED TOTAL  = 24
```

No OQI3 implementation file, migration, test, frontend, or API file is created or modified by this
governance-only amendment. PR #167, holding the already-completed 15-file implementation head
`bd07ea453cb4961719eee23f2bc96645673a84fe`, is untouched by this publication. Its base will drift
to this amendment's commit once merged into `main`'s history, exactly as OQI2's governance-then-PR
sequencing already established; this is base drift, not a branch modification, and does not require
syncing/rebasing the implementation branch.

## 18. Authorization

This amendment is approved and published as a standalone governance artifact, following the
established repository precedent of never silently rewriting an already-approved Artifact
Authorization in place. OQI3-I1 is formally closed against this corrected 24-path,
16-CREATE/8-MODIFY/0-DELETE authorization. OQI3-I2 may be authorized separately by the Product
Owner following review of this document.
