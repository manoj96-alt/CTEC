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
