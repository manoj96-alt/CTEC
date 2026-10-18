# CDD-090 — Governed Authority-Binding Azure Golden Demo Deployment Authorization

**Status:** FROZEN
**Originating phase:** NOETVA-GOVERNED-AUTHORITY-BINDING-GD-R1 (governance/deployment-authorization only — implements nothing, deploys nothing)
**Authorizes:** NOETVA-GOVERNED-AUTHORITY-BINDING-D-R1 (the sole next phase permitted to act on this authorization)
**Scope:** Freezes the exact integration candidate, authorized paths, deployment target, image-traceability requirements, post-deployment reset authority, and VM restart crown for deploying the governed authority-binding security correction to the dedicated Azure Golden Demo environment only. Does not reopen CDD-087 or any of its mechanism decisions. Does not authorize a main merge, a dev deployment, or correction of any deferred item listed in §9.

---

## 1. Numbering-uniqueness verification (performed, not assumed)

Highest CDD on `origin/main`: CDD-086. Independently re-checked every remote branch (`git for-each-ref refs/remotes/origin/`) for any file matching `CDD-09[0-2]`: zero matches anywhere. The only branch with CDD numbers above 086 is `product/wow-i4-b1` (open PR #245), which claims CDD-087, CDD-088, and CDD-089 — none of them this document's number. **CDD-090 is confirmed unclaimed anywhere in this repository's remote branch set at freeze time.**

## 2. Authoritative baseline (independently re-derived, not trusted from the prior phase's report)

```
origin/main                 = 171a398af6d4af6bd2149ff69879f4cdc178ed3e
PR #253                     = OPEN, MERGEABLE (azure/golden-demo-parity-g)
PR #254                     = OPEN, MERGEABLE (azure/golden-demo-parity-i1)
CDD-087 SHA-256              = cb38bc3ecaf4b8498d8626832eb5fc2cb61f5cdb6ced27d625517b91cc8daec4
Security correction branch  = security/governed-authority-binding-i-r1
Security correction commit  = ec896e21bae36910241e614cef2ab401d448dbd6
                               (merge-base with origin/main: 171a398af6d4af6bd2149ff69879f4cdc178ed3e — confirmed
                               branched directly from main, not from the Golden Demo branch)
```

All four match the NOETVA-GOVERNED-AUTHORITY-BINDING-I-R1 report exactly. No drift.

## 3. Security correction diff — independently re-verified

`git show --stat ec896e21bae36910241e614cef2ab401d448dbd6`: exactly 6 files (1 created, 5 modified, 0 deleted) —
`backend/app/api/oqi/router.py`, `backend/app/api/oqi/schemas.py`,
`backend/app/tests/test_oqi_remediation_identity_binding_postgres.py` (created),
`frontend/app/quality/findings/[findingId]/_components/decide-authorization-dialog.tsx`,
`frontend/lib/oqi/contracts.ts`, `frontend/tests/oqi-remediation-actions.test.tsx`.
Exact match to the I-R1 report's own §D. No unrelated path.

## 4. Security-test reconfirmation (re-run this phase, not merely re-cited)

Against the integration candidate (§5), not the isolated security branch alone:
`test_oqi_remediation_identity_binding_postgres.py` (4/4), `test_noetva_demo_readiness_golden_story.py` (18/18),
`test_database_cli_postgres.py`+`test_database_cli.py` (golden-restore/demo-verify suite) — **29/29 passed combined**,
zero failures. `black`/`mypy` clean on every changed file. Re-confirms, on the actual deployable candidate:
same-principal decide fails closed (`REMEDIATION_SELF_APPROVAL_PROHIBITED`, no candidate becomes `APPROVED`, no
sibling becomes `SUPERSEDED`); distinct-principal decide succeeds with exactly one `APPROVED` + sibling
`SUPERSEDED` (never `REJECTED`); a client-supplied `decided_by` in the request body cannot control the
persisted actor (proven by direct read of `OqiRemediationAuthorizationORM.decided_by` from real PostgreSQL);
the same binding holds on the reject path.

## 5. Golden Demo integration analysis and candidate strategy (§7/§H)

`azure/golden-demo-parity-i1` (PR #254, commit `4bf410a09712acb9ca22961c032160d7438040d5`) and
`security/governed-authority-binding-i-r1` (`ec896e2...`) share the **identical** merge-base
(`171a398...` = `origin/main`) and, independently verified via `comm -12` on their respective
`git show --name-only` file lists, touch **zero common files**. A floating-tag or main-built image would either
lose the Golden Demo restore mechanism (if built from the security branch alone) or carry the uncorrected
self-authorization defect (if built from the Golden Demo branch alone) — both unacceptable.

**Selected strategy: A** — a temporary local integration branch,
`governance/authority-binding-golden-integration`, created by merging `security/governed-authority-binding-i-r1`
into a copy of `azure/golden-demo-parity-i1`. Because the two commits are file-disjoint, the merge is conflict-free
by construction. Resulting merge commit: **`56d7adc21fc5ea62cffc0da21da7776eb93c367f`**
(parents: `4bf410a...`, `ec896e2...`). Independently re-diffed against `origin/main`: exactly the union of both
commits' changes (5 created, 9 modified, 0 deleted) — no third file, no unrelated change. This is a **local-only**
branch; it has not been pushed and is not a main-merge candidate.

## 6. Exact authorized path set for D-R1

No new source authorization beyond what CDD-087 (Golden Demo infra) and this document's §3 (security correction)
already each separately authorized. D-R1 may build and deploy exactly commit `56d7adc21fc5ea62cffc0da21da7776eb93c367f`
(or, if the operator instead merges these branches through the repository's normal PR mechanism before D-R1 runs,
whatever resulting commit is byte-for-byte equivalent in file content to this merge). D-R1 introduces **zero**
new source files of its own.

## 7. Deployment target freeze

**`rg-noetva-demo` only.** Explicitly excluded: `rg-noetva-dev`, any production/shared environment, any DNS
mutation, any claims-mapping-policy mutation, any `optionalClaims` mutation, any Key Vault mutation unless D-R1
independently proves one is structurally required merely to roll the already-certified images (none is expected —
this correction introduces no new secret, no new Key Vault reference, no new environment variable).

## 8. Image build/push/digest requirements

D-R1 must build immutable `linux/amd64` images from commit `56d7adc21fc5ea62cffc0da21da7776eb93c367f` (no floating
tag), push to `noetvademoeus2acr.azurecr.io`, resolve and record the real manifest-list digest for both backend
and frontend, independently verify each child manifest is `Architecture: amd64, Os: linux` (the same discipline
already established in this program's prior real builds), and bind `rg-noetva-demo`'s Container Apps to the
resolved digests — never a mutable tag. Source-to-image traceability requirement: D-R1's own report must state
both digests and the exact commit SHA they were built from.

## 9. Failed-VM-state preservation rule

The current `rg-noetva-demo` state (`MX = AUTHORIZED`, `US = SUPERSEDED`, no execution report, no re-evaluation —
the live artifact of the proven self-authorization defect) **must not be touched** until the corrected images are
deployed and independently verified healthy (`/health` 200 on both apps; unauthenticated protected call still
`401`). Only after that health verification may D-R1 invoke the golden-restore mechanism.

## 10. Post-deployment restore authority

Frozen sequence, exactly in this order:
```
deploy corrected images (§8)
  -> verify frontend/backend health
  -> verify an unauthenticated protected call is still 401 (fail-closed unregressed)
  -> trigger the existing noetva-demo-eus2-golden-restore Container Apps Job (unchanged mechanism, CDD-087 §7-§9)
  -> read its own demo-verify log output -- require literal "ALL CHECKS PASSED"
  -> hand control to AZURE-GOLDEN-DEMO-PARITY-VM for the restart crown (§11)
```
No direct SQL cleanup. No manual remediation-table editing. No mechanism other than the existing governed
`golden-demo-restore` CLI command, invoked exactly as CDD-087 already authorized.

## 11. VM restart crown (frozen for the resuming VM phase, not executed by D-R1 itself)

After §10 completes, `AZURE-GOLDEN-DEMO-PARITY-VM` resumes from the remediation lifecycle crown: Demo Steward
prepares (expect `MX`/`US` both `PENDING`) → Demo Steward attempts self-approval (expect fail-closed,
`REMEDIATION_SELF_APPROVAL_PROHIBITED`, both candidates still `PENDING`) → Demo Approver approves exactly one
(expect that candidate `APPROVED`, sibling `SUPERSEDED`, persisted authorizer equal to the Approver's own
server-authenticated principal) → report execution → re-evaluation → Finding remains `OPEN` while
SAP=US/PLM=MX remain unchanged, Reliance stays truthful to that unresolved state.

## 12. Dev non-interference requirement (binding on D-R1)

D-R1 must re-verify, before and after its own deployment actions: `rg-noetva-dev` resource-group state
unchanged; dev's claims-mapping-policy (`NoetvaTenantClaimMapping`) and its assignment to the dev backend SP
unchanged; no dev app registration, dev database, or dev DNS touched. Any unexplained dev-side change is an
automatic D-R1 failure, not a warning.

## 13. Gate S follow-up governance item (frozen here, not resolved here)

**Location:** `app/api/gate_s/router.py` line ~144-146, source: `app/api/gate_s/schemas.py`.
**Pattern:** `requested_by=request.requested_by` and `decided_by=request.decided_by` — both client-body-sourced,
materially identical in shape to the OQI defect this document's correction fixes.
**Potential impact:** the same class of self-authorization-guard bypass and audit-attribution spoofing risk,
in whatever governed-approval workflow Gate S backs — not yet characterized.
**Required future action:** a dedicated discovery phase (its own DR/G/I/VM sequence, scoped only to Gate S)
must independently characterize Gate S's actual blast radius before any fix is authorized. **Not to be combined
with, or silently folded into, the Azure Golden Demo deployment this document authorizes.**

## 14. Deferred items (carried forward, explicitly not touched by D-R1)

OQI propagated-impact limitation (`propagated_path = None`); active-principal visibility UX gap; demo backend's
`CTEC_ENVIRONMENT=development` anomaly; `optionalClaims` cleanup on the demo app registrations; the CDD-087
numbering collision with `product/wow-i4-b1` (already self-governed by CDD-087 §1's own renumber-at-merge-time
rule — re-check live state immediately before any actual PR #253 merge); §13's Gate S item.

## 15. Explicitly prohibited actions (binding on D-R1 and on any later phase citing this document)

No merge of any branch into `main`. No deployment to `rg-noetva-dev` or any production/shared environment. No
correction of Gate S (§13). No correction of the propagated-impact limitation. No unrelated cleanup bundled into
the same deployment. No floating-tag deployment. No restore before the post-deployment health check (§9).

## 16. Next-phase authorization

**NOETVA-GOVERNED-AUTHORITY-BINDING-D-R1** is authorized to, and only to: build, push, and deploy the exact
images traced to commit `56d7adc21fc5ea62cffc0da21da7776eb93c367f` to `rg-noetva-demo`; verify health; invoke
the existing golden-restore mechanism; hand off to `AZURE-GOLDEN-DEMO-PARITY-VM` for the restart crown (§11).
No competing or parallel VM phase may be created.

---

*This document authorizes governance and deployment scope only. It does not itself build, push, deploy, or
restore anything.*
