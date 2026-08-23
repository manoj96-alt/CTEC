# CDD-027 — Human-Approver Attribution Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Authority base: `9b7df4270187815a44d1d2dd25bc2ad509372d6a`

## Decision

This report resolves the Gate L6 implementation discovery finding: the published "CDD-027 — AI-
Assisted Semantic Mapping Candidate Discovery — Artifact Authorization" (§4.2) specifies
`approve()` constructing `created_by=Identifier(principal.principal_id)` on the resulting `Approved`
`SemanticMapping` row. Direct tracing of `SemanticMapping.created_by`/`modified_by` (§4.2 target
fields) against the actual, unmodified persistence contract found: (a) `principal.principal_id` is
`str` (the verified OIDC `sub` claim), while `Identifier` requires `UUID` — a direct type
incompatibility; (b) even a UUID-shaped value would need to satisfy a hard foreign-key constraint to
`enterprise_entities.enterprise_entity_id` (`fk_semantic_mappings_created_by`/`...modified_by`,
confirmed in `backend/app/infrastructure/persistence/models/semantic_mapping.py`), and no mapping
from an authenticated `TrustedPrincipal` subject to any `EnterpriseEntity` row exists anywhere in
this repository (confirmed by exhaustive search across domain, persistence, application,
authentication, and migration code). This is exactly the "governance discovery finding uncovered
during implementation, correctable without editing the frozen/published governing document" pattern
already established by this repository (see `CDD-015-Runtime-Composition-Clarification-and-
Remediation-Report.md` and its own two sibling reports against CDD-015): a standalone companion
document to the already-approved Gate L Artifact Authorization, not an edit to that document's own
text, not an edit to CDD-027 itself, and not a new architecture baseline.

Re-reading CDD-027 §13 and §15 directly (not the Artifact Authorization's own restatement of them)
confirms this is an Artifact-Authorization-only drafting error, not a CDD-027 requirement: §13
defines only the structural approval requirement (an authenticated `TrustedPrincipal` action
triggers a new, non-mutating `create()` call); §15 explicitly frames "the human approver's identity"
as content of "a record structurally separate from `SemanticMapping`" — CDD-027 itself never
required `SemanticMapping.created_by`/`modified_by` to carry it. Product Owner Decision L4-D2
(unchanged, not reopened) already deferred creating that separate record; this report corrects the
Artifact Authorization's own erroneous assumption that `created_by` could substitute for it.

## Gap verification (repeated directly against repository state)

- `backend/app/infrastructure/persistence/models/semantic_mapping.py`: `created_by: Mapped[UUID]`
  and `modified_by: Mapped[UUID | None]` both carry `ForeignKey("enterprise_entities.
  enterprise_entity_id", ...)`.
- `backend/app/domain/shared/value_objects/reference.py`: `Identifier.__post_init__` raises
  `ValidationException` unless `self.value` is an instance of `UUID`.
- `backend/app/api/supplier_risk/authentication.py`: `TrustedPrincipal.principal_id: str`
  (`principal_id=subject`, the JWT `sub` claim — no guaranteed UUID shape, no guaranteed
  correspondence to any `EnterpriseEntity` row).
- Exhaustive repository search (domain, persistence, application, authentication, tests, migrations)
  found zero precedent for populating an `enterprise_entities`-FK-backed column from a live
  `TrustedPrincipal` identity. The two existing precedents that actually persist an authenticated
  principal's identity durably — `EnterpriseEntityResolutionRecord.actor_id` (Gate C) and
  `ApiSecurityAuditEvent.principal_reference` (CDD-013) — both use a **plain string field with no
  FK**, never the `enterprise_entities` convention.
- `BOOTSTRAP_SYSTEM_ENTITY_ID` (`app.core.bootstrap`, unmodified) is the established, repository-wide
  convention for `created_by` on every system/proposal-originated governed row across this codebase
  (`blueprint_seed.py`, `ontology_seed.py`, `demo_semantic_mapping_seeder.py`, and others) — already
  the correct value for the `Proposed` row (unaffected by this report) and, by identical reasoning,
  the correct value for the `Approved` row.

## Resolved items

**A — Artifact Authorization §4.2, `approve()` (CLARIFIED, not modified in the repository).** The
`Approved` `SemanticMapping` row's `created_by` is `Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID)` — not
derived from `principal.principal_id` in any way. `modified_by` remains `None` on this initial
write, matching every other single-write `create()` call precedent in this repository. Human
approval authority continues to be enforced entirely by requiring a real, Gate-E-verified
`TrustedPrincipal` (tenant/scope/role checked) as `approve()`'s own required parameter — this
enforcement is unchanged and remains the actual governance control; only the *persisted attribution
value* is corrected.

**B — Artifact Authorization §9 (CLARIFIED).** `created_by=BOOTSTRAP_SYSTEM_ENTITY_ID` on both
`Proposed` and `Approved` rows satisfies only CDD-027 §15's *origin-distinction* requirement (this
row is proposal-system-originated, not human-authored via any other path). It does **not**, and is
not claimed to, satisfy §15's separate *human-approver-identity* requirement, which remains deferred
in full — not partially satisfied, as the original Artifact Authorization text could have been
misread to imply.

**C — Artifact Authorization §16, Non-claims (CLARIFIED, additive).** Add, as an explicit non-claim:
"any durable, governed linkage between a specific `TrustedPrincipal` subject and the resulting
`Approved` `SemanticMapping` — human-approver identity is verified at approval time (a real
authorization check) but is never persisted as `SemanticMapping` attribution or in any new record.
`BOOTSTRAP_SYSTEM_ENTITY_ID` on an `Approved` row must never be represented, documented, or tested as
if it secretly encodes or is recoverable to the specific human who approved it."

**D — Test obligations (CLARIFIED, additive).** The implementation's test suite must additionally
prove: `approve()` genuinely checks `TrustedPrincipal` tenant/scope/role authority (not merely
accepts any principal); `principal.principal_id` never appears in the resulting `Approved` row's
`created_by`/`modified_by`; `created_by` on the `Approved` row equals `BOOTSTRAP_SYSTEM_ENTITY_ID`
exactly; no test fabricates or relies on a human-linked `EnterpriseEntity` or any OIDC-subject
mapping; a structural assertion confirms no new table/column/record exists for durable per-human
provenance.

**E — Nothing else is authorized or changed by this report.** In particular, this report does NOT
authorize: any modification to CDD-027 itself; any modification to the Artifact Authorization
document's own file (this report supersedes only the *interpretation* of §4.2/§9/§16, as a
standalone companion — the original document's text is not edited); any new migration, persistence
model, or audit mechanism; any `EnterpriseEntity` fabrication or OIDC→`EnterpriseEntity` mapping; any
change to the existing six-file implementation allowlist; any change to `dependency_container.py`,
Gate E's authentication runtime, or H1/H2; any real model-provider integration, API, or frontend.

## Compatibility and boundaries

- No modification to CDD-027: §13's structural approval requirement and §15's separate-record
  framing are both already fully compatible with this clarification — confirmed by direct re-reading
  of both sections' own text, not merely asserted.
- No modification to the published Artifact Authorization's own file — this report is a standalone,
  additive companion, following the CDD-015 precedent of a second, independent report against an
  already-approved governing document.
- No modification to `architecture/INDEX.md`'s existing CDD-027 row structure beyond adding one
  additional companion link, following the identical CDD-015 precedent (a second/third link added to
  the same row).
- No modification to `architecture/released/*` and no new architecture baseline — this remediation
  is scoped entirely within CDD-027's own non-baseline-tracked `architecture/INDEX.md` entry.
- Gate E's authentication runtime, `TrustedPrincipal`, and JWT validation remain entirely unmodified;
  this report authorizes no new authentication or authorization framework.
- The six-file implementation allowlist (§3 of the original Artifact Authorization) is unchanged in
  every path, action, and purpose.

## Validation and rollback

Implementation under this report must pass every test obligation in the original Artifact
Authorization §12, as clarified/extended by Resolved Item D above. Rollback reverts only the
corrected `created_by`/`modified_by` values inside `approve()`'s own implementation (once written) —
no existing capability, migration, or governance document is affected by rollback, since none of
them are touched by this report in the first place.
