"""Add additive, nullable trusted display-name snapshot columns to
`oqi_remediation_authorizations` (CDD-091 §21.1/§22, NOETVA-OQI-DEMO-UX-
HARDENING-G-R1/G-R2-R1).

Two new columns -- `requested_by_display_name`, `decided_by_display_name`
-- carry a human-readable presentation snapshot of the requester/decider
alongside the existing, unchanged immutable machine identities
(`requested_by`, `decided_by`). Both are purely additive and nullable:
no backfill is performed (no historical row's display name can be known
or safely invented), the existing columns and every existing constraint
are untouched, and no row becomes unreadable. Downgrade drops exactly the
two added columns and nothing else.

Revision id is `0049_oqi_remediation_actor_name` (31 chars), deliberately
shorter than this filename: `alembic_version.version_num` is VARCHAR(32)
(CDD-091 §22.6), identical in kind to the CDD-040/CDD-051 and 0046
precedents. Columns are VARCHAR(256), the directory's own documented
displayName bound (CDD-091 §22.7)."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0049_oqi_remediation_actor_name"
down_revision: str | None = "0048_oqi_remediation_mutex"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "oqi_remediation_authorizations",
        sa.Column("requested_by_display_name", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "oqi_remediation_authorizations",
        sa.Column("decided_by_display_name", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oqi_remediation_authorizations", "decided_by_display_name")
    op.drop_column("oqi_remediation_authorizations", "requested_by_display_name")
