# CDD-091 — Noetva OQI Demo UX Hardening: Authorization-Dialog and Trusted-Identity Governance

**Status:** FROZEN
**Originating phase:** NOETVA-OQI-DEMO-UX-HARDENING-G (governance only — authorizes I1/I2, implements nothing)
**Follows:** NOETVA-OQI-DEMO-UX-HARDENING-DR; AZURE-GOLDEN-DEMO-PARITY-VM (PASS + CLOSED)
**Scope:** The Human Authorization dialog's interaction/state UX, active-principal visibility, and trusted human-readable audit attribution for OQI remediation. Does not reopen the authority-binding security correction (`ec896e2`/CDD-090) — it is reaffirmed, not re-decided, here.

---

## 1. Problem statement

Three defects and one architecture gap were discovered live, after Azure Golden Demo Parity VM certification:

1. After the backend correctly rejects a self-approval attempt (`REMEDIATION_SELF_APPROVAL_PROHIBITED`), the dialog's `Confirm: Approve` control remains enabled, visually inviting the user to repeat a forbidden action the server has already refused.
2. The Approve/Reject radio controls render visually detached from their labels, with no deliberate initial state and no CTA that names the selected action.
3. The authenticated shell shows only a "Sign out" control — no visible indication of which principal (Demo Steward, Demo Approver, or another user) is currently signed in.
4. Durable audit attribution displays only the opaque server-validated principal id (e.g. `Authorized by TKdj6d4rM5NYg_...`) as the primary, user-facing label.

## 2. Certified security invariants (reaffirmed, not reopened)

`requested_by` and `decided_by` remain derived exclusively from `authenticated.principal_id` (the validated access token's `sub`), never from client input (CDD-090, commit `ec896e2`). The self-approval guard (`requested_by == decided_by` → `REMEDIATION_SELF_APPROVAL_PROHIBITED`) is unchanged. Exactly one candidate may become `APPROVED`; its sibling becomes `SUPERSEDED`, never `REJECTED`. Authorization never executes; execution reporting never establishes truth; remediation never resolves the Finding. Nothing in this document weakens, bypasses, or duplicates server-side enforcement in frontend logic. **The disabled frontend control is a UX courtesy, never the security boundary** — a malicious or modified client bypassing it must still receive the backend's own authoritative rejection, unchanged.

## 3. Radio-control architecture (frozen)

Root cause, independently re-verified: `frontend/app/globals.css`, the rule `dialog label { display: flex; flex-direction: column; gap: 0.4rem; font-weight: 700; }` applies to every `<label>` inside any `<dialog>`, including the Approve/Reject radio labels, forcing each radio circle and its text onto separate lines. The native `<input type="radio">`/`<label>`/`<fieldset>`/`<legend>` elements already in use are correct and sufficient — **no custom radio component is authorized or required.**

Frozen target behavior:
- Initial state: `approve` state is `null` (neither selected) — no implicit decision. `Confirm` is disabled until a decision is deliberately selected.
- Approve selected: Approve radio checked; CTA reads `Confirm: Approve`.
- Reject selected: Reject radio checked; CTA reads `Confirm: Reject`; the existing optional `rejection_reason` field and its existing validation are unchanged.
- The entire label row (radio + text) is the click target, via correct native `<label>` wrapping — once the CSS no longer forces column layout, this is already native behavior, not new JS.
- Keyboard navigation, focus indication, `fieldset`/`legend` grouping semantics, and label/control association are preserved exactly as native HTML already provides them. No new `aria-*` attributes are authorized unless I1 implementation finds a genuine native-semantics gap (none is evidenced today).

## 4. Self-approval rejection architecture (frozen)

On receiving exactly `REMEDIATION_SELF_APPROVAL_PROHIBITED` (and only that code — no other error, known or unknown, triggers this state):
- The explanatory message remains visible.
- The Approve radio becomes disabled.
- `Confirm: Approve` becomes disabled (whether or not Approve was the selected option at the time of rejection).
- The forbidden action cannot be resubmitted through normal UI interaction.
- Cancel/Close remains available.

**Reject semantics (independently verified, not assumed):** the domain model's self-approval guard (`OqiRemediationService.approve()`) is the *only* identity comparison in this lifecycle; `reject()` contains no analogous self-rejection check anywhere in `backend/app/application/oqi_remediation_service.py`. Self-rejection is therefore not a separation-of-duty violation under the existing domain contract. Frozen: Reject remains selectable and submittable after a self-approval rejection; selecting it sets the CTA to `Confirm: Reject`. The self-approval explanatory text must not be worded in a way that implies Reject is also forbidden.

**Binding principle:** *Server establishes prohibition; frontend reflects it. Frontend never predicts or substitutes for server authority.* The frontend's role is limited to keying off the exact, already-unique error code already returned by the API — it performs no identity comparison of its own.

## 5. Active-principal visibility (frozen, with a mandatory verification checkpoint)

The ID token is already requested (`openid profile` + qualified capability scopes) and is already available client-side via `sessionManager().getUser()`. `user.profile.name` is assessed as very likely already populated (Entra's standard `profile`-scope behavior for the `name` claim, and the Demo Steward/Demo Approver accounts' own Entra `displayName` attribute is independently confirmed, via live Graph read during this program, to literally be `"Demo Steward"`/`"Demo Approver"`) — but this has **not** been proven by an actual runtime decode in this program, and no mutation-free way to prove it exists in a governance-only phase.

**Frozen as a mandatory I1 checkpoint, not an assumption:** I1's first implementation step must independently confirm, via a real signed-in session (reading `user.profile` client-side only — no raw token transmitted, no backend change), whether `name` and/or `preferred_username` are actually present. Implementation of the display logic proceeds only after this is confirmed; the frozen fallback order is:

```
1. user.profile.name           (preferred — matches the Entra displayName attribute)
2. user.profile.preferred_username
3. no label (graceful omission — "Sign out" alone is an acceptable degraded state)
```

Never displayed as the primary identity label: `sub`, `tid`/tenant id, raw token contents, or any other internal/opaque identifier. This is general enterprise shell behavior, not demo-specific logic, and requires zero backend change — it reads only the existing ID token already held client-side.

## 6. Human-readable audit identity — options evaluated

| Option | Trust | Readability | Historical correctness | Deployment cost | Verdict |
|---|---|---|---|---|---|
| A. Validated access-token `name` claim | Same JWT signature tier as `sub` | High ("Demo Approver") | Good, with snapshot (§7) | One `optionalClaims.accessToken` entry per backend app registration | **Selected** |
| B. Validated access-token `preferred_username` | Same tier | Lower (UPN/email-shaped, not a friendly name) | Good, with snapshot | Same as A | Rejected — inferior readability for no added trust |
| C. Stable directory id (`oid`) + server-side Graph lookup at read time | High at lookup time | High | **Fails** — a live lookup shows the *current* name even for old decisions, silently rewriting history | New Graph credential/secret, per-read network call, added latency | Rejected |
| D. Another already-available validated claim | N/A | N/A | N/A | N/A | None exists — the real, already-decoded Steward access token (VM-R2) carries only `iss`/`aud`/`sub`/`scp`/`noetva_tenant_id`; no name-shaped claim is present today without a CIAM change |

**Selected: Option A.** Client-supplied display identity (of any kind) is rejected outright — it would reintroduce exactly the client-controlled-identity trust boundary CDD-090 closed.

## 7. Immutable identity vs. display snapshot (frozen)

Two-layer model:
- **Security/audit authority** — `requested_by`/`decided_by` (`TrustedPrincipal.principal_id`, the access token's `sub`) remain the only identifiers used for authorization, the self-approval comparison, and durable machine attribution. Never replaced by, or compared against, a display name.
- **Human presentation** — a trustworthy display-name **snapshot**, captured once at the moment of each event (request, decide), from the same validated access token's `name` claim. A snapshot, not a live join: if "Jane Smith" later becomes "Jane Doe" in the directory, the historical record continues to read "Jane Smith" — the event's own context is never silently rewritten.

**Data minimization (frozen):** the snapshot contains **display name only** — not email, not UPN, not any other PII. `name` alone satisfies the entire target UX (`Authorized by Demo Approver`); nothing else is needed and nothing else is authorized to be persisted.

## 8. Requester/decider symmetry (frozen)

Symmetric. Both sides of the lifecycle gain a display-name snapshot alongside their existing machine identity: `requested_by` ↔ `requested_by_display_name`, `decided_by` ↔ `decided_by_display_name`. No asymmetry is authorized without evidence, and none was found.

## 9. Null/missing-claim fallback (frozen)

The display claim is optional in every sense that matters for correctness: `principal_id` remains the sole mandatory identity for authorization; no authorization-logic comparison ever reads a display name; a missing/null display name must never cause a legitimate request/decision to fail. Frozen UI fallback when the display-name snapshot is null (e.g. a historical row from before this correction, or a token that never carried the claim): `"Authorized by signed-in principal"` (or the analogous "Requested by…" form) — never an invented or guessed name. The opaque principal id remains available in detail/audit-evidence surfaces, never removed from the API response, simply not the primary label.

## 10. CIAM configuration (frozen, not yet executed)

Exactly one new optional claim, on exactly two application registrations, token type access-token only:

```
Applications:  noetva-dev-backend-api  (appId 3a880f13-985d-4a71-be05-20f97b9bcfa3)
               noetva-demo-backend-api (appId a2213cbd-d107-4ebe-b86d-e9521bc82544)
Token type:    optionalClaims.accessToken   (NOT idToken — idToken's own `name` claim,
               if present, is independent and already covered by §5's own, separate,
               zero-CIAM-change path)
Claim:         name
```

**Why both environments:** this is general product architecture (trusted audit attribution), not a demo-only artifact — every prior Entra correction in this program (CDD-064/065/073/074/076) applied uniformly to dev, with demo mirroring it; this follows the identical established pattern. **Why access-token only:** the backend never receives the ID token; `TrustedPrincipal` is built exclusively from the validated access token, exactly as `principal_id`/`sub` already is. **Rollback:** removing the single `optionalClaims.accessToken` entry; purely additive — no existing token validation, consent, or claims-mapping-policy behavior is touched, so rollback carries zero data-loss risk. **Explicitly excluded:** no change to either app's *existing* (already-inert) `optionalClaims` entries from the authority-binding investigation — those remain a separately tracked cleanup item (§15), never bundled here.

## 11. Schema/migration architecture (frozen)

One new, additive, nullable-only migration on `OqiRemediationAuthorizationORM` (`backend/app/infrastructure/persistence/models/oqi_remediation.py`), the single table that already holds both `requested_by` and `decided_by`:

```sql
ALTER TABLE oqi_remediation_authorizations
  ADD COLUMN requested_by_display_name VARCHAR(200) NULL,
  ADD COLUMN decided_by_display_name   VARCHAR(200) NULL;
```

No backfill (no historical name may be invented for existing rows — they remain `NULL`, rendered via §9's fallback). No rewriting, renaming, or narrowing of `requested_by`/`decided_by`. No destructive operation of any kind. Existing rows remain fully readable by every existing query.

## 12. API contract (frozen)

`RemediationCandidateAuthorizationView` (`backend/app/api/oqi/schemas.py`) gains two new optional fields, mirroring the existing `decided_by`/`decided_on` nullability pattern:

```python
requested_by_display_name: str | None
decided_by_display_name: str | None
```

The existing opaque `requested_by`/`decided_by` fields remain in the response, unchanged, unremoved. The frontend contract (`frontend/lib/oqi/contracts.ts`) mirrors these two fields exactly. The frontend must render only what the server returns — it is not authorized to infer, guess, or construct a display identity from the opaque id. No write-path request body gains any actor-identity field of any kind (`DecideAuthorizationRequest`/`PrepareRemediationRequest` remain exactly as CDD-090 left them).

## 13. Phase split (frozen)

A genuine architecture boundary, independently reconfirmed: I1 touches only frontend interaction/CSS/ID-token-already-held-client-side reads, with zero backend, schema, or CIAM footprint; I2 requires a new trusted claim, a schema migration, and CIAM configuration. They are not combined.

### I1 — Frontend authorization UX

**Exact authorized paths:**

| # | Path | Action |
|---|---|---|
| 1 | `frontend/app/quality/findings/[findingId]/_components/decide-authorization-dialog.tsx` | MODIFY |
| 2 | `frontend/app/globals.css` | MODIFY |
| 3 | `frontend/components/session-controls.tsx` | MODIFY |
| 4 | `frontend/tests/oqi-remediation-actions.test.tsx` | MODIFY |
| 5 | `frontend/tests/session-controls.test.tsx` | MODIFY |

No CREATE, no DELETE. `frontend/lib/auth/principal-presentation.ts` (or any shared presentation abstraction) is **explicitly not authorized** — I1's two identity-reading call sites (the dialog has none; only `session-controls.tsx` reads `user.profile`) do not share code, so no abstraction is warranted. No backend, database, or CIAM path is authorized under I1.

**Required tests (minimum, exact):**
1. Neither radio selected on dialog open.
2. Confirm disabled with no selection.
3. Selecting Approve checks only Approve.
4. CTA reads `Confirm: Approve` when Approve is selected.
5. Selecting Reject checks only Reject.
6. CTA reads `Confirm: Reject` when Reject is selected.
7. Each radio's label/row is correctly associated (clicking label text toggles the radio).
8. A generic/unknown API error code does not disable Approve.
9. `REMEDIATION_SELF_APPROVAL_PROHIBITED` specifically enters the blocked state.
10. The explanatory message remains visible in the blocked state.
11. Approve radio is disabled in the blocked state.
12. `Confirm: Approve` is disabled in the blocked state.
13. A second submit attempt cannot be made through the UI in the blocked state.
14. Reject remains selectable and submittable in the blocked state.
15. Cancel remains usable in every state.
16. The active principal's name renders when `user.profile.name` (or `.preferred_username`) is present.
17. A safe, neutral fallback renders when neither is present.
18. Sign-out remains functional regardless of display-name presence.
19. `sub` (or any other opaque/internal claim) is never rendered as the primary active-user label.

### I2 — Trusted audit identity

**Exact authorized paths:**

| # | Path | Action | Why |
|---|---|---|---|
| 1 | `backend/app/api/supplier_risk/authentication.py` | MODIFY | Add `TrustedPrincipal.display_name: str \| None`; extract in `_principal()` from the new claim |
| 2 | `backend/app/core/config.py` | MODIFY | New optional setting (e.g. `oidc_display_name_claim: str = "name"`) |
| 3 | `backend/app/application/oqi_remediation_service.py` | MODIFY | `request_authorization()`/`approve()`/`reject()` each gain an optional `*_display_name: str \| None = None` parameter alongside their existing identity parameter |
| 4 | `backend/app/application/oqi_product_experience_service.py` | MODIFY | `RemediationCandidateAuthorizationRow` dataclass and its construction in `get_remediation()` gain the two new fields (independently located this phase at the existing `is_stale`-computation call site; not in the original DR list, added here with this justification) |
| 5 | `backend/app/infrastructure/persistence/models/oqi_remediation.py` | MODIFY | Two new nullable columns (§11) |
| 6 | `backend/app/infrastructure/persistence/migrations/versions/<next>_remediation_actor_display_name.py` | CREATE | The migration itself |
| 7 | `backend/app/api/oqi/router.py` | MODIFY | Thread `authenticated.display_name` into the two existing call sites (`request_authorization`, `decide_authorization`); the `RemediationCandidateAuthorizationView` construction site (independently located this phase at line ~485) gains the two new fields |
| 8 | `backend/app/api/oqi/schemas.py` | MODIFY | `RemediationCandidateAuthorizationView` gains the two new optional fields (§12) |
| 9 | `backend/app/tests/test_oqi_remediation_identity_binding_postgres.py` | MODIFY | New test cases (§14) added to the existing real-router/real-service/real-Postgres file — no new test file, same security surface already covered here |
| 10 | `frontend/lib/oqi/contracts.ts` | MODIFY | Mirror the two new fields |
| 11 | `frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx` | MODIFY | Line ~218's `` `Authorized by ${authorization.decided_by}` `` becomes display-name-first with the §9 fallback — independently located this phase, the exact and only rendering site for this text |

No other path is authorized. No path is authorized merely because it was convenient to list.

**Required security tests (minimum, exact — real router + real service + real PostgreSQL, never mocked-router-only, exactly matching the existing file's established pattern):**
1. Client still cannot supply `requested_by`.
2. Client still cannot supply `decided_by`.
3. Client cannot supply a requester display identity via the request body.
4. Client cannot supply a decider display identity via the request body.
5. Requester machine identity (`requested_by`) is server-derived only.
6. Decider machine identity (`decided_by`) is server-derived only.
7. Requester display snapshot is derived only from the authenticated server context, never request input.
8. Decider display snapshot is derived only from the authenticated server context, never request input.
9. Same-principal approval still fails closed (`REMEDIATION_SELF_APPROVAL_PROHIBITED`) — regression proof that this correction did not touch the guard.
10. Distinct-principal approval still succeeds.
11. A spoofed display-name field in the request body cannot influence the persisted snapshot.
12. A missing/null display claim does not weaken, block, or alter authorization outcome.
13. A historical snapshot persists unchanged regardless of a later (simulated) identity-provider claim change.
14. Tenant isolation remains intact.
15. `APPROVED`/`SUPERSEDED` semantics remain intact.

## 14. Docker/runtime gates (frozen)

**I1:** frontend production build (`next build`) succeeds; full relevant frontend regression passes; Docker frontend image builds and boots; authenticated-shell display behavior verified at least via the §5 checkpoint.

**I2:** full relevant backend regression passes; frontend regression passes; the new migration applies cleanly both from a clean database and as an upgrade from the current head; Docker backend and frontend images build and boot; the live-served OpenAPI contract is inspected (non-mutating) to confirm the two new response fields exist with correct nullability; real-PostgreSQL persistence of the snapshot is proven (not mocked); OIDC/authentication regression passes unchanged; tenant isolation regression passes; the Golden-story crown passes unchanged.

## 15. Azure verification for I2 (frozen, two-stage, mirroring CDD-064/065's own established discipline)

**Stage 1 (structural, read-only):** confirm, via Graph, that `optionalClaims.accessToken` on both backend app registrations now contains exactly one new entry (`name`), with no other change to either app object, no claims-mapping-policy mutation, no consent-grant mutation.

**Stage 2 (real Azure, real principals):** Demo Steward and Demo Approver each complete a real interactive login; sanitized claim inspection only (no raw bearer token in any report); a protected backend request succeeds for each; the backend is independently confirmed to have extracted the expected `display_name` into `TrustedPrincipal`; the persisted `decided_by_display_name` (and, separately, `requested_by_display_name`) snapshot is confirmed to match the authenticated actor; same-principal self-approval still fails; a distinct principal's authorization still succeeds. Only Stage 2 success may declare the CIAM change operationally closed — Stage 1 alone authorizes merging the source/migration, exactly mirroring this program's own established terminology discipline (`PASS + SOURCE MERGED — ... PENDING AZURE EXECUTION`).

## 16. Golden Demo acceptance crown (frozen)

Steward session: shell shows `Demo Steward`; finding opened; remediation prepared, both candidates `Pending`; neither radio pre-selected; Approve selected; self-approval attempted; server rejects; message shown; Approve radio and `Confirm: Approve` both disabled; forbidden action cannot be repeated. Fresh Approver session: shell shows `Demo Approver`; radios render aligned and unambiguous; Approve deliberately selected; `Confirm: Approve` fires; authorization succeeds; UI reads `Authorized by Demo Approver` (opaque id retained only in detail/audit evidence); sibling reads `SUPERSEDED — an alternative candidate was approved`, never `REJECTED`; Report Execution remains a distinct, later, separate action; Finding remains `OPEN` while SAP=US/PLM=MX remain unchanged. Visibly demonstrates, without verbal explanation: RECOMMENDATION≠AUTHORIZATION, AUTHORIZATION≠EXECUTION, REMEDIATION≠RESOLUTION.

## 17. Scope exclusions (reconfirmed)

Not touched, not expanded into, by this document or by I1/I2: OQI propagated-impact limitation; the Gate S sibling authority-binding defect; `CTEC_ENVIRONMENT=development`; cleanup of the existing (already-inert) `optionalClaims` entries from the authority-binding investigation; the CDD numbering collision with `product/wow-i4-b1` (beyond this document safely choosing its own number, §18); build-pipeline fail-closed hardening for `NEXT_PUBLIC_OIDC_API_RESOURCE_URI`; ontology/propagated-impact redesign; general design-system rewrite; unrelated accessibility work; any dev deployment beyond the exact §15 CIAM verification; any production deployment; merge of PR #253 or PR #254.

## 18. Numbering-uniqueness verification (performed, not assumed)

Highest CDD on `origin/main`: CDD-086. Independently re-checked every remote branch for `CDD-09[0-9]`: zero matches anywhere remote. Independently re-checked every **local** branch too (since CDD-090 itself was committed only locally, on `governance/cdd-090-authority-binding-deployment-authorization`, never pushed): the only CDD-09x anywhere, local or remote, is that single local CDD-090 file. **CDD-091 is confirmed unclaimed anywhere in this repository's local or remote branch set at freeze time.**

## 19. Authoritative baseline at freeze

```
origin/main                   = 171a398af6d4af6bd2149ff69879f4cdc178ed3e
PR #253 (azure/golden-demo-parity-g)  = OPEN, head af20323d5a9f3031d8aa5f25d3a3f5a724488b7d
PR #254 (azure/golden-demo-parity-i1) = OPEN, head 4bf410a09712acb9ca22961c032160d7438040d5
Azure Golden integration candidate    = 56d7adc21fc5ea62cffc0da21da7776eb93c367f
Deployed backend digest       = sha256:7d6ffdefc3e79557ec993c9e222517918b030f38c06412c83bd90a32db1bf3e3
Deployed frontend digest      = sha256:bf5ac8da0836e56d84a70b3c43e0a77419c84f4a20e4a5a06b380c5da130d1b1
CDD-087 SHA-256                = cb38bc3ecaf4b8498d8626832eb5fc2cb61f5cdb6ced27d625517b91cc8daec4
CDD-090 SHA-256                = 2aed8fdc07f21138fdf367171b1d1b3d9ffab58d13ee764fa8a7f9e8c609c688
```

All independently re-derived this phase; zero drift from every prior phase's own record.

## 20. STOP conditions (all evaluated during this governance phase; none triggered)

Source/runtime drift — not found (§19). No safe CDD identifier — found (§18, CDD-091). Active-principal identity source uncharacterizable — resolved via a mandatory I1 verify-before-write checkpoint rather than an assumption (§5). Human-readable identity requiring client trust — rejected outright (§6/§9). Display identity replacing machine identity in authorization — explicitly never authorized (§7). CIAM change not narrowly definable — defined exactly (§10). Destructive migration — none; additive/nullable only (§11). Unbounded implementation scope — bounded to exact path lists (§13). Radio behavior conflicting with domain semantics — verified consistent (§3/§4). Self-rejection semantics uncertain — resolved by direct source trace (§4). Another material security defect discovered — none found. **No STOP condition fired.**

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself.*
