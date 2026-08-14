"""Focused PostgreSQL proof that the identity-resolution substrate cannot
leak data across tenant boundaries, per the Increment 3A tenant-foundation
gate. Composite foreign keys are expected to reject cross-tenant references
at the database level (sqlalchemy.exc.IntegrityError), independent of any
application-layer check.

Every tenant id used here is generated fresh per test (never a literal like
"tenant-a") because `migrated_engine` is a session-scoped fixture shared
across the whole test file: a literal tenant id could collide with data
another test module writes under the same name within the same pytest
session, producing a false isolation failure.
"""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.identity_resolution import EntityResolutionEngine, ResolutionPolicy
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.resolution_policy import ResolutionPolicyModel
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.runtime.orchestration import CapabilityStepError, CapabilityStepInput
from app.tests.test_supplier_risk_pipeline import runtime_and_persistence

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def _seed_enterprise_entity(session: Session, *, tenant_id: str, name: str) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=BOOTSTRAP_ENTITY_TYPE_ID,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _seed_source_system(session: Session, *, tenant_id: str, name: str) -> UUID:
    system_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    return system_id


def _seed_source_object(
    session: Session, *, tenant_id: str, source_system_id: UUID, name: str
) -> UUID:
    object_id = uuid4()
    session.add(
        SourceObject(
            source_object_id=object_id,
            tenant_id=tenant_id,
            source_object_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=source_system_id,
        )
    )
    session.flush()
    return object_id


def _seed_policy(session: Session, *, tenant_id: str, name: str) -> UUID:
    policy_id = uuid4()
    session.add(
        ResolutionPolicyModel(
            policy_id=policy_id,
            tenant_id=tenant_id,
            policy_name=name,
            policy_version="v1.0",
            preset_kind=name,
            definition={},
            status="Active",
            created_on=NOW,
        )
    )
    session.flush()
    return policy_id


def test_tenant_a_cannot_list_or_get_tenant_b_case(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        system_id = _seed_source_system(session, tenant_id=tenant_b, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_b, source_system_id=system_id, name=f"obj-{uuid4()}"
        )

    engine = EntityResolutionEngine(ResolutionPolicy(version="isolation-policy"))
    record = engine.resolve(
        tenant_id=tenant_b,
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=NOW,
    )
    understanding_key = EntityResolutionStore.understanding_key((source_id,))

    with Session(migrated_engine) as session, session.begin():
        EntityResolutionStore(session).append(record)

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        # Tenant A's queue must never include tenant B's case.
        assert store.list_current_records(tenant_a) == []
        # Guessing tenant B's real, valid understanding_key must not work
        # from tenant A's context.
        assert store.get_current_record(tenant_a, understanding_key) is None
        # Sanity: tenant B itself can still see its own case.
        own = store.get_current_record(tenant_b, understanding_key)
        assert own is not None and own.record_id == record.record_id


def test_tenant_a_cannot_resolve_against_tenant_b_enterprise_entity(
    migrated_engine: Engine,
) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        tenant_b_entity_id = _seed_enterprise_entity(
            session, tenant_id=tenant_b, name=f"Tenant B Co {uuid4()}"
        )
        system_id = _seed_source_system(session, tenant_id=tenant_a, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_a, source_system_id=system_id, name=f"obj-{uuid4()}"
        )

    engine = EntityResolutionEngine(ResolutionPolicy(version="isolation-policy"))
    record = engine.resolve(
        tenant_id=tenant_a,
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=NOW,
        override_entity_id=tenant_b_entity_id,
    )

    with pytest.raises(IntegrityError), Session(migrated_engine) as session, session.begin():
        EntityResolutionStore(session).append(record)


def test_tenant_a_cannot_reference_tenant_b_source_system(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        tenant_b_system_id = _seed_source_system(session, tenant_id=tenant_b, name=f"sys-{uuid4()}")

    with pytest.raises(IntegrityError), Session(migrated_engine) as session, session.begin():
        session.add(
            SourceObject(
                source_object_id=uuid4(),
                tenant_id=tenant_a,
                source_object_name=f"obj-{uuid4()}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                source_system_id=tenant_b_system_id,
            )
        )


def test_tenant_a_cannot_reference_tenant_b_policy(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        tenant_b_policy_id = _seed_policy(session, tenant_id=tenant_b, name="Conservative")
        system_id = _seed_source_system(session, tenant_id=tenant_a, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_a, source_system_id=system_id, name=f"obj-{uuid4()}"
        )

    engine = EntityResolutionEngine(ResolutionPolicy(version="isolation-policy"))
    base = engine.resolve(
        tenant_id=tenant_a,
        supporting_source_object_ids=(source_id,),
        candidates=(),
        produced_at=NOW,
    )
    record = replace(base, policy_id=tenant_b_policy_id)

    with pytest.raises(IntegrityError), Session(migrated_engine) as session, session.begin():
        EntityResolutionStore(session).append(record)


def test_missing_trusted_tenant_context_fails_closed() -> None:
    runtime, _ = runtime_and_persistence()
    adapter = runtime._orchestrator._ports.erm
    step_input = CapabilityStepInput(
        "2.0", uuid4(), uuid4(), uuid4(), uuid4(), b"", authority_context=None
    )
    with pytest.raises(CapabilityStepError):
        adapter.execute(step_input)


def test_identical_human_readable_names_allowed_across_tenants_not_within_one(
    migrated_engine: Engine,
) -> None:
    """Uses a single uncommitted transaction throughout (flush, never
    commit) so that proving cross-tenant name reuse succeeds does not leave
    behind data that would make the pre-0011 uniqueness constraint
    unsatisfiable if this session's migrated_engine fixture later downgrades
    back past 0011 during teardown."""
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    shared_name = f"Acme Holdings {uuid4()}"
    shared_system_name = f"SAP {uuid4()}"
    with Session(migrated_engine) as session:
        _seed_enterprise_entity(session, tenant_id=tenant_a, name=shared_name)
        _seed_enterprise_entity(session, tenant_id=tenant_b, name=shared_name)

        with pytest.raises(IntegrityError):
            _seed_enterprise_entity(session, tenant_id=tenant_a, name=shared_name)
        session.rollback()

        _seed_source_system(session, tenant_id=tenant_a, name=shared_system_name)
        _seed_source_system(session, tenant_id=tenant_b, name=shared_system_name)

        with pytest.raises(IntegrityError):
            _seed_source_system(session, tenant_id=tenant_a, name=shared_system_name)
        session.rollback()
        # No commit: the whole test's writes are discarded on session close.
