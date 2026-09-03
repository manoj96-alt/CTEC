# CDD-053 — Artifact Authorization Black-Formatting Reconciliation Amendment (OQI6-R2-GA2)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md` (OQI6-R2-GA — the
immediately preceding companion amendment, establishing that this correction class reuses CDD-053's own
number rather than consuming a new one); `CDD-040-Artifact-Authorization-Finding-Type-Column-Width-
Correction.md` / `CDD-040-Artifact-Authorization-Migration-Revision-Length-Correction.md` / `CDD-047-
Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md` (established repository precedent that a
single base CDD may accumulate multiple, sequential, narrow companion amendments as each is separately
discovered)
Classification: STATIC-FORMATTING AUTHORIZATION RECONCILIATION (mechanical, zero-semantic correction only;
does not reopen `CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-
Isolation-Correction.md` or `CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md`, both
of which remain FROZEN, byte-identical, unmodified)
Governs: `oqi6-r2/business-impact-evaluation-tenant-isolation` branch, PR #188, I-R1 candidate
`1ab029dd6757a41b27b72fd48359e4e6c67c979b`

## 1. Purpose

Independently re-examines the exact diff introduced by OQI6-R2-I-R1 (commit `1ab029d`) and determines
whether it exceeded the literal authorization of the first companion amendment
(`CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md`, commit `5329307`). It did: one
additional hunk — a pure Black line-wrap reflow of a pre-existing SQL statement in R2's own `test_r2ti10_
migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation` — was applied without being named in that
amendment's text. This document independently proves that hunk is zero-semantic, pre-existing (not
introduced by the migration-head correction itself), and required by CDD-053's own already-frozen §27
regression contract (`black --check` mandatory), and explicitly brings it inside the governed authorization
boundary rather than treating filename co-membership as sufficient authority.

## 2. Authoritative baseline — independently re-derived

`origin/main` and GitHub `main` both equal `0212eac0579c1abc0a801e3ebf45c56421313461`, unchanged since I-R1.
`CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md`
hash `abfa9f643ece58240b422c356c2a0b124aa6339ec705f45cbad1ab79fdb9186e` and `CDD-053-Artifact-Authorization-
Migration-Head-Regression-Amendment.md` hash `c180619f4acf71ccb3290d91a8626bed30d3945e5a3426ff657cb19e2c2faa77`
both independently re-confirmed byte-identical. Ancestry independently re-walked: `0212eac → 4646ada → be3def4
→ 5329307 → 1ab029d`, strictly linear.

## 3. Exact I-R1 diff, hunk-by-hunk classification

`git diff 5329307..1ab029d` touches exactly one file, `backend/app/tests/test_oqi_business_impact.py`, in
exactly three hunks:

```
Hunk A (import, line 19):    + from alembic.script import ScriptDirectory
                              AUTHORIZED — CDD-053-...-Migration-Head-Regression-Amendment.md §12 item 1

Hunk B (line 1302-1303):      test_ti10_...'s final assertion, literal -> dynamic ScriptDirectory resolution
                              AUTHORIZED — CDD-053-...-Migration-Head-Regression-Amendment.md §12 item 2

Hunk C (lines 1593-1597):     test_r2ti10_...'s DELETE statement, single-line -> Black 3-line wrap
                              NOT NAMED by the first amendment's text -- this document's subject
```

Hunk C, verbatim:
```python
-            text("DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"),
+            text(
+                "DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"
+            ),
```

## 4. Why the first amendment did not authorize Hunk C

`CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md` §11/§12 authorized exactly two
things: one new import, and the replacement of one named, specific assertion inside one named, specific
test function (`test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data`). Hunk C sits inside a
*different* test function (`test_r2ti10_...`), touches a different statement (a `DELETE`, not an `assert`),
and addresses a different defect class (formatter conformance, not stale-head semantics). Path co-membership
(both hunks are in the same file) is explicitly **not** treated as sufficient authority — Noetva's governance
convention authorizes by exact hunk/line, not by filename, exactly as CDD-053's own original Artifact
Authorization and both of its companion amendments already do throughout this entire OQI6-R1/R2 lineage.

## 5. Proof that Hunk C is pre-existing, not introduced by Hunk A/B

Independently re-verified against the exact pre-I-R1 commit (`5329307`, before any of this phase's edits):
```
$ black --check app/tests/test_oqi_business_impact.py   (run inside a clean worktree at 5329307)
would reformat app/tests/test_oqi_business_impact.py
--- app/tests/test_oqi_business_impact.py
+++ app/tests/test_oqi_business_impact.py
@@ -1589,11 +1589,13 @@
     ...
     connection.execute(
-            text("DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"),
+            text(
+                "DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"
+            ),
             {"evaluation_id": str(evaluation_id)},
         )
1 file would be reformatted.
```
Byte-for-byte identical to Hunk C in `1ab029d`. This conclusively proves the violation existed in `5329307`
(and, by extension, in `be3def4` — R2's own original structural implementation, authored under the original
CDD-053 before either amendment existed) and was never introduced by the migration-head correction itself.
Running `black --check` against the whole file at `5329307` reports **exactly** this one hunk — no other
formatting violation exists anywhere else in the file at that commit.

## 6. Proof of zero semantic difference (binding)

Comparing before/after character-for-character: the SQL string
`"DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"` is unchanged, verbatim;
the bound-parameter dictionary `{"evaluation_id": str(evaluation_id)}` is unchanged, verbatim; the enclosing
`connection.execute(...)` call, its two positional arguments, and their evaluation order are unchanged. Only
whitespace/line-break placement inside the `text(...)` call changes — Black's own line-length-100 wrapping
of a single argument that exceeded the column limit. This does **not** change: test inputs, assertions, SQL
semantics, migration revisions, tenant IDs, expected exceptions, control flow, fixture behavior, database
behavior, or any R1/R2 structural semantics. Independently re-confirmed by re-running the full R2-TI and R1-
TI matrix, byte-identical pass/fail results before and after this specific hunk (already reported in I-R1's
own §M-§Y, re-confirmed unaffected here).

## 7. Scope assessment

Hunk C is exactly a Black-required, zero-semantic formatting transformation of pre-existing R2 test content
(itself authored under the original CDD-053's own already-broader authorization for this file, not under
either narrower amendment). CDD-053's own §27 ("Full regression contract") already mandates `black --check`
as a precondition of R2's own completion — this hunk is required to satisfy an obligation the original,
still-frozen CDD-053 already imposed, not a new capability or semantic change. It is authorized here
explicitly, rather than retroactively waved through on the theory that "same file, therefore authorized."

## 8. GA2 invariant (binding)

```
A FORMATTER-ONLY TRANSFORMATION OF ALREADY-AUTHORIZED CONTENT, REQUIRED BY AN ALREADY-FROZEN
VERIFICATION CONTRACT, MUST STILL BE NAMED EXPLICITLY IN GOVERNANCE -- FILENAME CO-MEMBERSHIP
WITH AN AUTHORIZED HUNK IS NEVER, BY ITSELF, SUFFICIENT AUTHORITY.
```

## 9. Exact GA2 authorization (binding)

```
CREATE = 0
MODIFY = 1
DELETE = 0
```
```
MODIFY  backend/app/tests/test_oqi_business_impact.py

        Authorized narrowly to exactly Hunk C (§3): the Black-equivalent line-wrap reflow of the
        `text("DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id")`
        call inside test_r2ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation
        (lines ~1593-1597). No other line in this test function, no other test function, and no
        other hunk is authorized by this document. This authorization is additive to, and does not
        replace or re-open, the first amendment's own §12 authorization (Hunks A and B), which
        remains independently frozen and unchanged.
```

## 10. Structural-file preservation

`0042_oqi6_r2_evaluation_tenancy.py` and `oqi_business_impact.py` independently re-confirmed byte-identical
to `be3def4` (unchanged by I-R1, unchanged by this document).

## 11. R1 preservation

No change to any R1 assertion's meaning; Hunk B (the dynamic-head correction, governed by the first
amendment) is unchanged and unaffected by this document.

## 12. R2 preservation

No change to any R2 test's assertions, expected exceptions, or database behavior; Hunk C changes only the
lexical layout of one pre-existing SQL statement string's Python source representation.

## 13. R3 deferral (restated, unchanged)

```
OQI6-R3 — Current* Pointer Tenant-Isolation Correction
DEFERRED — FUTURE SEPARATELY GOVERNED PHASE
```

## 14. Production-orchestration deferral (restated, unchanged)

```
OQI4/OQI6/OQI5 production-orchestration trigger:
SEPARATE FUTURE GOVERNED INITIATIVE
```

## 15. Resumed-verification contract (binding on OQI6-R2-I-R2)

OQI6-R2-I-R2 does not need to re-apply Hunk C — commit `1ab029d` already contains exactly the byte sequence
this document authorizes (independently confirmed identical to Black's own deterministic output in §5-§6).
I-R2's task is to verify the final candidate's exact bytes against this now-complete governance record, not
to re-edit anything. I-R2 must independently re-establish, in full: both/all three governance-artifact
hashes (original CDD-053, first amendment, this amendment); the exact final candidate diff relative to main;
structural migration/ORM byte preservation; the corrected R1 test; the R1 tenant boundary; the R2 tenant
boundary; the complete R2-TI matrix; full backend regression; `black`/`isort`/`ruff`/`mypy`; frontend tests/
lint/typecheck/build; a **fresh** `--no-cache` Docker build (not waived merely because I-R1 already ran one);
Docker PostgreSQL tenant proofs; migration head/chain/table count; H5 regression; OQI6 regression; host/
Docker equivalence; the exact PR #188 head; and CI green. STOP for VM — do not merge.

## 16. Governance byte-integrity

Independently re-hashed immediately before this document's own publication and confirmed byte-identical:
```
abfa9f643ece58240b422c356c2a0b124aa6339ec705f45cbad1ab79fdb9186e
  CDD-053-Artifact-Authorization-OQI6-R2-Business-Impact-Evaluation-Dependency-Tenant-Isolation-Correction.md
c180619f4acf71ccb3290d91a8626bed30d3945e5a3426ff657cb19e2c2faa77
  CDD-053-Artifact-Authorization-Migration-Head-Regression-Amendment.md
```
Neither file, nor the structural implementation candidate, is modified by this document.

## 17. STOP conditions (binding, exhaustive)

STOP if: Hunk C is found to be semantic in any respect; a second, unauthorized hunk is discovered anywhere
in the diff; any path outside `test_oqi_business_impact.py` changed; the migration or ORM file changed; R1 or
R2 structural behavior changed; either prior governance hash changed; candidate ancestry differs materially;
main moved incompatibly; an R3 or production-orchestration change becomes necessary; a P0 appears; a
material new P1 appears.

## 18. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 0, P2 = 1 (R3 deferred), P3 = 1 (unauthorized-but-zero-semantic
                        formatter hunk present in the candidate, discovered by this document)
After this amendment:   P0 = 0, P1 = 0, P2 = 1 (R3 deferred), P3 = 0 (Hunk C is now explicitly authorized;
                        no re-edit is required since the candidate's existing bytes already match this
                        authorization exactly)
```

## 19. Allowed claim

```
An additional formatter-only transformation discovered during completion of the R2 verification contract
has been independently proven zero-semantic and explicitly authorized without changing R1 or R2 structural
behavior.
```

## 20. Forbidden claims

```
"R2 is closed."
"This amendment fixes an R2 structural defect."
"OQI6 is fully tenant-isolated."
```

## 21. Authorization

This document is approved and published as a standalone governance artifact, additive to and independent of
both prior CDD-053 documents, following the established repository precedent (§ header, Precedent) of a
single base CDD accumulating multiple sequential narrow companion amendments. Verification against the now-
complete governance record (this document plus its two predecessors) may proceed under `OQI6-R2-I-R2`.
