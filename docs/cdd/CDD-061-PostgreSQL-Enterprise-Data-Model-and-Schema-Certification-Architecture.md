# CDD-061 — PostgreSQL Enterprise Data Model & Schema Certification Architecture

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN (Discovery + Governance only — no implementation performed by this
document)
Phase: POSTGRES-DATA-MODEL-CLOSURE-DG
Classification: PRODUCT-WIDE PERSISTENCE INTEGRITY CLOSURE GATE (cross-cutting; not owned by any single
capability's own CDD lineage)

## 1. Purpose / Scope

This is the persistence-layer closure gate that must complete before Product-Wide Docker Closure (Step 14,
currently paused on branch `product-wide-docker-closure/step-13`) resumes. It independently reconstructs,
adversarially inspects, and governs the complete Noetva PostgreSQL schema — 126 application tables at
Alembic head `0045_oqi_connector_ingestion` — to answer: **does PostgreSQL itself enforce a coherent,
tenant-safe, relationally correct, migration-consistent persistence model**, not merely "do 126 tables
exist."

## 2. Authoritative baseline

```
local origin/main:  0fd3886ea0947c60897def30ba59bc2430fd43db
GitHub main:        0fd3886ea0947c60897def30ba59bc2430fd43db
```

Equal, matches the expected post-REAL-ENTERPRISE-INGESTION baseline. No drift. Branch
`postgres-data-model-closure/step-13` created fresh from `origin/main` (not from the paused
`product-wide-docker-closure/step-13` branch; CDD-060's Step-14 document was neither read for governance
content nor cherry-picked — confirmed absent from this branch before this document was authored). The
paused Step-14 branch was not modified.

**CDD numbering collision, disclosed and resolved (POSTGRES-DATA-MODEL-CLOSURE-G-R1)**: this document was
originally authored as `CDD-060` (the highest number on `main` at authoring time was `CDD-059`). The paused
Step-14 branch (`product-wide-docker-closure/step-13`) had already, chronologically first (commit
`a46096b`, 2026-09-05 10:44:21-07:00, versus this document's original commit `d729e29` at
2026-09-05 11:14:33-07:00), authored its own, different `CDD-060` document
(`CDD-060-Product-Wide-Docker-Closure-Architecture-and-Verification-Contract.md`) against the same
baseline. A dedicated governance-correction phase (POSTGRES-DATA-MODEL-CLOSURE-G-R1) independently verified
this collision, confirmed Step-14's `CDD-060` has chronological precedence and is preserved unchanged, and
renumbered this document to `CDD-061` — the next valid, unused identifier, independently confirmed absent
from `main`, from every remote branch, and from this document's own prior text. No substantive content
changed as part of this renumbering; only this document's own self-referential identifier and path.

## 3. Methodology

Independently derived from a real PostgreSQL 17 instance migrated from empty to head (not host PostgreSQL,
not assumption): `docker run postgres:17-alpine`, `alembic upgrade head` via a clean reused venv, then
exhaustive `pg_catalog`/`information_schema` extraction (tables, columns, PKs, FKs with delete rules,
unique constraints, partial/plain unique indexes, check constraints, all indexes, tenant_id-bearing
columns) into structured TSVs, cross-referenced against all 45 Alembic migration files' own table-creation
provenance. Every defect below was either (a) proven by a **live, real adversarial PostgreSQL INSERT**
inside a transaction later rolled back, or (b) proven by **direct constraint-definition analysis** (a
composite FK's own column list is deterministic ground truth for what PostgreSQL does and does not check —
no empirical test is needed to "confirm" a constraint that structurally cannot check what it doesn't
list). Both methods are disclosed per-finding below.

## 4. Physical schema inventory

Independently re-verified: single Alembic head `0045_oqi_connector_ingestion`; 126 application tables
(public schema, `BASE TABLE`, excludes `alembic_version`); 271 foreign keys; 65 unique constraints
(excluding PK-backing ones and `pg_catalog` noise); 16 additional partial/plain unique indexes; 34 CHECK
constraints; 683 total indexes; 48 tables carry a direct `tenant_id` column. Full detail: the companion
`docs/data-model/NOETVA-ENTERPRISE-DATA-MODEL.md` (hash below).

## 5. Domain model

126 tables classified into 21 sub-domains under 8 super-domains (Platform/Foundation, Source Management,
Evidence/Provenance, Ontology, OQI, Governed Approval Gate S/V, plus the Connector/Ingestion and Blueprint
sub-domains folded into Source Management). Full domain inventory, per-table membership, and a Level-1
ASCII domain diagram are in the ER document §2-3. No table is unclassified.

## 6. Crown-path ER model

Full crown-path (Source → Evidence → Ontology → OQI → Agents → Remediation → Business Impact) ER
specification, including explicit `DERIVED RELATIONSHIP — NO DIRECT FK` disclosures where no physical FK
exists (e.g., Finding → Ontology Impact Evaluation is a polymorphic `finding_family`/`finding_id` column
pair, never an FK), is in the ER document §8.

## 7. PK audit

**Certified clean.** All 126 tables have a primary key (`tables_without_pk.tsv`: 0 rows). Composite PKs are
used correctly for genuine associative/versioned identities (e.g., `oqi_business_dependencies(dependency_id,
version)`, `business_rule_evaluation_inputs(evaluation_id, input_role)`, `assertion_evidence(assertion_id,
evidence_id)`). No mutable business identifier is used as a bare PK. No weak junction identity found.

## 8. FK audit — summary (full detail: ER document §5, §15)

271 FKs total, every one `ON DELETE NO ACTION` (confirmed: zero `CASCADE` anywhere in the schema — a
maximally conservative, evidence/audit-preserving default; see §26). Two concrete FK-completeness gaps
found (not tenant-related; see Defect Register P2-3/P2-4): `oqi_connector_field_mappings.source_field_id`
and `oqi_remediation_instructions`/`oqi_remediation_candidates`'s own `target_source_object_id`/
`target_source_field_id` columns carry **no FK constraint at all** — bare UUID columns with zero
referential integrity, distinct from (and more severe than) a missing tenant qualification.

## 9. Tenant-integrity audit — the central finding of this phase

All 271 FKs classified:

```
STRUCTURALLY_SAFE (composite FK, tenant_id on both sides):        24
GLOBAL_PARENT (parent has no tenant_id — legitimately global):   119
CHILD_NOT_TENANT_OWNED (child has no tenant_id — single/clean
    hop to a tenant-owned or global ancestor, e.g. source_fields
    -> source_objects, oqi_remediation_candidates -> cases):      96
APPLICATION_GUARDED (child AND parent BOTH have their own
    independent tenant_id, but the FK does not check they match): 32
```

The 32 `APPLICATION_GUARDED` relationships are exactly the unsafe pattern this phase was chartered to find:
child.tenant_id = A, child.parent_id → a parent row owned by tenant B, and PostgreSQL's own FK constraint
validates only "does parent_id exist," never "does parent.tenant_id equal child.tenant_id." Two of these
32 were escalated to **live adversarial proof** (below); the methodology is identical for all 32 —
`pg_constraint`'s own column list is definitive, not probabilistic, evidence of what is and is not checked.

### 9.1 CONFIRMED P1 — Remediation authority chain has zero tenant consistency

Real PostgreSQL, inside a transaction (rolled back, no lasting effect):

```sql
INSERT INTO oqi_remediation_cases (case_id, tenant_id, ...) VALUES ('1111...', 'tenant-A', ...);
INSERT INTO oqi_remediation_candidates (candidate_id, case_id, ...) VALUES ('3333...', '1111...', ...);
INSERT INTO oqi_remediation_instructions (instruction_id, tenant_id, case_id, candidate_id, ...)
    VALUES ('4444...', 'tenant-B', '1111...', '3333...', ...);   -- claims tenant-B, case owned by tenant-A
INSERT INTO oqi_remediation_authorizations (authorization_id, tenant_id, instruction_id, ...)
    VALUES ('5555...', 'tenant-C', '4444...', ...);              -- claims tenant-C
```

Result: **all four inserts succeeded**. One logical remediation case/instruction/authorization chain now
carries three different tenant labels (`tenant-A`, `tenant-B`, `tenant-C`) with zero rejection anywhere.
`oqi_remediation_instructions.case_id`, `oqi_remediation_authorizations.instruction_id`, and
`oqi_remediation_agent_runs.case_id`/`oqi_remediation_agent_recommendations.case_id`/`run_id` are all
simple, non-tenant-qualified FKs despite every table in the chain independently carrying its own
`tenant_id` column. This is a "persisted authorization/execution boundary violation" and a "real
cross-tenant FK integrity hole in crown data" — the two named P1 examples in this phase's own charter.

### 9.2 RECLASSIFIED — FieldValueEvidence's governed identity IS database-enforced, via a documented
    domain-layer invariant, not a literal multi-column UNIQUE constraint

An earlier draft of this document (produced within this same DG phase, corrected before final publication
per this phase's own "trust but verify subagent work" discipline) classified this as a CONFIRMED P1 using
exactly the adversarial sequence below:

```sql
INSERT INTO field_value_evidence (field_value_evidence_id, source_field_id, source_record_reference,
    observed_representation, observed_at, received_at)
    VALUES (gen_random_uuid(), '<field>', 'REC-1', '42', '2026-01-01T00:00:00Z', now());
INSERT INTO field_value_evidence (field_value_evidence_id, source_field_id, source_record_reference,
    observed_representation, observed_at, received_at)
    VALUES (gen_random_uuid(), '<same field>', 'REC-1', '42', '2026-01-01T00:00:00Z', now());
-- SELECT count(*) WHERE the exact 4-tuple matches: 2
```

Both raw-SQL inserts do succeed. But independently reading
`backend/app/domain/integration/field_value_evidence.py` in full shows this test does not reach the real
enforcement mechanism: `derive_field_value_evidence_id()` deterministically derives
`field_value_evidence_id` as a `uuid5` hash over exactly the four governed identity inputs
(`source_field_id`, `source_record_reference`, `observed_representation`, `observed_at`, each
length-prefix-canonicalized), and `FieldValueEvidence.__post_init__` — invoked on **every** construction
path, both `.new()` and direct rehydration — raises `ValidationException` if the supplied ID does not match
that derivation. `FieldValueEvidenceRepositoryImpl.create_or_get_existing` (the sole write path) never
persists a caller-supplied ID; it only ever persists `evidence.field_value_evidence_id.value` taken from an
already-validated domain object. **No real application code path can ever produce two `FieldValueEvidence`
facts sharing the identical governed 4-tuple with two different `field_value_evidence_id` values** — the
adversarial test above only "succeeded" by inserting via raw SQL with independently-chosen
`gen_random_uuid()` values, bypassing the exact mechanism (`__post_init__`'s validation) that is the real
enforcement point. Two facts sharing the true governed identity, constructed through any real code path,
necessarily collide on the **PK itself** (`field_value_evidence_pkey`, which PostgreSQL absolutely does
enforce) — this is precisely the mechanism `create_or_get_existing`'s own docstring describes ("an identity
collision under normal operation can only mean identical replay") and exactly what CDD-059's own
same-connector concurrency crown already exercised and passed during REAL-ENTERPRISE-INGESTION's own
closure.

This is the "explicitly documented as an intentional higher-layer invariant with sufficient justification
and adversarial verification" case this phase's own §4 anticipates, not a gap: the invariant is documented
in exhaustive detail in the module's own docstring, and is adversarially sound against every reachable
application code path. **Reclassified from P1 to a certified-clean finding**, with one disclosed, optional,
non-blocking hardening opportunity carried to §32 as P3-4: a literal
`UNIQUE (source_field_id, source_record_reference, observed_representation, observed_at)` constraint would
be strictly redundant under every conforming row today (it could never reject a row the domain layer would
have accepted) but would add a second, independent line of defense against any *future* code path that
constructed a `FieldValueEvidenceORM` row directly, bypassing the domain object entirely. Not authorized for
`POSTGRES-DATA-MODEL-CLOSURE-I` — it maps to no discovered defect, only to a defense-in-depth opportunity,
and this phase's own instruction is to map every authorized change to a discovered defect, not to add
speculative hardening.

### 9.3 P2 — the exact same "current pointer" gap already fixed four times elsewhere was missed twice

`current_ontology_impacts`, `current_business_impacts`, and `current_reliance` all correctly use composite,
tenant-qualified FKs to their own "latest evaluation" pointer (`fk_current_ontology_impacts_tenant_evaluation`
etc.) — the product of the OQI4-R1/OQI6-R1/R2/R3 tenant-isolation correction chain (CDD-052-055) already
merged this session. **`business_rule_findings.latest_evaluation_id → business_rule_evaluations.evaluation_id`
and `quality_comparison_findings.latest_evaluation_id → quality_comparison_evaluations.evaluation_id` are the
two oldest "current finding" pointers in the schema (OQI2/OQI3) and were never given the same treatment** —
both tables independently carry `tenant_id`, the FK does not check it. Same defect class, same fix shape,
simply not yet applied here.

## 10. Unique-constraint audit — summary

Positive finding: the "exactly one active version" cardinality invariant is DB-enforced via **partial
unique indexes** in 8 places (`oqi_canonical_standards`, `oqi_quality_coverage_policies`, `business_rules`,
`quality_rules`, `comparison_subject_correspondences`, `oqi_integrity_relationship_cardinalities`,
`oqi_timeliness_policies`, `semantic_mappings`, `ontology_change_proposals`) — a well-executed, repeated
pattern, not a gap. Negative finding: `field_value_evidence`'s own governed identity is unprotected (§9.2).

## 11. Cardinality audit — summary

271 FKs: 265 classified `1:N`, 6 classified `1:0..1`/`1:1` (child FK columns themselves unique/PK). No
material cardinality mismatch found beyond the one P1 already covered (a tenant-consistency defect, not a
cardinality defect per se).

## 12. Index audit — summary

92 of 271 FK child-columns (≈34%) have no directly supporting index. Most are low-traffic audit columns
(`created_by`/`modified_by` on ECOM foundation tables) where this is a P3 hygiene item, not a correctness
concern. A crown-path-relevant subset — `business_rule_findings.latest_evaluation_id`,
`quality_comparison_findings.latest_evaluation_id`, `quality_evaluations.source_object_id`,
`quality_findings.source_object_id`, `oqi_timeliness_evaluations.field_value_evidence_id` — are the exact
lookup columns for "current finding state for a source object," a real product access path; no query-log
evidence of actual slowness was collected (none exists yet at this product's scale), so this is disclosed
as a **prioritized P3**, not elevated to P2 without that evidence, per this phase's own "no speculative
performance work" instruction.

## 13. Nullability/default/check audit — summary

34 CHECK constraints found, all semantically sound (closed-vocabulary status/outcome/dimension enums,
positive-number bounds, XOR shape validation on `assertions`). Notably, `oqi_quality_coverage_policy_dimensions`'s
own CHECK (`ck_oqi_qcp_dimensions_closed_vocab`) already enumerates all **9** CDD-046 dimensions including
`UNIQUENESS` — see §21.

## 14. Lifecycle/versioning audit — summary

Version-chain self-references (`previous_version_id`/`superseded_by_id`) exist on ~19 tables. Where the
table carries its own `tenant_id` (`enterprise_entities`, `institutional_relationships`, `source_objects`,
`source_systems`, `oqi_quality_coverage_policies`, `oqi_reference_evidence_assertions`,
`impact_propagation_policies`), these self-FKs are part of the same 32-count `APPLICATION_GUARDED` gap
(§9) — a version pointer could theoretically reference a different tenant's prior-version row. Lower
severity than §9.1/9.2 (an internal lineage pointer, not a live authority/evidence boundary), rolled into
the Defect Register as P2.

## 15. Evidence integrity — SourceSystem→SourceObject→SourceField→FieldValueEvidence

Chain traced end-to-end: `source_objects` → `source_systems` (composite tenant-qualified FK,
`fk_source_objects_tenant_source_system`, STRUCTURALLY_SAFE) → `source_fields` → `source_objects` (simple
FK; `source_fields` has no tenant_id of its own — CHILD_NOT_TENANT_OWNED, a legitimate, single-hop pattern,
not a gap) → `field_value_evidence` → `source_fields` (simple FK, same legitimate pattern). The one real
defect in this chain is §9.2 (identity uniqueness), not the tenant-scoping chain itself, which is sound.

## 16. Ontology persistence — summary

`ontology_relationship_bindings` triples are DB-uniqueness-protected
(`uq_ontology_bindings_triple`). `ontology_change_proposals` uses two partial unique indexes to prevent
duplicate Approved/Published concept/relationship names. No orphan-capable or duplicate-edge defect found.

## 17. OQI persistence — summary

Evaluation→Finding chains sound for OQI4/OQI6 (composite tenant-qualified current-pointers); OQI2/OQI3's
own equivalent pointers are the confirmed §9.3 gap. No cross-finding/cross-evaluation linkage defect found
beyond what's already listed.

## 18. Reliance persistence

`oqi_reliance_evaluations` → `current_reliance` is STRUCTURALLY_SAFE (composite tenant-qualified). Reliance
identity (`current_reliance` PK: `tenant_id, ontology_element_type, ontology_element_id`) is DB-enforced —
exactly one current Reliance row per tenant-scoped ontology element. Certified clean.

## 19. Agent/orchestration persistence

`oqi_remediation_agent_runs`/`oqi_remediation_agent_recommendations` are part of the §9.1 confirmed P1 —
their own `case_id`/`run_id` FKs to `oqi_remediation_cases`/`oqi_remediation_agent_runs` are simple, not
tenant-qualified, despite both sides carrying independent `tenant_id`. The intended authority boundary
(agent output ≠ authorization; recommendation ≠ execution permission) is correctly modeled as *separate
tables* (an `AgentRecommendation` cannot itself become an `Authorization` — no FK exists from
recommendations to authorizations at all), but the tenant boundary around the whole chain is not
DB-enforced, per §9.1.

## 20. Remediation/authority persistence

Full chain Finding(polymorphic, DERIVED) → Case → Candidate → Instruction → Authorization → (execution
report is a status transition, not a separate FK-linked row) → re-evaluation (DERIVED, a fresh OQI1-4
evaluation row with no FK back to the authorization that triggered it) → Resolution (a status value on
`oqi_remediation_cases.status`). §9.1 is the central integrity finding here.

## 21. Business impact / explainability persistence

`current_business_impacts` is STRUCTURALLY_SAFE. Business-impact and Reliance rows chain back to their own
evaluation tables via direct FK but not directly to the originating Finding/Evidence row — a multi-hop,
partially DERIVED traversal, disclosed in the ER document §8, not classified as a defect (the intermediate
FKs are all real; only the final hop back to raw evidence is indirect).

## 22. Connector/ingestion persistence (CDD-059)

`oqi_connector_configurations` → `source_systems`, `oqi_connector_field_mappings`/`oqi_connector_runs` →
`oqi_connector_configurations` are all STRUCTURALLY_SAFE (composite tenant-qualified, migration `0045`'s
own design, previously verified in CDD-059's own governance chain — unchanged). **New finding, not
previously disclosed by CDD-059 or any of its R1/R2/R3 amendments**: `oqi_connector_field_mappings.
source_field_id` — the column that says which governed field a mapping actually populates — carries **no
FK constraint whatsoever** to `source_fields`. A mapping can reference a nonexistent or cross-tenant
`source_field_id` with zero database enforcement. This does not reopen CDD-059's own HTTP-transport/SSRF
security architecture (unrelated), but is a genuine persistence-integrity gap in the connector's own
crown path.

## 23. Lineage/provenance

Source → SourceSystem → SourceObject → SourceField → Evidence is fully FK-explicit (§15). Evidence → OQI
Evaluation is FK-explicit (`quality_evaluation_evidence`/`business_rule_evaluation_inputs` join tables).
Evaluation → Finding → Ontology Impact → Recommendation → Authorization → Remediation is a mix of explicit
FK and polymorphic/DERIVED links, fully enumerated with no silent gaps in the ER document §8. No
closure-critical provenance break found beyond the already-listed defects.

## 24. ORM ↔ PostgreSQL parity

Spot-checked (not exhaustively re-verified against every one of 126 tables in this pass, given the ER
document's own catalog is already the authoritative physical-schema source): the tables central to the
confirmed P1 (`oqi_remediation_instructions`/`oqi_remediation_authorizations`/`oqi_remediation_agent_runs`)
have their ORM declarations in `oqi_remediation.py`/`oqi_remediation_agent.py` — neither currently declares
the missing tenant-qualified constraints (consistent with the DB catalog; no ORM/DB drift found, the ORM
correctly reflects what the DB actually enforces today, which is the gap itself, not a parity mismatch).
`field_value_evidence.py` was also independently read in full for §9.2's reclassification: its ORM
declaration correctly reflects the DB's actual constraint set, and (unlike the DB catalog alone) the
adjacent domain module `app/domain/integration/field_value_evidence.py` is where the real enforcement
mechanism lives — no ORM/domain drift found there either.

## 25. Migration integrity

45 migration files, 45 unique `revision` values (no duplicates), single Alembic head confirmed 4 times this
program (`0045_oqi_connector_ingestion`), no orphan revisions, deterministic linear chain (no branch
points). Fresh empty-DB replay succeeds cleanly to head, independently re-run for this phase. Migration 1
(`0001_canonical_v1_3`) bootstraps 32 foundation tables via a raw SQL file
(`canonical_v1_3.sql`) rather than `op.create_table` — accounted for explicitly in table provenance, not a
gap. No destructive migration (`DROP COLUMN`/`DROP TABLE` causing data loss) found; every tenant-isolation
correction migration in this program's history (CDD-052-055, H4-R1) is additive (adds a constraint/column),
consistent with this repository's own disclosed migration-governance convention.

## 26. Delete/retention posture

**Every one of 271 FKs is `ON DELETE NO ACTION`.** No `CASCADE` exists anywhere in the schema. This is a
maximally conservative default: a parent row (including evidence, audit, and governance data) can never be
silently destroyed by a cascading delete from anywhere in this schema. The tradeoff — a delete attempt on a
still-referenced parent simply fails, requiring explicit application-level cleanup — is the safe direction
for this product's own stated priorities (evidence/audit integrity). Certified clean; no correction
authorized or needed.

## 27. Concurrency integrity

The confirmed P1 (§9.1) does not depend on concurrency — it is deterministically insertable by a single
well-formed (but tenant-mismatched) request; no race condition is required to reach it. Separately, the
"SELECT-then-INSERT without a DB uniqueness constraint" race pattern this phase's own charter names
explicitly was independently checked against `field_value_evidence` (§9.2) and found **not** to apply here:
the governed 4-tuple's actual identity is the deterministically-derived `field_value_evidence_id` itself,
so two concurrent writers observing "the same" governed fact necessarily attempt to insert the identical
PK value, and PostgreSQL's own PK uniqueness constraint — not an application-level check — is the thing that
resolves the race (raising a real `IntegrityError` the caller must catch, exactly as
`connector_ingestion_service.py`'s existing `SAVEPOINT` handling already does). No other concurrency-race
finding was identified in this pass.

## 28. Data-type / JSON posture

No floating-point money columns found. Timestamps are uniformly `timestamp with time zone` (no
timezone-naive persisted timestamps found). A small number of `json` (not `jsonb`) columns exist
(`oqi_remediation_candidates.supporting_evidence_ids`/`conflicting_evidence_ids`/`missing_participant_roles`)
— these hold ID *lists* for advisory/audit display, not enforced relationships; PostgreSQL's inability to
FK-validate JSON-embedded IDs is a known, accepted tradeoff for this specific advisory-display use, not
elevated to a defect (the actual authority-relevant relationships in this exact remediation chain are
column-level FKs, covered in §9.1/§19-20).

## 29. Database security posture

Single database role (`ctec`), superuser, owns every table; migrations and runtime application both use
this same role; **no Row-Level Security anywhere** (`pg_tables.rowsecurity`: 0 of 126). Tenant isolation is
therefore entirely dependent on the application layer plus whatever FK/constraint layer PostgreSQL itself
enforces — there is no second line of defense. This is disclosed, not automatically classified a defect (a
service that mediates 100% of DB access through its own application layer, never exposing arbitrary
user-supplied SQL, is a legitimate architecture for this product's current maturity) — but it means the
confirmed P1 constraint gap (§9.1) currently has **no independent backstop**, which raises its practical
severity above what it would carry in an RLS-protected system.

## 30. Adversarial PostgreSQL results — summary

Two live, transactional (rolled back) adversarial INSERT sequences executed against a real, freshly
migrated PostgreSQL 17 instance: (1) three-tenant remediation-chain mismatch, accepted in full — a real,
reachable defect (§9.1); (2) duplicate governed-evidence-identity insert via raw SQL bypassing the domain
layer's own deterministic-ID construction path, also accepted in full, but confirmed **not reachable**
through any real application code path (§9.2) — both results are reproducible facts about the current
schema, not intermittent or environment-dependent, but only (1) represents an application-reachable defect.

## 31. Complete schema certification matrix

The full 126-row certification table (Table/Domain/Tenant class/PK/FK status/Same-tenant enforcement/
Logical uniqueness/Cardinality/Delete semantics/Index posture/Lifecycle/ORM parity/Migration provenance) is
the Table Summary Matrix in `docs/data-model/NOETVA-ENTERPRISE-DATA-MODEL.md` §15, cross-referenced with the
Tenant Model table in §7 of that same document. All 126 tables accounted for; 0 omissions.

## 32. Integrity/Correctness defect register

```
P0 = 0

P1 = 1 (adversarially proven against real PostgreSQL through a real, reachable application code path)
  P1-1  Remediation authority chain (oqi_remediation_instructions/authorizations/agent_runs/
        agent_recommendations) uses simple, non-tenant-qualified FKs despite every table independently
        carrying tenant_id -- proven exploitable (three-tenant chain accepted, zero rejection).

P2 = 4
  P2-1  business_rule_findings.latest_evaluation_id / quality_comparison_findings.latest_evaluation_id
        are not tenant-qualified composite FKs, unlike their four already-corrected sibling "current
        pointer" tables (same defect class as OQI4-R1/OQI6-R1/R2/R3, missed for OQI2/OQI3).
  P2-2  oqi_connector_field_mappings.source_field_id has no FK constraint at all to source_fields.
  P2-3  oqi_remediation_instructions/oqi_remediation_candidates's own target_source_object_id /
        target_source_field_id columns have no FK constraint at all (bare UUIDs).
  P2-4  ~7 version-chain self-references (previous_version_id/superseded_by_id) on tenant-owned tables
        (enterprise_entities, institutional_relationships, source_objects, source_systems,
        oqi_quality_coverage_policies, oqi_reference_evidence_assertions, impact_propagation_policies)
        are not tenant-qualified.

P3 = 4
  P3-1  92 of 271 FK child-columns lack a directly supporting index (mostly low-traffic audit columns;
        5 crown-path-relevant ones flagged for future priority, no query-log evidence of actual slowness).
  P3-2  ~13 created_by/modified_by audit-attribution FKs to enterprise_entities are not tenant-qualified
        (audit attribution only, not core business data -- lower priority than P2-4's lifecycle pointers).
  P3-3  No RLS / single superuser DB role (disclosed architecture choice, not corrected by this phase;
        raises the practical severity of any future constraint gap, noted for future consideration).
  P3-4  field_value_evidence's governed 4-tuple identity is certified-enforced today via a documented
        domain-layer deterministic-ID invariant (§9.2) rather than a literal multi-column UNIQUE
        constraint; adding the literal constraint as redundant defense-in-depth is a disclosed, optional,
        non-blocking hardening opportunity -- not a defect, not authorized for this phase's own I.
```

## 33. Performance/Operability register

Kept separate per this phase's own instruction: only §12/P3-1 above (index posture). No other
performance finding was pursued without query-log evidence.

## 34. UNIQUENESS-dimension assessment (persistence-only; NOT implemented here)

`oqi_quality_coverage_policy_dimensions`'s own CHECK constraint (`ck_oqi_qcp_dimensions_closed_vocab`)
**already lists `UNIQUENESS` as a valid dimension value**, alongside the 8 currently-implemented
dimensions — meaning **zero schema change is required** to begin using the UNIQUENESS dimension once
application/evaluator logic for it is built. This is a positive finding, not a defect: the persistence
layer already contains the primitive CDD-046's own architecture anticipated. No existing logical identity
was found to be "insufficiently constrained because UNIQUENESS functionality was confused with DB
uniqueness" — the two concepts are cleanly separated in this schema today (DB `UNIQUE` constraints exist
independently of, and were never a substitute for, the OQI UNIQUENESS quality dimension). **No
implementation of the OQI UNIQUENESS dimension is authorized or performed by this document.**

## 35. Step-13 → Step-14 impact matrix

```
Docker migration assumptions (single head 0045, 126 tables):        NO IMPACT — unchanged, re-confirmed.
Docker seed behavior (OntologySeeder/BlueprintSeeder/demo_oqi_seeder): NO IMPACT — none of the corrected
    paths are touched by any seeder.
Flagship end-to-end scenario (CDD-060/Step-14 §15):                  REVALIDATE — if POSTGRES-DATA-MODEL-
    CLOSURE-I is merged before Step 14 resumes, its own remediation-lifecycle walkthrough step should be
    re-exercised once against the corrected schema (no scenario STEP is removed or renamed).
OQI scenario / ingestion scenario:                                   NO IMPACT — the connector's own
    tenant-qualified configuration/mapping/run FKs (§22) are unaffected; the newly found
    source_field_id-missing-FK gap (P2-2) is deferred, not fixed by this phase, so no Step-14 assumption
    changes.
Persistence/restart contract:                                        NO IMPACT — no new table, no new
    seed data, no schema-shape change to what a fresh boot produces beyond the authorized correction's own
    additive constraints.
```

Step 14's own CDD-060 (Docker) document requires no edits as a result of this phase; only its own CDD
number requires renumbering per §2 above when it resumes.

## 36. Architecture decision

```
BOUNDED CORRECTION REQUIRED
```

The tenant model, evidence model, and migration architecture are **not** materially defective — the
established pattern (composite `(tenant_id, id)` FKs backed by a `UNIQUE(tenant_id, id)` on the parent) is
already used correctly in 24 places, including the entire REAL-ENTERPRISE-INGESTION connector chain. The
one P1 is a narrow, mechanical **absence** of that same, already-proven pattern in one specific place, not a
sign the pattern itself is wrong. No STOP condition is warranted; no redesign is required.

## 37. Implementation decision

```
IMPLEMENTATION REQUIRED
```

Scoped narrowly to the one confirmed P1 only. The four P2s and four P3s are explicitly **deferred** to a
future, separately governed narrow correction phase (mirroring this program's own established R1-style
pattern) — not silently dropped, not bundled into one large sweep. This keeps the authorized surface
minimal and precisely mapped to the single adversarially-proven, reachable defect, per this phase's own "no
wildcard authorization" instruction.

## 38. Frozen artifact authorization — `POSTGRES-DATA-MODEL-CLOSURE-I`

```
CREATE = 1
MODIFY = 3
DELETE = 0
TOTAL  = 4
```

**CREATE (1)**:
```
backend/app/infrastructure/persistence/migrations/versions/0046_oqi5_remediation_tenant_integrity.py
```
Purpose: close P1-1 only. Must, in order:
1. Add `UNIQUE (tenant_id, case_id)` to `oqi_remediation_cases`, `UNIQUE (tenant_id, instruction_id)` to
   `oqi_remediation_instructions`, `UNIQUE (tenant_id, run_id)` to `oqi_remediation_agent_runs` (prerequisite
   for composite FKs, mirroring the exact existing `uq_source_systems_tenant_pk`/
   `uq_oqi_business_impact_evaluations_tenant_pk` pattern already proven safe in this schema).
2. Replace `fk_oqi_remediation_instructions_case_id` with a composite `(tenant_id, case_id) →
   oqi_remediation_cases(tenant_id, case_id)` FK; replace `fk_oqi_remediation_authorizations_instruction_id`
   with a composite `(tenant_id, instruction_id) → oqi_remediation_instructions(tenant_id, instruction_id)`
   FK; replace `fk_oqi_remediation_agent_runs_case_id` with a composite `(tenant_id, case_id) →
   oqi_remediation_cases(tenant_id, case_id)` FK; replace `fk_oqi_remediation_agent_recommendations_case_id`
   and `..._run_id` with their own composite tenant-qualified equivalents.
3. **Downgrade**: drop the four new composite FKs and the three new `UNIQUE(tenant_id, id)` constraints in
   reverse order, restore the four original simple FKs. No data is destroyed by either direction. **Upgrade
   safety**: this environment carries only demo/test data (confirmed via this phase's own fresh-empty-DB
   replay methodology — no production tenant data exists anywhere this migration will run against yet), so
   "zero data rewrite, zero backfill" (this program's own established precedent for CDD-052/053/054/055/H4-R1)
   applies unchanged.

**MODIFY (3)**:
```
backend/app/infrastructure/persistence/models/oqi_remediation.py
backend/app/infrastructure/persistence/models/oqi_remediation_agent.py
backend/app/tests/test_production_remediation_orchestration_postgres.py
```
Semantic authorization for each: the two model files gain exactly the `UniqueConstraint`/
`ForeignKeyConstraint`/relationship declarations mirroring the migration above (ORM parity, §24) — no other
column, relationship, or behavior changes. The test file gains exactly one new adversarial Postgres test
reproducing the §9.1 three-tenant chain and asserting it now raises `IntegrityError`. No existing test
assertion may be weakened or removed.

**Prohibited**: any other path; `field_value_evidence.py` and any evidence-identity constraint (§9.2 is
certified-clean, not a defect — no change authorized); any change to `connector_ingestion_service.py`, any
API route, any migration other than the one new file, any Docker/CI configuration, any OQI evaluator/
service logic beyond what the new constraints require, implementation of the four deferred P2s or four
deferred P3s, implementation of the OQI UNIQUENESS dimension, or any change to the paused
`product-wide-docker-closure/step-13` branch.

## 39. Final VM contract — `POSTGRES-DATA-MODEL-CLOSURE-VM`

Must independently re-derive the full 126/271/65/34-count catalog fresh (not trust this document's own
counts); confirm the new migration applies cleanly from empty and reverses cleanly; re-run the §9.1
adversarial sequence and confirm it now raises `IntegrityError`; independently re-verify §9.2's own
reclassification (re-read `field_value_evidence.py`'s domain-derivation logic, confirm `__post_init__`
still validates it, confirm `create_or_get_existing` still only ever persists a validated domain object's
own ID) rather than trusting this document's own conclusion; confirm the four P2 and four P3 defect classes
remain exactly as disclosed here (not silently fixed, not silently worsened); confirm ORM parity for the
two modified model files; re-run the full measured backend regression (2177+1 new test) green in a clean
checkout; verify the corrected schema against a fresh Docker PostgreSQL runtime (`docker compose up` +
`alembic upgrade head` inside the real `backend` image, not host Postgres only); confirm the Step-13 →
Step-14 impact matrix (§35) still holds; merge via the repository's normal governed PR-based workflow only.

## 40. STOP conditions — assessment

None of the 15 listed STOP conditions triggered: authoritative main was established cleanly; no unexplained
tracked dirty state; no governance corruption; no destructive migration behavior found; the cross-tenant
finding (§9.1), while real, is narrow and mechanically fixable with an already-proven pattern, not a "broad"
compromise requiring redesign; evidence provenance was independently re-verified as already structurally
sound (§9.2), not merely assumed; authorization/execution persistence is a *gap* to close with the existing
pattern, not
a collapse requiring new architecture; migration history is consistent; no ORM/DB disagreement on crown
data was found (the ORM correctly reflects the gap, it does not contradict it); the correction is fully
bounded (§38); no rewriting of migration history is required (purely additive); the paused Step-14 branch
was never touched; UNIQUENESS application functionality is explicitly NOT required or performed; no defect
outside Step-13's own persistence scope was uncovered.

## 41. Product-claim boundary

**Will be claimable once VM certifies**: Noetva's PostgreSQL persistence model has been independently
certified across its complete physical schema (126 tables, 271 FKs, 65+16 unique constraints, 34 checks,
683 indexes) for identity, referential integrity, tenant relationships (with the one confirmed P1 gap
closed), logical uniqueness (the evidence 4-tuple already certified today via its documented domain-layer
deterministic-ID invariant, §9.2), cardinality, migration integrity, and ORM parity, subject to the
explicitly disclosed and justified application-layer invariants (§9 CHILD_NOT_TENANT_OWNED single-hop
patterns, §26 no-cascade delete posture, §29 no-RLS single-role architecture) and the four deferred P2/four
deferred P3 limitations named in §32.

**Not claimed**: perfect performance at arbitrary scale; formal mathematical proof of anything; the
implemented OQI UNIQUENESS dimension (still absent, deliberately not built here); database-level
enforcement of the four deferred P2 gaps (disclosed, not silently accepted as safe); any capability outside
this verified persistence scope.

## 42. Governance artifact hash

This document, once frozen: see the commit that publishes it for its own SHA-256 (computed and recorded at
publication time, following this repository's own established pattern).

## 43. ER document cross-reference

`docs/data-model/NOETVA-ENTERPRISE-DATA-MODEL.md`, hash
`29d5ee2d1d9a1f38df20b478029b3c1a240748d9a2deb74b398930ea3832c95b`, status `DISCOVERED / GOVERNED — PENDING
VM CERTIFICATION`. This CDD document and that ER document together constitute the complete Step-13
discovery deliverable; the ER document must be updated (by I, then re-verified by VM) if
`POSTGRES-DATA-MODEL-CLOSURE-I` changes any FK/constraint it currently documents.

**Exact next phase: `POSTGRES-DATA-MODEL-CLOSURE-I`.**
