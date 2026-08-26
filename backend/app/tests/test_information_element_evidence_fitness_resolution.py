"""Postgres-backed acceptance evidence for the Governed Evidence Fitness
Exposure application service's own governed-data failure taxonomy and
UNMAPPED short-circuit contract (CDD-034 §13, §18; CDD-034 Artifact
Authorization v1.0 §9).
`InformationElementEvidenceFitnessResolutionApplicationService` constructs
its `BlueprintRepositoryImpl`/`SemanticMappingRepositoryImpl`/
`FieldValueEvidenceRepositoryImpl` dependencies directly from a real
`Session`, exactly mirroring Gate O's own
`InformationElementContextResolutionApplicationService` orchestration
shape -- which has no fake-repository unit test either, for the identical
reason. The MAPPED+EVIDENCE_PRESENT (FIT/STALE/CONFLICTING) happy-path/
tenant-isolation/passthrough/zero-write/single-timestamp obligations
against the shared H3/CDD-022 demo fixture live in
`test_information_element_evidence_fitness_resolution_postgres.py`; this
file covers the failure conditions and the UNMAPPED short-circuit that
specifically require constructing governed data by hand -- mirroring
`test_information_element_context_resolution.py`'s own precedent exactly."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.information_element_evidence_fitness_resolution import (
    InformationElementEvidenceFitnessResolutionApplicationService,
    InformationElementEvidenceFitnessResolutionStatus,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.integration import SourceField
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _principal(*, tenant_id: str = "gate-cdd034-unit-tenant") -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=("information-element-evidence-fitness:read",),
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


def test_unmapped_requirement_resolves_with_null_source_field_and_fitness(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"CDD-034 Standalone Resolution Test Blueprint {uuid4()}"

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

    with (
        patch(
            "app.application.information_element_evidence_fitness_resolution."
            "InformationElementEvidenceAvailabilityApplicationService"
        ) as h4_class,
        patch(
            "app.application.information_element_evidence_fitness_resolution."
            "SourceEvidenceFitnessEvaluationApplicationService"
        ) as gate_t_class,
        factory() as session,
    ):
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name="Standalone Element",
        )

    assert result.status is InformationElementEvidenceFitnessResolutionStatus.RESOLVED
    assert result.source_field_id is None
    assert result.fitness_status is None
    assert result.information_element_requirement_id is not None
    assert result.evaluated_at is not None
    # CDD-034 §13 step 7, binding: H4 and Gate T must never be constructed at
    # all on the UNMAPPED path -- not merely uninvoked, never instantiated.
    h4_class.assert_not_called()
    gate_t_class.assert_not_called()


def test_mapped_element_with_zero_evidence_rows_resolves_with_real_source_field_and_null_fitness(
    migrated_engine: Engine,
) -> None:
    """CDD-034 §11's "MAPPED + NO_EVIDENCE" null-adjacent state: a real,
    non-null `source_field_id` together with a `null` `fitness_status`.
    Deliberately does not reuse the shared H3/CDD-022 demo fixture, for the
    identical reason `test_information_element_context_resolution.py`'s
    own comparable test does not: other test files seed real
    `FieldValueEvidence` against that shared canonical `SourceField`, making
    a demo-fixture-based "zero evidence" assumption order-dependent."""
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-no-evidence-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 No-Evidence Test Blueprint {uuid4()}"
    element_name = "No-Evidence Element"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()

        supplier_type_id = _entity_type_id(session, "Supplier")
        blueprint = _single_concept_blueprint(
            blueprint_name=blueprint_name,
            entity_type_id=supplier_type_id,
            element_name=element_name,
        )
        BlueprintRepositoryImpl(session).create(blueprint)

        system_id = uuid4()
        object_id = uuid4()
        session.add(
            SourceSystemORM(
                source_system_id=system_id,
                tenant_id=tenant_id,
                source_system_name=f"CDD-034 No-Evidence Source System {system_id}",
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
                source_object_name=f"CDD-034 No-Evidence Source Object {object_id}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                source_system_id=system_id,
            )
        )
        session.flush()

        requirement = blueprint.concept_requirements[0].information_element_requirements[0]
        source_field = SourceField(
            source_field_id=Identifier(uuid4()),
            source_object_id=Identifier(object_id),
            field_label=CanonicalName("CDD-034-NO-EVIDENCE-FIELD"),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
        )
        SourceFieldRepositoryImpl(session).create(source_field)

        mapping = SemanticMapping(
            semantic_mapping_id=Identifier(uuid4()),
            source_field_id=source_field.source_field_id,
            information_element_requirement_id=requirement.information_element_requirement_id,
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
        )
        SemanticMappingRepositoryImpl(session).create(mapping)
        # Deliberately no FieldValueEvidence row is added for this SourceField.
        session.commit()

    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.status is InformationElementEvidenceFitnessResolutionStatus.RESOLVED
    assert result.source_field_id == source_field.source_field_id.value
    assert result.fitness_status is None
    assert result.evaluated_at is not None


def test_blueprint_not_found(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=f"No Such Blueprint {uuid4()}",
            information_element_name="Anything",
        )
    assert result.status is InformationElementEvidenceFitnessResolutionStatus.BLUEPRINT_NOT_FOUND
    assert result.evaluated_at is None


def test_information_element_not_found(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"CDD-034 Element-Not-Found Test Blueprint {uuid4()}"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_type_id = _entity_type_id(session, "Supplier")
        blueprint = _single_concept_blueprint(
            blueprint_name=blueprint_name,
            entity_type_id=supplier_type_id,
            element_name="Real Element",
        )
        BlueprintRepositoryImpl(session).create(blueprint)
        session.commit()

    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name="No Such Element",
        )
    assert (
        result.status
        is InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NOT_FOUND
    )


def test_ambiguous_information_element_name_within_a_single_blueprint(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"CDD-034 Ambiguity Test Blueprint {uuid4()}"
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
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name=shared_element_name,
        )

    # Never confused with a genuine integrity violation.
    assert (
        result.status
        is InformationElementEvidenceFitnessResolutionStatus.INFORMATION_ELEMENT_NAME_AMBIGUOUS
    )


def test_duplicate_approved_blueprint_name_returns_upstream_integrity_failure(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    shared_blueprint_name = f"CDD-034 Integrity Test Blueprint {uuid4()}"

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
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=shared_blueprint_name,
            information_element_name="First Blueprint's Element",
        )

    # Never confused with the ordinary ambiguous-element-name outcome.
    assert (
        result.status
        is InformationElementEvidenceFitnessResolutionStatus.UPSTREAM_INTEGRITY_FAILURE
    )


def test_evaluated_at_is_a_single_real_timestamp_generated_within_the_call_window(
    migrated_engine: Engine,
) -> None:
    """Proves exactly one real UTC timestamp is generated per invocation --
    not a caller-supplied or otherwise fabricated value -- by bracketing the
    call with two independent `datetime.now(UTC)` reads (CDD-034 §12)."""
    factory = sessionmaker(migrated_engine)
    blueprint_name = f"CDD-034 Timestamp Test Blueprint {uuid4()}"

    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        supplier_type_id = _entity_type_id(session, "Supplier")
        blueprint = _single_concept_blueprint(
            blueprint_name=blueprint_name,
            entity_type_id=supplier_type_id,
            element_name="Timestamp Element",
        )
        BlueprintRepositoryImpl(session).create(blueprint)
        session.commit()

    before = datetime.now(UTC)
    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(),
            blueprint_name=blueprint_name,
            information_element_name="Timestamp Element",
        )
    after = datetime.now(UTC)

    assert result.evaluated_at is not None
    assert before <= result.evaluated_at <= after
