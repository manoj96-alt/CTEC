# CDD-084 — Artifact Authorization H6-G-R1 Frontend Test-Path and U19 Correction Amendment (OQI-H6-G-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (the direct
precedent for this exact governance shape: a real-runtime/adversarial-verification phase discovers a genuine
gap outside the scope any prior phase's own Artifact Authorization anticipated, closed by a narrow,
standalone, additive amendment rather than by silently rewriting an already-verified candidate or folding an
out-of-scope correction into an already-stopped candidate commit); `CDD-049-Artifact-Authorization-H3-VM-R1-CI-Type-Safety-Amendment.md`
(further precedent for the same defect class)
Classification: GOVERNANCE-PROCESS / PATH-AUTHORIZATION GAP (two already-written, already-verified-benign
test files retroactively authorized) + TEST-MATRIX-COMPLETENESS CORRECTION (one mandatory matrix item's
proof mechanism corrected to match actual frozen H6 architecture; zero production/test code change)
Governs: `oqi-h6/uniqueness` branch, stopped candidate `3c8d942ab1dec2b6239e502569ce1489c28127ec`

## 1. Purpose

Authorizes the exact, narrow, additive correction of the two governance-compliance gaps OQI-H6-VM
independently found while adversarially verifying the stopped H6 candidate `3c8d942ab1dec2b6239e502569ce1489c28127ec`,
and reported as:

```
OQI-H6-VM: STOPPED BEFORE MERGE — GOVERNANCE CORRECTION REQUIRED — two changed paths
(frontend/tests/oqi-finding-detail.test.tsx, frontend/tests/oqi-findings-workspace.test.tsx) are not
authorized by CDD-084's Artifact Authorization §4, and AA §12's mandatory I1 test-matrix item U19 was never
implemented; both require a narrow governance amendment before merge, per the AA's own binding
"STOP and return for amendment" rule
```

**CDD-084 itself, and its own original companion Artifact Authorization, are not modified, not reopened, and
remain FROZEN exactly as originally published.** This amendment closes a governance-process gap the original
Artifact Authorization's own text already anticipated and named the required response to ("if implementation
discovers a genuine need to touch an unnamed path, implementation must STOP and return for a narrow
amendment") — implementation discovered the need and did not stop. It also corrects one mandatory
test-matrix item's proof mechanism to match H6's actual, independently-traced architecture, rather than an
assumed runtime path that does not exist anywhere in this codebase, for any quality dimension.

## 2. Context — independently re-derived this phase, not merely trusted from VM's report

This session independently re-verified both findings before writing this amendment, against the unmoved,
unmerged candidate `3c8d942ab1dec2b6239e502569ce1489c28127ec` (`git rev-parse HEAD` reconfirmed;
`git merge-base --is-ancestor 3c8d942... origin/main` reconfirmed NOT an ancestor; `origin/main` reconfirmed
unchanged at `0e2223d26697b53d84478780b814102c2bb571cb`):

**Finding #1 reproduction.** `grep`-confirmed both paths are absent from
`CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness-Artifact-Authorization.md` in its entirety. `git diff`
of both files, `adfc31fa30eef6a8624778afd07dd21aa2a692ca..3c8d942ab1dec2b6239e502569ce1489c28127ec`,
independently read in full (not summarized): `frontend/tests/oqi-findings-workspace.test.tsx` gains one
`within` import and one new `it()` block, purely appended after the file's four pre-existing tests, zero of
which are touched. `frontend/tests/oqi-finding-detail.test.tsx` gains two new `vi.mock()` calls (for
`@/lib/auth/browser-session`/`@/lib/auth/config`, mocking the exact two functions the already-authorized
`fetchUniquenessCandidateDetail` production helper calls) and one new `describe` block of four `it()` tests,
purely appended after the file's existing ~130 tests, zero of which are touched. Both files import and render
the real, unmodified `FindingsPage`/`FindingDetailPage` production components — never duplicated fake
markup. No existing fixture value, mock, or assertion in either file is altered.

**Finding #2 reproduction.** `grep`-confirmed AA §12 binds U1-U20 on the three new I1 test files; `grep`
across `test_oqi_h6_uniqueness_crown.py`, `test_oqi_h6_uniqueness_authorization_and_tenant_isolation.py`,
and `test_oqi_uniqueness_domain.py` for `u19`/`U19`/`agent`/`Agent`/`§34` returns zero matches. U19 was never
implemented.

## 3. Root-cause analysis (independently re-derived)

**Finding #1 — implementation fail-closed process violation.** I2's own final report explicitly disclosed
discovering that the new UNIQUENESS frontend surface (filter option, pair-detail panel) had zero dedicated
component-level test coverage, and — motivated by the same "no interactive browser available" constraint
that made component tests the best available product-verification evidence — added the tests directly
rather than stopping for a narrow amendment, exactly as CDD-084 AA's own binding text required
("Any path not named below is unauthorized... implementation must STOP and return for a narrow
amendment"). The content is sound (§4 below); the process was not followed.

**Finding #2 — mandatory-matrix item written against an assumed runtime path never independently confirmed
to exist.** AA §12's U19 text ("agent-role investigation of a candidate → zero graph/entity mutation")
mirrors CDD-046 §34's own established test precedent for OQI1-3, which presumes a real, production-reachable
agent-investigation *execution* path exists to adversarially attack. Neither H6-DR, H6-G, H6-I1, nor H6-I2
independently confirmed, against the real repository, that such an execution path is actually
production-reachable for *any* dimension — H6-I1 assumed the CDD-046 §34 precedent transplanted cleanly, as
INTEGRITY's and TIMELINESS's own equivalent, unmodified matrix items had. §9 below documents this session's
own independent trace: it does not.

```
CDD-084 §29 architecture ("existing three agent roles remain sufficient... unmodified"):  SOUND — confirmed;
    H6 adds zero agent code, zero agent role, zero agent call site anywhere
Assumed U19 runtime path (an executable agent-investigation RUN against an H6 candidate):  DOES NOT EXIST —
    not for H6, not for any dimension; OqiRemediationAgentService (the sole class containing the one
    execution method, reason_about_case, that writes AgentRun/AgentAssessment/AgentRecommendation rows) is
    constructed exclusively inside test files, repository-wide, zero production call site
Available, already-proven-sufficient proof mechanism:  structural negative proof (§9-§11 below), the same
    class of proof this program's own established precedent already uses for the OQI4→OQI6 write-path gap
    and the production-remediation-orchestration gap, both independently disclosed during H6-I2/H6-VM
```

## 4. Finding #1 — content review (binding, independently confirmed benign)

Both files independently confirmed, by direct diff inspection (§2), to be:

- **test-only**: zero production file touched by either diff.
- **additive H6 coverage**: every change is a net-new `it()`/`describe()` block or the minimal mock
  scaffolding a new block requires; nothing removed, nothing replaced.
- **testing actual production components**: both files `import` and `render()` the real
  `FindingsPage`/`FindingDetailPage` components (`@/app/quality/findings/page`,
  `@/app/quality/findings/[findingId]/page`) already authorized and already shipped by AA §4 rows 8-9 —
  never a hand-rolled substitute.
- **not weakening any existing assertion**: `git diff` shows zero existing `it()` block, fixture constant, or
  `expect(...)` line modified or removed in either file.
- **not introducing product behavior**: the new `vi.mock()` calls in `oqi-finding-detail.test.tsx` mock
  `@/lib/auth/browser-session`/`@/lib/auth/config` — modules already imported, unmodified, by the
  already-authorized `fetchUniquenessCandidateDetail` helper (AA §4 row 9) — never a new production import,
  never a new auth pathway.
- **not altering unrelated semantics via fixture change**: the new `UNIQUENESS_CANDIDATE_DETAIL` fixture
  constant in `oqi-finding-detail.test.tsx` and the new mocked `listFindingsMock` payload in
  `oqi-findings-workspace.test.tsx` are both wholly new, additive constants scoped to their own new test
  blocks; the pre-existing `BASE_FINDING`/other fixtures are untouched.

None of §5's STOP triggers apply. **IMPLEMENTATION CORRECTION IS NOT REQUIRED.**

## 5. Finding #1 — authorization (binding)

The Artifact Authorization for `CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness.md` is amended to add
exactly the following two rows, appended to its existing §4 (I2 — MODIFY) table, with the identical
column shape:

```
MODIFY  frontend/tests/oqi-finding-detail.test.tsx
        Add dedicated component-level coverage for the Uniqueness pair-detail panel (CDD-084 §7/§28/§30):
        verify the panel renders when finding_family === "UNIQUENESS"; verify both member_a/member_b entity
        names render; verify the "Candidate — not established fact" framing renders verbatim and no bare,
        unqualified "duplicate" claim renders; verify no merge or deactivate control (button or text) is
        ever rendered; verify the governed-evidence-only adjudication label renders correctly when a
        steward has recorded CONFIRM_DUPLICATE, never presented as resolved proof; verify every other
        Finding family's Evidence tab renders unaffected. No production file touched. No existing test in
        this file may change.

MODIFY  frontend/tests/oqi-findings-workspace.test.tsx
        Add dedicated component-level coverage verifying the UNIQUENESS option is a real, selectable entry
        in the "Quality family" filter `<select>`, and that a UNIQUENESS row renders with its own family
        label and condition text (CDD-084 §30/§34). No production file touched. No existing test in this
        file may change.
```

No third new path is authorized by this section. No production, schema, API, or additional frontend page
path is authorized here or anywhere in this amendment.

## 6. Finding #1 — why this amendment does not normalize unauthorized writes (binding, restated)

This amendment is a correction of a process failure, not an endorsement of it. The binding rule this
amendment exists to enforce, unchanged and restated here without qualification:

```
FUTURE UNNAMED PATH  →  STOP + RETURN FOR A NARROW GOVERNANCE AMENDMENT, NEVER PROCEED UNILATERALLY.
```

Retroactive authorization is granted here *only* because independent re-verification (§4) confirmed the
actual content is exactly the kind of narrow, additive, non-semantic-expanding correction this program's own
established amendment discipline (CDD-039, CDD-049, CDD-050-R1, and now this document) already treats as
authorizable after the fact — never because "the implementation happened to be good" is by itself a
sufficient reason to skip the STOP. A future phase that discovers a genuine need to touch an unnamed path
must still STOP and return for amendment before writing, exactly as CDD-084 AA's own original text already
required and this amendment does not relax.

## 7. U19 — original requirement (restated exactly, AA §12)

```
U19  agent-role investigation of a candidate → zero graph/entity mutation (mirrors CDD-046 §34 test
     precedent)
```

Binding on the three new I1 test files (AA §12's own preamble: "Binding on the three new test files (rows
11-13 of §2): U1-U20").

## 8. U19 — threat-model reconstruction (independently derived this phase)

```
Assumed actor:               a governed agent role (EVIDENCE_CONSISTENCY_ANALYST / IMPACT_CONTINUITY_ANALYST
                              / RECOMMENDATION_SYNTHESIZER, CDD-046 §34, unmodified by H6)
Assumed operation:            a real, executed agent-investigation RUN against an H6
                              DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE Finding/candidate
Assumed expected transition:  the agent may read/compare/explain candidate evidence and produce a
                              recommendation; it may never write to EnterpriseEntity, InstitutionalRelationship,
                              or any other identity/graph structure
Assumed mutation surface:     EnterpriseEntity rows (identity, lifecycle_state, governance_status, version),
                              InstitutionalRelationship graph edges touching either pair member
Assumed expected proof:       before/after snapshot equality across an actually-executed agent run
```

## 9. U19 — actual H6 agent-path trace (independently performed this phase, exhaustive)

```
$ grep -rn "AgentRunORM\|AgentAssessmentORM\|AgentRecommendationORM" app/application app/api \
    app/infrastructure/persistence --include="*.py" | grep -v test
  -- writers/readers exist only in oqi_product_experience_service.py (READ side, GET route) and
     oqi_remediation_agent_repository.py (the repository implementation itself)

$ grep -n "@router\." app/api/oqi/router.py | grep -i agent
  -- exactly one route: GET /findings/{finding_id}/agent-investigation → get_agent_investigation
  -- zero POST/trigger route exists anywhere for agent investigation

$ [get_agent_investigation's own body, read in full]
  -- pure SELECT: resolves an existing OqiRemediationCaseORM by derived case_id, returns an empty
     AgentInvestigationRow immediately if no case row exists, otherwise SELECTs AgentRunORM/
     AgentAssessmentORM/AgentRecommendationORM read-only. Zero session.add/session.commit/mutation of any
     kind in this method.

$ grep -rln "OqiRemediationAgentService(" app --include="*.py"
  -- app/tests/test_oqi_product_experience_service.py
  -- app/tests/test_oqi_api_postgres.py
  -- app/tests/test_oqi_remediation_agent_i2.py
  -- ZERO production file. The class containing reason_about_case (the sole method that actually executes
     specialists and WRITES AgentRun/AgentAssessment/AgentRecommendation rows) is constructed exclusively
     inside test files, for every dimension this repository governs, not only UNIQUENESS.

$ grep -n "UNIQUENESS" app/application/oqi_remediation_agent_service.py
  -- zero matches: H6 adds no agent-specific code of any kind, confirming CDD-084 §29's own claim
     ("the existing three agent roles remain sufficient... unmodified") literally

$ grep -rn "InstitutionalRelationship" app/domain/oqi_uniqueness app/application/oqi_uniqueness_evaluation_service.py \
    app/infrastructure/persistence/oqi_uniqueness_*.py
  -- zero matches: H6 never references InstitutionalRelationship anywhere
```

**Conclusion: no real, production-reachable agent-investigation *execution* path exists anywhere in this
repository, for any quality dimension, H6 included.** The agent-investigation subsystem currently exposes
only a read-only query surface in production; its one execution entrypoint is exercised exclusively by
tests. This is a pre-existing, whole-program characteristic — not something H6 introduced, and not something
this narrow amendment's scope authorizes changing (§12).

## 10. U19 — Option A vs. Option B decision (binding)

**Option B is selected.** No executable agent-investigation path exists for U19's original wording to attack
adversarially; inventing one merely to satisfy a test label would be exactly the "fake implementation work"
this phase's own governing instructions forbid (§12/§26 of the governing prompt), and would itself be an
unauthorized H6 architecture expansion (§12 below). U19's proof mechanism is corrected to a structural
negative proof, matching H6's actual frozen architecture, while preserving the identical underlying safety
guarantee the original wording intended.

## 11. U19 — frozen structural negative-proof requirement (binding, replaces the executable-test wording)

```
U19 — AGENT/IDENTITY MUTATION NEGATIVE PROOF (structural, not executable-runtime)

Required, to be independently re-performed and recorded by OQI-H6-VM-R1 before merge (no new test file or
test-matrix code path is authorized or required by this correction):

1. No H6 agent-specific mutation entrypoint exists.
   (`grep -n "UNIQUENESS" app/application/oqi_remediation_agent_service.py` → zero matches)

2. No UNIQUENESS remediation candidate can ever be produced.
   (`extract_candidates(quality_dimension="UNIQUENESS")` dispatches to `extract_reasonableness_candidates()`,
   a zero-argument function whose body is exactly `return ()` — independently confirmed structurally
   incapable of returning non-empty without a direct source edit to that one shared function)

3. The allowed adjudication-action domain is closed to exactly REJECT_NOT_DUPLICATE / CONFIRM_DUPLICATE.
   (DB CHECK constraint `ck_oqi_uniqueness_adjudications_action`; adversarially confirmed by
   `test_cp07_adjudication_action_check_rejects_merge`, a genuine `session.add()`+`flush()` DB-level attack
   attempting `action="MERGE_ENTITY"`, `IntegrityError` raised)

4. Neither adjudication action mutates EnterpriseEntity.
   (`test_u14_confirm_duplicate_never_mutates_the_entities`, before/after snapshot equality, already green)

5. No merge/deactivate/repoint action exists anywhere in H6's product surface.
   (repository-wide grep across `app/quality`, `lib/oqi` for merge/deactivate/consolidate finds only code
   comments documenting the absence, zero actual control)

6. Repository-wide production-code search finds no H6 path capable of mutating EnterpriseEntity or
   InstitutionalRelationship from agent investigation.
   (§9 above: zero production caller of `OqiRemediationAgentService`/`reason_about_case` exists anywhere in
   this repository, for any dimension; the one production-reachable agent-investigation route,
   `GET /findings/{finding_id}/agent-investigation`, is independently confirmed pure-SELECT with zero
   `session.add`/`session.commit`/mutation of any kind)

7. The existing CONFIRM_DUPLICATE identity-immutability test remains green.
   (`test_u14_confirm_duplicate_never_mutates_the_entities`, re-run fresh by OQI-H6-VM-R1 against the
   governed merge candidate)
```

This is not a waiver of the safety property AGENT ≠ FACT / no identity mutation from agent investigation. It
is a correction of the *proof mechanism* to match H6's actual, independently-traced architecture: the
property holds today by the stronger fact that no execution path exists at all, not merely that an executed
agent happens to behave safely.

## 12. No agent-scope-expansion proof (binding)

This amendment authorizes zero new path beyond the two named in §5. It does not add, modify, or reference:
an H6 agent role; agent mutation capability; agent adjudication authority; agent remediation authority;
autonomous duplicate resolution; merge authority; or any change to `oqi_remediation_agent_service.py`,
`oqi_remediation_agent_repository.py`, `models/oqi_remediation_agent.py`, or any agent-role enum. The
structural proof in §11 is read-only, grep/inspection-based verification of the *existing, unmodified*
codebase — it requires zero code change to execute.

## 13. Zero semantic/downstream change (binding, restated)

This amendment authorizes zero change to: any H6 evaluator algorithm; SATISFIED/VIOLATED/NOT_EVALUABLE
semantics; Finding identity or lifecycle; candidate qualification or blocking; QualityFindingOrigin; OQI4;
OQI6; H1 Coverage; Reliance; remediation dispatch; production orchestration; the pair-detail or generic
Finding API; the frontend filter or pair-detail *production* rendering logic; migration `0047`; table count;
Keycloak/authority. The only two paths this amendment touches (§5) are pre-existing, already-committed test
files; this amendment changes zero bytes of them (retroactive authorization only — see §19 for the
unmodified candidate's own preservation).

## 14. Table-count / migration freeze (binding, restated)

```
H6 candidate 3c8d942, migration head 0047_oqi_h6_uniqueness:  131 governed business tables
After this amendment:                                          131 governed business tables (unchanged)
```

Zero tables created. Zero tables deleted. Zero migration added or altered. This amendment authorizes no
schema, migration, or table-count change of any kind.

## 15. Updated exact Artifact Authorization accounting (binding)

The original AA's own §1 summary table (`I1: CREATE=13, MODIFY=3`; `I2: CREATE=0, MODIFY=15`; `TOTAL=31`)
counts **accounting rows**, not individual file paths — §4 row 15 alone bundles 10 distinct files
(`.github/workflows/ci.yml` plus nine table-count test files) under one row, and §4 row 9 names one file per
row throughout. Independently enumerating every individual file named across AA §2 (13 rows, 13 files),
§3 (3 rows, 3 files), and §4 (15 rows, expanding row 15's own bundle to its 10 constituent files: 13 + 1 + 10
= 24 files) yields **40 authorized implementation files**. Adding the 2 original governance documents
(`CDD-084-...md` and its own companion AA, both self-authorizing, standard for every prior phase) gives
**42 total originally-authorized paths** — independently re-derived and cross-checked in OQI-H6-VM by direct
set comparison against the real candidate diff, not copied from any prior report.

```
Original authorized paths (2 governance + 40 implementation, individually enumerated):  42
This amendment's Finding #1 correction (§5, both MODIFY, no CREATE, no DELETE):          +2
Updated total authorized paths:                                                          44
```

Independently re-derived directly against the actual candidate diff (not trusted from any prior report):
`git diff --name-status 0e2223d26697b53d84478780b814102c2bb571cb...3c8d942ab1dec2b6239e502569ce1489c28127ec`
yields exactly **44** changed paths (16 create, 28 modify, 0 delete). This equals the updated authorized
total exactly. The candidate's actual changed-path set now equals, byte-for-byte, the authorized path set —
no discrepancy remains. This amendment's own artifact (§16) is a 45th path, itself, but is self-authorizing
(governance documents authorize their own publication, per every prior phase's identical convention) and is
not counted against the implementation-path total above.

## 16. Amendment artifact path

```
CREATE = 1
MODIFY = 0
DELETE = 0
TOTAL  = 1
```

```
CREATE  docs/cdd/CDD-084-Artifact-Authorization-H6-G-R1-Frontend-Test-Path-And-U19-Correction-Amendment.md
        This document. No other path touched by this amendment's own publication.
```

## 17. G-R1 STOP conditions (binding, exhaustive — restated for the record; none triggered this phase)

```
 1. either unauthorized frontend file was found to contain production semantics.        NOT TRIGGERED (§4)
 2. any further unauthorized path was discovered.                                        NOT TRIGGERED
 3. U19 was found to expose an actual missing production safety mechanism.               NOT TRIGGERED (§9)
 4. a real H6 agent path was found capable of mutating identity.                         NOT TRIGGERED (§9)
 5. UNIQUENESS was found capable of generating a remediation candidate.                  NOT TRIGGERED (§11.2)
 6. confirmation was found capable of mutating entity/graph.                             NOT TRIGGERED (§11.4)
 7. governance was found to require product redesign.                                    NOT TRIGGERED
 8. frozen original governance artifacts were found to have drifted.                     NOT TRIGGERED (§18)
 9. main was found to have moved incompatibly.                                           NOT TRIGGERED (§2)
10. the amendment was found to require expanding H6 architecture.                        NOT TRIGGERED (§12)
```

## 18. Governance byte-integrity (binding)

Independently re-hashed immediately before this document was written and confirmed byte-identical to their
prior publication values, both in the working tree and inside the unmoved, unmerged candidate commit
`3c8d942ab1dec2b6239e502569ce1489c28127ec`:

```
8280675f41532eba41e17ff61a2375e6d84b1f7d14eedc98d13782c251c3ae78
  CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness.md
fd79ef89f541df03aadd6444b396bac2a3172b6bd9299e349368dcc73bb4c169
  CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness-Artifact-Authorization.md
```

Neither file is modified by this amendment. This document is the sole new governance artifact this phase
publishes.

## 19. Candidate preservation (binding)

`3c8d942ab1dec2b6239e502569ce1489c28127ec` is not amended, rebased, or squashed by this document. History
remains: main → H6-G (`425e7e8`) → H6-I1 (`adfc31f`) → H6-I2 candidate (`3c8d942`) → this governance
amendment (additive, governance-artifact-only, on top of `3c8d942`) → restarted H6-VM (OQI-H6-VM-R1).

## 20. H6-VM-R1 restart rule (binding, restated)

OQI-H6-VM-R1 does not resume from OQI-H6-VM's own prior stopping point. It restarts in full against the new
governance-amendment head, independently re-proving: governance (original CDD-084 + AA, now read alongside
this amendment), the complete exact diff (now expected to reconcile exactly against the updated 44-path
authorized set, §15), source-level architecture, all adversarial DB/API/tenant attacks, whole-package static
verification, full backend and frontend regression, real PostgreSQL, fresh Docker, this amendment's own §11
structural U19 proof, CI, and — only after all of the above are independently green — PR creation, exact-head
merge, and full post-merge verification. No result from the prior, stopped OQI-H6-VM run substitutes for
proof against the new candidate identity.

## 21. Historical honesty (binding, disclosed without euphemism)

OQI-H6-VM correctly stopped pre-merge rather than silently accept two unauthorized-but-benign test-file
paths or quietly waive a mandatory, binding test-matrix item. This session's own independent re-trace found
no evidence the original I1/I2 governance chain (H6-DR through H6-VM) ever confirmed U19's assumed
executable agent-investigation path actually exists in production code, for any dimension — an omission this
amendment closes by tracing it exhaustively (§9) rather than by assumption. No implementation write against
any path has occurred as part of this amendment; it is a governance-artifact-only correction.

## 22. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 1 (two changed paths outside AA authorization, per the AA's own binding
                        STOP-and-amend rule — content independently confirmed benign, but the process
                        requirement was not met), P2 = 1 (AA §12's mandatory U19 test-matrix item never
                        implemented; underlying safety property independently confirmed structurally true,
                        but the binding verification requirement was unresolved)
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending OQI-H6-VM-R1's own full, independent
                        re-verification of the updated 44-path authorized set and the frozen §11 structural
                        U19 proof)
```

## 23. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent (CDD-039, CDD-049-Artifact-Authorization-H3-VM-R1, CDD-050-Artifact-Authorization-H4-R1)
of never silently rewriting an already-approved Artifact Authorization in place, and never folding an
out-of-scope correction into an already-stopped candidate commit. `CDD-084-OQI-H6-Governed-Enterprise-Entity-Uniqueness.md`
and its original companion Artifact Authorization remain FROZEN, unmodified, and fully authoritative. This
amendment's §5 retroactively authorizes exactly the two named frontend test paths already present in
candidate `3c8d942ab1dec2b6239e502569ce1489c28127ec`, and §11 replaces U19's proof mechanism with a
structural negative proof, to be independently executed and recorded by OQI-H6-VM-R1. No implementation
phase is required before OQI-H6-VM-R1 resumes. OQI-H6 merge readiness is reauthorized to resume, under the
identifier OQI-H6-G-R1 → OQI-H6-VM-R1, only after OQI-H6-VM-R1's own complete, independent re-verification.
