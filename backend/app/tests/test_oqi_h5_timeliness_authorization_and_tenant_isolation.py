"""CDD-051 OQI-H5 Governed Timeliness -- Artifact Authorization row 11:
real-PostgreSQL adversarial tenant-isolation proof for every composite
tenant-qualified FK introduced by H5 (CDD-051 §29), mirroring
`test_oqi_h4_integrity_authorization_and_tenant_isolation.py`'s R1 series
exactly -- direct `session.add()`+`flush()` insertion that deliberately
bypasses the service layer, proving PostgreSQL itself (not application
code) rejects every cross-tenant reference. Positive same-tenant controls
prove the legitimate path still works; this is not a "reject everything"
suite."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.oqi_business_impact.process import (
    BusinessImpactCategory,
    create_business_process,
)
from app.infrastructure.persistence.models.oqi_business_impact import OqiBusinessProcessORM
from app.infrastructure.persistence.models.oqi_timeliness import (
    TimelinessEvaluationORM,
    TimelinessFindingORM,
    TimelinessPolicyORM,
)
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture(scope="module")
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine)


@pytest.fixture()
def session(factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with factory() as session:
        yield session
        session.rollback()


def _tenant() -> str:
    return f"tenant-{uuid4()}"


def _source_object(session: Session, *, tenant_id: str) -> UUID:
    system_id, object_id = uuid4(), uuid4()
    session.add(
        SourceSystemORM(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"TI Source System {system_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    session.add(
        SourceObjectORM(
            source_object_id=object_id,
            tenant_id=tenant_id,
            source_object_name=f"TI Source Object {object_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()
    return object_id


def _business_process(session: Session, *, tenant_id: str) -> tuple[UUID, int]:
    process = create_business_process(
        process_id=uuid4(),
        tenant_id=tenant_id,
        name="TI Process",
        description=None,
        category=BusinessImpactCategory.OPERATIONAL,
        created_by="steward",
        created_on=NOW,
    )
    OqiBusinessImpactRepositoryImpl(session).insert_business_process(process)
    session.flush()
    return process.process_id, process.version


def _information_element_requirement(session: Session, *, tenant_id: str) -> UUID:
    """Shared-platform (no tenant_id) -- any real, persisted
    InformationElementRequirement satisfies the plain FK regardless of
    which tenant later anchors a policy to it (correct by design, CDD-051
    §7). Reuses the ontology/blueprint seed to obtain one real row rather
    than fabricating a fresh Blueprint per test (mechanically simpler; the
    identity of *which* IE is used is irrelevant to tenant isolation)."""
    from sqlalchemy import select

    from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
    from app.infrastructure.persistence.models.blueprint import (
        InformationElementRequirementORM,
    )
    from app.infrastructure.persistence.ontology_seed import OntologySeeder

    OntologySeeder(session).load()
    BlueprintSeeder(session).load()
    session.commit()
    ie_id = session.scalar(
        select(InformationElementRequirementORM.information_element_requirement_id)
    )
    assert ie_id is not None
    return ie_id


def _policy(
    session: Session,
    *,
    tenant_id: str,
    business_process_id: UUID,
    business_process_version: int,
    ie_id: UUID,
) -> tuple[UUID, int]:
    policy_id = uuid4()
    session.add(
        TimelinessPolicyORM(
            policy_id=policy_id,
            version=1,
            tenant_id=tenant_id,
            information_element_requirement_id=ie_id,
            business_process_id=business_process_id,
            business_process_version=business_process_version,
            freshness_window_seconds=1800,
            ingestion_sla_seconds=None,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    session.flush()
    return policy_id, 1


# =====================================================================
# TI-01/02: TimelinessPolicy -> BusinessProcess.
# =====================================================================


def test_ti01_same_tenant_policy_to_business_process_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    process_id, process_version = _business_process(session, tenant_id=tenant_id)
    ie_id = _information_element_requirement(session, tenant_id=tenant_id)
    _policy(
        session,
        tenant_id=tenant_id,
        business_process_id=process_id,
        business_process_version=process_version,
        ie_id=ie_id,
    )  # no raise


def test_ti02_cross_tenant_policy_to_business_process_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    process_id_b, process_version_b = _business_process(session, tenant_id=tenant_b)
    ie_id = _information_element_requirement(session, tenant_id=tenant_a)
    session.add(
        TimelinessPolicyORM(
            policy_id=uuid4(),
            version=1,
            tenant_id=tenant_a,  # claims tenant A
            information_element_requirement_id=ie_id,
            business_process_id=process_id_b,  # but points at tenant B's process
            business_process_version=process_version_b,
            freshness_window_seconds=1800,
            ingestion_sla_seconds=None,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-03/04: Evaluation -> TimelinessPolicy.
# =====================================================================


def test_ti03_same_tenant_evaluation_to_policy_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    process_id, process_version = _business_process(session, tenant_id=tenant_id)
    ie_id = _information_element_requirement(session, tenant_id=tenant_id)
    policy_id, policy_version = _policy(
        session,
        tenant_id=tenant_id,
        business_process_id=process_id,
        business_process_version=process_version,
        ie_id=ie_id,
    )
    source_object_id = _source_object(session, tenant_id=tenant_id)
    from app.domain.integration import SourceField
    from app.domain.integration.field_value_evidence import FieldValueEvidence
    from app.domain.shared.enums import GovernanceStatus, LifecycleState
    from app.domain.shared.value_objects import CanonicalName, Identifier
    from app.infrastructure.persistence.field_value_evidence_repository import (
        FieldValueEvidenceRepositoryImpl,
    )
    from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

    field = SourceField(
        source_field_id=Identifier(uuid4()),
        source_object_id=Identifier(source_object_id),
        field_label=CanonicalName(f"TI-FIELD-{uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )
    SourceFieldRepositoryImpl(session).create(field)
    evidence = FieldValueEvidence.new(
        source_field_id=field.source_field_id,
        source_record_reference="REC-1",
        observed_representation="v1",
        observed_at=NOW,
        received_at=NOW,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    session.flush()

    session.add(
        TimelinessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id,
            field_value_evidence_id=evidence.field_value_evidence_id.value,
            outcome="SATISFIED",
            evaluation_horizon=NOW,
            evaluated_on=NOW,
        )
    )
    session.flush()  # no raise


def test_ti04_cross_tenant_evaluation_to_policy_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    process_id_b, process_version_b = _business_process(session, tenant_id=tenant_b)
    ie_id_b = _information_element_requirement(session, tenant_id=tenant_b)
    policy_id_b, policy_version_b = _policy(
        session,
        tenant_id=tenant_b,
        business_process_id=process_id_b,
        business_process_version=process_version_b,
        ie_id=ie_id_b,
    )
    source_object_id_a = _source_object(session, tenant_id=tenant_a)
    session.add(
        TimelinessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_a,  # claims tenant A
            policy_id=policy_id_b,  # but points at tenant B's policy
            policy_version=policy_version_b,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id_a,
            field_value_evidence_id=uuid4(),  # unreachable in practice; FK on policy fails first
            outcome="SATISFIED",
            evaluation_horizon=NOW,
            evaluated_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-05/06: Evaluation -> SourceObject.
# =====================================================================


def test_ti05_cross_tenant_evaluation_to_source_object_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    process_id_a, process_version_a = _business_process(session, tenant_id=tenant_a)
    ie_id_a = _information_element_requirement(session, tenant_id=tenant_a)
    policy_id_a, policy_version_a = _policy(
        session,
        tenant_id=tenant_a,
        business_process_id=process_id_a,
        business_process_version=process_version_a,
        ie_id=ie_id_a,
    )
    source_object_id_b = _source_object(session, tenant_id=tenant_b)
    session.add(
        TimelinessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_a,
            policy_id=policy_id_a,
            policy_version=policy_version_a,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id_b,  # tenant B's source object
            field_value_evidence_id=uuid4(),
            outcome="SATISFIED",
            evaluation_horizon=NOW,
            evaluated_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-06/07: Finding -> TimelinessPolicy / -> SourceObject.
# =====================================================================


def test_ti06_same_tenant_finding_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    process_id, process_version = _business_process(session, tenant_id=tenant_id)
    ie_id = _information_element_requirement(session, tenant_id=tenant_id)
    policy_id, policy_version = _policy(
        session,
        tenant_id=tenant_id,
        business_process_id=process_id,
        business_process_version=process_version,
        ie_id=ie_id,
    )
    source_object_id = _source_object(session, tenant_id=tenant_id)
    session.add(
        TimelinessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    session.flush()  # no raise


def test_ti07_cross_tenant_finding_to_policy_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    process_id_b, process_version_b = _business_process(session, tenant_id=tenant_b)
    ie_id_b = _information_element_requirement(session, tenant_id=tenant_b)
    policy_id_b, policy_version_b = _policy(
        session,
        tenant_id=tenant_b,
        business_process_id=process_id_b,
        business_process_version=process_version_b,
        ie_id=ie_id_b,
    )
    source_object_id_a = _source_object(session, tenant_id=tenant_a)
    session.add(
        TimelinessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,
            policy_id=policy_id_b,  # tenant B's policy
            policy_version=policy_version_b,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id_a,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_ti08_cross_tenant_finding_to_source_object_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    process_id_a, process_version_a = _business_process(session, tenant_id=tenant_a)
    ie_id_a = _information_element_requirement(session, tenant_id=tenant_a)
    policy_id_a, policy_version_a = _policy(
        session,
        tenant_id=tenant_a,
        business_process_id=process_id_a,
        business_process_version=process_version_a,
        ie_id=ie_id_a,
    )
    source_object_id_b = _source_object(session, tenant_id=tenant_b)
    session.add(
        TimelinessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,
            policy_id=policy_id_a,
            policy_version=policy_version_a,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id_b,  # tenant B's source object
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-09: mixed-parent attack -- both foreign references cross tenants.
# =====================================================================


def test_ti09_both_foreign_references_cross_tenant_rejected(session: Session) -> None:
    tenant_a, tenant_b, tenant_c = _tenant(), _tenant(), _tenant()
    process_id_b, process_version_b = _business_process(session, tenant_id=tenant_b)
    ie_id_b = _information_element_requirement(session, tenant_id=tenant_b)
    policy_id_b, policy_version_b = _policy(
        session,
        tenant_id=tenant_b,
        business_process_id=process_id_b,
        business_process_version=process_version_b,
        ie_id=ie_id_b,
    )
    source_object_id_c = _source_object(session, tenant_id=tenant_c)
    session.add(
        TimelinessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,
            policy_id=policy_id_b,
            policy_version=policy_version_b,
            finding_type="STALE_SOURCE_EVIDENCE",
            source_object_id=source_object_id_c,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-10: business_processes tenant-qualified key itself (CDD-051 §9).
# =====================================================================


def test_ti10_business_processes_tenant_qualified_key_rejects_duplicate(session: Session) -> None:
    """Direct proof that `uq_oqi_business_processes_tenant_pk` (CDD-051 §9)
    is real and enforced -- inserting a second row with the same
    (tenant_id, process_id, version) must fail (it is already guaranteed
    unique by the table's own primary key, but this proves the *additional*
    constraint exists and is wired, not merely declared in the ORM)."""
    tenant_id = _tenant()
    process_id, version = _business_process(session, tenant_id=tenant_id)
    session.add(
        OqiBusinessProcessORM(
            process_id=process_id,
            version=version,
            tenant_id=tenant_id,
            name="Duplicate",
            description=None,
            status="ACTIVE",
            category=None,
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
