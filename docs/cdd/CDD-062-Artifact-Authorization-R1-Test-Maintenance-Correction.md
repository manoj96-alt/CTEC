# CDD-062 Artifact Authorization Companion — R1 Test-Maintenance Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION (narrow correction)
**Version:** 1.0
**Governed via:** `PRODUCT-WIDE-UX-I` (STOPPED correctly, evidence preserved, not lost) →
`PRODUCT-WIDE-UX-G-R1` (this document) → `PRODUCT-WIDE-UX-I-R1` (authorized by this document) →
`PRODUCT-WIDE-UX-VM`.
**Extends, does not edit:** `docs/cdd/CDD-062-Product-Wide-UX-Hardening-Artifact-Authorization.md`
(parent, byte-unchanged, hash re-verified below). This is test-maintenance authorization only — it changes
no product decision CDD-062 froze.
**Precedent-class:** same narrow, disclosed, companion-document pattern as every `*-Correction.md`/
`*-Amendment.md` file already in `docs/cdd/` (e.g. `CDD-050-...-Correction-Amendment.md`,
`CDD-059-Artifact-Authorization-I-R1-SSRF-Test-Boundary-Correction-Amendment.md`) — new file, zero in-place
edit of any frozen document, same number as its parent.

## 0. Governance hashes (re-verified this phase, not assumed)

Authoritative main at phase start: `2edd28c25f7f5a5d18d38fdce4d160d29a92eb72` — independently confirmed via
both `git rev-parse origin/main` and `gh api repos/manoj96-alt/CTEC/git/refs/heads/main`. Unmoved since
`PRODUCT-WIDE-UX-G`.

```
f4096164c4b39c9669da762ba40a5c8e7e074024be6696c39fa0ddf9a2b2f92f  docs/cdd/CDD-062-Product-Wide-UX-Hardening-Artifact-Authorization.md
220f2e41ecc641b64ee38ead504be96037a7e4ef45b6ddb61e681d1d3c600243  docs/cdd/CDD-033-Enterprise-UX-Governed-Product-Experience.md
5dd2d76a0ac46079833be69086ea4356d4907888b73d205e365ae9901de895c7  docs/cdd/CDD-033-Enterprise-UX-Governed-Product-Experience-Artifact-Authorization.md
44fd13ec08eda34f31ed2c522edbb8e8e80ded4347d48138c5be0d2b8be43e24  docs/cdd/CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience-Artifact-Authorization.md
3b6bcc4493eb0ee5141e0b53bd497dc1978320a407c4c9ff1c5123a93c8421bf  docs/cdd/CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md
2e2ce41f182210af1553e0a6c9bf37ac1ede6a8f4e3f7a860587a784c5663a63  docs/cdd/CDD-014-INFORMATION-ARCHITECTURE-AND-ROUTE-MAP.md
869b24c56d66bcf82f5901051d5ae1cd8789a8e6539714a2eaf62f4403824478  docs/cdd/CDD-014-ACCESSIBILITY-AND-RESPONSIVE-DESIGN-SPECIFICATION.md
81af53b0edb8e2b0f12f8b3e784df2aecd5ff2dea3b494435624b00903db30aa  docs/cdd/CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md
```

All 8 hashes match CDD-062 §0 and its own referenced set exactly. No drift. No historical artifact is
edited by this document.

## 1. Preserved I-phase evidence

`PRODUCT-WIDE-UX-I` STOPPED correctly before commit, per its own governing instructions, rather than
expanding its authorized path ceiling. Its worktree was preserved, untouched, as read-only evidence for
this phase:

```
Worktree: /private/tmp/claude-501/-Users-manojvelayudhannair-Developer-CTEC/f909d579-183d-49f9-98ef-70483e06aa6c/scratchpad/uxi-main
Branch:   product-wide-ux-i
HEAD:     2edd28c25f7f5a5d18d38fdce4d160d29a92eb72  (== authoritative main, confirmed unmoved)
```

Re-verified this phase, from that untouched worktree, without modifying it:

```
git status --short / git diff --name-status:
 M frontend/app/context/_components/context-lookup.tsx
 M frontend/app/data/page.tsx
 M frontend/app/globals.css
 M frontend/app/intelligence/decisions/page.tsx
 M frontend/app/layout.tsx
 M frontend/app/ontology-studio/_components/ontology-graph.tsx
 M frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
 M frontend/components/design-system/capability-status-badge.tsx
 M frontend/components/site-shell.tsx
 M frontend/tests/ontology-studio.test.tsx
 M frontend/tests/oqi-remediation-actions.test.tsx
```

Exactly the 9 product paths + 2 test paths CDD-062 authorized. No unauthorized path present. No CREATE, no
DELETE.

**Patch fingerprint, frozen for I-R1 to re-verify against:**

```
Method: `git diff --no-color` run from the preserved worktree above (working tree vs. its own HEAD,
        2edd28c25f7f5a5d18d38fdce4d160d29a92eb72), captured to a file, then SHA-256'd. Deterministic as
        long as the worktree itself is not touched between phases (per this document's own instruction to
        I-R1: treat the worktree as read-only evidence, do not rebase/reset/reformat it).

SHA-256(git diff --no-color): 2b62c7eace8c2ffe58bba33b06559fd914ec8ebaab98b21ebed3d12cea2402d7
```

I-R1 must reproduce this exact hash from the same worktree before touching anything. If it differs, I-R1
must STOP — the preserved evidence would have been altered outside this governed sequence.

## 2. Site-shell failure — independently reproduced, not assumed from the I report

Read directly, this phase, from clean `origin/main` (`frontend/tests/site-shell.test.tsx`, unmodified):
exactly one assertion references the pre-CDD-062 footer literal —

```ts
expect(
  screen.getByText(/Enterprise Cognitive Operating Model prototype/),
).toBeInTheDocument();
```

— out of six total assertions in the test (`Primary`/`Secondary` nav roles, `Home`/`Intelligence`/
`Architecture`/`Prototype` link hrefs, `"Page content"`, and this footer regex). None of the other five is
affected by anything CDD-062 authorized.

Read directly from the preserved I-phase worktree's `frontend/components/site-shell.tsx`: the implemented
footer text is `Noetva — Governed Enterprise Understanding` — byte-identical to CDD-062 §4's frozen
replacement string.

**Causal conclusion, proven not assumed:** OLD TEST ASSERTION (asserts a string CDD-062 explicitly
authorized removing) + GOVERNED NEW FOOTER (correctly implemented exactly as frozen) = a purely mechanical
regression-test failure. The product is displaying exactly the governed copy. No route, no authority
boundary, no capability semantic, no backend contract is implicated anywhere in this test or its failure.
This is not a product defect.

## 3. Historical precedent — inspected directly, used as supporting evidence only

`frontend/tests/gate-x-runtime-architecture.test.tsx`, read directly from clean `main`, contains (verbatim):

```ts
// X-PR5-D1: narrowly authorized regression-test maintenance exception,
// a mechanically necessary consequence of item 1's nav rewrite -- not a
// 30th Gate X product artifact.
"frontend/tests/site-shell.test.tsx",
```

This is a real, prior, on-point governance decision in this same repository: a `site-shell.tsx` nav change
(item 1 of that phase's own authorization) mechanically forced a `site-shell.test.tsx` update, and the
governing authority at the time recorded that as a narrow test-maintenance exception, explicitly distinct
from — and not counted against — the frozen product-artifact ceiling of that phase. This precedent is
treated here as supporting evidence for the *shape* of the correct decision, not as self-executing authority
— the reasoning in §2 and §6 stands on its own regardless of this precedent's existence.

## 4. Gate-X runtime architecture — independently analyzed; Outcome A frozen

Read directly, this phase, the actual `gitChangedPaths()` implementation in
`frontend/tests/gate-x-runtime-architecture.test.tsx`:

```ts
function gitChangedPaths(): string[] {
  const tracked = execSync("git diff --name-only HEAD", { cwd: REPOSITORY_ROOT, encoding: "utf-8" });
  const untracked = execSync("git ls-files --others --exclude-standard", { cwd: REPOSITORY_ROOT, encoding: "utf-8" });
  return [...tracked.split("\n"), ...untracked.split("\n")].filter(Boolean);
}
```

This diffs the **working tree against its own HEAD**, plus untracked files — not a fixed historical
baseline, not `origin/main` at some earlier commit. Once the I-R1 candidate is committed (HEAD advances to
include the new commit, working tree becomes clean, nothing is untracked), `git diff --name-only HEAD`
returns empty and `git ls-files --others` returns empty — `changed` is `[]`, the `for` loop over it never
executes an assertion, and **the test passes vacuously**. This is exactly the same mechanism, independently
re-confirmed here, that CDD-062 §16 already predicted, and the identical mechanism this program's Azure
workstream diagnosed repeatedly for the backend's analogous `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists`
(same "working tree, not committed baseline" root cause, confirmed harmless once committed, every time it
was checked against real CI in this repository's history).

**Outcome A is frozen: NO FILE CHANGE REQUIRED.** The Gate-X allowlist itself does not need updating. This
failure is expected during I-R1's local/dirty-tree verification and is expected to resolve on its own once
committed to a clean checkout — I-R1 must reproduce and re-confirm this exact mechanism against its own
real commit (not merely assume it), but no second test-authorization gap exists here. Per §8 of the
governing prompt: this closes the risk of a predictable second STOP.

## 5. Governance decision

CDD-062 omitted exactly one mechanically dependent regression-test path from its otherwise-correct freeze.
Authorized, and only, by this document:

**MODIFY: `frontend/tests/site-shell.test.tsx`**

Restricted strictly to: replacing the stale `screen.getByText(/Enterprise Cognitive Operating Model
prototype/)` assertion with an equivalent assertion matching the exact, already-frozen new footer text,
`Noetva — Governed Enterprise Understanding`. Suggested, non-mandatory exact form (I-R1 may use an
equivalent regex/string match, but must not weaken specificity):

```ts
expect(
  screen.getByText(/Noetva — Governed Enterprise Understanding/),
).toBeInTheDocument();
```

**No other assertion in this file may change.** No test deletion, no `.skip`/`.only`, no snapshot
regeneration, no navigation-assertion change, no accessibility-assertion change, no weakening of
specificity (e.g. replacing an exact/regex match with a vague substring or a non-text-based assertion).

## 6. Updated implementation ceiling

```
PRODUCT PATHS (CDD-062, unchanged):        9 MODIFY
ORIGINALLY AUTHORIZED TEST PATHS (CDD-062): 2 MODIFY
R1 TEST-MAINTENANCE EXCEPTION (this doc):   1 MODIFY
---------------------------------------------------
CREATE = 0
MODIFY = 12
DELETE = 0
TOTAL  = 12
```

The only newly authorized path anywhere in this document is `frontend/tests/site-shell.test.tsx`. Every
other CDD-062 authorization — the exact 9 product paths, the exact 2 originally-authorized test paths, every
frozen string/mapping/token/architecture decision, and every deferral — remains byte-for-byte unchanged and
is restated by reference, not reproduced or re-litigated here.

## 7. Product-semantics non-change confirmation

This document authorizes zero change to: the Noetva branding decision, the footer wording itself (already
frozen by CDD-062 §4 — this document only lets the *test* catch up to it), the capability taxonomy or its
visual mapping, the semantic tokens, remediation lifecycle semantics, active-navigation rules, loading-state
decisions, the ontology legend, raw-status treatment, the Context/UX-06 deferral, the UX-14 closure, or the
Golden-Thread/demo-data narrative decision. Every CDD-062 deferral (§9) remains deferred, unchanged, and is
not touched by this correction.

## 8. Truth contract (restated, binding)

`AGENT RECOMMENDATION ≠ AUTHORIZATION` · `REMEDIATION ≠ RESOLUTION` · `DEFERRED CAPABILITY ≠ PRODUCT
CAPABILITY` · `DEMO DATA ≠ REAL ENTERPRISE DATA` · `DOCKER-VERIFIED ≠ AZURE-PRODUCTION-DEPLOYED` ·
`RECOMMENDATION ≠ CERTAINTY` · `SUCCESSFUL REMEDIATION ≠ RESOLUTION` — and every other distinction in
CDD-062 §2, restated there in full and not weakened by this narrow test-maintenance correction.

## 9. STOP conditions carried into I-R1

I-R1 must STOP, not improvise, if: the preserved worktree's patch fingerprint (§1) does not match
`2b62c7eace8c2ffe58bba33b06559fd914ec8ebaab98b21ebed3d12cea2402d7` when re-derived by the same method; more
than the single named assertion in `site-shell.test.tsx` requires change; the Gate-X runtime architecture
test fails for any reason other than the working-tree-diff mechanism analyzed in §4 once committed; any
other full-regression failure surfaces that was not already known (the pre-existing, already-diagnosed
frozen-allowlist symptom is the only category of "expected" failure — any different failure is new evidence
requiring its own governance, not something to route through this document); or any product file outside
CDD-062's original 9 requires touching.

## 10. Future I-R1 and VM requirements

I-R1 must: re-establish authoritative main; re-verify this document's hash and CDD-062's hash; re-derive the
preserved implementation's patch fingerprint and confirm it matches §1 exactly; modify only
`frontend/tests/site-shell.test.tsx` as newly authorized here; re-run the complete verification suite
(`prettier --check`, `eslint --max-warnings=0`, `tsc --noEmit`, `next build`, both CDD-062-authorized test
files, the newly-corrected `site-shell.test.tsx`, `gate-x-navigation.test.tsx`, `gate-x-honesty.test.tsx`,
`gate-x-runtime-architecture.test.tsx`, and the complete frontend regression suite) and require **full
green** — no known/expected/waived failure is acceptable at I-R1, since the one previously-expected failure
mode (§4) is only actually resolved once real work is committed, which I-R1 (unlike I) will do; commit, push,
open a PR against authoritative main; and explicitly not merge, handing off to `PRODUCT-WIDE-UX-VM` for the
full CDD-062 §17 Docker + real-browser verification, which remains entirely unperformed by both I and this
G-R1 phase.
