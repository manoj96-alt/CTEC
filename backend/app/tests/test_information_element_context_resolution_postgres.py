"""Postgres-backed acceptance evidence for Gate O (CDD-029; Gate O Artifact
Authorization v1.0). Composes the real, unmodified `BlueprintApplicationService`,
Gate I, H4, and Gate N against the existing H3/CDD-022 demo fixture
(`DemoFieldValueEvidenceSeeder`, reused by call only, no new seeder) --
proving real Blueprint/Information-Element resolution, tenant-scoped
semantic evaluation, cross-tenant isolation, Gate I/H4/Gate N passthrough,
zero write side effects, and determinism against real PostgreSQL.

Blueprint-not-found and Information-Element-not-found are proven here too
(trivial against the real database); the ambiguous-element-name and
governed-data-integrity-violation outcomes are proven at the application
(fake-repository) tier in `test_information_element_context_resolution.py`,
since neither condition depends on real persistence mutation -- both are
purely about Blueprint-domain-object shape, which fakes construct far more
directly than a Postgres fixture could."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.blueprint_service import BlueprintApplicationService
from app.application.information_element_context_availability import (
    InformationElementContextAvailabilityApplicationService,
)
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionApplicationService,
    InformationElementContextResolutionStatus,
)
from app.application.information_element_evidence_availability import (
    EvidenceAvailabilityStatus,
    InformationElementEvidenceAvailabilityApplicationService,
)
from app.application.semantic_coverage_evaluation import (
    CoverageStatus,
    SemanticCoverageEvaluationApplicationService,
)
from app.application.semantic_mapping_resolution import SemanticMappingResolutionApplicationService
from app.core.bootstrap import BOOTSTRAP_DEMO_TENANT_ID
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.blueprint_seed import CANONICAL_BLUEPRINT_NAME
from app.infrastructure.persistence.demo_field_value_evidence_seeder import (
    DemoFieldValueEvidenceSeeder,
)
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl

NOW = datetime.now(UTC)


def _seed(factory: "sessionmaker[Session]") -> None:
    with factory() as session:
        DemoFieldValueEvidenceSeeder(session).seed()
        session.commit()


def _principal(*, tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=("information-element-context:read",),
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _field_value_evidence_row_count(session: Session) -> int:
    return len(session.execute(select(FieldValueEvidenceORM)).all())


def test_supplier_legal_name_resolves_mapped_evidence_present(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )

    assert result.status is InformationElementContextResolutionStatus.RESOLVED
    assert result.coverage_status is CoverageStatus.MAPPED
    assert result.evidence_availability_status is EvidenceAvailabilityStatus.EVIDENCE_PRESENT
    assert result.blueprint_id is not None
    assert result.information_element_name == "Supplier Legal Name"


def test_risk_event_severity_resolves_unmapped(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Risk Event Severity",
        )

    assert result.status is InformationElementContextResolutionStatus.RESOLVED
    assert result.coverage_status is CoverageStatus.UNMAPPED
    assert result.evidence_availability_status is None


def test_blueprint_not_found_against_real_database(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name="Nonexistent Blueprint",
            information_element_name="Supplier Legal Name",
        )

    assert result.status is InformationElementContextResolutionStatus.BLUEPRINT_NOT_FOUND


def test_information_element_not_found_against_real_database(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Nonexistent Element",
        )

    assert result.status is InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND


def test_cross_tenant_isolation_never_leaks_another_tenants_mapping(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)
    other_tenant_id = f"gate-o-isolation-tenant-{uuid4()}"

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=other_tenant_id),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )

    # The legitimate, tenant-scoped result for a tenant with no mapping of its
    # own -- never a leak of BOOTSTRAP_DEMO_TENANT_ID's own MAPPED state, and
    # never an authorization failure (CDD-029 §8, O3-D11).
    assert result.status is InformationElementContextResolutionStatus.RESOLVED
    assert result.coverage_status is CoverageStatus.UNMAPPED
    assert result.evidence_availability_status is None


def test_gate_i_h4_gate_n_output_is_passed_through_unmodified(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        gate_o_result = InformationElementContextResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )

    with factory() as session:
        blueprint_service = BlueprintApplicationService(repository=BlueprintRepositoryImpl(session))
        coverage_result = SemanticCoverageEvaluationApplicationService(
            blueprint_service=blueprint_service,
            resolver=SemanticMappingResolutionApplicationService(
                repository=SemanticMappingRepositoryImpl(session)
            ),
        ).evaluate(blueprint_name=CANONICAL_BLUEPRINT_NAME, tenant_id=BOOTSTRAP_DEMO_TENANT_ID)
        evidence_availability_results = InformationElementEvidenceAvailabilityApplicationService(
            evidence_provider=FieldValueEvidenceRepositoryImpl(session)
        ).evaluate(coverage_result=coverage_result)
        composed = InformationElementContextAvailabilityApplicationService().compose(
            coverage_result=coverage_result,
            evidence_availability_results=evidence_availability_results,
        )

    direct = next(
        c
        for c in composed
        if c.information_element_requirement_id == gate_o_result.information_element_requirement_id
    )
    assert gate_o_result.coverage_status == direct.coverage_status
    assert gate_o_result.evidence_availability_status == direct.evidence_availability_status
    assert gate_o_result.obligation == direct.obligation


def test_repeated_resolution_of_unchanged_state_is_deterministic(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as first_session:
        first = InformationElementContextResolutionApplicationService(
            session=first_session
        ).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )
    with factory() as second_session:
        second = InformationElementContextResolutionApplicationService(
            session=second_session
        ).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )

    assert first == second


def test_no_persistence_side_effect(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    _seed(factory)

    with factory() as session:
        before = _field_value_evidence_row_count(session)

    with factory() as session:
        InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=BOOTSTRAP_DEMO_TENANT_ID),
            blueprint_name=CANONICAL_BLUEPRINT_NAME,
            information_element_name="Supplier Legal Name",
        )
        session.commit()

    with factory() as session:
        after = _field_value_evidence_row_count(session)

    assert after == before
