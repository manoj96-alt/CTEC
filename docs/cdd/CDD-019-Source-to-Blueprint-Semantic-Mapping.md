# CDD-019 — Source-to-Blueprint Semantic Mapping (H1-H3)

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-015 (FROZEN, tenant ownership physical model — `source_systems`/
`source_objects` are two of the tables RFC-015 tenant-scoped, unchanged), CDD-017 (FROZEN, Canonical
Supply Chain Blueprint Requirement Contract, unchanged), CDD-017 G2/G3/G3.5 artifact-authorization
companions (FROZEN, unchanged), CDD-018 (FROZEN, Blueprint Conformance Evaluation, unchanged)
Mandatory template: CDD Template v2.2

**Publication note**: this Work Order is an architecture authority (CDD Gate: FROZEN), published via
`architecture/INDEX.md`'s "Governed implementation work orders" table, following the identical
non-baseline-tracked mechanism already used for CDD-011 through CDD-018 (see §31 for the direct
evidence this CDD does not require a new numbered architecture baseline). No implementation exists
yet — this document does not itself authorize implementation; separate, subsequent artifact-
authorization companions (mirroring CDD-017's G2/G3/G3.5 and CDD-018's G4 companion precedent) are
required before any code is written against it, one per phase (§25).

## 1. Objective and business outcome

Establish, as its own governed architecture authority, **Source-to-Blueprint Semantic Mapping**: the
capability to declare and deterministically resolve a governed correspondence between a physical
source-system field and a canonical Supply Chain Blueprint `InformationElementRequirement` (CDD-017).
This is the capability CDD-018 §6 and §23 name, by that exact title, as "a separate, later,
separately-governed effort" outside CDD-018's own authority — "Gate H." This CDD authorizes exactly the
declaration and resolution of that correspondence (H1-H3, §3); it does not authorize consuming that
correspondence to evaluate `InformationElementRequirement` conformance (H4, §6, §20 — reserved,
unauthorized, contingent on a still-unanswered question this CDD does not attempt to answer).

## 2. Governing authorities

Current frozen: RFC-015 (tenant ownership physical model, cited unchanged — the authority under which
`source_systems`/`source_objects` already carry their `tenant_id` column, per migration
`0011_entity_resolution_tenant_and_evidence.py`'s and `0012_institutional_relationship_tenant_ownership.py`'s
own citation of RFC-015 for this exact tenant-scoping pattern), CDD-017 (Canonical Supply Chain
Blueprint Requirement Contract, cited unchanged as the source of `InformationElementRequirement`, this
CDD's mapping target — **this CDD does not amend, extend, or reinterpret CDD-017; CDD-017 remains
FROZEN and unchanged**), CDD-017's G2/G3/G3.5 artifact-authorization companions (cited unchanged as the
source of the already-merged Blueprint persistence and application-service capabilities this CDD
references by ID only), CDD-018 (Blueprint Conformance Evaluation, cited unchanged — this CDD's H4
firewall, §6, is the direct continuation of CDD-018 §6's own "G4 / Gate H boundary," restated from the
opposite side). CDD-018's G4 artifact-authorization companion is not cited as a governing authority
here: this CDD depends on CDD-018's architecture (§6, §10, §22's boundary language), not on any
artifact the G4 companion specifically authorized (`BlueprintConformanceContextStore`,
`BlueprintConformanceApplicationService` internals) — this CDD neither consumes nor references either
(§4, §20). This CDD introduces no new RFC and no new PAD (§29).

**Explicit relationship to CDD-018 (binding, restated throughout)**: CDD-018 §6 states plainly that
determining "which SAP/Oracle/source-system field supplies this Blueprint requirement... belongs
exclusively to Gate H — Source-to-Blueprint Semantic Mapping, a separate, later, separately-governed
effort," and that CDD-018 "introduces no mapping table, no mapping rule, no field-name inspection logic
of any kind." This CDD is that separate, later governance — a new, standalone document citing CDD-018
unchanged, not a CDD-018 companion, for the identical reason CDD-018 itself was not drafted as a
CDD-017 companion (CDD-018 §5): a companion can only authorize implementation detail of architecture
its cited CDD already defines, and neither CDD-017 nor CDD-018 defines any source-mapping architecture.

## 3. In scope

- A new, minimal source-field identity capability: `SourceField`, identifying a physical field within
  an already-governed `SourceObject`, at the smallest granularity CDD-017/018's existing source-side
  architecture (`SourceSystem`/`SourceObject`) does not already reach (§7).
- A new, minimal mapping-declaration capability: `SemanticMapping`, recording a deterministic 1:1
  correspondence between one `SourceField` and one `InformationElementRequirement` (§8-§11), governed
  by the same `LifecycleState`/`GovernanceStatus` machinery every other governed object in this
  repository already uses.
- An internal, deterministic, Approved-only mapping-resolution application service (H2, §14) answering
  exactly one question: for a given tenant and `InformationElementRequirement`, what `SourceField` (if
  any) does the governed, Approved mapping resolve to.
- Deterministic seed/demonstration evidence (H3, §15) proving the H1/H2 architecture against the
  existing canonical Blueprint's real `InformationElementRequirement`s, covering successful resolution,
  missing-mapping, tenant isolation, and ambiguity-prevention behavior.

## 4. Out of scope (binding)

Any many-to-one mapping, one-to-many mapping, transformation, derivation, calculation, unit conversion,
conditional mapping, or expression-engine logic of any kind (§9, §12 — Product Owner Decision 1, Option
A, binding without exception); any `InformationElementDefinition` or other intermediate canonical-
semantic-identity object between `SourceField` and `InformationElementRequirement` (§10 — Product Owner
Decision 2, direct mapping only); any modification to `Blueprint`, `ConceptRequirement`,
`InformationElementRequirement`, the Blueprint domain model, the Blueprint ORM, any Blueprint migration,
`BlueprintRepository`, or `BlueprintApplicationService` (§19 — this CDD consumes
`information_element_requirement_id` exactly as merged, unmodified); any modification to
`BlueprintConformanceApplicationService` or any other CDD-018 artifact (§6, §19); any change to
`InformationElementRequirement` evaluation status — it remains `NOT_EVALUATED`, exactly as CDD-018 §10
establishes, for the full duration of this CDD's authority (§6); any live source-system connectivity,
source-field value reading, or evidence-of-presence evaluation of any kind (§6, §20 — reserved for a
future H4 authorization contingent on a question this CDD does not answer); any minting of a second
Blueprint version, or any Blueprint version re-parenting/versioning mechanism implementation (§19 — an
inherited dependency this CDD records but does not own or implement); any modification to
`SourceSystem`, `SourceObject`, or their governing RFC-015 physical model (§7 — referenced by ID only);
any new ontology concept or relationship (RFC-010/RFC-017 remain the sole vocabulary authority; §17); any
external HTTP endpoint, API schema, or FastAPI router (§21); any frontend or UI of any kind (§21); any
new authentication or authorization scope (§21); any modification to Entity Resolution, Governance
Engine, Knowledge Engine, Decision Engine, Ask CTEC's traversal code, Gate F's DRM/GRM,
`runtime/orchestration.py`, or `runtime/recovery.py` (§18); any modification to the `assertions` table,
`Assertion.predicate`, or `SourceObservation` (CDD-011/RFC-014/CIM-001's own artifacts — referenced only
as prior-art evidence in this CDD's discovery record, never consumed, extended, or modified, §17).

## 5. Why Source-to-Blueprint Semantic Mapping requires its own governance (not a CDD-017/018 companion)

A CDD-017 companion (the mechanism already used for G2, G3, and G3.5) or a CDD-018 companion (the
mechanism already used for G4) is only capable of authorizing implementation-level artifact detail for
architecture its cited CDD has *already* defined in its own body. Neither CDD-017 nor CDD-018 defines
any source-field identity, mapping-declaration, or mapping-resolution architecture — CDD-018 §6
explicitly disclaims it by name ("Gate H... a separate, later, separately-governed effort"). A new,
standalone CDD, citing both CDD-017 and CDD-018 unchanged, is therefore the only textually honest
instrument, matching the Product Owner's Gate H Governance Discovery & Authorization Planning
conclusion (§7 of that planning document: "CDD — required... a new capability bridging source-system
field identity to Blueprint information elements").

## 6. H4 boundary (binding)

**This CDD (H1-H3) answers**: "Given a tenant and a Blueprint `InformationElementRequirement`, does a
governed, Approved mapping exist to a specific physical `SourceField`, and if so, which one?" This is
answerable using only already-governed identity (`information_element_requirement_id`,
`source_field_id`) and requires no source-system connectivity, no source-value reading, and no
completeness/conformance judgment of any kind.

**This CDD does NOT answer**: "Does the tenant's actual source data satisfy this Blueprint information
element?" That question requires reading a live source-field *value* and judging its presence/adequacy
against `InformationElementRequirement`'s obligation — a capability this CDD's Gate H Governance
Discovery record (§10 of that report) identified as depending on a currently unanswered architectural
question: **how does CTEC obtain authoritative live source-field values/evidence for information-element
conformance evaluation?** This CDD does not answer or design around that question. That capability is
named **H4 — Blueprint Information-Element Conformance Integration**, and is explicitly NOT AUTHORIZED
by this CDD (§4, §20, §25). `InformationElementRequirement` evaluation remains `NOT_EVALUATED`
(CDD-018 §10, unchanged) for the full duration of this CDD's authority. H4 requires its own, separate,
future governance/authorization cycle, contingent on that question being resolved first.

## 7. Architectural model and physical source identity

```
Tenant
  │ (owns, via composite tenant-qualified FK, RFC-015 pattern)
  ▼
SourceSystem  (existing, CDD-003/RFC-015 — unmodified)
  │ (contains)
  ▼
SourceObject  (existing, CDD-003/RFC-015 — unmodified)
  │ (contains)
  ▼
SourceField  [NEW — this CDD]
  │ (referenced by)
  ▼
SemanticMapping  [NEW — this CDD]
  │ (targets)
  ▼
InformationElementRequirement  (existing, CDD-017 — unmodified)
```

`SourceField` identity is the minimum necessary to reach field granularity, which neither
`SourceSystem` nor `SourceObject` reaches: `source_field_id` (primary key), `source_object_id`
(FK, establishing both provenance and, transitively, tenant scope — `tenant_id` is NOT duplicated
directly on `SourceField`; it is always resolved through the `source_object_id` join, exactly as
`BlueprintConformanceContextStore` resolves tenant scope through a join rather than a duplicated
column), `field_label` (the field's identity within its object), `lifecycle_state`/`governance_status`
(§13), and standard audit metadata (`created_by`/`created_on`/`modified_by`/`modified_on`). No source
schema/version field is authorized on `SourceField` — that context is already carried by
`SourceObject`'s own `version_number`/`previous_version_id` and is inherited transitively, not
duplicated (Gate H Governance Discovery §2).

## 8. SemanticMapping identity and deterministic correspondence

`SemanticMapping` identity: `semantic_mapping_id` (primary key), `source_field_id` (FK, the source
side), `information_element_requirement_id` (FK, the target side — direct, per §10), `lifecycle_state`/
`governance_status` (§13), and standard audit metadata. `tenant_id` is NOT a direct column on
`SemanticMapping`; tenant scope is inherited transitively through `source_field_id → source_object_id → tenant_id`, for the identical single-source-of-truth reason `SourceField` does not duplicate it either (§7). Exactly one `SemanticMapping` row expresses exactly one correspondence — `SourceField`
X corresponds to `InformationElementRequirement` Y — and nothing else. `SemanticMapping` carries no
computation, expression, transformation, or condition field of any kind (§4, §12).

## 9. Cardinality (binding)

Gate H MVP supports exactly: **one `SourceField` maps to one `InformationElementRequirement`, in both
directions** — one `SourceField` resolves to at most one Approved `InformationElementRequirement`, and
one `InformationElementRequirement` resolves to at most one Approved `SourceField` per tenant, both
enforced by §11's two symmetric uniqueness rules. No many-to-one, one-to-many, or multi-candidate
resolution model is authorized. A `SourceField` or an `InformationElementRequirement` MAY each be
referenced by more than one `SemanticMapping` row across time (e.g. a superseded mapping, Retired, and
a replacement, Approved) — but at most one such row touching either side may be `Approved` at a time
(§11). This is Product Owner Decision 1, Option A, applied without exception.

## 10. Mapping target (binding)

The governed mapping target is `InformationElementRequirement.information_element_requirement_id`
directly. This CDD does not introduce, reference, or depend on any `InformationElementDefinition` or
other intermediate canonical-semantic-identity object (Product Owner Decision 2). This is safe because
CDD-017 §8 already binds `*_requirement_id` values (including `information_element_requirement_id`) to
be "minted once and preserved across a `Blueprint` row's version chain... so that a future capability
referencing a specific requirement by ID remains valid across Blueprint edits" — language that already
anticipates exactly this CDD's use case. This CDD inherits, but does not own or implement, the
dependency that follows from that guarantee (§19).

## 11. Uniqueness and ambiguity (binding)

Gate H MVP's deterministic 1:1 correspondence (§9) is enforced by **two symmetric, binding uniqueness
rules**, both scoped by governed ID, never by name:

- **Target-side**: at most one `Approved` `SemanticMapping` row may exist per
  `(information_element_requirement_id, tenant)` pair — where `tenant` is the tenant transitively
  resolved through the row's `source_field_id → source_object_id → tenant_id` chain (§7-§8), not a
  stored column.
- **Source-side**: at most one `Approved` `SemanticMapping` row may exist per `source_field_id`. A
  `SourceField` belongs to exactly one tenant, inherited transitively from exactly one `SourceObject`
  (§7); no `SourceField` row is ever shared across tenants. Uniqueness scoped by `source_field_id`
  alone is therefore already single-tenant by construction — this is not an invented global rule, it
  follows directly from `SourceField`'s existing single-tenant-ownership model (§7, §18).

Both rules apply only to rows in `governance_status = Approved`; `Draft`, `Retired`, and `Archived`
rows are never counted as competing mappings under either rule, regardless of which identities they
reference (§13's Approved-only eligibility applies identically here). Both rules are enforced at the
application/repository layer with an explicit raised exception on ambiguity (mirroring
`BlueprintRepository.get_approved_by_name`'s exact precedent: `None` on zero matches, the single match
on exactly one, an explicit raise — never a silent first-match, last-write-wins, priority-ordering, or
confidence-scored resolution — on more than one, for either rule). A bare database-level unique
constraint is not sufficient by itself for the target-side rule, since tenant scope there is inherited
via a join rather than a direct column (§8); the source-side rule, by contrast, MAY additionally be
enforced by a direct database-level unique constraint on `source_field_id` (scoped to
`governance_status = 'Approved'`), since `source_field_id` is a direct column — but implementation MUST
still verify both rules explicitly at the application layer regardless of any database-level guard, for
identical, consistent failure semantics (§23) across both directions.

Together, these two rules guarantee no `SourceField` resolves ambiguously to more than one
`InformationElementRequirement`, and no `InformationElementRequirement` resolves ambiguously to more
than one `SourceField` within a tenant. This rule exists specifically to prevent the scenario Gate H
Governance Discovery §4 and §9 of the Governance Discovery report identified — extended, per the
Product Owner Governance Review's F1 finding, to cover both directions of the correspondence, not only
the target-side direction the original draft enforced — so that H2 resolution (§14) remains
deterministic in both query directions without priority ordering, winner selection, arbitrary
first-match behavior, confidence scoring, or name matching.

## 12. Transformation boundary (binding)

`SemanticMapping` records semantic correspondence only. It never computes, derives, converts, or
conditionally selects a value. No field, column, or configuration on `SourceField` or `SemanticMapping`
may express or enable a transformation, unit-conversion, calculation, or expression of any kind, in any
form, including a "narrow" or single-purpose one (§4 — matches CDD-018 §20's identical "total,
non-narrow" exclusion precedent for source-mapping).

## 13. Lifecycle, governance, and versioning

`SourceField` and `SemanticMapping` both reuse the existing `LifecycleState`
(`Draft`/`Active`/`Suspended`/`Archived`) and `GovernanceStatus`
(`Proposed`/`Approved`/`Retired`/`Archived`) enums unchanged — no new vocabulary is authorized. Only
`Approved` rows are eligible for resolution (H2, §14), mirroring `get_approved_by_name`'s exact
precedent. An `Approved` row is immutable; any correction is expressed as Retiring the incorrect row
(`governance_status = Retired`) and Approving a replacement — never an in-place mutation of an Approved
row's identity or target. Neither `SourceField` nor `SemanticMapping` is authorized to carry
`version_number`/`previous_version_id` in this CDD's scope: Gate H Governance Discovery §5 found this
convention, while present on `Blueprint`/`SourceSystem`/`SourceObject`/`InstitutionalConcept`, is
`NULL`/unexercised at every single call site in this entire repository, for every table that has it —
copying an unproven, never-exercised mechanism onto two more tables is not authorized without
demonstrated need. If a future phase demonstrates a concrete need for field-level or mapping-level
version chains, that is its own, separate governance question, not decided here.

## 14. H2 — Internal Mapping Resolution Service boundary

An internal application-layer service, matching `BlueprintApplicationService`'s (G3) and
`BlueprintConformanceApplicationService`'s (G4) established constructor-injection, no-persistence-of-
its-own pattern, answering exactly: for a given tenant and `information_element_requirement_id`, what is
the Approved `SourceField` (if any) the governed mapping resolves to? Behavior, binding:

- **Approved-only resolution**: only `governance_status = Approved` `SemanticMapping` rows are eligible
  (§13).
- **Tenant isolation**: every resolution is scoped to exactly one tenant; no resolution may span or
  aggregate more than one tenant's mappings in a single call (mirroring CDD-018 §18's binding tenant-
  isolation constraint exactly).
- **Deterministic selection**: exactly zero or one result is possible per call, by construction of
  §11's uniqueness rule — this service performs no ranking, scoring, or priority selection among
  candidates, because no scenario producing multiple simultaneous candidates is authorized to exist.
- **Ambiguity handling**: if the underlying data somehow violates §11 (a defect, not an expected
  runtime state), the service MUST raise explicitly rather than silently pick one — identical to
  `get_approved_by_name`'s binding precedent.
- **Missing-mapping behavior**: if no Approved mapping exists, the service returns `None` — matching
  `BlueprintApplicationService.get_by_id`'s and `BlueprintRepository.get_approved_by_name`'s identical
  `X | None` "not found" idiom, not a new or open-ended return contract — this is a valid,
  successfully-produced outcome, not a failure
  (mirroring CDD-018 §22's non-conformance-is-not-failure distinction, applied here to
  mapping-does-not-exist versus resolution-failed).
  - **Provenance returned**: a successful resolution's result includes enough information to identify
    the resolved `SourceField` (`source_field_id`, `source_object_id`, `source_system_id` via join) and
    the `SemanticMapping` row's own identity/audit metadata — sufficient for a future H4 (once
    separately authorized) to know exactly which physical field and mapping record produced a
    resolution, without this service performing any evaluation itself.
- **Version-selection behavior**: not applicable in this CDD's scope — only one Blueprint version
  exists (§19), so no version-selection logic beyond §11's tenant/element uniqueness rule is
  authorized or required.

No public HTTP API, no authentication/authorization change, and no `BlueprintConformanceApplicationService`
integration of any kind is authorized for this service (§4, §21).

## 15. H3 — Deterministic Mapping Demonstration boundary

Deterministic seed/demonstration evidence, following the existing deterministic-seeder precedent
(`BlueprintSeeder`'s `uuid5`-under-`BOOTSTRAP_SEED_NAMESPACE` determinism and idempotency pattern,
adapted for test/demonstration fixtures rather than production canonical content — Gate H has no
canonical global content analogous to the Blueprint itself, since mappings are inherently
tenant/source-specific data, not global governed vocabulary). Must use the existing, real, already-
governed Blueprint `InformationElementRequirement`s (e.g. "Supplier Legal Name") — no fabricated or
placeholder Blueprint content. Must prove, at minimum: successful resolution (an Approved mapping
resolves correctly); missing-mapping behavior (no Approved mapping exists for a given tenant/element,
resolution returns the explicit "no mapping" outcome); tenant isolation (two tenants' mappings do not
leak into each other's resolution, proven against real PostgreSQL, mirroring
`test_context_store_tenant_isolation`'s exact established pattern); ambiguity prevention (attempting a
second simultaneous Approved mapping for the same tenant/element is rejected, per §11). H3 MUST NOT
create, connect to, or simulate any production connector, live source-system integration, or scheduled
ingestion behavior of any kind — it is fixture/test evidence only, exactly as G3.5's canonical seed was
production content while G2's Postgres tests were fixture-only, and H3 sits entirely in the latter
category.

## 16. Application/service boundary

`SourceField`/`SemanticMapping` persistence and repositories (H1) are the sole source of truth; the H2
resolution service performs no persistence of its own, matching every existing application-service
precedent in this repository (`BlueprintApplicationService`, `BlueprintConformanceApplicationService`).

## 17. Ownership boundary versus existing capabilities

Verified directly against every plausible existing capability, per the Gate H Decision 2 Resolution
Review's exhaustive check:

- **`assertions`/`Assertion.predicate`** (CDD-003/006, ASM-001): a different, already-FROZEN capability
  (institutional/evidence-backed facts about entities). This CDD does not read, write, extend, or
  depend on `assertions` in any way — `SourceField` identity is independently governed, never derived
  from or correlated to `Assertion.predicate`'s free-text values.
- **`SourceObservation`** (RFC-014/CIM-001, CDD-011): an ephemeral, non-persisted integration DTO
  scoped exclusively to the Supplier-Risk pipeline, explicitly carrying "no new canonical entity or
  business vocabulary" per its own artifact-authorization table. This CDD does not consume, extend, or
  depend on `SourceObservation`.
- **`InstitutionalConcept`** (base ontology, used by Ask CTEC's assertion-object vocabulary): wrong
  scope (`enterprise_id`, not tenant/global) and wrong shape (no `description` field) for this CDD's
  purposes; not referenced by any artifact this CDD authorizes.
- **`SemanticResolutionRecord`** (SRM-001, Entity Resolution): a probabilistic, confidence-scored
  candidate-interpretation engine resolving to `InstitutionalConcept`, not a deterministic 1:1
  declarative correspondence to `InformationElementRequirement`. Different target, different
  resolution philosophy, different capability owner. Not referenced by any artifact this CDD
  authorizes.
- **Entity Resolution, Governance Engine, Knowledge Engine, Decision Engine, Ask CTEC's traversal
  code**: no overlap identified; this CDD does not modify or invoke any of them.

No ownership overlap identified with any existing capability.

## 18. Security and tenancy boundaries

No new authentication or authorization mechanism, scope, or Keycloak configuration is authorized (no
external surface exists to protect, §21). `SourceField`/`SemanticMapping` inherit tenant scope
transitively (§7, §8) rather than duplicating it — every resolution query MUST join through
`SourceObject`'s tenant-qualified structure. Isolation here is achieved by construction, not by
replicating migration `0012`'s composite-FK mechanism literally: `SourceField`/`SemanticMapping`
deliberately carry no direct `tenant_id` column (§7, §8), so there is no second, independently-stored
tenant marker that could ever disagree with `SourceObject`'s own — the isolation property migration
`0012`'s composite FK exists to guarantee (no cross-tenant reference) holds here without needing that
same mechanism, because the thing it protects against (a duplicated, potentially-inconsistent tenant
column) was never introduced in the first place. No resolution result or its provenance (§14) may
reference or reveal a `SourceField`, `SourceObject`, or mapping belonging to any tenant other than the
one being resolved.

## 19. Blueprint dependency (binding)

This CDD references `InformationElementRequirement.information_element_requirement_id` by ID only and
modifies no Blueprint artifact of any kind (§4). It inherits, but does not own or implement, the
following dependency, restated here as binding and explicit:

**No second Blueprint version may be minted until the existing Blueprint versioning/re-parenting
mechanism (CDD-017 §8's stated intent; G2's recorded "Remaining risks" P1) is explicitly resolved and
implemented sufficiently to guarantee unchanged `*_requirement_id` values are actually preserved across
versions.** Only Blueprint `version_number = 1` currently exists, and no code path anywhere in this
repository mints a second version (verified by repository-wide search, Gate H Decision 2 Resolution
Review §1). For as long as that remains true, every `SemanticMapping` this CDD authorizes targets a
stable, unambiguous `information_element_requirement_id`. Should a second Blueprint version ever be
minted without first resolving that mechanism, every `SemanticMapping` referencing an affected
`information_element_requirement_id` would be at risk of silent staleness — this CDD does not solve
that risk; the future work that mints a second Blueprint version inherits the obligation to resolve it,
exactly as G2 already recorded.

## 20. H4 exclusion (binding)

No evaluation of `InformationElementRequirement` conformance, no live source-field value reading, no
completeness/presence judgment, and no modification to `BlueprintConformanceApplicationService` of any
kind is authorized by this CDD, in any artifact, in any form (§4, §6). `InformationElementRequirement`
evaluation remains exactly `NOT_EVALUATED` for every element, regardless of obligation, unchanged from
CDD-018 §10, for the full duration of this CDD's authority. This exclusion is total and does not admit a
narrow or hardcoded exception.

## 21. API and frontend exclusions

No external HTTP endpoint, FastAPI router, or API schema is authorized (§4). No frontend, UI, or
authoring surface of any kind is authorized (§4). This matches the default every Gate G phase and
CDD-018 have held: internal-only capability, with any future external exposure requiring its own,
separately authorized PAD amendment.

## 22. Determinism and idempotency

Resolving the same tenant/`information_element_requirement_id` pair against unchanged `SemanticMapping`
state MUST yield an identical result on repeated resolution — guaranteed directly by §11's uniqueness
invariant and the H2 service's read-only nature (no additional mechanism required). Seed/demonstration
data (H3, §15) MUST be idempotent, following `BlueprintSeeder`'s exact precedent (deterministic
`uuid5`-derived identity, re-running the loader against already-seeded fixtures creates nothing new).

## 23. Failure semantics

If a `SemanticMapping` resolution query somehow finds more than one simultaneously `Approved` row for
the same `(information_element_requirement_id, tenant)` pair (a defect, since §11 is binding),
resolution MUST fail explicitly (raise) rather than silently selecting one — consistent with CDD-017
§7's and CDD-018 §22's identical binding instructions elsewhere in this governance family.
**Missing-mapping is not resolution failure (binding, must not be collapsed)**: "no Approved mapping
exists" is a valid, successfully-produced outcome (§14), categorically different from "the resolution
query itself could not be answered" (ambiguity, or a tenant/element reference that does not resolve at
all). Implementation MUST represent these as different mechanisms — an explicit "no mapping" result
value for the former, a raised exception for the latter — never collapsed into one.

## 24. Authorized business artifacts

None authorized. This CDD introduces no new Business Capability Specification or business-authority
artifact — it implements a mapping-declaration and resolution capability over already-released
Blueprint semantics (CDD-017) and already-governed source/tenant physical structure (RFC-015), matching
CDD-017 §15's and CDD-018 §23's identical precedent.

## 25. Authorized persistence, domain, and implementation artifacts

**Reserved for future, separately-authorized implementation phases, not authorized by this governance
document itself.** This CDD authorizes the *architecture* of Source-to-Blueprint Semantic Mapping
(§6-20); it does not itself authorize writing `SourceField`, `SemanticMapping`, their persistence,
repositories, or the H2 resolution service. The exhaustive artifact-authorization table for each
implementation phase (mirroring CDD-017's G2/G3/G3.5 and CDD-018's G4 companions' exact format: artifact
path, Action/Authority/Purpose/Exclusions/Evidence columns) is intentionally deferred to that phase's own
CDD-Template-v2.2-compliant authorization record — **one companion per phase**: H1 (`SourceField`/
`SemanticMapping` domain and persistence), H2 (resolution service), H3 (deterministic demonstration
evidence). Implementation MUST NOT proceed against §6-20's model without the applicable phase's separate,
subsequent artifact-authorization record existing first — the identical binding precondition CDD-017
§17/§19 and CDD-018 §25 established, restated here for this CDD's own authority. **H4 has no
artifact-authorization companion under this CDD at all** — it requires its own, separate, future CDD
(§6, §20).

## 26. Authorized configuration artifacts

None authorized. No new environment variable, Keycloak scope, or deployment configuration is authorized
by this CDD (§21 — no API means no new scope is needed yet).

## 27. Acceptance criteria

1. `SourceField`/`SemanticMapping` correctly express exactly one `SourceField` ↔ one
   `InformationElementRequirement` correspondence, with `tenant_id` never duplicated as a direct column
   on either table.
2. At most one `Approved` `SemanticMapping` exists per `(information_element_requirement_id, tenant)`
   pair, enforced and tested, including an explicit ambiguity-raises test.
3. No transformation, derivation, calculation, unit-conversion, or conditional-mapping field or logic
   exists anywhere in the implementation.
4. No `InformationElementDefinition` or other intermediate semantic-identity object exists anywhere in
   the implementation.
5. No `Blueprint`, `ConceptRequirement`, `InformationElementRequirement`, Blueprint persistence,
   Blueprint migration, `BlueprintRepository`, `BlueprintApplicationService`, or
   `BlueprintConformanceApplicationService` modification exists anywhere in the implementation.
6. `InformationElementRequirement` evaluation remains `NOT_EVALUATED` for every element, unchanged.
7. Cross-tenant mapping resolution is structurally impossible, proven against real PostgreSQL
   (mirroring `test_context_store_tenant_isolation`'s exact precedent).
8. No HTTP endpoint, authentication check, or scope enforcement exists anywhere in the implementation,
   confirmed by an architecture-drift-style test extension (`test_runtime_architecture.py` precedent).
9. No modification to `assertions`, `SourceObservation`, `InstitutionalConcept`,
   `SemanticResolutionRecord`, Entity Resolution, Governance Engine, Knowledge Engine, or Decision
   Engine.
10. Resolving the same tenant/element pair against unchanged data twice yields an identical result.
11. Seed/demonstration data is idempotent (re-running creates nothing new).
12. Architecture-drift, dependency, and secret checks pass with zero unauthorized diff.

## 28. Rollback

Backend-only, additive: revert the implementation phase's code. Each phase's migration (H1 only —
H2/H3 introduce no schema) is independently revertible with no impact on `Blueprint`,
`BlueprintConformance`, or any other existing table, since `SourceField`/`SemanticMapping` are new,
independent tables with no inbound FK from any existing table. No frontend, Keycloak, or
business-policy rollback is implicated, since none of those are touched by this CDD.

## 29. Architecture drift check

This CDD introduces no new canonical ontology concept, canonical relationship, business rule, RFC
exception, architecture bypass, unapproved technology, Keycloak change, or Gate F/Ask CTEC/Entity
Resolution/Governance Engine/Knowledge Engine/Decision Engine/Blueprint/Blueprint Conformance behavior
change. A future implementation must stop if satisfying any part of this CDD requires such a change —
in particular, if mapping declaration is ever found to require reading a live source-field value (§6,
§20), or if a second Blueprint version is ever minted without first resolving the dependency §19
records.

## 30. Non-claims

This CDD does not authorize any new ontology concept or relationship (RFC-010/RFC-017 remain the sole
vocabulary authority); any API, Keycloak, or authentication/authorization change; any transformation,
derivation, or expression-engine capability (§4, §12); any `InformationElementDefinition` or
intermediate semantic-identity object (§4, §10); any modification to CDD-017, CDD-018, their
companions, Gate F, Ask CTEC, Entity Resolution, Governance Engine, Knowledge Engine, or Decision
Engine; any Blueprint versioning/re-parenting mechanism implementation (§19 — inherited, not owned);
the H1/H2/H3 implementation itself (§25, reserved for separate, subsequent, phase-by-phase
implementation authorizations); or H4 — Blueprint Information-Element Conformance Integration (§6,
§20) — none are implemented, authorized, or implied by this document.

## 31. Numbered architecture baseline determination

**No new numbered architecture baseline is required.** Resolved directly from repository precedent,
following the identical method CDD-017 §24 and CDD-018 §31 used: this CDD introduces no new RFC-tier or
PAD-tier document — it cites RFC-015, CDD-017 (with companions), and CDD-018 unchanged, and defers any possible future PAD (if an external mapping-authoring API is ever authorized,
§21) and any possible future RFC (if new ontology vocabulary is ever needed) to their own, separate,
later publications. CDD-011 through CDD-018 were all published via `architecture/INDEX.md`'s
non-baseline-tracked "Governed implementation work orders" table alone, with no new
`architecture/released/v1.\d+/` directory created for any of them — confirmed structurally exempt from
`scripts/verify_architecture_release.py`'s baseline/checksum checks, identical to every prior CDD entry
there. This CDD follows that identical, now eight-times-proven pattern.

## 32. Authorization

Authorized by CTEC Product Owner Manoj Nair: this Work Order's publication to FROZEN governance state,
per the Gate H Phase 0 Discovery Report, the Gate H Product Owner Architecture Decision Review, the
Gate H Decision 2 Resolution Review, the Gate H Governance Discovery & Authorization Planning report,
and the Product Owner's frozen Decision 1 (Option A — deterministic 1:1 correspondence, no
transformation) and Decision 2 (direct mapping to `InformationElementRequirement`, no
`InformationElementDefinition`). No implementation exists yet — separate, subsequent Product Owner
implementation-planning authorizations (§25), one per phase, are required before any persistence,
domain, application, or test artifact for H1, H2, or H3 is created. H4 is not authorized by this
document under any circumstance and requires its own, separate, future CDD.
