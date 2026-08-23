# CDD-027 — AI-Assisted Semantic Mapping Candidate Discovery with Human Governance

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — §2-3 "Ontology precedes
cognition... Cognitive services shall not introduce or modify canonical entities," binding on this CDD's
entire scope, §7 below), RFC-013 (FROZEN, Governance Authority and Evaluation Separation — the
constitutional basis for this CDD's human-only approval requirement, §12 below), RFC-015 (FROZEN, Tenant
Ownership Physical Model Authorization — tenant origin exclusively from `TrustedPrincipal`, §17 below),
CDD-017 (FROZEN, unchanged, §4's explicit "AI-assisted authoring" exclusion restated and honored, §8
below), CDD-019 (FROZEN, Gate H H1-H3, unchanged, the sole reused vocabulary and persistence mechanism,
§9-§13 below), CDD-020 (FROZEN, Gate I, unchanged, never directly consumed), CDD-021 (FROZEN, Gate J,
unchanged, the sole upstream trigger signal, §10 below), CDD-022/023 (FROZEN, unchanged, `FieldValueEvidence`
explicitly excluded from this CDD's input boundary, §16 below)
Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via discovery (Gate L0) → independent
Product Owner architecture-decision resolution (Gate L1, resolving Decisions L-D1 through L-D9) →
drafting (Gate L2) → Product Owner governance review (Gate L2.5), which identified two open questions
(candidate-rejection disposition and duplicate-proposal handling) and resolved them as Decisions L2-AC-1
and L2-AC-2, both approved, with the resulting corrected §13 and §15 text integrated into this document
→ Product Owner approval of the fully integrated draft, with P0=0/P1=0/P2=0 confirmed at each review
stage. It is **not yet published on entry into this file**: publication into `architecture/INDEX.md` is
this same Gate L3 turn's own authorized action; merge of the resulting publication PR remains a separate,
subsequent Product Owner authorization, matching every prior CDD's identical multi-step discipline in
this lineage. No implementation exists, and none is authorized by this frozen document — a separate,
subsequent Artifact Authorization companion remains required before any file is created or modified.

## 1. Objective and business outcome

For one tenant's `SourceField` flagged `UNMAPPED` by Gate I and carrying Gate J's
`RemediationAction.REVIEW_SEMANTIC_MAPPING`, non-deterministically generate a candidate correspondence
to an existing, already-governed `InformationElementRequirement`; deterministically validate that
candidate; and, only through an authenticated human decision, materialize it as a governed `Approved`
`SemanticMapping` — explicitly without the AI ever constructing, approving, or publishing governed
state itself.

## 2. Governing authorities

(restated per header; RFC-010/013/015 govern this CDD's constitutional boundaries; CDD-017/019/020/021/022/023
govern the reused vocabulary, persistence, and upstream trigger this CDD consumes, all unchanged)

## 3. Why this CDD requires its own governance

No prior CDD authorizes any non-deterministic candidate-generation capability. CDD-019 authorizes
`SemanticMapping` declaration and Approved-only resolution but not proposal generation. RFC-010's own
"Cognitive services shall not introduce or modify canonical entities" and CDD-017 §4's explicit
"AI-assisted authoring" exclusion both anticipate, without authorizing, exactly this kind of capability —
a new, standalone CDD is the only textually honest instrument, identical reasoning to every prior
standalone CDD in this lineage.

## 4. In scope

AI-assisted candidate generation for `SourceField ↔ InformationElementRequirement` correspondence only
(§5); a deterministic validation boundary (§11); persistence of a `SemanticMapping` row with
`GovernanceStatus.PROPOSED` via the existing, unmodified `create()` method (§12); a human decision
mechanism, `TrustedPrincipal`-authenticated, producing a **new** `Approved` row (§13); minimal
provenance, structurally separate from `SemanticMapping` (§15); a provider-neutral architectural
boundary, interface only (§14).

## 5. Out of scope (binding)

Any new ontology concept, `EntityType`, `RelationshipType`, or `InstitutionalConcept` (§7, RFC-010
constitutional prohibition). Any Blueprint authoring, modification, or new `InformationElementRequirement`/
`ConceptRequirement` (§8, CDD-017 §4). Any modification to Gate H1/H2/H3, Gate I, Gate J, Gate N, Gate P,
Gate K production code or semantics (§9-§10, §18-§21 firewalls). Any direct AI-to-`create()` call
bypassing §11's deterministic validation. Any AI-originated `Approved` row (§12-§13). Any mutation of a
`Proposed` row into `Approved`, or into any other `GovernanceStatus` value including `RETIRED` (§13). Any
raw `FieldValueEvidence`/enterprise-value disclosure to an AI provider (§16). Any SDK selection,
installation, or provider credential configuration (§14). Any Gate O/Q/M capability (§22-§24). Any
generic agent framework (§24). Any persistence of prompts, completions, token counts, temperature,
embeddings, or chain-of-thought (§15). Any new column or schema change on `SemanticMapping` itself (§15).

## 6. Relationship to prior roadmap items (binding)

This CDD does not claim, interpret, or extend any item in CDD-017 §23's five-item roadmap list — "AI-assisted
ontology discovery" is not among them. This is a genuinely new capability, not a prospective interpretation
of an existing reservation.

## 7. RFC-010 constitutional firewall (binding, load-bearing)

RFC-010 §2-3: "Ontology precedes cognition. Cognition consumes ontology. Governance institutionalizes
cognition... Cognitive services shall not introduce or modify canonical entities." This CDD's AI-assisted
candidate-generation capability is a cognitive service in RFC-010's own sense. It MUST NOT, under any
circumstance, introduce or modify `EntityType`, `RelationshipType`, `InstitutionalConcept`, `Enterprise`,
`Enterprise Type`, `Business Domain`, or `Country` — the full RFC-010 §4 canonical-foundation list. This
firewall is absolute and admits no MVP exception.

## 8. CDD-017 Blueprint-authoring firewall (binding, restated)

CDD-017 §4 excludes "any Blueprint authoring UI, admin UI, or AI-assisted authoring" from its own scope.
This CDD honors that exclusion exactly: no `InformationElementRequirement`, `ConceptRequirement`, or
`Blueprint` row of any kind may be created, modified, or proposed by this CDD's capability. The Blueprint
is consumed strictly as an existing, already-governed read target.

## 9. Gate H firewall / reused vocabulary (binding)

`SemanticMapping`, `SourceField`, `LifecycleState`, and `GovernanceStatus` (CDD-019, unmodified) are
reused exactly as CDD-019 §13 already establishes — "no new vocabulary is authorized" — restated and
honored, not merely cited. This CDD introduces no new enum, no new status value, no new domain type
duplicating `SemanticMapping`'s own responsibility. The existing `SemanticMappingRepository` Protocol's
three methods (`create()`, `get_by_id()`, `get_approved_by_information_element_requirement()`) are
consumed exactly as they exist; this CDD does not modify their signatures. Any new repository query (e.g.
a tenant-scoped `SourceField` listing, or a `list_by_governance_status`-style read) is additive only,
authorized in a future, separate Artifact Authorization, never a modification to an existing method.

## 10. Gate J trigger firewall (binding)

`GapImpactContext` and `RemediationAction.REVIEW_SEMANTIC_MAPPING` (Gate J, CDD-021, unmodified) are
consumed strictly as an already-produced, in-memory signal supplied by the caller — this CDD MUST NOT
call, reconstruct, or reinterpret `GapImpactRemediationApplicationService.derive()`'s own logic, and MUST
NOT infer any new meaning for `REVIEW_SEMANTIC_MAPPING` beyond "a candidate-discovery opportunity exists
for this element."

## 11. Deterministic validation contract (binding, exact)

Before any `SemanticMapping` may be persisted with `governance_status=PROPOSED`, the following MUST all
pass, in this order, unconditionally (AI confidence/ranking never substitutes for or shortcuts any of
them):
1. Candidate schema validity.
2. Candidate identifier is a member of the CTEC-supplied candidate universe (§11.1) — never a
   freely-generated identifier.
3. `SourceField` exists and is not currently the source side of an `Approved` `SemanticMapping`.
4. `InformationElementRequirement` exists and is not currently the target side of an `Approved`
   `SemanticMapping` (both 3 and 4 reuse H1's own existing `_raise_if_ambiguous` invariant at the same
   `create()` call site — no duplicated logic is authorized).
5. Tenant ownership of the `SourceField` is confirmed via the existing transitive `SourceObject.tenant_id`
   chain, using `TrustedPrincipal.tenant_id` — never a value the AI supplied.
6. No forbidden cross-tenant reference (defense-in-depth; structurally redundant with 5 given RFC-015's
   own database-level tenant-qualified foreign keys, but checked explicitly).
7. Both referenced objects are in a valid lifecycle/governance state (`Active`/existing `Approved`
   status as applicable) — a mapping MUST NOT target a `Retired` or `Archived` requirement.

### 11.1 Candidate universe (binding)

CTEC deterministically constructs the candidate universe **before** any AI call, scoped to one tenant's
`SourceField`s and the specific `InformationElementRequirement` Gate J's `GapImpactContext` already
identifies. The AI selects or abstains within this universe only; it cannot expand it.

## 12. Proposed materialization (binding)

Exactly one deterministic CTEC application-layer service is authorized to call
`SemanticMappingRepository.create()` with `governance_status=GovernanceStatus.PROPOSED`, and only after
§11's validation passes in full. The model-provider port (§14) MUST NOT import or call the repository,
directly or indirectly — it returns only an in-memory candidate or abstention value. `created_by` on a
`Proposed` row MUST reference a real, governed system-service `Identifier`, never a fabricated "AI"
identity (§15).

## 13. Human decision and approval semantics (binding, exact)

Two architecture-level human actions are authorized: **APPROVE** and **REJECT**.

- **APPROVE**: an authenticated `TrustedPrincipal` action triggers a **new** `create()` call with
  `governance_status=GovernanceStatus.APPROVED`, referencing the same `source_field_id`/
  `information_element_requirement_id` as the `Proposed` row. **The `Proposed` row is never mutated** —
  matching CDD-019 §13's immutability discipline exactly, and directly anticipated by CDD-019 §9's own
  text permitting more than one `SemanticMapping` row to reference the same `SourceField`/
  `InformationElementRequirement` "across time." H1's existing Approved-uniqueness invariant, unmodified
  and unweakened, is the sole mechanism preventing two simultaneous Approved rows for the same target;
  this CDD introduces no new uniqueness logic.
- **REJECT**: does not create any new row and does not mutate the `Proposed` row's own
  `governance_status` or any other field. `GovernanceStatus.RETIRED` is **not** assigned to a rejected
  `Proposed` row — CDD-019 §13 defines `RETIRED` only in the context of correcting a previously-*Approved*
  row, and this CDD does not extend or reinterpret that meaning. A rejection decision is recorded
  exclusively in the external human-decision/provenance record (§15) — never as a change to
  `SemanticMapping` itself, which remains append-only and otherwise untouched by a rejection.

Multiple `Proposed` rows for the same `source_field_id`/`information_element_requirement_id` pair are
permitted at MVP; this CDD authorizes no deterministic deduplication rule preventing a second `Proposed`
row while an earlier one remains unresolved for the same pair. If the eventual human-review surface
requires such a constraint, that is an Artifact-Authorization/UX-phase decision, not a governance-boundary
one, since permitting multiple candidate proposals does not itself cross the AI-authority/human-authority
trust boundary this CDD exists to protect.

Concurrency: no new concurrency primitive is introduced. A race between two approvals targeting the same
requirement is caught by H1's existing, unmodified uniqueness check on whichever `create()` call executes
second — fail-closed, consistent with every existing write path in this repository.

## 14. Provider-neutral model-port boundary (binding, architecture only)

Input: the bounded, deterministically-assembled discovery context (§16). Output: an untrusted candidate
result (identifier from the supplied universe, plus optional non-authoritative ranking/explanation
metadata) or an explicit abstention. The port MUST NOT expose persistence, governance-approval authority,
tenant-authority determination, repository access, or any ability to mutate Gate I/Gate J state. No SDK,
provider selection, or credential configuration is authorized by this CDD — implementation of this port
is reserved for a later, separate Artifact Authorization.

## 15. Provenance contract (binding)

Governed semantic provenance is recorded in a record **structurally separate from `SemanticMapping`**
— never as a new column, field, or schema change on `SemanticMapping` itself, which remains exactly
CDD-019's own existing nine-field shape (`semantic_mapping_id`, `source_field_id`,
`information_element_requirement_id`, `lifecycle_state`, `governance_status`, `created_by`, `created_on`,
`modified_by`, `modified_on`), unmodified by this CDD. That separate record carries: an origin/
`proposal_source` distinction (human-authored vs. AI-assisted), a correlation/reference identifier
linking a `Proposed` row to its generation event, a generation timestamp, the disposition of a review
(approved/rejected, per §13), and — on approval — the human approver's identity. Model
observability/telemetry (prompts, completions, chain-of-thought, token counts, temperature, embeddings,
provider internals) is explicitly **not** governed semantic state and MUST NOT be persisted in this
record or in `SemanticMapping` — if retained at all, it belongs in application logs, a decision reserved
for Artifact Authorization, not this CDD. `created_by`/`modified_by` on any `SemanticMapping` row MUST
NEVER be assigned a fabricated "AI" identity (§12).

## 16. Trusted input boundary (binding)

Permitted AI input: `SourceSystem`/`SourceObject`/`SourceField` identity and structural labels; the
target `InformationElementRequirement`'s governed identity, name, description, and `Obligation`; Gate
J's own bounded `GapImpactContext`/`relationship_context`; existing `Approved` mapping metadata where
needed for conflict-avoidance context. **Forbidden**: `FieldValueEvidence.observed_representation` or
any other raw enterprise business value (CDD-022, unmodified, excluded exactly as every prior gate this
lineage has excluded it). Context assembly is single-tenant per generation call — no cross-tenant
batching.

## 17. Tenant boundary (binding)

Tenant identity originates exclusively from `TrustedPrincipal.tenant_id`, matching RFC-015's own binding
requirement repository-wide, and fails closed when unavailable. AI output MUST NEVER establish, imply,
or override tenant scope.

## 18. Confidence/ranking firewall (binding)

Any AI-returned confidence or ranking is non-authoritative review/ordering metadata only. It MUST NOT
mean, be represented as, or be convertible into: semantic correctness, governance approval, mapping
validity, Gate I's `MAPPED` status, conformance, or business truth. It MUST NOT be persisted as a
`SemanticMapping` field. It MUST NOT be confused with, aggregated with, or presented as equivalent to
Gate C's own `business_confidence` (a distinct, deterministic, policy-derived concept) or Gate K's
`PrerequisiteStatus`.

## 19. Gate I/N/P/K firewalls (binding, restated for emphasis)

Gate I's `MAPPED`/`UNMAPPED` determination is never directly asserted, set, or bypassed by this CDD —
Gate L's only effect on Gate I is indirect, through a new `Approved` row later resolved by the existing,
unmodified H2. Gate N is not consumed. Gate P (Ask CTEC) is not consumed, modified, or extended. Gate K's
`PrerequisiteStatus`/`PrerequisiteReasonCode` are never read or reinterpreted as AI instruction or
decision authority — no legitimate relationship exists between Gate K and this CDD.

## 20. Determinism boundary (binding)

Non-deterministic: AI candidate ranking/selection, AI explanation text, AI confidence. Deterministic:
tenant scope resolution, candidate-universe construction, §11's validation, `Proposed` materialization,
human identity resolution, the approve/reject action, `Approved`-uniqueness enforcement (H1, unmodified),
downstream H2 resolution and Gate I evaluation (both unmodified). No non-deterministic value may ever
appear in, or influence, governed persisted state beyond the bounded fact "an AI-assisted proposal
existed" (§15).

## 21. Failure and abstention semantics (binding)

No credible candidate, provider failure, malformed output, and validation failure all produce the same
outcome: no `Proposed` row is created. No new governed persistence state is introduced merely to record
a technical failure.

## 22. Gate O firewall (binding)

This CDD does not implement Context-as-a-Service. The model-provider port (§14) is an internal
application-layer interface only, never a public/external service contract.

## 23. Gate Q firewall (binding)

This CDD does not implement MCP, an MCP client or server, or a connector framework. The model-provider
port is a direct, narrow interface, never a protocol framework, regardless of any future Gate Q plan.

## 24. Gate M firewall (binding)

This CDD does not implement visual ontology modeling and does not introduce a generic agent architecture.
Any future minimal review UI (deferred, not authorized here) would be a narrow approve/reject surface
only, categorically distinct from a modeling environment.

## 25. Persistence / migration boundary (binding)

Limited to what §12/§15 require: no new domain type beyond what already exists (`SemanticMapping`); any
new column (e.g. `proposal_source`, correlation id) or new query method belongs to the structurally
separate provenance record (§15) or is an additive-only new query, both reserved for Artifact
Authorization to specify exactly. No modification to any existing table, column, or migration. No new
column of any kind on `SemanticMapping` itself.

## 26. API / frontend / auth boundary (binding)

Any new API surface for the human decision action, and any new minimal review UI, is reserved for
Artifact Authorization — this CDD authorizes the *architectural need* for a human-decision surface (§13)
without specifying its exact shape. No modification to any existing API, router, schema, or frontend
file. No new authentication mechanism — `TrustedPrincipal`/Gate E's existing runtime is reused unchanged.

## 27. Acceptance criteria (illustrative, non-exhaustive, refined at Artifact Authorization)

1. An AI-assisted candidate generated for a `SourceField` not in the CTEC-supplied universe is rejected
   by deterministic validation, never persisted.
2. A `Proposed` `SemanticMapping` is created only after all §11 checks pass.
3. Approval creates a new `Approved` row; the originating `Proposed` row's own fields are unchanged
   afterward.
4. Rejection creates no new row and leaves the `Proposed` row's `governance_status` unchanged.
5. Two simultaneous approval attempts for the same target: exactly one succeeds, the other fails via
   H1's existing uniqueness check.
6. No test or code path allows the model-provider port to call `SemanticMappingRepository.create()`
   directly.
7. No `FieldValueEvidence` value appears in any AI input context.
8. No confidence/ranking value is persisted on any `SemanticMapping` row.
9. No new column exists on `SemanticMapping` after implementation.
10. `test_domain_foundation.py` and Gate I/H1/H2/J production tests remain unaffected.

## 28. Non-claims

This CDD does not authorize: any new ontology concept or relationship (§7); any Blueprint authoring
(§8); any AI-originated Approved state (§12-§13); any mutation of a Proposed row, including into
`RETIRED` (§13); any SDK/provider selection or credential configuration (§14); any persistence of raw
enterprise values (§16) or provider telemetry (§15); any schema change on `SemanticMapping` itself
(§15); any deterministic proposal-deduplication rule (§13); any Gate O/Q/M capability (§22-§24); the
implementation itself (deferred to a separate, subsequent Artifact Authorization).

## 29. Rollback

Backend-only, additive — no schema/migration beyond what a future Artifact Authorization narrowly
specifies; no modification to any existing production file.

## 30. Compatibility

No breaking change to any existing capability — introduces a new, independent candidate-discovery and
human-decision capability consuming Gate J's already-frozen output and producing `SemanticMapping` rows
exclusively through H1's already-frozen, unmodified `create()` method.

## 31. Observability and performance

Not applicable at this architecture-governance stage; deferred to implementation, with the explicit
constraint that any observability/telemetry captured must remain outside governed semantic state (§15).

## 32. Numbered architecture baseline determination

No new numbered architecture baseline required — follows the identical non-baseline-tracked
`architecture/INDEX.md` publication pattern used by CDD-011 through CDD-026.

## 33. Authorization

**GOVERNANCE FROZEN.** This document reached FROZEN state via Gate L0 discovery → Gate L1 Product Owner
architecture-decision resolution (Decisions L-D1 through L-D9, all approved) → Gate L2 drafting → Gate
L2.5 Product Owner governance review, which identified two open questions and resolved them as Decisions
L2-AC-1 and L2-AC-2 (both approved), with the resulting corrected §13 and §15 integrated → Product Owner
approval of the fully integrated document, with P0=0/P1=0/P2=0 confirmed at each review stage.
Publication into `architecture/INDEX.md` is this same Gate L3 turn's own authorized action. No
implementation exists, and none is authorized by this frozen document — a separate, subsequent Artifact
Authorization companion remains required before any file is created or modified. Gate H, Gate I, Gate J,
Gate N, Gate P, Gate K, RFC-010, RFC-013, RFC-015, RFC-017, and CDD-017 remain entirely outside this
document's authority and remain unchanged.
