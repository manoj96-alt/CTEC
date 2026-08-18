"""Gate F adapter unit tests (CDD-015 §9-§12, §35; remediated per the
merged Gate F Governed Impact Decision Policy Clarification and
Remediation Report, PR #69): KRM tri-state derivation, DRM's governed
four-condition binary policy (RECOMMENDED/REJECTED only, UNKNOWN != FALSE),
and GRM's REQUIRES_REVIEW-only boundary via the public repository contract.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4, uuid5

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_SEED_NAMESPACE,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.decision_engine import DecisionEvaluationGroupModel, EvaluationOutcome
from app.domain.decision_engine.configuration import GateFPolicyConfiguration
from app.domain.governance_engine import GovernanceOutcome
from app.infrastructure.persistence.decision_repository import DecisionEvaluationRepositoryImpl
from app.infrastructure.persistence.models.assertion import Assertion
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.governance_evaluation import GovernanceEvaluationORM
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.integration.adapters.gate_f.drm import DrmUnit, GateFDecisionAdapter
from app.integration.adapters.gate_f.grm import GateFGovernanceAdapter
from app.integration.adapters.gate_f.krm import GateFKnowledgeAdapter, GovernedFact

NOW = datetime(2026, 1, 1, tzinfo=UTC)
POLICY = GateFPolicyConfiguration()


def _tenant() -> str:
    return f"gate-f-adapters-{uuid4()}"


def _entity_type_id(session: Session, name: str) -> UUID:
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _entity(session: Session, *, tenant_id: str, name: str, type_name: str) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            entity_type_id=_entity_type_id(session, type_name),
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _seed_source_system(session: Session, tenant_id: str) -> UUID:
    identifier = uuid5(BOOTSTRAP_SEED_NAMESPACE, f"gate-f-test-seed-source:{tenant_id}")
    if session.get(SourceSystem, identifier) is None:
        session.add(
            SourceSystem(
                source_system_id=identifier,
                tenant_id=tenant_id,
                source_system_name=f"Gate F Test Seed Source ({tenant_id})",
                lifecycle_state="Active",
                effective_from=NOW,
                effective_to=None,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                modified_by=None,
                modified_on=None,
                version_number=1,
                previous_version_id=None,
            )
        )
        session.flush()
    return identifier


def _assert_literal(
    session: Session,
    *,
    subject_entity_id: UUID,
    predicate: str,
    object_value: str,
    source_system_id: UUID,
) -> UUID:
    assertion_id = uuid4()
    session.add(
        Assertion(
            assertion_id=assertion_id,
            assertion_name=f"gate-f-test:{assertion_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            effective_to=None,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            modified_by=None,
            modified_on=None,
            version_number=1,
            previous_version_id=None,
            subject_entity_id=subject_entity_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=None,
            source_system_id=source_system_id,
            source_object_id=None,
            asserted_on=NOW,
            prior_assertion_id=None,
            knowledge_id=None,
            assertion_type="Institutional",
            relationship_type_id=None,
        )
    )
    session.flush()
    return assertion_id


def _seed_group(session: Session, decision_evaluation_id: UUID, tenant_id: str) -> None:
    DecisionEvaluationRepositoryImpl(session).create_group(
        DecisionEvaluationGroupModel(
            decision_evaluation_id=decision_evaluation_id, tenant_id=tenant_id, created_at=NOW
        )
    )
    session.flush()


def test_krm_high_severity_unknown_without_assertion(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        risk_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        session.commit()

        fact = GateFKnowledgeAdapter(session).derive_high_severity_disruption(
            risk_event_entity_id=risk_event
        )
    assert fact.value is None


def test_krm_high_severity_true_and_false(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)
        severe_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        moderate_event = _entity(
            session, tenant_id=tenant_id, name=f"RISK-{uuid4()}", type_name="Risk Event"
        )
        _assert_literal(
            session,
            subject_entity_id=severe_event,
            predicate="severity",
            object_value="Severe",
            source_system_id=source_system_id,
        )
        _assert_literal(
            session,
            subject_entity_id=moderate_event,
            predicate="severity",
            object_value="Moderate",
            source_system_id=source_system_id,
        )
        session.commit()

        adapter = GateFKnowledgeAdapter(session)
        severe_fact = adapter.derive_high_severity_disruption(risk_event_entity_id=severe_event)
        moderate_fact = adapter.derive_high_severity_disruption(risk_event_entity_id=moderate_event)

    assert severe_fact.value is True
    assert moderate_fact.value is False


def test_krm_candidate_evidence_missing_fact_is_unknown_not_false(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)
        alt = _entity(
            session, tenant_id=tenant_id, name=f"ALT-{uuid4()}", type_name="Alternate Supplier"
        )
        material = _entity(
            session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material"
        )
        _assert_literal(
            session,
            subject_entity_id=alt,
            predicate="qualification",
            object_value="true",
            source_system_id=source_system_id,
        )
        # No capacity assertion at all.
        session.commit()

        evidence = GateFKnowledgeAdapter(session).derive_candidate_evidence(
            tenant_id=tenant_id,
            alternate_supplier_entity_id=alt,
            material_entity_id=material,
            now=NOW,
        )
    assert evidence.qualified.value is True
    assert evidence.capacity_sufficient.value is None  # Unknown, not False


def test_drm_all_four_true_recommends(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)
        alt = _entity(
            session, tenant_id=tenant_id, name=f"ALT-{uuid4()}", type_name="Alternate Supplier"
        )
        material = _entity(
            session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material"
        )
        for predicate, value in (("qualification", "true"), ("capacity", "true")):
            _assert_literal(
                session,
                subject_entity_id=alt,
                predicate=predicate,
                object_value=value,
                source_system_id=source_system_id,
            )
        session.commit()

        decision_evaluation_id = uuid4()
        _seed_group(session, decision_evaluation_id, tenant_id)
        evidence = GateFKnowledgeAdapter(session).derive_candidate_evidence(
            tenant_id=tenant_id,
            alternate_supplier_entity_id=alt,
            material_entity_id=material,
            now=NOW,
        )
        unit = DrmUnit(
            material_entity_id=material,
            alternate_supplier_entity_id=alt,
            high_severity_disruption=GovernedFact(True),
            single_source_exposure=GovernedFact(True),
            revenue_materiality=GovernedFact(True),
            candidate=evidence,
        )
        result = GateFDecisionAdapter(session).evaluate(
            decision_evaluation_id=decision_evaluation_id, unit=unit, policy=POLICY, now=NOW
        )
        session.commit()

    assert result is not None
    assert result.outcome is EvaluationOutcome.RECOMMENDED


def test_drm_unknown_condition_returns_none_not_rejected(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        source_system_id = _seed_source_system(session, tenant_id)
        alt = _entity(
            session, tenant_id=tenant_id, name=f"ALT-{uuid4()}", type_name="Alternate Supplier"
        )
        material = _entity(
            session, tenant_id=tenant_id, name=f"MAT-{uuid4()}", type_name="Material"
        )
        for predicate, value in (("qualification", "true"), ("capacity", "true")):
            _assert_literal(
                session,
                subject_entity_id=alt,
                predicate=predicate,
                object_value=value,
                source_system_id=source_system_id,
            )
        session.commit()

        decision_evaluation_id = uuid4()
        _seed_group(session, decision_evaluation_id, tenant_id)
        evidence = GateFKnowledgeAdapter(session).derive_candidate_evidence(
            tenant_id=tenant_id,
            alternate_supplier_entity_id=alt,
            material_entity_id=material,
            now=NOW,
        )
        # Condition 4 (candidate) is known True; condition 1 (severity) is
        # the only Unknown one, and no condition is positively False --
        # the policy must not fabricate a result.
        unit = DrmUnit(
            material_entity_id=material,
            alternate_supplier_entity_id=alt,
            high_severity_disruption=GovernedFact(None),
            single_source_exposure=GovernedFact(True),
            revenue_materiality=GovernedFact(True),
            candidate=evidence,
        )
        result = GateFDecisionAdapter(session).evaluate(
            decision_evaluation_id=decision_evaluation_id, unit=unit, policy=POLICY, now=NOW
        )
        session.commit()

    assert result is None


def test_drm_single_known_false_forces_rejected_even_with_other_unknowns(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        decision_evaluation_id = uuid4()
        _seed_group(session, decision_evaluation_id, tenant_id)
        unit = DrmUnit(
            material_entity_id=uuid4(),
            alternate_supplier_entity_id=None,
            high_severity_disruption=GovernedFact(False),
            single_source_exposure=GovernedFact(None),
            revenue_materiality=GovernedFact(None),
            candidate=None,
        )
        result = GateFDecisionAdapter(session).evaluate(
            decision_evaluation_id=decision_evaluation_id, unit=unit, policy=POLICY, now=NOW
        )
        session.commit()

    assert result is not None
    assert result.outcome is EvaluationOutcome.REJECTED


def test_grm_only_produces_requires_review_via_public_contract(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine)
    tenant_id = _tenant()
    with factory() as session:
        OntologySeeder(session).load()
        session.commit()
        decision_evaluation_id = uuid4()
        _seed_group(session, decision_evaluation_id, tenant_id)
        session.commit()

        result = GateFGovernanceAdapter(session).evaluate(
            decision_evaluation_id=decision_evaluation_id, now=NOW
        )
        session.commit()

    with factory() as session:
        record = session.get(GovernanceEvaluationORM, result.record_identifier)
        assert record is not None
        assert record.governance_outcome == GovernanceOutcome.REQUIRES_REVIEW.value
        assert record.governed_record_type == "DecisionEvaluation"
