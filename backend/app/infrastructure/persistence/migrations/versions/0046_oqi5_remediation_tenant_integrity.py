"""Structurally enforce OQI5 remediation authority chain tenant isolation
at the database level (CDD-061 §9.1, §38; Artifact Authorization row --
POSTGRES-DATA-MODEL-CLOSURE-I).

`oqi_remediation_instructions.fk_oqi_remediation_instructions_case_id`,
`oqi_remediation_authorizations.fk_oqi_remediation_authorizations_instruction_id`,
and `oqi_remediation_agent_runs.fk_oqi_remediation_agent_runs_case_id`
previously carried plain (non-tenant-qualified) foreign keys, proving only
that the referenced parent row exists, never that it belongs to the
child's own tenant -- discovered by POSTGRES-DATA-MODEL-CLOSURE-DG's real
PostgreSQL adversarial verification to let a single remediation lineage
(Case -> Instruction -> Authorization) persist three mutually
inconsistent tenant labels with zero rejection. Reuses the identical,
already-proven-safe migration-0041/0042/0043/0044 (OQI6-R1/R2/R3,
OQI4-R1) pattern: add a tenant-qualified composite candidate key to the
parent table, then replace the plain child FK with a tenant-qualified
composite FK.

`oqi_remediation_candidates`, `oqi_remediation_agent_assessments`, and
`oqi_remediation_agent_recommendations` carry no `tenant_id` column of
their own (CDD-061 CHILD_NOT_TENANT_OWNED classification, the same
legitimate single-hop pattern already used elsewhere, e.g. `source_fields`
-> `source_objects`) -- a composite tenant-qualified FK requires a
tenant_id column on both sides, which does not exist here, so none of
their FKs are touched by this migration. This reconciles CDD-061 §19/§38's
own prose (which named `oqi_remediation_agent_recommendations` as also
needing composite tenant qualification) against the actual schema: that
table has no `tenant_id` column to qualify with, so no such constraint is
implementable or applicable there. The adversarial defect this migration
closes never depended on that table.

Revision id shortened to `0046_oqi5_remediation_tenancy` (29 chars) from the
conceptually-named `0046_oqi5_remediation_tenant_integrity` (38 chars): the
latter does not fit `alembic_version.version_num`'s pre-existing
`VARCHAR(32)` column, discovered empirically running this migration against
real PostgreSQL, identical in kind to the established
CDD-040/CDD-051 Migration-Revision-Length-Correction precedent. Only the
literal `revision` string differs from the conceptual name; the authorized
file path, `down_revision`, and every constraint/table/column decision
below are unchanged.

Constraint-only correction: zero new/dropped table, zero new/dropped
column, zero data rewrite, zero backfill (this environment carries only
demo/test data; no production tenant data exists anywhere this migration
will run against). Governed table count remains 126 before and after.
`0001`-`0045` are unmodified by this migration."""

from collections.abc import Sequence

from alembic import op

revision: str = "0046_oqi5_remediation_tenancy"
down_revision: str | None = "0045_oqi_connector_ingestion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_oqi_remediation_cases_tenant_pk",
        "oqi_remediation_cases",
        ["tenant_id", "case_id"],
    )
    op.create_unique_constraint(
        "uq_oqi_remediation_instructions_tenant_pk",
        "oqi_remediation_instructions",
        ["tenant_id", "instruction_id"],
    )

    op.drop_constraint(
        "fk_oqi_remediation_instructions_case_id",
        "oqi_remediation_instructions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_instructions_tenant_case",
        "oqi_remediation_instructions",
        "oqi_remediation_cases",
        ["tenant_id", "case_id"],
        ["tenant_id", "case_id"],
    )

    op.drop_constraint(
        "fk_oqi_remediation_authorizations_instruction_id",
        "oqi_remediation_authorizations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_authorizations_tenant_instruction",
        "oqi_remediation_authorizations",
        "oqi_remediation_instructions",
        ["tenant_id", "instruction_id"],
        ["tenant_id", "instruction_id"],
    )

    op.drop_constraint(
        "fk_oqi_remediation_agent_runs_case_id",
        "oqi_remediation_agent_runs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_agent_runs_tenant_case",
        "oqi_remediation_agent_runs",
        "oqi_remediation_cases",
        ["tenant_id", "case_id"],
        ["tenant_id", "case_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_oqi_remediation_agent_runs_tenant_case",
        "oqi_remediation_agent_runs",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_agent_runs_case_id",
        "oqi_remediation_agent_runs",
        "oqi_remediation_cases",
        ["case_id"],
        ["case_id"],
    )

    op.drop_constraint(
        "fk_oqi_remediation_authorizations_tenant_instruction",
        "oqi_remediation_authorizations",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_authorizations_instruction_id",
        "oqi_remediation_authorizations",
        "oqi_remediation_instructions",
        ["instruction_id"],
        ["instruction_id"],
    )

    op.drop_constraint(
        "fk_oqi_remediation_instructions_tenant_case",
        "oqi_remediation_instructions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_oqi_remediation_instructions_case_id",
        "oqi_remediation_instructions",
        "oqi_remediation_cases",
        ["case_id"],
        ["case_id"],
    )

    op.drop_constraint(
        "uq_oqi_remediation_instructions_tenant_pk",
        "oqi_remediation_instructions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_oqi_remediation_cases_tenant_pk",
        "oqi_remediation_cases",
        type_="unique",
    )
