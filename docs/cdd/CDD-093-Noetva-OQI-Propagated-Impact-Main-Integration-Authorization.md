# CDD-093 — Noetva OQI Propagated Impact: Main Integration Authorization

**Status:** FROZEN
**Version:** 1.0
**Date:** 2026-10-11
**Originating phase:** NOETVA-OQI-PROPAGATED-IMPACT-INTEGRATION-DRG (Discover + Resolve + Govern only — pushes nothing, opens or closes no PR, merges nothing, deploys nothing)
**Authorizes:** NOETVA-OQI-PROPAGATED-IMPACT-INTEGRATION-I, then NOETVA-OQI-PROPAGATED-IMPACT-INTEGRATION-VM (the only phases permitted to act on this record, in that order)
**Scope:** Freezes the integration route, exact content, construction steps, push and PR scope, CI/Docker/merge gates, drift handling, and STOP conditions for integrating the VM-certified OQI propagated-impact capability (and the certified prerequisite work it is built on) into `main`. Introduces **no product change**. Does not amend CDD-042, CDD-087, CDD-090, CDD-091, or CDD-092 (including R1); it only routes their already-frozen, already-certified content into `main`.

---

## 1. Numbering-uniqueness verification (performed, not assumed)

Every local and `origin` ref was searched for `docs/cdd/CDD-093*`, commit messages were searched for `CDD-093`, and every open PR's file list was searched for `CDD-09*`: zero matches. The highest number used by this workstream is CDD-092. **CDD-093 is unclaimed.**

Recorded, out of scope here: CDD numbers 087–089 are claimed by more than one workstream (`CDD-087` exists as three different documents on `azure/golden-demo-parity-g`, `product/wow-i4-b1`, and `product/noetva-mypy-baseline-closure-gov`; `CDD-088`/`CDD-089` belong to `product/wow-i4-b1`, PR #245). The filenames differ, so no path collision exists. The CDD-087 that governs this integration is exclusively `CDD-087-Azure-Golden-Demo-Parity-Dedicated-Demo-Environment-Governance.md` (§4). Numbering de-duplication across workstreams is deferred (§17).

## 2. Authoritative state (independently re-derived at DRG)

```
origin/main                    = 171a398af6d4af6bd2149ff69879f4cdc178ed3e
Certified candidate (VM)       = f7c63bfe09e00a7beaa4f866e341546cbca77c5a   (branch product/oqi-propagated-impact-i, local only)
Candidate tree                 = ef2e48d62b144142bb2156482f1fca13062c419f
Candidate parent               = 80ac89a56085fcf6459273fef4356a55da1b11a4
Prior certified baseline       = e8c61ae840f9cef362788dad1ea91f64bd88d276
merge-base(candidate, main)    = 171a398af6d4af6bd2149ff69879f4cdc178ed3e   (origin/main is an ancestor of the candidate)

PR #253  azure/golden-demo-parity-g  -> main  OPEN  head af20323d5a9f3031d8aa5f25d3a3f5a724488b7d
         1 file (CDD-087 governance), 0 reviews, checks backend/frontend/containers = SUCCESS, MERGEABLE
         NOT an ancestor of the candidate
PR #254  azure/golden-demo-parity-i1 -> main  OPEN  head 4bf410a09712acb9ca22961c032160d7438040d5
         8 files (CDD-087 I1 implementation), 0 reviews, checks backend/frontend/containers = SUCCESS, MERGEABLE
         IS an ancestor of the candidate (unmodified commit)

main protection: required status checks backend, frontend, containers (strict=false);
                 required approving reviews = 0; linear history not required; force-push and deletion disallowed.
Repository merge methods: merge commit, squash, rebase all enabled.
Repository convention: 40 of the last 40 first-parent commits on main are PR merge commits.
```

None of the CDD-090/091/092 governance branches, the candidate branch, or the intermediate integration branches exist on `origin`; no PR references any of their commits.

## 3. Certified commits beyond `origin/main` (exact, in topological order)

| Commit | Parents | Content | Governing authority |
|---|---|---|---|
| `4bf410a09712acb9ca22961c032160d7438040d5` | 171a398 | Golden Demo restore code + static Azure infra (CDD-087 I1) — PR #254 head | CDD-087 |
| `ec896e21bae36910241e614cef2ab401d448dbd6` | 171a398 | bind remediation decision-actor identity to the authenticated principal | CDD-090 (frozen as its integration candidate) |
| `56d7adc…` | 4bf410a, ec896e2 | merge: authority-binding golden integration | CDD-090 |
| `72a3e22…` | ec896e2 | OQI authorization-dialog radios, self-approval UX, active-principal visibility (CDD-091 I1) | CDD-091 |
| `9e71eed…` | 56d7adc, 72a3e22 | merge: OQI UX hardening golden integration | CDD-091 |
| `1461058…` | 9e71eed | trusted display-name claim in TrustedPrincipal (CDD-091 I2, partial) | CDD-091 |
| `e8c61ae840f9cef362788dad1ea91f64bd88d276` | 1461058 | trusted human-readable authority attribution (CDD-091 I2-R3) | CDD-091 |
| `80ac89a56085fcf6459273fef4356a55da1b11a4` | e8c61ae | governed propagated ontology exposure (CDD-092) | CDD-092 v1 |
| `f7c63bfe09e00a7beaa4f866e341546cbca77c5a` | 80ac89a | upgrade-safe Golden propagation-policy enrollment (CDD-092 R1) | CDD-092 R1 |

These commits are integrated **unmodified** (no rebase, squash, cherry-pick, or amend). Their identities are part of the certification chain.

## 4. Governance authority and frozen hashes

Parent architectural authority for OQI4: **CDD-042** (already on `main`; unchanged).

| Document (path under `docs/cdd/`) | Source commit (branch) | SHA-256 | Role |
|---|---|---|---|
| `CDD-087-Azure-Golden-Demo-Parity-Dedicated-Demo-Environment-Governance.md` | `af20323d5a9f3031d8aa5f25d3a3f5a724488b7d` (PR #253 head) | `cb38bc3ecaf4b8498d8626832eb5fc2cb61f5cdb6ced27d625517b91cc8daec4` | Authority for `4bf410a` (PR #254) and the Golden Restore mechanism; cited by CDD-090 and CDD-091 at exactly this hash |
| `CDD-090-Governed-Authority-Binding-Azure-Golden-Demo-Deployment-Authorization.md` | `1969b54…` (`governance/cdd-090-authority-binding-deployment-authorization`) | `2aed8fdc07f21138fdf367171b1d1b3d9ffab58d13ee764fa8a7f9e8c609c688` | Authority for `ec896e2` / `56d7adc`; cited by CDD-091 at exactly this hash |
| `CDD-091-Noetva-OQI-Demo-UX-Hardening-Authorization-Dialog-and-Trusted-Identity-Governance.md` | `731ef29…` (`governance/cdd-091-oqi-demo-ux-hardening-g-r3`; chain 811522d → 70a612a → aec2a15 → 731ef29) | `72ec6d1d7ebc15885612490d6b988f4fea12a04a1f60cc6e86ea7144e3738881` (final, G-R3) | Authority for `72a3e22`, `1461058`, `e8c61ae` (incl. migration `0049` and `models/oqi_remediation.py`) |
| `CDD-092-Noetva-OQI-Governed-Propagated-Ontology-Exposure.md` | `2e74d27127015c99e951e071f5cd727a32e77bd7` (`governance/cdd-092-r1-oqi-propagated-impact-g-r1`; v1 `995abac` is its parent) | `208793c00a0878eae04c698c77c666c95c2ada4286016507d59205c914f0dc64` (R1); v1.0 prefix `0382f8769dd5da334603cb778ca4135639f79090b904e946386e8a79e60a1b1e` | Authority for `80ac89a`, `f7c63bf` |
| `CDD-093-Noetva-OQI-Propagated-Impact-Main-Integration-Authorization.md` (this record) | this commit (`governance/cdd-093-oqi-propagated-impact-integration`) | recorded by the committing phase in its report (a document cannot contain its own hash) | Integration authority |

Intermediate CDD-091 hashes (all recorded in the final document): original `d0876b46…`, G-R1 `9fbc5cfb…`, G-R2 `aa9c5c89…`. Append-only verification at DRG: G-R1 ⊂ G-R2 ⊂ G-R3 are exact byte prefixes; CDD-092 v1.0 is an exact byte prefix of R1. **Finding (non-material, already self-declared by CDD-091 §21):** the original CDD-091 is not a strict byte prefix of G-R1 because G-R1 relocated the single non-normative closing footer line; the original minus that footer line (246 lines, §§1–20) is an exact byte prefix of G-R1. The final G-R3 hash above governs.

**CDD-087 resolution:** *required, not represented on `main`, not superseded.* `4bf410a` (CDD-087 I1, PR #254) is an ancestor of the certified candidate and therefore enters `main` with this integration; its governing document exists only on PR #253 (`af20323`). CDD-090 states it "does not reopen CDD-087", and both CDD-090 and CDD-091 cite CDD-087 at `cb38bc3e…` as standing authority. Its authority therefore resides in the final integration tree at `docs/cdd/CDD-087-Azure-Golden-Demo-Parity-Dedicated-Demo-Environment-Governance.md`, byte-identical to `af20323`, carried by merging PR #253's unmodified head commit.

There is **no CDD-088 or CDD-089 in this lineage** (those numbers belong to `product/wow-i4-b1`); the VM report's phrase "CDD-089–092" is corrected to CDD-087, CDD-090, CDD-091, CDD-092 (+R1), CDD-093.

## 5. Routes considered

**Route A — prerequisite PRs separately, then the remainder.** Merge PR #253, then PR #254, then a third PR carrying `ec896e2 … f7c63bf` plus CDD-090/091/092/093. *Rejected:* three separate mutations of `main`, each creating an intermediate `main` state that no phase has certified as a whole (e.g. Golden Restore tooling on `main` without the authority-binding correction or the governance that frames it); the third PR's tree could only be verified after the first two land, so the certified tree and the merged tree would be built at different times against a moving base. More mutations, more drift windows, no added assurance.

**Route B — one consolidated integration PR that carries the prerequisite PR head commits unmodified (SELECTED).** A single integration branch is constructed from the certified candidate (which already contains `origin/main` and PR #254's head) by non-fast-forward merging PR #253's head and the governance branch heads. One PR, one CI run, one Integration-VM of the exact tree, one merge into `main`. PR #253's and #254's commits are preserved byte-for-byte by ancestry, so their review route is honored rather than replaced, and GitHub can recognize both as merged.

**Route C — rebase/squash/cherry-pick into a fresh linear series.** *Rejected:* rewrites certified commit identities and the certified tree lineage that VM, CDD-090, CDD-091, and CDD-092 bind to by SHA.

## 6. PR #253 / #254 disposition (frozen)

| PR | Retained changes | Disposition | Order / dependency |
|---|---|---|---|
| #253 (`af20323`) | Its single file, byte-identical (`cb38bc3e…`) | **Retained in full** — its unmodified head commit is merged into the integration branch (§8 step 2) | First merge into the integration branch, before any other governance |
| #254 (`4bf410a`) | All 8 files, byte-identical as already contained in the candidate tree | **Retained in full** — its unmodified head commit is already an ancestor of the candidate | Already in place; no action |

Rules:
1. Neither PR is modified, rebased, retargeted, commented on, approved, merged directly, or closed by INTEGRATION-I.
2. If either PR's head SHA differs from §2 at any time before the integration merge: **STOP** (§16).
3. If either PR is merged into `main` independently before the integration merge, `origin/main` drifts: **STOP** (§12).
4. After the integration merge, INTEGRATION-VM verifies that `af20323` and `4bf410a` are both ancestors of the new `main`. If GitHub has not marked a PR merged, INTEGRATION-VM may close it **only** with a comment citing the integration PR, the `main` merge commit SHA, and the ancestry proof. Closure before the integration merge is prohibited.

## 7. Frozen integration content

### 7.1 Implementation (exactly the certified candidate tree)

Every path outside `docs/cdd/` in the integration tree must be byte-identical to tree `ef2e48d62b144142bb2156482f1fca13062c419f`. Relative to `origin/main` that is exactly **37 paths: 31 MODIFY, 6 CREATE, 0 DELETE**, each named by at least one governing document (verified at DRG; zero unnamed paths):

```
A .github/workflows/azure-golden-demo-restore.yml                                   4bf410a                  CDD-087
M backend/app/api/oqi/router.py                                                     ec896e2 e8c61ae 80ac89a  CDD-090/091/092
M backend/app/api/oqi/schemas.py                                                    ec896e2 e8c61ae 80ac89a  CDD-090/091/092
M backend/app/api/supplier_risk/authentication.py                                   1461058 e8c61ae          CDD-091
M backend/app/application/oqi_ontology_impact_evaluation_service.py                 80ac89a                  CDD-092
M backend/app/application/oqi_product_experience_service.py                         e8c61ae 80ac89a          CDD-091/092
M backend/app/application/oqi_remediation_service.py                                e8c61ae                  CDD-091
M backend/app/application/production_remediation_orchestration_service.py           e8c61ae                  CDD-091
M backend/app/core/config.py                                                        4bf410a 1461058          CDD-087/091
M backend/app/domain/oqi_remediation/authorization.py                               e8c61ae                  CDD-091
M backend/app/infrastructure/persistence/database_cli.py                            4bf410a e8c61ae 80ac89a  CDD-087/091/092
M backend/app/infrastructure/persistence/demo_oqi_seeder.py                         80ac89a f7c63bf          CDD-092 (+R1)
A backend/app/infrastructure/persistence/migrations/versions/0049_oqi_remediation_actor_display_name.py  e8c61ae  CDD-091
M backend/app/infrastructure/persistence/models/oqi_remediation.py                  e8c61ae                  CDD-091
M backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py  80ac89a               CDD-092
M backend/app/infrastructure/persistence/oqi_remediation_repository.py              e8c61ae                  CDD-091
A backend/app/tests/test_database_cli.py                                            4bf410a                  CDD-087
A backend/app/tests/test_database_cli_postgres.py                                   4bf410a                  CDD-087
M backend/app/tests/test_noetva_demo_readiness_golden_story.py                      80ac89a                  CDD-092
M backend/app/tests/test_oqi_api_router.py                                          e8c61ae 80ac89a          CDD-091/092
M backend/app/tests/test_oqi_ontology_impact_postgres.py                            80ac89a f7c63bf          CDD-092 (+R1)
M backend/app/tests/test_oqi_ontology_impact_service.py                             80ac89a                  CDD-092
A backend/app/tests/test_oqi_remediation_identity_binding_postgres.py               ec896e2 e8c61ae          CDD-090/091
M frontend/app/globals.css                                                          72a3e22                  CDD-091
M frontend/app/quality/findings/[findingId]/_components/decide-authorization-dialog.tsx  ec896e2 72a3e22     CDD-090/091
M frontend/app/quality/findings/[findingId]/_components/ontology-impact-panel.tsx   80ac89a                  CDD-092
M frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx       e8c61ae                  CDD-091
M frontend/components/session-controls.tsx                                          72a3e22                  CDD-091
M frontend/lib/oqi/contracts.ts                                                     ec896e2 e8c61ae 80ac89a  CDD-090/091/092
M frontend/tests/oqi-conflict-lens.test.tsx                                         80ac89a                  CDD-092
M frontend/tests/oqi-finding-detail.test.tsx                                        e8c61ae 80ac89a          CDD-091/092
M frontend/tests/oqi-product-truth.test.tsx                                         e8c61ae 80ac89a          CDD-091/092
M frontend/tests/oqi-remediation-actions.test.tsx                                   ec896e2 72a3e22 e8c61ae  CDD-090/091
M frontend/tests/session-controls.test.tsx                                          72a3e22                  CDD-091
M infra/azure/main.bicep                                                            4bf410a                  CDD-087
A infra/azure/modules/container-apps-job-golden-restore.bicep                       4bf410a                  CDD-087
M infra/azure/resources.bicep                                                       4bf410a                  CDD-087
```

Inventory fingerprint (`git diff --name-status --no-renames 171a398 f7c63bf`, LF-terminated): SHA-256 `d97f08e23e74f674170466692f497219f9254889c1d50081e3f285b0661181d6`.

The only migration is `0049_oqi_remediation_actor_display_name.py` (`revision = "0049_oqi_remediation_actor_name"`, `down_revision = "0048_oqi_remediation_mutex"`, single head), and the only ORM model change is `models/oqi_remediation.py`; both are CDD-091-authorized and VM-certified. **No other migration or ORM change is authorized.**

### 7.2 Governance additions (exactly five new files, no other `docs/` change)

```
A docs/cdd/CDD-087-Azure-Golden-Demo-Parity-Dedicated-Demo-Environment-Governance.md          cb38bc3e…daec4
A docs/cdd/CDD-090-Governed-Authority-Binding-Azure-Golden-Demo-Deployment-Authorization.md     2aed8fdc…c688
A docs/cdd/CDD-091-Noetva-OQI-Demo-UX-Hardening-Authorization-Dialog-and-Trusted-Identity-Governance.md  72ec6d1d…8881
A docs/cdd/CDD-092-Noetva-OQI-Governed-Propagated-Ontology-Exposure.md                           208793c0…dc64
A docs/cdd/CDD-093-Noetva-OQI-Propagated-Impact-Main-Integration-Authorization.md                (this record; hash per DRG report)
```

Final integration tree vs `origin/main`: **42 paths = 37 implementation (31 M, 6 A) + 5 governance (5 A), 0 DELETE.** Final integration tree vs candidate tree: exactly the 5 governance additions.

## 8. INTEGRATION-I construction (exact)

Branch (new, local first): `governance/oqi-propagated-impact-main-integration` (follows the repository's existing `governance/*-integration` precedent). Preconditions are §12 checks. Steps, in this order, each a `git merge --no-ff` of an unmodified head commit with the stated message, then a `Co-Authored-By` trailer as required by the executing environment:

```
0. git switch -c governance/oqi-propagated-impact-main-integration f7c63bfe09e00a7beaa4f866e341546cbca77c5a
1. (no-op: PR #254 head 4bf410a is already an ancestor — verify, do not merge)
2. git merge --no-ff af20323d5a9f3031d8aa5f25d3a3f5a724488b7d  -m "Merge PR #253 head (CDD-087 governance) into OQI propagated-impact main integration (CDD-093)"
3. git merge --no-ff <CDD-090 commit 1969b54, full SHA resolved and verified>  -m "Merge CDD-090 governance into OQI propagated-impact main integration (CDD-093)"
4. git merge --no-ff <CDD-091 G-R3 commit 731ef29, full SHA>                    -m "Merge CDD-091 governance (G-R3 final) into OQI propagated-impact main integration (CDD-093)"
5. git merge --no-ff 2e74d27127015c99e951e071f5cd727a32e77bd7                   -m "Merge CDD-092 governance (v1 + R1) into OQI propagated-impact main integration (CDD-093)"
6. git merge --no-ff <CDD-093 commit, full SHA from the DRG report>             -m "Merge CDD-093 integration authorization into OQI propagated-impact main integration"
```

Each source commit's full SHA must be re-resolved from its branch and must equal the SHA recorded in §4 / the DRG report before merging; any mismatch is a STOP.

**Mechanical conflict resolutions permitted: none.** DRG proved by `git merge-tree --write-tree` in a disposable shared clone that steps 2–5 are conflict-free pure additions (each source branch adds exactly one new file absent from the candidate) and that the result differs from the candidate tree by exactly the four governance files, with every non-`docs/cdd` path byte-identical. Step 6 is likewise a single-file addition. **Any conflict in any step is a STOP**, not a resolution.

After step 6, INTEGRATION-I must verify and record: integration head commit SHA, tree SHA, parents; `git diff --name-status origin/main HEAD` equals §7 exactly (42 paths); `git diff f7c63bf HEAD` equals exactly the 5 governance additions; all five governance hashes; `git diff --quiet f7c63bf HEAD -- . ':!docs/cdd'`; Alembic single head `0049_oqi_remediation_actor_name`; `make verify-architecture` passes (DRG simulation: 205 artifacts, same as `origin/main`); clean tree.

## 9. Push and PR scope (authorized for INTEGRATION-I only)

- **Push exactly one ref:** `governance/oqi-propagated-impact-main-integration` → `origin`, as a new branch, non-force. No other branch is pushed (the source governance branches and the candidate branch are carried by ancestry; they need not and may not be pushed by this authorization).
- **Open exactly one PR:** base `main`, head `governance/oqi-propagated-impact-main-integration`. Title: `OQI propagated-impact main integration (CDD-087/090/091/092 R1/093)`. Body must truthfully state: the route (§5 B), the 9 certified commits, the 5 governance documents and hashes, that PR #253/#254 heads are carried unmodified, that no product change is introduced by integration, what has and has not been verified on this exact tree, and the deferred items (§17). It must not claim the integration tree is certified, deployed, or merged.
- INTEGRATION-I does **not** merge. It ends after CI on the exact head completes and is reported.

## 10. Gates

### 10.1 INTEGRATION-I gates (before handing to VM)
Construction verifications (§8), required CI checks `backend`, `frontend`, `containers` = SUCCESS on the exact PR head SHA, and the local critical crown on the exact integration commit in a fresh disposable worktree: CDD-092 crowns incl. the 12 R1 crowns and the dense-graph fail-closed crown; CDD-091 identity crown and authorization UI tests; Golden story; full backend, ruff, mypy; frontend tsc, Vitest, Gate X, eslint, prettier, `next build`.

### 10.2 INTEGRATION-VM (independent; against the exact integration commit/tree)
Prior candidate and Azure certification are supporting evidence only; they do not certify the integration tree. VM must independently verify, on the exact PR head SHA:
1. Governance presence, all five hashes, append-only chains, authority (CDD-042 parent; CDD-087/090/091/092/093).
2. Implementation preservation: non-`docs/cdd` tree byte-identical to `ef2e48d6…`; complete diff vs `origin/main` equals §7; no migration/ORM change beyond §7.1.
3. CDD-091 crowns (identity binding, self-approval prevention, human-readable attribution, frontend authorization).
4. CDD-092 and R1 crowns (fresh, zero-policy existing tenant, idempotency, partial set, six same-ID conflicts, different-ID conflict, Golden Restore atomicity).
5. Independent adversarial propagation checks (cycles, dense-graph fail-closed with nothing persisted, near-ceiling completeness, multi-path, digest version, tenant isolation, direction/depth/deny-by-default).
6. Full backend regression, ruff, mypy; frontend tests, eslint, tsc, prettier, Gate X, production build; `make verify-architecture`.
7. Candidate-specific CI: required checks green on the exact head SHA.
8. Docker images built `linux/amd64` from the exact integration tree; source-to-image identity (every Python source in the backend image byte-identical to the integration tree); frontend build lineage (frontend tree identity and governed build inputs).
9. Fresh-database seed and Golden Restore: 15/15 PASS, `ontology_propagated_chain` exposed=3, literal `demo-verify: ALL CHECKS PASSED`, exactly 3 frozen policies.
10. Upgrade: previously certified old backend image `sha256:c34e8ed5f06ddad441aa354641b5a752d787cc30b8a11f5c727d53133188967a` on a persisted database → integration image on the same database → Golden Restore: same requirements as 9; then a repeat restore with byte-identical policy rows and chain.
11. Fail-closed policy-semantic conflict and real `golden_demo_restore()` transaction atomicity.

### 10.3 Merge gate and method (INTEGRATION-VM only, after 10.2 passes)
Immediately before merging, re-verify: `origin/main` = `171a398…`; PR head = the VM-verified SHA; PR #253/#254 heads unchanged; governance hashes unchanged; required checks green on that SHA; no new review blocker. **Method: merge commit**, bound to the verified head (`gh pr merge <n> --merge --match-head-commit <verified SHA>`). Squash and rebase are prohibited (they would rewrite certified identities).

### 10.4 Post-merge verification
Fetch `origin/main`; record the merge commit SHA; verify its second parent is the verified head and its first parent is `171a398…`; verify `main^{tree}` equals the verified integration tree (with `origin/main` an ancestor of the head, a merge commit cannot change the tree — if it differs, STOP and treat `main` as uncertified pending a new VM); verify `af20323` and `4bf410a` are ancestors of `main` (§6 rule 4); run a narrow smoke on the merged commit: governance hashes, Alembic head, critical propagation tests, R1 upgrade-lifecycle crowns, CDD-091 crown subset, frontend critical OQI tests, clean tree.

## 11. Prohibited changes

Any product, test, migration, ORM, infra, workflow, or configuration change not already in the certified candidate; any edit to an existing frozen governance document; any conflict "resolution"; rebase, squash, cherry-pick, amend, or force-push of any certified or governance commit; pushing any ref other than §9; modifying, commenting on, retargeting, closing, or directly merging PR #253/#254 before the integration merge; merging `origin/main` (or anything else) into the integration branch; Azure deployment, Golden Restore against Azure, or any application-data mutation; CIAM, dev, or production changes; resolving any deferred item.

## 12. Drift handling (fail closed)

Before construction, before push, before PR creation, before VM, and immediately before merge, verify: `origin/main` = `171a398af6d4af6bd2149ff69879f4cdc178ed3e`; candidate branch head = `f7c63bf…`; PR #253 head = `af20323…`; PR #254 head = `4bf410a…`; governance source heads and hashes = §4; integration branch head (once pushed) = the recorded SHA. **Any difference is a STOP.** No re-integration of a moved `main` is authorized by this record; drift requires a governance amendment that re-derives §7 and re-proves conflict analysis.

## 13. Recovery (preserving existing work)

No existing branch, worktree, or PR is reset, cleaned, deleted, overwritten, or repurposed. INTEGRATION-I works only in a new worktree on the new integration branch. If construction is wrong **before push**, INTEGRATION-I may delete only the local integration branch it created and reconstruct it from §8. **After push**, no force-push or remote deletion is authorized: a defective pushed branch is reported and left in place for governance disposition. All certified source branches remain untouched throughout.

## 14. Azure boundary

This record authorizes no Azure action. The demo environment remains as certified by NOETVA-OQI-PROPAGATED-IMPACT-VM (backend `--0000004` `sha256:da6393183362095c29af1a88dccc9496b4cca6f78c9c77d234abc2d38f3a0e82`, frontend `--0000005` `sha256:1919d905d231ddc80bcf1a96dcd51cba0e94b336185e15f283aac2bc71f39e0e`, Golden Restore job on the backend digest, migrate job on `sha256:c34e8ed5…`). Merging source to `main` does not redeploy Azure; any redeployment from `main` requires separate governance.

## 15. Product truth (unchanged; integration may not alter it)

MAJORITY ≠ TRUTH · AUTHORITY ≠ TRUTH · CANDIDATE ≠ TRUTH · AGENT ≠ FACT · UNKNOWN ≠ LOW · CONNECTED ≠ IMPACTED · PATH ≠ CAUSATION · REACHABILITY ≠ CRITICALITY · REMEDIATION ≠ RESOLUTION · FRESH-BOOT SUCCESS ≠ UPGRADE SAFETY · DETERMINISTIC IDENTITY ≠ SEMANTIC EQUIVALENCE.

Certified story: SAP says US while PLM says MX for Meridian Cell Components. Noetva preserves the unresolved disagreement and shows Aurora X1 exposure through governed, approved dependencies, with the exact path as evidence. Not claimed: that either source value is true; that propagation establishes product failure; that the disagreement or propagation caused HIGH or RELIANCE_AT_RISK; that an agent investigation occurred (it remains "Not invoked").

## 16. STOP conditions

STOP — INTEGRATION BLOCKED if any of: drift per §12; any governance hash or source SHA mismatch; any merge conflict in §8; the resulting tree differs from §7 by even one path or byte outside `docs/cdd`, or `docs/cdd` differs by anything other than the five additions; a migration or ORM change beyond §7.1; `make verify-architecture` fails; any required CI check missing, pending at decision time, or failing on the exact head; any INTEGRATION-VM crown fails or is unverifiable (including source-to-image identity); a material review blocker appears; the merge would require a method other than §10.3; the post-merge tree differs from the verified tree; any action outside §9/§11 would be needed.

## 17. Deferred (outside this integration)

CLI settings-cache test-ordering fragility (`test_database_cli_postgres.py::dedicated_engine`); historical live policy-row count; Evidence + exposure screenshot composite; cross-workstream CDD numbering de-duplication (087–089); `relationship_type_name` non-unique index observation; Gate S sibling authority-binding (`app/api/gate_s/router.py`, reported by `ec896e2`); every deferred item of CDD-087, CDD-090, CDD-091, CDD-092 §27 and R1.18; Azure redeployment from `main`.

---

*CDD-093 authorizes integration governance only. It implements, pushes, merges, and deploys nothing itself. It amends no other CDD.*

---

# CDD-093 R1 — Required CI-Conformance Repair (append-only amendment)

**Status:** FROZEN (R1)
**Version:** 1.1 (v1.0 text above is unchanged and remains frozen)
**Date:** 2026-10-11
**Originating phases:** NOETVA-OQI-PROPAGATED-IMPACT-INTEGRATION-I (STOP — INTEGRATION BLOCKED) → NOETVA-OQI-PROPAGATED-IMPACT-INTEGRATION-G-R1 (first attempt STOPPED; this freeze)
**v1.0 SHA-256 (exact byte prefix of this document):** `4912192eece60707c06649ec748c716aa7215d2dc9531ae60bb77c4ed3f1c8d3`
**Classification:** REQUIRED CI-CONFORMANCE REPAIR — comments only, tests only, zero product semantic change, zero Azure change. Not an OQI propagation change, not a CDD-091 security change, not a CDD-092 remediation, not an Azure correction. CDD-091 and CDD-092 (incl. R1) are not reopened.

R1 supersedes v1.0 only where it says so: §7 (content, inventory, fingerprint), §8 (construction gains two steps), §9 (push target is the existing branch / existing PR), §10.1–§10.2 (gates gain exact CI parity), §11 (prohibitions gain the R1.9 exceptions-and-limits), and §16 (STOP conditions extended). Everything else in v1.0 stands.

## R1.1 Incident

INTEGRATION-I constructed head `2f2cb3ce3a6624b1e7ba29407b28dc367d74f719` (tree `131ff911bf8a0a29135c00c12e85e025251a023c`, exactly as predicted), passed its local crown, pushed `governance/oqi-propagated-impact-main-integration`, and opened PR #255. Required checks on that exact head: `frontend` SUCCESS, `containers` SUCCESS, **`backend` FAILURE** (both runs: 38180995860, 38181025024). The backend job stopped at `isort --check-only .` on exactly one file. A first G-R1 attempt proved that the proposed one-line isort fix was correct but **insufficient**: the next CI step, `ruff check .`, fails on 16 pre-existing findings that the isort failure had masked. That attempt correctly STOPPED without amending governance.

## R1.2 Exact backend CI contract (authority: `.github/workflows/ci.yml`, byte-identical on `main` 171a398 and on 2f2cb3c, blob `b12f7550fde4…`)

Python 3.12; `pip install -e '.[dev]'` (floating ranges: `black>=25.1,<26`, `isort>=6,<7`, `ruff>=0.9,<1`, `mypy>=1.15,<2`, `pytest>=8.3,<9`, `pytest-cov>=6,<7`); then in order `black --check .` → `isort --check-only .` → `ruff check .` → `mypy app` → `pytest` (addopts `--cov=app --cov-report=term-missing --cov-fail-under=80`). Frontend: Node 22, `npm ci` → `npm run format:check` → `npm run lint` → `npm run typecheck` → `npm test -- --run --coverage` (thresholds 80% lines/functions/statements/branches on `components/**/*.tsx`) → `npm run build`. Containers: the 15-step compose smoke incl. migration head = repository head, exactly 131 tables, Keycloak scope classification, 401 unauthenticated, PKCE-authenticated OQI read, demo seeder. Required checks (branch protection, re-read at G-R1): `backend`, `frontend`, `containers`; strict=false; 0 approvals; linear history not required.

**Resolved toolchain (CI parity manifest).** Failing run 38181025024 installed 51 packages including black 25.12.0, isort 6.1.0, ruff 0.17.0, mypy 1.20.2, pytest 8.4.2, pytest-cov 6.3.0. A fresh *unpinned* `pip install -e '.[dev]'` on CPython 3.12.7 at G-R1 resolved **identical versions for all 51 packages** (no pinning was used). `main` was last green on 2026-09-25 with ruff 0.16.9 (CI log evidence); ruff 0.17.0 was published 2026-10-09 and is what every CI run since resolves.

## R1.3 Blocker 1 — isort (pre-existing, CDD-091 lineage)

- Failing file (only one; 30 files skipped): `backend/app/tests/test_oqi_remediation_identity_binding_postgres.py`. Clean at `ec896e2`; incompatible from `e8c61ae` (CDD-091 I2-R3), which added `from alembic import command as alembic_command` / `from alembic.config import Config`; carried unchanged through `80ac89a`, `f7c63bf`, and the integration. It predates CDD-092.
- Cause: isort classifies `alembic` as first-party (the repository-local `backend/alembic/` directory is in its `src_paths`), ruff classifies it as third-party (`known-first-party = ["app"]` only). Both alternatives were tried at G-R1: the isort-preferred order fails ruff (I001); the `import alembic.command` form still fails isort. No ordering satisfies both under current configuration.
- Repository convention: 30 files carry `# isort: skip_file`, including every other non-migration module that imports `alembic` (21 test files); migrations use `from alembic import op` only. This file is the sole non-migration `alembic` importer without the directive.
- Classification: **pre-existing integration-gate incompatibility exposed by the first exact CI-parity execution.**

## R1.4 Blocker 2 — ruff 0.17.0 RUF100 (pre-existing on `main`)

`ruff check .` (ruff 0.17.0) reports exactly **16 findings, all `RUF100` (unused `noqa` directive, non-enabled `DTZ001`) in 14 test files**. Main control: the identical 16 findings (same path, line, column, message; 16/16 identical line content) exist on `origin/main` 171a398; **none** is in a file touched by the integration diff. `DTZ001` is not among the 407 enabled rules (the enabled DTZ set is DTZ002/003/004 only); `RUF100` is enabled. Classification: **floating dev-dependency resolution exposed stale suppression comments that the newly resolved ruff version treats as RUF100 failures** — not an application regression.

## R1.5 Alternatives considered

| Option | Decision |
|---|---|
| isort: reorder imports | Rejected — no order satisfies both isort and ruff (proven) |
| isort: change global isort config | Rejected — global tooling policy change, wider blast radius |
| isort: change ruff config | Rejected — same |
| **isort: add repository-standard `# isort: skip_file`** | **Selected** — matches 30-file convention, one comment line, no import change |
| **ruff: remove only the 16 stale `noqa: DTZ001` directives** | **Selected** — they suppress a non-enabled rule; removal fixes the underlying hygiene issue; AST unchanged |
| ruff: pin `ruff<0.17` | Rejected — tooling-policy change; preserves stale suppressions |
| ruff: per-file-ignores / config tolerance | Rejected — config change; masks the finding |
| ruff: disable RUF100 | Rejected — masks all future stale suppressions repository-wide |
| ruff: `ruff check --select RUF100 --fix` | **Prohibited** — proven at G-R1 to modify 31 files (with only RUF100 selected, every legitimate BLE001/TRY004/PLR0124 suppression appears unused and is stripped together with its rationale) |

## R1.6 Frozen repair (exact; 15 unique paths; comments only)

**(a) isort — 1 path, +1 line.** In `backend/app/tests/test_oqi_remediation_identity_binding_postgres.py` insert the single line `# isort: skip_file` immediately above the line `from __future__ import annotations` (the repository-standard position used by `test_database_cli_postgres.py` and `test_oqi_api_postgres.py`). No other change to that file.

**(b) ruff — 14 paths, 16 edits.** For each row below, on exactly that line, delete the `noqa: DTZ001` directive. Where the directive carries rationale prose after a `--`/`-` separator, the prose is preserved as a plain trailing comment (`  # <prose>`); otherwise the whole `  # noqa: DTZ001` comment is removed. All 16 directives are trailing (none standalone). No other byte changes.

| # | Path | Line | Before (stripped) | After (stripped) |
|---|---|---|---|---|
| 1 | `backend/app/tests/test_blueprint_persistence.py` | 53 | `_blueprint(created_on=datetime(2026, 1, 1))  # noqa: DTZ001` | `_blueprint(created_on=datetime(2026, 1, 1))` |
| 2 | `backend/app/tests/test_domain_foundation.py` | 171 | `**_profile(effective_from=datetime(2026, 1, 1)),  # noqa: DTZ001` | `**_profile(effective_from=datetime(2026, 1, 1)),` |
| 3 | `backend/app/tests/test_domain_operational.py` | 144 | `**_profile(effective_from=datetime(2026, 1, 1)),  # noqa: DTZ001` | `**_profile(effective_from=datetime(2026, 1, 1)),` |
| 4 | `backend/app/tests/test_field_value_evidence_persistence.py` | 83 | `observed_at=datetime(2026, 1, 1),  # noqa: DTZ001` | `observed_at=datetime(2026, 1, 1),` |
| 5 | `backend/app/tests/test_field_value_evidence_persistence.py` | 95 | `received_at=datetime(2026, 1, 1),  # noqa: DTZ001` | `received_at=datetime(2026, 1, 1),` |
| 6 | `backend/app/tests/test_integration_contracts.py` | 55 | `datetime(2026, 1, 1),  # noqa: DTZ001 - deliberately naive negative fixture` | `datetime(2026, 1, 1),  # deliberately naive negative fixture` |
| 7 | `backend/app/tests/test_knowledge_engine.py` | 284 | `store.current(assertion_id, as_of=datetime(2026, 1, 1))  # noqa: DTZ001` | `store.current(assertion_id, as_of=datetime(2026, 1, 1))` |
| 8 | `backend/app/tests/test_oqi_cross_source_evaluation_domain.py` | 332 | `evaluation_horizon=datetime(2026, 1, 1, tzinfo=None),  # noqa: DTZ001` | `evaluation_horizon=datetime(2026, 1, 1, tzinfo=None),` |
| 9 | `backend/app/tests/test_oqi_integrity_reference_evaluation_domain.py` | 138 | `evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive` | `evaluation_horizon=datetime(2026, 1, 1),  # deliberately naive` |
| 10 | `backend/app/tests/test_oqi_integrity_structural_evaluation_domain.py` | 214 | `evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive` | `evaluation_horizon=datetime(2026, 1, 1),  # deliberately naive` |
| 11 | `backend/app/tests/test_oqi_quality_evaluation_service.py` | 208 | `naive_horizon = datetime(2026, 1, 1, tzinfo=None)  # noqa: DTZ001 -- deliberately naive` | `naive_horizon = datetime(2026, 1, 1, tzinfo=None)  # deliberately naive` |
| 12 | `backend/app/tests/test_oqi_timeliness_evaluation_domain.py` | 112 | `created_on=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive` | `created_on=datetime(2026, 1, 1),  # deliberately naive` |
| 13 | `backend/app/tests/test_oqi_timeliness_evaluation_domain.py` | 342 | `evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001` | `evaluation_horizon=datetime(2026, 1, 1),` |
| 14 | `backend/app/tests/test_runtime_invocation.py` | 169 | `store = InMemoryExecutionStore(clock=lambda: datetime(2026, 1, 1))  # noqa: DTZ001` | `store = InMemoryExecutionStore(clock=lambda: datetime(2026, 1, 1))` |
| 15 | `backend/app/tests/test_semantic_mapping_persistence.py` | 41 | `_semantic_mapping(created_on=datetime(2026, 1, 1))  # noqa: DTZ001` | `_semantic_mapping(created_on=datetime(2026, 1, 1))` |
| 16 | `backend/app/tests/test_source_field_persistence.py` | 38 | `_source_field(created_on=datetime(2026, 1, 1))  # noqa: DTZ001` | `_source_field(created_on=datetime(2026, 1, 1))` |

**Unique path count:** 15 (the isort file is not among the 14 ruff files). Every path matches `backend/app/tests/test_*.py`. No application, deployment, migration, frontend, workflow, dependency, or configuration path.

**Fingerprints** (each = SHA-256 of `git diff` output, default context, against `2f2cb3ce…`, paths in git order):
- isort patch: `8e518194c0759ba9a9ac8f5841bbdc91cef2587e99fe54d996434b6369a1d23c` (identical to the INTEGRATION-I / first-G-R1 reference)
- ruff patch (14 files): `fb959dde13e714ad085044d8e05ce533ec31b798a52db139dc6fc36a03fab97b`
- combined repair (15 files, +17 −16): `f4dcab517cdd85fe701b93eef7296b88a0107e716d3a76a8779ffea8e1ca2070`

**Executable-semantics proof (G-R1, all 15 files):** location-free `ast.dump` identical before/after, and the `tokenize` stream excluding `COMMENT`/`NL` tokens identical before/after. No import, expression, fixture, assertion, SQL, or parameter changed.

## R1.7 Corrected content, inventory, and fingerprint (supersedes v1.0 §7 counts)

Repair-only tree (2f2cb3c + R1.6, CDD-093 still at v1.0 bytes): `4f507b47cbd7f9fb4be4969dcd44bf6434da185b` (constructed in a disposable worktree). After the repair, the integration diff vs `origin/main` 171a398 is **56 paths: 45 MODIFY, 11 CREATE, 0 DELETE** = 51 implementation/test paths (v1.0's 37 + the 14 ruff paths; the isort file was already counted) + 5 governance documents. The v1.0 implementation-inventory fingerprint `d97f08e2…81d6` hashed the name-status path list and is **retired** because 14 paths entered; the corrected fingerprint (`git diff --name-status --no-renames 171a398 <head> -- . ':!docs/cdd'`) is `a37e4fabc4b37e0f384d05707ca174525cd7c6d2baccb92011926ec510fb73e8` (51 paths). Merging this R1 document changes only the bytes of the already-counted CDD-093 path; the final path count stays 56.

## R1.8 Prototype certification of the repair tree (G-R1, CI-resolved toolchain)

Backend CI contract, complete sequence: black PASS (664 unchanged) · isort PASS · ruff PASS · mypy PASS (663 files) · pytest **2425 passed, 0 failed, coverage 95.20%** (floor 80%). Frontend CI contract: npm ci · format:check PASS · lint PASS · typecheck PASS · `npm test -- --run --coverage` **464/464**, thresholds met (lines 98.51%, branches 87.75%, functions 90.24%) · build PASS (local Node v24; the frontend tree is byte-identical to 2f2cb3c, whose GitHub `frontend` check passed on Node 22). Containers CI contract: all 15 steps executed verbatim from ci.yml PASS (migration head `0049_oqi_remediation_actor_name`, 131 tables, scopes, 401, PKCE-authenticated OQI read 200, demo seeder) and torn down. Crowns: CDD-091 identity 36/36, authorization UI 48/48, Gate X 5/5, CDD-092 40/40 (incl. 50,000-row fail-closed 2/2 and R1 upgrade-safe enrollment 12/12), Golden story 19/19. `make verify-architecture` PASS (205 artifacts).

## R1.9 INTEGRATION-I-R1 construction (supersedes v1.0 §8–§9 for the correction)

Start from the existing local and remote branch `governance/oqi-propagated-impact-main-integration` at exactly `2f2cb3ce3a6624b1e7ba29407b28dc367d74f719` (no reconstruction, no reset). In a new worktree on that branch:

```
A. git merge --no-ff <CDD-093 R1 governance commit, full SHA from the G-R1 report>
     -m "Merge CDD-093 R1 (CI-conformance) governance into OQI propagated-impact main integration"
   (merge-base is 8253769, already in the branch: the result changes only docs/cdd/CDD-093-…; any conflict = STOP)
B. Apply exactly R1.6 (manual, line-addressed; ruff/isort autofix prohibited), verify the combined
   diff of B against A's result has SHA-256 f4dcab51… when produced as `git diff` default context
   (paths in git order), then ONE commit:
     "ci: required CI-conformance repair -- isort skip_file + remove 16 stale noqa:DTZ001 (CDD-093 R1)"
```

Governance precedes code (A before B). No other commit, no amend of existing commits, no merge of `main` or anything else. The resulting tree MUST equal the final expected tree recorded in the G-R1 report (this document cannot contain the hash of a tree that includes itself); any difference = STOP. Then: AST/token proof (R1.6) on the 15 files; exact backend, frontend, and containers CI contracts per R1.2 with the CI-resolved toolchain and the parity manifest recorded; crowns per R1.8; `make verify-architecture`; clean tree. Push **normally (non-force)** to the existing `governance/oqi-propagated-impact-main-integration` so PR #255 updates in place. No new PR, no closing #255, no branch deletion or recreation.

## R1.10 Exact-head GitHub requirement and CI drift

Before pushing, re-read `.github/workflows/ci.yml` at the intended head and base and branch protection; if any required command, required check, or protection setting changed since G-R1: STOP. After pushing, all required checks (`backend`, `frontend`, `containers`, and any other required check) must be SUCCESS **on the exact new PR #255 head SHA**; pending, cancelled, unexpectedly skipped, or stale (other-SHA) results do not count. Inspect the resolved tool versions in the new GitHub backend log; if any gating tool resolves to a version other than the R1.2 manifest and produces any new finding: STOP (no serial patching without governance). I-R1 does **not** merge.

## R1.11 CI-parity delivery invariant

**IF CI CAN BLOCK MERGE, ITS EXACT COMMANDS BELONG IN PRE-MERGE CERTIFICATION. CI PARITY INCLUDES RESOLVED TOOL VERSIONS, NOT ONLY COMMAND NAMES.** RUFF PASS ≠ ISORT PASS; LOCAL TOOL SUBSET ≠ REQUIRED CI PARITY; COMMAND PARITY WITHOUT VERSION PARITY IS NOT CI PARITY. From R1 onward, every local integration crown and INTEGRATION-VM must run the complete backend, frontend, and containers CI contracts (R1.2) with the CI-resolved toolchain, executing every step even after an earlier step fails, and record a CI parity manifest.

## R1.12 INTEGRATION-VM boundary (extends v1.0 §10.2–§10.4)

INTEGRATION-VM may begin only after I-R1 completes R1.9–R1.10 green. It must independently verify, on the exact PR #255 head: no material `main` drift; the head SHA and final tree; all governance hashes (CDD-087/090/091/092 unchanged; CDD-093 = R1 hash); the 56-path diff and the `a37e4fab…` fingerprint; the R1.6 repair is exactly 15 paths, comment-only, AST/token-identical; implementation semantics unchanged (every non-test, non-`docs/cdd` path byte-identical to the certified candidate tree `ef2e48d6…`); migration head; `make verify-architecture`; the complete CI parity contracts locally with the manifest; required GitHub checks green on the exact head; branch protection; mergeability; plus every v1.0 §10.2 item (Docker images from the exact tree with source-to-image identity, fresh-DB and old-image→new-image persisted upgrade with repeat). Merge only per v1.0 §10.3 (merge commit bound to the verified head SHA), with the immediate pre-merge re-verification of `origin/main`, PR head, governance hashes, required checks, mergeability, branch protection, and exact tree. Any drift: STOP.

## R1.13 Azure boundary (unchanged, restated)

R1 authorizes no backend or frontend redeployment, no Golden Restore, no migrate-job change, no CIAM, demo-database, dev, or production change. Product runtime bytes are unchanged by the repair.

## R1.14 Additional STOP conditions

STOP if: ruff, isort, or any CI step reports anything beyond the frozen set; any repair touches a byte beyond R1.6; any AST/token difference; any runtime, migration, workflow, dependency, configuration, or frontend change; dependency pinning becomes necessary; any CI contract (backend/frontend/containers) fails locally or on GitHub; CDD-091 or CDD-092 crowns regress; `verify-architecture` fails; the resulting tree differs from the G-R1-recorded final tree; `main`, PR #253/#254/#255 heads, governance sources, workflow, or branch protection drift; the final topology cannot include this R1 document.

## R1.15 Deferred (recommendation only — not implemented here)

Make CI tooling deterministic (lockfile, constraints file, or exact/compatible version policy; reproducible dev environment) so that a tool release cannot silently change merge gates. Plus all v1.0 §17 items.

---

*CDD-093 R1 authorizes integration-governance correction only. It implements, pushes, merges, and deploys nothing itself.*
