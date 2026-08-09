"""Add the bounded append-only API security audit record."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009_api_security_audit"
down_revision: str | None = "0008_durable_execution"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_security_audit_events",
        sa.Column("audit_event_id", sa.Uuid(), primary_key=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(200)),
        sa.Column("principal_reference", sa.String(200)),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("endpoint_classification", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(80), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("diagnostic_code", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid()),
        sa.Column("attempt_id", sa.Uuid()),
        sa.Column("authorization_decision_reference", sa.String(200)),
        sa.Column("evidence_resource_reference", sa.String(300)),
        sa.Column("source_channel", sa.String(100)),
        sa.Column("retention_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legal_hold_reference", sa.String(200)),
        sa.Column("integrity_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("integrity_digest", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "retention_until >= event_timestamp", name="api_security_audit_retention_valid"
        ),
    )
    op.create_index(
        "ix_api_security_audit_tenant_time",
        "api_security_audit_events",
        ["tenant_id", "event_timestamp"],
    )
    op.create_index(
        "ix_api_security_audit_category_time",
        "api_security_audit_events",
        ["event_category", "event_timestamp"],
    )
    op.create_index(
        "ix_api_security_audit_correlation", "api_security_audit_events", ["correlation_id"]
    )
    op.create_index(
        "ix_api_security_audit_retention",
        "api_security_audit_events",
        ["retention_until", "legal_hold"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_api_security_audit_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND current_setting('ctec.audit_disposition', true) = 'authorized' THEN
            RETURN OLD;
          END IF;
          RAISE EXCEPTION 'api_security_audit_events are append-only';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER api_security_audit_immutable
        BEFORE UPDATE OR DELETE ON api_security_audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_api_security_audit_mutation();
    """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS api_security_audit_immutable ON api_security_audit_events")
    op.execute("DROP FUNCTION IF EXISTS reject_api_security_audit_mutation()")
    for name in (
        "ix_api_security_audit_retention",
        "ix_api_security_audit_correlation",
        "ix_api_security_audit_category_time",
        "ix_api_security_audit_tenant_time",
    ):
        op.drop_index(name, table_name="api_security_audit_events")
    op.drop_table("api_security_audit_events")
