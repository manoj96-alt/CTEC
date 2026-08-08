"""Create the canonical ECOM Physical Model v1.3."""

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import text

from alembic import op
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_BUSINESS_DOMAIN_NAME,
    BOOTSTRAP_COUNTRY_ID,
    BOOTSTRAP_COUNTRY_ISO2,
    BOOTSTRAP_COUNTRY_ISO3,
    BOOTSTRAP_COUNTRY_NAME,
    BOOTSTRAP_ENTERPRISE_ID,
    BOOTSTRAP_ENTERPRISE_NAME,
    BOOTSTRAP_ENTERPRISE_TYPE_ID,
    BOOTSTRAP_ENTERPRISE_TYPE_NAME,
    BOOTSTRAP_ENTITY_TYPE,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_GOVERNANCE_STATUS,
    BOOTSTRAP_INSTITUTIONAL_CONCEPT_ID,
    BOOTSTRAP_STATUS,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
    BOOTSTRAP_SYSTEM_NAME,
    SEED_TIMESTAMP,
)

revision: str = "0001_canonical_v1_3"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FOREIGN_KEY_MARKER = "-- ---------- Foreign key constraints ----------"


def _canonical_sql() -> str:
    return (Path(__file__).parents[1] / "canonical_v1_3.sql").read_text()


def _insert_bootstrap_records() -> None:
    connection = op.get_bind()
    common = {
        "lifecycle_state": BOOTSTRAP_STATUS,
        "effective_from": SEED_TIMESTAMP,
        "governance_status": BOOTSTRAP_GOVERNANCE_STATUS,
        "created_by": BOOTSTRAP_SYSTEM_ENTITY_ID,
        "created_on": SEED_TIMESTAMP,
    }
    connection.execute(
        text("INSERT INTO enterprise_types (enterprise_type_id, type_name) VALUES (:id, :name)"),
        {"id": BOOTSTRAP_ENTERPRISE_TYPE_ID, "name": BOOTSTRAP_ENTERPRISE_TYPE_NAME},
    )
    connection.execute(
        text(
            "INSERT INTO countries (country_id, country_name, iso2_code, iso3_code) "
            "VALUES (:id, :name, :iso2, :iso3)"
        ),
        {
            "id": BOOTSTRAP_COUNTRY_ID,
            "name": BOOTSTRAP_COUNTRY_NAME,
            "iso2": BOOTSTRAP_COUNTRY_ISO2,
            "iso3": BOOTSTRAP_COUNTRY_ISO3,
        },
    )
    connection.execute(
        text(
            "INSERT INTO enterprises "
            "(enterprise_id, enterprise_name, enterprise_type_id, country_id, lifecycle_state, "
            "effective_from, governance_status, created_by, created_on, version_number) "
            "VALUES (:id, :name, :enterprise_type_id, :country_id, :lifecycle_state, "
            ":effective_from, :governance_status, :created_by, :created_on, 1)"
        ),
        {
            **common,
            "id": BOOTSTRAP_ENTERPRISE_ID,
            "name": BOOTSTRAP_ENTERPRISE_NAME,
            "enterprise_type_id": BOOTSTRAP_ENTERPRISE_TYPE_ID,
            "country_id": BOOTSTRAP_COUNTRY_ID,
        },
    )
    connection.execute(
        text(
            "INSERT INTO business_domains "
            "(business_domain_id, enterprise_id, domain_name, lifecycle_state, effective_from, "
            "governance_status, created_by, created_on, version_number) "
            "VALUES (:id, :enterprise_id, :name, :lifecycle_state, :effective_from, "
            ":governance_status, :created_by, :created_on, 1)"
        ),
        {
            **common,
            "id": BOOTSTRAP_BUSINESS_DOMAIN_ID,
            "enterprise_id": BOOTSTRAP_ENTERPRISE_ID,
            "name": BOOTSTRAP_BUSINESS_DOMAIN_NAME,
        },
    )
    connection.execute(
        text(
            "INSERT INTO institutional_concepts "
            "(institutional_concept_id, institutional_concept_name, lifecycle_state, "
            "effective_from, governance_status, created_by, created_on, version_number, enterprise_id) "
            "VALUES (:id, :name, :lifecycle_state, :effective_from, :governance_status, "
            ":created_by, :created_on, 1, :enterprise_id)"
        ),
        {
            **common,
            "id": BOOTSTRAP_INSTITUTIONAL_CONCEPT_ID,
            "name": BOOTSTRAP_ENTITY_TYPE,
            "enterprise_id": BOOTSTRAP_ENTERPRISE_ID,
        },
    )
    connection.execute(
        text(
            "INSERT INTO entity_types "
            "(entity_type_id, entity_type_name, lifecycle_state, effective_from, "
            "governance_status, created_by, created_on, version_number, institutional_concept_id) "
            "VALUES (:id, :name, :lifecycle_state, :effective_from, :governance_status, "
            ":created_by, :created_on, 1, :concept_id)"
        ),
        {
            **common,
            "id": BOOTSTRAP_ENTITY_TYPE_ID,
            "name": BOOTSTRAP_ENTITY_TYPE,
            "concept_id": BOOTSTRAP_INSTITUTIONAL_CONCEPT_ID,
        },
    )
    connection.execute(
        text(
            "INSERT INTO enterprise_entities "
            "(enterprise_entity_id, enterprise_entity_name, lifecycle_state, effective_from, "
            "governance_status, created_by, created_on, version_number, entity_type_id, "
            "business_domain_id) VALUES (:id, :name, :lifecycle_state, :effective_from, "
            ":governance_status, :created_by, :created_on, 1, :entity_type_id, :domain_id)"
        ),
        {
            **common,
            "id": BOOTSTRAP_SYSTEM_ENTITY_ID,
            "name": BOOTSTRAP_SYSTEM_NAME,
            "entity_type_id": BOOTSTRAP_ENTITY_TYPE_ID,
            "domain_id": BOOTSTRAP_BUSINESS_DOMAIN_ID,
        },
    )


def upgrade() -> None:
    schema_sql, constraints_sql = _canonical_sql().split(FOREIGN_KEY_MARKER, maxsplit=1)
    connection = op.get_bind()
    connection.exec_driver_sql(schema_sql)
    _insert_bootstrap_records()
    connection.exec_driver_sql(f"{FOREIGN_KEY_MARKER}{constraints_sql}")


def downgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        """
        DROP TABLE IF EXISTS institutional_relationship_assertions CASCADE;
        DROP TABLE IF EXISTS assertion_evidence CASCADE;
        DROP TABLE IF EXISTS reason_evidence CASCADE;
        DROP TABLE IF EXISTS reason_decision_objectives CASCADE;
        DROP TABLE IF EXISTS contexts CASCADE;
        DROP TABLE IF EXISTS institutional_acts CASCADE;
        DROP TABLE IF EXISTS source_objects CASCADE;
        DROP TABLE IF EXISTS source_systems CASCADE;
        DROP TABLE IF EXISTS accountable_owners CASCADE;
        DROP TABLE IF EXISTS governances CASCADE;
        DROP TABLE IF EXISTS experiences CASCADE;
        DROP TABLE IF EXISTS outcomes CASCADE;
        DROP TABLE IF EXISTS institutional_actions CASCADE;
        DROP TABLE IF EXISTS decision_states CASCADE;
        DROP TABLE IF EXISTS decisions CASCADE;
        DROP TABLE IF EXISTS pattern_of_relevances CASCADE;
        DROP TABLE IF EXISTS occasions CASCADE;
        DROP TABLE IF EXISTS decision_objectives CASCADE;
        DROP TABLE IF EXISTS reason_graphs CASCADE;
        DROP TABLE IF EXISTS reasons CASCADE;
        DROP TABLE IF EXISTS knowledges CASCADE;
        DROP TABLE IF EXISTS institutional_relationships CASCADE;
        DROP TABLE IF EXISTS assertions CASCADE;
        DROP TABLE IF EXISTS evidences CASCADE;
        DROP TABLE IF EXISTS enterprise_entities CASCADE;
        DROP TABLE IF EXISTS entity_types CASCADE;
        DROP TABLE IF EXISTS relationship_types CASCADE;
        DROP TABLE IF EXISTS institutional_concepts CASCADE;
        DROP TABLE IF EXISTS business_domains CASCADE;
        DROP TABLE IF EXISTS countries CASCADE;
        DROP TABLE IF EXISTS enterprise_types CASCADE;
        DROP TABLE IF EXISTS enterprises CASCADE;
        DROP TYPE IF EXISTS occasionlifecycle_t;
        DROP TYPE IF EXISTS decisionstatestatus_t;
        DROP TYPE IF EXISTS assertiontype_t;
        DROP TYPE IF EXISTS governancestatus_t;
        DROP TYPE IF EXISTS lifecyclestate_t;
        """
    )
