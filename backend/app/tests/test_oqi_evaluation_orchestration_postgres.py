"""CDD-056 Production OQI Explicit Evaluation Orchestration -- real-
PostgreSQL crown suite. Proves the new `OqiEvaluationOrchestrationService`
(and, for authorization/shape, the new `POST /api/v1/oqi/evaluate` route)
compose the existing, unmodified DQ dimension evaluators, OQI4, OQI6, and
Reliance correctly, preserve NOT_EVALUABLE semantics, fail closed on
cross-tenant subjects, converge on retrigger, and never cross the OQI5
authority boundary. Reuses this repository's own established sibling-test-
file helper-import precedent (`_seed_mapped_element`/`_seed_business_
process`/`_add_evidence` from `test_oqi_h5_timeliness_crown.py`; `_entity`/
`_resolve_entity` from `test_oqi_ontology_impact_postgres.py`)."""

# isort: skip_file
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.api.supplier_risk.authentication import TrustedPrincipal
from app.api.supplier_risk.dependencies import container, principal
from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_evaluation_orchestration_service import (
    OqiEvaluationOrchestrationService,
)
from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.core.config import Settings
from app.core.dependency_container import Container
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.integration import SourceField
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.oqi_cross_source_correspondence_repository import (
    OqiCrossSourceCorrespondenceRepositoryImpl,
)
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.infrastructure.persistence.models.oqi_ontology_impact_evaluation import (
    CurrentOntologyImpactORM,
)
from app.infrastructure.persistence.models.oqi_quality_evaluation import (
    QualityEvaluationORM,
)
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentRecommendationORM,
)
from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
    OqiQualityEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.main import create_app
from app.tests.test_oqi_cross_source_postgres import _admit_evidence
from app.tests.test_oqi_h5_timeliness_crown import (
    _add_evidence,
    _seed_business_process,
    _seed_mapped_element,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity
from app.tests.test_source_field_persistence_postgres import _seed_source_object, _source_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


def _orchestrator(session: Session) -> OqiEvaluationOrchestrationService:
    return OqiEvaluationOrchestrationService(session, clock=lambda: NOW)


def _completeness_rule(*, information_element_requirement_id: UUID) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=f"condition-{uuid4()}",
        version=1,
        dimension=QualityDimension.COMPLETENESS,
        finding_type=QualityFindingType.MISSING_VALUE,
        validity_primitive=None,
        information_element_requirement_id=str(information_element_requirement_id),
        rule_parameters={},
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


# =====================================================================
# Migration/table-count invariant (CDD-056 SS27).
# =====================================================================


def test_production_orchestration_introduces_zero_new_tables(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    tables = set(inspect(migrated_engine).get_table_names()) - {"alembic_version"}
    assert len(tables) == 123


# =====================================================================
# NOT_EVALUABLE baseline (CDD-056 SS47).
# =====================================================================


def test_evaluate_with_no_governed_configuration_returns_all_not_evaluable(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=uuid4(),
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )
    assert len(result.dimensions) == 9
    assert all(d.status == "NOT_EVALUABLE" for d in result.dimensions)
    assert result.ontology_impact.status == "NOT_ATTEMPTED"
    assert result.business_impact == ()
    assert result.reliance.status == "NOT_ATTEMPTED"


# =====================================================================
# OQI1 Completeness EVALUATED through the orchestrator (CDD-056 SS11, a
# crown requirement -- must not remain deferred, per SS4/SS59).
# =====================================================================


def test_completeness_and_validity_evaluated_through_orchestrator(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    completeness = next(d for d in result.dimensions if d.dimension == "COMPLETENESS")
    assert completeness.status == "EVALUATED"
    assert completeness.outcome == "SATISFIED"
    # A SATISFIED outcome with no pre-existing Finding never creates one
    # (CDD-039 SS23-25) -- the response must report `finding_id=None`, never
    # fabricate one and never substitute a bare evaluation identifier.
    assert completeness.finding_id is None
    validity = next(d for d in result.dimensions if d.dimension == "VALIDITY")
    assert validity.status == "NOT_EVALUABLE"  # no VALIDITY rule seeded -- honest, not fabricated


# =====================================================================
# Timeliness EVALUATED through the orchestrator, reusing H5's own
# established fresh/stale fixture shape (CDD-056 SS19).
# =====================================================================


def test_timeliness_evaluated_through_orchestrator(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        business_process_id, business_process_version = _seed_business_process(
            session, tenant_id=tenant_id
        )
        from app.domain.oqi_timeliness.policy import new_timeliness_policy
        from app.infrastructure.persistence.oqi_timeliness_policy_repository import (
            OqiTimelinessPolicyRepositoryImpl,
        )

        policy = new_timeliness_policy(
            policy_id=uuid4(),
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            business_process_id=business_process_id,
            business_process_version=business_process_version,
            freshness_window_seconds=1800,
            ingestion_sla_seconds=None,
            created_by="steward",
            created_on=NOW,
        )
        OqiTimelinessPolicyRepositoryImpl(session).insert_policy(policy)
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=business_process_id,
            business_process_version=business_process_version,
        )

    timeliness = next(d for d in result.dimensions if d.dimension == "TIMELINESS")
    assert timeliness.status == "EVALUATED"
    assert timeliness.outcome == "SATISFIED"


# =====================================================================
# Cross-tenant adversarial test (CDD-056 SS43). Tenant A supplies Tenant
# B's own information_element_requirement_id; the semantic-mapping lookup
# is itself tenant-scoped (SemanticMappingRepositoryImpl.get_approved_by_
# information_element_requirement takes tenant_id), so Tenant A must
# receive NOT_EVALUABLE across every dimension -- never Tenant B's data.
# =====================================================================


def test_cross_tenant_subject_fails_closed(factory: sessionmaker[Session]) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_b
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_a,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    assert all(d.status == "NOT_EVALUABLE" for d in result.dimensions)
    assert result.ontology_impact.status == "NOT_ATTEMPTED"
    assert result.business_impact == ()
    assert result.reliance.status == "NOT_ATTEMPTED"


def test_cross_tenant_subject_does_not_persist_any_evaluation(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_b
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    # Scoped to `tenant_a` (a freshly generated, test-unique tenant_id) --
    # never a blanket whole-table count, which would be contaminated by
    # every other test's own committed rows when this file runs alongside
    # other real-PostgreSQL crown suites sharing one session-scoped engine.
    with factory() as session:
        before = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_a)
        ).all()
        _orchestrator(session).evaluate(
            tenant_id=tenant_a,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )
    with factory() as session:
        after = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_a)
        ).all()
    assert len(after) == len(before) == 0


# =====================================================================
# Idempotent retrigger (CDD-056 SS45).
# =====================================================================


def test_idempotent_retrigger_converges(factory: sessionmaker[Session]) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    with factory() as session:
        first = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )
        session.commit()
    with factory() as session:
        second = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )
        session.commit()

    first_completeness = next(d for d in first.dimensions if d.dimension == "COMPLETENESS")
    second_completeness = next(d for d in second.dimensions if d.dimension == "COMPLETENESS")
    # SATISFIED with no pre-existing Finding creates no Finding on either
    # call (CDD-039 SS23-25) -- `finding_id` is stably `None` both times,
    # never fabricated on retry.
    assert first_completeness.finding_id is None
    assert second_completeness.finding_id is None
    assert first_completeness.outcome == second_completeness.outcome == "SATISFIED"

    with factory() as session:
        rows = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
        ).all()
    assert len(rows) == 1  # no uncontrolled duplicate despite two full orchestrator runs


# =====================================================================
# OQI4 -> OQI6 -> Reliance integration through the orchestrator.
# =====================================================================


def test_ontology_impact_business_impact_and_reliance_propagate_through_orchestrator(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, _source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )

        # Resolve the semantic-mapped source field's own source object to a
        # real EnterpriseEntity -- required for direct-impact resolution
        # (OQI4) and for Business-Impact/Reliance subject identity (OQI6).
        from app.infrastructure.persistence.semantic_mapping_repository import (
            SemanticMappingRepositoryImpl,
        )

        mapping = SemanticMappingRepositoryImpl(
            session
        ).get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )
        assert mapping is not None

        # Establish "known lineage" (CDD-039 §12) via evidence on a second,
        # unrelated SourceField belonging to the same SourceObject/record --
        # while deliberately leaving the *target* `source_field_id` without
        # any evidence at all, so Completeness evaluates a genuine VIOLATED
        # MISSING_VALUE outcome (a SATISFIED outcome with no pre-existing
        # Finding creates no Finding row at all, so OQI4 would have nothing
        # to propagate).
        lineage_field = SourceField(
            source_field_id=Identifier(uuid4()),
            source_object_id=Identifier(mapping.source_object_id),
            field_label=CanonicalName(f"Orchestration Lineage Field {uuid4()}"),
            lifecycle_state=LifecycleState.ACTIVE,
            governance_status=GovernanceStatus.APPROVED,
            created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
            created_on=NOW,
        )
        SourceFieldRepositoryImpl(session).create(lineage_field)
        _add_evidence(
            session,
            source_field_id=lineage_field.source_field_id.value,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )

        entity_id = _entity(session, tenant_id=tenant_id, name=f"Material-{uuid4()}")
        _resolve_entity(
            session,
            tenant_id=tenant_id,
            source_object_id=mapping.source_object_id,
            entity_id=entity_id,
        )

        process = OqiBusinessImpactService(session).create_process(
            tenant_id=tenant_id,
            name="Orchestration Test Process",
            created_by="steward",
            created_on=NOW,
        )
        OqiBusinessImpactService(session).create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    assert result.ontology_impact.status == "EVALUATED"
    assert len(result.business_impact) == 1
    assert result.business_impact[0].status == "EVALUATED"
    assert result.reliance.status == "EVALUATED"
    # A genuine open Finding on this entity deterministically yields
    # RELIANCE_AT_RISK (CDD-044 §58's decision table: `any_open_finding`
    # takes precedence over every other input) -- this is this file's own
    # AT_RISK proof through Production Orchestration.
    assert result.reliance.state == "RELIANCE_AT_RISK"

    # CDD-056 §9 (Production-Orchestration-I-R1 correction): the VIOLATED
    # Completeness dimension must report the *actual persisted* Finding ID,
    # not a bare evaluation identifier -- verify by direct PostgreSQL lookup.
    completeness = next(d for d in result.dimensions if d.dimension == "COMPLETENESS")
    assert completeness.status == "EVALUATED"
    assert completeness.outcome == "VIOLATED"
    assert completeness.finding_id is not None
    with factory() as session:
        persisted_finding = OqiQualityEvaluationRepositoryImpl(session).get_finding(
            completeness.finding_id
        )
    assert persisted_finding is not None
    assert persisted_finding.finding_id == completeness.finding_id


# =====================================================================
# Multi-source Consistency (CDD-056 §42, strengthened per I-R1 resume) --
# Source A + Source B under an active Correspondence, evaluated through
# the production orchestrator; then the missing-correspondence case,
# proving native NOT_EVALUABLE preservation, never a fabricated
# disagreement.
# =====================================================================


def test_multi_source_consistency_evaluated_through_orchestrator(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    comparison_subject_id = uuid4()
    with factory() as session:
        sap_object = _seed_source_object(session, tenant_id=tenant_id)
        sap_field = _source_field(source_object_id=sap_object, field_label=f"SAP-MFRPN-{uuid4()}")
        SourceFieldRepositoryImpl(session).create(sap_field)
        plm_object = _seed_source_object(session, tenant_id=tenant_id)
        plm_field = _source_field(source_object_id=plm_object, field_label=f"PLM-MPN-{uuid4()}")
        SourceFieldRepositoryImpl(session).create(plm_field)

        OqiQualityRuleRepositoryImpl(session).create(
            QualityRule.new(
                quality_condition_id=f"cond-{uuid4()}",
                version=1,
                dimension=QualityDimension.CONSISTENCY,
                finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
                validity_primitive=None,
                information_element_requirement_id=str(comparison_subject_id),
                rule_parameters={
                    "participants": [
                        {
                            "role": "SAP",
                            "source_field_id": str(sap_field.source_field_id.value),
                            "eligible": True,
                            "expected": True,
                            "authoritative": False,
                        },
                        {
                            "role": "PLM",
                            "source_field_id": str(plm_field.source_field_id.value),
                            "eligible": True,
                            "expected": True,
                            "authoritative": True,
                        },
                    ]
                },
                status=QualityRuleStatus.ACTIVE,
                created_by="steward",
                created_on=NOW,
            )
        )
        OqiCrossSourceCorrespondenceRepositoryImpl(session).create(
            ComparisonSubjectCorrespondence.new(
                comparison_subject_id=comparison_subject_id,
                tenant_id=tenant_id,
                version=1,
                status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
                members=(
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="SAP",
                        source_object_id=sap_object,
                        source_record_reference="MAT-100",
                    ),
                    ComparisonSubjectCorrespondenceMember(
                        participant_role="PLM",
                        source_object_id=plm_object,
                        source_record_reference="MAT-100",
                    ),
                ),
                created_by="steward",
                created_on=NOW,
            )
        )
        # Source A and Source B genuinely agree -> SATISFIED (a real
        # multi-source governed comparison, never an orchestrator-local
        # computation).
        _admit_evidence(
            session,
            source_field_id=sap_field.source_field_id.value,
            source_record_reference="MAT-100",
            value="ACME-100",
        )
        _admit_evidence(
            session,
            source_field_id=plm_field.source_field_id.value,
            source_record_reference="MAT-100",
            value="ACME-100",
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=comparison_subject_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    consistency = next(d for d in result.dimensions if d.dimension == "CONSISTENCY")
    assert consistency.status == "EVALUATED"
    assert consistency.outcome == "SATISFIED"


def test_missing_correspondence_preserves_not_evaluable_consistency(
    factory: sessionmaker[Session],
) -> None:
    """CDD-056 §13/§42: absence of an active Correspondence is a legitimate
    NOT_EVALUABLE -- the orchestrator must never interpret the absence of a
    second source as a disagreement/VIOLATED outcome."""
    tenant_id = f"tenant-{uuid4()}"
    comparison_subject_id = uuid4()
    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=comparison_subject_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    consistency = next(d for d in result.dimensions if d.dimension == "CONSISTENCY")
    assert consistency.status == "NOT_EVALUABLE"
    assert consistency.outcome is None


# =====================================================================
# Reliance -- all three governed states through Production Orchestration
# (CDD-056 §19, strengthened per I-R1 resume). AT_RISK is already proven
# above (a genuine open Finding); this section independently proves
# SUPPORTED and UNKNOWN.
# =====================================================================


def test_reliance_supported_through_orchestrator(factory: sessionmaker[Session]) -> None:
    """CDD-044 §58: `any_evaluation_ever_run=True`, no open Finding, no
    active IMPACT_UNKNOWN -> RELIANCE_SUPPORTED."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        # Evidence present on the target field itself -> genuine SATISFIED
        # (a real DQ evaluation ran; no open Finding results).
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        from app.infrastructure.persistence.semantic_mapping_repository import (
            SemanticMappingRepositoryImpl,
        )

        mapping = SemanticMappingRepositoryImpl(
            session
        ).get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )
        assert mapping is not None
        entity_id = _entity(session, tenant_id=tenant_id, name=f"Supported-Material-{uuid4()}")
        _resolve_entity(
            session,
            tenant_id=tenant_id,
            source_object_id=mapping.source_object_id,
            entity_id=entity_id,
        )
        process = OqiBusinessImpactService(session).create_process(
            tenant_id=tenant_id,
            name="Reliance Supported Process",
            created_by="steward",
            created_on=NOW,
        )
        OqiBusinessImpactService(session).create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    completeness = next(d for d in result.dimensions if d.dimension == "COMPLETENESS")
    assert completeness.outcome == "SATISFIED"
    assert completeness.finding_id is None
    assert result.reliance.status == "EVALUATED"
    assert result.reliance.state == "RELIANCE_SUPPORTED"


def test_reliance_unknown_through_orchestrator(factory: sessionmaker[Session]) -> None:
    """CDD-044 §58: `any_evaluation_ever_run=False` (no DQ evaluation has
    ever run for this entity) -> RELIANCE_UNKNOWN, even though a real
    business dependency and a resolved entity both exist."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        # No QualityRule seeded at all -> every DQ dimension reports
        # NOT_EVALUABLE, so no evaluation is ever actually run for this
        # entity, yet the entity/dependency prerequisites for OQI6/Reliance
        # are genuinely present.
        information_element_requirement_id, _source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        from app.infrastructure.persistence.semantic_mapping_repository import (
            SemanticMappingRepositoryImpl,
        )

        mapping = SemanticMappingRepositoryImpl(
            session
        ).get_approved_by_information_element_requirement(
            information_element_requirement_id, tenant_id
        )
        assert mapping is not None
        entity_id = _entity(session, tenant_id=tenant_id, name=f"Unknown-Material-{uuid4()}")
        _resolve_entity(
            session,
            tenant_id=tenant_id,
            source_object_id=mapping.source_object_id,
            entity_id=entity_id,
        )
        process = OqiBusinessImpactService(session).create_process(
            tenant_id=tenant_id,
            name="Reliance Unknown Process",
            created_by="steward",
            created_on=NOW,
        )
        OqiBusinessImpactService(session).create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()

    with factory() as session:
        result = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    assert all(d.status == "NOT_EVALUABLE" for d in result.dimensions)
    assert result.reliance.status == "EVALUATED"
    assert result.reliance.state == "RELIANCE_UNKNOWN"


# =====================================================================
# Concurrency (Production-Orchestration-I-R1 resume, mandatory before
# VM-R1). No orchestrator-level locking was added -- every stage's own
# existing advisory-lock/idempotent-upsert mechanism is exercised as-is
# (CDD-056 §25).
# =====================================================================


def test_concurrent_same_tenant_same_subject_evaluations_converge(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    errors: list[BaseException] = []

    def _run() -> None:
        try:
            with factory() as session:
                _orchestrator(session).evaluate(
                    tenant_id=tenant_id,
                    information_element_requirement_id=information_element_requirement_id,
                    source_record_reference="REC-1",
                    business_process_id=uuid4(),
                    business_process_version=1,
                )
        except BaseException as exc:  # noqa: BLE001 -- captured for the assertion below
            errors.append(exc)

    import threading

    threads = [threading.Thread(target=_run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert errors == []  # no uncontrolled IntegrityError, no deadlock
    with factory() as session:
        rows = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
        ).all()
    assert len(rows) == 1  # concurrent identical evaluations converge, no duplicate


def test_concurrent_same_tenant_different_subjects_do_not_block_each_other(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    subjects: list[tuple[UUID, UUID]] = []
    with factory() as session:
        for _ in range(3):
            ie_id, field_id = _seed_mapped_element(session, tenant_id=tenant_id)
            OqiQualityRuleRepositoryImpl(session).create(
                _completeness_rule(information_element_requirement_id=ie_id)
            )
            _add_evidence(
                session,
                source_field_id=field_id,
                observed_at=NOW - timedelta(minutes=10),
                received_at=NOW - timedelta(minutes=10),
            )
            subjects.append((ie_id, field_id))
        session.commit()

    errors: list[BaseException] = []

    def _run(ie_id: UUID) -> None:
        try:
            with factory() as session:
                _orchestrator(session).evaluate(
                    tenant_id=tenant_id,
                    information_element_requirement_id=ie_id,
                    source_record_reference="REC-1",
                    business_process_id=uuid4(),
                    business_process_version=1,
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    import threading

    threads = [threading.Thread(target=_run, args=(ie_id,)) for ie_id, _ in subjects]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert errors == []
    with factory() as session:
        rows = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
        ).all()
    assert len(rows) == 3  # one genuine row per distinct subject, no cross-subject corruption


def test_concurrent_different_tenants_same_shaped_identifiers_do_not_converge(
    factory: sessionmaker[Session],
) -> None:
    """Different tenants, each with their own independently-governed
    subject, but supplying the identical externally-visible
    `source_record_reference` literal ("REC-1", exactly as every other test
    in this file already does) and evaluated concurrently -- tenant-
    qualified natural keys (R1-R4) must keep them fully isolated even under
    real concurrency; neither tenant's row may leak into or be corrupted by
    the other's concurrent evaluation."""
    tenants_and_subjects: list[tuple[str, UUID]] = []
    with factory() as session:
        for _ in range(2):
            tenant_id = f"tenant-{uuid4()}"
            ie_id, field_id = _seed_mapped_element(session, tenant_id=tenant_id)
            OqiQualityRuleRepositoryImpl(session).create(
                _completeness_rule(information_element_requirement_id=ie_id)
            )
            _add_evidence(
                session,
                source_field_id=field_id,
                observed_at=NOW - timedelta(minutes=10),
                received_at=NOW - timedelta(minutes=10),
            )
            tenants_and_subjects.append((tenant_id, ie_id))
        session.commit()

    errors: list[BaseException] = []

    def _run(tenant_id: str, ie_id: UUID) -> None:
        try:
            with factory() as session:
                _orchestrator(session).evaluate(
                    tenant_id=tenant_id,
                    information_element_requirement_id=ie_id,
                    source_record_reference="REC-1",  # identical literal across both tenants
                    business_process_id=uuid4(),
                    business_process_version=1,
                )
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    import threading

    threads = [
        threading.Thread(target=_run, args=(tenant_id, ie_id))
        for tenant_id, ie_id in tenants_and_subjects
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert errors == []
    with factory() as session:
        for tenant_id, _ie_id in tenants_and_subjects:
            rows = session.execute(
                select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
            ).all()
            assert len(rows) == 1  # each tenant has its own, independent, uncorrupted row


# =====================================================================
# Transaction-boundary / partial-failure adversarial proof
# (Production-Orchestration-I-R1 correction, CDD-056 §22-§23, §46).
# =====================================================================


def _seed_violated_completeness_with_direct_entity(
    session: Session, *, tenant_id: str
) -> tuple[UUID, UUID]:
    """Shared fixture: a genuine VIOLATED MISSING_VALUE Completeness Finding
    (via the known-lineage-on-a-second-field convention) plus a resolved
    direct EnterpriseEntity, so OQI4 reaches its own persistence step
    (`upsert_current_impact`) rather than stopping at IMPACT_UNKNOWN.
    Returns `(information_element_requirement_id, enterprise_entity_id)`."""
    from app.infrastructure.persistence.semantic_mapping_repository import (
        SemanticMappingRepositoryImpl,
    )

    information_element_requirement_id, _source_field_id = _seed_mapped_element(
        session, tenant_id=tenant_id
    )
    OqiQualityRuleRepositoryImpl(session).create(
        _completeness_rule(information_element_requirement_id=information_element_requirement_id)
    )
    mapping = SemanticMappingRepositoryImpl(
        session
    ).get_approved_by_information_element_requirement(information_element_requirement_id, tenant_id)
    assert mapping is not None
    lineage_field = SourceField(
        source_field_id=Identifier(uuid4()),
        source_object_id=Identifier(mapping.source_object_id),
        field_label=CanonicalName(f"R1 Lineage Field {uuid4()}"),
        lifecycle_state=LifecycleState.ACTIVE,
        governance_status=GovernanceStatus.APPROVED,
        created_by=Identifier(BOOTSTRAP_SYSTEM_ENTITY_ID),
        created_on=NOW,
    )
    SourceFieldRepositoryImpl(session).create(lineage_field)
    _add_evidence(
        session,
        source_field_id=lineage_field.source_field_id.value,
        observed_at=NOW - timedelta(minutes=10),
        received_at=NOW - timedelta(minutes=10),
    )
    entity_id = _entity(session, tenant_id=tenant_id, name=f"R1-Material-{uuid4()}")
    _resolve_entity(
        session, tenant_id=tenant_id, source_object_id=mapping.source_object_id, entity_id=entity_id
    )
    session.commit()
    return information_element_requirement_id, entity_id


def test_genuine_db_failure_in_oqi4_preserves_committed_dq_state_and_recovers_session(
    factory: sessionmaker[Session],
) -> None:
    """CDD-056 §22-§23/§46 (Production-Orchestration-I-R1 primary P0
    regression test): a genuine PostgreSQL-level failure inside OQI4's own
    persistence step must NOT discard the already-computed, already-
    committed upstream Completeness Finding, must NOT leave the Session in
    an unusable aborted-transaction state, and must NOT escape `evaluate()`
    as an unhandled exception -- it must be reported as `FAILED`, exactly as
    CDD-056's partial-failure contract requires."""
    import app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository as repo_mod

    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, _entity_id = (
            _seed_violated_completeness_with_direct_entity(session, tenant_id=tenant_id)
        )

    orig_upsert = repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact

    def _broken_upsert(self: object, current_impact: object) -> None:
        # A deterministic, test-only genuine DBAPI-level failure (never a
        # pure-Python guard exception) -- simulates a real technical fault
        # mid-OQI4, strictly after upstream DQ has already been evaluated
        # and committed in an earlier, separate transaction.
        self.session.execute(  # type: ignore[attr-defined]
            text("SELECT * FROM this_table_does_not_exist_i_r1_injected")
        )

    repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact = _broken_upsert  # type: ignore[method-assign]
    try:
        with factory() as session:
            result = _orchestrator(session).evaluate(
                tenant_id=tenant_id,
                information_element_requirement_id=information_element_requirement_id,
                source_record_reference="REC-1",
                business_process_id=uuid4(),
                business_process_version=1,
            )
            # The request must not have escaped as an unhandled exception --
            # reaching this line at all is part of the proof. The Session
            # must also still be genuinely usable afterward (no lingering
            # `PendingRollbackError`/`InFailedSqlTransaction`).
            session.execute(select(1))
    finally:
        repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact = (  # type: ignore[method-assign]
            orig_upsert
        )

    completeness = next(d for d in result.dimensions if d.dimension == "COMPLETENESS")
    assert completeness.status == "EVALUATED"
    assert completeness.outcome == "VIOLATED"
    assert completeness.finding_id is not None
    assert result.ontology_impact.status == "FAILED"

    # The upstream DQ Finding/Evaluation must have survived -- committed in
    # its own earlier transaction, never rolled back by OQI4's later,
    # independent failure.
    with factory() as session:
        persisted_finding = OqiQualityEvaluationRepositoryImpl(session).get_finding(
            completeness.finding_id
        )
        rows = session.execute(
            select(QualityEvaluationORM).where(QualityEvaluationORM.tenant_id == tenant_id)
        ).all()
    assert persisted_finding is not None
    assert persisted_finding.finding_id == completeness.finding_id
    assert len(rows) == 1

    # No corrupt CurrentOntologyImpact was left behind by the failed upsert.
    with factory() as session:
        current_rows = session.execute(
            select(CurrentOntologyImpactORM).where(CurrentOntologyImpactORM.tenant_id == tenant_id)
        ).all()
    assert current_rows == []


def test_retry_after_genuine_oqi4_failure_converges(factory: sessionmaker[Session]) -> None:
    """CDD-056 §46 (Production-Orchestration-I-R1): after a genuine OQI4
    technical failure (previous test), retrying the identical governed
    evaluation with the failure injection removed must converge correctly
    -- no manual database cleanup, stable Finding identity, OQI4 now
    EVALUATED, CurrentOntologyImpact now correct."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, _entity_id = (
            _seed_violated_completeness_with_direct_entity(session, tenant_id=tenant_id)
        )

    import app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository as repo_mod

    orig_upsert = repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact

    def _broken_upsert(self: object, current_impact: object) -> None:
        self.session.execute(text("SELECT * FROM this_table_does_not_exist_i_r1_injected"))  # type: ignore[attr-defined]

    repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact = _broken_upsert  # type: ignore[method-assign]
    try:
        with factory() as session:
            first = _orchestrator(session).evaluate(
                tenant_id=tenant_id,
                information_element_requirement_id=information_element_requirement_id,
                source_record_reference="REC-1",
                business_process_id=uuid4(),
                business_process_version=1,
            )
    finally:
        repo_mod.OqiOntologyImpactEvaluationRepositoryImpl.upsert_current_impact = (  # type: ignore[method-assign]
            orig_upsert
        )
    assert first.ontology_impact.status == "FAILED"

    with factory() as session:
        second = _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )

    first_completeness = next(d for d in first.dimensions if d.dimension == "COMPLETENESS")
    second_completeness = next(d for d in second.dimensions if d.dimension == "COMPLETENESS")
    assert first_completeness.finding_id == second_completeness.finding_id
    assert second.ontology_impact.status == "EVALUATED"

    with factory() as session:
        current_rows = session.execute(
            select(CurrentOntologyImpactORM).where(CurrentOntologyImpactORM.tenant_id == tenant_id)
        ).all()
    assert len(current_rows) == 1


def test_genuine_db_failure_in_oqi6_reliance_preserves_dq_and_oqi4_state(
    factory: sessionmaker[Session],
) -> None:
    """CDD-056 §22 (Production-Orchestration-I-R1): a genuine downstream
    failure inside the shared OQI6+Reliance transaction must not roll back
    the already-committed upstream DQ Finding or the already-committed OQI4
    CurrentOntologyImpact (each its own, earlier, separate transaction);
    the shared OQI6+Reliance block itself is reported honestly as `FAILED`
    (never a fabricated partial success), preserving CDD-056's own frozen
    shared-transaction boundary rather than inventing independent commits
    within it."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, entity_id = (
            _seed_violated_completeness_with_direct_entity(session, tenant_id=tenant_id)
        )
        process = OqiBusinessImpactService(session).create_process(
            tenant_id=tenant_id, name="R1 Downstream Process", created_by="steward", created_on=NOW
        )
        OqiBusinessImpactService(session).create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()

    import app.infrastructure.persistence.oqi_business_impact_repository as biz_repo_mod
    from app.domain.oqi_business_impact.dependency import BusinessDependency

    orig_list = biz_repo_mod.OqiBusinessImpactRepositoryImpl.list_active_dependencies_for_subject

    def _broken_list(
        self: biz_repo_mod.OqiBusinessImpactRepositoryImpl,
        *,
        tenant_id: str,
        ontology_element_type: OntologyElementType,
        ontology_element_id: UUID,
    ) -> tuple[BusinessDependency, ...]:
        self.session.execute(text("SELECT * FROM this_table_does_not_exist_i_r1_injected"))
        raise AssertionError("unreachable -- the statement above always raises")

    biz_repo_mod.OqiBusinessImpactRepositoryImpl.list_active_dependencies_for_subject = (  # type: ignore[method-assign]
        _broken_list
    )
    try:
        with factory() as session:
            result = _orchestrator(session).evaluate(
                tenant_id=tenant_id,
                information_element_requirement_id=information_element_requirement_id,
                source_record_reference="REC-1",
                business_process_id=uuid4(),
                business_process_version=1,
            )
            session.execute(select(1))  # Session must remain usable.
    finally:
        biz_repo_mod.OqiBusinessImpactRepositoryImpl.list_active_dependencies_for_subject = (  # type: ignore[method-assign]
            orig_list
        )

    completeness = next(d for d in result.dimensions if d.dimension == "COMPLETENESS")
    assert completeness.status == "EVALUATED"
    assert completeness.finding_id is not None
    assert result.ontology_impact.status == "EVALUATED"
    assert result.business_impact == ()
    assert result.reliance.status == "FAILED"

    with factory() as session:
        current_impact_rows = session.execute(
            select(CurrentOntologyImpactORM).where(CurrentOntologyImpactORM.tenant_id == tenant_id)
        ).all()
    assert len(current_impact_rows) == 1  # OQI4's own earlier, separate commit survived.


# =====================================================================
# Frozen response contract -- `finding_id`, never `evaluation_id`
# (Production-Orchestration-I-R1 correction, CDD-056 §9).
# =====================================================================


def test_evaluate_route_response_exposes_finding_id_not_evaluation_id(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, _entity_id = (
            _seed_violated_completeness_with_direct_entity(session, tenant_id=tenant_id)
        )

    app = create_app()
    app.dependency_overrides[principal] = lambda: _test_principal(
        scopes=("oqi-evaluation:trigger",), tenant_id=tenant_id
    )
    app.dependency_overrides[container] = lambda: Container(Settings(), ontology_sessions=factory)
    client = TestClient(app)
    response = client.post(
        "/api/v1/oqi/evaluate",
        json={
            "information_element_requirement_id": str(information_element_requirement_id),
            "source_record_reference": "REC-1",
            "business_process_id": str(uuid4()),
            "business_process_version": 1,
        },
    )
    assert response.status_code == 202
    body = response.json()
    completeness = next(d for d in body["dimensions"] if d["dimension"] == "COMPLETENESS")
    assert set(completeness.keys()) == {"dimension", "status", "finding_id", "outcome"}
    assert completeness["outcome"] == "VIOLATED"
    assert completeness["finding_id"] is not None

    validity = next(d for d in body["dimensions"] if d["dimension"] == "VALIDITY")
    assert validity["status"] == "NOT_EVALUABLE"
    assert validity["finding_id"] is None


# =====================================================================
# Authority firewall (CDD-056 SS21, SS30, SS49) -- orchestration must
# never cross into OQI5 authority.
# =====================================================================


def test_orchestration_creates_zero_remediation_authority_rows(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        information_element_requirement_id, source_field_id = _seed_mapped_element(
            session, tenant_id=tenant_id
        )
        OqiQualityRuleRepositoryImpl(session).create(
            _completeness_rule(
                information_element_requirement_id=information_element_requirement_id
            )
        )
        _add_evidence(
            session,
            source_field_id=source_field_id,
            observed_at=NOW - timedelta(minutes=10),
            received_at=NOW - timedelta(minutes=10),
        )
        session.commit()

    with factory() as session:
        before_auth = session.execute(select(OqiRemediationAuthorizationORM)).all()
        before_rec = session.execute(select(AgentRecommendationORM)).all()
        _orchestrator(session).evaluate(
            tenant_id=tenant_id,
            information_element_requirement_id=information_element_requirement_id,
            source_record_reference="REC-1",
            business_process_id=uuid4(),
            business_process_version=1,
        )
    with factory() as session:
        after_auth = session.execute(select(OqiRemediationAuthorizationORM)).all()
        after_rec = session.execute(select(AgentRecommendationORM)).all()
    assert len(after_auth) == len(before_auth) == 0
    assert len(after_rec) == len(before_rec) == 0


# =====================================================================
# API layer: authorization scope + tenant-authority firewall through the
# real HTTP route (CDD-056 SS7, SS37-SS39).
# =====================================================================


def _test_principal(*, scopes: tuple[str, ...], tenant_id: str) -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id="user-jane",
        tenant_id=tenant_id,
        scopes=scopes,
        roles=(),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def test_evaluate_route_requires_exact_scope(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[principal] = lambda: _test_principal(
        scopes=(), tenant_id=f"tenant-{uuid4()}"
    )
    app.dependency_overrides[container] = lambda: Container(Settings(), ontology_sessions=factory)
    client = TestClient(app)
    response = client.post(
        "/api/v1/oqi/evaluate",
        json={
            "information_element_requirement_id": str(uuid4()),
            "source_record_reference": "REC-1",
            "business_process_id": str(uuid4()),
            "business_process_version": 1,
        },
    )
    assert response.status_code == 403


def test_evaluate_route_rejects_body_tenant_id(migrated_engine: Engine) -> None:
    """CDD-056 SS8/SS38: `tenant_id` is not part of the public request
    contract at all -- an attempt to inject it must be rejected by schema
    validation (extra fields forbidden), never silently accepted."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[principal] = lambda: _test_principal(
        scopes=("oqi-evaluation:trigger",), tenant_id=f"tenant-{uuid4()}"
    )
    app.dependency_overrides[container] = lambda: Container(Settings(), ontology_sessions=factory)
    client = TestClient(app)
    response = client.post(
        "/api/v1/oqi/evaluate",
        json={
            "tenant_id": "attacker-tenant",
            "information_element_requirement_id": str(uuid4()),
            "source_record_reference": "REC-1",
            "business_process_id": str(uuid4()),
            "business_process_version": 1,
        },
    )
    assert response.status_code == 422


def test_evaluate_route_with_correct_scope_returns_202(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    app = create_app()
    app.dependency_overrides[principal] = lambda: _test_principal(
        scopes=("oqi-evaluation:trigger",), tenant_id=f"tenant-{uuid4()}"
    )
    app.dependency_overrides[container] = lambda: Container(Settings(), ontology_sessions=factory)
    client = TestClient(app)
    response = client.post(
        "/api/v1/oqi/evaluate",
        json={
            "information_element_requirement_id": str(uuid4()),
            "source_record_reference": "REC-1",
            "business_process_id": str(uuid4()),
            "business_process_version": 1,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert len(body["dimensions"]) == 9
    assert all(d["status"] == "NOT_EVALUABLE" for d in body["dimensions"])
