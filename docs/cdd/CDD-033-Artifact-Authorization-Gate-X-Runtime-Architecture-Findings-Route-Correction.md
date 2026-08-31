# CDD-033 Artifact Authorization Amendment — Gate X Runtime-Architecture Findings-Route Correction

**Status:** APPROVED GOVERNANCE AMENDMENT
**Version:** 1.0
**Amends:** `frontend/tests/gate-x-runtime-architecture.test.tsx` (CDD-033 Artifact Authorization §5 item 29)
— narrowly, mechanically, aligning this one executable test's `/quality/findings` route prohibition with
governance that already superseded it in prose; does not reopen CDD-033's architecture, its Artifact
Authorization's other 28 items, the CDD-033 OQI7 companion amendment, CDD-045, or the OQI7 Artifact
Authorization's 18-path product/test accounting
**Precedent:** same class of narrow, disclosed, companion-document correction as
`CDD-043-Artifact-Authorization-I2-Accounting-Correction.md` and
`CDD-045-Artifact-Authorization-OQI7-I2-Test-Path-Correction.md` — an implementation-discovered
misalignment in already-frozen governance, corrected via companion document rather than in-place edit

## 1. Discovered defect

At OQI7-I2 implementation (second attempt, after the OQI7-GC1 test-path correction), the corrected 18-path
implementation was built exactly as authorized and placed uncommitted in the working tree. Running the full
frontend suite against it surfaced two failures in `frontend/tests/gate-x-runtime-architecture.test.tsx`, a
file CDD-033's own Artifact Authorization §5 item 29 describes as "frontend file-boundary enforcement
mirroring the backend's own `AUTHORIZED_CHANGED_PATHS` discipline, scoped to exactly this §5 allowlist."

Independent investigation in an isolated git worktree (a clean checkout of authoritative main, with zero
diff and zero untracked files, so the preserved OQI7-I2 implementation was never touched) established that
**one of the two failures was a genuine, permanent conflict and the other was a false alarm caused by the
uncommitted local diff, not a real architectural boundary**:

**Genuine, permanent conflict** — the test's `"never creates an active route for a PLANNED generalized-DQ
capability"` assertion performs a literal `existsSync()` check against three hard-coded paths:

```tsx
it("never creates an active route for a PLANNED generalized-DQ capability", () => {
  for (const forbidden of [
    "frontend/app/quality/rules/page.tsx",
    "frontend/app/quality/findings/page.tsx",
    "frontend/app/quality/impact/page.tsx",
  ]) {
    expect(existsSync(join(REPOSITORY_ROOT, forbidden))).toBe(false);
  }
});
```

This assertion directly encodes CDD-033's own historical route table (Artifact Authorization §8: `/quality/
rules — PLANNED, NO ACTIVE ROUTE`, `/quality/findings — PLANNED, NO ACTIVE ROUTE`, `/quality/impact —
PLANNED, NO ACTIVE ROUTE`) and its §14 prohibition. CDD-045's own Artifact Authorization explicitly
authorizes CREATE of `frontend/app/quality/findings/page.tsx` as a live route — so this assertion will
deterministically and permanently fail on any commit, any branch, any CI run (not merely a local uncommitted
diff) from the moment that file exists on disk, until the assertion itself is corrected.

**False alarm, requiring no correction** — the test's `"touches only the frozen Artifact Authorization
allowlist plus the authorized exceptions"` assertion computes changed paths via `git diff --name-only HEAD`
plus `git ls-files --others --exclude-standard` — i.e., the *local working-tree diff relative to HEAD*, not
a comparison across git history or against any committed baseline. Proven directly, in the isolated
worktree: on a genuinely clean checkout of authoritative main (zero diff, zero untracked files), all 5 tests
in this file pass trivially, regardless of the allowlist's contents, because there is no changed path to
check against it at all. This assertion is a local-development tripwire — useful during a phase's own active
implementation to catch stray unintended file changes — not an ongoing architectural boundary enforced
against any properly committed and merged code. It will pass normally on OQI7-I2's own PR CI (a clean
checkout of that PR's head commit) and on authoritative main after merge, without requiring the
`AUTHORIZED_CHANGED_PATHS` allowlist to be extended with any OQI7 path. This resolves the interpretation
question this correction was required to answer (cumulative architecture boundary vs. Gate-X-only historical
footprint vs. other): neither — it is a local-diff-only development-time check, and it needs no
modification for this correction to be sufficient.

## 2. Independent proof of the corrected scope

Performed in an isolated git worktree at authoritative main `40190f55da3b2b4d495a5ccd372acd7842757abc`
(detached HEAD, zero diff, zero untracked files throughout — the preserved OQI7-I2 implementation in the
primary working tree was never read from or written to during this investigation):

1. Clean-checkout baseline: all 5 `gate-x-runtime-architecture.test.tsx` tests pass (proves the allowlist
   test is not a standing failure and needs no change).
2. A dummy `frontend/app/quality/findings/page.tsx` was created (never the preserved OQI7-I2 file itself) and
   the isolated `"never creates an active route..."` assertion was run alone: it fails exactly as predicted,
   independent of git diff status.
3. The assertion was corrected to remove only the `frontend/app/quality/findings/page.tsx` entry. Re-run:
   passes with the dummy file present.
4. Dummy `frontend/app/quality/rules/page.tsx` and `frontend/app/quality/impact/page.tsx` files were then
   created and the same assertion re-run: **both still fail closed** — the guardrail's protection against
   the two routes OQI7 does *not* authorize (Rules-authoring and a standalone Impact page are both
   explicitly out of OQI7's scope per the OQI7-D discovery phase's own Product Owner decisions) is fully
   preserved.
5. All dummy files were removed; the full Gate X governance suite (`gate-x-navigation.test.tsx`,
   `gate-x-honesty.test.tsx`, `gate-x-runtime-architecture.test.tsx`) was re-run together: **19/19 pass**.

## 3. Exact correction

```
frontend/tests/gate-x-runtime-architecture.test.tsx:

REMOVE from the "never creates an active route for a PLANNED generalized-DQ capability" forbidden-path
array:
  "frontend/app/quality/findings/page.tsx"

RENAME the test description to:
  "never creates an active route for a PLANNED generalized-DQ capability not authorized by governance"

ADD a one-paragraph comment immediately above the test explaining the CDD-045/CDD-033-companion-amendment
supersession for /quality/findings specifically, and that /quality/rules and /quality/impact remain
unauthorized.

NO OTHER CHANGE to this file: the AUTHORIZED_CHANGED_PATHS allowlist (lines 12-50), the
"touches only the frozen Artifact Authorization allowlist" test, the "contains exactly the 29 authorized
Gate X product artifacts on disk" test, the "never touches a backend, persistence, migration, or Keycloak
path" test, and the "preserves every legacy deep-link route relocated across PR1-PR4" test are all
unmodified.
```

## 4. Scope of this correction (binding)

Changes only the one named assertion in `gate-x-runtime-architecture.test.tsx`. It does **not** change:

- the `AUTHORIZED_CHANGED_PATHS` allowlist or its 29-item accounting (CDD-033 Artifact Authorization §5) —
  proven unnecessary by direct testing (§2 above), not merely assumed;
- the `/quality/rules` or `/quality/impact` route prohibitions — both remain enforced exactly as before,
  independently re-verified (§2.4 above);
- any other CDD-033 decision, route, or firewall (§5 items 1-28, §6-24 all unaffected);
- the already-published `CDD-033-OQI7-Placeholder-Supersession-Amendment.md`, which correctly superseded the
  *prose* prohibition in CDD-033's own Artifact Authorization §8/§14 — this correction only extends that
  same, already-approved supersession to the one *executable* assertion that still encoded the historical
  prohibition in code;
- CDD-045 or its Artifact Authorization — both remain byte-identical and unmodified;
- the `CDD-045-Artifact-Authorization-OQI7-I2-Test-Path-Correction.md` (GC1) companion — unrelated, also
  unmodified;
- the corrected OQI7-I2 product/test-file accounting (still `CREATE=16, MODIFY=2, DELETE=0, TOTAL=18` —
  `frontend/tests/gate-x-runtime-architecture.test.tsx` is a Gate X governance artifact, not an OQI7 product
  path, and is corrected here, in GC2, precisely so OQI7-I2's own authorization does not need to grow to 19
  paths to accommodate an unrelated governance-boundary alignment);
- historical CDD-033 itself, which remains frozen and unedited throughout.

## 5. Why this is safe

The correction is proven, not assumed, by direct adversarial testing in an isolated workspace: the guardrail
continues to fail closed for every path it protected before this correction (`/quality/rules`,
`/quality/impact`, and — via the unmodified allowlist test — any unrelated unauthorized local diff), and
passes only for the one route CDD-045's own frozen governance has already, separately, explicitly
authorized. No new implementation surface is introduced by this document itself; it only aligns an
executable check with a supersession this repository's own governance already approved in prose.

## 6. Authorization

`frontend/tests/gate-x-runtime-architecture.test.tsx`'s `"never creates an active route for a PLANNED
generalized-DQ capability"` assertion is corrected to exclude `frontend/app/quality/findings/page.tsx` from
its forbidden-route list, effective immediately, per the exact diff in §3. `frontend/app/quality/rules/
page.tsx` and `frontend/app/quality/impact/page.tsx` remain prohibited by this same assertion. No other file,
allowlist entry, route, or governance decision is affected. This document does not authorize any OQI7-I2
product implementation change — the preserved OQI7-I2 implementation (16 CREATE + 2 MODIFY, unchanged by
this correction) remains gated behind its own separate Product Owner continuation authorization.
