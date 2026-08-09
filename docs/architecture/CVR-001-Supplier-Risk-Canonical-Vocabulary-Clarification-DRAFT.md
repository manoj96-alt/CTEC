# CVR-001 — Supplier-Risk Canonical Vocabulary Clarification

Version: 1.0 DRAFT
Status: DEVELOPMENT / NON-AUTHORITATIVE

## Inspection result

The approved Logical Model, Physical Model, EAD traceability material, domain foundation, Registry, and released architecture define the structures `Relationship Type` and `Institutional Concept` but contain no exact frozen value-level identifier or definition for an active supplier-risk condition. Dataset values and test strings are non-authoritative and were not reused.

## Amendment record

| Item | Value |
|---|---|
| Governing artifacts | RFC-010; CDD-003 Revision 2; Logical Model v1.3; Physical Model v1.3; EAD-001 v1.3 |
| Exact section affected | Canonical vocabulary values only; no schema/entity/attribute/relationship-structure change |
| Change type | Normative addition of two minimum governed vocabulary values |
| Downstream dependency | SRM-001, ASM-001, RFC-014, CIM-001, future CDD-011 |

## Proposed Institutional Concept value

| Property | Proposed value |
|---|---|
| Stable vocabulary identifier | `SUPPLIER_RISK_CONDITION` |
| Immutable UUID | `cdbb90c4-6518-59cd-aa13-989d2717a256` |
| Owning Enterprise | ECOM Platform — `00000000-0000-0000-0000-000000000004` under bounded ARCH-005 authority |
| Canonical name | Supplier Risk Condition |
| Definition | A governed concept representing a condition that may expose a supplier's ability to satisfy an enterprise obligation to risk. Activity and effective time are established by an Assertion, not embedded as mutable concept state. |
| Provenance requirement | Must trace to a resolved semantic interpretation and governed SourceObservations. |
| Usage constraint | May be used only as the object concept of a governed risk-condition assertion. It does not itself establish risk, severity, sourcing status, or recommendation. |

## Proposed Relationship Type value

| Property | Proposed value |
|---|---|
| Stable vocabulary identifier | `HAS_ACTIVE_RISK_CONDITION` |
| Immutable UUID | `de39e820-d95c-51ce-9cd3-da98cb072a36` |
| Owning Enterprise | ECOM Platform — `00000000-0000-0000-0000-000000000004` under bounded ARCH-005 authority |
| Canonical name | Has Active Risk Condition |
| Definition | Relates an identified supplier Enterprise Entity to the Supplier Risk Condition Institutional Concept when governed evidence establishes that the condition is active at the Assertion's effective time. |
| Directionality | Supplier Enterprise Entity → Supplier Risk Condition Institutional Concept |
| Domain | Enterprise Entity resolved and classified as a supplier under governed enterprise vocabulary |
| Range | Institutional Concept `SUPPLIER_RISK_CONDITION` |
| Provenance requirement | Minimum one current governed ERM record, one current governed SRM record, and the SourceObservations supporting the effective-time condition. |
| Usage constraints | Relational Assertion use only; never inferred directly from a CSV field; missing/conflicting evidence yields pre-ASM `INDETERMINATE`; never represents supplier approval, qualification, eligibility, capacity, or sourcing recommendation. |

## Current authoritative language

Logical Model v1.3 states that relational Assertions use `relationship_type_id` as the governed verb and that the object uses Institutional Concept. It defines their structures but no supplier-risk-specific values.

## Proposed additive language

Register the two values above within the existing enterprise-owned canonical vocabularies. Do not add tables, columns, entities, attributes, relationship structures, or implementation technology.

## Reason and compatibility

The bounded proposition cannot be constructed with exact governed vocabulary today. The addition is schema-compatible and does not alter existing values. Semantic compatibility is additive but normative because it creates canonical vocabulary values.

## Governance actions

ARCH-005 authorizes the existing ECOM Platform Enterprise as the bounded owner. UUIDs are generated with UUIDv5 namespace `00000000-0000-0000-0000-000000000008` and exact names `institutional_concept:SUPPLIER_RISK_CONDITION` and `relationship_type:HAS_ACTIVE_RISK_CONDITION`. Registry/dependency updates, checksums/manifest regeneration, and consistency/drift/readiness approval remain required.

## Validation and rollback

Validate uniqueness, enterprise ownership, exact directionality/domain/range, absence of approximate duplicates, and ASM/SRM compatibility. Rollback prohibits new use and supersedes the vocabulary values under canonical governance; existing immutable references must remain historically resolvable and must not be deleted.
