"""PostgreSQL-backed proof of DemoEntityResolutionSeeder: seeding the
labeled demo tenant produces exactly the three honest TSMC evidence cases
with the expected outcomes, seeding is idempotent (a second run creates
nothing new), and a real (non-fake) session still refuses to write
anything for a non-demo tenant.
"""

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.domain.identity_resolution.model import BusinessConfidence, ResolutionOutcome
from app.infrastructure.persistence.demo_entity_resolution_seeder import (
    DemoEntityResolutionSeeder,
    DemoTenantRequiredError,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)


def test_seeding_the_demo_tenant_creates_the_three_honest_cases(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        summary = DemoEntityResolutionSeeder(session).seed()

    assert summary.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
    assert summary.no_strong_identifier.created is True
    assert summary.matching_strong_identifier.created is True
    assert summary.conflicting_strong_identifiers.created is True

    keys = {
        summary.no_strong_identifier.understanding_key,
        summary.matching_strong_identifier.understanding_key,
        summary.conflicting_strong_identifiers.understanding_key,
    }
    assert len(keys) == 3  # three genuinely distinct cases, not one repeated

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)

        no_strong_id = store.get_current_record(
            BOOTSTRAP_DEMO_TENANT_ID, summary.no_strong_identifier.understanding_key
        )
        assert no_strong_id is not None
        assert no_strong_id.outcome == ResolutionOutcome.POSSIBLE.value
        assert no_strong_id.business_confidence == BusinessConfidence.MEDIUM.value
        assert no_strong_id.enterprise_entity_id is not None

        matching = store.get_current_record(
            BOOTSTRAP_DEMO_TENANT_ID, summary.matching_strong_identifier.understanding_key
        )
        assert matching is not None
        assert matching.outcome == ResolutionOutcome.RESOLVED.value
        assert matching.business_confidence == BusinessConfidence.HIGH.value
        assert matching.enterprise_entity_id is not None

        conflicting = store.get_current_record(
            BOOTSTRAP_DEMO_TENANT_ID, summary.conflicting_strong_identifiers.understanding_key
        )
        assert conflicting is not None
        assert conflicting.outcome == ResolutionOutcome.BLOCKED_CONFLICT.value
        assert conflicting.enterprise_entity_id is None
        assert conflicting.evidence_profile is not None
        veto_items = [
            item
            for item in conflicting.evidence_profile["items"]
            if item["classification"] == "Veto"
        ]
        assert veto_items


def test_seeding_twice_is_idempotent(migrated_engine: Engine) -> None:
    with Session(migrated_engine) as session, session.begin():
        first = DemoEntityResolutionSeeder(session).seed()

    with Session(migrated_engine) as session:
        record_count_after_first = len(
            session.scalars(
                select(EnterpriseEntityResolutionRecordModel.record_id).where(
                    EnterpriseEntityResolutionRecordModel.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
                )
            ).all()
        )

    with Session(migrated_engine) as session, session.begin():
        second = DemoEntityResolutionSeeder(session).seed()

    assert second.no_strong_identifier.created is False
    assert second.matching_strong_identifier.created is False
    assert second.conflicting_strong_identifiers.created is False
    assert (
        second.no_strong_identifier.understanding_key
        == first.no_strong_identifier.understanding_key
    )
    assert (
        second.matching_strong_identifier.understanding_key
        == first.matching_strong_identifier.understanding_key
    )
    assert (
        second.conflicting_strong_identifiers.understanding_key
        == first.conflicting_strong_identifiers.understanding_key
    )

    with Session(migrated_engine) as session:
        record_count_after_second = len(
            session.scalars(
                select(EnterpriseEntityResolutionRecordModel.record_id).where(
                    EnterpriseEntityResolutionRecordModel.tenant_id == BOOTSTRAP_DEMO_TENANT_ID
                )
            ).all()
        )

    assert record_count_after_second == record_count_after_first


def test_real_session_still_refuses_a_non_demo_tenant_and_writes_nothing(
    migrated_engine: Engine,
) -> None:
    other_tenant = "tenant-not-the-demo-tenant"
    with Session(migrated_engine) as session, session.begin():
        try:
            DemoEntityResolutionSeeder(session).seed(tenant_id=other_tenant)
            raised = False
        except DemoTenantRequiredError:
            raised = True
        assert raised

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        assert store.list_current_records(other_tenant) == []
