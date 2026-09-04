"""CDD-051 OQI-H5 Governed Timeliness -- Artifact Authorization row 10: the
real-PostgreSQL crown suite. Both Finding types (STALE_SOURCE_EVIDENCE,
INGESTION_LATENCY_EXCEEDED), the exact inclusive threshold boundary, every
NOT_EVALUABLE case (CDD-051 §6), historical/as-of evaluation using a
caller-supplied `evaluation_horizon` distinct from wall-clock `now()`, a
re-ingestion laundering-resistance proof, idempotent replay, the full
six-branch lifecycle, real-PostgreSQL structural invariants (CHECK
constraints, partial unique index), OQI4 origin/subject resolution, and
H1-H4 crown + OQI6 non-regression after the narrow additive
`oqi_business_processes` correction (CDD-051 §9) -- all against real seeded
data flowing through the real evaluator, never a directly-inserted
conclusion (CDD-046 §45)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_timeliness_evaluation_service import OqiTimelinessEvaluationService
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.integration import SourceField
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.quality_rule import QualityDimension
from app.domain.oqi_business_impact.process import (
    BusinessImpactCategory,
    create_business_process,
)
from app.domain.oqi_finding_origin.origin import FindingStorageFamily
from app.domain.oqi_ontology_impact.evaluation import ImpactOutcome
from app.domain.oqi_timeliness.evaluation import (
    TimelinessFindingStatus,
    TimelinessFindingType,
)
from app.domain.oqi_timeliness.policy import new_timeliness_policy
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.oqi_timeliness import (
    TimelinessEvaluationORM,
    TimelinessPolicyORM,
)
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_timeliness_evaluation_repository import (
    OqiTimelinessEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_timeliness_policy_repository import (
    OqiTimelinessPolicyRepositoryImpl,
)
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

NOW = datetime(2026, 9, 3, 15, 0, 0, tzinfo=UTC)


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


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _seed_mapped_element(session: Session, *, tenant_id: str) -> tuple[UUID, UUID]:
    """Mirrors `test_information_element_evidence_fitness_resolution_
    postgres.py`'s own established `_seed_mapped_element` fixture pattern:
    a fresh Blueprint with one InformationElementRequirement, a real
    SourceSystem/SourceObject/SourceField, and an Approved SemanticMapping.
    Returns `(information_element_requirement_id, source_field_id)`."""
    OntologySeeder(session).load()
    session.commit()

    supplier_type_id = _entity_type_id(session, "Supplier")
    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    requirement_id = Identifier(uuid4())
    blueprint = Blueprint(
        blueprint_id=blueprint_id,
        blueprint_name=CanonicalName(f"CDD-051 H5 Crown Blueprint {uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_requirement_id,
                blueprint_id=blueprint_id,
                entity_type_id=supplier_type_id,
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=requirement_id,
                        concept_requirement_id=concept_requirement_id,
                        element_name=CanonicalName("Shipment Expected Arrival"),
                        description=Description("CDD-051 H5 crown fixture element."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        ),
    )
    BlueprintRepositoryImpl(session).create(blueprint)

    system_id, object_id = uuid4(), uuid4()
    session.add(
        SourceSystemORM(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"CDD-051 Carrier Feed {system_id}",
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
            source_object_name=f"CDD-051 Shipment Source Object {object_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=system_id,
        )
    )
    session.flush()

    source_field = SourceField(
        source_field_id=Identifier(uuid4()),
        source_object_id=Identifier(object_id),
        field_label=CanonicalName(f"CDD-051-FIELD-{uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )
    SourceFieldRepositoryImpl(session).create(source_field)

    mapping = SemanticMapping(
        semantic_mapping_id=Identifier(uuid4()),
        source_field_id=source_field.source_field_id,
        information_element_requirement_id=requirement_id,
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )
    SemanticMappingRepositoryImpl(session).create(mapping)
    session.commit()

    return requirement_id.value, source_field.source_field_id.value


def _seed_unmapped_information_element(session: Session, *, tenant_id: str) -> UUID:
    """A real, governed `InformationElementRequirement` with zero
    `SemanticMapping` pointing at it -- distinct from `_seed_mapped_element`,
    used only to prove the NOT_EVALUABLE "no mapping" case honestly (a
    random unpersisted UUID would fail `TimelinessPolicy`'s own FK, not
    exercise the mapping-lookup path at all)."""
    OntologySeeder(session).load()
    session.commit()
    supplier_type_id = _entity_type_id(session, "Supplier")
    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    requirement_id = Identifier(uuid4())
    blueprint = Blueprint(
        blueprint_id=blueprint_id,
        blueprint_name=CanonicalName(f"CDD-051 H5 Crown Unmapped Blueprint {uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_requirement_id,
                blueprint_id=blueprint_id,
                entity_type_id=supplier_type_id,
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=requirement_id,
                        concept_requirement_id=concept_requirement_id,
                        element_name=CanonicalName("Unmapped Element"),
                        description=Description("CDD-051 H5 crown fixture element (never mapped)."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        ),
    )
    BlueprintRepositoryImpl(session).create(blueprint)
    session.commit()
    return requirement_id.value


def _seed_business_process(session: Session, *, tenant_id: str) -> tuple[UUID, int]:
    process = create_business_process(
        process_id=uuid4(),
        tenant_id=tenant_id,
        name="Customer Delivery Promise",
        description=None,
        category=BusinessImpactCategory.CUSTOMER,
        created_by="steward",
        created_on=NOW,
    )
    OqiBusinessImpactRepositoryImpl(session).insert_business_process(process)
    session.commit()
    return process.process_id, process.version


def _seed_policy(
    session: Session,
    *,
    tenant_id: str,
    information_element_requirement_id: UUID,
    business_process_id: UUID,
    business_process_version: int,
    freshness_window_seconds: int | None = 1800,
    ingestion_sla_seconds: int | None = None,
) -> UUID:
    policy = new_timeliness_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        information_element_requirement_id=information_element_requirement_id,
        business_process_id=business_process_id,
        business_process_version=business_process_version,
        freshness_window_seconds=freshness_window_seconds,
        ingestion_sla_seconds=ingestion_sla_seconds,
        created_by="steward",
        created_on=NOW,
    )
    OqiTimelinessPolicyRepositoryImpl(session).insert_policy(policy)
    session.commit()
    return policy.policy_id


def _add_evidence(
    session: Session, *, source_field_id: UUID, observed_at: datetime, received_at: datetime
) -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=Identifier(source_field_id),
        source_record_reference="REC-1",
        observed_representation="2026-09-04T18:00:00Z",
        observed_at=observed_at,
        received_at=received_at,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    session.commit()


def _service(session: Session) -> OqiTimelinessEvaluationService:
    repo = OqiTimelinessEvaluationRepositoryImpl(session)
    return OqiTimelinessEvaluationService(
        evaluation_repository=repo,
        evidence_lookup=repo,
        policy_lookup=OqiTimelinessPolicyRepositoryImpl(session),
        semantic_mapping_lookup=SemanticMappingRepositoryImpl(session),
        clock=lambda: NOW,
    )


# =====================================================================
# NOT_EVALUABLE cases (CDD-051 §6).
# =====================================================================


def test_no_active_policy_is_not_evaluable(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=uuid4(),
        business_process_version=1,
        evaluation_horizon=NOW,
    )
    assert result == ()


def test_no_semantic_mapping_is_not_evaluable(session: Session) -> None:
    tenant_id = _tenant()
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    unmapped_ie_id = _seed_unmapped_information_element(session, tenant_id=tenant_id)
    policy_id = _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=unmapped_ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
    )
    assert policy_id is not None
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=unmapped_ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result == ()


def test_no_evidence_is_not_evaluable(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result == ()


# =====================================================================
# STALE_SOURCE_EVIDENCE (CDD-051 §4, §12, §22 worked threat model).
# =====================================================================


def _setup_freshness_scenario(
    session: Session, *, freshness_window_seconds: int = 1800
) -> tuple[str, UUID, UUID, int, UUID]:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    policy_id = _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        freshness_window_seconds=freshness_window_seconds,
        ingestion_sla_seconds=None,
    )
    return tenant_id, ie_id, process_id, process_version, policy_id


def test_fresh_evidence_is_satisfied(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=NOW - timedelta(minutes=10),
        received_at=NOW - timedelta(minutes=10),
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert len(result) == 1
    assert result[0].finding_type is TimelinessFindingType.STALE_SOURCE_EVIDENCE
    assert result[0].outcome is EvaluationOutcome.SATISFIED


def test_stale_evidence_is_violated(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=NOW - timedelta(hours=6, minutes=30),
        received_at=NOW - timedelta(hours=6, minutes=25),
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert len(result) == 1
    assert result[0].finding_type is TimelinessFindingType.STALE_SOURCE_EVIDENCE
    assert result[0].outcome is EvaluationOutcome.VIOLATED

    # CDD-057: scoped to this test's own tenant -- a blanket whole-table
    # count is unsafe once another legitimate tenant's TimelinessEvaluation
    # rows can exist in the same session-scoped database (e.g. Production
    # Orchestration's own crown, run earlier in the same pytest session).
    findings = session.execute(
        select(TimelinessEvaluationORM).where(TimelinessEvaluationORM.tenant_id == tenant_id)
    ).all()
    assert len(findings) == 1


def test_threshold_boundary_is_inclusive(session: Session) -> None:
    """CDD-051 §4: age_seconds == threshold_seconds is SATISFIED; one
    second beyond is VIOLATED."""
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(
        session, freshness_window_seconds=1800
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    exact_boundary_observed_at = NOW - timedelta(seconds=1800)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=exact_boundary_observed_at,
        received_at=exact_boundary_observed_at,
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result[0].outcome is EvaluationOutcome.SATISFIED


def test_threshold_boundary_plus_one_second_is_violated(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(
        session, freshness_window_seconds=1800
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    one_second_past_boundary = NOW - timedelta(seconds=1801)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=one_second_past_boundary,
        received_at=one_second_past_boundary,
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result[0].outcome is EvaluationOutcome.VIOLATED


# =====================================================================
# INGESTION_LATENCY_EXCEEDED.
# =====================================================================


def test_ingestion_latency_within_sla_is_satisfied(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        freshness_window_seconds=None,
        ingestion_sla_seconds=1800,
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    observed = NOW - timedelta(hours=10)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=observed,
        received_at=observed + timedelta(minutes=10),
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert len(result) == 1
    assert result[0].finding_type is TimelinessFindingType.INGESTION_LATENCY_EXCEEDED
    assert result[0].outcome is EvaluationOutcome.SATISFIED


def test_ingestion_latency_exceeded_is_violated(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        freshness_window_seconds=None,
        ingestion_sla_seconds=1800,
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    observed = NOW - timedelta(hours=10)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=observed,
        received_at=observed + timedelta(days=10),  # source fresh, ingestion badly delayed
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW + timedelta(days=11),
    )
    assert len(result) == 1
    assert result[0].finding_type is TimelinessFindingType.INGESTION_LATENCY_EXCEEDED
    assert result[0].outcome is EvaluationOutcome.VIOLATED


def test_both_thresholds_produce_two_independent_evaluations(session: Session) -> None:
    """CDD-051 §22 worked threat model: source fresh at the source, but
    ingestion badly delayed -- the two reason paths diverge independently,
    never merged."""
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    _seed_policy(
        session,
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        # Generous, monthly-like source cadence (CDD-046 §15's own example)
        # vs. a strict 30-minute ingestion SLA -- deliberately far apart so
        # the two reason paths can diverge independently.
        freshness_window_seconds=30 * 24 * 3600,
        ingestion_sla_seconds=1800,
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    # CDD-046 §22's exact worked scenario: evidence observed fresh at the
    # source, but ingestion delayed 2 hours before received_at.
    observed = NOW - timedelta(hours=6)
    received = observed + timedelta(hours=2)
    horizon = received + timedelta(minutes=5)  # evaluate shortly after ingestion completes
    _add_evidence(
        session, source_field_id=mapping.source_field_id, observed_at=observed, received_at=received
    )
    evaluations = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=horizon,
    )
    by_type = {e.finding_type: e for e in evaluations}
    assert len(by_type) == 2
    assert (
        by_type[TimelinessFindingType.STALE_SOURCE_EVIDENCE].outcome is EvaluationOutcome.SATISFIED
    )
    assert (
        by_type[TimelinessFindingType.INGESTION_LATENCY_EXCEEDED].outcome
        is EvaluationOutcome.VIOLATED
    )


# =====================================================================
# Historical/as-of evaluation (CDD-051 §13) and anti-laundering (CDD-051 §5).
# =====================================================================


def test_historical_evaluation_uses_supplied_horizon_not_wall_clock(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(
        session, freshness_window_seconds=1800
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    historical_observed = datetime(2020, 1, 10, 10, 0, tzinfo=UTC)
    historical_horizon = datetime(2020, 1, 10, 10, 5, tzinfo=UTC)  # 5 min later, well within 1800s
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=historical_observed,
        received_at=historical_observed,
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=historical_horizon,
    )
    # Real "today" is 2026+; if the evaluator used wall-clock now() instead
    # of the supplied historical horizon, this would be VIOLATED (years
    # stale). It must be SATISFIED.
    assert result[0].outcome is EvaluationOutcome.SATISFIED
    assert result[0].evaluation_horizon == historical_horizon


def test_reingestion_does_not_launder_stale_evidence(session: Session) -> None:
    """Principle 5 / task §23's exact adversarial scenario: real source
    observation is old; the record is "re-ingested" (create_or_get_existing
    called again with identical semantic content) -- age must still reflect
    the true, original `observed_at`, never a refreshed system timestamp."""
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    original_observed = NOW - timedelta(days=30)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=original_observed,
        received_at=original_observed,
    )
    # "Re-ingestion": identical semantic fact submitted again, much later in
    # wall-clock terms -- create_or_get_existing must return the existing
    # row unchanged (CDD-022 §25), never advance observed_at/received_at.
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=original_observed,
        received_at=original_observed,
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result[0].outcome is EvaluationOutcome.VIOLATED  # still stale, not laundered fresh


# =====================================================================
# Idempotence and lifecycle (CDD-051 §19).
# =====================================================================


def test_repeated_identical_evaluation_is_idempotent(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    observed = NOW - timedelta(hours=6)
    _add_evidence(
        session, source_field_id=mapping.source_field_id, observed_at=observed, received_at=observed
    )

    service = _service(session)
    service.evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    service.evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    # CDD-057: scoped to this test's own tenant, same reason as above.
    rows = session.execute(
        select(TimelinessEvaluationORM).where(TimelinessEvaluationORM.tenant_id == tenant_id)
    ).all()
    assert len(rows) == 1  # second call was a genuine no-op, not a duplicate


def test_lifecycle_open_resolve_reopen(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    service = _service(session)

    # T1: stale -> OPEN.
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=NOW - timedelta(hours=6),
        received_at=NOW - timedelta(hours=6),
    )
    r1 = service.evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert r1[0].outcome is EvaluationOutcome.VIOLATED

    # T2: fresh evidence arrives -> RESOLVED.
    horizon_2 = NOW + timedelta(hours=1)
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=horizon_2 - timedelta(minutes=5),
        received_at=horizon_2 - timedelta(minutes=5),
    )
    service.evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=horizon_2,
    )

    finding_id = None
    from app.domain.oqi_timeliness.evaluation import derive_timeliness_finding_id

    finding_id = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=_policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=r1[0].source_object_id,
    )
    finding = OqiTimelinessEvaluationRepositoryImpl(session).get_finding(finding_id)
    assert finding is not None
    assert finding.status is TimelinessFindingStatus.RESOLVED

    # T3: evidence goes stale again (no new observation, horizon advances
    # far past the threshold) -> reopen.
    horizon_3 = horizon_2 + timedelta(hours=6)
    service.evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=horizon_3,
    )
    finding = OqiTimelinessEvaluationRepositoryImpl(session).get_finding(finding_id)
    assert finding is not None
    assert finding.status is TimelinessFindingStatus.OPEN
    assert finding.reopen_count == 1


# =====================================================================
# OQI4 origin/subject resolution (CDD-051 §22).
# =====================================================================


def test_oqi4_origin_and_subject_resolution(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, policy_id = _setup_freshness_scenario(session)
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(ie_id, tenant_id)
    assert mapping is not None
    _add_evidence(
        session,
        source_field_id=mapping.source_field_id,
        observed_at=NOW - timedelta(hours=6),
        received_at=NOW - timedelta(hours=6),
    )
    result = _service(session).evaluate_current_state(
        tenant_id=tenant_id,
        information_element_requirement_id=ie_id,
        business_process_id=process_id,
        business_process_version=process_version,
        evaluation_horizon=NOW,
    )
    assert result[0].outcome is EvaluationOutcome.VIOLATED

    from app.domain.oqi_timeliness.evaluation import derive_timeliness_finding_id

    finding_id = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=TimelinessFindingType.STALE_SOURCE_EVIDENCE,
        source_object_id=result[0].source_object_id,
    )
    impact_repo = OqiOntologyImpactEvaluationRepositoryImpl(session)
    origin = impact_repo.resolve_timeliness_finding_origin(
        tenant_id=tenant_id, finding_id=finding_id
    )
    assert origin.finding_storage_family is FindingStorageFamily.TIMELINESS
    assert origin.quality_dimension == QualityDimension.TIMELINESS.value

    subject = impact_repo.resolve_timeliness_finding_subject(
        tenant_id=tenant_id, finding_id=finding_id
    )
    # No ER resolution record exists for this fresh source_object -> IMPACT_UNKNOWN,
    # never a fabricated resolved entity (honest absence, not a defect).
    assert subject.outcome is ImpactOutcome.IMPACT_UNKNOWN


# =====================================================================
# Real-PostgreSQL structural invariants.
# =====================================================================


def test_db_rejects_policy_with_neither_threshold(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    session.add(
        TimelinessPolicyORM(
            policy_id=uuid4(),
            version=1,
            tenant_id=tenant_id,
            information_element_requirement_id=ie_id,
            business_process_id=process_id,
            business_process_version=process_version,
            freshness_window_seconds=None,
            ingestion_sla_seconds=None,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_db_rejects_non_positive_threshold(session: Session) -> None:
    tenant_id = _tenant()
    ie_id, _field_id = _seed_mapped_element(session, tenant_id=tenant_id)
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    session.add(
        TimelinessPolicyORM(
            policy_id=uuid4(),
            version=1,
            tenant_id=tenant_id,
            information_element_requirement_id=ie_id,
            business_process_id=process_id,
            business_process_version=process_version,
            freshness_window_seconds=0,
            ingestion_sla_seconds=None,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_db_rejects_duplicate_active_policy_for_same_anchor(session: Session) -> None:
    tenant_id, ie_id, process_id, process_version, _policy_id = _setup_freshness_scenario(session)
    session.add(
        TimelinessPolicyORM(
            policy_id=uuid4(),
            version=1,
            tenant_id=tenant_id,
            information_element_requirement_id=ie_id,
            business_process_id=process_id,
            business_process_version=process_version,
            freshness_window_seconds=900,
            ingestion_sla_seconds=None,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# OQI6 regression after the narrow additive `oqi_business_processes`
# correction (CDD-051 §9) -- the pre-existing consumer must be unaffected.
# =====================================================================


def test_oqi6_business_process_insert_and_dependency_fk_still_work(session: Session) -> None:
    tenant_id = _tenant()
    process_id, process_version = _seed_business_process(session, tenant_id=tenant_id)
    from app.domain.oqi_business_impact.dependency import (
        BusinessDependency,
        BusinessDependencyStatus,
    )
    from app.domain.oqi_ontology_impact.evaluation import OntologyElementType

    dependency = BusinessDependency(
        dependency_id=uuid4(),
        tenant_id=tenant_id,
        version=1,
        business_process_id=process_id,
        business_process_version=process_version,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        criticality=None,
        status=BusinessDependencyStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )
    OqiBusinessImpactRepositoryImpl(session).insert_business_dependency(dependency)
    session.commit()  # would raise IntegrityError if the additive constraint broke the existing FK
