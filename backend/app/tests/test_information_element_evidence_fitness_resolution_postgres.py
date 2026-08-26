"""Postgres-backed acceptance evidence for the Governed Evidence Fitness
Exposure application service's MAPPED composition path (CDD-034 §9, §12,
§13, §18; CDD-034 Artifact Authorization v1.0 §9). Composes the real,
unmodified `BlueprintApplicationService`, `SemanticCoverageEvaluationApplicationService`
(Gate I), `InformationElementEvidenceAvailabilityApplicationService` (H4),
and `SourceEvidenceFitnessEvaluationApplicationService` (Gate T) via
`InformationElementEvidenceFitnessResolutionApplicationService`, proving a
real fitness classification (`FIT`/`STALE`/`CONFLICTING`), `source_field_id`
propagation, the single-timestamp contract (`evaluated_at` passed to Gate T
unmodified as `as_of`), and zero persistence side effects against real
PostgreSQL.

Since this service generates its own real `datetime.now(UTC)` `evaluated_at`
rather than accepting a caller-supplied `as_of` (CDD-034 §12), the shared
H3/CDD-022 demo fixture (whose evidence is seeded at a fixed historical
`SEED_TIMESTAMP`) cannot be used to construct a `FIT` state under real-clock
evaluation -- it would always classify `STALE` by construction. Fresh,
self-contained fixtures with `observed_at` values relative to real "now"
are built instead, mirroring `test_information_element_context_resolution
.py`'s own precedent for self-contained data over the shared demo
fixture."""

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
from app.application.source_evidence_fitness_evaluation import (
    EvidenceFitnessStatus,
    SourceEvidenceFitnessEvaluationApplicationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.blueprint import (
    Blueprint,
    ConceptRequirement,
    InformationElementRequirement,
    Obligation,
)
from app.domain.integration import SourceField
from app.domain.integration.field_value_evidence import FieldValueEvidence
from app.domain.semantic_mapping import SemanticMapping
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Description, Identifier
from app.infrastructure.persistence.blueprint_repository import BlueprintRepositoryImpl
from app.infrastructure.persistence.field_value_evidence_repository import (
    FieldValueEvidenceRepositoryImpl,
)
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.field_value_evidence import FieldValueEvidenceORM
from app.infrastructure.persistence.models.source_object import SourceObject as SourceObjectORM
from app.infrastructure.persistence.models.source_system import SourceSystem as SourceSystemORM
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.semantic_mapping_repository import SemanticMappingRepositoryImpl
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl

NOW = datetime.now(UTC)


def _entity_type_id(session: Session, name: str) -> Identifier:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return Identifier(value)


def _principal(*, tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=("information-element-evidence-fitness:read",),
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _field_value_evidence_row_count(session: Session) -> int:
    return len(session.execute(select(FieldValueEvidenceORM)).all())


def _seed_mapped_element(
    session: Session,
    *,
    tenant_id: str,
    blueprint_name: str,
    element_name: str,
) -> tuple[Blueprint, Identifier]:
    """Builds a fresh, self-contained Blueprint with one MAPPED
    InformationElementRequirement (a real SourceSystem/SourceObject/
    SourceField/Approved SemanticMapping), with zero FieldValueEvidence
    rows -- callers add whatever evidence rows their own scenario needs."""
    OntologySeeder(session).load()
    session.commit()

    supplier_type_id = _entity_type_id(session, "Supplier")
    blueprint_id = Identifier(uuid4())
    concept_requirement_id = Identifier(uuid4())
    requirement_id = Identifier(uuid4())
    blueprint = Blueprint(
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
                entity_type_id=supplier_type_id,
                obligation=Obligation.REQUIRED,
                information_element_requirements=(
                    InformationElementRequirement(
                        information_element_requirement_id=requirement_id,
                        concept_requirement_id=concept_requirement_id,
                        element_name=CanonicalName(element_name),
                        description=Description("CDD-034 postgres fixture element."),
                        obligation=Obligation.REQUIRED,
                    ),
                ),
            ),
        ),
    )
    BlueprintRepositoryImpl(session).create(blueprint)

    system_id = uuid4()
    object_id = uuid4()
    session.add(
        SourceSystemORM(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"CDD-034 Postgres Fixture Source System {system_id}",
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
            source_object_name=f"CDD-034 Postgres Fixture Source Object {object_id}",
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
        field_label=CanonicalName(f"CDD-034-FIELD-{uuid4()}"),
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

    return blueprint, source_field.source_field_id


def _add_evidence(
    session: Session,
    *,
    source_field_id: Identifier,
    source_record_reference: str,
    observed_representation: str,
    observed_at: datetime,
) -> None:
    evidence = FieldValueEvidence.new(
        source_field_id=source_field_id,
        source_record_reference=source_record_reference,
        observed_representation=observed_representation,
        observed_at=observed_at,
        received_at=observed_at,
    )
    FieldValueEvidenceRepositoryImpl(session).create_or_get_existing(evidence)
    session.commit()


def test_fresh_evidence_is_fit(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-fit-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 FIT Test Blueprint {uuid4()}"
    element_name = "FIT Element"

    with factory() as session:
        _, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id, blueprint_name=blueprint_name, element_name=element_name
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-fit-record",
            observed_representation="Fresh Value",
            observed_at=datetime.now(UTC),
        )

    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.status is InformationElementEvidenceFitnessResolutionStatus.RESOLVED
    assert result.source_field_id == source_field_id.value
    assert result.fitness_status is EvidenceFitnessStatus.FIT


def test_stale_evidence_is_stale(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-stale-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 STALE Test Blueprint {uuid4()}"
    element_name = "STALE Element"

    with factory() as session:
        _, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id, blueprint_name=blueprint_name, element_name=element_name
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-stale-record",
            observed_representation="Old Value",
            observed_at=datetime.now(UTC) - timedelta(days=30),
        )

    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.source_field_id == source_field_id.value
    assert result.fitness_status is EvidenceFitnessStatus.STALE


def test_conflicting_evidence_is_conflicting(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-conflicting-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 CONFLICTING Test Blueprint {uuid4()}"
    element_name = "CONFLICTING Element"

    with factory() as session:
        _, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id, blueprint_name=blueprint_name, element_name=element_name
        )
        now = datetime.now(UTC)
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-conflicting-record",
            observed_representation="Value A",
            observed_at=now,
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-conflicting-record",
            observed_representation="Value B",
            observed_at=now,
        )

    with factory() as session:
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.source_field_id == source_field_id.value
    assert result.fitness_status is EvidenceFitnessStatus.CONFLICTING


def test_evaluated_at_is_passed_to_gate_t_unmodified_as_of(migrated_engine: Engine) -> None:
    """CDD-034 §12, binding: the exact same timestamp returned as
    `evaluated_at` is passed to Gate T as `as_of` -- proven here by spying
    on the real, unmodified `SourceEvidenceFitnessEvaluationApplicationService
    .evaluate` call, not merely by inference from the response shape."""
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-timestamp-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 Timestamp-Passthrough Test Blueprint {uuid4()}"
    element_name = "Timestamp-Passthrough Element"

    with factory() as session:
        _, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id, blueprint_name=blueprint_name, element_name=element_name
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-timestamp-record",
            observed_representation="Fresh Value",
            observed_at=datetime.now(UTC),
        )

    original_evaluate = SourceEvidenceFitnessEvaluationApplicationService.evaluate
    captured: dict[str, datetime] = {}

    def _spy_evaluate(self: object, **kwargs: object) -> object:
        captured["as_of"] = kwargs["as_of"]  # type: ignore[assignment]
        return original_evaluate(self, **kwargs)  # type: ignore[arg-type]

    with (
        patch.object(
            SourceEvidenceFitnessEvaluationApplicationService,
            "evaluate",
            _spy_evaluate,
        ),
        factory() as session,
    ):
        result = InformationElementEvidenceFitnessResolutionApplicationService(
            session=session
        ).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    assert result.evaluated_at is not None
    assert captured["as_of"] == result.evaluated_at


def test_no_persistence_side_effect(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = f"cdd034-no-write-tenant-{uuid4()}"
    blueprint_name = f"CDD-034 No-Write Test Blueprint {uuid4()}"
    element_name = "No-Write Element"

    with factory() as session:
        _, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id, blueprint_name=blueprint_name, element_name=element_name
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            source_record_reference="cdd034-no-write-record",
            observed_representation="Fresh Value",
            observed_at=datetime.now(UTC),
        )

    with factory() as session:
        before = _field_value_evidence_row_count(session)

    with factory() as session:
        InformationElementEvidenceFitnessResolutionApplicationService(session=session).resolve(
            principal=_principal(tenant_id=tenant_id),
            blueprint_name=blueprint_name,
            information_element_name=element_name,
        )

    with factory() as session:
        after = _field_value_evidence_row_count(session)

    assert after == before
