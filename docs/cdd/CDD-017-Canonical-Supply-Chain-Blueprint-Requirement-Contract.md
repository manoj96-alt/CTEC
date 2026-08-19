# CDD-017 — Canonical Supply Chain Blueprint Requirement Contract

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary, unchanged), RFC-017
(FROZEN, Gate F Supply Chain Semantic Vocabulary Authorization, unchanged), CDD-003 Revision 2
(FROZEN, Complete Canonical Enterprise Ontology, unchanged), CDD-015 (FROZEN, Governed Supply Chain
Impact and Mitigation Decision — formally closed, unchanged)
Mandatory template: CDD Template v2.2

**Publication note**: this Work Order is an architecture authority (CDD Gate: FROZEN), published via
`architecture/INDEX.md`'s "Governed implementation work orders" table — the same non-baseline-tracked
mechanism already used for CDD-011 through CDD-013, CDD-015, and CDD-016 (see §24 for the direct
evidence this CDD does not require a new numbered architecture baseline). No implementation exists
yet — this document does not itself authorize implementation; a separate Product Owner
implementation-planning authorization is required before any code is written against it.

## 1. Objective and business outcome

Establish, as its own governed architecture authority, a **Canonical Supply Chain Blueprint
Requirement Contract**: a declarative statement of which governed ontology concepts, relationships,
and information elements a named supply-chain domain (e.g. "CTEC Semiconductor Supply Chain
Blueprint") is expected to have, independent of any source system's representation. This closes the
gap identified in Gate G's G0 discovery and Product Owner Architecture Decision Review: CTEC's
existing ontology (`entity_types`/`relationship_types`/`institutional_concepts`) can say a concept or
relationship *exists and is available for use*; it has no mechanism to say a concept, relationship, or
information element *should* exist for a given supply-chain domain. This CDD authorizes exactly that
missing requirement layer, and nothing else.

**Explicit distinction (binding, restated throughout).** The existing governed ontology vocabulary
(`entity_types`, `relationship_types`, `institutional_concepts`) remains the sole authority for
concept/relationship *identity and semantics*. This CDD's Blueprint layer never redefines, duplicates,
or overrides that identity — it only references it and declares an obligation level (REQUIRED /
CONDITIONAL / OPTIONAL) against it. A Blueprint requirement that has no corresponding governed
ontology identity to reference cannot be authored under this CDD (§7).

## 2. Governing authorities

Current frozen: RFC-010 (Canonical Enterprise Ontology Boundary — governs concept/relationship
identity, cited unchanged), RFC-017 (Gate F Supply Chain Semantic Vocabulary Authorization — the most
recent addition to the concept/relationship vocabulary this CDD's MVP content references, cited
unchanged), CDD-003 Revision 2 (Complete Canonical Enterprise Ontology, cited unchanged), CDD-015
(Governed Supply Chain Impact and Mitigation Decision — formally closed by Product Owner authorization
at commit `b7524de0c47bc96faaa9c4206c7f84f2033d650f`; cited only as the precedent for the RFC+CDD+seed
governed-extension pattern this CDD's own future implementation will reuse, and as the source of the
"Alternate Supplier"/`assembledAt`/`coveredBy`/`candidateFor` vocabulary this CDD's illustrative MVP
content may reference — not modified). This CDD introduces no new RFC and no new PAD (§24, §14).

## 3. In scope

- A new, minimal domain model: `Blueprint`, `ConceptRequirement`, `RelationshipRequirement`,
  `InformationElementRequirement` (§6) — the exact model corrected and approved by the Gate G Product
  Owner Architecture Decision Review, superseding G0's original proposal (§6 explains the correction).
- `ConceptRequirement`/`RelationshipRequirement` reference existing governed `entity_type_id`/
  `relationship_type_id` identities exclusively (§7). No parallel concept or relationship identity is
  created.
- `InformationElementRequirement` as a genuinely new, deliberately minimal (name + description +
  obligation only, no type system, no validation rule) semantic-content layer, because no existing
  canonical attribute/property identity mechanism exists in CTEC to reference instead (§11 — evidence
  restated from the Architecture Decision Review §8).
- Global, product-owned, non-tenant-scoped Blueprint definitions (§9), with row-level versioning
  reusing the ontology's existing `version_number`/`previous_version_id`/`lifecycle_state`/
  `governance_status` convention (§8, §12) — no separate version/group table.
- A future, separately-implemented deterministic seed populating at least one named canonical
  Blueprint (e.g. covering the concepts/relationships already governed by the base ontology and Gate
  F's RFC-017 extension), authored via a controlled system/database mechanism only — no authoring UI
  (§13).
- A future, separately-implemented backend read *service* (not a public API) sufficient to answer:
  which concepts/relationships/information elements a named Blueprint requires, and which Blueprint
  versions exist (§14).

## 4. Out of scope (binding)

Any new ontology concept or relationship type (this CDD's MVP content is limited to what RFC-010/
RFC-017 already govern — introducing a new concept/relationship requires its own RFC, not this CDD,
§4 of the Product Owner Architecture Decision Review, Decision 1); any authenticated read or write
API (requires its own PAD amendment before implementation, §14); any Blueprint authoring UI, admin
UI, or AI-assisted authoring; any tenant-specific Blueprint configuration, activation, extension,
override, conformance state, or adoption state (Decision 2, binding: Blueprint DEFINITION and future
Blueprint CONFIGURATION are distinct, and only DEFINITION is authorized here); any runtime conformance
engine, tenant conformance scoring, decision-execution gating, Entity Resolution gating, Ask CTEC
gating, or automatic source-system completeness enforcement (§10, binding — Blueprint is declarative
only under this CDD); any modification to Gate F's DRM/GRM, `runtime/orchestration.py`,
`runtime/recovery.py`, Ask CTEC's traversal boundary (PAD-001), or Entity Resolution; any new
authentication or authorization mechanism (§15); any source-system table, field, or mapping reference
of any kind (that is explicitly a future, separately-governed capability's concern, not this CDD's).

## 5. Why Blueprint requires its own governance (not an ontology extension)

The existing ontology extension mechanism (RFC + CDD + `ontology_seed.py`, proven twice: the base
seven-relationship set, then RFC-017's three-relationship Gate F extension) is the correct mechanism
for adding new concept/relationship *identity* — but it has no way to express *obligation*. Adding an
`is_required` flag directly onto `entity_types`/`relationship_types` was evaluated and rejected during
the Product Owner Architecture Decision Review (Architecture Option C there): a single flag on a
shared, globally-referenced ontology row cannot express that two different Blueprints (e.g.
Semiconductor vs. Automotive) might disagree about whether the same relationship is required, and
conflates two distinct authorities (ontology identity governance and Blueprint requirement governance)
on one row. This CDD's additive, referencing-only design (§7) avoids that conflation entirely.

## 6. Domain model authorized (architecture decision)

The following is the exact minimal model approved by the Product Owner (Architecture Decision Review
§4, Decision 1) — it corrects and supersedes G0's original proposal, which had included a separate
`BlueprintVersion` group table. That correction is preserved here, not reopened:

```
Blueprint
  blueprint_id              (PK, stable)
  blueprint_name             (e.g. "CTEC Semiconductor Supply Chain Blueprint")
  lifecycle_state            (reuse existing Draft/Active/Suspended/Archived enum)
  governance_status          (reuse existing Proposed/Approved/Retired/Archived enum)
  version_number              \  reuse the EXACT existing ontology row-versioning
  previous_version_id          > convention (entity_types/relationship_types/
  (self-FK, nullable)          /  institutional_concepts) -- no separate group/
                                   version table (§8)
  created_by / created_on   \  existing BaseEntity convention, identical to
  modified_by / modified_on /  entity_types/institutional_concepts (§12)

  1 ── * ConceptRequirement
         concept_requirement_id   (PK, stable, preserved across a Blueprint's
                                    version chain -- §8)
         blueprint_id             (FK)
         entity_type_id           (FK -> existing entity_types -- §7)
         domain_label              (free-text, NOT governed -- presentation/
                                    organizational only, no own lifecycle)
         obligation                (REQUIRED | CONDITIONAL | OPTIONAL)

         1 ── * RelationshipRequirement
                relationship_requirement_id (PK, stable)
                concept_requirement_id      (FK)
                relationship_type_id        (FK -> existing relationship_types -- §7)
                target_entity_type_id       (FK -> existing entity_types -- §7)
                obligation                  (REQUIRED | CONDITIONAL | OPTIONAL)

         1 ── * InformationElementRequirement
                information_element_requirement_id (PK, stable)
                concept_requirement_id             (FK)
                element_name        (e.g. "Supplier Legal Name" -- §11)
                description
                obligation          (REQUIRED | CONDITIONAL | OPTIONAL)
```

`ConceptRequirement` and `RelationshipRequirement` remain two separate objects, matching the existing
`entity_types`/`relationship_types` precedent of two separate tables rather than one generalized
supertype (Decision 1B) — no generalized "Requirement" abstraction is authorized.
`InformationElementRequirement` attaches to `ConceptRequirement` only (Decision 1C) — no
relationship-level information elements are authorized under this CDD.

## 7. Ontology identity reuse (binding boundary)

`ConceptRequirement.entity_type_id` and `RelationshipRequirement.relationship_type_id`/
`target_entity_type_id` MUST reference existing rows in `entity_types`/`relationship_types` by their
authoritative primary key. This CDD's MVP content is limited to the governed vocabulary already seeded
by `backend/app/infrastructure/persistence/ontology_seed.py` (confirmed by direct inspection, this
Work Order's authoring evidence): the ten concepts (Supplier, Material, BOM, Product, Facility,
Region, Contract, Risk Event, Revenue Exposure, Alternate Supplier) and ten relationships (`supplies`,
`usedIn`, `defines`, `generatesRevenue`, `locatedIn`, `exposedTo`, `boundBy`, `assembledAt`,
`coveredBy`, `candidateFor`). No `ConceptRequirement`/`RelationshipRequirement` row may be authored
against a concept or relationship that does not already exist in `entity_types`/`relationship_types`
at implementation time. If a future Blueprint genuinely needs a concept or relationship this vocabulary
does not cover, implementation MUST STOP and report exactly which is missing — a new RFC is required
before that specific requirement may be authored (§4, restated from the Product Owner Architecture
Decision Review's explicit guardrail).

**Authoring-discipline requirement (binding, carried from the Architecture Decision Review's Critical
Architectural Question finding).** Before authoring an `InformationElementRequirement`, the author
MUST confirm no equivalent governed concept or relationship already exists to express the same fact
(the Decision Review found `Product.revenue_exposure` was not a valid information element, because
"Revenue Exposure" already exists as its own governed concept reachable via the existing
`generatesRevenue` relationship — encoding it as a flat attribute would silently duplicate that
relationship's meaning under an ungoverned name). This check is a named Gate G acceptance criterion
(§20 item 4), not left to author judgment alone.

## 8. Versioning and immutability

`Blueprint` carries its own `version_number`/`previous_version_id` chain, identical in shape and
behavior to the existing ontology tables' convention — no separate `BlueprintVersion` group table is
authorized (§5, §6; the Product Owner Architecture Decision Review's correction to G0, preserved here:
Gate F's `decision_evaluations` group table exists because one API call creates many runtime child
rows needing correlation — Blueprint has no analogous runtime-multiplicity problem, since it is seeded,
not created at request time, §13). `ConceptRequirement`/`RelationshipRequirement`/
`InformationElementRequirement` primary keys (`*_requirement_id`) are minted once and preserved across
a `Blueprint` row's version chain — a requirement's identity does not change merely because its parent
`Blueprint` row is superseded by a new version, so that a future capability referencing a specific
requirement by ID remains valid across Blueprint edits. A published `Blueprint` (`governance_status =
Approved`) is immutable; any change is a new `Blueprint` row with `previous_version_id` set, following
the existing `institutional_concepts`/`entity_types` precedent exactly. This CDD does not further
specify a publication *workflow* (no DRAFT→REVIEW→APPROVED state-machine engine) — publication is a
governance act performed through the same seeded/controlled mechanism as authoring (§13), not a
runtime feature.

**Precision clarifications (binding, closing gaps a future implementer would otherwise have to invent
independently).** (a) `blueprint_id` is a **per-row, per-version** identifier, exactly as
`institutional_concept_id`/`entity_type_id` already are on the tables this convention is copied from —
a new version is a genuinely new row with a new `blueprint_id`, linked backward via
`previous_version_id`. This CDD does not introduce a separate, version-independent "logical Blueprint"
identity; a future consumer needing "the current Approved version of the Semiconductor Blueprint"
resolves it the same way any existing consumer already resolves "the current Approved version of a
concept" — by name lookup plus `governance_status = Approved` filtering, or by walking
`previous_version_id`. (b) A `Blueprint` row in `lifecycle_state = Draft` may be edited in place
(tracked via `modified_by`/`modified_on`); once `governance_status = Approved`, the row is immutable
and any further change is a new row, per the paragraph above. (c) No physical deletion is authorized on
any table in §6 — retirement is expressed only via `governance_status = Retired`/`lifecycle_state =
Archived`, identical to the existing ontology tables' convention; this CDD does not introduce a DELETE
path.

**Honest precedent caveat (binding).** `previous_version_id` exists on `entity_types`/
`relationship_types`/`institutional_concepts` today, but is set to `NULL` at every existing call site
(`ontology_seed.py`, `seed_loader.py`, `krm.py` — verified by direct repository search); no code path in
CTEC has ever actually exercised a non-null version chain. This CDD reuses that convention's *schema
shape* because it is the smallest correct model (§5, §8) — it does not claim the chain-walk behavior
itself is battle-tested, and Gate G's implementation will be the first to exercise it for real.
**Consequence for uniqueness**: `blueprint_name` MUST NOT be given a blanket database-level
`unique=True` constraint copied naively from `institutional_concept_name`/`entity_type_name` — doing so
would make versioning (§8(a), the same name across two rows in a `previous_version_id` chain)
physically impossible the first time it is exercised. Name uniqueness, if required at all, must be
scoped at the application layer to "at most one `governance_status = Approved` row per name," not
enforced as a raw column constraint. This is a concrete implementation-time pitfall this CDD flags so
G2 does not inherit it silently.

## 9. Ownership and tenancy

Canonical `Blueprint` definitions are global and product-owned — no `tenant_id` column is authorized on
`Blueprint`, `ConceptRequirement`, `RelationshipRequirement`, or `InformationElementRequirement`,
matching the existing global scope of `entity_types`/`relationship_types`/`institutional_concepts`
(confirmed by direct model inspection: none of the three carry a `tenant_id` column). Multiple named
Blueprints (e.g. "CTEC Semiconductor Supply Chain Blueprint," "CTEC Automotive Supply Chain Blueprint")
are represented as separate `Blueprint` rows, all global, all product-owned — industry variance is
expressed through row cardinality, never through a tenant dimension (Decision 2, binding). Any future
tenant-specific Blueprint configuration, activation, extension, override, conformance state, or
adoption state is explicitly out of scope for this CDD and requires its own, separately authorized
governance — this CDD does not reserve a column, table, or API shape for it, per the explicit
instruction not to add `tenant_id` merely for future flexibility.

## 10. Declarative vs. executable boundary (binding)

Under this CDD, a Blueprint requirement is a **structural declaration only** — it describes expected
semantic coverage; it does not constitute, trigger, or imply any runtime conformance check. This CDD
explicitly does not authorize: a runtime conformance/validation engine; tenant conformance scoring;
any change that causes a Gate F (or any other) decision to execute or be blocked based on Blueprint
completeness; any change to Entity Resolution behavior triggered by Blueprint's existence; any
requirement that Ask CTEC enforce or reference Blueprint conformance; any automatic source-system
completeness check. Blueprint is expected to become one input to future, separately-governed
capabilities (a Profiling + Gap Engine evaluating actual data against Blueprint requirements; a
Decision Requirements/Readiness capability referencing a subset of Blueprint requirements per decision
type) — this CDD establishes only the declarative target those future capabilities would compare
against; it builds none of the comparison logic itself.

## 11. Information element boundary (binding)

Investigated directly (Product Owner Architecture Decision Review §8, restated here as this CDD's own
evidence): `assertions.predicate` is an ungoverned free-text `String(100)` column with no backing
identity table; `enterprise_entity_resolution_records.evidence_profile` is an instance-level JSON blob
for Entity Resolution matching, not a schema-level attribute mechanism; the ECOM Physical Data Model
(`architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql`) contains no attribute/property table.
**No existing canonical governed attribute/property identity mechanism exists in CTEC.**
`InformationElementRequirement` is therefore authorized as new (Product Owner Architecture Decision
Review Decision 1, Information Element Architecture §8, Option A — introduce now), but held
deliberately minimal: `element_name` (string) + `description` + `obligation` only. No type system
(string/number/date/enum typing), no validation rule, and no live binding to any `assertions.predicate`
value is authorized under this CDD — an `InformationElementRequirement` names a documented target only.
Binding it to real, observed data (i.e., solving "does an actual `assertions.predicate` value satisfy
this requirement") is explicitly deferred to a future, separately-governed capability (plausibly a
Source-to-Blueprint Mapping capability) and MUST NOT be attempted opportunistically under this CDD or
its implementation.

## 12. Governance lifecycle reuse

`lifecycle_state` (Draft, Active, Suspended, Archived) and `governance_status` (Proposed, Approved,
Retired, Archived) are reused verbatim on every new table in §6, identical to their existing use on
`entity_types`/`relationship_types`/`institutional_concepts`. No new lifecycle or governance-status
enum (e.g. no DRAFT/REVIEW/APPROVED/PUBLISHED/SUPERSEDED state machine) is authorized — that would
duplicate governance machinery the repository already has, for no evidenced benefit (Product Owner
Architecture Decision Review Decision 1, unchallenged conclusion, restated as binding here).

## 13. Seeding and authoring

A future, separately-implemented Blueprint content seed MUST follow the existing
`OntologySeeder`/`ontology_seed.py` pattern exactly: deterministic (`uuid5`-derived identifiers under
the existing `BOOTSTRAP_SEED_NAMESPACE` convention), idempotent (re-running creates nothing new),
curated as static metadata in a version-controlled Python module reviewed under ordinary code review —
not authored through any runtime UI, admin tool, or AI-assisted process. No Blueprint authoring API,
UI, or admin surface of any kind is authorized by this CDD, now or as a silent future extension without
its own separate authorization.

## 14. Read surface boundary (binding — no API authorized here)

This CDD authorizes, at most, an internal backend read *service* (a repository/application-service
layer answering the query patterns named in §3, consumed only by backend tests and, later, other
backend capabilities within the same process) — **it does not authorize any HTTP endpoint, any
authenticated API route, or any externally-reachable read surface.** Per the Product Owner's explicit
G1 guardrail: if a future implementation phase determines an externally exposed read API is necessary,
that API requires its own PAD amendment (a new `blueprint:read` scope, following PAD-003's exact
precedent for `supply-chain-impact:read`) authorized separately, before that specific implementation
phase — not silently folded into this CDD's authority. This CDD's own artifact table (§19) authorizes
no `api/blueprint/` package.

## 15. Authorized business artifacts

None authorized. This CDD introduces no new Business Capability Specification or business-authority
artifact — it implements a requirement-declaration layer over already-released BCS capability
semantics and RFC-010/RFC-017's already-released canonical vocabulary (matching CDD-011 §5's and
CDD-015 §31's identical precedent).

## 16. Authorized external contracts

None authorized by this CDD. No API route, request/response schema, or scope-dependency file may be
created under this CDD's authority (§14). A future, separately-authorized CDD/PAD amendment would
authorize any such artifact.

## 17. Authorized persistence artifacts

**Reserved for a future, separately-authorized Gate G implementation phase (G2, §16 of the Product
Owner Architecture Decision Review's recommended phase structure) — not authorized by this governance
document itself.** This CDD authorizes the *architecture* of the persistence model (§6-9); it does not
itself authorize writing the migration, ORM models, or repository. The exhaustive artifact-authorization
table for that implementation phase (mirroring CDD-015 §33's exact format: migration path, model path,
repository path, each with Action/Authority/Purpose/Exclusions/Evidence columns) is intentionally
deferred to that phase's own CDD-Template-v2.2-compliant authorization record, consistent with the
Product Owner's explicit "governance work only, no implementation" boundary for G1. Implementation
MUST NOT proceed against §6's model without that separate, subsequent artifact-authorization record
existing first.

## 18. Authorized configuration artifacts

None authorized. No new environment variable, Keycloak scope, or deployment configuration is
authorized by this CDD (§14 — no API means no new scope is needed yet).

## 19. Authorized implementation and test artifacts

None authorized by this governance document. Per §17, the exhaustive per-file artifact-authorization
table for Gate G's actual persistence/domain/seed/read-service implementation is reserved for that
implementation phase's own separate authorization record — this CDD establishes the architecture (§6-14)
that record must conform to; it does not itself list implementation file paths.

## 20. Acceptance criteria

1. Every `ConceptRequirement.entity_type_id` and `RelationshipRequirement.relationship_type_id`/
   `target_entity_type_id` resolves to a real, existing `entity_types`/`relationship_types` row — zero
   orphaned or invented ontology identity.
2. No `Blueprint`, `ConceptRequirement`, `RelationshipRequirement`, or `InformationElementRequirement`
   table carries a `tenant_id` column.
3. No separate `BlueprintVersion`/group table exists; `Blueprint` carries its own
   `version_number`/`previous_version_id` chain directly.
4. Before any `InformationElementRequirement` is authored, the seed/authoring process demonstrably
   checks for an equivalent existing governed concept/relationship first (§7's authoring-discipline
   requirement) — evidenced by the seed module's own commentary or a dedicated test, not merely
   asserted.
5. `InformationElementRequirement` carries no type system and no live binding/validation against any
   `assertions.predicate` value.
6. No HTTP endpoint, authentication check, or scope enforcement exists anywhere in the implementation
   (§14) — confirmed by an architecture-drift-style test extension.
7. No modification to Gate F's DRM/GRM, `runtime/orchestration.py`, `runtime/recovery.py`, Ask CTEC's
   traversal code, or Entity Resolution code.
8. `*_requirement_id` values are stable and preserved across a `Blueprint` row's version chain (not
   regenerated on each new version).
9. Seed content is deterministic and idempotent (re-running creates nothing new), matching
   `test_demo_gate_f_seeder.py`'s established test pattern.
10. Architecture-drift, dependency, and secret checks pass with zero unauthorized diff.

## 21. Rollback

Backend-only, additive: revert the implementation phase's migration and code; no data migration
downgrade risk beyond the new tables themselves (no existing table is altered). No frontend, Keycloak,
or business-policy rollback is implicated, since none of those are touched by this CDD.

## 22. Architecture drift check

This CDD introduces no new canonical ontology concept, canonical relationship, business rule, RFC
exception, architecture bypass, unapproved technology, Keycloak change, or Gate F/Ask CTEC/Entity
Resolution behavior change. A future implementation must stop if satisfying any part of this CDD
requires such a change — in particular, if the MVP content genuinely needs a concept or relationship
beyond RFC-010/RFC-017's existing vocabulary (§7), or if a read surface beyond an internal service is
found necessary before its own PAD is authorized (§14).

## 23. Non-claims

This CDD does not authorize any new ontology concept or relationship (RFC-010/RFC-017 remain the sole
vocabulary authority); any API, Keycloak, or authentication/authorization change; any Blueprint
authoring UI or admin surface; any tenant-specific Blueprint configuration/activation/extension; any
runtime conformance/validation engine or decision-execution gating; any modification to Gate F, Ask
CTEC, or Entity Resolution; the persistence/domain/seed/read-service implementation itself (§17-19,
reserved for a separate, subsequent implementation-phase authorization); or any of the five other
protected future platform capabilities this CDD's own objective (§1) is the first step toward
(Source-to-Blueprint Semantic Mapping, Profiling + Gap Engine, Gap Impact + Remediation Engine,
Decision Requirements, Decision Readiness) — none are implemented, authorized, or implied by this
document.

## 24. Numbered architecture baseline determination

**No new numbered architecture baseline is required.** Resolved directly from repository precedent,
not assumed, following the identical method CDD-016 §24 used: this CDD introduces no new RFC-tier or
PAD-tier document — it cites RFC-010, RFC-017, CDD-003 Revision 2, and CDD-015 unchanged, and defers
both a possible future RFC (if new ontology vocabulary is ever needed, §4/§7) and a possible future PAD
(if an external read API is ever authorized, §14) to their own, separate, later publications, each of
which would independently determine whether it triggers a baseline bump at that time. CDD-011,
CDD-012, CDD-013, CDD-015, and CDD-016 were all published via `architecture/INDEX.md`'s non-baseline-
tracked "Governed implementation work orders" table alone, with no new `architecture/released/v1.\d+/`
directory created for any of them — confirmed structurally exempt from
`scripts/verify_architecture_release.py`'s baseline/checksum checks (that table carries no
Status/Current/Authority columns and no `released/v1.\d+/` location, identical to every prior CDD entry
there, directly inspected in `architecture/INDEX.md` lines 107-120). This CDD follows that identical,
now six-times-proven pattern.

## 25. Authorization

Authorized by CTEC Product Owner Manoj Nair: this Work Order's publication to FROZEN governance state,
per the Gate G G0 discovery report, the Gate G Product Owner Architecture Decision Review (three
decisions approved), and this G1 governance-authorization phase's drafting and publication review
sequence. No implementation exists yet — a separate, subsequent Product Owner implementation-planning
authorization (§17-19) is required before any persistence, domain, seed, or read-service code is
written against it.
