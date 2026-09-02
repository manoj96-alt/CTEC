"""Create OQI-H2 governed Reference Evidence persistence (CDD-048 §15-§16;
Artifact Authorization row 9).

Six new tables: `oqi_reference_evidence_assertions` (envelope),
`oqi_governed_reference_dataset_entries`/`oqi_human_verified_evidence_
entries`/`oqi_business_rule_derived_reference_entries` (1:1 form-specific
children), `oqi_reference_evidence_conflicts` (mutable governance
condition), `oqi_reference_evidence_conflict_members` (normalized conflict
membership). No existing table is altered by this migration. No row of any
new table is created by this migration."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028_oqi_h2_reference_evidence"
down_revision: str | None = "0027_h1_coverage_policy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REFERENCE_EVIDENCE_FORM_VALUES = (
    "GOVERNED_REFERENCE_DATASET",
    "HUMAN_VERIFIED_EVIDENCE",
    "BUSINESS_RULE_DERIVED_VALUE",
)
_REFERENCE_EVIDENCE_FORM_CHECK_SQL = "form IN ({})".format(
    ", ".join(f"'{value}'" for value in _REFERENCE_EVIDENCE_FORM_VALUES)
)


def upgrade() -> None:
    op.create_table(
        "oqi_reference_evidence_assertions",
        sa.Column("assertion_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id",
                name="fk_oqi_reference_evidence_assertions_source_field_id",
            ),
            nullable=False,
        ),
        sa.Column("form", sa.String(32), nullable=False),
        sa.Column("asserted_value", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "previous_version_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_reference_evidence_assertions_previous_version_id",
            ),
            nullable=True,
        ),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_on", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retired_on", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_reference_evidence_assertions_anchor_type",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RETIRED')", name="ck_oqi_reference_evidence_assertions_status"
        ),
        sa.CheckConstraint(
            _REFERENCE_EVIDENCE_FORM_CHECK_SQL, name="ck_oqi_reference_evidence_assertions_form"
        ),
    )
    op.create_index(
        "idx_oqi_reference_evidence_assertions_tenant_id",
        "oqi_reference_evidence_assertions",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_reference_evidence_assertions_anchor",
        "oqi_reference_evidence_assertions",
        ["tenant_id", "ontology_element_type", "ontology_element_id", "source_field_id"],
    )
    op.create_index(
        "uq_oqi_reference_evidence_assertions_one_active",
        "oqi_reference_evidence_assertions",
        ["tenant_id", "ontology_element_type", "ontology_element_id", "source_field_id", "form"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "oqi_governed_reference_dataset_entries",
        sa.Column(
            "assertion_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_governed_reference_dataset_entries_assertion_id",
            ),
            primary_key=True,
        ),
        sa.Column("dataset_name", sa.String(200), nullable=False),
        sa.Column("dataset_version", sa.String(64), nullable=False),
        sa.Column("entry_key", sa.String(1000), nullable=False),
    )

    op.create_table(
        "oqi_human_verified_evidence_entries",
        sa.Column(
            "assertion_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_human_verified_evidence_entries_assertion_id",
            ),
            primary_key=True,
        ),
        sa.Column("verifying_actor_id", sa.String(200), nullable=False),
        sa.Column("verification_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_rationale", sa.String(4000), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "oqi_business_rule_derived_reference_entries",
        sa.Column(
            "assertion_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_business_rule_derived_reference_entries_assertion_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "deriving_business_rule_id",
            sa.Uuid(),
            sa.ForeignKey(
                "business_rules.rule_id",
                name="fk_oqi_business_rule_derived_reference_entries_rule_id",
            ),
            nullable=False,
        ),
        sa.Column("deriving_rule_version", sa.Integer(), nullable=False),
        sa.Column(
            "deriving_evaluation_id",
            sa.Uuid(),
            sa.ForeignKey(
                "business_rule_evaluations.evaluation_id",
                name="fk_oqi_business_rule_derived_reference_entries_evaluation_id",
            ),
            nullable=False,
        ),
    )

    op.create_table(
        "oqi_reference_evidence_conflicts",
        sa.Column("conflict_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.String(200), nullable=False),
        sa.Column("ontology_element_type", sa.String(16), nullable=False),
        sa.Column("ontology_element_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_field_id",
            sa.Uuid(),
            sa.ForeignKey(
                "source_fields.source_field_id",
                name="fk_oqi_reference_evidence_conflicts_source_field_id",
            ),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "ontology_element_type IN ('ENTITY', 'RELATIONSHIP')",
            name="ck_oqi_reference_evidence_conflicts_anchor_type",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'RESOLVED')", name="ck_oqi_reference_evidence_conflicts_status"
        ),
    )
    op.create_index(
        "idx_oqi_reference_evidence_conflicts_tenant_id",
        "oqi_reference_evidence_conflicts",
        ["tenant_id"],
    )
    op.create_index(
        "idx_oqi_reference_evidence_conflicts_anchor",
        "oqi_reference_evidence_conflicts",
        ["tenant_id", "ontology_element_type", "ontology_element_id", "source_field_id"],
    )

    op.create_table(
        "oqi_reference_evidence_conflict_members",
        sa.Column(
            "conflict_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_conflicts.conflict_id",
                name="fk_oqi_reference_evidence_conflict_members_conflict_id",
            ),
            primary_key=True,
        ),
        sa.Column(
            "assertion_id",
            sa.Uuid(),
            sa.ForeignKey(
                "oqi_reference_evidence_assertions.assertion_id",
                name="fk_oqi_reference_evidence_conflict_members_assertion_id",
            ),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    # Children before their parents.
    op.drop_table("oqi_reference_evidence_conflict_members")
    op.drop_table("oqi_reference_evidence_conflicts")
    op.drop_table("oqi_business_rule_derived_reference_entries")
    op.drop_table("oqi_human_verified_evidence_entries")
    op.drop_table("oqi_governed_reference_dataset_entries")
    op.drop_table("oqi_reference_evidence_assertions")
