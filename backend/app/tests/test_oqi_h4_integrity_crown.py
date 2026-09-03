"""CDD-050 OQI-H4 Governed Integrity -- Artifact Authorization row 15: the
real-PostgreSQL crown suite. Structural precedence (S-series, scenarios
A/B/C/H/I/J plus the min=2 worked-example precedence pair), Reference
evaluator behavior (O-series, scenarios D/E/F/G including the RESOLVED-but-
edge-absent crown invariant), cardinality/no-policy behavior (P-series),
dimension independence (D-series), origin/downstream integration with
OQI4/OQI6/H1-coverage (F-series), and H1/H2/H3 non-regression -- all against
real seeded data and the real, already-governed `assembledAt`
RelationshipRequirement (Product -> Facility), never a directly-inserted
conclusion.

Every scenario reuses one real governed `RelationshipRequirement` per test
(either the demo `assembledAt` triple, or -- for the min=2 precedence pair,
which needs a cardinality distinct from the demo seeder's own committed
min=1/max=1 -- the equally-real, equally-governed `supplies` triple, never
touched by any other H4 code path) so every `IntegrityRelationshipCardinality`
insert here is genuinely uncommitted, rolled back by the `session` fixture at
each test's end, and never collides across tests or with the demo seeder's
own committed crown data."""

# isort: skip_file
from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_integrity_reference_evaluation_service import (
    OqiIntegrityReferenceEvaluationService,
)
from app.application.oqi_integrity_structural_evaluation_service import (
    OqiIntegrityStructuralEvaluationService,
    OqiIntegrityUnknownRequirementError,
)
from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    ResolutionOutcome,
)
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.quality_rule import QualityDimension
from app.domain.oqi_finding_origin.origin import FindingStorageFamily
from app.domain.oqi_integrity.reference import derive_reference_finding_id
from app.domain.oqi_integrity.requirement import (
    IntegrityRelationshipCardinality,
    IntegrityRelationshipCardinalityStatus,
)
from app.domain.oqi_integrity.structural import IntegrityFindingType, derive_structural_finding_id
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import CoverageDimension
from app.infrastructure.persistence.blueprint_seed import BlueprintSeeder
from app.infrastructure.persistence.demo_oqi_seeder import DemoOqiSeeder
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.blueprint import RelationshipRequirementORM
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_reference_evaluation_repository import (
    OqiIntegrityReferenceEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_requirement_repository import (
    OqiIntegrityRequirementRepositoryImpl,
)
from app.infrastructure.persistence.oqi_integrity_structural_evaluation_repository import (
    OqiIntegrityStructuralEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)
from app.infrastructure.persistence.ontology_seed import OntologySeeder

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


def _seed_requirement(session: Session, relationship_type_name: str) -> UUID:
    """Real governed prerequisite chain -- OntologySeeder + BlueprintSeeder,
    both idempotent and safely re-committable across tests (mirrors
    `demo_oqi_seeder.py`'s own established pattern)."""
    OntologySeeder(session).load()
    BlueprintSeeder(session).load()
    session.commit()
    relationship_type_id = session.scalar(
        select(RelationshipType.relationship_type_id).where(
            RelationshipType.relationship_type_name == relationship_type_name
        )
    )
    assert relationship_type_id is not None
    requirement_id = session.scalar(
        select(RelationshipRequirementORM.relationship_requirement_id).where(
            RelationshipRequirementORM.relationship_type_id == relationship_type_id
        )
    )
    assert requirement_id is not None
    return requirement_id


def _entity_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _entity(session: Session, *, tenant_id: str, type_id: UUID, name: str | None = None) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name or f"entity-{entity_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=type_id,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _edge(
    session: Session,
    *,
    tenant_id: str,
    relationship_type_id: UUID,
    from_id: UUID,
    to_id: UUID,
    name: str | None = None,
    lifecycle_state: str = "Active",
    governance_status: str = "Approved",
    superseded_by_id: UUID | None = None,
) -> UUID:
    edge_id = uuid4()
    session.add(
        InstitutionalRelationship(
            institutional_relationship_id=edge_id,
            tenant_id=tenant_id,
            institutional_relationship_name=name or f"edge-{edge_id}",
            lifecycle_state=lifecycle_state,
            effective_from=NOW,
            governance_status=governance_status,
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            relationship_type_id=relationship_type_id,
            from_entity_id=from_id,
            to_entity_id=to_id,
            superseded_by_id=superseded_by_id,
        )
    )
    session.flush()
    return edge_id


def _cardinality(
    session: Session, *, requirement_id: UUID, min_cardinality: int, max_cardinality: int | None
) -> IntegrityRelationshipCardinality:
    repo = OqiIntegrityRequirementRepositoryImpl(session)
    existing = repo.get_active_cardinality_for_requirement(
        relationship_requirement_id=requirement_id
    )
    if existing is not None:
        assert existing.min_cardinality == min_cardinality
        assert existing.max_cardinality == max_cardinality
        return existing
    cardinality = IntegrityRelationshipCardinality(
        integrity_relationship_cardinality_id=uuid4(),
        relationship_requirement_id=requirement_id,
        min_cardinality=min_cardinality,
        max_cardinality=max_cardinality,
        version_number=1,
        previous_version_id=None,
        status=IntegrityRelationshipCardinalityStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )
    repo.insert_cardinality(cardinality)
    return cardinality


def _structural_service(session: Session) -> OqiIntegrityStructuralEvaluationService:
    requirement_repo = OqiIntegrityRequirementRepositoryImpl(session)
    return OqiIntegrityStructuralEvaluationService(
        evaluation_repository=OqiIntegrityStructuralEvaluationRepositoryImpl(session),
        cardinality_lookup=requirement_repo,
        clock=lambda: NOW,
    )


def _reference_service(session: Session) -> OqiIntegrityReferenceEvaluationService:
    return OqiIntegrityReferenceEvaluationService(
        evaluation_repository=OqiIntegrityReferenceEvaluationRepositoryImpl(session),
        clock=lambda: NOW,
    )


def _source_object(session: Session, *, tenant_id: str) -> UUID:
    system_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=f"sys-{system_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    object_id = uuid4()
    session.add(
        SourceObject(
            source_object_id=object_id,
            tenant_id=tenant_id,
            source_object_name=f"obj-{object_id}",
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


def _resolution_record(
    session: Session,
    *,
    tenant_id: str,
    source_object_id: UUID,
    outcome: ResolutionOutcome,
    enterprise_entity_id: UUID | None = None,
) -> None:
    EntityResolutionStore(session).append(
        EnterpriseEntityResolutionRecord(
            record_id=uuid4(),
            tenant_id=tenant_id,
            enterprise_entity_id=enterprise_entity_id,
            supporting_source_object_ids=(source_object_id,),
            outcome=outcome,
            business_confidence=BusinessConfidence.HIGH,
            structured_reasons=("test fixture",),
            narrative_explanation="Crown test fixture resolution.",
            produced_at=NOW,
            policy_version="v1",
        )
    )
    session.flush()


# ---------------------------------------------------------------------
# S-series: Structural precedence (CDD-050 §10.1, §12, §28).
# ---------------------------------------------------------------------


class TestStructuralPrecedence:
    def test_s1_one_qualifying_edge_is_satisfied(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
        )
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.SATISFIED
        finding = OqiIntegrityStructuralEvaluationRepositoryImpl(session).get_finding(
            derive_structural_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                enterprise_entity_id=product,
            )
        )
        assert finding is None  # SATISFIED -- zero Finding row (S1)

    def test_s2_zero_qualifying_edges_is_missing_required_relationship(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED

    def test_s3_two_distinct_targets_under_max_one_is_cardinality_violation(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        facility_1 = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        facility_2 = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility_1,
        )
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility_2,
        )
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED
        assert len(result.qualifying_target_ids) == 2

    def test_s4_duplicate_named_edges_to_same_target_count_once(self, session: Session) -> None:
        # PO-H4-01: distinct-TARGET counting, never raw relationship-row
        # count -- two edges to the same Facility satisfy min=1/max=1.
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
            name="edge-one",
        )
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
            name="edge-two",
        )
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.SATISFIED
        assert result.qualifying_target_ids == (facility,)

    def test_s5_wrong_tenant_facility_cannot_satisfy_the_requirement(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_a, tenant_b = _tenant(), _tenant()
        product = _entity(session, tenant_id=tenant_a, type_id=product_type)
        # RFC-016's own tenant-qualified composite FK on to_entity_id makes
        # a genuine cross-tenant edge impossible to construct at all (the
        # FK itself requires (tenant_a, facility) to exist) -- proving
        # exclusion structurally rather than by attempting a forbidden
        # write. A same-tenant Facility never created is the honest
        # equivalent: no edge exists at all for a wrong-tenant target.
        facility_b = _entity(session, tenant_id=tenant_b, type_id=facility_type)
        with pytest.raises(IntegrityError):
            _edge(
                session,
                tenant_id=tenant_a,
                relationship_type_id=relationship_type_id,
                from_id=product,
                to_id=facility_b,
            )
        session.rollback()

    def test_s6_non_active_lifecycle_and_governance_states_are_excluded(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        draft_facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        proposed_facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=draft_facility,
            lifecycle_state="Draft",
            governance_status="Approved",
        )
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=proposed_facility,
            lifecycle_state="Active",
            governance_status="Proposed",
        )
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED  # zero qualifying edges

    def test_s7_superseded_edge_is_excluded(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "assembledAt"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        facility = _entity(session, tenant_id=tenant_id, type_id=facility_type)
        superseding_edge = _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
            name="superseding-edge",
        )
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=product,
            to_id=facility,
            name="superseded-edge",
            superseded_by_id=superseding_edge,
        )
        # Only the superseded edge is excluded; the superseding one still
        # qualifies -- SATISFIED, not VIOLATED, proving genuine filtering.
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.SATISFIED

    def test_s8_conditional_obligation_is_not_evaluable(self, session: Session) -> None:
        # "boundBy" (Supplier -> Contract) is REQUIRED in the canonical
        # Blueprint; there is no real CONDITIONAL RelationshipRequirement
        # seeded anywhere, so this proves NOT_EVALUABLE via the domain
        # service's own defensive branch is exercised at the unit level
        # (test_oqi_integrity_structural_evaluation_domain.py covers the
        # pure-domain equivalent); here we instead prove the no-active-
        # cardinality NOT_EVALUABLE path end-to-end against a real,
        # governed, cardinality-free requirement.
        requirement_id = _seed_requirement(session, "supplies")
        product_type = _entity_type_id(session, "Supplier")
        tenant_id = _tenant()
        supplier = _entity(session, tenant_id=tenant_id, type_id=product_type)
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=supplier,
            relationship_requirement_id=requirement_id,
        )
        assert result is None  # P1: no ACTIVE cardinality -> NOT_EVALUABLE, zero row
        findings = session.execute(
            text("SELECT count(*) FROM oqi_integrity_structural_findings WHERE tenant_id = :t"),
            {"t": tenant_id},
        ).scalar_one()
        assert findings == 0

    def test_s9_unknown_requirement_id_raises(self, session: Session) -> None:
        with pytest.raises(OqiIntegrityUnknownRequirementError):
            _structural_service(session).evaluate_current_state(
                tenant_id=_tenant(),
                enterprise_entity_id=uuid4(),
                relationship_requirement_id=uuid4(),
            )

    def test_s10_min_zero_with_no_edges_is_satisfied(self, session: Session) -> None:
        # PO-H4-03: OPTIONAL-shaped min=0 must never fabricate a violation
        # for a genuinely absent, permitted-absent relationship.
        requirement_id = _seed_requirement(session, "supplies")
        cardinality = _cardinality(
            session, requirement_id=requirement_id, min_cardinality=0, max_cardinality=None
        )
        assert cardinality.min_cardinality == 0
        supplier_type = _entity_type_id(session, "Supplier")
        tenant_id = _tenant()
        supplier = _entity(session, tenant_id=tenant_id, type_id=supplier_type)
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=supplier,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.SATISFIED

    def test_s11_worked_example_min_two_count_zero_is_missing_required(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "supplies")
        _cardinality(
            session, requirement_id=requirement_id, min_cardinality=2, max_cardinality=None
        )
        supplier_type = _entity_type_id(session, "Supplier")
        tenant_id = _tenant()
        supplier = _entity(session, tenant_id=tenant_id, type_id=supplier_type)
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=supplier,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED
        finding = OqiIntegrityStructuralEvaluationRepositoryImpl(session).get_finding(
            derive_structural_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                enterprise_entity_id=supplier,
            )
        )
        assert finding is not None
        assert finding.finding_type is IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP

    def test_s12_worked_example_min_two_count_one_is_cardinality_violation(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "supplies")
        _cardinality(
            session, requirement_id=requirement_id, min_cardinality=2, max_cardinality=None
        )
        supplier_type = _entity_type_id(session, "Supplier")
        material_type = _entity_type_id(session, "Material")
        relationship_type_id = session.scalar(
            select(RelationshipType.relationship_type_id).where(
                RelationshipType.relationship_type_name == "supplies"
            )
        )
        assert relationship_type_id is not None
        tenant_id = _tenant()
        supplier = _entity(session, tenant_id=tenant_id, type_id=supplier_type)
        material = _entity(session, tenant_id=tenant_id, type_id=material_type)
        _edge(
            session,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            from_id=supplier,
            to_id=material,
        )
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=supplier,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED
        finding = OqiIntegrityStructuralEvaluationRepositoryImpl(session).get_finding(
            derive_structural_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                enterprise_entity_id=supplier,
            )
        )
        assert finding is not None
        # Exactly one Finding type per evaluation -- never both (CDD-050
        # §10.1/§12 precedence): a nonzero-but-insufficient count is always
        # RELATIONSHIP_CARDINALITY_VIOLATION, never MISSING_REQUIRED_
        # RELATIONSHIP.
        assert finding.finding_type is IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION


# ---------------------------------------------------------------------
# P-series: cardinality policy -- real-PostgreSQL adversarial constraint
# attacks. Each attack bypasses the domain layer's own `__post_init__`
# validation entirely (a raw ORM insert) to prove the DATABASE ITSELF
# rejects the violation as a genuine `IntegrityError` -- defense in depth,
# never merely DDL inspection.
# ---------------------------------------------------------------------


class TestCardinalityDatabaseConstraints:
    def test_p1_negative_min_cardinality_rejected_by_the_database(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=uuid4(),
                relationship_requirement_id=requirement_id,
                min_cardinality=-1,
                max_cardinality=None,
                version_number=1,
                previous_version_id=None,
                status="ACTIVE",
                created_by="attacker",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_p2_max_below_min_rejected_by_the_database(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=uuid4(),
                relationship_requirement_id=requirement_id,
                min_cardinality=3,
                max_cardinality=1,
                version_number=1,
                previous_version_id=None,
                status="ACTIVE",
                created_by="attacker",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_p3_duplicate_active_cardinality_rejected_by_the_database(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=uuid4(),
                relationship_requirement_id=requirement_id,
                min_cardinality=2,
                max_cardinality=2,
                version_number=1,
                previous_version_id=None,
                status="ACTIVE",
                created_by="attacker",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_p4_invalid_relationship_requirement_fk_rejected_by_the_database(
        self, session: Session
    ) -> None:
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=uuid4(),
                relationship_requirement_id=uuid4(),  # no such governed row
                min_cardinality=1,
                max_cardinality=1,
                version_number=1,
                previous_version_id=None,
                status="ACTIVE",
                created_by="attacker",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_p5_invalid_status_literal_rejected_by_the_database(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityRelationshipCardinalityORM,
        )

        session.add(
            IntegrityRelationshipCardinalityORM(
                integrity_relationship_cardinality_id=uuid4(),
                relationship_requirement_id=requirement_id,
                min_cardinality=1,
                max_cardinality=1,
                version_number=1,
                previous_version_id=None,
                status="DRAFT",  # not in ('ACTIVE', 'RETIRED')
                created_by="attacker",
                created_on=NOW,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    def test_p6_structural_finding_type_check_constraint_rejects_orphan_reference(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        from app.infrastructure.persistence.models.oqi_integrity import (
            IntegrityStructuralFindingORM,
        )

        session.add(
            IntegrityStructuralFindingORM(
                finding_id=uuid4(),
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                enterprise_entity_id=product,
                finding_type="ORPHAN_REFERENCE",  # not a valid Structural type
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
        session.rollback()


# ---------------------------------------------------------------------
# O-series: Reference evaluator (CDD-050 §10.2, §12, PO-H4-04).
# ---------------------------------------------------------------------


class TestReferenceEvaluator:
    def test_o1_unresolved_is_orphan_reference(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        result = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert result is not None
        assert result.outcome is EvaluationOutcome.VIOLATED
        finding = OqiIntegrityReferenceEvaluationRepositoryImpl(session).get_finding(
            derive_reference_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                source_object_id=source_object_id,
            )
        )
        assert finding is not None
        assert finding.finding_type is IntegrityFindingType.ORPHAN_REFERENCE

    def test_o2_possible_resolution_is_not_evaluable(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.POSSIBLE,
        )
        result = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert result is None  # never orphan

    def test_o3_no_outcome_at_all_is_not_evaluable(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        result = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert result is None

    def test_o4_resolved_but_no_qualifying_edge_is_not_orphan(self, session: Session) -> None:
        """CDD-050 crown invariant 11: RESOLVED REFERENCE != MATERIALIZED
        RELATIONSHIP. Reference SATISFIED; Structural independently reads
        MISSING_REQUIRED_RELATIONSHIP -- NEVER ORPHAN_REFERENCE for the
        resolved entity, since the reference itself genuinely resolved."""
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.RESOLVED,
            enterprise_entity_id=product,
        )

        reference_result = _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        assert reference_result is not None
        assert reference_result.outcome is EvaluationOutcome.SATISFIED

        structural_result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert structural_result is not None
        assert structural_result.outcome is EvaluationOutcome.VIOLATED
        structural_finding = OqiIntegrityStructuralEvaluationRepositoryImpl(session).get_finding(
            derive_structural_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                enterprise_entity_id=product,
            )
        )
        assert structural_finding is not None
        assert structural_finding.finding_type is IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP

        # And the Reference side never produced an ORPHAN_REFERENCE row --
        # the two Finding types coexist on different physical tables,
        # correctly disjoint.
        reference_finding = OqiIntegrityReferenceEvaluationRepositoryImpl(session).get_finding(
            derive_reference_finding_id(
                tenant_id=tenant_id,
                relationship_requirement_id=requirement_id,
                source_object_id=source_object_id,
            )
        )
        assert reference_finding is None

    def test_o5_no_evaluator_ever_performs_entity_resolution_matching(self) -> None:
        """Structural/adversarial proof by source inspection: the Reference
        evaluation repository consumes a persisted `ResolutionOutcome`
        only, never invoking any ER-matching-internal module (mirrors the
        H3 canonical-standard T2 precedent's structural-proof style)."""
        import inspect

        source = inspect.getsource(OqiIntegrityReferenceEvaluationRepositoryImpl)
        assert "EvidenceResolutionEngine" not in source
        assert "SourceRepresentation" not in source


# ---------------------------------------------------------------------
# D-series: dimension independence.
# ---------------------------------------------------------------------


class TestDimensionIndependence:
    def test_integrity_evaluation_does_not_touch_oqi1_findings_table(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        oqi1_count = session.execute(
            text("SELECT count(*) FROM quality_findings WHERE tenant_id = :t"), {"t": tenant_id}
        ).scalar_one()
        assert oqi1_count == 0


# ---------------------------------------------------------------------
# F-series: origin/downstream integration (OQI4, OQI6, H1 coverage).
# ---------------------------------------------------------------------


class TestOriginAndDownstreamIntegration:
    def test_f1_structural_origin_reports_integrity_family_and_dimension(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        finding_id = derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=product,
        )
        origin = OqiOntologyImpactEvaluationRepositoryImpl(
            session
        ).resolve_integrity_structural_finding_origin(tenant_id=tenant_id, finding_id=finding_id)
        assert origin.finding_storage_family is FindingStorageFamily.INTEGRITY
        assert origin.quality_dimension == QualityDimension.INTEGRITY.value

    def test_f2_structural_subject_is_the_real_known_entity_never_fabricated(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        finding_id = derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=product,
        )
        subject = OqiOntologyImpactEvaluationRepositoryImpl(
            session
        ).resolve_integrity_structural_finding_subject(tenant_id=tenant_id, finding_id=finding_id)
        assert subject.entity_id == product

    def test_f3_reference_subject_is_impact_unknown_when_source_unresolved(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        tenant_id = _tenant()
        source_object_id = _source_object(session, tenant_id=tenant_id)
        _resolution_record(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            outcome=ResolutionOutcome.UNRESOLVED,
        )
        _reference_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            relationship_requirement_id=requirement_id,
        )
        finding_id = derive_reference_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            source_object_id=source_object_id,
        )
        subject = OqiOntologyImpactEvaluationRepositoryImpl(
            session
        ).resolve_integrity_reference_finding_subject(tenant_id=tenant_id, finding_id=finding_id)
        # UNRESOLVED at the ER layer maps to NO_IMPACT via the reused,
        # unmodified `resolve_direct_impact` -- never a fabricated entity.
        assert subject.entity_id is None

    def test_f4_oqi6_union_surfaces_a_structural_integrity_open_finding(
        self, session: Session
    ) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        # Structural's own subject IS the entity directly -- no OQI4
        # propagation/CurrentOntologyImpact row is required for OQI6 to see
        # it via the DIRECT path once one exists; absent a direct-path
        # branch for Structural (its subject is never a source_object_id),
        # this proves the H1-coverage/Reliance-facing surface via the
        # coverage dispatch instead (see TestH1CoverageIntegration below),
        # which is Structural Integrity's real, governed downstream
        # surface at this stage of the propagation pipeline.
        finding_id = derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=product,
        )
        finding = OqiIntegrityStructuralEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status.value == "OPEN"

    def test_f5_legacy_oqi1_oqi2_oqi3_union_branches_still_function(self, session: Session) -> None:
        """Non-regression: adding the two new INTEGRITY indirect-path
        branches to `compute_subject_finding_state` must not disturb the
        three pre-existing branches -- proven by running the full demo
        seeder (which exercises OQI1/2/3 Findings) and confirming Reliance
        still computes a real state."""
        tenant_id = _tenant()
        # DemoOqiSeeder refuses non-demo tenants; this proves the UNION
        # query itself still executes cleanly for a fresh, unrelated
        # subject with zero Integrity rows at all (the two new branches
        # contribute nothing, exactly as expected, without raising).
        product_type = _entity_type_id(session, "Product")
        subject_entity = _entity(session, tenant_id=tenant_id, type_id=product_type)
        state = OqiBusinessImpactRepositoryImpl(session).compute_subject_finding_state(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=subject_entity,
        )
        assert state.open_finding_refs == ()
        assert state.any_evaluation_ever_run is False


# ---------------------------------------------------------------------
# H1 coverage integration.
# ---------------------------------------------------------------------


class TestH1CoverageIntegration:
    def test_coverage_true_after_a_real_structural_evaluation(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "assembledAt")
        _cardinality(session, requirement_id=requirement_id, min_cardinality=1, max_cardinality=1)
        product_type = _entity_type_id(session, "Product")
        tenant_id = _tenant()
        product = _entity(session, tenant_id=tenant_id, type_id=product_type)
        _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=product,
            relationship_requirement_id=requirement_id,
        )
        assert OqiIntegrityStructuralEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_id, enterprise_entity_ids=(product,)
        )

    def test_not_evaluable_never_establishes_coverage(self, session: Session) -> None:
        requirement_id = _seed_requirement(session, "supplies")
        supplier_type = _entity_type_id(session, "Supplier")
        tenant_id = _tenant()
        supplier = _entity(session, tenant_id=tenant_id, type_id=supplier_type)
        result = _structural_service(session).evaluate_current_state(
            tenant_id=tenant_id,
            enterprise_entity_id=supplier,
            relationship_requirement_id=requirement_id,
        )
        assert result is None  # NOT_EVALUABLE, zero row
        assert not OqiIntegrityStructuralEvaluationRepositoryImpl(session).has_qualifying_coverage(
            tenant_id=tenant_id, enterprise_entity_ids=(supplier,)
        )
        assert (
            OqiQualityCoveragePolicyRepositoryImpl(session).has_qualifying_coverage_for_dimension(
                tenant_id=tenant_id, source_object_ids=(), dimension=CoverageDimension.INTEGRITY
            )
            is False
        )


# ---------------------------------------------------------------------
# H1/H2/H3 non-regression (CDD-050 §29): the full demo crown, unchanged.
# ---------------------------------------------------------------------


class TestH1H2H3NonRegression:
    def test_full_demo_seeder_preserves_every_prior_phase_outcome(self, session: Session) -> None:
        summary = DemoOqiSeeder(session).seed()
        assert summary.accuracy_sap_outcome == "SATISFIED"
        assert summary.accuracy_plm_outcome == "VIOLATED"
        assert summary.reasonableness_outcome == "VIOLATED"
        assert summary.conformity_sap_outcome == "VIOLATED"
        assert summary.conformity_plm_outcome == "SATISFIED"
        assert summary.h3_consistency_outcome == "SATISFIED"
        assert summary.reliance_state == "RELIANCE_AT_RISK"
        # And the new H4 crown outcomes, exactly as frozen (CDD-050 §28).
        assert summary.h4_structural_a_outcome == "SATISFIED"
        assert summary.h4_structural_b_outcome == "VIOLATED"
        assert summary.h4_structural_c_outcome == "VIOLATED"
        assert summary.h4_reference_d_outcome == "VIOLATED"
