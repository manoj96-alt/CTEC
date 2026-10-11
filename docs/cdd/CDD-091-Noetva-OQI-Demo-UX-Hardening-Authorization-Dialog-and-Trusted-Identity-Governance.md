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

## 21. G-R1 governance correction (amendment — does not reopen §§1-20)

**Originating phase:** NOETVA-OQI-DEMO-UX-HARDENING-G-R1, following NOETVA-OQI-DEMO-UX-HARDENING-I2's own correct fail-closed stop.

**What happened:** I2 implemented paths #1-#2 of §13's I2 table (`TrustedPrincipal.display_name` and its configuration), verified them safe, and then stopped before touching paths #3-#11, having traced — not merely suspected — that persisting the requester/decider display-name snapshot is structurally impossible without two files absent from §13's list. The original §13 table is **not edited in place**; it stands as written, and this section records the correction additively, exactly as CDD-064/065's own amendment precedent in this repository already established.

**Why the two paths are required (traced exhaustively, not asserted):**
- `OqiRemediationRepositoryImpl.create_authorization()` and `.update_authorization_decision()` (`backend/app/infrastructure/persistence/oqi_remediation_repository.py`) map the domain `RemediationAuthorization` object to the ORM **by named field, one at a time** (`_authorization_to_orm`/`_authorization_to_domain`; `update_authorization_decision` copies exactly `status`/`decided_by`/`decided_on`/`rejection_reason`). There is no side-channel.
- The domain object itself (`backend/app/domain/oqi_remediation/authorization.py`, `RemediationAuthorization`, `frozen=True, slots=True`) is therefore the *only* carrier available to either repository method — it has no field to carry a display-name snapshot today.

**Full end-to-end plumbing trace performed this phase (every hop proven, not assumed):**
- Construction sites: exactly three `RemediationAuthorization(...)` call sites exist anywhere in `app/` — `oqi_remediation_service.py:349` (request), `:459` (decide), and `oqi_remediation_repository.py:791` (`_authorization_to_domain`). No fourth, hidden site exists.
- Decision-time: `approve()` and `reject()` **both** call the same private `_decide()` — proven by direct read, not assumed — so there is exactly one decision-time code path, not two, and exactly one repository call (`update_authorization_decision`) to extend.
- Read-time: `get_candidates_with_authorizations_for_case()` (the method `oqi_product_experience_service.py`'s row construction actually calls) itself reuses the same `_authorization_to_domain()` helper — no separate, third mapping function exists anywhere in the repository file.
- Test paths: no file under `app/tests/` constructs `RemediationAuthorization(...)` directly today — the dataclass is exercised only through the existing real-router/real-service/real-Postgres integration file already authorized as I2 path #9 (`test_oqi_remediation_identity_binding_postgres.py`). No new test file is required; the existing one is structurally sufficient to cover domain construction, the repository round trip, decision-update persistence, missing-display-claim behavior, and both adversarial cases (§24/§25 below).

**Domain-model semantics decision:** the display-name snapshot belongs on `RemediationAuthorization` as event/audit metadata, not a separate persistence-only structure — it is specific to one authorization event (one request, one decision), exactly the granularity this domain object already represents, and it never participates in any comparison inside `__post_init__` or the service's own `_decide()` guard. This is additive data on an already-correct object, not a reopened architecture decision.

**Security invariant reconfirmed:** `_decide()`'s guard (`decided_by == authorization.requested_by`, line 454) compares only the two existing, unmodified machine-identity fields. Neither new field is read by any authorization/separation-of-duty logic anywhere in the traced chain. `requested_by`/`decided_by` remain the sole security identities.

**Nullability/backward compatibility:** both new fields are optional (`str | None = None`), validated in `__post_init__` only as "if present, must be a non-blank string" — mirroring the dataclass's own existing treatment of `rejection_reason`. A historical row with `NULL` in the new columns converts to `None` on both fields and remains fully constructible and readable; no backfill is performed or needed.

### 21.1 Corrected exact I2 path set (13 paths total — §13's original 11 plus these 2)

| # | Path | Action | Why (newly justified here) |
|---|---|---|---|
| 12 | `backend/app/domain/oqi_remediation/authorization.py` | MODIFY | Add `requested_by_display_name: str \| None = None` and `decided_by_display_name: str \| None = None` to `RemediationAuthorization`; extend `__post_init__`'s existing per-field validation loop to cover them identically to `rejection_reason`'s existing optional-string pattern |
| 13 | `backend/app/infrastructure/persistence/oqi_remediation_repository.py` | MODIFY | Thread both new fields through `_authorization_to_orm()`, `_authorization_to_domain()`, and `update_authorization_decision()` (which must additionally copy `model.decided_by_display_name = authorization.decided_by_display_name`) |

**Corrected counts: CREATE = 1, MODIFY = 12, DELETE = 0** (§13's original 10 MODIFY + 1 CREATE, plus these 2 MODIFY). No 14th path was found by the exhaustive trace above.

### 21.2 Test-path sufficiency (re-audited)

No additional test path is required. §13 I2 path #9 (`test_oqi_remediation_identity_binding_postgres.py`) remains sufficient and is hereby confirmed, not merely assumed, to be the correct and only location for:
- domain-level construction of both new fields (exercised transitively through every real service call this file already makes);
- the repository round trip (persisted via the same real-Postgres session this file already uses);
- decision-update persistence for both APPROVE and REJECT;
- missing/null display-claim behavior;
- both adversarial cases below.

### 21.3 Required adversarial tests (added to I2 path #9, not a new file)

1. **Same display name, distinct principals:** Principal A (`principal_id=A`, `display_name="Alex Smith"`) requests; Principal B (`principal_id=B`, `display_name="Alex Smith"`) decides. Must succeed (`APPROVED`) — proving display-name equality never implies principal equality.
2. **Distinct display name, same principal:** Principal A requests as `display_name="Old Name"`; the same `principal_id=A` later attempts to decide presenting `display_name="New Name"`. Must still fail with `REMEDIATION_SELF_APPROVAL_PROHIBITED` — proving principal equality overrides any display-name difference, so a rename can never bypass separation of duties.

### 21.4 Partial-commit disposition

**PRESERVE.** Commit `1461058df337161d255545b199530e8824f9f5c5` (paths #1-#2: `TrustedPrincipal.display_name` and its configuration) is independently re-verified this phase as byte-exact, additive-only, and fully consistent with the corrected architecture — it requires no rework. NOETVA-OQI-DEMO-UX-HARDENING-I2-R1 resumes directly on top of it.

### 21.5 Governance hash record

```
Original CDD-091 SHA-256 (sections 1-20, as originally frozen) = d0876b46ee7e95b365d101b959e2259470bb75b2d3062227421803679bddc97e
```

The amended document's own hash is computed and recorded by the committing phase immediately after this section is appended (§21.5 itself cannot contain its own final hash). Both hashes remain permanently on record; no future phase may cite the original hash as still authoritative for I2's path ceiling — only the amended hash governs I2-R1 onward.

### 21.6 I2-R1 authorization

**NOETVA-OQI-DEMO-UX-HARDENING-I2-R1** is authorized to resume from the preserved partial commit and implement exactly the corrected 13-path set (§21.1), run the complete §13 security-test crown plus §21.3's two adversarial tests (all within existing authorized test path #9), run the migration (§13 path #6, now correctly populable), run backend/frontend regression, run Docker verification, perform CIAM Stage 1 on both `noetva-dev-backend-api` and `noetva-demo-backend-api` exactly as §10/§18-20 already froze, perform real Azure Stage 2 verification, and execute the two-principal human-readable-attribution crown. I2-R1 does not merge. I2-R1 may not expand beyond the 13-path set without a further, equally narrow correction following this same discipline.

### 21.7 Scope reaffirmed unchanged

OQI propagated-impact limitation; Gate S sibling authority-binding defect; `CTEC_ENVIRONMENT=development`; existing (pre-I2) `optionalClaims` cleanup; build-pipeline `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` hardening; CDD numbering collision; any production deployment; PR #253/#254 merge — none touched, none reopened by this amendment.

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself. §21 amends CDD-091 additively; §§1-20 are not edited in place and remain available in full for historical/audit reference.*

---

## 22. G-R2 final governance correction (amendment — does not reopen §§1-21)

**Originating phases:** NOETVA-OQI-DEMO-UX-HARDENING-I2-R1 (STOPPED before any write), NOETVA-OQI-DEMO-UX-HARDENING-G-R2 (STOPPED — full analysis, no amendment written, because its own fail-closed rule required STOP when the true path count was not exactly 14), NOETVA-OQI-DEMO-UX-HARDENING-G-R2-R1 (this freeze, following explicit approval of the 16-path ceiling). §§1-21 are not edited; this section is appended after the original footer so that the G-R1 document (SHA-256 `9fbc5cfb…1382`) is an exact byte prefix of this one.

**Baseline for every line reference below:** source at `1461058df337161d255545b199530e8824f9f5c5` (preserved partial I2 commit; `origin/main` = `171a398af6d4af6bd2149ff69879f4cdc178ed3e`; PR #253 OPEN @ `af20323d…`, PR #254 OPEN @ `4bf410a0…`).

### 22.1 Why I2-R1 stopped — the missing production orchestration hop

§13 path #7 assumed the router threads `authenticated.display_name` directly into `request_authorization`. It does not. The actual production request-time chain is:

`router.prepare_remediation` (`backend/app/api/oqi/router.py:519`, call at `:535`) → `ProductionRemediationOrchestrationService.prepare_remediation(*, tenant_id, finding_id, requested_by, correlation_id)` (`backend/app/application/production_remediation_orchestration_service.py:197`) → `service.request_authorization(tenant_id, instruction_id, requested_by, now)` (same file, `:292`).

`:292` is the **only** production caller of `OqiRemediationService.request_authorization` anywhere in the repository. `prepare_remediation()` has no parameter, field, or context capable of carrying a display snapshot. Adding `requested_by_display_name: str | None = None` to `prepare_remediation()` and forwarding it on `:292` is the narrowest correct solution and is pure transport: the orchestration service must not resolve identity, inspect tokens, perform directory lookup, compare display names, default, or invent a name.

### 22.2 Why two frontend test paths are required

`frontend/tests/oqi-product-truth.test.tsx:263` and `frontend/tests/oqi-finding-detail.test.tsx:932` each assert `screen.getByText(/Authorized by steward@example.com/)` — i.e. the opaque `decided_by` rendering that §9/§12 require I2 to replace. Their fixtures are inline JSX props type-checked against `RemediationCandidateAuthorizationView` (no cast), so they must change whether the new contract fields are required (`tsc` failure) or optional (assertion failure under the §9 fallback). They are also the only existing tests of the panel's attribution sentence (`remediation-panel.tsx:218`, which renders both `Authorized by …` and `Rejected by …`). Both were exhaustively confirmed to be the only frontend assertions on the rendered decider string; `frontend/tests/oqi-remediation-actions.test.tsx` uses `as unknown as` casts and asserts no attribution text, so it is **not** required. These two paths are mandatory mechanical consequences of the already-frozen UX, not feature expansion; no unrelated rewrite of either file is authorized.

### 22.3 Complete production caller audit (two independent techniques, cross-checked)

Performed by (1) whole-repository PCRE text search and (2) a Python AST scan of every call node (including `dataclasses.replace`, `getattr`, `functools.partial`) — results identical; re-run at G-R2-R1 with zero drift.

| Concern | Sole production path |
|---|---|
| Authorization creation | `router.py:535` → `production_remediation_orchestration_service.py:292` → `oqi_remediation_service.py:349` (construct) → `:358` `create_authorization` |
| Authorization decision | `router.py:603` → `OqiProductExperienceService.decide_authorization` (`oqi_product_experience_service.py:1278`; `approve` at `:1292`, `reject` at `:1296`) → shared `_decide()` (`oqi_remediation_service.py:438`; construct `:459`) → `update_authorization_decision` (`:473`) |
| Read | `get_candidates_with_authorizations_for_case` → `_authorization_to_domain` (`oqi_remediation_repository.py:791`) → `RemediationCandidateAuthorizationRow` (sole constructor `oqi_product_experience_service.py:1235`) → `RemediationCandidateAuthorizationView` (sole constructor `router.py:485`) → `contracts.ts` → `remediation-panel.tsx:218` |

Other writers of `oqi_remediation_authorizations`, none of which establishes a human actor: `supersede_pending_sibling_authorizations` writes only `status`/`decided_on` (`oqi_remediation_repository.py:423-424`) — SUPERSEDED is a system consequence with `decided_by` and `decided_by_display_name` both NULL; `consume_authorization` writes only `consumed_on`/`consumed_execution_id` (`:431-432`); `database_cli.py` Golden restore only deletes/counts. Unrelated same-named methods: `GateSApprovalService.approve/reject/_decide`, ontology-modeling and semantic-mapping proposal `approve/reject`, `oqi_remediation_agent_service` (uses only `construct_instruction`). `PrepareRemediationResponse.authorizations` exposes only id/instruction/status — no second actor-bearing read model exists. The frontend has no mapper/whitelist between JSON and the contract type.

### 22.4 Frozen flows

**Requester:** validated access token → `TrustedPrincipal.display_name` → `router.prepare_remediation` → `ProductionRemediationOrchestrationService.prepare_remediation(requested_by_display_name=…)` → `OqiRemediationService.request_authorization(requested_by_display_name=…)` → `RemediationAuthorization.requested_by_display_name` → `_authorization_to_orm` → ORM → DB.

**Decider:** validated access token → `TrustedPrincipal.display_name` → `router.decide_authorization` → `OqiProductExperienceService.decide_authorization(decided_by_display_name=…)` → `approve()`/`reject()` → `_decide()` → `RemediationAuthorization.decided_by_display_name` → `update_authorization_decision` (also copies `decided_by_display_name`) → DB. `_decide()` carries the pre-decision row's `requested_by_display_name` through unchanged; the requester's snapshot is never copied into the decider's.

**Security boundary (unchanged):** the self-approval guard remains exclusively `if decided_by == authorization.requested_by` (`oqi_remediation_service.py:454`). No display name is ever read by that guard or by any other authorization/separation-of-duty logic.

### 22.5 Idempotency invariant (frozen)

`requested_by_display_name` is written **exactly once**, when a new authorization is created. When `prepare_remediation()` finds an existing authorization for an instruction it performs only a read (`repository.get_authorization_by_id`) and makes no `request_authorization` call and no repository write; concurrent prepares are serialized by a `pg_advisory_xact_lock` held for the entire method with a single final commit. Neither `requested_by` nor `requested_by_display_name` of an existing authorization can therefore be overwritten by a later prepare, by any caller. This holds under the existing architecture; no additional path is required.

### 22.6 Migration (frozen)

- **Path:** `backend/app/infrastructure/persistence/migrations/versions/0049_oqi_remediation_actor_display_name.py` (the directory named by `backend/alembic.ini` `version_locations`; there is no `backend/alembic/versions/`).
- **`revision = "0049_oqi_remediation_actor_name"`** (31 characters; unique).
- **`down_revision = "0048_oqi_remediation_mutex"`**.
- The revision id is intentionally shorter than the filename: Alembic declares `Column("version_num", String(32), nullable=False)` (`alembic/ddl/impl.py:169`), `backend/alembic/env.py` sets no `version_table` override, and a live PostgreSQL 15 check (temp table) rejected the 39-character id with `value too long for type character varying(32)` while accepting the 31-character id. Identical in kind to the CDD-040/CDD-051 and migration-0046 precedents (filename kept, `revision` shortened). The 39-character WIP revision must not survive into I2-R2.
- Upgrade adds the two columns in §22.7; downgrade drops exactly those two columns. No backfill, no destructive operation.

### 22.7 Display-name storage (frozen — supersedes §11's `VARCHAR(200)`)

`requested_by_display_name VARCHAR(256) NULL`, `decided_by_display_name VARCHAR(256) NULL`. Not TEXT (bounded presentation metadata, not free text); not VARCHAR(200).

Evidence: Microsoft Graph `user.displayName` — "Maximum length is 256 characters"; the Entra access-token `name` claim is documented as mutable and "for display purposes only… Don't use this value to make authorization decisions." Live PostgreSQL 15 (temp tables): a 256-character value fails in `VARCHAR(200)` (`value too long`), and `VARCHAR(256)` accepts 256 multibyte characters (512 bytes) — the limit is in characters, consistent with Python `len`. `VARCHAR(200)` would therefore make a legitimate authorization fail, violating §9.

### 22.8 Normalization and overflow (frozen — enforced once, at the trust boundary in `authentication.py`)

| Claim value | `TrustedPrincipal.display_name` |
|---|---|
| missing | `None` |
| non-string | `None` |
| empty string | `None` |
| whitespace-only | `None` |
| valid string | surrounding whitespace trimmed; every interior character preserved exactly |
| trimmed length ≤ 256 | exact trimmed value |
| trimmed length > 256 | `None` |

No truncation. No Unicode normalization, case folding, email extraction, or canonical identity mapping. An unusable display claim never rejects authentication, authorization request, or decision — presentation identity is never an availability dependency. Overflow options evaluated: truncate (rejected — falsifies the trusted snapshot), reject the operation (rejected — violates §9), store NULL beyond the directory's own bound (adopted as defense in depth), widen to the directory's documented bound (adopted).

### 22.9 Domain defensive invariant (frozen)

`RemediationAuthorization.__post_init__`: if `requested_by_display_name`/`decided_by_display_name` is not `None`, it must be a non-blank `str` (existing actor-field convention) and `len ≤ 256` (mirroring the existing `rejection_reason` length-check pattern). Production input already satisfies this via §22.8; the check is a defensive invariant only and never participates in separation-of-duty logic.

### 22.10 Corrected exact I2 path ceiling — 16 paths (supersedes §13's and §21.1's counts)

| # | Path | Action |
|---|---|---|
| 1 | `backend/app/api/supplier_risk/authentication.py` | MODIFY (partial done in `1461058`; I2-R2 adds the §22.8 >256 → `None` rule) |
| 2 | `backend/app/core/config.py` | MODIFY (done in `1461058`) |
| 3 | `backend/app/application/oqi_remediation_service.py` | MODIFY |
| 4 | `backend/app/application/oqi_product_experience_service.py` | MODIFY |
| 5 | `backend/app/infrastructure/persistence/models/oqi_remediation.py` | MODIFY |
| 6 | `backend/app/infrastructure/persistence/migrations/versions/0049_oqi_remediation_actor_display_name.py` | CREATE |
| 7 | `backend/app/api/oqi/router.py` | MODIFY |
| 8 | `backend/app/api/oqi/schemas.py` | MODIFY |
| 9 | `backend/app/tests/test_oqi_remediation_identity_binding_postgres.py` | MODIFY |
| 10 | `frontend/lib/oqi/contracts.ts` | MODIFY |
| 11 | `frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx` | MODIFY |
| 12 | `backend/app/domain/oqi_remediation/authorization.py` | MODIFY |
| 13 | `backend/app/infrastructure/persistence/oqi_remediation_repository.py` | MODIFY |
| 14 | `backend/app/application/production_remediation_orchestration_service.py` | MODIFY (new — §22.1) |
| 15 | `frontend/tests/oqi-product-truth.test.tsx` | MODIFY (new — §22.2) |
| 16 | `frontend/tests/oqi-finding-detail.test.tsx` | MODIFY (new — §22.2) |

**Counts: MODIFY = 15, CREATE = 1, DELETE = 0.** No other path is authorized. Path #9 remains sufficient for every backend proof (it may drive real orchestration by importing existing helpers, e.g. from `test_production_remediation_orchestration_postgres.py`, without adding a path). `backend/app/tests/test_oqi_api_router.py`'s fake `decide_authorization(**kwargs)` and key-level asserts, and every `get_current_head()`-based head test, are unaffected and require no change.

### 22.11 WIP disposition (pre-existing, uncommitted, on `product/oqi-demo-ux-hardening-i2-r1`)

Fingerprints at freeze: tracked-diff SHA-256 `820941886c48c62d58e238cb1619c43009a9b8ab25799d8740a0468cc33900f8` (7 paths: #3, #4, #5, #7, #8, #12, #13); untracked migration SHA-256 `d1f4a75183b530562f517b8ff2036756dfba59f840b59132b709550352a22886`.

- **Partial commit `1461058…`: PRESERVE.**
- **WIP migration: PRESERVE + CORRECT** — `revision` → `"0049_oqi_remediation_actor_name"`; both columns → `sa.String(length=256)`. `down_revision`, nullability, downgrade, and filename are already correct.
- **WIP source: PRESERVE, subject to I2-R2's own independent verification** (never blind trust). Appears consistent with this governance: domain fields and validation loop; schema view fields; product-experience row and construction; router view construction; all three repository mapping sites; service/`_decide()` threading including carry-through of the requester snapshot. **Requires correction:** ORM `String(200)` → `String(256)`; domain ≤256 defensive check. **Not yet written:** router requester and decider threading of `authenticated.display_name`; `OqiProductExperienceService.decide_authorization` `decided_by_display_name` kwarg; orchestration `requested_by_display_name` kwarg and forwarding; `authentication.py` >256 → `None`; `contracts.ts`; panel rendering; all tests (paths #9, #15, #16).

### 22.12 Frontend rendering (restating §9/§12 precisely for I2-R2)

`contracts.ts` mirrors `requested_by_display_name: string | null` and `decided_by_display_name: string | null`. The panel sentence at `remediation-panel.tsx:218` renders `Authorized by <decided_by_display_name>` / `Rejected by <decided_by_display_name>` when present, and `Authorized by signed-in principal` / `Rejected by signed-in principal` when `null`; the timestamp is preserved. The opaque `decided_by` is never the primary label and is never used to derive a name. No new requester-attribution UI element is authorized.

### 22.13 Required I2-R2 test crown (minimum)

Backend (path #9, real router + real service + real PostgreSQL): (1) trusted requester name passes through real production orchestration; (2) requester snapshot persists; (3) repeated prepare does not overwrite requester attribution; (4) trusted decider name persists; (5) APPROVE attribution; (6) REJECT attribution; (7) same display name / different principals → permitted; (8) same principal / changed display name → `REMEDIATION_SELF_APPROVAL_PROHIBITED`; (9) missing display claim does not block; (10) blank claim → `None`; (11) >256-character claim → `None`; (12) exactly 256 characters persists exactly; (13) client cannot spoof any of `requested_by`, `requested_by_display_name`, `decided_by`, `decided_by_display_name` (zero effect on persistence, whether the schema rejects — `PrepareRemediationRequest`, `extra="forbid"` → 422 — or ignores — `DecideAuthorizationRequest`); (14) NULL historical rows remain readable; (15) real PostgreSQL round trip; plus every §13 and §21.3 test. Migration: (16) upgrade from `0048_oqi_remediation_mutex`; (17) clean chain to head; (18) downgrade/upgrade; (19) the `alembic_version` row contains `0049_oqi_remediation_actor_name`. Frontend (paths #15/#16): (20) human-readable authorizer renders; (21) `signed-in principal` fallback renders; (22) rejected attribution renders. (23) I1 self-approval UX and all I1 tests remain green.

### 22.14 OpenAPI, Docker, and cloud ordering (frozen)

I2-R2 inspects the live OpenAPI: none of the four actor fields may appear in any write contract; both display fields appear on `RemediationCandidateAuthorizationView` as nullable. Mandatory order, never reordered: **SOURCE → TESTS → MIGRATION → REGRESSION → DOCKER** (backend + frontend image builds, real PostgreSQL, clean migration, upgrade, boot, health, live prepare, live decision, human-readable attribution) **→ CIAM STAGE 1** (exactly `optionalClaims.accessToken: name` on `noetva-demo-backend-api` and `noetva-dev-backend-api`, no other change, no existing-optionalClaims cleanup) **→ AZURE DEPLOY** (exact verified demo candidate only) **→ STAGE 2** (real Authorization Code + PKCE for Demo Steward and Demo Approver; sanitized proof that the issued access tokens carry `name`; never a raw token) **→ GOLDEN CROWN** (§16: Steward self-approval blocked; Approver approval succeeds; UI `Authorized by Demo Approver`; DB `decided_by` = immutable principal and `decided_by_display_name` = trusted snapshot, and likewise for the requester; sibling SUPERSEDED, never REJECTED; RECOMMENDATION ≠ AUTHORIZATION; REMEDIATION ≠ RESOLUTION).

### 22.15 Scope

**Explicitly out of scope (future consideration only):** `construct_instruction(created_by=requested_by)` records a machine actor on instructions without a display snapshot; CDD-091's display-snapshot symmetry applies to the authorization event only, and I2-R2 must not generalize instruction identity attribution. All §17/§21.7 exclusions remain unchanged: OQI propagated impact; Gate S sibling authority-binding; `CTEC_ENVIRONMENT=development`; existing optionalClaims cleanup; `NEXT_PUBLIC_OIDC_API_RESOURCE_URI` build-pipeline hardening; CDD numbering collision; production deployment; PR #253/#254 merge; unrelated UX cleanup; Graph lookup for display identity.

### 22.16 Hash record

```
Original CDD-091 (sections 1-20)  = d0876b46ee7e95b365d101b959e2259470bb75b2d3062227421803679bddc97e
G-R1 amended (sections 1-21)      = 9fbc5cfb03b7f1e046de5ee39f0a5f4c1efd7208001fa8f711c7e358f1d61382
```

This amended document's own hash is computed and recorded by the committing phase immediately after this section is appended. From that point only the G-R2-R1 hash governs I2-R2; neither earlier hash may be cited as the current I2 path ceiling.

### 22.17 I2-R2 authorization

**NOETVA-OQI-DEMO-UX-HARDENING-I2-R2** is authorized to resume — not restart — on `product/oqi-demo-ux-hardening-i2-r1` from `1461058…` plus the §22.11 WIP. It must first verify this document's G-R2-R1 hash, preserve `1461058…`, independently inspect the WIP against the fingerprints above, then apply only the §22.11 corrections and completions within the exact 16-path ceiling, run the §22.13 crown, and follow the §22.14 order. I2-R2 does not merge. If a seventeenth path is genuinely required: **STOP**.

---

*§22 amends CDD-091 additively; §§1-21 and the original footer above it are unchanged byte-for-byte.*
