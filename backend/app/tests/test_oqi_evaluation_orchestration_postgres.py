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
from sqlalchemy import Engine, inspect, select
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
from app.domain.shared.enums import GovernanceStatus, LifecycleState
from app.domain.shared.value_objects import CanonicalName, Identifier
from app.infrastructure.persistence.source_field_repository import SourceFieldRepositoryImpl
from app.infrastructure.persistence.models.oqi_remediation import (
    OqiRemediationAuthorizationORM,
)
from app.infrastructure.persistence.models.oqi_remediation_agent import (
    AgentRecommendationORM,
)
from app.infrastructure.persistence.oqi_quality_rule_repository import (
    OqiQualityRuleRepositoryImpl,
)
from app.main import create_app
from app.tests.test_oqi_h5_timeliness_crown import (
    _add_evidence,
    _seed_business_process,
    _seed_mapped_element,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _resolve_entity

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
    assert completeness.evaluation_id is not None
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

    from app.infrastructure.persistence.models.oqi_quality_evaluation import (
        QualityEvaluationORM,
    )

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
    assert first_completeness.evaluation_id == second_completeness.evaluation_id
    assert first_completeness.outcome == second_completeness.outcome == "SATISFIED"

    from app.infrastructure.persistence.models.oqi_quality_evaluation import (
        QualityEvaluationORM,
    )

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
    assert result.reliance.state in ("RELIANCE_SUPPORTED", "RELIANCE_AT_RISK", "RELIANCE_UNKNOWN")


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
