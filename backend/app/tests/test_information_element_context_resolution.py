"""Postgres-backed acceptance evidence for Gate O's own governed-data
failure taxonomy (CDD-029 §15; Gate O Artifact Authorization v1.0 §8).
`InformationElementContextResolutionApplicationService` constructs its
`BlueprintRepositoryImpl`/`SemanticMappingRepositoryImpl`/
`FieldValueEvidenceRepositoryImpl` dependencies directly from a real
`Session`, exactly mirroring Gate P's own `ontology_copilot_api.py`
orchestration shape -- which has no fake-repository unit test either, for
the identical reason. The happy-path/tenant-isolation/passthrough/
zero-write/determinism obligations against the existing H3/CDD-022 demo
fixture live in `test_information_element_context_resolution_postgres.py`;
this file covers the two failure conditions that specifically require
constructing governed data by hand: an ambiguous `InformationElementRequirement`
name within one Blueprint, and more than one Approved Blueprint sharing a
name (a genuine `BlueprintRepositoryImpl` integrity violation, kept
structurally distinct from the ambiguity case per CDD-029 §15's own
integrity/ambiguity correction)."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionApplicationService,
    InformationElementContextResolutionStatus,
)
from app.application.semantic_coverage_evaluation import CoverageStatus
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.ontology_seed import OntologySeeder

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _principal(*, tenant_id: str = "gate-o-unit-tenant") -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=("information-element-context:read",),
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _single_concept_blueprint(
    *, blueprint_name: str, entity_type_id: Identifier, element_name: str
) -> Blueprint:
    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    return Blueprint(
        blueprint_id=blueprint_id,
        blueprint_name=CanonicalName(blueprint_name),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
        concept_requirements=(
            ConceptRequirement(
                concept_requirement_id=concept_requirement_id,
                blueprint_id=blueprint_id,
                entity_type_id=entity_type_id,
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=Identifier(uuid4()),
                        concept_requirement_id=concept_requirement_id,
                        element_name=CanonicalName(element_name),
                        description=Description("Test fixture element."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        ),
    )


def test_ambiguous_information_element_name_within_a_single_blueprint_returns_ambiguous(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"Gate O Ambiguity Test Blueprint {uuid4()}"
    shared_element_name = "Duplicate Element Name"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        material_type_id = _entity_type_id(session, "Material")

        first_concept_id = Identifier(uuid4())
        second_concept_id = Identifier(uuid4())
        blueprint_id = Identifier(uuid4())
        blueprint = Blueprint(
            blueprint_id=blueprint_id,
            blueprint_name=CanonicalName(blueprint_name),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
            concept_requirements=(
                ConceptRequirement(
                    concept_requirement_id=first_concept_id,
                    blueprint_id=blueprint_id,
                    entity_type_id=supplier_type_id,
                    obligation=Obligation.REQUIRED,
                    information_element_requirements=(
                        InformationElementRequirement(
                            information_element_requirement_id=Identifier(uuid4()),
                            concept_requirement_id=first_concept_id,
                            element_name=CanonicalName(shared_element_name),
                            description=Description("First concept's own element."),
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                ),
                ConceptRequirement(
                    concept_requirement_id=second_concept_id,
                    blueprint_id=blueprint_id,
                    entity_type_id=material_type_id,
                    obligation=Obligation.REQUIRED,
                    information_element_requirements=(
                        InformationElementRequirement(
                            information_element_requirement_id=Identifier(uuid4()),
                            concept_requirement_id=second_concept_id,
                            element_name=CanonicalName(shared_element_name),
                            description=Description(
                                "Second concept's own, distinctly-owned element."
                            ),
                            obligation=Obligation.REQUIRED,
                        ),
                    ),
                ),
            ),
        )
        BlueprintRepositoryImpl(session).create(blueprint)
        session.commit()

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name=shared_element_name,
        )

    # Never confused with a genuine integrity violation (CDD-029 §15's own correction).
    assert (
        result.status
        is InformationElementContextResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
    )
    assert result.coverage_status is None


def test_duplicate_approved_blueprint_name_returns_upstream_integrity_failure(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    shared_blueprint_name = f"Gate O Integrity Test Blueprint {uuid4()}"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        first_blueprint = _single_concept_blueprint(
            blueprint_name=shared_blueprint_name,
            entity_type_id=supplier_type_id,
            element_name="First Blueprint's Element",
        )
        second_blueprint = _single_concept_blueprint(
            blueprint_name=shared_blueprint_name,
            entity_type_id=supplier_type_id,
            element_name="Second Blueprint's Element",
        )
        repository = BlueprintRepositoryImpl(session)
        repository.create(first_blueprint)
        repository.create(second_blueprint)
        session.commit()

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(),
            blueprint_name=shared_blueprint_name,
            information_element_name="First Blueprint's Element",
        )

    # Never confused with the ordinary ambiguous-element-name outcome.
    assert result.status is InformationElementContextResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
    assert result.coverage_status is None


def test_a_freshly_governed_single_element_blueprint_resolves_unmapped(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"Gate O Standalone Resolution Test Blueprint {uuid4()}"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        blueprint = _single_concept_blueprint(
            blueprint_name=blueprint_name,
            entity_type_id=supplier_type_id,
            element_name="Standalone Element",
        )
        BlueprintRepositoryImpl(session).create(blueprint)
        session.commit()

    with factory() as session:
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name="Standalone Element",
        )

    assert result.status is InformationElementContextResolutionStatus.RESOLVED
    assert result.coverage_status is CoverageStatus.UNMAPPED
    assert result.evidence_availability_status is None
    assert result.information_element_name == "Standalone Element"
