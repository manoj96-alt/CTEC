# RFC-016 — Institutional Relationship Canonical Authorization and Tenant Ownership

Version: 1.0
Status: FROZEN
Current: YES
Authority: AUTHORITATIVE
Supersedes: — (new authority)
Approval: Product Owner authorization, Gate D0/D1
Scope: `institutional_relationships` canonical-entity status and tenant ownership only

## 0. Purpose

This RFC resolves the "Track 1" architecture blocker identified during
Priority 6 ("Ontology Copilot / Ask CTEC") discovery: whether
`institutional_relationships` — the ECOM Physical Data Model's existing
instance-level relationship-edge table between two `enterprise_entities` —
may be exposed through a new read-only capability, and if so, on what
governed footing.

It does not authorize implementation of any capability that would read this
table. It does not authorize any Priority 6 API, intent parser, traversal
engine, answer composer, frontend workspace, demo data seeding, or LLM
integration. Those remain governed separately and are explicitly out of scope
(see §4, Non-claims).

## 1. Problem statement

Two independent gaps were found while evaluating whether Ask CTEC could safely
read `institutional_relationships`:

**1a. Canonical-entity authorization gap.** RFC-010 §4 and both versions of
CDD-003 (the original, HISTORICAL/SUPERSEDED `docs/cdd/CDD-003-Foundation-Reference-Model.md`,
and the current AUTHORITATIVE `CDD-003 Revision 2`) enumerate the Canonical
Enterprise Ontology's authorized entities explicitly. Neither ever names
"Institutional Relationship" — only "Relationship Type" (the taxonomy) appears
in either list. A substantive design description of "Institutional Relationship"
does exist, in `architecture/released/v1.2/ECOM_Logical_Data_Model_v1_3.md`
("Package: Operational" — `Enterprise Entity`, `Institutional Relationship`,
`Context`), but that document is registered in `architecture/INDEX.md` as
`ECOM Logical Data Model | 1.3 | DEVELOPMENT | NO | NON-AUTHORITATIVE` and
therefore confers no current authority. `architecture/INDEX.md`'s only other
trace of authorization is an unverifiable reference to a "frozen CDD-002
archive" — no file named CDD-002 exists anywhere in this repository or its git
history (confirmed by exhaustive search, including deleted-file search across
all commits). This gap is not invented by this RFC; it predates it and would
exist regardless of Priority 6.

**1b. Tenant-ownership gap.** `institutional_relationships` carries the
identical governance/lifecycle column shape as `enterprise_entities`
(`created_by`, `governance_status`, `version_number`, `previous_version_id`,
etc. — unlike pure reference tables such as `relationship_types`, which carry
none of that lineage), and both of its foreign keys (`from_entity_id`,
`to_entity_id`) already reference `enterprise_entities`
(`fk_institutional_relationships_from_entity_id`,
`fk_institutional_relationships_to_entity_id`,
`architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql:570-571`) — plain,
not tenant-qualified. This makes it structurally the same kind of
customer-owned instance data RFC-015 already tenant-scoped for
`enterprise_entities`/`source_objects`/`source_systems`. RFC-015 §1 states its
own scoping criterion directly: the three tables it authorized were "the first
surface (the Entity Resolution Steward workspace, Increment 3A) to disclose
that content directly to an authenticated caller." `institutional_relationships`
was never named in RFC-015 not because it was considered and excluded, but
because no capability had yet proposed exposing it — RFC-015's own Non-claims
section confirms it authorizes nothing "other than the Entity Resolution
tenant-foundation work of Increment 3A-0."

**Relevance to the canonical model as a whole.** The Physical Model itself
already treats `institutional_relationships` as the sole authorized mechanism
for entity-to-entity relationships, via its own embedded "Universal
Relationship Principle" hard rule (GMR-032,
`architecture/released/v1.8/ECOM_Physical_Data_Model_v1_6.sql:1000-1006`):
*"No Enterprise-Entity-to-Enterprise-Entity relationship may be added as a
direct FK column anywhere in this schema. Every such relationship goes through
institutional_relationships (from_entity_id/to_entity_id) or through
assertions... at the predication layer."* This table has been physically
present, unchanged in shape, in every released Physical Model since v1.3. This
RFC treats §1a as closing a pre-existing documentation gap around an entity
the physical model already depends on structurally, not as introducing a new
entity.

## 2. Scope

This RFC authorizes exactly two changes, both delivered in the new physical
model release described in §3:

### 2a. Canonical-entity re-authorization of Institutional Relationship

"Institutional Relationship" becomes an explicitly authorized entity of the
Canonical Enterprise Ontology's Operational package, alongside Enterprise
Entity, Source System, and Source Object — consistent with its existing
physical-model presence, its role as the exclusive mechanism required by
GMR-032, and the design description already on file (non-authoritatively) in
`ECOM_Logical_Data_Model_v1_3.md`. This RFC is self-contained authorization,
following RFC-015's own precedent of authorizing physical-model change
directly rather than requiring a separately-frozen predecessor document —
because the predecessor document (CDD-002) cannot be located or reconstructed
from any authoritative or historical artifact in this repository. This RFC
does not assert what CDD-002 originally said; it only re-establishes
authorization going forward, on this RFC's own authority, for this specific
entity.

### 2b. Tenant ownership on `institutional_relationships`

`tenant_id VARCHAR(200) NOT NULL` is added to `institutional_relationships`,
mirroring RFC-015's exact mechanism:

```sql
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_from_entity_id
    FOREIGN KEY (tenant_id,from_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT fk_institutional_relationships_to_entity_id
    FOREIGN KEY (tenant_id,to_entity_id) REFERENCES enterprise_entities(tenant_id,enterprise_entity_id);
ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_name
    UNIQUE (tenant_id,institutional_relationship_name);
ALTER TABLE institutional_relationships ADD CONSTRAINT uq_institutional_relationships_tenant_pk
    UNIQUE (tenant_id,institutional_relationship_id);
CREATE INDEX idx_institutional_relationships_tenant_id ON institutional_relationships(tenant_id);
```

A cross-tenant `institutional_relationships` row (one endpoint owned by tenant
A, the other by tenant B, or the row itself claiming a tenant neither endpoint
belongs to) becomes structurally rejected by PostgreSQL, matching RFC-015's own
stated goal ("even if application code contains a defect") rather than relying
on transitive application-layer inference. `tenant_id` originates only from the
trusted authority boundary (`TrustedPrincipal.tenant_id` →
`AuthorityContext.organization_id`), identical to RFC-015 §1's rule, never from
an unrestricted request field.

## 3. Governed artifacts

Delivered together with this authorization, in the Gate D1 baseline release:

- `architecture/released/v1.9/ECOM_Physical_Data_Model_v1_7.sql` — the new
  physical model, generated (not hand-edited) from v1.6 by
  `tools/generate_v1_9_physical_model_release.py`.
- `docs/persistence/traceability/EAD-001-v1.7.json` — the Enterprise Attribute
  Dictionary, extended with a `tenant_id` attribute row for the already-present
  `Institutional Relationship` entity, generated by
  `tools/generate_v1_9_ead_release.py`.
- `docs/persistence/traceability/PERSISTENCE-TRACEABILITY-v1.7.json` —
  regenerated canonical-column traceability for physical model v1.7 by
  `tools/build_persistence_traceability.py`; zero missing EAD traces.
- `backend/app/infrastructure/persistence/migrations/versions/0012_institutional_relationship_tenant_ownership.py` —
  the tenant-ownership migration, implementing the §2b invariant with the §5a
  pre-existing-row safety requirement.
- `backend/app/infrastructure/persistence/models/institutional_relationship.py` —
  repointed to match physical model v1.7.
- `backend/app/tests/test_canonical_metadata.py` — repointed to physical model
  v1.7; canonical column total updated to 374 (table count unchanged at 32).
- `architecture/released/v1.9/DEPENDENCY-MATRIX-v1.9.csv`,
  `architecture/INDEX.md` — registry and dependency updates recording this
  authorization.
- `architecture/released/v1.9/RELEASE-MANIFEST-v1.9.xlsx` — the checksummed
  release manifest for this baseline, generated by
  `tools/generate_v1_9_release_manifest.py`.

## 4. Non-claims

This RFC does not authorize, and no Gate D1 artifact implements, any Priority 6
capability: no Ask CTEC API, intent parser, traversal engine, answer composer,
frontend workspace, demo relationship seeding, or LLM integration. It does not
authorize any change to any other canonical entity, to CDD-012
runtime-persistence behavior, to CDD-013 application-security-audit behavior,
to the Supplier Risk API, or to the existing Ontology Service API. It
authorizes exactly the two changes in §2, to exactly one table.

## 5. Migration

The Alembic migration described in §3 lands in this same Gate D1 authorized
release, per RFC-015's own precedent of bundling architecture authorization
with its implementing migration.

### 5a. Pre-existing row safety (binding requirement on the migration)

The migration must not assume `institutional_relationships` is empty in every
deployed environment merely because no code path in the application
constructs a row today — absence of a known writer is not proof of absence of
data. Before adding `tenant_id NOT NULL`, the migration is required to:

1. Query for the existence of any pre-existing `institutional_relationships`
   row, in the target database, before making any schema change.
2. If none exist, proceed directly to the §2b schema change — no backfill
   step is needed.
3. If any exist, attempt to resolve each row's tenant deterministically and
   only from already-authorized governed data: both `from_entity_id` and
   `to_entity_id` resolve to `enterprise_entities` rows, and (post RFC-015)
   each carries its own authoritative `tenant_id`. A row's tenant is
   deterministically resolvable only when both endpoints resolve to an
   existing `enterprise_entities` row and both agree on `tenant_id`.
4. The migration must never invent, default, or infer a tenant for a row from
   any source other than that agreement (not from a configuration default,
   not from "the only tenant currently seeded," not from request context —
   there is no request context at migration time).
5. If any existing row's tenant cannot be deterministically resolved this way
   (either endpoint missing, or the two endpoints disagree on tenant — itself
   evidence of a pre-existing cross-tenant data-integrity problem this RFC's
   invariant is designed to prevent going forward), the migration must fail
   closed: abort before altering the table, and surface exactly which
   row(s) and which reason (missing endpoint vs. tenant disagreement) blocked
   it. It must not proceed partially, silently skip unresolvable rows, or
   force a placeholder tenant to satisfy `NOT NULL`.

## 6. Authorization

Authorized by CTEC Product Owner Manoj Nair on 2026-08-15: the architecture
decisions in §2 (canonical-entity re-authorization and tenant ownership for
`institutional_relationships`) and the stated scope in §4 (Non-claims) were
approved together with the binding pre-existing-row-safety requirement in
§5a (Gate D0). Gate D1 completes registry publication: the §3 artifacts, this
document's FROZEN status, and the atomic `architecture/INDEX.md` update land
together in this baseline.
