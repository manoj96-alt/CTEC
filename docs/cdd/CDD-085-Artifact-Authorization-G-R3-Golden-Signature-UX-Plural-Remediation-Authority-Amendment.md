# CDD-085 — Artifact Authorization G-R3 Golden Signature UX + Plural Remediation Authority Amendment (NOETVA-GOLDEN-SIGNATURE-UX-G)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-085-Artifact-Authorization-G-R2-Golden-Parity-Test-Fixture-Transaction-Isolation-Amendment.md` (the
direct precedent for this governance shape: a real, browser-verified Golden Demo defect chain — VM STOP →
DR → DR-R1 → G — closed by the narrowest correct fix, frozen as a standalone additive amendment);
`CDD-052`/`CDD-053`/`CDD-054`/`CDD-055` (this repository's own established precedent for adding database-level
structural defense-in-depth for a governance-critical invariant, not relying on application logic alone)
Classification: THREE INSEPARABLE IMPLEMENTATION GAPS, none an architecture/governance reopening — (A)
Remediation Prepare has no browser entry point; (B) the remediation read model was built for the
single-candidate case and never extended to the true plural `CROSS_SOURCE_VALUE_CONFLICT` case, which (C) in
turn leaves a genuine **domain-governance defect**: nothing today prevents two mutually-exclusive remediation
candidates from both reaching `APPROVED`. A fourth, independent implementation gap (D) leaves the Evidence
tab's "View resolved entity" link pointing at a steward triage queue that structurally, correctly, and
intentionally excludes fully-Resolved entities — the correct fix adds a new read surface, it does not touch
the queue.
Governs: this amendment only. `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original
companion Artifact Authorization, `CDD-085-Artifact-Authorization-G-R1-Entity-Resolution-Flush-Ordering-
Amendment.md`, `CDD-085-Artifact-Authorization-G-R2-Golden-Parity-Test-Fixture-Transaction-Isolation-
Amendment.md`, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion Artifact Authorization are
all unmodified, unreopened, and remain FROZEN exactly as originally published.

## 1. Purpose

Authorizes the exact, complete, minimal correction for the material Golden Demo defects `NOETVA-DEMO-
READINESS-VM` correctly refused to merge behind:

```
NOETVA-DEMO-READINESS-VM: STOPPED —
REMEDIATION LIFECYCLE ("PREPARE") HAS NO BROWSER UI TRIGGER ANYWHERE IN THE FRONTEND —
"VIEW RESOLVED ENTITY" LINK LANDS ON A QUEUE THAT STRUCTURALLY EXCLUDES RESOLVED RECORDS —
PR #250 NOT MERGED
```

exhaustively root-caused and boundary-determined by `NOETVA-GOLDEN-SIGNATURE-UX-DR` and its own required
follow-up, `NOETVA-GOLDEN-SIGNATURE-UX-DR-R1` (which discovered, while resolving DR's own findings, a deeper
correctness defect — contradictory dual-approval of mutually-exclusive remediation candidates — and fully
resolved its design before this phase began). This amendment freezes governance for all four gaps as one
coherent correction; none may be implemented without the others; none is a Golden-story redesign.

## 2. Context — independently re-verified this phase, not merely trusted from DR-R1's report

```
origin/main                                  91e90b5812a123d08d58e78347f7283d285921f6  (re-fetched and
                                              re-confirmed this phase)
product/noetva-demo-readiness-final @        b254372b9632c0bd16174678e2ba7f2afd95688c  (unchanged; this
                                              amendment does not touch it)
PR #250                                      OPEN, headRefOid unchanged
PR #249 (historical)                         OPEN, b286c8cddbad11a1c3b3ffcaa40aaca08a0097f1, unchanged
PR #248 (historical)                         OPEN, e9a04bba956ab88694b9113856961436f23661a5, unchanged
```

All six pre-existing governance hashes (§0 below) independently re-hashed against the unmodified
`b254372b...` worktree this phase — byte-identical, confirmed again immediately before writing this
document.

```
CDD-085                                      c813b47b60a324de798ddbc6097b6b0b4be9806cd9ed720274f1be62d1c9b984
CDD-085 original AA                          7ac0d7454a174b0c8e6202062153f827ff8a11a8c121e6ebaebdadc651fe39b4
CDD-085 G-R1                                 bcc4fc8fe8c435d1a9c44079c059065ab15aba3070f5fd1b3bf7163502038efb
CDD-086                                      02f893bdf8d310dd0e8270879928c2c5ed1eb30aebae4d42ae7185346347dd67
CDD-086 AA                                   162bb163a2af5394caddab5f35c5451d242090d2829dca1a39d33a268fcf9bd7
CDD-085 G-R2                                 fb7d90ec8500387d09ccb75310b1022cccae93e7f8e5f5e4b5949905ec51587f
```

**Fresh, independent re-verification of the migration-critical facts this phase performed before freezing**
(not re-cited from DR-R1's own text): migration head on `b254372b...` is confirmed still exactly
`0047_oqi_h6_uniqueness` (direct directory listing); `"SUPERSEDED"` is 10 characters, fits the existing
`oqi_remediation_authorizations.status` column (`String(16)`, no `CHECK` constraint) with no migration needed
for the vocabulary itself; the entity-resolution router's existing route convention is confirmed by direct
read (`APIRouter(prefix="/api/v1/entity-resolution")`, existing sibling routes `/cases`, `/cases/{understanding_key}`)
so the new route's exact shape is derived from the real file, not invented; `frontend/lib/entity-resolution/
{api-client.ts,contracts.ts}` and `frontend/app/ontology-studio/entity-resolution/_components/case-detail-
panel.tsx` are confirmed to exist at exactly these paths.

## 3. Governed product principles — frozen, extended by exactly one new invariant

```
MAJORITY ≠ TRUTH
AUTHORITY ≠ TRUTH
CANDIDATE ≠ TRUTH
AGENT ≠ FACT
RECOMMENDATION ≠ AUTHORIZATION
AUTHORIZATION ≠ REMEDIATION
REMEDIATION ≠ RESOLUTION
```

New, added by this amendment:

```
FOR ONE REMEDIATION CASE, MUTUALLY-EXCLUSIVE CANDIDATES MUST HAVE AT MOST ONE EFFECTIVE APPROVAL.
SUPERSEDED ≠ REJECTED.
```

`REJECTED` means a human explicitly rejected that specific candidate. `SUPERSEDED` means a *different*,
mutually-exclusive candidate was approved, so this candidate's still-pending authorization is no longer
actionable — it implies nothing about whether the superseded candidate's own proposed value was itself wrong.
These must never be conflated in code, UI copy, or test naming.

## 4. Remediation domain cardinality — frozen from direct model read

```
RemediationCase        1
                        │ (oqi_remediation_candidates.case_id, FK, no cap)
                        ▼
Candidate               N
                        │ (oqi_remediation_instructions.candidate_id, FK, created 1:1 at prepare time)
                        ▼
Instruction              1
                        │ (oqi_remediation_authorizations.instruction_id, FK, created 1:1 at prepare time)
                        ▼
Authorization             1
```

`oqi_remediation_cases` has a unique index on `(tenant_id, finding_family, finding_id)` — exactly one case per
Finding. Confirmed by direct read of `backend/app/infrastructure/persistence/models/oqi_remediation.py`
(unmodified by this amendment — this file governs read-model behavior via the service layer, not the ORM
class itself, except for the one additive column in §9). **No existing model, constraint, or code path ties
sibling candidates of the same case together today** — this absence is the root of the invariant gap this
amendment closes.

## 5. Prepare contract

Frozen exactly as DR-R1 established:

```
POST /api/v1/oqi/findings/{finding_id}/remediation/prepare
Scope required: oqi-remediation:prepare
requested_by: sourced exclusively from authenticated.principal_id -- never request-body content
tenant: sourced exclusively from authenticated.tenant_id -- PrepareRemediationRequest carries no tenant field
Preparation: deliberate, explicit, human/steward-triggered -- never automatic after Finding evaluation
```

Keycloak realm (`keycloak/ctec-realm.json`) already correctly defines and assigns `oqi-remediation:prepare` as
an optional client scope to `ctec-frontend` — **independently re-confirmed this phase against the live realm
file in the unmodified `b254372b...` worktree**. No realm change is authorized or required. The only missing
piece is the frontend's own scope *request* list.

## 6. Prepare UI

When no remediation case exists, the Remediation panel must expose a deliberate "Prepare remediation" action.
After a successful prepare call: refresh remediation state via the plural GET (§7); display all resulting
candidates (§10); surface backend errors honestly (never swallow or paraphrase into a fabricated success);
never auto-select or auto-recommend a candidate. No automatic prepare may ever run on page load or on any
other implicit trigger.

## 7. Plural response contract

```
RemediationResponse:
  case_status: str | null
  candidates: [
    {
      candidate_id: str
      proposed_value: str
      basis: str
      authorization: {
        authorization_id: str
        status: "PENDING" | "APPROVED" | "REJECTED" | "SUPERSEDED"
        requested_by: str
        requested_on: datetime
        decided_by: str | null
        decided_on: datetime | null
        rejection_reason: str | null
        is_stale: bool
      } | null
    }, ...
  ]
  recommendation: ... (unchanged shape)
  external_execution: ... (unchanged shape)
```

No internal-only field (`payload_digest`, `target_source_object_id`, `target_source_field_id`) may be
exposed — none is exposed by the existing singular contract either, and none is required by any known
consumer.

**Clean contract replacement, frozen:** the existing singular `candidate`/`authorization` fields are replaced,
not duplicated. Repository-wide discovery (`grep -rln "RemediationResponse|remediation\.candidate\b|
remediation\.authorization\b|PrepareRemediationResponse"`, re-run this phase against the unmodified
`b254372b...` worktree, identical result to DR-R1's own run) finds **zero** consumers outside this
correction's own blast radius — no MCP/agent connector, no runbook tooling, no other API route. If
implementation independently discovers an external consumer this scan missed: **STOP**, do not silently add a
compatibility shim.

## 8. Deterministic candidate ordering

```
ORDER BY extracted_at ASC, candidate_id ASC
```

`extracted_at` is an existing, already-persisted column on `oqi_remediation_candidates` (confirmed by direct
model read, §4's own source). Never rely on incidental database row order (the exact defect this amendment
closes — the current singular read model's `ORDER BY created_on DESC LIMIT 1` on `instructions` is precisely
this mistake, applied to authorizations rather than candidates, and is removed by this correction). This
ordering is generic — it is not permitted to special-case "US before MX"; the Golden seed's own SAP-before-PLM
extraction order is what deterministically produces that presentation, not a hardcoded rule.

## 9. SUPERSEDED semantics

`RemediationAuthorizationStatus` (`backend/app/domain/oqi_remediation/authorization.py`) gains exactly one new
member: `SUPERSEDED = "SUPERSEDED"`. A human decision (`decide_authorization`) may produce `APPROVED` or
`REJECTED` only — `SUPERSEDED` may never be requested by any API caller; it is produced **exclusively** as the
system-driven consequence of a sibling candidate becoming `APPROVED` (§10). `SUPERSEDED` must never imply the
candidate's proposed value was false, that its supporting evidence was invalid, or that a human rejected it —
it means only that it is no longer actionable because an alternative was authorized.

## 10. Single-effective-approval invariant — application transaction contract

When approving candidate `C`'s authorization for case `K`, the service (`OqiRemediationService.approve()`,
`backend/app/application/oqi_remediation_service.py`) must, in one transaction:

```
1. lock the parent RemediationCase row K (SELECT ... FOR UPDATE, or the repository's exact equivalent
   idiom already used elsewhere in this file for authorization-row locking);
2. re-read C's authorization under that lock and re-validate it is still PENDING (existing check, preserved);
3. query all other authorizations for instructions belonging to case K;
4. confirm none is already effectively APPROVED (should be structurally impossible once step 1's lock is
   held for every approval attempt against this case, but must fail closed with a clear domain error,
   never a raw exception, if found anyway);
5. transition C's authorization to APPROVED (existing behavior, preserved);
6. transition every other still-PENDING sibling authorization for case K to SUPERSEDED;
7. set case.status = AUTHORIZED (existing behavior, preserved);
8. persist all of the above atomically, in the one existing transaction/session already in use.
```

No partial sibling state may ever be observable after this method returns — either the whole step sequence
commits, or none of it does (ordinary transactional atomicity; no new machinery required beyond the lock).

## 11. Concurrency contract

**Independently re-derived, not inferred, this phase**, from direct source read of `get_authorization_for_
update()` (`backend/app/infrastructure/persistence/oqi_remediation_repository.py:313-319`, a genuine
`SELECT ... FOR UPDATE`) and `_decide()`'s own call site: the row lock today is scoped **only to the single
authorization row being decided**, never the parent case, never sibling rows. Two concurrent `approve()` calls
against sibling authorizations of the same case touch disjoint rows and do not contend — this was proven, not
theorized, by DR-R1's own live experiment (both siblings reached `APPROVED` via a plain sequential pair of
calls, with **no** race required to reproduce the defect; a genuinely concurrent pair would fare no better).

Frozen fix: every `approve()` call must acquire the **parent case row's** lock (§10 step 1) before reading or
writing any authorization belonging to that case. This serializes all decision attempts against one case
through one lock, exactly closing the gap: whichever concurrent request acquires the case lock first
completes the full sequence in §10 (including superseding the sibling); the second request, once it acquires
the lock, finds its own target authorization already `SUPERSEDED` (or the case already `AUTHORIZED`) and must
fail closed with an existing-vocabulary error — `REMEDIATION_AUTHORIZATION_NOT_PENDING` (the same code the
`_decide()` method already raises today when an authorization's status is anything but `PENDING`, confirmed by
direct read; no new error code is authorized unless implementation finds this code's existing message
genuinely misleading in this new context, in which case use `REMEDIATION_AUTHORIZATION_NOT_PENDING` with
updated user-facing copy only — never a new machine-readable code without returning to governance).

## 12. Database defense-in-depth

Frozen, following this repository's own established precedent (CDD-052 §6/§13, CDD-053 §9/§13, CDD-054
§14/§15, CDD-055 §12/§13 — each added DB-level structural enforcement for a governance-critical invariant
specifically because application-layer checks alone were judged insufficient):

```
ADD COLUMN oqi_remediation_authorizations.case_id UUID NOT NULL
  (denormalized from instruction.case_id -- mirrors the existing precedent where
   oqi_remediation_instructions already denormalizes finding_id even though it is reachable via case_id)
ADD CONSTRAINT fk_oqi_remediation_authorizations_case_id
  FOREIGN KEY (case_id) REFERENCES oqi_remediation_cases (case_id)
CREATE UNIQUE INDEX uq_oqi_remediation_authorizations_case_one_approved
  ON oqi_remediation_authorizations (case_id)
  WHERE status = 'APPROVED'
```

Purpose: even if a future code path bypasses the parent-case lock in §10/§11, PostgreSQL itself rejects a
second `APPROVED` row for the same `case_id` with a `UniqueViolation`, which the repository/service layer must
catch and translate to the same `REMEDIATION_AUTHORIZATION_NOT_PENDING`-class domain error, never an
unhandled 500. This is defense-in-depth, not the primary enforcement path — §10/§11 remain the primary,
user-facing correctness mechanism.

## 13. Migration contract — exactly one new migration authorized

```
Expected file: backend/app/infrastructure/persistence/migrations/versions/0048_oqi_remediation_
               authorization_mutual_exclusion.py
down_revision: "0047_oqi_h6_uniqueness"
```

Frozen upgrade order:

```
1. add case_id as NULLABLE first (safe against any existing rows);
2. backfill: UPDATE oqi_remediation_authorizations SET case_id = <instruction.case_id via join> for every
   existing row -- structurally guaranteed complete: authorization.instruction_id is NOT NULL + FK-enforced,
   instruction.case_id is NOT NULL + FK-enforced, so no row can lack a resolvable case_id;
3. defensive pre-check, MUST run and MUST fail the migration loudly (raise, do not silently proceed) if it
   finds: SELECT case_id, COUNT(*) FROM oqi_remediation_authorizations WHERE status = 'APPROVED'
   GROUP BY case_id HAVING COUNT(*) > 1 returns any row -- i.e. if any environment's already-persisted data
   already violates the invariant this migration is about to enforce, the migration must STOP and require a
   governed data-repair decision, never silently pick a winner (per §14 of the governing prompt);
4. alter case_id to NOT NULL;
5. add the FK constraint (§12);
6. add the partial unique index (§12).
```

Downgrade must reverse only what this migration creates (drop the unique index, drop the FK, drop the
column) — it must not touch `0047` or any earlier migration, and must not attempt to resurrect pre-migration
data.

**Existing-data invariant check, performed this phase (not deferred to I):** the Golden Demo's own seed
lifecycle (`DemoOqiSeeder`) never creates a remediation case at seed time — confirmed by direct read,
consistent with DR-R1's own finding that "the demo must begin with no remediation case." CI's test databases
are recreated per-run. No currently-known environment this program controls can contain a pre-existing
violation of this invariant; the pre-check in step 3 exists as a permanent, structural safeguard for any
environment this program does not control, not because one is currently known to exist.

## 14. Execution-report contract — preserved, VERIFY ONLY

`report_external_execution()` (`backend/app/application/oqi_remediation_service.py:452-511`) already requires
`authorization.status is APPROVED`, explicitly rejects `REJECTED` with `REMEDIATION_AUTHORIZATION_REJECTED`,
and falls through to `REMEDIATION_AUTHORIZATION_NOT_PENDING` for any other status — **live-proven this
session** (DR-R1's own experimental simulation: calling this method against a manually-superseded sibling
correctly returned `409 REMEDIATION_AUTHORIZATION_REJECTED`; calling it against the genuinely approved
authorization succeeded and returned `EXTERNAL_EXECUTION_REPORTED`). Once `SUPERSEDED` exists as a real status
value, it falls into this same "anything but `APPROVED`" branch automatically — **no code change required in
this method**, confirmed by direct re-read of its exhaustive status branching this phase.

## 15. Re-evaluation contract — preserved, VERIFY ONLY

Re-evaluation is triggered automatically, server-side, within the same `report-execution` request (existing
behavior, `backend/app/api/oqi/router.py:668-692`, unmodified by this amendment). It never mutates source
evidence. **Live-proven this session**, end-to-end through the full simulated-fix lifecycle: after
report-execution + automatic re-evaluation, `quality_comparison_findings.status` remained `OPEN` and every
`field_value_evidence` row (SAP=US, PLM=MX, and all others) was byte-identical before and after, via direct
database comparison. REMEDIATION ≠ RESOLUTION is proven to hold through the corrected lifecycle design, not
merely asserted.

## 16. Explicit-rejection residual — frozen as KNOWN OUT-OF-SCOPE

If the sole/last remaining candidate's authorization is explicitly `REJECTED` by a human and no `PENDING`
authorization remains for the case, `case.status` can remain stuck at `AWAITING_AUTHORITY` with nothing
actionable — confirmed by direct read: `reject()` (`_decide()` with `REJECTED`) never calls `save_case()` at
all, unlike `approve()`. **This is a genuine, real, pre-existing defect, independent of the plural-candidate
correction, and it is explicitly NOT authorized for correction by this amendment.** It is unrelated to the
Golden signature approval path (which always approves the deterministic candidate matching the actual
governed evidence basis) and was discovered only as a byproduct of this investigation. Implementation must
not attempt to fix it, and must not weaken or skip a test to avoid exercising it. A future, separate governed
hardening phase is recommended after Golden Demo closure — not before, and not as part of this correction.

## 17. Plural frontend UX

`remediation-panel.tsx` renders every candidate in `remediation.candidates` (§7's order), showing for each:
proposed value, basis, and its own authorization's status/available action (reusing the existing,
already-correct `DecideAuthorizationDialog`/`ReportExecutionDialog` per-candidate, keyed by that candidate's
own `authorization_id` — both components are unmodified by this amendment; VERIFY ONLY that they continue to
receive the correct per-candidate `authorization_id`). No candidate may ever be labeled "correct," "winner,"
"truth," or "recommended" unless `remediation.recommendation` (a real, governed, separate field, already
existing, unmodified) genuinely names it.

## 18. UI after approval

Once one candidate's authorization is `APPROVED`: that candidate shows `APPROVED`; every sibling whose
authorization is now `SUPERSEDED` shows that status with honest copy equivalent to "Superseded — an
alternative candidate was approved," with its action controls disabled. **UI disablement is cosmetic only —
the backend transaction (§10) and the database constraint (§12) are the actual enforcement boundary**, exactly
as the governing prompt requires; implementation must never treat client-side disablement as sufficient on
its own.

## 19. Entity Resolution — steward queue preserved unchanged

`/data/entity-resolution`'s existing `EntityResolutionWorkspace` → `entityResolutionApi.queue()` →
`QUEUE_OUTCOMES = (POSSIBLE, UNRESOLVED, BLOCKED_CONFLICT)` (`backend/app/application/entity_resolution_
steward_api.py:49-53`) is **frozen exactly as-is**. This amendment authorizes **zero** modification to this
constant, to the `queue()` method, or to any of its existing callers. `RESOLVED` must never be added to it.
This is a deliberate work-queue contract (confirmed by the file's own module docstring), not a defect.

## 20. Resolved-identity entity lookup — new, additive surface

```
GET /api/v1/entity-resolution/entities/{entity_id}
```

matching the router's own existing convention (`APIRouter(prefix="/api/v1/entity-resolution")`, sibling to the
existing `/cases` and `/cases/{understanding_key}` routes — independently re-confirmed by direct file read
this phase, §2). Tenant-scoped via `authenticated.tenant_id` exactly as every other lookup in this file
already is. Response:

```
{
  enterprise_entity_id: str
  enterprise_entity_name: str
  records: [
    {
      understanding_key: str
      outcome: str
      business_confidence: str
      structured_reasons: string[]
      narrative_explanation: str | null
      produced_at: str
      source_representations: ... (existing shape, reused from CaseDetailResponse)
    }, ...
  ]
}
```

No new persisted truth is introduced — every field is read from `EntityResolutionStore`'s existing methods,
reusing the same data `get_case()` (`entity_resolution_steward_api.py:123-180`) already assembles per-record,
generalized to return one row per resolution record contributing to the given `enterprise_entity_id` (Meridian
has exactly two: one from SAP, one from PLM) rather than one row per `understanding_key`. Unknown
`entity_id`: 404. Wrong-tenant `entity_id`: 404 (identical fail-closed shape to every other lookup in this
router — no distinguishable error between "doesn't exist" and "exists in another tenant," matching
established convention). Entity with zero resolution records: 404 (an `EnterpriseEntity` with no resolution
history is not a resolved identity; this mirrors `get_case()`'s own `None`-on-missing-record behavior).

## 21. Resolved-identity frontend route

```
CREATE frontend/app/data/entity-resolution/entities/[entityId]/page.tsx
CREATE frontend/app/data/entity-resolution/entities/[entityId]/_components/resolved-entity-detail.tsx
```

matching this Golden Demo work's own established colocation convention (`_components` directly under the
route, as used throughout `app/quality/findings/[findingId]/_components/`). This is explicitly **not** the
steward queue — it is a read-only detail surface showing the canonical `EnterpriseEntity` and every
contributing source resolution record (§20's response shape), reusing `case-detail-panel.tsx`'s existing
rendering primitives where the shapes align rather than duplicating presentation logic.

## 22. Evidence → resolved-entity deep link — exact prop thread

Independently re-traced this phase (not re-cited): `frontend/app/quality/findings/[findingId]/page.tsx`'s own
`load()` function already calls `oqiApi.ontologyImpact(findingId)` as part of its existing `Promise.all(...)`
(unchanged), storing the result as `state.impact: OntologyImpactResponse`, which already carries
`direct_entity_id: string | null` on the existing, unmodified contract. The **only** required change on this
file is passing `entityId={state.impact.direct_entity_id}` as a new prop into the existing `<EvidencePanel>`
render call. `evidence-panel.tsx` gains `entityId: string | null` as a new prop; when it is non-null and the
existing OQI2-only condition for showing the contextual link still holds (unchanged), the link's `href`
becomes `/data/entity-resolution/entities/${entityId}` instead of the current bare `/data/entity-resolution`.
No display-name lookup. No hardcoded Meridian UUID anywhere in this path — the mechanism is fully general for
any Finding/entity with a governed resolved identity.

## 23. Golden entity expectation

For the Golden seed, Meridian Cell Components must show **both** governed contributing resolution records
(SAP and PLM, both `Resolved`) — independently re-confirmed present in the database this session (two
`EnterpriseEntityResolutionRecord` rows, `outcome = 'Resolved'`, one per source object). This proves "multiple
source representations resolve to one governed enterprise identity" — a claim distinct from, and never to be
conflated with, the Country-of-Origin *value* disagreement (US vs. MX) the OQI2 Finding itself is about.
Resolving WHO the supplier is and resolving WHAT its country of origin is are separate governed questions;
this page answers only the first.

## 24. Security / tenancy — preserved, no weakening authorized

Remediation: tenant sourced exclusively from `authenticated.tenant_id`; actor sourced exclusively from
`authenticated.principal_id` (prepare) or the session's own `sub` claim (decide, unchanged,
`DecideAuthorizationDialog` already does this correctly); self-approval prohibited backend-side (unchanged,
`decided_by == authorization.requested_by` check, `oqi_remediation_service.py:429`); authorization scopes
enforced (`oqi-remediation:prepare`/`:authorize`/`:report-execution`, unchanged). Entity Resolution: new
lookup is tenant-scoped exactly as every existing lookup in the same file; no cross-tenant record can ever
appear in a response (§20). No security boundary in either domain is weakened for demo convenience anywhere
in this amendment.

## 25. No agent change, no seed change

No agent code path is authorized by this amendment. Agent Investigation remains "not invoked" for the Golden
Finding; no automatic agent recommendation; no agent-triggered remediation; no new recommendation semantics.
No demo seed change is authorized — the Golden seed's `SAP=US`/`PLM=MX` evidence and its deliberate omission
of any pre-seeded remediation case (so the presenter visibly performs Prepare live) are both already correct
and unmodified.

## 26. Golden runbook disposition

The existing narration "the system proposes real candidates from the real conflicting evidence — US and
MX — never a fabricated single answer" (runbook row 9) **remains correct as written and requires no change**.
The corrected product will genuinely and persistently show both candidates. If implementation independently
discovers this wording is not achievable exactly as designed: **STOP and return to governance** — do not
silently edit the runbook to paper over an implementation shortfall.

## 27. Exact Artifact Authorization

### 27.1 Backend

```
MODIFY  backend/app/domain/oqi_remediation/authorization.py
        Add exactly one new RemediationAuthorizationStatus member: SUPERSEDED. No other enum, class, or
        function in this file may change.

MODIFY  backend/app/application/oqi_remediation_service.py
        approve(): extend per §10/§11 exactly (parent-case lock, sibling query, sibling supersession, all in
        the existing transaction). No other method's behavior may change except as required to catch and
        translate the new partial-unique-index violation (§12) into the existing REMEDIATION_AUTHORIZATION_
        NOT_PENDING-class error. reject(), report_external_execution(), refresh_case() unchanged (VERIFY
        ONLY, §14/§15).

MODIFY  backend/app/infrastructure/persistence/oqi_remediation_repository.py
        Add: a parent-case FOR UPDATE lock operation; a sibling-authorizations-for-case query; a
        sibling-authorization bulk status-update operation; a plural, deterministically-ordered
        candidates-for-case retrieval (§8). No existing method signature may change in an incompatible way.

MODIFY  backend/app/infrastructure/persistence/models/oqi_remediation.py
        OqiRemediationAuthorizationORM gains exactly one new column: case_id (UUID, NOT NULL after
        migration, FK to oqi_remediation_cases.case_id) plus the partial unique index (§12). No other model
        in this file may change.

CREATE  backend/app/infrastructure/persistence/migrations/versions/0048_oqi_remediation_authorization_
        mutual_exclusion.py
        Exactly the six-step upgrade in §13, and its exact-inverse downgrade. No other migration file may
        be created or modified.

MODIFY  backend/app/api/oqi/schemas.py
        RemediationResponse (and its nested view types) become plural per §7. PrepareRemediationRequest/
        PrepareRemediationResponse/DecideAuthorizationRequest/ReportExecutionRequest/
        RemediationCaseActionResponse unchanged.

MODIFY  backend/app/api/oqi/router.py
        get_remediation(): build the plural response from the repository's new plural retrieval (§7/§8).
        prepare_remediation()/decide_authorization()/report_execution() unchanged (VERIFY ONLY).

MODIFY  backend/app/application/oqi_product_experience_service.py
        get_remediation(): rewritten to assemble the plural RemediationRow per §7/§8, replacing the current
        candidates[0]/ORDER BY created_on DESC LIMIT 1 logic. No other method in this file may change.

MODIFY  backend/app/application/entity_resolution_steward_api.py
        Add exactly one new, additive method implementing §20's lookup, reusing get_case()'s existing
        per-record assembly logic generalized to iterate every resolution record for a given
        enterprise_entity_id. queue()/QUEUE_OUTCOMES/get_case()/list_cases and every other existing method
        in this file remain completely unmodified (§19).

MODIFY  backend/app/api/entity_resolution/router.py
        Add exactly one new, additive route: GET /entities/{entity_id} per §20. No existing route in this
        file may change.
```

### 27.2 Frontend

```
MODIFY  frontend/lib/auth/config.ts
        Add exactly one string, "oqi-remediation:prepare", to BACKEND_CAPABILITY_SCOPES. No other line may
        change.

MODIFY  frontend/lib/oqi/api-client.ts
        Add exactly one new function, prepareRemediation(findingId), calling POST .../remediation/prepare.
        Update the existing remediation() function's return type only to the extent required by the plural
        contract (§7) -- no new remediation-domain function beyond prepareRemediation.

MODIFY  frontend/lib/oqi/contracts.ts
        RemediationResponse (and nested types) become plural per §7, replacing the existing singular fields.
        No other interface in this file may change.

MODIFY  frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx
        Add the Prepare control (§6) to the current hasNothing branch; render every candidate in
        remediation.candidates (§17); render SUPERSEDED siblings per §18. No other component's markup
        changes as a result of this file's edit.

VERIFY ONLY  frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
        Reads only case_status; confirm this remains true and unaffected by the plural candidate change.
        No edit authorized unless verification proves otherwise, in which case: STOP, return to governance.

MODIFY  frontend/app/quality/findings/[findingId]/page.tsx
        Pass entityId={state.impact.direct_entity_id} into the existing <EvidencePanel> render call (§22).
        No other line in this file's load()/render logic may change.

MODIFY  frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx
        Accept entityId: string | null; change the existing OQI2-only link's href per §22. No other markup,
        prop, or conditional branch in this file may change.

CREATE  frontend/app/data/entity-resolution/entities/[entityId]/page.tsx
CREATE  frontend/app/data/entity-resolution/entities/[entityId]/_components/resolved-entity-detail.tsx
        Per §21. No other new route/component is authorized.

MODIFY  frontend/lib/entity-resolution/contracts.ts
        Add exactly one new interface matching §20's response shape. No existing interface may change.

MODIFY  frontend/lib/entity-resolution/api-client.ts
        Add exactly one new function calling GET /entities/{entity_id}. No existing function may change.
```

### 27.3 Tests

```
MODIFY  backend/app/tests/test_production_remediation_orchestration_postgres.py
        Add coverage for: real CROSS_SOURCE_VALUE_CONFLICT prepare producing 2 candidates; approve one →
        sibling SUPERSEDED; second sibling cannot become effectively APPROVED (service-level); concurrent
        sibling-approval attempts (both spawned against the same case) → at most one APPROVED; wrong tenant
        cannot decide a sibling; self-approval remains prohibited; report-execution only for APPROVED,
        rejected for SUPERSEDED; re-evaluation leaves Finding OPEN with unchanged source evidence; existing
        single-candidate cases (already covered) remain passing unchanged; prepare idempotency remains
        intact. No existing test in this file may be weakened, skipped, or deleted.

MODIFY  backend/app/tests/test_oqi_api_postgres.py (or the existing router-level remediation test file this
        repository actually uses -- implementation must independently confirm the exact file, not guess)
        Add: plural GET returns both candidates; deterministic ordering.

CREATE  backend/app/tests/test_oqi_remediation_authorization_migration_postgres.py
        Per §28 (migration tests) -- upgrade from 0047, backfill correctness, NOT NULL, FK, partial unique
        index rejecting a second APPROVED row at the database layer directly (bypassing the application
        layer, to prove defense-in-depth independently of §10/§11), downgrade reverses only this migration's
        own changes, existing migration round-trip tests remain clean.

CREATE  backend/app/tests/test_entity_resolution_entity_lookup_postgres.py
        Found (multi-record, Meridian-equivalent fixture); unknown entity_id → 404; wrong-tenant entity_id →
        404; entity with zero resolution records → 404; queue()/QUEUE_OUTCOMES unaffected (regression guard
        against accidental modification).

MODIFY  frontend/tests/oqi-remediation-actions.test.tsx
        Add: prepare scope requested at sign-in; Prepare control renders and invokes the API; state refresh
        after prepare; both candidates render; deterministic order; APPROVED/SUPERSEDED rendering; sibling
        action controls disabled after a sibling is approved; existing DecideAuthorizationDialog/
        ReportExecutionDialog coverage unchanged.

MODIFY  (or CREATE, if no existing file covers this component) an entity-resolution frontend test file
        covering: entity-specific Evidence href construction; resolved-entity page rendering multiple
        source records; not-found behavior. Implementation must name the exact file before writing it, not
        after.
```

### 27.4 Accounting

```
CREATE       = 6   (1 migration, 2 backend test files, 2 frontend route/component files under
                     entities/[entityId]/, +1 possible new frontend test file if no existing file covers it
                     -- implementation must resolve this exact count before writing code, per §41 of the
                     governing prompt; if the frontend test path resolves to MODIFY instead, CREATE = 5)
MODIFY       = 17  (9 backend production files + 2 backend test files + 6 frontend production files)
VERIFY ONLY  = 1   (remediation-stepper.tsx)
DELETE       = 0
```

No implementation may touch any path outside this exact set. Any path not named above and found genuinely
necessary during implementation requires a STOP and a narrow follow-up amendment — exactly this program's
own established discipline (`CDD-084-Artifact-Authorization-H6-G-R1`, `CDD-050-Artifact-Authorization-H4-R1`,
`CDD-085-Artifact-Authorization-G-R1`, `CDD-085-Artifact-Authorization-G-R2`).

### 27.5 Explicitly prohibited paths (non-exhaustive callouts)

`keycloak/ctec-realm.json` (already correct, §5); `entity_resolution_steward_api.py`'s `queue()`/
`QUEUE_OUTCOMES`/`list_cases`/`get_case()` (§19, unmodified); `backend/app/infrastructure/persistence/
migrations/versions/0047_oqi_h6_uniqueness.py` or any earlier migration; any `DemoOqiSeeder` file (§25); any
agent code path (§25); `docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md` (§26); `remediation-stepper.tsx` beyond
VERIFY ONLY; PR #250, #249, #248, and `product/noetva-demo-readiness-final`/`-i-r2`/`-r1` themselves (§29).

## 28. Future backend/frontend/DB/Docker/browser acceptance crowns — frozen for I/VM

```
Backend:    targeted remediation + entity-resolution tests; Golden 18/18; Parity 23/23; H4 32/32; full
            CI-faithful backend suite, zero failures.
Frontend:   targeted tests; complete suite; format; lint; typecheck; production build.
DB:         two concurrent sibling-approval attempts against one case, followed by a direct SQL query,
            COUNT(*) <= 1 for status='APPROVED' grouped by case_id -- proven at the database layer, not
            merely through the UI.
Docker:     fresh image build; fresh Postgres; migration 0047 -> 0048; demo-reset; demo-verify 11/11.
Browser:    real Keycloak Authorization Code + PKCE, no bypass -- the exact 22-step journey in DR-R1's own
            §V, reproduced here as the binding acceptance crown for the eventual VM phase:
            login -> Golden Finding -> Evidence shows SAP=US/PLM=MX -> View resolved entity ->
            entity-specific page shows Meridian with both SAP and PLM records -> continue Golden journey ->
            Remediation initially has no case -> Prepare -> both US and MX visible, both PENDING ->
            authorize one -> approved candidate shows APPROVED, sibling shows SUPERSEDED -> attempting to
            approve the sibling cannot create a second APPROVED -> report execution against the approved
            authorization -> server re-evaluates -> Finding remains OPEN -> SAP=US/PLM=MX evidence unchanged
            -> reset -> demo-verify 11/11.
```

## 29. Composition and PR strategy

This amendment does not modify, rebase, or advance `product/noetva-demo-readiness-final` (`b254372b...`) or
PR #250 — both remain exactly as they are, PR #250 preserved as historical evidence of the exact candidate
`NOETVA-DEMO-READINESS-VM` correctly refused to merge. PR #249 and PR #248 remain untouched. This amendment
is published on a new branch cut from authoritative `origin/main`,
`product/noetva-demo-readiness-g-r4` (following this program's established convention of never reusing a
prior governance branch for a new amendment). The future implementation phase (`NOETVA-GOLDEN-SIGNATURE-UX-I`)
must compose its own new candidate from exactly `b254372b9632c0bd16174678e2ba7f2afd95688c` plus this
amendment's own governance commit plus the exact §27 path set — mirroring the exact composition method
`NOETVA-CI-BACKEND-ISOLATION-I-R1` already used successfully (branch from the certified prior candidate,
cherry-pick the governance commit, apply the authorized correction). No implementation PR exists yet; the
future implementation phase must open a new PR, never reuse #250.

## 30. Authorization

This amendment is approved and published as a standalone governance artifact, following this program's
established convention of never silently rewriting an already-approved Artifact Authorization in place.
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original companion Artifact Authorization,
its G-R1 and G-R2 amendments, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion Artifact
Authorization all remain FROZEN, unmodified, and fully authoritative. This amendment's §27 authorizes exactly
the path set enumerated there — 6 CREATE, 17 MODIFY, 1 VERIFY ONLY, 0 DELETE (subject to the one
implementation-time resolution noted in §27.4) — confined to remediation Prepare/plural-candidate/
mutual-exclusion correctness and the resolved-entity-identity read surface, and nothing else. No
implementation write against any path has occurred as part of this amendment. Implementation readiness is
reauthorized to resume, under the identifier `NOETVA-GOLDEN-SIGNATURE-UX-I`, only after that phase's own
complete, independent re-verification of every crown in §28.
