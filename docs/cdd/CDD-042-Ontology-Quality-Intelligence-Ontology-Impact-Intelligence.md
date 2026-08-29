# CDD-042 — Ontology Quality Intelligence: Ontology Impact Intelligence (OQI4)

**Status:** FROZEN
**Version:** 1.0
**Governs:** OQI4 — the deterministic layer connecting governed Quality Findings (OQI1/OQI2/OQI3) to the specific ontology knowledge they affect, and to further ontology knowledge reached only through explicitly governed relationship propagation.
**Predecessor closure:** OQI1 (CDD-039), OQI2 (CDD-040 + amendments), OQI3 (CDD-041 + amendments), all CLOSED. OQI3 authoritative merge: `0ddfdf29466538be6caf132d621a0833391e9f2c`.
**Discovery/resolution basis:** OQI4-DR (architecture discovery, Product-Owner-approved with the derive-before-persist refinement) and this OQI4-G lineage-derivation proof, conducted against the actual repository — not against DR's earlier hypothetical schema.

## 1. Purpose

OQI1–OQI3 answer: *what quality condition exists in the governed evidence?* OQI4 answers: *what knowledge represented by the ontology is affected by that quality condition, on what governed basis, and by what deterministic evidence chain?*

A Finding is not automatically an ontology impact. OQI4 exists to make that connection explicit, provable, and — where it cannot be proven — honestly unknown rather than guessed.

## 2. Canonical terminology

- **Ontology Impact** — a deterministic, governed conclusion that a specific ontology element (`EnterpriseEntity` or `InstitutionalRelationship`) is affected by a Quality Finding.
- **Direct Impact** — impact established by governed lineage from the Finding's own evidence to a specific ontology element's identity.
- **Propagated Impact** — impact established by traversing governed, explicitly-enrolled relationship semantics from a directly-impacted element.
- **Impact Basis** — the closed, named reason a specific impact row exists.
- **Impact Evaluation** — one immutable, deterministic execution of OQI4 against one Finding state, at one moment, against one coherent ontology snapshot.
- **Current Ontology Impact** — the mutable current-state projection of the latest relevant Impact Evaluation for one (Finding, ontology element, impact kind) triple.

## 3. Primary invariants (unchanged from OQI4-DR, reaffirmed)

1. A Finding is not automatically an ontology impact — impact requires governed, deterministic lineage.
2. Ontology impact is not business impact. OQI4 never computes severity, criticality, monetary exposure, or trust. That is OQI6.
3. Graph reachability is not automatically impact. Propagation requires an explicit, ACTIVE, versioned `ImpactPropagationPolicy` enrollment for the specific relationship type and direction. **Deny by default.**
4. AI does not determine ontology impact. OQI4 is fully deterministic and reproducible. OQI5 agents may reason over OQI4's facts later; they never become the source of those facts.
5. Majority is not truth. OQI2's preserved disagreement/missingness is never collapsed into a canonical ontology value by OQI4.
6. Source authority is not truth. An authoritative-source designation is participant metadata, never converted into an ontology fact by OQI4.
7. `IMPACT_UNKNOWN` is a first-class, permanent, legitimate outcome — never manufactured away, never confused with `NO_IMPACT`.

## 4. Lineage derivation proof (release-critical — this section is the crux of OQI4-G)

The mandate governing this phase was explicit: **derive before persist** — reuse existing immutable provenance before creating new provenance; if deterministic lineage cannot be proven from existing governed facts, persist only the smallest missing governed fact required; never build a bridge table or a generalized lineage platform by default.

The chain investigated, read from the actual current repository (not from DR's earlier hypothesis):

```
FieldValueEvidence → SourceField → SemanticMapping → EnterpriseEntityResolutionRecord → EnterpriseEntity → Assertion
```

### 4.1 FieldValueEvidence → SourceField

**DIRECT FK.** `FieldValueEvidenceORM.source_field_id` is a non-nullable FK to `source_fields.source_field_id` (CDD-022). `source_record_reference` carries the record-level lineage identity already reused verbatim by OQI1/OQI2/OQI3. Tenant is resolved transitively through `SourceField → SourceObject.tenant_id` (evidence itself carries no `tenant_id` column, by design — CDD-022 §6/§25). Fully deterministic.

### 4.2 SourceField → SemanticMapping

**GOVERNED VERSIONED MAPPING, schema-level only.** `SemanticMappingORM` is a direct `source_field_id ↔ information_element_requirement_id` correspondence (CDD-019), Approved-lifecycle-partial-unique-indexed to at most one Approved mapping per `source_field_id`. This proves *which Blueprint semantic concept a field's evidence is meant to satisfy at the class/type level* — it does **not** reference any specific `EnterpriseEntity` instance, and it does not reference `Knowledge`/`Assertion` identity at all (see §4.4). Deterministic at the schema level; **does not, by itself, reach instance or attribute level.**

### 4.3 SourceObject → EnterpriseEntity (instance-level resolution)

**DERIVABLE THROUGH EXISTING FACTS — real, live, governed.** `EnterpriseEntityResolutionRecordModel` (`app/domain/identity_resolution`) is a genuine production pipeline, not demo-only: tenant-qualified composite FK to `enterprise_entities`, a `ResolutionOutcome` closed enum (`RESOLVED`, `POSSIBLE`, `UNRESOLVED`, `BLOCKED_CONFLICT` — only `RESOLVED` requires `enterprise_entity_id`), `supporting_source_object_ids` (JSON array, tenant-consistency application-enforced and proven by test — `EntityResolutionStore`), and an append-only history chain (`EnterpriseEntityResolutionHistoryModel`) giving deterministic "latest record" semantics per tenant. Verified live via `entity_resolution_steward_api.py` and multiple real-Postgres concurrency/tenant-isolation/full-stack tests. **This link is real, governed, and requires zero new persistence.**

### 4.4 EnterpriseEntity → Assertion (attribute/relationship-claim level)

**MISSING — as a live pipeline, not as a schema gap.** `Assertion.predicate` (String(100), free text) and `Assertion.knowledge_id` (nullable FK to `knowledges.knowledge_id`) both exist as schema, but:

- `Assertion.knowledge_id` and `SemanticMapping.information_element_requirement_id` are **two disjoint identity spaces** — nothing in the repository joins `InformationElementRequirement` to `Knowledge`. A predicate-string-to-`element_name`-string match would be exactly the free-text collision risk this governance forbids relying on.
- Mechanically verified (grep across all production code): **the only code path in the entire repository that constructs an `Assertion` ORM row is `demo_gate_f_seeder.py`** — a static demo/seed generator. Its `_assert_literal()` helper sets `source_object_id=None` unconditionally and never sets `knowledge_id`. `AssertionRepository` is a generic persistence-only CRUD shell with "do not add business logic" as its own file header.
- **Conclusion: there is no live, evidence-driven process anywhere in this codebase today that creates or updates `Assertion` rows from real `FieldValueEvidence`.** This is not "one narrow missing relationship" fixable by a single new FK or bridge table — persisting such a fact would require *also* building the live assertion-authoring pipeline itself (deciding, from real evidence, when and how an `Assertion` should be created/superseded), which is ontology/assertion-authoring write authority. Per this phase's own instruction (§136 of the governing prompt), OQI4 must not casually absorb that authority.

### 4.5 Derivation test results

| Finding family | Entity-identity-level (§4.3 chain) | Attribute/assertion-level (§4.4 chain) |
|---|---|---|
| OQI1 completeness | **FULLY PROVABLE** (Finding carries `SourceRecordLineageIdentity` → resolvable) | NOT PROVABLE (no live Assertion pipeline) |
| OQI1 validity | **FULLY PROVABLE** (same chain) | NOT PROVABLE |
| OQI3 BusinessRule (incl. compound) | **FULLY PROVABLE** — resolves via the Finding's own `subject_identity` (`source_object_id` + `source_record_reference`, persisted since OQI3-I2-R). Compound clause-level distinction (predicate/consequence/condition-subject evidence) does **not** change which ontology element receives Direct Impact at this granularity — there is exactly one subject entity per Finding regardless of how many clauses failed. | NOT PROVABLE |
| OQI2 N-source consistency | **PARTIALLY PROVABLE** — see §4.6 | NOT PROVABLE |

### 4.6 OQI2 special case

An OQI2 Finding's comparison subject has multiple participant `SourceObject`s (one per source system), each independently resolvable via §4.3. If all participants that resolve, resolve to the **same** `EnterpriseEntity`, that entity is `IMPACTED`. If participants resolve to **different** entities, OQI4 must never pick one (that would be exactly the majority/authority-as-truth violation this governance forbids) — the result is `IMPACT_UNKNOWN` with the disagreement recorded as an observation. If no participant resolves, `IMPACT_UNKNOWN`.

### 4.7 LINEAGE GAP VERDICT

**A — for the scope this governance authorizes.** Entity-identity-level Direct Impact requires **zero new lineage persistence** — it is fully derivable today from `EnterpriseEntityResolutionRecordModel` alone. Attribute/assertion-level Direct Impact is **permanently and explicitly out of OQI4's scope** — not a temporary implementation gap awaiting a future extension inside OQI4, but a structural non-claim, because the live evidence-to-Assertion authoring pipeline does not exist and creating it is a separate capability layer's responsibility, not OQI4's. `IMPACT_UNKNOWN` is the correct, permanent answer for any impact question that would require attribute-level lineage. This is not a defect — it is `IMPACT_UNKNOWN` doing exactly the epistemic job it exists to do.

**New lineage tables authorized: 0. No bridge table. No generalized lineage platform. No speculative relationship lineage.**

## 5. Epistemic vocabulary (closed, 3-value)

```
IMPACTED
NO_IMPACT
IMPACT_UNKNOWN
```

- **IMPACTED**: governed lineage deterministically proves the element is affected.
- **NO_IMPACT**: governed lineage deterministically proves the element is *not* affected — a positive fact, not an absence of a join result. The only frozen NO_IMPACT basis in this initial scope: the latest resolution record for the Finding's SourceObject has outcome `UNRESOLVED` or `BLOCKED_CONFLICT` (CTEC has positively evaluated the evidence and found no current entity claim).
- **IMPACT_UNKNOWN**: no resolution record exists for the SourceObject at all, or its outcome is `POSSIBLE` (not yet settled), or (OQI2) participants resolve to conflicting entities, or the question requires attribute-level lineage (§4.7).

## 6. Direct Impact — final definition

> Direct Ontology Impact exists only when a governed `EnterpriseEntityResolutionRecord` deterministically proves — via `RESOLVED` outcome and a non-null `enterprise_entity_id` — that the Finding's affected `SourceObject` lineage establishes the identity of a specific `EnterpriseEntity`.

Direct Impact is **not**: same entity type therefore impacted; coincidental predicate/string match; graph-neighbor reachability; AI inference; attribute-level in this initial scope (§4.7).

Basis (closed): `DIRECT_ENTITY_IDENTITY_LINEAGE`.

## 7. Propagated Impact — final definition

> An `EnterpriseEntity` or `InstitutionalRelationship` is Propagated-Impacted when it is reached from a directly-impacted `EnterpriseEntity` through one or more `institutional_relationships` edges whose `relationship_type_id` is enrolled, in the traversed direction, in an ACTIVE `ImpactPropagationPolicy` version for that tenant.

Basis (closed): `GOVERNED_RELATIONSHIP_PROPAGATION`.

**Ontology element taxonomy (closed):** `ENTITY`, `RELATIONSHIP`. No `ASSERTION` element type in this scope (§4.7 — Assertions carry no live evidence-linked graph data today).

**Impact class (closed):** `DIRECT`, `PROPAGATED`. No `CRITICAL`/`HIGH`/`MEDIUM`/`LOW` — that is OQI6's territory.

## 8. ImpactPropagationPolicy — governed, versioned, deny-by-default

A relationship type carries **no** propagation semantics of its own (`relationship_types` is a bare governed name registry — verified by direct read). Propagation authority is therefore a new, first-class OQI4 concept:

```
impact_propagation_policies
  policy_id            UUID PK
  tenant_id            tenant scope
  relationship_type_id FK → relationship_types
  direction             FORWARD | REVERSE | BOTH
  max_depth             integer, policy-governed
  governance_status     Draft | Active | Retired  (reuse existing lifecycle enum pattern)
  version_number, previous_version_id  (immutable-per-version, same discipline as QualityRule/BusinessRule)
```

**Deny-by-default:** if a `relationship_type_id` has no ACTIVE policy enrollment for the traversed direction and tenant, impact never propagates across it. This is a data-governed firewall, not a code branch — auditable, not hard-coded.

**Depth:** each policy carries its own `max_depth`. A global hard safety ceiling of **10** is additionally frozen as a secondary bound (implementation constant, documented, revisable only by governance amendment).

## 9. Single recursive CTE — the graph-snapshot-coherence invariant

OQI3 already proved that multi-statement reads under PostgreSQL READ COMMITTED can construct evidence states that never existed atomically. The identical risk applies to multi-hop graph traversal. OQI4 freezes the equivalent fix up front:

> All mutable ontology facts (institutional relationships, and the ACTIVE propagation-policy rows that gate them) used to derive one Impact Evaluation's propagation result must be read through **one PostgreSQL recursive CTE statement**, obtaining one statement snapshot.

**Explicit resolution of the policy-snapshot question:** ACTIVE policy rows are **not** looked up in a separate pre-query. The recursive CTE's own non-recursive leading term includes a CTE that selects the currently-ACTIVE policy set for the tenant, and the recursive term joins `institutional_relationships` against that same in-statement policy CTE. This closes the exact torn-snapshot risk a separate policy lookup would reopen.

**Tenant filtering:** `tenant_id` is re-applied at the anchor **and every recursive step** — not only at the seed.

**Cycle safety:** the recursive term carries a `path` array of visited `enterprise_entity_id`s; recursion for a branch terminates the instant a node would re-enter its own path. Deterministic termination, no heuristic depth guess needed for cycle safety specifically (the depth cap in §8 is a separate, additional bound).

**Multiple paths:** one `CurrentOntologyImpact` row per impacted element regardless of path count (§11's identity excludes path). Path *evidence* is deduplicated by node-set and capped at the **shortest 3 distinct paths** per element per evaluation (frozen governed constant — bounded, not "every path," not "first found").

## 10. Finding-family integration

OQI1/OQI2/OQI3 Findings are three deliberately disjoint, independently-versioned persistence families with no shared supertype (a repeated, deliberate architectural choice across this session). OQI4 does **not** introduce a common Finding registry or reopen any of the three closed capability layers.

**Adapter:** a plain composite value, never a polymorphic DB FK (Postgres cannot natively express one FK spanning three tables without a shared parent, and creating one would mean reopening all three closed layers):

```
finding_family        closed enum: OQI1 | OQI2 | OQI3
finding_id             the family's own native UUID
finding_state_revision the Finding's own state_revision at evaluation time
```

Referential correctness is enforced at the application boundary (a dedicated per-family lookup + adversarial test), the same precedent already accepted in this codebase for `EnterpriseEntityResolutionRecordModel.supporting_source_object_ids`.

## 11. Persistence model — immutable ledger + mutable current projection

Re-derived (not blindly copied) from the same shape this codebase has now proven correct three times (OQI1/2/3 Evaluation+Finding): immutable audit trail plus a fast, indexed current-state read.

### 11.1 `ontology_impact_evaluations` (immutable)

```
evaluation_id            UUID PK
tenant_id
finding_family, finding_id, finding_state_revision
outcome                  IMPACTED | NO_IMPACT | IMPACT_UNKNOWN
resolution_record_id     nullable FK → enterprise_entity_resolution_records (the exact record used)
traversed_state_digest   canonical digest (see §11.4)
evaluated_at
UNIQUE(tenant_id, finding_family, finding_id, finding_state_revision, traversed_state_digest)
```

**Evaluation identity** = `tenant_id + finding_family + finding_id + finding_state_revision + traversed_state_digest`. Deliberately **excludes** any invented global "ontology version" (§57–§58 of the governing prompt explicitly forbid fabricating one) — reproducibility instead comes from capturing exactly which versioned rows were actually traversed (§11.4).

### 11.2 `ontology_impact_observations` (immutable)

```
evaluation_id, ontology_element_type, ontology_element_id, impact_kind   composite PK
FK → ontology_impact_evaluations
basis      DIRECT_ENTITY_IDENTITY_LINEAGE | GOVERNED_RELATIONSHIP_PROPAGATION
depth      0 for direct; hop count for propagated
```

### 11.3 `ontology_impact_paths` (immutable)

```
evaluation_id, ontology_element_id, path_ordinal   composite PK
FK → ontology_impact_evaluations
institutional_relationship_id  FK
direction
policy_id, policy_version_number   FK → impact_propagation_policies
```

### 11.4 Traversed-state digest

Canonical, sorted, content-addressed over: the resolution record id+outcome used for direct impact; the sorted set of `(institutional_relationship_id, version_number)` pairs actually traversed; the sorted set of `(policy_id, version_number)` pairs actually applied. Row-return order never affects the digest. If any traversed row's version later changes, a replay against the new Finding state naturally produces a new digest and therefore a new immutable Evaluation — old Evaluations remain byte-identical and independently explainable (§4/§64/§65 of the prior OQI phases' own precedent, re-applied here).

### 11.5 `current_ontology_impacts` (mutable projection)

```
current_impact_id   UUID PK
tenant_id, finding_family, finding_id, ontology_element_type, ontology_element_id, impact_kind
UNIQUE(tenant_id, finding_family, finding_id, ontology_element_type, ontology_element_id, impact_kind)
status               ACTIVE | RESOLVED
latest_evaluation_id FK → ontology_impact_evaluations
first_seen_at, last_seen_at
```

**Current-impact identity** deliberately excludes `evaluation_id`, `traversed_state_digest`, policy version, and path (§55 of the governing prompt) — it is condition-level, one row per (Finding, element, kind) triple, exactly mirroring the Finding/Evaluation identity split OQI1–3 already proved. No `occurrence_count`/`reopen_count`/`state_revision` counters are added here — those already belong to the Finding itself; duplicating them on the impact projection would violate minimality without adding correctness.

## 12. Lifecycle interaction

- **Finding OPEN**: evaluate; upsert `current_ontology_impacts` to `ACTIVE` for every element found.
- **Finding RESOLVED**: a closure evaluation runs; prior `ACTIVE` current-impact rows for that Finding transition to `RESOLVED` (never deleted). Historical Evaluations/Observations/Paths are untouched.
- **Finding REOPENED**: a new immutable Evaluation is produced; the same stable `current_ontology_impacts` identity (§11.5) is reactivated to `ACTIVE` where the same element is again affected.
- **Ontology changes while Finding stays OPEN**: a later evaluation may produce a different impact set (different `traversed_state_digest` → new Evaluation). The prior Evaluation remains immutable and independently explainable.
- **Propagation-policy version changes while Finding stays OPEN**: same treatment — new Evaluation, old Evaluation stays bound to its own policy version.
- **SATISFIED vs. NOT_APPLICABLE** (OQI3 resolution_basis): no different ontology-impact behavior is defined — both resolve the current impact projection identically; resolution_basis is not consumed by OQI4 impact logic.

## 13. Failure isolation

OQI4 evaluation failure must never mutate, roll back, or invalidate the underlying OQI1/OQI2/OQI3 Finding — OQI4 owns its own transaction, invoked as a downstream, independently retryable consumer. Infrastructure/database errors fail and roll back the OQI4 operation; they are never mapped to `IMPACT_UNKNOWN` (which is an epistemic domain result, not an error state).

## 14. Concurrency, replay, and why no new advisory-lock seed is required

**Replay:** the immutable Evaluation's natural key (§11.1's UNIQUE constraint) makes replay idempotent via the same parent-gated `INSERT ... ON CONFLICT DO NOTHING RETURNING` pattern this session proved for OQI3's historical replay (CDD-041 G3/I2-R3). A transaction that loses the conflict never writes `Observations`/`Paths`, mirroring OQI3's rule exactly.

**Current-projection concurrency:** only the transaction that won the immutable-Evaluation insert may upsert `current_ontology_impacts`. This is sufficient — a losing transaction simply does nothing further, and the winning transaction's upsert is a plain natural-key upsert with no independent race window. **No new advisory-lock seed is introduced.** Unlike OQI1–3's Finding lifecycle (which must serialize repeated *mutations of counters/state* across genuinely concurrent evaluators), `current_ontology_impacts` has no counters and no reopen/occurrence semantics to race on — its only mutation is "set to the latest evaluation's outcome," which the parent-gated ownership rule already makes safe without a lock.

## 15. Tenant isolation

`tenant_id` is enforced at every boundary: Finding lookup (existing OQI1-3 tenancy), resolution-record lookup, recursive-CTE anchor and every recursive step (§9), propagation-policy lookup, `current_ontology_impacts` lookup, `ontology_impact_paths` lookup. New tables use tenant-qualified composite FKs where the referenced table (e.g. `enterprise_entities`, `institutional_relationships`) already supports them, matching the strongest practical pattern already established in this repository (`enterprise_entity_resolution_records`' own composite FKs). This does not worsen OQI-P3-002 (inherited OQI1-3 evidence tenant debt) — OQI4 introduces no new write path into `field_value_evidence`.

## 16. Firewalls (reaffirmed)

- **OQI1**: `QualityRule`, Evaluation semantics, Finding identity/lifecycle, seed-1 — untouched, read-only consumption only.
- **OQI2**: majority≠truth, authority≠truth preserved exactly; no canonical-value selection; no remediation candidate.
- **OQI3**: `BusinessRule`, closed AST, Kleene semantics, `BusinessRuleFinding` lifecycle, seed-3, atomic evidence frontier — untouched.
- **Gate T**: not redesigned; OQI4 composes with governed evidence/horizon concepts only.
- **Gate V**: no agents in OQI4. OQI4 produces deterministic facts; OQI5 agents reason over them later.
- **Gate S**: no human-approval/remediation authority in OQI4.
- **Gate W**: no API version change.
- **OQI5**: no recommendation, remediation candidate, agent conversation, auto-correction, or source-value selection.
- **OQI6**: no business criticality, monetary impact, severity levels, or trust score. OQI4 preserves the structural facts OQI6 will need.
- **OQI7**: no dashboard, graph coloring, or frontend. OQI4 preserves the truthful, explainable evidence OQI7 will later visualize.

## 17. Downstream consumer contracts

- **OQI5** will consume: Finding identity/revision/evidence, direct+propagated impact sets, path provenance, evaluation identity, current-impact state — all structurally available without OQI4 performing any reasoning itself.
- **OQI6** will consume: which knowledge is affected, direct vs. propagated, how impact propagated, which relationships were involved, current affected-element counts — no severity pre-computed.
- **OQI7** will consume exactly the path-provenance rows to answer, for every highlighted element: which Finding, which evidence, direct or propagated, which exact path, which policy version, when evaluated, current or historical.

## 18. Source-neutrality

No SAP-specific table, Finding model, or propagation logic exists in OQI4 core. SAP ECC concepts (MARA/MARC/MAKT/MBEW/LFA1/LFM1/EKKO/EKPO/MAST/STKO/STPO) are validation examples only, consistent with OQI1–3's own established discipline.

## 19. Capability claim

> OQI4 proves CTEC Ontology Quality Intelligence can deterministically connect governed Quality Findings to the specific ontology entity they identify through explicit source-evidence/entity-resolution lineage, distinguish known impact from known non-impact and unknown impact, and propagate proven direct impact across only explicitly governed, versioned relationship semantics using a coherent single-statement relational graph snapshot — while preserving immutable path provenance and a queryable current-impact projection, and without inventing attribute-level lineage that does not yet exist in this system.

## 20. Explicit non-claims

OQI4 does NOT prove: attribute/assertion-level ontology impact (§4.7 — permanently deferred pending a future live evidence-to-Assertion authoring capability, not OQI4's to build); canonical truth selection; source correction; cross-source BusinessRule evaluation; agent reasoning; remediation; human approval; business criticality; monetary impact; trust score; UI/dashboard; SAP-specific integration; a generalized lineage platform.

## 21. Defect register

```
P0 = 0
P1 = 0
P2 = 0   (the OQI4-DR field-lineage gap is resolved by explicit, permanent, honest scope
          narrowing — §4.7 — not by new persistence; it is not a defect once scoped)
P3 = 7 (inherited 6 unchanged + 1 new)

OQI-P3-001  64-bit advisory-hash collision / harmless over-serialization
OQI-P3-002  residual DB tenant defense-in-depth
OQI-P3-003  explicit correspondence scalability
OQI-P3-004  deferred composite evidence lookup index
OQI-P3-005  inherited historical-replay race in OQI1/OQI2
OQI-P3-006  equal-temporal-key latest-evidence tie ambiguity
OQI-P3-007  no pre-existing relationship types are propagation-eligible (relationship_types
            carries zero propagation metadata today, per §8) -- the first ImpactPropagationPolicy
            row must be authored by a Product Owner/data steward before OQI4-I's traversal has
            any real edge to propagate across; this is an adoption/rollout note, not an
            architecture defect.
```

## 22. Implementation shape

**SINGLE `OQI4-I`.** The one hard correctness question (graph-traversal snapshot coherence) is solved by construction in this document (§9), exactly as OQI3's evidence-frontier problem was eventually solved — but without requiring OQI3's discovery-through-failure cycle, because the entire traversal source is a small, fully relational table set already understood. There is no genuine architectural boundary here forcing a split the way "prove the frontier before building Finding lifecycle" forced OQI3's. No new authority boundary is crossed (§4.7 keeps OQI4 a pure consumer of existing entity-resolution and relationship data).

## 23. Migration

Expected next migration: `0023_oqi4_ontology_impact`, `down_revision = "0022_oqi3_business_rule"`. Not created in this phase — OQI4-I creates it. Pre-OQI4 table count (mechanically verified from `test_persistence_integration.py`): **81**. Post-OQI4 expected count: **86** (5 new tables, §11 and §8).
