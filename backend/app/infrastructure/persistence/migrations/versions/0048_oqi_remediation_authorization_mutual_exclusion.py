"""Structurally enforce single-effective-approval for mutually-exclusive
remediation candidates at the database level (CDD-085 G-R3 Sec10-Sec14,
G-R4 Sec4).

NOETVA-GOLDEN-SIGNATURE-UX-DR-R1's own live adversarial probe proved that
today's `oqi_remediation_authorizations` table structurally permits two
sibling authorizations of the same remediation case (e.g. a Finding's real
`US` and `MX` remediation candidates) to both independently reach
`APPROVED` -- nothing ties sibling authorizations of one case together, and
`OqiRemediationService.approve()`'s own row lock (`SELECT ... FOR UPDATE`)
is scoped only to the single authorization being decided, never the parent
case or its siblings.

The primary correction (this migration's sibling change, CDD-085 G-R3
Sec12/Sec13) makes `approve()` lock the parent case and supersede sibling
PENDING authorizations in the same transaction. This migration adds the
database-level defense-in-depth: a denormalized `case_id` column on
`oqi_remediation_authorizations` (mirroring the pre-existing precedent
where `oqi_remediation_instructions` already denormalizes `finding_id` even
though it is reachable via `case_id`) backing a partial unique index that
makes PostgreSQL itself reject a second `APPROVED` row for the same case,
independent of the application layer ever being bypassed.

Pre-existing row safety, mirroring migration 0012's own precedent exactly:
`case_id` is always deterministically resolvable for every existing
authorization row via the existing, unbroken FK chain
`authorization.instruction_id -> instruction.case_id` (both NOT NULL,
both FK-enforced) -- so backfill can never leave an unresolved row. But
before enforcing the new invariant, this migration additionally verifies no
already-persisted case currently holds more than one `APPROVED`
authorization; if one is found, the migration raises before any schema
change is applied, exactly as 0012 does for its own pre-existing-data
safety check -- this migration never silently picks a winner among
conflicting historical approvals."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0048_oqi_remediation_mutex"
down_revision: str | None = "0047_oqi_h6_uniqueness"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class RemediationDuplicateApprovalError(RuntimeError):
    """Raised when a pre-existing case already holds more than one
    APPROVED remediation authorization -- the exact invalid historical
    state the new partial unique index is about to forbid going forward.
    No schema change is applied before this can be raised."""


def _find_duplicate_approvals(bind: sa.engine.Connection) -> list[str]:
    rows = bind.execute(
        sa.text(
            """
            SELECT i.case_id AS case_id, COUNT(*) AS approved_count
            FROM oqi_remediation_authorizations a
            JOIN oqi_remediation_instructions i ON i.instruction_id = a.instruction_id
            WHERE a.status = 'APPROVED'
            GROUP BY i.case_id
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    return [f"case_id={row.case_id}: {row.approved_count} APPROVED authorizations" for row in rows]


def upgrade() -> None:
    bind = op.get_bind()

    blocking = _find_duplicate_approvals(bind)
    if blocking:
        raise RemediationDuplicateApprovalError(
            "0048_oqi_remediation_authorization_mutual_exclusion: refusing to add "
            "the single-effective-approval partial unique index -- "
            f"{len(blocking)} pre-existing case(s) already hold more than one "
            "APPROVED remediation authorization. No schema change has been "
            "applied. This requires a governed data-repair decision, not an "
            "automatic migration choice. Blocking case(s):\n" + "\n".join(blocking)
        )

    op.add_column(
        "oqi_remediation_authorizations", sa.Column("case_id", sa.Uuid(), nullable=True)
    )
    bind.execute(
        sa.text(
            """
            UPDATE oqi_remediation_authorizations a
            SET case_id = i.case_id
            FROM oqi_remediation_instructions i
            WHERE i.instruction_id = a.instruction_id
            """
        )
    )
    op.alter_column("oqi_remediation_authorizations", "case_id", nullable=False)

    op.create_index(
        "idx_oqi_remediation_authorizations_case_id",
        "oqi_remediation_authorizations",
        ["case_id"],
    )
    op.create_foreign_key(
        "fk_oqi_remediation_authorizations_case_id",
        "oqi_remediation_authorizations",
        "oqi_remediation_cases",
        ["case_id"],
        ["case_id"],
    )
    op.create_index(
        "uq_oqi_remediation_authorizations_case_one_approved",
        "oqi_remediation_authorizations",
        ["case_id"],
        unique=True,
        postgresql_where=sa.text("status = 'APPROVED'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_oqi_remediation_authorizations_case_one_approved",
        table_name="oqi_remediation_authorizations",
    )
    op.drop_constraint(
        "fk_oqi_remediation_authorizations_case_id",
        "oqi_remediation_authorizations",
        type_="foreignkey",
    )
    op.drop_index(
        "idx_oqi_remediation_authorizations_case_id",
        table_name="oqi_remediation_authorizations",
    )
    op.drop_column("oqi_remediation_authorizations", "case_id")
