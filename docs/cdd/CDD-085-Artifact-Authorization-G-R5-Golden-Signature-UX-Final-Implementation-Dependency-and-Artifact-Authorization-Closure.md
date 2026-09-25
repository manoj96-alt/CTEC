# CDD-085 — Artifact Authorization G-R5 Golden Signature UX Final Implementation Dependency and Artifact Authorization Closure (NOETVA-GOLDEN-SIGNATURE-UX-G-R2)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-085-Artifact-Authorization-G-R4-Golden-Signature-UX-Exact-Artifact-Authorization-Closure.md`
(the literal 28-path table this amendment supersedes with a complete, final, self-consistent 33-path table —
no architecture, contract shape, or product behavior decided by G-R3/G-R4 is reopened by this amendment)
Classification: FINAL DEPENDENCY CLOSURE. This amendment's sole content is: (1) disclosing six genuine hidden
consumers of the G-R3/G-R4 contract changes, discovered only through disposable-proof construction and the
mandatory full test suites (never found by grep alone); (2) republishing one complete, final, literal Artifact
Authorization table incorporating them; (3) disclosing and independently proving orthogonal one pre-existing,
environment-sensitive governance-test condition (`gate-x-runtime-architecture.test.tsx` and its backend analog
`test_runtime_architecture.py::test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists`) is not a
seventh consumer and requires no Signature UX scope change.
Governs: this amendment only. `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md` and its original
companion Artifact Authorization, its G-R1, G-R2, G-R3, and G-R4 amendments, `CDD-086-Generic-Finding-Detail-
Parity.md`, and its own companion Artifact Authorization are all unmodified, unreopened, and remain FROZEN
exactly as originally published.

## 1. Purpose

Three prior implementation phases (internally sequenced I, G-R2, G-R3 in the working session) each independently
attempted the complete G-R3/G-R4 disposable implementation and STOPPED on discovering one additional hidden
consumer of the plural-remediation, `case_id`, or auth-scope contract changes — never previously named in any
Artifact Authorization, discovered only by disposable-proof construction, TypeScript compilation, or the full
test suite, never by grep alone. This amendment (internally sequenced G-R4 in the working session) constructs
the *complete* intended implementation (all prior hidden-consumer fixes plus every already-authorized-but-
previously-unfinished path) in disposable form one final time, runs the full backend suite, the full frontend
suite, and six explicit semantic dependency searches, discloses one further, closely related gap (three already-
authorized Entity Resolution backend test files that had never actually been written to), closes it, and proves
no seventh path remains.

## 2. Context — independently re-verified this phase

```
origin/main                                  91e90b5812a123d08d58e78347f7283d285921f6  (re-fetched,
                                              re-confirmed)
product/noetva-demo-readiness-final @        b254372b9632c0bd16174678e2ba7f2afd95688c  (unchanged; this
                                              amendment does not touch it)
PR #250                                      OPEN, unmerged, unmoved
PR #249 / #248 (historical)                  OPEN, unchanged
product/noetva-demo-readiness-g-r5 @         8d43a71f0d2338776691b36d93761ad9c58edaa0  (unchanged; not
                                              rewritten by this amendment)
```

All eight prior governance hashes independently re-hashed this phase — byte-identical:

```
CDD-085                    c813b47b60a324de798ddbc6097b6b0b4be9806cd9ed720274f1be62d1c9b984
CDD-085 AA                 7ac0d7454a174b0c8e6202062153f827ff8a11a8c121e6ebaebdadc651fe39b4
CDD-085 G-R1               bcc4fc8fe8c435d1a9c44079c059065ab15aba3070f5fd1b3bf7163502038efb
CDD-086                    02f893bdf8d310dd0e8270879928c2c5ed1eb30aebae4d42ae7185346347dd67
CDD-086 AA                 162bb163a2af5394caddab5f35c5451d242090d2829dca1a39d33a268fcf9bd7
CDD-085 G-R2               fb7d90ec8500387d09ccb75310b1022cccae93e7f8e5f5e4b5949905ec51587f
CDD-085 G-R3               2e1ba7485781855a9398a6a52e93d5ecd5903ef00073a50b8eda48f3d9114c71
CDD-085 G-R4               5873a45bd3cffd3181b14c311ac7cb322b98189f4a8c89b76dbbebbe44e77f82
```

The preserved stopped implementation worktree (`product/noetva-demo-readiness-signature-ux-i` @ `8efd781`) was
hashed at the start and close of this phase — byte-identical, zero drift, at every checkpoint across all prior
phases and this one.

## 3. G-R3/G-R4 architecture — explicitly reaffirmed, not reopened

Every decision in G-R3 §3–§26 and every path-ownership resolution in G-R4 §4–§6 is unchanged and remains binding
exactly as published. This amendment touches only: the literal path table (one new gap found and closed, six
hidden consumers folded in), and the disposition of one orthogonal, pre-existing governance-test condition.

## 4. Gate X / `test_runtime_architecture.py` — orthogonal, pre-existing, not a Signature UX consumer

Both `frontend/tests/gate-x-runtime-architecture.test.tsx` and its backend analog
`backend/app/tests/test_runtime_architecture.py::test_changed_files_match_cdd_010_and_cdd_012_exhaustive_
allowlists` share one identical mechanism: each computes the *entire* working tree's changed/untracked path set
(`git diff --name-only HEAD` union `git ls-files --others --exclude-standard`) and asserts it is a subset of its
own historical, frozen allowlist — Gate X's own 29-file nav/IA allowlist for the frontend test, and the
CDD-010/CDD-012 durable-execution/replay allowlist for the backend test. Neither test references, imports, or
asserts against any Signature UX contract (`RemediationResponse`, `candidates`, `case_id`, `oqi-remediation:
prepare`, `EvidencePanel`'s `entityId`, `RemediationPanel`'s `findingId`, or any Entity Resolution contract).

**Independent control proof (not inference):** both exact tests were run against the real, current repository,
on its actual current branch, with zero Signature UX changes present — using only the pre-existing untracked
`docs/product/` directory already present before this entire working session began. Both failed identically,
for the identical reason, confirming the failure predates and is fully independent of every contract this
amendment's implementation touches:

```
frontend:  tests/gate-x-runtime-architecture.test.tsx — fails on docs/product/*.md, *.docx (untracked)
backend:   test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists — fails identically, same cause
```

In the disposable copy, the frontend test's second assertion (no `backend/`/`migrations?/` path) additionally
fails purely because the disposable copy legitimately contains this amendment's own authorized backend and
migration work — a mechanical consequence of the same repo-global scope, not evidence of any hidden consumer.

**Disposition, frozen:** both tests are OUTSIDE this Artifact Authorization's scope and are NOT Signature UX
consumers. Per governance instruction, they are not modified, deleted, skipped, xfailed, or weakened; Gate X's
allowlist is not touched; no unrelated user/repository state (`docs/product/`) is deleted or hidden merely to
make either test pass. A separate, narrow governance action — outside Golden Signature UX — should in future
decide whether a repository-diff architecture test of this shape belongs in permanent CI at all, since by
construction it can only ever pass against a perfectly clean working tree.

## 5. Six confirmed hidden consumers (folded into §7's final table)

```
1. backend/app/tests/test_generic_finding_detail_parity.py
   Singular remediation.candidate/.authorization assertions -> remediation.candidates == ().

2. backend/app/tests/test_oqi_api_router.py
   FakeService.get_remediation() stub and the authorization-ID-survives-serialization test rebuilt to the
   plural candidates=(...) shape.

3. backend/app/tests/test_oqi_product_experience_service.py
   Stage1/Stage2 recommendation-vs-authorization assertions rebuilt to stage{1,2}.candidates[0].authorization.

4. frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
   isRejected generalized to the plural form: case_status == AWAITING_AUTHORITY AND candidates non-empty AND
   every candidate's authorization.status == REJECTED. (This is G-R4 §7.3 item 28's own VERIFY-ONLY
   verification proving an edit IS genuinely required — reclassified MODIFY per G-R4 §7.3's own explicit
   fail-closed instruction.)

5. frontend/tests/oqi-product-truth.test.tsx
   Three RemediationPanel fixtures converted to plural, findingId="f1" added.

6. frontend/tests/browser-session.test.ts
   oqi-remediation:prepare inserted into both exact-scope-string assertions and the expectedQualified array
   (already-authorized config.ts scope-list addition); "ten"->"eleven" in the affected test title.
```

None of these six reference Gate X, CDD-010, CDD-012, or any path outside the Signature UX contract surface.

## 6. One further gap found and closed this phase: unwritten Entity Resolution backend test coverage

G-R4 §7.2 items 23–25 already authorized three existing files as MODIFY for the new `get_resolved_entity()`
service method and `GET /entities/{entity_id}` route's own test coverage. Independent inspection this phase
found all three still fully unmodified in every disposable reconstruction to date — the new capability had zero
test coverage. This is not a governance gap (the paths were already correctly authorized by G-R4 §5) — it is
unfinished, already-authorized implementation work, closed this phase:

```
backend/app/tests/test_entity_resolution_steward_api_postgres.py
    +4 tests: every current record returned unfiltered by outcome (the Meridian Cell Components two-record,
    both-Resolved fixture, cross-checked disjoint from the QUEUE_OUTCOMES-filtered triage queue), None for an
    unknown entity_id, None for another tenant's entity_id (with same-tenant sanity check), None for an entity
    with zero resolution records.

backend/app/tests/test_entity_resolution_steward_router.py
    +3 tests: 403 without entity-resolution:read scope, 404 (RESOLVED_ENTITY_NOT_FOUND) when the service
    returns None, 200 with full record/source-representation serialization survival.

backend/app/tests/test_entity_resolution_tenant_isolation.py
    +1 test, at this file's own store/domain layer: tenant A's list_current_records() never surfaces a record
    naming tenant B's real, valid enterprise_entity_id (the exact composition get_resolved_entity() depends on),
    with a same-tenant sanity check.
```

`_seed_case()` in the first file gained one new optional `entity_id: UUID | None = None` keyword parameter
(defaults to its prior per-call fresh-entity behavior, zero change to any existing caller) so two records could
be attached to one known EnterpriseEntity within a single test.

## 7. Explicit semantic dependency searches — all six, no seventh path found

```
case_id consumers:       only the repository's own _authorization_to_orm() constructor and the two already-
                          authorized test-file OqiRemediationAuthorizationORM(...) constructions (both already
                          carry case_id=). No raw SQL INSERT into oqi_remediation_authorizations exists anywhere.

SUPERSEDED consumers:    no exhaustive status switch/match/dict exists outside the two already-authorized
                          frontend files (remediation-panel.tsx, remediation-stepper.tsx) and the repository's
                          own supersede_pending_sibling_authorizations(). approve()/reject() never pattern-match
                          exhaustively over status; SUPERSEDED is set only via the dedicated repository method.

auth-scope consumers:    only frontend/lib/auth/config.ts and frontend/tests/browser-session.test.ts on the
                          frontend side. backend/app/tests/test_oqi_keycloak_scope_reconciliation.py already
                          includes oqi-remediation:prepare (pre-existing, unauthorized-and-unnecessary to
                          touch) and passed in the full backend suite. keycloak/ctec-realm.json already carries
                          the scope (pre-existing, explicitly PROHIBITED from modification by G-R3 §27.5/G-R4
                          §7.4 — confirmed untouched).

remediation-contract     six hidden consumers (§5) plus the 24 already-authorized MODIFY paths account for
consumers:               every real consumer; typecheck, build, and the full 441-test frontend suite plus the
                          full 2325-test backend suite surface nothing further.

EvidencePanel/           only frontend/app/quality/findings/[findingId]/page.tsx (already-authorized MODIFY)
RemediationPanel prop    renders either component in production code; the unrelated frontend/app/supply-chain-
consumers:               impact/_components/evidence-panel.tsx is a structurally different, unrelated component
                          (different props, Supplier Risk domain) sharing only a filename.

Entity Resolution        every consumer (the two new frontend files, the two frontend lib files, the two
contract consumers:      backend files, and the three backend test files closed in §6) is already within the
                          33-path table below; no other file imports ResolvedEntity*/resolvedEntity/
                          get_resolved_entity anywhere in the repository.

action-eligibility       only frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx
consumers:               computes canDecide/canReportExecution; no other file duplicates this logic.
```

No seventh Signature UX mutation path exists.

## 8. Final literal Artifact Authorization

### 8.1 CREATE (3)

```
1. backend/app/infrastructure/persistence/migrations/versions/0048_oqi_remediation_authorization_mutual_exclusion.py
2. frontend/app/data/entity-resolution/entities/[entityId]/page.tsx
3. frontend/app/data/entity-resolution/entities/[entityId]/_components/resolved-entity-detail.tsx
```

### 8.2 MODIFY (30)

Backend production (9):

```
4.  backend/app/domain/oqi_remediation/authorization.py
5.  backend/app/application/oqi_remediation_service.py
6.  backend/app/infrastructure/persistence/oqi_remediation_repository.py
7.  backend/app/infrastructure/persistence/models/oqi_remediation.py
8.  backend/app/api/oqi/schemas.py
9.  backend/app/api/oqi/router.py
10. backend/app/application/oqi_product_experience_service.py
11. backend/app/application/entity_resolution_steward_api.py
12. backend/app/api/entity_resolution/router.py
```

Frontend production (8):

```
13. frontend/lib/auth/config.ts
14. frontend/lib/oqi/api-client.ts
15. frontend/lib/oqi/contracts.ts
16. frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx
17. frontend/app/quality/findings/[findingId]/page.tsx
18. frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx
19. frontend/lib/entity-resolution/contracts.ts
20. frontend/lib/entity-resolution/api-client.ts
```

Frontend production, path closure (1 — G-R4 §7.3's VERIFY-ONLY item, confirmed an edit is genuinely required):

```
21. frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
```

Backend test (5):

```
22. backend/app/tests/test_production_remediation_orchestration_postgres.py
23. backend/app/tests/test_oqi_api_postgres.py
24. backend/app/tests/test_entity_resolution_steward_api_postgres.py
25. backend/app/tests/test_entity_resolution_steward_router.py
26. backend/app/tests/test_entity_resolution_tenant_isolation.py
```

Backend test, hidden-consumer closure (3):

```
27. backend/app/tests/test_generic_finding_detail_parity.py
28. backend/app/tests/test_oqi_api_router.py
29. backend/app/tests/test_oqi_product_experience_service.py
```

Frontend test (2):

```
30. frontend/tests/oqi-remediation-actions.test.tsx
31. frontend/tests/oqi-finding-detail.test.tsx
```

Frontend test, hidden-consumer closure (2):

```
32. frontend/tests/oqi-product-truth.test.tsx
33. frontend/tests/browser-session.test.ts
```

### 8.3 VERIFY ONLY (0)

None. G-R4 §7.3's sole VERIFY-ONLY item (`remediation-stepper.tsx`) is resolved: verification proved an edit is
genuinely required (§5 item 4), reclassified MODIFY at §8.2 item 21.

### 8.4 PROHIBITED (explicit, non-exhaustive, restated from G-R4 §7.4, unchanged)

```
keycloak/ctec-realm.json
frontend/tests/gate-x-runtime-architecture.test.tsx (§4 — orthogonal, pre-existing, not a consumer)
backend/app/tests/test_runtime_architecture.py (§4 — orthogonal, pre-existing, not a consumer)
backend/app/application/entity_resolution_steward_api.py's queue()/QUEUE_OUTCOMES/list_cases/get_case() bodies
  (the file itself is MODIFY-authorized at §8.2 item 11 for one additive method only)
backend/app/infrastructure/persistence/migrations/versions/0047_oqi_h6_uniqueness.py or any earlier migration
any DemoOqiSeeder file
any agent code path
docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md
docs/product/ (pre-existing, unrelated untracked user state -- never deleted or hidden by this amendment)
PR #250, #249, #248
product/noetva-demo-readiness-final, -i-r2, -r1 (and their exact SHAs)
```

### 8.5 DELETE (0)

No path is authorized for deletion.

## 9. Count consistency — narrative

```
CREATE       = 3
MODIFY       = 30  (9 backend production + 8 frontend production + 1 path closure
                     + 5 backend test + 3 backend test hidden-consumer closure
                     + 2 frontend test + 2 frontend test hidden-consumer closure)
VERIFY ONLY  = 0
DELETE       = 0
TOTAL        = 33
```

## 10. Independent recount from the literal table (§8)

Counting the numbered entries directly: §8.1 lists items 1–3 (3 items). §8.2 lists items 4–33 (30 items: 9 + 8
+ 1 + 5 + 3 + 2 + 2 = 30). §8.3 lists zero items. §8.5 lists zero items. **3 + 30 + 0 + 0 = 33**, matching §9
exactly, and matching the highest item number (33) in the consecutively-numbered table. No path appears in more
than one category — independently re-checked by scanning §8.1–§8.2 for duplicate path strings; none found. This
table was mechanically cross-checked against the disposable implementation's own complete `git diff --name-
status` plus untracked-file listing: every one of the 33 authorized paths was genuinely changed in the
disposable proof, and every changed path in the disposable proof is among these 33 — zero unauthorized paths,
zero unexplained authorized-but-untouched paths.

## 11. Verification evidence this phase

```
Backend mypy:              clean, all 18 touched files (9 production + 9 test)
Migration round-trip:      upgrade to head / inspect schema (case_id NOT NULL, FK, partial unique index
                           uq_oqi_remediation_authorizations_case_one_approved) / downgrade -1 (case_id column
                           genuinely dropped) / re-upgrade — all clean
Backend full suite:        2324 passed, 1 failed (§4 -- orthogonal, independently proven pre-existing)
TypeScript typecheck:      zero errors
Production build:          clean; /data/entity-resolution/entities/[entityId] registered as a dynamic route
Targeted frontend tests:   5 files, 117 tests, all passed
Full frontend suite:       49/50 files, 439/441 tests passed; sole failing file is §4's orthogonal condition
Format/lint:                clean (format:check and eslint --max-warnings=0)
```

## 12. Implementation composition contract — unchanged from G-R3/G-R4, restated

The future implementation phase (`NOETVA-GOLDEN-SIGNATURE-UX-I-R1`) must construct its new candidate from
exactly `b254372b9632c0bd16174678e2ba7f2afd95688c` plus G-R3's, G-R4's, and this amendment's own governance
commits (all cherry-picked in sequence), then re-apply the preserved stopped-implementation worktree
(`product/noetva-demo-readiness-signature-ux-i` @ `8efd781`, proven byte-identical at the close of every prior
phase including this one) plus every fix and addition disclosed in §5, §6, and §8 of this amendment, then
independently re-run the entire certification suite from scratch — backend full suite, migration round-trip,
TypeScript, build, frontend full suite, format/lint — before any commit or merge. This amendment's own
disposable-proof results are evidence for governance closure only, never a substitute for implementation's own
independent certification. Implementation is bound to exactly the 33 literal paths in §8 and no others; `product/
noetva-demo-readiness-final` and PR #250 are not advanced by this amendment — a new PR is required.

## 13. Authorization

This amendment is approved and published as a standalone governance artifact, following this program's
established convention of never silently rewriting an already-approved Artifact Authorization in place.
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original companion Artifact Authorization, its
G-R1, G-R2, G-R3, and G-R4 amendments, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion
Artifact Authorization all remain FROZEN, unmodified, and fully authoritative. G-R3's architecture and G-R4's
path-ownership resolutions are unchanged in every particular; this amendment's sole effect is disclosing six
confirmed hidden consumers, closing one further already-authorized-but-unfinished test-coverage gap, proving one
orthogonal pre-existing governance-test condition is not a seventh consumer, and republishing the complete,
final, literal, independently-recounted 33-path Artifact Authorization table in §8. No implementation write
against any path has occurred as part of this amendment — all work described here was performed and verified in
a disposable, discarded copy; the preserved stopped-implementation worktree remains byte-identical, unmutated.
Implementation readiness is reauthorized to resume, under the identifier `NOETVA-GOLDEN-SIGNATURE-UX-I-R1`,
bound to exactly the 33 paths in §8 and no others.
