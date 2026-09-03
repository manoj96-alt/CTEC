# CDD-050 — OQI-H4 Governed Integrity

Version: 1.0
Status: FROZEN
Governing authorities: CDD-046 (OQI-H0, nine-dimension architecture, FROZEN, §16/§23/§27/§29-§30/§35/§41/§44
consumed directly), CDD-046 QualityRule Ownership Erratum (FROZEN, consumed for `RelationshipRequirement`
ownership reasoning by direct analogy), CDD-047/CDD-048/CDD-049 and their Artifact Authorizations and
amendments (FROZEN, read as precedent for evaluator-family/Finding-storage/coverage/remediation shape —
never modified by this document), CDD-017 (Blueprint, read as the governed ontology-requirement anchor this
document reuses unmodified)
Precedent phases: OQI-H4-DR (`OQI-H4-DR: COMPLETE — PRODUCT OWNER DECISION REQUIRED`), Product Owner
decisions PO-H4-01 through PO-H4-05 (accepted, restated and applied throughout this document)

## 1. Purpose

Freezes the exact, implementation-ready architecture for OQI-H4 — governed Integrity — converting CDD-046's
already-frozen conceptual definition (§16, §23) and the accepted H4-DR discovery into precise persistence
topology, evaluation algorithms, Finding taxonomy integration, and a companion exact Artifact Authorization.
This document authorizes no implementation; a future Artifact Authorization-gated implementation phase
(OQI-H4-I) is required before any code, migration, test, or Docker change occurs.

## 2. Authoritative baseline (verified at G-start)

```
HEAD (working tree, verified byte-identical to origin/main):  e87bb29580952ab05b0879100511f70f88523fc4
origin/main:                                                   5bf3e70a8a0cd2f94b78b262f231d3ffc7d3d9f5
Branch:                                                         oqi-h3/conformity-canonical-standards
Working tree at start: ?? docs/product/ (pre-existing, untouched)
Migration head:         0033_oqi_h3_consistency_proj
Governed business table count (fresh, real PostgreSQL, excludes alembic_version): 114
Highest existing CDD:   CDD-049  →  this document is CDD-050
```

No implementation change occurred anywhere in the repository during H4-DR or H4-G discovery. §17 below
records the exact new persistence this document authorizes for a future phase.

## 3. Capability claim (exact, binding)

This document freezes: the exact governed relationship-requirement reuse (§5-§6); the exact new cardinality
extension schema (§7); the exact two-evaluator-subject architecture and their exact algorithms (§8-§13); the
exact Finding taxonomy integration, including the first-ever extension of `FindingStorageFamily` (§14-§16);
the exact downstream integration with OQI4/OQI6/Reliance/Coverage/Remediation, including two genuine,
concretely-discovered compatibility gaps (§18-§22); the exact persistence schema, six new tables (§17); the
exact migration sequence, four migrations (§23); the exact governed table-count delta, `114 → 120` (§17);
the exact crown scenario, built entirely from already-seeded, already-governed data (§25); the exact
executable test matrix (§26); the exact Docker verification gate (§27); the exact eleven new crown
invariants plus every preserved invariant from H0-H3 (§28); and a companion Artifact Authorization
(`CDD-050-OQI-H4-Governed-Integrity-Artifact-Authorization.md`).

This document does **not** implement any of the above. Its only authorized repository writes are itself and
its companion Artifact Authorization.

## 4. Product Owner decisions (accepted, restated verbatim in force)

```
PO-H4-01  Cardinality measured over DISTINCT QUALIFYING GOVERNED TARGET ENTITIES, not raw row count.
          Representation: min_cardinality (integer >= 0), max_cardinality (integer >= min_cardinality |
          NULL = unbounded). No ONE_TO_ONE/ONE_TO_MANY/MANY_TO_MANY shorthand.
PO-H4-02  New FindingStorageFamily.INTEGRITY (not OQI4, not OQI_H4). FindingFamily unchanged.
          QualityFindingOrigin dataclass shape unchanged. The three Finding types remain exactly
          MISSING_REQUIRED_RELATIONSHIP, ORPHAN_REFERENCE, RELATIONSHIP_CARDINALITY_VIOLATION.
PO-H4-03  Two semantic evaluation subjects: STRUCTURAL (EnterpriseEntity x RelationshipRequirement) and
          REFERENCE (reference observation x RelationshipRequirement x persisted ER ResolutionOutcome).
          Two semantic subjects do not automatically mean four persistence tables -- topology resolved
          independently at §17.
PO-H4-04  ORPHAN_REFERENCE requires a genuine persisted ResolutionOutcome.UNRESOLVED. POSSIBLE and "no
          outcome" are both NOT_EVALUABLE. RESOLVED reference with an absent edge is Structural Integrity's
          concern (MISSING_REQUIRED_RELATIONSHIP where applicable), never ORPHAN_REFERENCE.
          RESOLVED REFERENCE != MATERIALIZED RELATIONSHIP.
PO-H4-05  H4 v1 is investigation-oriented. No CREATE_RELATIONSHIP/DELETE_RELATIONSHIP/RESOLVE_ENTITY. No
          UPDATE_FIELD misuse. No autonomous graph mutation.
```

## 5. Existing ontology architecture reused (re-verified directly against current source, not the DR report
alone)

Three layers, unmodified, all confirmed by direct inspection of `backend/app/domain/blueprint/model.py`,
`backend/app/infrastructure/persistence/models/{blueprint,institutional_relationship,
ontology_relationship_binding,enterprise_entity,relationship_type,entity_type,entity_resolution}.py`:

```
TYPE/COMPATIBILITY (SHARED PLATFORM, no tenant_id):
    EntityType, RelationshipType, OntologyRelationshipBinding
        (source_entity_type_id x relationship_type_id x target_entity_type_id -- permitted triples)

GOVERNED REQUIREMENT (SHARED PLATFORM, no tenant_id, CDD-017 §9 reconfirmed directly against the ORM):
    Blueprint -> ConceptRequirement (entity_type_id, Obligation)
             -> RelationshipRequirement (relationship_requirement_id, concept_requirement_id,
                                          relationship_type_id, target_entity_type_id, Obligation)

TENANT INSTANCE GRAPH (TENANT-OWNED, RFC-016 tenant-qualified composite FKs, confirmed directly):
    EnterpriseEntity (entity_type_id FK)
        <-> InstitutionalRelationship (relationship_type_id, from_entity_id, to_entity_id,
             lifecycle_state Draft/Active/Suspended/Archived, governance_status
             Proposed/Approved/Retired/Archived, version_number, previous_version_id, superseded_by_id --
             history preserved, never physically deleted)

ER (TENANT-OWNED, confirmed directly against enterprise_entity_resolution_records):
    EnterpriseEntityResolutionRecordModel.outcome: String(32), carrying ResolutionOutcome's three real,
    persisted values -- RESOLVED / POSSIBLE / UNRESOLVED -- keyed to supporting_source_object_ids
    (SourceObject-granularity, not FieldValueEvidence-granularity).
```

`RelationshipRequirement` is the exact governed anchor CDD-046 §16 requires and this document reuses
unmodified. **No competing relationship schema is created anywhere in this document.**

## 6. RelationshipRequirement — confirmed gap (binding)

`RelationshipRequirementORM` carries `relationship_requirement_id`, `concept_requirement_id`,
`relationship_type_id`, `target_entity_type_id`, `obligation` (`REQUIRED`/`CONDITIONAL`/`OPTIONAL`) —
**no cardinality field of any kind**, confirmed directly against both the domain dataclass and the ORM.
`Obligation` alone cannot express `1..1` vs `1..N` vs `2..3`. This is the exact, sole gap this document's
new cardinality extension (§7) closes — additively, anchored to the existing requirement, never
duplicating its source/type/target fields.

## 7. Cardinality extension — exact schema (binding, resolves PO-H4-01 + G0 §8-§9 of the governing prompt)

**Domain name**: `IntegrityRelationshipCardinality` (permanent domain vocabulary — no implementation-phase
name).

**Ownership**: SHARED PLATFORM. Refines the H4-DR discovery (not CDD-046 §29's original tenant-owned
guess, which predated confirmation that `RelationshipRequirement` itself is shared, CDD-017 §9): a
cardinality refinement of an already-shared governed requirement is itself governed, enterprise-universal
structure — identical reasoning to the QualityRule Ownership Erratum's own precedent (a governed
expectation tied to shared structure is shared structure, never a per-tenant artifact). A tenant's
*satisfaction* of the cardinality remains entirely tenant-owned (§8).

**Table**: `oqi_integrity_relationship_cardinalities`

```
integrity_relationship_cardinality_id   UUID, primary key
relationship_requirement_id             UUID, FK -> relationship_requirements.relationship_requirement_id,
                                         NOT NULL
min_cardinality                         INTEGER, NOT NULL, CHECK (min_cardinality >= 0)
max_cardinality                         INTEGER, NULLABLE, CHECK (max_cardinality IS NULL
                                             OR max_cardinality >= min_cardinality)
status                                  ACTIVE | RETIRED
version_number                          INTEGER, NOT NULL, >= 1
previous_version_id                     UUID, FK -> oqi_integrity_relationship_cardinalities
                                         .integrity_relationship_cardinality_id, NULLABLE
created_by                              TEXT, NOT NULL
created_on                              TIMESTAMPTZ, NOT NULL
retired_on                              TIMESTAMPTZ, NULLABLE
```

**Uniqueness**: a partial unique index, `UNIQUE(relationship_requirement_id) WHERE status = 'ACTIVE'` —
exactly one ACTIVE cardinality definition per `RelationshipRequirement`, mirroring
`uq_oqi_canonical_standards_one_active`'s established precedent (CDD-049 §10) exactly.

**Version chain**: identical shape to `CanonicalStandard`'s own versioning (CDD-049 §10) — immutable rows,
`previous_version_id` self-FK, retirement is a status flip via a dedicated `retire_cardinality` repository
method, never a physical delete. No DELETE authorized on this table (§17's deletion-behavior column, all
rows).

**Advisory lock**: dedicated seed distinct from every existing OQI1-6/H1-H3 seed (§39's exact assignment
deferred to implementation per CDD-046 §39's own precedent — H4-I assigns the next available integer,
disclosed in its own report, never silently reused).

## 8. Obligation + cardinality interaction (binding, resolves governing prompt §9)

```
REQUIRED      applicable to H4 v1. min_cardinality MUST be >= 1 on any cardinality row anchored to a
              REQUIRED RelationshipRequirement (enforced at H4-I's own validation layer, not a DB CHECK
              spanning two tables).
OPTIONAL      applicable if a cardinality row exists. min_cardinality may be 0 -- zero relationships is
              SATISFIED.
CONDITIONAL   H4 v1 has no governed conditional-applicability engine for RelationshipRequirement (none
              exists anywhere in the current codebase for this concept -- confirmed absent). Therefore
              NOT_EVALUABLE, zero persisted row. Never silently treated as REQUIRED or OPTIONAL.
```

## 9. No-policy behavior (binding, resolves governing prompt §10 — Option B selected)

**A RelationshipRequirement with no ACTIVE `IntegrityRelationshipCardinality` row is NOT_EVALUABLE for
Structural Integrity**, regardless of its `Obligation` value. Option A (treat bare `Obligation.REQUIRED`
as an implicit `min=1, max=unbounded`) is explicitly rejected: it would retroactively make every one of
the canonical Blueprint's already-existing `REQUIRED` relationship requirements immediately,
silently Integrity-evaluable the moment H4 ships, without any deliberate H4-level governance act creating
a cardinality row for each — precisely the "absence of new H4 configuration becoming fabricated certainty"
the governing prompt warns against. A cardinality row (even a trivial `min=1, max=NULL`) is a deliberate,
minimal, explicit act of governance per relationship — never inferred.

## 10. Two evaluation subjects — exact algorithms

### 10.1 Structural Integrity

**Subject**: `(tenant_id, EnterpriseEntity.enterprise_entity_id, RelationshipRequirement
.relationship_requirement_id, IntegrityRelationshipCardinality.integrity_relationship_cardinality_id)`.

**Qualifying relationship** (exact, binding, resolves governing prompt §11) — an `InstitutionalRelationship`
row qualifies toward cardinality iff **all**:

```
relationship.tenant_id == evaluated tenant
relationship.from_entity_id == evaluated source EnterpriseEntity
relationship.relationship_type_id == RelationshipRequirement.relationship_type_id
target EnterpriseEntity.entity_type_id == RelationshipRequirement.target_entity_type_id
relationship.governance_status == 'Approved'
relationship.lifecycle_state == 'Active'
relationship.superseded_by_id IS NULL
```

Excluded, explicitly: Proposed/Retired/Archived governance status; Draft/Suspended/Archived lifecycle
state; superseded rows; wrong `relationship_type_id`; wrong target `entity_type_id`; wrong tenant.
**Source entity currency**: the evaluated `EnterpriseEntity` itself is not additionally filtered by its own
`lifecycle_state`/`governance_status` for H4 v1 (the entity is the evaluation *subject*, not a *candidate
edge*; filtering it out would silently produce `NOT_EVALUABLE`-shaped absence rather than an honest
`MISSING_REQUIRED_RELATIONSHIP`/`SATISFIED` verdict about that named entity — deferred, not silently
decided, if future evidence proves otherwise).

**Cardinality count** (resolves PO-H4-01 exactly): `COUNT(DISTINCT qualifying_relationship.to_entity_id)`
— distinct target entities, never raw edge-row count. Two edges to the same target under different
`institutional_relationship_name`s count once (governing prompt §11, PO-H4-01 example). Two edges to
different targets count as two.

**Outcome precedence** (exact, binding, resolves governing prompt §12 and §30):

```
count = 0 AND min_cardinality > 0        -> VIOLATED, MISSING_REQUIRED_RELATIONSHIP
count > 0 AND count < min_cardinality    -> VIOLATED, RELATIONSHIP_CARDINALITY_VIOLATION
max_cardinality IS NOT NULL
    AND count > max_cardinality          -> VIOLATED, RELATIONSHIP_CARDINALITY_VIOLATION
otherwise                                -> SATISFIED
```

Exactly one Finding type per evaluation, never both — `min=2, count=1` is
`RELATIONSHIP_CARDINALITY_VIOLATION` (a relationship genuinely exists, just insufficiently), never
`MISSING_REQUIRED_RELATIONSHIP` (reserved for the `count=0` case, where no relationship of the required
type exists at all) — exactly the distinction the governing prompt §12 requires frozen.

### 10.2 Reference Integrity

**Subject**: `(tenant_id, source_object_id, RelationshipRequirement.relationship_requirement_id)`,
consulting the tenant's latest `EnterpriseEntityResolutionRecordModel` row whose
`supporting_source_object_ids` includes `source_object_id` (ER's own real granularity, confirmed §5 — not
per-`FieldValueEvidence`).

**Algorithm** (exact, binding, resolves governing prompt §13, PO-H4-04):

```
ResolutionOutcome.UNRESOLVED   -> VIOLATED, ORPHAN_REFERENCE
ResolutionOutcome.POSSIBLE     -> NOT_EVALUABLE, zero row
no ResolutionOutcome record    -> NOT_EVALUABLE, zero row
ResolutionOutcome.RESOLVED     -> SATISFIED, persisted evaluation row (no Finding)
```

A `SATISFIED` row **is** persisted for the `RESOLVED` case — required so H1 coverage (§20) can honestly
distinguish "evaluated and resolved" from "never evaluated," mirroring every other dimension's own
`NOT_EVALUABLE`-means-zero-row / `SATISFIED`-means-a-real-row discipline exactly. Reference Integrity
**never** calls Entity Resolution's matching pipeline, never infers a target, never performs fuzzy lookup
— it is a strictly read-only consumer of an outcome ER already, independently, produced (governing prompt
§13, preserves `INTEGRITY EVALUATION != ENTITY RESOLUTION`).

**Explicit, binding limitation** (resolves governing prompt §18): `InstitutionalRelationship` carries no
FK to raw `FieldValueEvidence`. Structural Integrity may truthfully explain the governed requirement, the
entity, the current qualifying graph state, and relationship governance/lifecycle state — it may **never**
claim "this exact raw source observation created this edge." This is disclosed here as a genuine H4 v1
limitation, not silently worked around, and is explicitly **not** expanded into a relationship-evidence
provenance redesign (§29, deferred).

## 11. Persistence topology — G0 decision (binding, the single largest architecture decision this document
resolves)

**DECISION: OPTION B — subject-specific ledgers.**

Evaluated against all seventeen criteria in the governing prompt §5:

```
1. DB-level subject validity     B: every column NOT NULL and honestly typed per subject. A: would
                                  require nullable FKs for whichever subject-shape a given row is NOT,
                                  approximating two unrelated schemas behind CHECK constraints.
2. FK enforceability             B strictly stronger -- Structural FKs to EnterpriseEntity/
                                  RelationshipRequirement/cardinality-row are all NOT NULL; Reference FKs
                                  to source_object/RelationshipRequirement/resolution-record are all NOT
                                  NULL. Neither table's FKs are ever conditionally-relevant.
3. Tenant isolation               Equal under both -- not a discriminator.
4. Provenance reconstruction      B: each table's columns ARE its provenance, no discriminator-branching
                                  needed to interpret a row.
5. Deterministic Finding identity Equal -- identity formula is independent of physical table shape (§15).
6. Finding lifecycle              B: two independent, simply-shaped current-state machines, exactly
                                  mirroring how OQI1/OQI2/OQI3 already each own an independent Finding
                                  lifecycle despite sharing QualityFindingOrigin's semantic unification.
7. Idempotent re-evaluation       Equal under both.
8. History                        Equal -- both are append-only ledgers.
9. Downstream origin resolution   B: the new OQI4 resolver method (§19) branches on which of two new
                                  physical tables a finding_id belongs to -- an explicit, honest branch,
                                  not a subject_kind discriminator column masking two different row shapes.
10. OQI4 subject resolution       B: no ambiguity about which columns are meaningful for a given row.
11. OQI6 open-Finding aggregation B: a clean, explicit new UNION branch per physical table (§20), exactly
                                  the shape every existing family (OQI1/OQI2/OQI3) already uses there.
12. H1 coverage                   Equal -- both resolvable via a dispatch branch (§20).
13. Remediation/investigation     Equal -- both route to zero-candidate investigation (§22).
14. Query simplicity              A marginally simpler for a single "any Integrity evaluation exists"
                                  query; B requires two queries OR one UNION -- an acceptable, bounded
                                  cost, not a genuine complexity risk (governing prompt §5's own
                                  instruction: do not choose on table count).
15. Migration safety              Equal -- both are purely additive CREATE TABLE sets.
16. Future extensibility          B: a future third Integrity subject (if ever needed) adds a third table
                                  cleanly; A would need a third discriminator value plus more nullable
                                  columns, compounding the exact risk this decision avoids.
17. Impossible-hybrid-row risk    B eliminates it structurally -- a row cannot simultaneously carry a
                                  cardinality-violation shape and an orphan-reference shape, because no
                                  single table can hold both. A cannot eliminate this without the same
                                  CHECK-constraint apparatus this criterion warns against.
```

Option B wins on the criteria that matter (1, 2, 4, 6, 9, 11, 17 decisively; the rest at worst tied) and
loses only on query simplicity, explicitly the one criterion the governing prompt instructs not to decide
on. **Option A is rejected.**

## 12. Exact new tables (binding, resolves governing prompt §17/§34 — no ambiguity permitted)

```
1. oqi_integrity_relationship_cardinalities   (§7, full schema above) — SHARED PLATFORM

2. oqi_integrity_structural_evaluations        — TENANT-OWNED
   evaluation_id                UUID, PK
   tenant_id                    TEXT, NOT NULL
   relationship_requirement_id  UUID, FK -> relationship_requirements, NOT NULL
   integrity_relationship_cardinality_id  UUID, FK -> oqi_integrity_relationship_cardinalities, NOT NULL
   enterprise_entity_id         UUID, FK -> (tenant_id, enterprise_entity_id) composite, NOT NULL
   qualifying_target_count      INTEGER, NOT NULL
   outcome                      SATISFIED | VIOLATED
   evaluation_horizon           TIMESTAMPTZ, NOT NULL
   evaluated_on                 TIMESTAMPTZ, NOT NULL
   Indexes: (tenant_id), (tenant_id, enterprise_entity_id, relationship_requirement_id)

3. oqi_integrity_structural_evaluation_relationships  — TENANT-OWNED (evaluation-to-qualifying-edge link,
   mirrors quality_evaluation_evidence / oqi_comparison_participant_canonical_projection's established
   link-table precedent exactly)
   evaluation_id                 UUID, FK -> oqi_integrity_structural_evaluations, PK (composite)
   institutional_relationship_id UUID, FK -> institutional_relationships, PK (composite)
   Purpose: pins exactly which qualifying InstitutionalRelationship rows were counted -- reconstructable
   distinct-target provenance, never opaque JSON.

4. oqi_integrity_structural_findings           — TENANT-OWNED, mirrors quality_findings's own shape
   finding_id                   UUID, PK
   tenant_id                    TEXT, NOT NULL
   relationship_requirement_id  UUID, FK -> relationship_requirements, NOT NULL
   enterprise_entity_id         UUID, NOT NULL (tenant-qualified composite FK to enterprise_entities)
   finding_type                 MISSING_REQUIRED_RELATIONSHIP | RELATIONSHIP_CARDINALITY_VIOLATION
   status                       OPEN | RESOLVED
   state_revision, first_seen_at, last_seen_at, last_evaluated_horizon, occurrence_count, reopen_count
       -- identical shape to QualityFindingORM's own lifecycle columns
   Indexes: (tenant_id), (status)

5. oqi_integrity_reference_evaluations         — TENANT-OWNED
   evaluation_id                 UUID, PK
   tenant_id                     TEXT, NOT NULL
   relationship_requirement_id   UUID, FK -> relationship_requirements, NOT NULL
   source_object_id              UUID, FK -> (tenant_id, source_object_id) composite, NOT NULL
   resolution_record_id          UUID, FK -> enterprise_entity_resolution_records, NOT NULL
   resolution_outcome            RESOLVED | UNRESOLVED   (POSSIBLE/none never persist a row, §10.2)
   outcome                       SATISFIED | VIOLATED
   evaluation_horizon, evaluated_on  TIMESTAMPTZ, NOT NULL
   Indexes: (tenant_id), (tenant_id, source_object_id, relationship_requirement_id)

6. oqi_integrity_reference_findings            — TENANT-OWNED
   finding_id                    UUID, PK
   tenant_id                     TEXT, NOT NULL
   relationship_requirement_id   UUID, FK -> relationship_requirements, NOT NULL
   source_object_id              UUID, NOT NULL (tenant-qualified composite FK)
   finding_type                  ORPHAN_REFERENCE  (the table's sole possible value -- no CHECK needed
                                      beyond the domain enum's own closure, mirrors precedent of
                                      single-value finding_type columns elsewhere in this codebase)
   status, state_revision, first_seen_at, last_seen_at, last_evaluated_horizon, occurrence_count,
       reopen_count               -- identical shape to (4)
   Indexes: (tenant_id), (status)
```

**Deletion behavior, all six tables**: no DELETE authorized anywhere. Retirement/supersession is a status
flip only (table 1); evaluations/Findings are strictly append-only ledgers (tables 2-6), identical
discipline to every existing OQI evaluation/Finding table in this repository.

## 13. Exact table-count delta (binding)

```
114 (pre-H4, fresh-verified real PostgreSQL, excludes alembic_version)
  + 6 (§12)
= 120 (post-H4, governed business table count)
```

No ambiguity, no range. H4-I must re-verify `120` fresh against real PostgreSQL before any completion
claim, exactly as every predecessor phase's own discipline requires (CDD-044 §46 precedent, restated).

## 14. Finding types (binding, unchanged from CDD-046 §19)

Exactly `MISSING_REQUIRED_RELATIONSHIP`, `RELATIONSHIP_CARDINALITY_VIOLATION` (table 4, §12) and
`ORPHAN_REFERENCE` (table 6, §12). No fourth type. Represented as a new, dedicated `IntegrityFindingType`
StrEnum in the new domain module (§17) — **not** a `QualityFindingType` extension, since Integrity Findings
are not OQI1-storage-shaped (§16).

## 15. Finding identity (binding, resolves governing prompt §15)

Distinct OQI-family namespace, mirroring CDD-039 §20's precedent exactly:

```
OQI_INTEGRITY_NAMESPACE = uuid5(NAMESPACE_URL, "urn:ctec:oqi:integrity:v1")
```

```
Structural Finding identity = uuid5(OQI_INTEGRITY_NAMESPACE,
    tenant_id + "|" + enterprise_entity_id + "|" + relationship_requirement_id + "|STRUCTURAL")

Reference Finding identity = uuid5(OQI_INTEGRITY_NAMESPACE,
    tenant_id + "|" + source_object_id + "|" + relationship_requirement_id + "|REFERENCE")
```

**Explicitly excluded from identity** (stable across policy-version churn, per §5.4's own precedent,
restated here as binding): `integrity_relationship_cardinality_id`, `min_cardinality`, `max_cardinality`,
`version_number`, evidence/outcome values, `evaluation_horizon`. A cardinality policy version change never
creates a duplicate current Finding for the same entity/requirement pair — the existing Finding's own
lifecycle (§16) transitions instead.

Evaluation-row identity (distinct from Finding identity, following `derive_evaluation_id`'s own precedent)
additionally folds in the evaluation horizon and a digest of the consulted evidence/outcome, exactly
mirroring OQI1-3/H2/H3's established idempotent-replay discipline — full formula frozen at H4-I against
`derive_evaluation_id`'s exact signature, no new discipline invented.

## 16. Finding lifecycle (binding, resolves governing prompt §16)

Two new, independent transition functions — `apply_structural_finding_transition`,
`apply_reference_finding_transition` — mirroring `apply_transition`/`apply_correspondence_finding_
transition`'s identical state-machine shape (OPEN/RESOLVED, `state_revision`/`occurrence_count`/
`reopen_count`), never a shared generic abstraction invented for this document (matches this repository's
own established per-family duplication-over-premature-genericization discipline, confirmed by OQI1/OQI2
each already owning independent transition functions despite conceptually identical logic).

```
VIOLATED, fresh evaluation      -> opens or refreshes the current Finding (occurrence_count increments,
                                    reopen_count increments if the prior state was RESOLVED)
SATISFIED, fresh evaluation     -> transitions an existing OPEN current Finding to RESOLVED; no Finding
                                    row exists/created if none was already open
NOT_EVALUABLE                    -> MUST NOT close an existing Finding (zero row inserted; existing
                                    Finding, if any, untouched) -- binding, critical (governing prompt §16)
```

`NOT_EVALUABLE != RESOLVED` is structural: `NOT_EVALUABLE` never reaches the transition function at all
(zero-row short-circuit, identical to every prior dimension's own discipline).

## 17. New persistence and modules — exact naming

```
DOMAIN:
  backend/app/domain/oqi_integrity/__init__.py
  backend/app/domain/oqi_integrity/requirement.py    IntegrityRelationshipCardinality + version/
                                                        activation logic
  backend/app/domain/oqi_integrity/structural.py      IntegrityFindingType (shared enum, both subjects),
                                                        Structural evaluation/Finding dataclasses, identity
                                                        derivation, apply_structural_finding_transition
  backend/app/domain/oqi_integrity/reference.py       Reference evaluation/Finding dataclasses, identity
                                                        derivation, apply_reference_finding_transition

APPLICATION:
  backend/app/application/oqi_integrity_structural_evaluation_service.py
  backend/app/application/oqi_integrity_reference_evaluation_service.py

PERSISTENCE (models):
  backend/app/infrastructure/persistence/models/oqi_integrity.py   all six ORM classes (§12)

PERSISTENCE (repositories):
  backend/app/infrastructure/persistence/oqi_integrity_requirement_repository.py   (cardinality policy
      CRUD/versioning + dedicated advisory lock, §7)
  backend/app/infrastructure/persistence/oqi_integrity_structural_evaluation_repository.py
  backend/app/infrastructure/persistence/oqi_integrity_reference_evaluation_repository.py
```

## 18. QualityDimension placement (binding, resolves governing prompt §7 — a genuinely novel wrinkle,
disclosed explicitly)

`QualityDimension` gains `INTEGRITY` as its sixth member (`backend/app/domain/oqi/quality_rule.py`).
**Explicit disclosure**: Integrity is the first `QualityDimension` member that will **never** appear on any
`QualityRule.dimension` field — Integrity has no `QualityRule`-shaped configuration at all (§7's
`IntegrityRelationshipCardinality` is a distinct, non-`QualityRule` policy object). The member is added
**solely** so `QualityFindingOrigin.quality_dimension` (whose valid-value set is `QualityDimension` ∪
`BusinessRulePurpose`, confirmed directly against `_VALID_QUALITY_DIMENSION_VALUES`) can honestly carry
`"INTEGRITY"` — mirroring exactly how `CoverageDimension.INTEGRITY` already exists today with zero live
evaluator behind it (CDD-047 §4's own explicit, precedented pattern: "membership here never implies a live
evaluator exists"). **Zero change to `_ALLOWED_COMBINATIONS` or `QualityFindingType`** — narrower than
every prior dimension's own extension, since no `QualityRule` row shape is ever validated against
`INTEGRITY`.

## 19. FindingStorageFamily.INTEGRITY (binding, resolves PO-H4-02 exactly)

`backend/app/domain/oqi_finding_origin/origin.py` gains exactly one new `FindingStorageFamily` member,
`INTEGRITY`. `FindingFamily` (`backend/app/domain/oqi_ontology_impact/evaluation.py`, CDD-042 §10) is
**not touched** — direct repository evidence (§5, §12) proves this is not merely possible but the correct,
honest design: Integrity's evaluation shape fits none of OQI1/OQI2/OQI3's physical tables, and
`FindingFamily`'s own docstring ("OQI4 never introduces a fourth source of Findings") independently forbids
naming this new family "OQI4," confirming `INTEGRITY` as the only correct name (matches PO-H4-02 exactly).
`QualityFindingOrigin`'s dataclass shape requires zero structural change (§26 of the H4-DR report,
reconfirmed here against the actual `__post_init__` source: any new `FindingStorageFamily` member is
accepted trivially).

## 20. OQI4 origin/subject resolution — exact additive method (binding, resolves governing prompt §19-§20)

`OqiOntologyImpactEvaluationRepositoryImpl` (`backend/app/infrastructure/persistence/
oqi_ontology_impact_evaluation_repository.py`) gains two new, narrow, additive methods — never modifying
`resolve_finding_subject`/`resolve_finding_origin`'s existing `FindingFamily`-typed signatures (which stay
exactly as-is, serving OQI1/2/3 only, per PO-H4-02's own instruction that `FindingFamily` stays closed):

```
resolve_integrity_structural_finding_origin(tenant_id, finding_id) -> QualityFindingOrigin
    finding_storage_family = FindingStorageFamily.INTEGRITY, quality_dimension = "INTEGRITY"

resolve_integrity_structural_finding_subject(tenant_id, finding_id) -> ResolvedFindingSubject
    subject = the evaluated EnterpriseEntity's own id (a real, known, governed entity -- never fabricated)

resolve_integrity_reference_finding_origin / _subject   -- identical shape for table 6

    Reference Integrity subject: the SOURCE-side EnterpriseEntity, if and only if that source_object_id
    is itself independently resolved (a genuinely separate ER resolution fact from the orphaned target
    reference). If the source itself is unresolved too, the subject is honestly IMPACT_UNKNOWN -- never a
    fabricated target entity for the orphaned reference itself (governing prompt §20, preserves
    UNKNOWN TARGET != ORPHAN FACT and ORPHAN REFERENCE != KNOWN TARGET ENTITY).
```

**Confirmed, concrete schema blocker requiring a narrow additive migration** (governing prompt §6 mandates
this exact class of discovery be found now, not at H4-VM): `OntologyImpactEvaluationORM.finding_family` and
`CurrentOntologyImpactORM.finding_family` (`backend/app/infrastructure/persistence/models/
oqi_ontology_impact_evaluation.py`, both lines confirmed directly) are `String(8)` — sized for
`"OQI1"`/`"OQI2"`/`"OQI3"` (4 chars) but not `"INTEGRITY"` (9 chars). **This document authorizes widening
both columns to `String(16)`** via a dedicated migration (§23) — a pure storage-width change, zero semantic
change to `FindingFamily`'s membership or to any existing OQI1/2/3 value, zero risk to existing data.

## 21. OQI4 impact — no automatic criticality (binding)

`INTEGRITY VIOLATION != AUTOMATIC ONTOLOGY IMPACT` (crown invariant §28). No dimension-specific
criticality shortcut, no hard-coded `MISSING_REQUIRED_RELATIONSHIP = CRITICAL`. Impact remains entirely a
function of `BusinessDependency` (unchanged, CDD-046 §33 reaffirmed) — Integrity Findings enter the
identical, unmodified propagation pipeline as every other Finding source, via the two new resolver methods
(§20) feeding `CurrentOntologyImpact` exactly as OQI1/2/3 already do.

## 22. OQI6 / Reliance — exact required compatibility change (binding, resolves governing prompt §22 — a
concrete finding, not an assumption)

**Confirmed, concrete gap**: `OqiBusinessImpactRepositoryImpl.compute_subject_finding_state`
(`backend/app/infrastructure/persistence/oqi_business_impact_repository.py`) is **not** dimension-blind at
the storage-family level — it is a hardcoded `union_all` of exactly six `SELECT` branches (three direct,
`source_object_ids`-keyed; three indirect, `CurrentOntologyImpactORM`-keyed), one literal pair per
`FindingFamily` member, confirmed directly against the source. **This document authorizes exactly one new
indirect-path `SELECT` branch** for `oqi_integrity_structural_findings`, joined through
`CurrentOntologyImpactORM.finding_family == 'INTEGRITY'` (the widened column, §20) exactly mirroring the
three existing indirect-path branches' shape — and one further branch for `oqi_integrity_reference_
findings` under the same join condition, for the cases where a Reference Integrity subject legitimately
resolves (§20). Without this addition, Integrity Findings would silently never surface in Reliance's
`any_open_finding` computation — this is the exact, concrete instance of the H3-VM-R1 lesson (§3 of the
governing prompt) this document exists to preempt.

No new `RelianceState`. `RELIANCE_UNKNOWN` for required-but-uncovered Integrity, `AT_RISK` via the existing
`any_open_finding` input once the new branches are added — both entirely unmodified downstream logic.

## 23. Exact migration sequence (binding, resolves governing prompt §35 — no ambiguity)

```
Expected current head: 0033_oqi_h3_consistency_proj  (VERIFIED, real PostgreSQL, this phase)

0034_oqi_h4_integrity_policy       (28 chars)   down_revision: 0033_oqi_h3_consistency_proj
    Creates: oqi_integrity_relationship_cardinalities

0035_oqi_h4_integrity_structural   (32 chars)   down_revision: 0034_oqi_h4_integrity_policy
    Creates: oqi_integrity_structural_evaluations, oqi_integrity_structural_evaluation_relationships,
             oqi_integrity_structural_findings

0036_oqi_h4_integrity_reference    (31 chars)   down_revision: 0035_oqi_h4_integrity_structural
    Creates: oqi_integrity_reference_evaluations, oqi_integrity_reference_findings

0037_oqi_h4_impact_width           (24 chars)   down_revision: 0036_oqi_h4_integrity_reference
    ALTER COLUMN ontology_impact_evaluations.finding_family TYPE VARCHAR(16)
    ALTER COLUMN current_ontology_impacts.finding_family TYPE VARCHAR(16)
    (widening only -- no data migration, no semantic change, existing OQI1/2/3 values unaffected)
```

All four revision IDs independently character-counted, confirmed <= 32 chars (32/31/28/24). Single linear
head required throughout. Required round trip: `114 -> 120 -> 114 -> 120`, using
`0033_oqi_h3_consistency_proj` (the exact pre-H4 head) as the downgrade target, mirroring every predecessor
phase's own round-trip discipline exactly.

## 24. Coverage semantics (binding, resolves governing prompt §23)

`CoverageDimension.INTEGRITY` already exists (CDD-047, confirmed live). One new dispatch branch in
`OqiQualityCoveragePolicyRepositoryImpl.has_qualifying_coverage_for_dimension`: **Candidate C** (subject-
correct, not "any Integrity row exists anywhere in the tenant") — existence of a qualifying Structural
**or** Reference Integrity evaluation row (any outcome, `SATISFIED` or `VIOLATED`, existence-only per every
prior dimension's identical precedent) whose subject (`enterprise_entity_id` or `source_object_id`) matches
the coverage anchor's own `source_object_ids`, exactly mirroring the Accuracy/Conformity precedent's own
existence-only, subject-scoped query shape.

## 25. Remediation (binding, resolves PO-H4-05 + governing prompt §24)

**No new `RemediationCandidateBasis` member.** Both Structural and Reference Integrity Findings route to
zero candidates / `STEWARD_INVESTIGATION`, mirroring `extract_reasonableness_candidates()`'s own precedent
exactly (`backend/app/domain/oqi_remediation/candidate.py`, unmodified) — a function that always returns
`()`, requiring no new enum member because no `RemediationCandidate` is ever constructed.
`backend/app/application/oqi_remediation_service.py` gains one new dispatch branch,
`quality_dimension == "INTEGRITY"` → zero candidates, mirroring the existing `REASONABLENESS` branch's
exact shape. No `CREATE_RELATIONSHIP`/`DELETE_RELATIONSHIP`/`RESOLVE_ENTITY` action type is introduced. No
`UPDATE_FIELD` misuse. Resolution requires a fresh, independent re-evaluation exactly as every prior
dimension requires (§16) — never a human/agent/authorization/execution-report say-so.

## 26. Authority (binding, resolves governing prompt §25)

**No new Keycloak scope, no new API route.** Cardinality-policy configuration remains under existing
governed Blueprint/steward-configuration mechanisms (seeder/steward-authored, identical to how
`QualityRule`/`CanonicalStandard` are configured today — no live write API exists for either, confirmed
directly, and none is authorized for `IntegrityRelationshipCardinality` either).

## 27. Tenancy (binding, resolves governing prompt §26)

```
RelationshipRequirement              SHARED PLATFORM   (unchanged, CDD-017)
IntegrityRelationshipCardinality     SHARED PLATFORM   (§7)
EnterpriseEntity                     TENANT-OWNED       (unchanged)
InstitutionalRelationship            TENANT-OWNED, RFC-016 composite FKs (unchanged)
Integrity evaluation (both tables)   TENANT-OWNED
Integrity Finding (both tables)      TENANT-OWNED
FieldValueEvidence / source_object   TENANT-OWNED       (unchanged, existing model)
ResolutionOutcome                    TENANT-OWNED       (unchanged, existing model)
```

No tenant's graph or ER result may satisfy another tenant's evaluation — structurally enforced by the same
RFC-016 tenant-qualified composite FKs the existing `InstitutionalRelationship`/`EnterpriseEntity` tables
already carry, reused unmodified. Real-PostgreSQL adversarial proof required at H4-I (§26 of the future
test matrix).

## 28. Exact crown scenario (binding, resolves governing prompt §27 — verified against real seed source,
not invented)

**Confirmed directly** against `backend/app/infrastructure/persistence/ontology_seed.py` and
`backend/app/infrastructure/persistence/blueprint_seed.py`: the canonical Blueprint **already, today,
unmodified** governs a real `RelationshipRequirement`:

```
Source concept:       Product      (real EntityType, real ConceptRequirement, Obligation.REQUIRED)
Relationship type:    assembledAt  (real RelationshipType, real OntologyRelationshipBinding)
Target concept:       Facility     (real EntityType)
Obligation:            REQUIRED     (hardcoded uniformly for every RelationshipRequirement in the
                                     canonical Blueprint, confirmed directly)
relationship_requirement_id = uuid5(BOOTSTRAP_SEED_NAMESPACE,
    "CANONICAL-BLUEPRINT-V1:relationship-requirement:assembledAt")   (deterministic, reproducible)
```

**Zero new Blueprint/ConceptRequirement/RelationshipRequirement is authorized or required.** The demo
seeder's own H4 addition (governed by the companion Artifact Authorization) creates exactly: one
`IntegrityRelationshipCardinality` row (`min=1, max=1`, ACTIVE, anchored to the real
`relationship_requirement_id` above); real `EnterpriseEntity` rows of `entity_type_id = Product`/`Facility`
for each scenario; real `InstitutionalRelationship` edges (`relationship_type_id = assembledAt`,
`governance_status = Approved`, `lifecycle_state = Active`) for scenarios A/C; a real
`EnterpriseEntityResolutionRecordModel` row with `outcome = 'Unresolved'` for scenario D.

```
A. Product P1 --assembledAt--> Facility S1 (one qualifying edge)          -> SATISFIED
B. Product P2, zero qualifying assembledAt edges                          -> MISSING_REQUIRED_RELATIONSHIP
C. Product P3 --assembledAt--> S1 AND --assembledAt--> S2 (two distinct)  -> RELATIONSHIP_CARDINALITY_
                                                                              VIOLATION
D. Product P4's source reference genuinely evaluated, ResolutionOutcome
   .UNRESOLVED persisted                                                  -> ORPHAN_REFERENCE
E. ResolutionOutcome.POSSIBLE                                             -> NOT_EVALUABLE
F. No ResolutionOutcome record exists at all                              -> NOT_EVALUABLE
G. ResolutionOutcome.RESOLVED, but the resolved EnterpriseEntity has no
   qualifying assembledAt edge                                             -> not orphan; Structural
                                                                               independently reads
                                                                               MISSING_REQUIRED_RELATIONSHIP
H. Duplicate-named edges to the same target (P1->S1 twice, distinct
   institutional_relationship_name)                                        -> count once (PO-H4-01)
I. A wrong-tenant Facility cannot satisfy P1's requirement                 -> excluded structurally
   (RFC-016 composite FK)
J. Proposed/Draft/Suspended/Retired/superseded edges                       -> excluded, cannot satisfy
```

## 29. H1/H2/H3 non-regression (binding)

No Integrity evaluator may modify `FieldValueEvidence`; alter `OqiAccuracyEvaluationService` (confirmed
zero diff required — Integrity never imports it); alter canonicalization (`OqiConformityEvaluationService`/
`CanonicalStandard`, zero diff required); create new ER matches (§10.2, read-only consumption only);
reinterpret Consistency; or alter any existing Finding's identity formula. Verified: none of
Completeness/Validity/Consistency/Accuracy/Conformity's evaluators touch `InstitutionalRelationship`,
`RelationshipRequirement`, or `ResolutionOutcome` (zero cross-reference, grep-confirmed) — zero shared
mutable state with H4's new tables.

## 30. Crown invariants (binding, all eleven frozen)

```
1.  DATABASE FK VALID != BUSINESS INTEGRITY
2.  VALUE PRESENT != RELATIONSHIP PRESENT
3.  VALID REFERENCE FORMAT != RESOLVED REFERENCE
4.  CONSISTENT REFERENCE != RESOLVED REFERENCE
5.  CANONICAL REFERENCE != RESOLVED REFERENCE
6.  UNKNOWN TARGET != ORPHAN FACT
7.  RELATIONSHIP CANDIDATE != RELATIONSHIP FACT
8.  AGENT INFERENCE != GOVERNED RELATIONSHIP
9.  INTEGRITY VIOLATION != AUTOMATIC ONTOLOGY IMPACT
10. REMEDIATION != RELATIONSHIP RESOLUTION
11. RESOLVED REFERENCE != MATERIALIZED RELATIONSHIP
```

Plus, restated and preserved unmodified from CDD-046/048/049 (verified fresh against those documents'
exact wording, not paraphrased): `MAJORITY ≠ TRUTH`, `AUTHORITY ≠ TRUTH`, `CANDIDATE ≠ TRUTH`,
`AGENT ≠ FACT`, `RECOMMENDATION ≠ AUTHORIZATION`, `AUTHORIZATION ≠ REMEDIATION`, `REMEDIATION ≠ RESOLUTION`,
`AUTHORIZATION_ID ≠ AUTHORITY`, `UNKNOWN ≠ LOW`, `NO FINDINGS ≠ TRUSTED`, `VALID ≠ ACCURATE`,
`CONSISTENT ≠ ACCURATE`, `CANONICAL ≠ ACCURATE`, `DUPLICATE CANDIDATE ≠ DUPLICATE FACT`,
`ANOMALY ≠ QUALITY DEFECT`, `PARTIAL REQUIRED COVERAGE ≠ SUPPORTED`, `QUALITY CONCLUSION ≠ REFERENCE
EVIDENCE`, `CONFIGURATION AUTHORITY ≠ REMEDIATION AUTHORITY`, `CONFIGURATION AUTHORITY ≠ VERIFICATION
AUTHORITY`, `VERIFICATION AUTHORITY ≠ REMEDIATION AUTHORITY`, `VALID ≠ CONFORMING`, `CONFORMING ≠
ACCURATE`, `CANONICAL EQUIVALENCE ≠ RAW EQUALITY`, `NORMALIZED FOR MATCHING ≠ GOVERNED CANONICAL`,
`CANONICALIZATION ≠ SOURCE MUTATION`, `NON-CONFORMITY ≠ ONTOLOGY IMPACT`, `CANONICALIZATION FAILURE ≠
VALUE CONFLICT`.

Additionally adopted, named explicitly in response to §32-§33 of the governing prompt:
`POLICY CHANGE ≠ QUALITY RESOLUTION` (a cardinality-version retirement never itself closes a Finding —
only a fresh, independently re-evaluated `SATISFIED` result does, §16) and `GRAPH MUTATION WITHOUT FRESH
EVALUATION ≠ RESOLUTION` (relationship retirement/supersession itself never closes a Finding — the
existing `InstitutionalRelationship` version-history mechanism, §5, is sufficient; no broader temporal
graph redesign is required or authorized).

## 31. Repository-wide compatibility findings (binding — pre-authorized now, not deferred to H4-VM)

Searched repository-wide for every `QualityDimension`/`FindingStorageFamily`/`FindingFamily` consumer.
Confirmed genuine, mechanically necessary touch points (each named in the companion Artifact Authorization):

```
backend/app/domain/oqi/quality_rule.py                        QualityDimension gains INTEGRITY (§18)
backend/app/domain/oqi_finding_origin/origin.py                FindingStorageFamily gains INTEGRITY (§19)
backend/app/infrastructure/persistence/oqi_ontology_impact_
    evaluation_repository.py                                   two new additive resolver methods (§20)
backend/app/infrastructure/persistence/models/
    oqi_ontology_impact_evaluation.py                           finding_family String(8) -> String(16)
backend/app/infrastructure/persistence/oqi_business_impact_
    repository.py                                                two new UNION branches (§22)
backend/app/infrastructure/persistence/
    oqi_quality_coverage_policy_repository.py                    one new dispatch branch (§24)
backend/app/application/oqi_remediation_service.py               one new dispatch branch (§25)
backend/app/tests/test_oqi_quality_coverage_policy_domain.py     exact-member-count assertion, 5 -> 6
backend/app/tests/test_oqi_quality_coverage_policy_service.py    INTEGRITY dispatch test (mirrors H3's own
                                                                    Conformity-dispatch-test precedent)
backend/app/tests/test_runtime_architecture.py                   construction-site firewall additions for
                                                                    every new ORM class (§12)
.github/workflows/ci.yml                                         table-count assertion 114 -> 120
6 mechanical table-count files (identical set to H3's own precedent, confirmed by fresh grep):
    test_oqi_business_rule_postgres.py, test_oqi_ontology_impact_postgres.py,
    test_persistence_integration.py, test_oqi_business_impact.py,
    test_oqi_remediation_agent_i2.py, test_oqi_remediation_i1.py
```

**No unexpected `_FakeRepository`/Protocol-conformance risk was found this phase** — Integrity introduces
three genuinely new Protocols (its own repositories), each with no pre-existing test double to go stale,
unlike H3's `link_canonical_projection` extension of an *existing* Protocol. H4-I must still run
whole-package `mypy app` before any completion claim (§32) — this finding reduces, but does not eliminate,
that obligation.

## 32. Whole-package verification requirement (binding, carries forward §3 of the governing prompt as
permanent doctrine)

H4-I's frozen completion criteria **must** include, before any VM phase, not discovered there for the
first time:

```
cd backend && python3 -m mypy app                      (whole package, exact CI scope, not AA-scoped)
cd backend && python3 -m black --check . && isort --check-only . && ruff check .   (exact CI commands)
full backend regression, real PostgreSQL, correct CTEC_DATABASE_URL + CTEC_TEST_DATABASE_URL
architecture tests (test_runtime_architecture.py in full)
migration round-trip 114 -> 120 -> 114 -> 120, real PostgreSQL
fresh --no-cache Docker build (backend + frontend) + fresh compose runtime + full crown proof (§28)
```

Any H4-caused unexplained failure in any of the above: STOP, narrow governance correction, exactly the
OQI-H3-VM-R1 precedent — never opportunistic repair of an unauthorized path.

## 33. API / Frontend impact (binding)

**Zero new API routes.** Generic Finding-detail/downstream APIs already render Findings by
`finding_type`/`status` without a closed dimension enum at the schema layer (confirmed directly, H3's own
precedent: `FindingDetailResponse`'s `dimension: str` field is unconstrained). **Frontend**: no closed
dimension/family map was found in this phase's search that would need correction beyond the already-
disclosed, already-deferred cosmetic label gap from H3 (`frontend/app/quality/findings/page.tsx`'s
family-filter dropdown) — H4-I must independently re-verify this at implementation time and, if a genuine
closed-enum mismatch is found, correct only that narrow label, never absorb a Command Center redesign.

## 34. Seeder honesty (binding)

The seeder (§28) creates only governed prerequisite configuration (cardinality policy row), real tenant
graph data (`EnterpriseEntity`/`InstitutionalRelationship`), and real evidence/ER outcome rows. It **must
not** directly insert Integrity evaluation rows, Integrity Findings, ontology impact conclusions, business
impact conclusions, Reliance conclusions, or remediation resolutions — those must arise through the real
`OqiIntegrityStructuralEvaluationService`/`OqiIntegrityReferenceEvaluationService` exactly as every prior
phase's seeder discipline requires (`SEED DATA ≠ QUALITY CONCLUSION`, restated here as binding).

## 35. Explicit deferrals (binding — unchanged from H4-DR §BK, restated)

Production evaluator orchestration/scheduling; tenant-private Reference Evidence datasets; tenant
CanonicalStandard overrides; fuzzy canonicalization; semantic/unit conversion; autonomous remediation;
`CREATE_RELATIONSHIP`/`DELETE_RELATIONSHIP`/`RESOLVE_ENTITY` action types; broad graph mutation API; broad
`RelationshipRequirement` CRUD API; a `CONDITIONAL`-obligation applicability engine; broad relationship-
evidence provenance redesign; broad temporal graph redesign; OQI Command Center redesign; the inherited
frontend Docker HEALTHCHECK false-negative (proven pre-existing, H3-VM); generic FK→HTTP-500 correction;
the local `docs/product/` allowlist condition; unrelated Reference-Evidence CI scope debt; unrelated
`QualityRule`-configure wiring. None may be absorbed merely because a touched file is nearby.

## 36. H4-I STOP conditions (binding, twenty-one, restated from the governing prompt §47 with confirmation
of resolution status for each)

```
1.  RelationshipRequirement cannot serve as the real governed anchor        RESOLVED -- confirmed §5-§6
2.  Cardinality requires duplicating source/relationship/target semantics    RESOLVED -- §7 is purely
                                                                               additive, FK-anchored only
3.  Qualifying relationship cannot be determined deterministically           RESOLVED -- §10.1 exact
4.  Distinct-target cardinality cannot be implemented correctly              RESOLVED -- §10.1 COUNT DISTINCT
5.  UNRESOLVED cannot be tied to the exact reference evidence evaluated      RESOLVED -- §10.2, at ER's own
                                                                               real granularity (source_
                                                                               object_id), disclosed exactly
6.  Integrity must invoke ER matching to establish orphan state              RESOLVED -- §10.2, read-only
7.  ORPHAN_REFERENCE requires guessing a target                              RESOLVED -- never; no target
                                                                               is ever asserted for an orphan
8.  Structural/Reference subjects cannot be persisted without dishonest
    provenance                                                                RESOLVED -- §11, Option B
9.  QualityFindingOrigin requires a major redesign beyond one additive
    branch                                                                    RESOLVED -- §19, dataclass
                                                                               unchanged
10. OQI4 requires a fabricated target for orphan impact                      RESOLVED -- §20, IMPACT_
                                                                               UNKNOWN is the honest fallback
11. H1 coverage cannot honestly incorporate Integrity                        RESOLVED -- §24
12. OQI6 cannot consume the new storage family without redefining Reliance   RESOLVED -- §22, one new
                                                                               UNION branch, zero Reliance
                                                                               redefinition
13. Remediation requires autonomous graph mutation                           RESOLVED -- §25, investigation-
                                                                               only
14. Tenant isolation cannot be DB/service enforced                           RESOLVED -- §27, RFC-016 reuse
15. FieldValueEvidence must be mutated                                       RESOLVED -- never touched
16. H1/H2/H3 semantics must change                                           RESOLVED -- §29, zero shared
                                                                               mutable state
17. Actual seeded crown cannot be built using real governed machinery        RESOLVED -- §28, confirmed
                                                                               against real seed source
18. Exact migration/table-count assumptions are false                        Verify fresh at H4-I (§13/§23
                                                                               are this document's best
                                                                               verified estimate; if real
                                                                               PostgreSQL contradicts them,
                                                                               STOP for a narrow amendment,
                                                                               exactly the H3-I-R1 precedent)
19. Whole-package mypy reveals a required path outside this Authorization    STOP, narrow governance
                                                                               correction (H3-VM-R1 precedent)
20. Full regression reveals a required path outside this Authorization       STOP, same precedent
21. Docker reveals a material architecture prerequisite outside frozen
    scope                                                                     STOP, same precedent
```

Eighteen of twenty-one are resolved by this document's own discovery; three (18-19-20-21, effectively the
same discipline) remain live STOP conditions **by design** — this document freezes architecture, it cannot
freeze what real PostgreSQL/whole-package mypy/Docker will say until H4-I actually runs them, and per §3 of
the governing prompt, H4-I must run them **before** claiming completion, not discover gaps at H4-VM.

## 37. Authorization

This CDD is approved for publication as the frozen, implementation-ready architecture for OQI-H4 Integrity,
following the discovery (OQI-H4-DR), Product Owner decision (PO-H4-01 through PO-H4-05), and governance
resolution (this document) sequence. CDD-039 through CDD-049 and all their Artifact Authorizations and
amendments remain FROZEN and unmodified. No implementation is authorized by this document alone — a
companion, exact Artifact Authorization (`CDD-050-OQI-H4-Governed-Integrity-Artifact-Authorization.md`) is
required and published alongside it; implementation against that Authorization's exact path list is
authorized only after both documents' publication and hash computation.
