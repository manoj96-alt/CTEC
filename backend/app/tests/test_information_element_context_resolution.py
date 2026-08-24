"""Postgres-backed acceptance evidence for Gate O's own governed-data
failure taxonomy (CDD-029 §15; Gate O Artifact Authorization v1.0 §8).
`InformationElementContextResolutionApplicationService` constructs its
`BlueprintRepositoryImpl`/`SemanticMappingRepositoryImpl`/
`FieldValueEvidenceRepositoryImpl` dependencies directly from a real
`Session`, exactly mirroring Gate P's own `ontology_copilot_api.py`
orchestration shape -- which has no fake-repository unit test either, for
the identical reason. The MAPPED+EVIDENCE_PRESENT happy-path/tenant-isolation/
passthrough/zero-write/determinism obligations against the existing
H3/CDD-022 demo fixture live in
`test_information_element_context_resolution_postgres.py`; this file
covers the failure conditions that specifically require constructing
governed data by hand -- an ambiguous `InformationElementRequirement` name
within one Blueprint, and more than one Approved Blueprint sharing a name
(a genuine `BlueprintRepositoryImpl` integrity violation, kept structurally
distinct from the ambiguity case per CDD-029 §15's own integrity/ambiguity
correction) -- plus the MAPPED+`NO_EVIDENCE` domain outcome (CDD-029's own
"MAPPED + UNAVAILABLE" scenario, expressed in H4's real
`EvidenceAvailabilityStatus` vocabulary), built from a fully self-contained
fixture (mirroring `test_semantic_mapping_persistence_postgres.py`'s own
precedent) rather than the shared H3 demo fixture, since other test files
seed real evidence against that shared fixture's own canonical SourceField,
making a demo-fixture-based "zero evidence" assumption order-dependent."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.information_element_context_resolution import (
    InformationElementContextResolutionApplicationService,
    InformationElementContextResolutionStatus,
)
from app.application.information_element_evidence_availability import EvidenceAvailabilityStatus
from app.application.semantic_coverage_evaluation import CoverageStatus
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


def test_mapped_element_with_zero_evidence_rows_resolves_mapped_no_evidence(
    migrated_engine: Engine,
) -> None:
    """CDD-029's "MAPPED + UNAVAILABLE" domain outcome, in H4's real
    vocabulary. Deliberately does NOT reuse the shared H3/CDD-022 demo
    fixture (`DemoSemanticMappingSeeder`/`DemoFieldValueEvidenceSeeder`):
    when the full suite runs, other test files seed real `FieldValueEvidence`
    against that same shared canonical "Supplier Legal Name" `SourceField`,
    so a demo-fixture-based "zero evidence" assumption is order-dependent
    and unreliable. Instead builds a fully self-contained, uniquely-named
    Blueprint + SourceSystem + SourceObject + SourceField + Approved
    SemanticMapping (mirroring `test_semantic_mapping_persistence_postgres.py`'s
    own precedent), adding zero `FieldValueEvidence` rows for the new
    SourceField -- guaranteeing H4 classifies it `NO_EVIDENCE` regardless of
    what any other test has already seeded, while Gate I still classifies it
    `MAPPED`. Proves Gate O passes through H4's real unavailable-equivalent
    state rather than reinterpreting it (CDD-029 §7, §25/§26; Gate O
    Artifact Authorization v1.0 §8)."""
    factory = sessionmaker(migrated_engine)
    tenant_id = f"gate-o-no-evidence-tenant-{uuid4()}"
    blueprint_name = f"Gate O No-Evidence Test Blueprint {uuid4()}"
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
                source_system_name=f"Gate O No-Evidence Source System {system_id}",
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
                source_object_name=f"Gate O No-Evidence Source Object {object_id}",
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
            field_label=CanonicalName("NO-EVIDENCE-FIELD"),
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
        result = InformationElementContextResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.status is InformationElementContextResolutionStatus.RESOLVED
    assert result.coverage_status is CoverageStatus.MAPPED
    assert result.evidence_availability_status is EvidenceAvailabilityStatus.NO_EVIDENCE
