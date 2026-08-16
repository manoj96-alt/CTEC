"""Add tenant ownership to institutional_relationships (Gate D1 / RFC-016).

Tenant ownership rationale: institutional_relationships is the ECOM Physical
Data Model's sole authorized mechanism for entity-to-entity relationships
(the "Universal Relationship Principle," GMR-032) and carries the identical
governance/lifecycle column shape as enterprise_entities, source_systems, and
source_objects -- the three tables RFC-015 already tenant-scoped. RFC-016
extends that same mechanism to this fourth table and re-authorizes
"Institutional Relationship" as a canonical Operational entity (see RFC-016,
architecture/released/v1.9/).

Database-enforced isolation, mirroring RFC-015 exactly: a composite unique
constraint (tenant_id, institutional_relationship_id) backs two new composite
foreign keys (tenant_id, from_entity_id) and (tenant_id, to_entity_id), both
referencing enterprise_entities(tenant_id, enterprise_entity_id) -- so a
cross-tenant relationship is structurally rejected by PostgreSQL even if
application code contains a defect:

  institutional_relationships(tenant_id, from_entity_id)
    -> enterprise_entities(tenant_id, enterprise_entity_id)
  institutional_relationships(tenant_id, to_entity_id)
    -> enterprise_entities(tenant_id, enterprise_entity_id)

Pre-existing row safety (RFC-016 §5a) -- the load-bearing difference from
migration 0011's backfill: 0011 applied a single blanket backfill tenant
because no production row could possibly predate that migration (only
demo-seed content existed). institutional_relationships carries a real,
if currently unused, write path (InstitutionalRelationship / the generated
repository), so this migration must not assume the table is empty. Before
any schema change, it queries every existing row and attempts to resolve its
tenant deterministically, and only from already-authorized governed data:
both from_entity_id and to_entity_id must resolve to an existing
enterprise_entities row, and both must agree on tenant_id. No tenant is ever
invented, defaulted, or inferred from any other source. If any row's tenant
cannot be resolved this way, the migration raises before making any schema
change at all -- the whole migration aborts atomically (Alembic runs each
migration inside a transaction), leaving the database exactly as it was,
identifying every blocking row and the specific reason (missing endpoint vs.
tenant disagreement) without ever printing raw row content.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_ir_tenant_ownership"
down_revision: str | None = "0011_erm_tenant_and_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class InstitutionalRelationshipTenantResolutionError(RuntimeError):
    """Raised when a pre-existing institutional_relationships row's tenant
    cannot be deterministically resolved from governed data. No schema
    change is applied before this can be raised, and Alembic's transactional
    DDL rolls back anything already attempted in this migration."""


def _resolve_pre_existing_row_tenants(bind: sa.engine.Connection) -> dict[str, str]:
    rows = bind.execute(
        sa.text(
            """
            SELECT
                ir.institutional_relationship_id AS row_id,
                from_ee.tenant_id AS from_tenant,
                to_ee.tenant_id AS to_tenant
            FROM institutional_relationships ir
            LEFT JOIN enterprise_entities from_ee
                ON from_ee.enterprise_entity_id = ir.from_entity_id
            LEFT JOIN enterprise_entities to_ee
                ON to_ee.enterprise_entity_id = ir.to_entity_id
            """
        )
    ).fetchall()

    resolved: dict[str, str] = {}
    blocking: list[str] = []
    for row in rows:
        row_id = str(row.row_id)
        if row.from_tenant is None or row.to_tenant is None:
            missing = "from_entity_id" if row.from_tenant is None else "to_entity_id"
            blocking.append(
                f"institutional_relationship_id={row_id}: {missing} does not resolve "
                "to an existing enterprise_entities row"
            )
            continue
        if row.from_tenant != row.to_tenant:
            blocking.append(
                f"institutional_relationship_id={row_id}: from_entity_id and "
                "to_entity_id resolve to different tenants"
            )
            continue
        resolved[row_id] = row.from_tenant

    if blocking:
        raise InstitutionalRelationshipTenantResolutionError(
            "0012_institutional_relationship_tenant_ownership: refusing to add "
            "institutional_relationships.tenant_id NOT NULL -- "
            f"{len(blocking)} pre-existing row(s) could not be deterministically "
            "assigned a tenant from governed data (RFC-016 §5a). No schema "
            "change has been applied. Blocking row(s):\n" + "\n".join(blocking)
        )
    return resolved


def upgrade() -> None:
    bind = op.get_bind()
    resolved_tenants = _resolve_pre_existing_row_tenants(bind)

    # ---- Every pre-existing row (if any) has a deterministically resolved
    # tenant; safe to proceed. ----
    op.add_column(
        "institutional_relationships", sa.Column("tenant_id", sa.String(200), nullable=True)
    )
    for row_id, tenant_id in resolved_tenants.items():
        bind.execute(
            sa.text(
                "UPDATE institutional_relationships SET tenant_id = :tenant_id "
                "WHERE institutional_relationship_id = :row_id"
            ),
            {"tenant_id": tenant_id, "row_id": row_id},
        )
    op.alter_column("institutional_relationships", "tenant_id", nullable=False)

    op.create_index(
        "idx_institutional_relationships_tenant_id",
        "institutional_relationships",
        ["tenant_id"],
    )
    op.drop_constraint(
        "institutional_relationships_institutional_relationship_name_key",
        "institutional_relationships",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_institutional_relationships_tenant_name",
        "institutional_relationships",
        ["tenant_id", "institutional_relationship_name"],
    )
    op.create_unique_constraint(
        "uq_institutional_relationships_tenant_pk",
        "institutional_relationships",
        ["tenant_id", "institutional_relationship_id"],
    )

    op.drop_constraint(
        "fk_institutional_relationships_from_entity_id",
        "institutional_relationships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutional_relationships_from_entity_id",
        "institutional_relationships",
        "enterprise_entities",
        ["tenant_id", "from_entity_id"],
        ["tenant_id", "enterprise_entity_id"],
    )
    op.drop_constraint(
        "fk_institutional_relationships_to_entity_id",
        "institutional_relationships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutional_relationships_to_entity_id",
        "institutional_relationships",
        "enterprise_entities",
        ["tenant_id", "to_entity_id"],
        ["tenant_id", "enterprise_entity_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_institutional_relationships_to_entity_id",
        "institutional_relationships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutional_relationships_to_entity_id",
        "institutional_relationships",
        "enterprise_entities",
        ["to_entity_id"],
        ["enterprise_entity_id"],
    )
    op.drop_constraint(
        "fk_institutional_relationships_from_entity_id",
        "institutional_relationships",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutional_relationships_from_entity_id",
        "institutional_relationships",
        "enterprise_entities",
        ["from_entity_id"],
        ["enterprise_entity_id"],
    )

    op.drop_constraint(
        "uq_institutional_relationships_tenant_pk",
        "institutional_relationships",
        type_="unique",
    )
    op.drop_constraint(
        "uq_institutional_relationships_tenant_name",
        "institutional_relationships",
        type_="unique",
    )
    op.create_unique_constraint(
        "institutional_relationships_institutional_relationship_name_key",
        "institutional_relationships",
        ["institutional_relationship_name"],
    )
    op.drop_index(
        "idx_institutional_relationships_tenant_id", table_name="institutional_relationships"
    )
    op.drop_column("institutional_relationships", "tenant_id")
