# RFC-017 — Gate F Supply Chain Semantic Vocabulary Authorization

Version: 1.0 DRAFT
Status: RELEASE CANDIDATE — PENDING PRODUCT OWNER AUTHORIZATION
Current: NO
Authority: NON-AUTHORITATIVE — PENDING REGISTRY PUBLICATION
Supersedes: — (new authority)
Scope: minimal canonical concept/relationship-type authorization required for
Gate F ("Governed Supply Chain Impact & Mitigation Decision"), plus
retroactive ratification of the pre-existing `SUPPLIER-RISK-ONTOLOGY-V1`
vocabulary it depends on

## 0. Purpose

Gate F F1 Architecture Decision Analysis found that the ontology vocabulary
currently seeded under the code constant `SUPPLIER-RISK-ONTOLOGY-V1`
(`backend/app/infrastructure/persistence/ontology_seed.py`) — 10 concepts and
7 relationship types — was introduced by a single engineering commit
(`8887b93`, "Increment 2A: Ontology Studio backend foundation", 2026-08-12)
that cites no CDD, RFC, or PAD authority, and in fact predates RFC-016 and
PAD-001 (both authorized 2026-08-15). The Product Owner's Gate F F1 decision
record rejected CDD-only authority for new canonical vocabulary and rejected
using that ungoverned precedent to justify further silent additions. This RFC
is the explicit authorization Increment 2A never obtained, scoped to exactly
what Gate F requires — nothing broader.

This RFC does not authorize any traversal engine, decision logic, API, scope,
persistence table, or frontend capability. Those remain governed separately
by the accompanying proposed PAD-003 and CDD-015 (see §8, Non-claims).

## 1. What Gate F reuses without change

Gate F's business chain — Supplier → Material → Product/BOM → Facility →
Revenue Exposure → Alternate Supplier → Mitigation Recommendation — maps onto
the *existing* canonical vocabulary as follows. No change is proposed to any
of the following:

**Concepts** (`ontology_seed.py:38-49`, all already `Approved`/`Active`):
`Supplier`, `Material`, `BOM`, `Product`, `Facility`, `Region`, `Contract`,
`Risk Event`, `Revenue Exposure`, `Alternate Supplier`. All ten Gate F
business-flow nodes already exist as governed concepts — Gate F requires zero
new concepts.

**Relationship types** (`ontology_seed.py:54-61`):

| Existing type | Direction | Reused for |
|---|---|---|
| `supplies` | Supplier → Material | Material Dependency step |
| `usedIn` | Material → BOM | Product/BOM Dependency step |
| `defines` | BOM → Product | Product/BOM Dependency step |
| `generatesRevenue` | Product → Revenue Exposure | Revenue Exposure step — see §2, Decision 6 note |
| `locatedIn` | Supplier → Region | Risk + Evidence step |
| `exposedTo` | Region → Risk Event | Risk + Evidence step |

Revenue exposure (Gate F F1 Decision 6, Product Owner-approved): Gate F MUST
NOT introduce a generalized revenue-aggregation mechanism. The existing
`generatesRevenue` (Product → Revenue Exposure) edge is sufficient to
represent revenue exposure as "a governed business fact associated with the
affected business context," exactly as the Product Owner's decision requires.
No new relationship type is needed for revenue exposure.

## 2. Contract vs. Supply Agreement (Product Owner F1 Decision 7)

**Finding**: `Contract` is already a governed concept —
*"A binding agreement governing the terms of a supplier relationship"*
(`ontology_seed.py:45`) — with an existing `boundBy` (Supplier → Contract)
edge. The non-authoritative frontend behavioral prototype
(`frontend/lib/demo/scenario-facts.ts:125-126`,
`frontend/app/_components/architecture/sample-relationships.ts:26`) uses a
distinct label, "Supply Agreement," for a Material-to-agreement relationship
("Material → Supply Agreement (COVERED_BY)"), but defines no distinct
business semantics from a Contract that happens to cover specific materials.

**Resolution**: per Decision 7, existing `Contract` is REUSED. No new
"Supply Agreement" concept is authorized or required. What is missing is not
a concept but a *relationship* — nothing today connects `Material` to
`Contract` (`boundBy` only connects Supplier to Contract). §3b closes this
gap by adding one new relationship type, using the existing `Contract`
concept unchanged.

## 3. New relationship-type authorization (the only new canonical vocabulary this RFC adds)

Three relationship-type gaps prevent Gate F's business chain from being
representable in the existing vocabulary. Each is authorized here as a new
row in the existing `relationship_types` reference table (RFC-010/CDD-003
lineage — see §5) — no new table, no new concept, no new entity type.

### 3a. `assembledAt` (Product → Facility)

Represents the Facility Exposure step (which facility depends on a given
product). No existing relationship type connects Product to Facility. Naming
follows the frontend behavioral prototype's existing terminology
("ASSEMBLED_AT", `frontend/lib/demo/mapping-definitions.ts:78`) for
consistency with the already-reviewed UX/business-fact reference material —
reused as a naming convention only; the prototype carries no architectural
authority (Gate F F1 §4, F0 §5).

Curated definition (MVP-curated metadata, same non-database-governed status
as all other `ontology_seed.py` definitions — see §6): *"The Facility at
which a Product is assembled or produced."*

### 3b. `coveredBy` (Material → Contract)

Represents the Material Dependency step's link to sourcing-agreement terms
(what the prototype calls "Supply Agreement" — see §2). Reuses the existing
`Contract` concept; adds only the missing edge direction.

Curated definition: *"The Contract whose terms govern the sourcing of a
Material."*

### 3c. `candidateFor` (Alternate Supplier → Material)

Represents the Alternative Supplier step: which Materials a given Alternate
Supplier is being evaluated as a candidate to cover. This is deliberately
**not** a reuse of `supplies` (Supplier → Material): `supplies` represents an
actual, current sourcing relationship; `candidateFor` represents a
not-yet-active candidacy under evaluation, which Gate F's qualification,
capacity, lead-time, and cost evaluation (governed by CDD-015, not this RFC)
operates over. Conflating the two would make an evaluated-but-unqualified
candidate indistinguishable from an actual live source of supply.

Curated definition: *"An Alternate Supplier's candidacy to cover a Material,
pending qualification, capacity, lead-time, and cost evaluation."*

This RFC authorizes only the relationship type itself. The contextual
qualification/capacity/lead-time/cost facts evaluated for a given
`candidateFor` instance are attached to that specific
`institutional_relationships` row via the existing
`institutional_relationship_assertions` junction table, governed entirely by
CDD-015 (§9), not by this RFC — this RFC does not authorize, and takes no
position on, how those contextual facts are persisted or associated.

## 4. Institutional Relationship mechanism (unchanged)

All three new relationship types (§3) are instantiated exclusively through
the existing `institutional_relationships` table, using the existing
`relationship_type_id` foreign-key mechanism RFC-016 already authorizes, with
tenant ownership inherited unchanged from RFC-016 §2b
(`tenant_id` originates only from `TrustedPrincipal.tenant_id` →
`AuthorityContext.organization_id`, never from client input). This RFC adds
no new relationship *mechanism* — only new taxonomy values within the
mechanism RFC-015/RFC-016 already govern. The Universal Relationship
Principle / GMR-032 (`ECOM_Physical_Data_Model_v1_7.sql:1003-1010` — no direct
FK for Enterprise-Entity-to-Enterprise-Entity relationships) is fully
respected: no FK column is added anywhere by this RFC.

## 5. Physical schema / canonical entity/attribute impact

**No physical schema change is required.** `entity_types`, `relationship_types`,
and `institutional_concepts` already exist as tables (RFC-010/CDD-003
lineage, confirmed structurally unchanged since ECOM Physical Data Model
v1.3). This RFC authorizes new **data rows** in `relationship_types` (§3). No
canonical entity is added (all ten concepts in §1 already exist); no
canonical attribute is added or changed on any existing entity.

**RFC-010 primary-text verification (F2.1, closes the F2 evidentiary
caveat)**: RFC-010 ("Canonical Enterprise Ontology Boundary," v1.0, FROZEN,
`architecture/released/v1.1/` and `v1.2/`) was read directly, read-only
(extracted from its `.docx` primary text; no repository file was altered or
added — see the Gate F F2.1 report for method). §4 ("Canonical Enterprise
Ontology") lists "Relationship Type" as one of seven Foundation-package
entities, alongside Institutional Concept and Entity Type — confirming
RFC-016 §1a's characterization directly, not merely by inference from
RFC-016's quotation of it. §10 ("Architectural Constraints") states,
verbatim: *"Cognitive capabilities shall not introduce canonical entities,
attributes, relationships or lifecycle changes. Such changes require a new
RFC and updates to the Logical Model, Physical Model and EAD-001."* This is
a **direct, explicit requirement** that new canonical relationship types be
authorized by RFC — stronger confirmation than this RFC's earlier
"lightweight reference-table" framing suggested, not weaker. This RFC's use
of RFC-level authorization for §3's three new relationship types, and for
§6's ratification, is therefore fully and directly supported by RFC-010's
primary text, with no remaining evidentiary gap.

**Gate F F2.2 — Logical Model, Physical Model, and EAD-001 compliance
determination (resolves the F2.1 residual item, honoring RFC-010 §10
literally per the Product Owner's F2.2 Decision A — no artifact is silently
skipped).**

- **Physical Model — no update required, directly evidenced.**
  `architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql` defines the
  `relationship_types` TABLE structure only; it contains zero `INSERT`
  statements for any relationship-type or entity-type VALUE (confirmed by
  direct inspection — no seed data of any kind appears in this file for
  `relationship_types`, `entity_types`, or `institutional_concepts`). Seed
  values are exclusively application-level (`ontology_seed.py`). Because
  RFC-017 §3/§6 add and ratify DATA ROWS only — no new column, no new table,
  no structural change — there is nothing in the Physical Model artifact for
  this RFC to update. This is not an inference from RFC-016's language; it
  is direct inspection of the current authoritative Physical Model file.
- **EAD-001 — no update required, directly evidenced.** The current EAD-001
  traceability artifact (`docs/persistence/traceability/EAD-001-v1.7.json`)
  was read directly: every entry is one row per (Entity, Attribute Name)
  pair — e.g. `Enterprise.enterprise_id`, `Enterprise.enterprise_name` — i.e.
  column/attribute-level metadata. It contains no entries representing
  taxonomy *values* (no row for "supplies" or "boundBy" as a value of
  `Relationship Type`), even though "Institutional Concept" itself has
  attribute-level entries. RFC-017 changes no attribute/column on any
  entity, so EAD-001 requires no update. (Note, for completeness, not
  decision-relevant: the formally INDEX.md-registered "EAD-001" document —
  `architecture/released/v1.2/EAD-001_Enterprise_Attribute_Dictionary_v1_3.xlsx`,
  registered DEVELOPMENT/NON-AUTHORITATIVE, `architecture/INDEX.md:103` — is
  a different, stale artifact from the JSON traceability lineage RFC-015/016
  actually updated as their "EAD-001." This is a pre-existing inconsistency
  in how "EAD-001" is tracked, predating Gate F; this RFC follows the
  JSON-traceability lineage precedent RFC-015/016 actually used, and does
  not attempt to resolve the inconsistency, which is out of Gate F's scope.)
- **Logical Model — no update possible or required, directly evidenced, and
  explicitly recorded rather than silently skipped.** `architecture/INDEX.md:102`
  registers "ECOM Logical Data Model | 1.3 | DEVELOPMENT | NO |
  NON-AUTHORITATIVE." **No authoritative Logical Model exists in this
  repository at all.** RFC-010 §10 requires updating "the Logical Model" as
  an authoritative artifact; there being none, this RFC cannot update what
  does not authoritatively exist, and does not attempt to. This is not a
  gap RFC-017 introduces: RFC-015 and RFC-016 (`architecture/released/v1.8/RFC-015...md`,
  `architecture/released/v1.9/RFC-016...md`) — both read directly — list
  their governed artifacts explicitly (§"Governed artifacts" in each) and
  **neither lists any Logical Model file**, for the same reason, though
  neither RFC stated that reason explicitly. This RFC does what its two
  predecessors did not: it explicitly records why the Logical Model
  obligation is inapplicable, rather than silently omitting mention of it.
- **The correlation-persistence extension separately authorized under
  CDD-015** (a new, noncanonical `decision_evaluations` table — see CDD-015
  §16-17) similarly requires no Physical Model, EAD-001, or Logical Model
  update, on independent grounds: `decision_evaluation_records` and
  `governance_evaluation_records` — the tables it is a direct peer to —
  were themselves never added to the Physical Model SQL or to EAD-001 when
  they were created under CDD-008/CDD-009, confirming this class of
  noncanonical runtime/decision persistence artifact sits outside the
  boundary RFC-010 §10 governs in practice, not just in this RFC's
  argument. This is CDD-015's determination, cited here only for
  completeness; RFC-017 does not authorize the persistence extension (see
  CDD-015 §17's canonical-vs-runtime distinction).

With this direct evidence, no residual uncertainty remains for RFC-017's
own scope. The only remaining pre-existing inconsistency (the stale
INDEX.md-registered EAD-001 v1.3 vs. the JSON traceability lineage) is noted
for completeness and is explicitly out of scope for Gate F to resolve.

## 6. SUPPLIER-RISK-ONTOLOGY-V1 governance-trail resolution

Per Gate F F1 Decision 5 (§9), the Product Owner's Gate F F1 instruction not
to treat that precedent as justification for new vocabulary, and the Product
Owner's Gate F F2.1 Decision B (approved narrowly): this RFC does not rely
on Increment 2A as authority for anything, and does not claim Increment 2A
was properly governed. RFC-010 §10 (verified above) states plainly that
"cognitive capabilities shall not introduce canonical entities, attributes,
relationships or lifecycle changes" without a new RFC — Increment 2A's
commit (`8887b93`, 2026-08-12, three days before RFC-016/PAD-001 were even
authorized) did exactly what §10 prohibits, without the RFC §10 requires.
This was not merely an undocumented process gap; it was a specific,
identifiable action inconsistent with an already-standing constitutional
constraint.

This RFC prospectively/formally authorizes, from the Gate F architecture
release forward only, exactly and only the ten concepts and seven
relationship types enumerated in §1 — no more — exactly as currently
implemented in `ontology_seed.py` (no renaming, no redefinition, no behavior
change). **This is not a blanket ratification of historical ontology
content, Increment 2A's commit, or any other content that commit or any
other ungoverned change may have introduced beyond the specific items listed
in §1.** Any other vocabulary Increment 2A or any later ungoverned change may
have touched, if any exists outside the ten concepts/seven relationship
types identified by F0/F1/F2 as Gate F's semantic foundation, remains
unratified and outside this RFC's scope — a separate governance question,
not resolved here. This ratification is retroactive-in-effect only for the
listed items; it does not assert that Increment 2A's original introduction
of them was properly governed at the time, and it does not ratify any
process used to introduce them (see §8).

The curated concept/relationship definitions remain MVP-curated metadata, not
a database-governed field (the physical model carries no free-text
definition column on `entity_types`/`relationship_types` — `ontology_seed.py:8-13`).
This RFC does not change that status; it authorizes the *existence and
semantic meaning* of the values, consistent with how RFC-016 authorized
Institutional Relationship's canonical status without altering its physical
representation.

## 7. Tenant-ownership implications

None. §3's new relationship types are taxonomy/reference data
(`relationship_types` rows), which — per RFC-015 §1 and RFC-016 §1b — are
explicitly **not** tenant-scoped, unlike instance data
(`institutional_relationships` rows that use these types, which are already
tenant-scoped under RFC-016 §2b). This RFC introduces no new tenant-ownership
surface.

## 8. Non-claims

This RFC does not authorize: any API, traversal-engine behavior beyond what
PAD-001 already permits, DRM/GRM policy or recommendation logic, any new
access scope, any new persistence table, any frontend behavior, any
retirement of the frontend behavioral prototype, any human-approval
workflow, or any of the protected future platform capabilities (Supply Chain
Blueprint, Source-to-Blueprint Semantic Mapping, Profiling + Gap Engine, Gap
Impact + Remediation Engine, Decision Requirements, Decision Readiness). It
does not ratify the *process* by which Increment 2A introduced the
pre-existing vocabulary — only the resulting values, on this RFC's own
authority, going forward (§6). It authorizes exactly: ten pre-existing
concepts (ratified, unchanged), seven pre-existing relationship types
(ratified, unchanged), and three new relationship types (§3) — nothing else.

## 9. Authorization

**RELEASE CANDIDATE — PENDING PRODUCT OWNER AUTHORIZATION.** This RFC has
passed Gate F F3 architecture consistency and dependency verification (see
`GATE-F-ARCHITECTURE-CONSISTENCY-REPORT_RELEASE_CANDIDATE.md`) but remains
non-authoritative. It requires explicit Product Owner authorization before
any implementation may reference it, and before `architecture/INDEX.md` may
be updated to register it.
