# CDD-045 Artifact Authorization Companion — OQI-UX N+1 Test Authorization Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION
**Version:** 1.0
**Extends:** `CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md` (Set A) and
`CDD-045-Artifact-Authorization-OQI-UX-Authorization-ID-Contract-Correction.md` (Set B) — authorizes exactly
two additional pre-existing test files whose own contracts are mechanically/semantically invalidated by Set A
and Set B, discovered mid-implementation during OQI-UX-I-R, not a reopening of either prior document.
**Precedent:** same class of narrow, disclosed, companion-document governance artifact as
`CDD-045-Artifact-Authorization-OQI7-I2-Test-Path-Correction.md`,
`CDD-033-Artifact-Authorization-Gate-X-Runtime-Architecture-Findings-Route-Correction.md`, and the two prior
OQI-UX companions this document itself extends — new file, zero in-place edit of any frozen document.

## 1. Why these two paths are required

OQI-UX-I-R implemented the full, frozen Set A (11 paths) and Set B (7 paths) changeset and, before committing,
ran the complete verification matrix (`tsc --noEmit`, `vitest run`, full backend regression). Two pre-existing
test files outside both frozen sets failed as a direct, unavoidable consequence of contract changes Set A and
Set B already, deliberately authorized:

**`frontend/tests/oqi-product-truth.test.tsx`** — `tsc --noEmit` fails with exactly 3 errors (lines 213, 239,
259, independently reconfirmed this phase): two `<RemediationPanel remediation={...} />` fixtures now missing
the `onMutated` prop Set A's `RemediationPanel` signature change requires, and one authorization fixture
missing the `authorization_id` field Set B's `RemediationAuthorizationView` contract now requires. Pure
type-completeness — no assertion in this file is affected.

**`frontend/tests/browser-session.test.ts`** — two tests hard-code the exact pre-Set-A default OIDC scope
string, and the first is explicitly named "...with no write/decide scope," with an exhaustive `not.toContain`
list of every other optional write/decide scope in the realm (`entity-resolution:decide`,
`supplier-risk:submit/retry/replay`, `ontology-modeling:propose/approve/publish`) that predates
`oqi-remediation:authorize`/`oqi-remediation:report-execution`. Set A's `frontend/lib/auth/config.ts` change
(frozen, already authorized) deliberately adds exactly these two scopes to that same default string — the
test's literal string assertions are now false against the new, correctly-governed contract, and its "no
write/decide scope" claim, if left unmodified, would be actively false rather than merely outdated.

## 2. Independently reconfirmed this phase (not carried from OQI-UX-I-R's disclosure)

`origin/main` and GitHub `main` re-verified unchanged at `0cf2c5ab0b52e9ca9a5738b09a9360e16260d24f`; branch
`oqi-ux/governed-remediation-lifecycle` at tip `0cf2c5ab0b52e9ca9a5738b09a9360e16260d24f`; preserved working
tree matches the OQI-UX-I-R disclosure exactly (20 paths, unchanged); both prior companion hashes reverified
byte-identical (`3b6bcc4493eb0ee5141e0b53bd497dc1978320a407c4c9ff1c5123a93c8421bf` and
`6408b3fd3c3f8f13aabd60174e0f6596fbfc87fc7e3c023875160e909f7658ba`); `npx tsc --noEmit` re-run, producing the
identical 3 errors at the identical 3 lines; `frontend/tests/browser-session.test.ts` read in full, confirming
exactly 2 of its 4 tests hard-code the pre-Set-A scope string (the third, "explicit non-empty
NEXT_PUBLIC_OIDC_SCOPE overrides the canonical default," and the fourth, "browser auth configuration fails
closed," are both unaffected and out of scope). No third N+1 path found.

## 3. Exact authorized correction (Set C)

```
MODIFY frontend/tests/oqi-product-truth.test.tsx
  ALLOWED: add onMutated={() => {}} to the two existing RemediationPanel fixtures that now require the prop;
    add authorization_id: "<stable test string>" to the existing authorization fixture that now requires the
    field. Pure type/contract completeness only.
  FORBIDDEN: weakening, deleting, generalizing, or skipping any existing assertion; any behavioral semantic
    change; any change to any other test in the file.

MODIFY frontend/tests/browser-session.test.ts
  ALLOWED: update the two expected scope-string literals to include exactly
    "oqi-remediation:authorize oqi-remediation:report-execution" appended, matching frontend/lib/auth/
    config.ts's own frozen Set A change exactly; evolve the "with no write/decide scope" test name and its
    not.toContain assertion list so the test continues proving, by exact string equality (not a generalized
    substring/contains relaxation), that no write/decision scope beyond the two explicitly frozen OQI
    remediation scopes (oqi-remediation:authorize, oqi-remediation:report-execution) has entered the default
    scope string -- the existing exhaustive not.toContain list (entity-resolution:decide,
    supplier-risk:submit/retry/replay, ontology-modeling:propose/approve/publish) is preserved unchanged; the
    two OQI remediation scopes are added to the config.scope.toBe(...) exact-string assertions, not to the
    not.toContain exclusion list.
  FORBIDDEN: changing the OIDC scope names themselves; changing the "browser auth configuration fails closed"
    or "explicit non-empty NEXT_PUBLIC_OIDC_SCOPE overrides the canonical default" tests; relaxing any exact
    scope-string assertion into a substring/contains check where an exact match remains possible (it does);
    any change to frontend/lib/auth/config.ts itself (already frozen and implemented under Set A).

CREATE = 0
MODIFY = 2
DELETE = 0
TOTAL  = 2
```

## 4. Combined product authorization

```
Set A (CDD-045-Artifact-Authorization-OQI-UX-Lifecycle-Closure.md):                  CREATE=4, MODIFY=7,  TOTAL=11
Set B (CDD-045-Artifact-Authorization-OQI-UX-Authorization-ID-Contract-Correction.md): CREATE=0, MODIFY=7,  TOTAL=7
Set C (this document):                                                                CREATE=0, MODIFY=2,  TOTAL=2

COMBINED PRODUCT PATHS = 11 + 7 + 2 = 20 (zero overlap across all three sets)
```

Governance paths remain separately accounted: 2 (the two prior companions), not part of the product-path
count; this document is a third governance path, also not part of the product-path count.

## 5. Scope of this correction (binding)

Changes only the two named test files, in exactly the manner in §3. It does **not** change: any Set A or Set
B path (all 18 remain exactly as previously frozen and implemented); `backend/app/domain/**`; any migration;
`keycloak/**`; any Dockerfile/compose/entrypoint/CI-workflow/seeder/smoke-doc path; any API route beyond the 3
already frozen in Set B; tenant enforcement; remediation semantics; authorization semantics; the source-write
boundary; case-state/lifecycle semantics; the two OQI-UX-frozen scope *names* (only the two already-authorized
Set A `config.ts` values, now also reflected in this test's expectations); or either prior governance
companion, both confirmed byte-identical in §2.

## 6. Why this is safe

Both corrections are the same class already established twice in this exact implementation: `oqi-finding-
detail.test.tsx`'s two evolved assertions (authorized under Set A) applied the identical principle -- a
pre-existing test's *specific claim* is preserved and re-targeted at what it actually protects, never
generalized away. `oqi-product-truth.test.tsx`'s fix touches zero assertions. `browser-session.test.ts`'s fix
preserves exact-string equality throughout (no relaxation to `.toContain`), and its exhaustive exclusion list
for every *other* unauthorized scope is untouched -- the security boundary the test protects (no scope beyond
an explicit, governed, minimal set) is fully preserved, merely updated to reflect that the governed set now
correctly includes the two OQI remediation scopes Set A already, deliberately added.

## 7. Authorization

The exact 2 paths in §3 are authorized for implementation as part of OQI-UX-I2-R, verification by OQI-UX-VM,
and merge to `main` upon independent adversarial confirmation, strictly within the constraints of §3 and §5
above. This document does not authorize any 21st product path, any change to CDD-045, its Artifact
Authorization, either prior OQI-UX companion, any OQI1-7 domain class, any migration, `keycloak/
ctec-realm.json`, or any Docker-G artifact.
