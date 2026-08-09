# ARCH-005 — Bounded Supplier-Risk Vocabulary Ownership

Version: 1.0
Status: FROZEN

## Decision

The existing ECOM Platform Enterprise, identifier `00000000-0000-0000-0000-000000000004`, is the accountable owner of exactly these canonical vocabulary values:

- `SUPPLIER_RISK_CONDITION` — `cdbb90c4-6518-59cd-aa13-989d2717a256`
- `HAS_ACTIVE_RISK_CONDITION` — `de39e820-d95c-51ce-9cd3-da98cb072a36`

This is a narrow qualification of the implementation-support limitation attached to the ECOM Platform Enterprise. It authorizes stewardship, lifecycle management, referential integrity, and governance only for vocabulary introduced by RFC-014/CIM-001 for the supplier-risk vertical slice.

It does not grant unrestricted enterprise-semantic authority, authorize unrelated vocabulary, create a new Enterprise or organization, or modify canonical schema.

## Deterministic identifiers

Identifiers use RFC 4122 UUIDv5 with namespace `00000000-0000-0000-0000-000000000008` and UTF-8 name `{category}:{value}`:

| Value | UUIDv5 name | Immutable UUID |
|---|---|---|
| `SUPPLIER_RISK_CONDITION` | `institutional_concept:SUPPLIER_RISK_CONDITION` | `cdbb90c4-6518-59cd-aa13-989d2717a256` |
| `HAS_ACTIVE_RISK_CONDITION` | `relationship_type:HAS_ACTIVE_RISK_CONDITION` | `de39e820-d95c-51ce-9cd3-da98cb072a36` |

The UUIDs are unique, deterministic, and immutable upon publication. Regeneration with the same namespace and exact names must produce the same values. Random replacement and reassignment are prohibited.

## Boundary

This decision changes no entity, attribute, relationship structure, persistence model, API, or implementation. Any new vocabulary value requires separate governance.

## Traceability

ARCH-004; RFC-010; CDD-003 Revision 2; CVR-001 v1.0; RFC-014 v1.1; CIM-001 v1.1.
