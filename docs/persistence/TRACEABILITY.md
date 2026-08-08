# CDD-002 ORM Traceability

Version: 1.0  
Status: Frozen with CDD-002

## Purpose

This document provides the human-readable path from each SQLAlchemy persistence model to its canonical authority. It complements the machine-readable `traceability/PERSISTENCE-TRACEABILITY-v1.3.json` artifact, which records all 370 columns and 123 foreign keys.

The authoritative schema source is `architecture/released/v1.1/ECOM_Physical_Data_Model_v1_3.sql`. The migration copy is an implementation artifact and is required to match that source byte-for-byte; it is not an architecture authority.

The precedence remains Constitution → RFCs → Logical Model → Physical Model → EAD-001 → Persistence. ORM classes implement the model; they do not define or extend it.

## Canonical entity models

| SQLAlchemy model | Physical table | Logical entity | EAD reference |
| --- | --- | --- | --- |
| Enterprise | `enterprises` | Enterprise | EAD-001 v1.3 — Enterprise |
| EnterpriseType | `enterprise_types` | Enterprise Type | EAD-001 v1.3 — Enterprise Type |
| Country | `countries` | Country | EAD-001 v1.3 — Country |
| BusinessDomain | `business_domains` | Business Domain | EAD-001 v1.3 — Business Domain |
| InstitutionalConcept | `institutional_concepts` | Institutional Concept | EAD-001 v1.3 — Institutional Concept |
| RelationshipType | `relationship_types` | Relationship Type | EAD-001 v1.3 — Relationship Type |
| EntityType | `entity_types` | Entity Type | EAD-001 v1.3 — Entity Type |
| EnterpriseEntity | `enterprise_entities` | Enterprise Entity | EAD-001 v1.3 — Enterprise Entity |
| Assertion | `assertions` | Assertion | EAD-001 v1.3 — Assertion |
| InstitutionalRelationship | `institutional_relationships` | Institutional Relationship | EAD-001 v1.3 — Institutional Relationship |
| Evidence | `evidence` | Evidence | EAD-001 v1.3 — Evidence |
| Knowledge | `knowledge` | Knowledge | EAD-001 v1.3 — Knowledge |
| Reason | `reasons` | Reason | EAD-001 v1.3 — Reason |
| ReasonGraph | `reason_graphs` | Reason Graph | EAD-001 v1.3 — Reason Graph |
| DecisionObjective | `decision_objectives` | Decision Objective | EAD-001 v1.3 — Decision Objective |
| Occasion | `occasions` | Occasion | EAD-001 v1.3 — Occasion |
| PatternOfRelevance | `patterns_of_relevance` | Pattern of Relevance | EAD-001 v1.3 — Pattern of Relevance |
| Decision | `decisions` | Decision | EAD-001 v1.3 — Decision |
| DecisionState | `decision_states` | Decision State | EAD-001 v1.3 — Decision State |
| InstitutionalAction | `institutional_actions` | Institutional Action | EAD-001 v1.3 — Institutional Action |
| Outcome | `outcomes` | Outcome | EAD-001 v1.3 — Outcome |
| Experience | `experiences` | Experience | EAD-001 v1.3 — Experience |
| Governance | `governance` | Governance | EAD-001 v1.3 — Governance |
| AccountableOwner | `accountable_owners` | Accountable Owner | EAD-001 v1.3 — Accountable Owner |
| SourceSystem | `source_systems` | Source System | EAD-001 v1.3 — Source System |
| SourceObject | `source_objects` | Source Object | EAD-001 v1.3 — Source Object |
| InstitutionalAct | `institutional_acts` | Institutional Act | EAD-001 v1.3 — Institutional Act |
| Context | `contexts` | Context | EAD-001 v1.3 — Context |

## Physical relationship models

These four ORM models implement Physical Model v1.3 many-to-many join tables. They do not introduce logical entities or business attributes. Their columns and keys are governed by the Physical Model relationships rather than standalone EAD entity sections.

| SQLAlchemy model | Physical table | Logical relationship | EAD reference |
| --- | --- | --- | --- |
| ReasonDecisionObjectives | `reason_decision_objectives` | Reason ↔ Decision Objective | Physical Model v1.3 M:N relationship; endpoint identifiers trace to EAD-001 |
| ReasonEvidence | `reason_evidence` | Reason ↔ Evidence | Physical Model v1.3 M:N relationship; endpoint identifiers trace to EAD-001 |
| AssertionEvidence | `assertion_evidence` | Assertion ↔ Evidence | Physical Model v1.3 M:N relationship; endpoint identifiers trace to EAD-001 |
| InstitutionalRelationshipAssertions | `institutional_relationship_assertions` | Institutional Relationship ↔ Assertion | Physical Model v1.3 M:N relationship; endpoint identifiers trace to EAD-001 |

## Verification

- ORM models: 32
- Physical tables: 32
- Physical columns: 370
- Foreign keys: 123
- Missing EAD traces: 0
- Canonical schema SHA-256: `9242abdd3de19f7a2c33f406e71d50ad629132dfe783375d864a7fcb2f90cd2b`

No ORM model is permitted without an approved canonical mapping. Changes require the governing model update and RFC or CDD approval before persistence code changes.

## Cognitive immutable-record projections

Cognitive evaluation and resolution records are immutable and append-only. Currentness is determined externally from the complete ordered record history in accordance with RFC-011. No cognitive record changes state from active to archived.

The Identity Resolution, Semantic Resolution, and Assertion persistence projections retain the physical columns `active_record_id` and `archived_record_ids` solely for compatibility with their existing migrations. ORM and repository code expose these fields as `current_record_identifier` and `historical_record_references`. The legacy column names are implementation projection details; they are not business attributes, lifecycle state, or architecture authority.

Decision and Knowledge repositories derive currentness directly from immutable records using effective date, produced timestamp, and record identifier ordering. Their history operations return the complete immutable sequence; they do not update prior records.
