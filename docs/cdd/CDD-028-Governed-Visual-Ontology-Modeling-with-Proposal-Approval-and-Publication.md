# CDD-028 — Governed Visual Ontology Modeling with Proposal, Approval, and Publication

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — §2-3, binding on this
CDD's entire scope, §9 below), RFC-013 (FROZEN, Governance Authority and Evaluation Separation — the
constitutional basis for this CDD's separated APPROVE/PUBLISH human actions, §14/§16 below), RFC-015
(FROZEN, Tenant Ownership Physical Model Authorization — establishes the tenant-origin discipline this
CDD's canonical target explicitly does not carry, §10 below), CDD-003 Revision 2 (FROZEN, canonical
entity enumeration — `EntityType`/`RelationshipType`/`InstitutionalConcept` are the RFC-010-protected
entities this CDD's PUBLISH step alone may write to, §9 below), CDD-016 (FROZEN, Gate F — first named
"visual ontology modeling" as an excluded non-goal, §6 below), CDD-017 through CDD-027 (FROZEN, Gates
G/H/I/J/K/L/N/P, unchanged, none consumed or modified, §24-§25 below)
Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via discovery (Gate M0, which
established that no prior authority sufficiently defined "Gate M") → Product Owner architecture-decision
resolution (Gate M1, resolving Decisions M-D1 through M-D3 and M1-D1 through M1-D4) → drafting (Gate M2)
→ Product Owner open-question resolution (Gate M2-R1, resolving M2-OQ-1/M2-OQ-2/M2-OQ-3) → a
discovered-and-resolved scope correction (Gate M2-R2, Decision M2-R2-D1 — NET-NEW ontology creation only,
existing-object modification/versioning explicitly deferred, unnumbered) → Product Owner approval of the
fully integrated draft, with P0=0/P1=0/P2=0 confirmed at the final review stage → this Gate M2-R3
publication turn. No implementation exists, and none is authorized by this frozen document — a separate,
subsequent Artifact Authorization companion remains required before any file is created or modified.

## 1. Objective and business outcome

Allow an authenticated, newly-scoped enterprise user to visually explore CTEC's governed ontology and
construct a **net-new** candidate Concept or Relationship, persist that candidate as a durable,
non-canonical proposal, have it reviewed and either REJECTed (durably, with attribution) or APPROVEd, and
— only through a separate, independently-authorized PUBLISH action — materialize it as the **initial**
canonical representation of a new `EntityType`/`InstitutionalConcept` or `RelationshipType`/
`OntologyRelationshipBinding` pair. The modeling workspace never becomes canonical ontology authority at
any point in this flow. Modification, renaming, replacement, retirement, deletion, or supersession of an
**existing** canonical ontology object is explicitly out of scope (§27).

## 2. Governing authorities

(restated per header)

## 3. Why this CDD requires its own governance

Gate M0 confirmed the only existing mechanism able to write `EntityType`/`RelationshipType`/
`InstitutionalConcept` is `OntologySeeder.load()` — a deploy/test-time-only static loader, never invoked
by any human action or API. CDD-016 §4/§11 and CDD-027 §24 both named "visual ontology modeling" as an
excluded non-goal without ever defining it. This CDD is the first document to define, rather than merely
exclude, that capability.

## 4. In scope

VIEW (reusing, unmodified, `resolve_supplier_risk_ontology`/`GET /api/v1/ontologies/*`); ephemeral,
client-side visual construction of one net-new candidate Concept or Relationship; deterministic
server-side validation against live canonical state; persistence of a validated candidate as a new,
non-canonical `OntologyChangeProposal`; an authenticated human APPROVE/REJECT decision; a separate,
independently-authorized human PUBLISH action that alone may write `entity_types`/`institutional_concepts`
/`relationship_types`/`ontology_relationship_bindings`, and only ever an **initial** representation of a
new object; two new, narrow authorization scopes (§14).

## 5. Explicit MVP capability (binding — encodes M2-R2-D1)

Gate M MVP supports exactly: proposing a NEW Concept; proposing a NEW Relationship; reviewing a proposal;
approving or rejecting it; separately publishing an Approved proposal; creating the **initial** canonical
representation of that new object. Gate M MVP does **not** support modifying, renaming, replacing,
retiring, deleting, or superseding any existing Concept or Relationship (§27).

## 6. Out of scope (binding)

Any modification to an *existing* `EntityType`, `RelationshipType`, `InstitutionalConcept`, or
`OntologyRelationshipBinding` row, under any name (rename/modify/replace/retire/delete/supersede — §27).
Any write to `entity_types`/`relationship_types`/`institutional_concepts`/`ontology_relationship_bindings`
outside the single PUBLISH write path (§16). Any modification to `resolver.py` or any consumer of it
(§20). Any modification to `OntologySeeder`/`ontology_seed.py`. Any downstream wiring of a newly Published
object into Blueprint, H1-H4, Gate I/J/K/L/N/P (§21). Any tenant-scoping of canonical ontology state — none
exists (§10). Any AI/LLM/agent/MCP capability (§22). Any Gate L deferred capability (§23). Any new
authentication *mechanism* — only new *scopes* under Gate E's existing runtime (§14). Any change to
`entity_type_name`/`relationship_type_name`/`institutional_concept_name`'s existing uniqueness constraint.
Any Artifact Authorization content.

## 7. Business problem

Today, changing the enterprise ontology requires a developer to hand-edit `ontology_seed.py` and
redeploy. There is no way for a business user to propose *any* ontology change, including a wholly new
Concept or Relationship. Gate M closes that gap for the net-new case without granting the workspace
canonical authority.

## 8. Architecture problem

Let a human construct and visualize a candidate net-new ontology object against global,
non-tenant, RFC-010-protected vocabulary, such that only one clearly-bounded step can ever write a
canonical row, and that row is always structurally indistinguishable from one the existing seeder could
have written.

## 9. Canonical publication boundary / RFC-010 firewall (binding, load-bearing)

RFC-010 §2-3: "Cognitive services shall not introduce or modify canonical entities." Only the PUBLISH
action (§16) may write to `entity_types`, `institutional_concepts`, `relationship_types`, or
`ontology_relationship_bindings`. Every such write:
- targets a **net-new** object only — never an existing row (§5);
- sets `version_number = 1`, `previous_version_id = None` — identical to every row `OntologySeeder` has
  ever written;
- always sets `governance_status = "Approved"` — identical to every existing row, which is precisely what
  makes `resolver.py` safe to leave unmodified (§20);
- sets `created_by = Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID)`, never the publishing principal's
  `principal_id` — pre-applying the Gate L Human-Approver Attribution Clarification and Remediation
  Report's resolved answer from the outset (§17), rather than rediscovering that blocker mid-implementation
  as Gate L itself did.

## 10. Tenant boundary (binding)

None. `entity_types`, `relationship_types`, `institutional_concepts`, and `ontology_relationship_bindings`
carry no `tenant_id` column, confirmed by direct schema inspection. RFC-015's tenant-origin discipline
does not apply to this CDD's canonical target. Authorization here is a question of *global* authority
(§14), not tenant isolation.

## 11. User / persona

An authenticated enterprise user holding the new `ontology-modeling:propose` scope (to MODEL/SUBMIT) and,
separately, a user holding `ontology-modeling:approve` (to APPROVE/REJECT) and independently-checked
PUBLISH authority (§14). Exact persona/role naming is deferred to Artifact Authorization; no existing
scope or role in the repository maps to any of these actions.

## 12. Domain model authorized

One new, non-canonical domain entity: `OntologyChangeProposal`. Fields at the architecture level (exact
column list reserved for Artifact Authorization): `ontology_change_proposal_id`; `proposal_kind`
(`CreateConcept` | `CreateRelationship` — a new, narrow enum, distinct from `GovernanceStatus`); a
proposed-content payload (concept name/definition, or relationship name + source/target concept
reference — exact shape reserved for Artifact Authorization); a proposal lifecycle `status` (§13);
`proposed_by`/`approved_by`/`rejected_by`/`published_by` (§17); `rejection_reason` (nullable, §15).
`OntologyChangeProposal` confers no ontology authority of its own, is never read by `resolver.py` or any
existing ontology consumer, and exists solely to carry a net-new candidate object from MODEL through
PUBLISH.

## 13. Proposal lifecycle (binding, exact)

```
Proposed
    |
    | authenticated human APPROVE (S14)          authenticated human REJECT (S15)
    v                                                      v
Approved                                              Rejected (terminal)
    |
    | authenticated, independently-authorized human PUBLISH (S16)
    v
Published (terminal; initial canonical object now exists, S9)
```

REVIEW is an action a human performs over a `Proposed` row (reading it), **not a persisted state** — the
smallest architecture does not require a fifth status value for this. The durable status set is exactly
`Proposed | Approved | Rejected | Published`. `Proposed != Approved != Published`; `Rejected` is a
terminal state distinct from all three others and is never publishable. `Published` is terminal and can
never be republished. APPROVE transitions the *same* `OntologyChangeProposal` row's status (not a new
row) — a deliberate departure from Gate L's row-immutability convention, since here the proposal, not a
canonical entity, is what's being tracked; the one canonical write happens only at PUBLISH (§9), which
*does* follow the immutable-new-row convention.

## 14. Authorization semantics (binding, exact)

Two architecture-significant scopes, under Gate E's existing, unmodified OIDC/JWKS runtime — no new
authentication mechanism:
- `ontology-modeling:propose` — required for MODEL/SUBMIT (creating a `Proposed` row).
- `ontology-modeling:approve` — required for both APPROVE and REJECT (the same governance authority
  governs both, per Product Owner decision; no `ontology-modeling:reject` scope is introduced).

PUBLISH requires its own, **independently checked** authorization boundary — a prior successful APPROVE
call never implicitly authorizes a later PUBLISH call; PUBLISH re-authenticates and re-authorizes the
acting `TrustedPrincipal` at its own boundary, every time. Whether PUBLISH reuses `ontology-modeling:approve`
or requires a distinct, further-narrowed scope is safely deferred to Artifact Authorization — no frozen
authority or security property requires the literal to be fixed here, only that PUBLISH's check is
independent, which this CDD binds.

## 15. Rejection semantics (binding, exact)

REJECT requires the same authorization as APPROVE. It transitions `OntologyChangeProposal` to `Rejected`,
records `rejected_by` (§17), and performs **zero** canonical writes of any kind. It may carry a bounded,
human-readable `rejection_reason` (nullable). The reason is untrusted, display-only text: never
interpolated into any query, never treated as a governance instruction, never a channel for disclosing
anything beyond what the rejecting principal themselves typed (restated from Gate L §16's trusted-input
discipline). Exact field type, length limit, DTO shape, validation, and sanitization are deferred to
Artifact Authorization.

## 16. Publication semantics (binding, exact)

PUBLISH requires: (1) a real, Gate-E-authenticated `TrustedPrincipal` holding independently-checked
publication authority (§14); (2) the proposal's status is exactly `Approved`; (3) the proposed object is
revalidated as still genuinely net-new against **live** canonical state immediately before writing — a
name that was available at PROPOSE/APPROVE time may have been taken by a *different*, since-published
proposal, and this must be caught, not assumed away; (4) fail-closed on any conflict (§18); (5) safe
rejection of replay — an identical PUBLISH call for an already-`Published` proposal must not create a
second canonical row (§18); (6) transactional: no partial canonical object survives a failed PUBLISH; (7)
the frontend never performs this write — it is server-side, single, narrow code path only; (8) no
downstream gate is rewired as a side effect (§21).

## 17. Provenance / canonical attribution (binding)

`OntologyChangeProposal` durably records, as plain, unconstrained string fields (never `enterprise_entities`
FK columns) — following the exact precedent of `EnterpriseEntityResolutionRecord.actor_id` and
`ApiSecurityAuditEvent.principal_reference` — the authenticated `principal_id` of whoever proposed,
approved, rejected, and (if reached) published it: `proposed_by`, `approved_by`, `rejected_by`,
`published_by`. This is entirely separate from the canonical `EntityType`/`RelationshipType`/
`InstitutionalConcept` `created_by` columns, which remain `enterprise_entities`-FK-constrained and are
written **only** at PUBLISH, **only** as `BOOTSTRAP_SYSTEM_ENTITY_ID` (§9) — never the publishing
principal's `principal_id`. This does not reopen or modify Gate L's `SemanticMapping` provenance model,
and introduces no generic, reusable governance-actor abstraction — each field is narrow and
single-purpose to this artifact.

## 18. Concurrency / idempotency invariants (binding)

Binding invariants only; exact mechanism reserved for Artifact Authorization (H1's own
`uq_semantic_mappings_approved_source_field`-style partial unique index and `pg_advisory_xact_lock`
pattern are available, already-reviewed precedent, not prescribed here): a conflicting second proposal for
the same intended name cannot also publish successfully once one has published; APPROVE never guarantees
future PUBLISH success; PUBLISH always revalidates against live canonical state immediately before
writing (§16); duplicate-name publication fails closed; replay of an identical PUBLISH call cannot create
a duplicate canonical row; concurrent PUBLISH attempts for the same intended name fail closed, at most one
succeeding; no partial canonical mutation (e.g., a `RelationshipType` row without its
`OntologyRelationshipBinding`) ever survives a failed PUBLISH.

## 19. Net-new Concept publication (binding)

Before PUBLISH: proposal status is `Approved`; the proposed Concept name does not exist in
`institutional_concepts`/`entity_types` (live re-check); publication authorization passes (§14). PUBLISH
inserts, in one transaction, one new `InstitutionalConcept` row and one new `EntityType` row
(`institutional_concept_id` linking them), both `governance_status = "Approved"`, `version_number = 1`,
`previous_version_id = None`, `created_by = BOOTSTRAP_SYSTEM_ENTITY_ID` — the identical two-row shape
`OntologySeeder` already produces for every concept it seeds.

## 20. Net-new Relationship publication (binding)

Before PUBLISH: proposal status is `Approved`; the proposed Relationship name does not exist in
`relationship_types` (live re-check); the proposed source and target `EntityType` rows exist, are
`Active`, and are `Approved` (mirroring exactly the discipline Gate L's `_validate_candidate` established
for `SourceField`); publication authorization passes. PUBLISH inserts, in one transaction, one new
`RelationshipType` row and one new `OntologyRelationshipBinding` row referencing the (already-canonical)
source/target `EntityType` ids — the identical two-row shape `OntologySeeder` already produces for every
relationship it seeds. Any endpoint-validation or duplicate-name failure fails the entire transaction
closed; no orphaned `RelationshipType`-without-`OntologyRelationshipBinding` (or vice versa) may ever
exist.

## 21. Existing read-path firewall (binding)

`app.domain.ontology.resolver.resolve_supplier_risk_ontology` and every existing consumer of it (the
`GET /api/v1/ontologies/*` surface, the Ontology Studio graph, Gate F's adapters, Ask CTEC's traversal
engine) are **not modified**. Confirmed safe by construction (§9): every canonical row this CDD ever
writes carries `governance_status = "Approved"`, identical to the seeder's own convention, so the
resolver's existing unconditional read remains correct without any filter change. No `Proposed`,
`Approved`-but-unpublished, or `Rejected` `OntologyChangeProposal` can ever become visible through any
existing canonical read path, because it never enters `entity_types`/`relationship_types`/
`institutional_concepts`/`ontology_relationship_bindings` until PUBLISH succeeds.

## 22. Downstream consumption exclusion (binding)

Publishing a new Concept or Relationship does not automatically wire it into Blueprint (CDD-017), H1-H4
(CDD-019/022/023), Gate I (CDD-020), Gate J (CDD-021), Gate K (CDD-026), Gate L (CDD-027), Gate N
(CDD-024), or Gate P (CDD-025). Nothing changes for any downstream consumer of the ontology, because
§9/§19/§20's writes are indistinguishable, by construction, from a seeder-written row. Wiring newly
Published vocabulary into any other gate's own logic requires separate, future governance.

## 23. AI / agent firewall (binding)

No LLM, embeddings, RAG, vector database, agent framework, or MCP capability of any kind. Every action in
§13's lifecycle is deterministic. "Generic agent architecture" (restated from CDD-027 §24) remains
categorically excluded.

## 24. Gate L firewall (binding)

None of Gate L's seven deferred capabilities are absorbed: real model-provider integration; durable
per-human approver provenance on `SemanticMapping` specifically (§17's provenance model concerns only this
CDD's own new artifact); `TrustedPrincipal` subject → Approved `SemanticMapping` durable linkage; OIDC
subject → `EnterpriseEntity` mapping; generic governance actor model; rejection-disposition persistence on
`SemanticMapping` specifically (§15 concerns only this CDD's own new artifact); correlation/reference-
identifier persistence. `semantic_mapping_candidate_discovery.py` and `semantic_mapping_proposal_governance.py`
are neither imported nor modified.

## 25. Gate H/I/J/K/N/P/O/Q firewalls (binding, restated)

This CDD does not modify Gate H1-H4, Gate I's `MAPPED`/`UNMAPPED` determination, Gate J's remediation
semantics, Gate K's prerequisite classification, Gate N's context-availability composition, or Gate P's
Ask CTEC surface. Gate O and Gate Q remain unscoped and are not prerequisites of this CDD (restated from
Gate M0/M1's own M-D3).

## 26. Security invariants (binding, summary)

No cross-tenant risk exists (§10 — no tenant dimension on the canonical target). No unauthorized canonical
mutation (§9/§14/§16). No stale-proposal publication (§16 bullet 3, §18). No replay-created duplicate
canonical rows (§18). No privilege escalation via APPROVE implicitly granting PUBLISH (§14). No direct
API bypass of validation — every check in §19/§20 is re-run server-side at PUBLISH regardless of what was
true at PROPOSE/APPROVE time.

## 27. Deferred future scope (binding)

**Existing Ontology Object Evolution and Historical Version Publication** — explicitly deferred, not
assigned a gate number, requiring separate future architecture/governance before any implementation.
Deferred items include, without limitation: renaming, modifying, replacing, superseding, retiring, or
deleting an existing Concept or Relationship; historical-version publication of any kind; any redesign of
`entity_type_name`/`relationship_type_name`/`institutional_concept_name`'s existing unconditional
uniqueness constraint (e.g., toward a partial/filtered uniqueness scoped to current/`Approved` rows);
current-version selection semantics; relationship survival/remapping across versions. This CDD does not
solve, imply an answer to, or reserve implementation responsibility for any of these — precisely mirroring
CDD-026 §18's own disclaimer pattern for "Gate O."

## 28. Persistence / migration architecture boundary (binding)

Exactly one new table (`OntologyChangeProposal` and its supporting `proposal_kind`/`status` enums), one
new migration, one new repository. `entity_types`, `relationship_types`, `institutional_concepts`,
`ontology_relationship_bindings`, and `resolver.py` are not modified (§9, §21). No column is added to any
existing table. No change to any existing uniqueness constraint (§27).

## 29. API architecture boundary (binding)

This CDD authorizes the architectural need for a propose/review/approve/reject/publish surface without
specifying its exact shape — reserved for Artifact Authorization. No modification to any existing API,
router, or schema file.

## 30. Frontend architecture boundary (binding)

`frontend/app/ontology-studio/_components/ontology-graph.tsx` may be *extended* by a future Artifact
Authorization with an ephemeral, client-side propose affordance for net-new objects only; it is never
retrospectively relabeled as Gate M implementation (restated from Gate M0/M1), and its existing read
behavior is never modified without new authority. A review/approve/reject surface may reuse the Entity
Resolution `decision-dialog.tsx` UX pattern (already established in this same frontend area) — a pattern
reference, not a shared code dependency.

## 31. Explicit non-goals

AI/model providers; agents; MCP; RAG; embeddings; generic agent architecture; downstream Blueprint/H1-H4/
Gate I/J/K/L/N/P rewiring; any Gate L deferred capability; a generic, reusable "change proposal" mechanism
usable by any future gate (`OntologyChangeProposal` is scoped to net-new ontology objects only); a generic
workflow engine; tenant-specific ontology variants; a Palantir-scale visual modeling environment; automatic
publication; frontend direct canonical writes; existing-object modification of any kind (§27).

## 32. Artifact Authorization boundary

Deferred to Artifact Authorization: exact filenames; exact table name; exact migration filename; exact
column SQL types/nullability where not architecture-significant; exact indexes; exact advisory-lock usage;
exact transaction mechanics; exact endpoint paths; exact request/response DTOs; exact publish-scope
literal (§14); exact frontend files/components; exact `rejection_reason` length/shape (§15); exact
idempotency implementation (§18); exact test filenames; exact `AUTHORIZED_CHANGED_PATHS` entries.

## 33. Acceptance criteria (illustrative, non-exhaustive, refined at Artifact Authorization)

1. A proposal for a name that already exists in `entity_types`/`relationship_types` is rejected by
   deterministic validation, never persisted, and never publishable even if it slips past PROPOSE-time
   validation (re-checked again at PUBLISH).
2. APPROVE transitions `Proposed → Approved` only; it never writes to any canonical ontology table.
3. REJECT transitions `Proposed → Rejected` only, records `rejected_by` and (optionally) `rejection_reason`;
   it never writes to any canonical ontology table.
4. PUBLISH performs exactly one transactional write producing either (Concept case) one `InstitutionalConcept`
   + one `EntityType` row, or (Relationship case) one `RelationshipType` + one `OntologyRelationshipBinding`
   row, each `governance_status="Approved"`, `version_number=1`, `previous_version_id=None`,
   `created_by=BOOTSTRAP_SYSTEM_ENTITY_ID`.
5. A second proposal for an already-`Published` name fails closed at PUBLISH even if it was independently
   `Approved` earlier.
6. `resolver.py` and every existing consumer of it pass unmodified, with zero behavior change, both before
   and after this CDD's implementation.
7. No test or code path allows the frontend, or any component other than the single PUBLISH action, to
   write a canonical ontology row.
8. No test or code path allows modification of an existing `EntityType`/`RelationshipType`/
   `InstitutionalConcept`/`OntologyRelationshipBinding` row.
9. `test_domain_foundation.py` and every Gate H/I/J/K/L/N/P production test remain unaffected.

## 34. Frozen-authority compatibility

Fully additive. No existing frozen CDD's acceptance criteria, test, or production code path is affected —
confirmed by §21's construction argument (every write is seeder-shaped) and §6/§27's explicit exclusion of
any existing-row modification.

## 35. Product Owner decisions incorporated

M-D1 (Gate M is real), M-D2 (Governed Visual Ontology Modeling; VISUAL MODELING != CANONICAL MUTATION),
M-D3 (independent of Gate O/Q), M1-D1 (new narrow scopes, no new auth mechanism), M1-D2 (separate
APPROVE/PUBLISH), M1-D3 (Option 1 — new, separate, non-canonical persistence), M1-D4 (downstream
integration deferred), M2-OQ-1 (resolved by existing authority — plain-string provenance permitted),
M2-OQ-2 (durable rejection disposition, Option B), M2-OQ-3 (downgraded to engineering decision — binding
invariants only, H1 precedent available), M2-R2-D1 (NET-NEW ontology creation only; existing-object
evolution explicitly deferred, unnumbered).

## 36. Rollback

Reverting this CDD's eventual implementation removes exactly one table/migration/repository/service set;
`entity_types`/`relationship_types`/`institutional_concepts`/`ontology_relationship_bindings`/`resolver.py`
require no rollback because they are never modified.

## 37. Numbered architecture baseline determination

No new numbered architecture baseline is required, following the identical, repeatedly-proven method
CDD-016/017/024/025/026/027 each used: this CDD introduces no new RFC-tier or PAD-tier document, cites
RFC-010/013/015 and CDD-003 Revision 2 unchanged, and is registered via `architecture/INDEX.md`'s existing
"Governed implementation work orders" table alone — not a new `architecture/released/v1.\d+/` directory,
confirmed structurally exempt from `scripts/verify_architecture_release.py`'s baseline/checksum checks,
identical to CDD-011/012/013/015/016 and every CDD since.

## 38. Authorization

**FROZEN.** Governance-frozen by explicit Product Owner authorization (Gate M2-R3). No implementation
exists, and none is authorized by this document — a separate, subsequent Artifact Authorization companion
remains required before any file is created or modified.
