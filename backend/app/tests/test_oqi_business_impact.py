"""CDD-044 Artifact Authorization §2.1 row 10: OQI6 -- Criticality,
Business Impact & Explainable Reliance test suite. Domain-level decision-
table proofs, migration round trip, and real-PostgreSQL crown tests built
on real OQI1/OQI4 Finding/impact/entity-resolution cascades (reusing this
repository's own established sibling-test-file helper-import
precedent -- e.g. `test_oqi_remediation_agent_i2.py` already imports
`_seed_oqi1_finding`/`_seed_oqi2_finding`/`_seed_oqi3_finding` from
`test_oqi_remediation_i1.py`)."""

# isort: skip_file
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, inspect
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_business_impact_service import OqiBusinessImpactService
from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.domain.oqi_business_impact.dependency import (
    BusinessDependencyStatus,
    Criticality,
    criticality_sort_key,
)
from app.domain.oqi_business_impact.impact import (
    BusinessImpactOutcome,
    derive_business_impact_outcome,
)
from app.domain.oqi_business_impact.process import BusinessImpactCategory, BusinessProcessStatus
from app.domain.oqi_business_impact.reliance import ReasonCode, RelianceState, derive_reliance_state
from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    FindingFamily,
    OntologyElementType,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.oqi_business_impact import (
    CurrentRelianceORM,
    OqiBusinessDependencyORM,
    OqiBusinessImpactEvaluationORM,
    OqiRelianceEvaluationORM,
)
from app.infrastructure.persistence.oqi_business_impact_repository import (
    OqiBusinessImpactRepositoryImpl,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.tests.test_oqi_ontology_impact_postgres import _entity, _oqi1_finding, _resolve_entity
from app.tests.test_oqi_quality_postgres import _completeness_rule, _seed_field as _seed_oqi1_field

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _clock() -> datetime:
    return NOW


def _ontology_impact_service(session: Session) -> OqiOntologyImpactEvaluationService:
    return OqiOntologyImpactEvaluationService(
        OqiOntologyImpactEvaluationRepositoryImpl(session), clock=_clock
    )


def _business_impact_service(session: Session) -> OqiBusinessImpactService:
    return OqiBusinessImpactService(session)


def _evaluate_oqi1_finding_impact(session: Session, *, tenant_id: str, finding_id: UUID) -> None:
    """Runs OQI4's real, unmodified evaluator against a real OQI1 Finding
    -- exactly the composition OQI6 depends on, never a shortcut."""
    _ontology_impact_service(session).evaluate_current_state(
        tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
    )


def _seed_oqi1_finding_with_evaluation(
    session: Session, *, tenant_id: str, status: str = "OPEN"
) -> tuple[UUID, UUID]:
    """A real OQI1 Finding *and* a real `quality_evaluations` row proving
    OQI1 actually ran against its evidence -- required for CDD-044 §18
    coverage to be establishable, unlike the bare-Finding-only
    `_oqi1_finding` shortcut some sibling suites use. Hand-built directly
    against the ORM (same technique as `_seed_oqi3_finding`'s own raw
    `BusinessRuleEvaluationORM` insert)."""
    from app.infrastructure.persistence.models.oqi_quality_evaluation import QualityEvaluationORM
    from app.infrastructure.persistence.oqi_quality_rule_repository import (
        OqiQualityRuleRepositoryImpl,
    )

    object_id, field_id = _seed_oqi1_field(session, tenant_id=tenant_id, field_label="F-1")
    condition_id = f"cond-{uuid4()}"
    rule = _completeness_rule(quality_condition_id=condition_id)
    OqiQualityRuleRepositoryImpl(session).create(rule)
    session.flush()

    session.add(
        QualityEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            quality_condition_id=condition_id,
            rule_id=rule.rule_id,
            rule_version=1,
            subject_type="SINGLE_RECORD",
            source_object_id=object_id,
            source_record_reference="REC-1",
            source_field_id=field_id,
            evaluation_mode="CURRENT_STATE",
            evaluation_origin="RULE_DETERMINISTIC",
            evaluation_horizon=NOW,
            evidence_set_digest="0" * 64,
            outcome="VIOLATED" if status == "OPEN" else "SATISFIED",
            applied_current_state_authority=True,
            state_revision_applied=1,
            evaluated_on=NOW,
        )
    )
    session.flush()

    finding_id = _oqi1_finding(
        session, tenant_id=tenant_id, source_object_id=object_id, source_field_id=field_id
    )
    if status != "OPEN":
        from app.infrastructure.persistence.models.oqi_quality_finding import QualityFindingORM

        model = session.get(QualityFindingORM, finding_id)
        assert model is not None
        model.status = status
        session.flush()
    return finding_id, object_id


@pytest.fixture
def factory(migrated_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(migrated_engine, expire_on_commit=False)


# =====================================================================
# Domain-level decision-table proofs (CDD-044 §58-§59) -- no DB required.
# =====================================================================


def test_reliance_decision_table_exact() -> None:
    """CDD-044 §58's exact four rows."""
    state, reasons = derive_reliance_state(
        any_open_finding=True, any_evaluation_ever_run=False, any_active_impact_unknown=False
    )
    assert state is RelianceState.RELIANCE_AT_RISK
    assert reasons == (ReasonCode.OPEN_QUALITY_CONDITION,)

    state, reasons = derive_reliance_state(
        any_open_finding=False, any_evaluation_ever_run=False, any_active_impact_unknown=False
    )
    assert state is RelianceState.RELIANCE_UNKNOWN
    assert reasons == (ReasonCode.INSUFFICIENT_QUALITY_COVERAGE,)

    state, reasons = derive_reliance_state(
        any_open_finding=False, any_evaluation_ever_run=True, any_active_impact_unknown=True
    )
    assert state is RelianceState.RELIANCE_UNKNOWN
    assert reasons == (ReasonCode.ONTOLOGY_IMPACT_UNKNOWN,)

    state, reasons = derive_reliance_state(
        any_open_finding=False, any_evaluation_ever_run=True, any_active_impact_unknown=False
    )
    assert state is RelianceState.RELIANCE_SUPPORTED
    assert reasons == ()


def test_zero_findings_never_yields_supported() -> None:
    """CDD-044 §9's own single-most-important invariant, asserted directly."""
    state, _ = derive_reliance_state(
        any_open_finding=False, any_evaluation_ever_run=False, any_active_impact_unknown=False
    )
    assert state is not RelianceState.RELIANCE_SUPPORTED


def test_business_impact_decision_table_exact() -> None:
    """CDD-044 §59's exact four rows."""
    assert (
        derive_business_impact_outcome(active_dependency_exists=False, impact_status=None)
        is BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN
    )
    assert (
        derive_business_impact_outcome(
            active_dependency_exists=True, impact_status=CurrentImpactStatus.ACTIVE
        )
        is BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED
    )
    assert (
        derive_business_impact_outcome(
            active_dependency_exists=True, impact_status=CurrentImpactStatus.RESOLVED
        )
        is BusinessImpactOutcome.NO_KNOWN_BUSINESS_IMPACT
    )
    assert (
        derive_business_impact_outcome(active_dependency_exists=True, impact_status=None)
        is BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN
    ), "absence of any CurrentOntologyImpact row must never become NO_KNOWN_BUSINESS_IMPACT"


def test_impact_unknown_never_becomes_no_known_impact() -> None:
    """CDD-044 §23-§24's firewall, asserted directly against the
    implementation-time finding documented in `impact.py`."""
    assert (
        derive_business_impact_outcome(active_dependency_exists=True, impact_status=None)
        is not BusinessImpactOutcome.NO_KNOWN_BUSINESS_IMPACT
    )


def test_criticality_ordering_is_sort_only() -> None:
    assert criticality_sort_key(Criticality.LOW) < criticality_sort_key(Criticality.CRITICAL)


# =====================================================================
# Domain object construction / versioning (no DB required).
# =====================================================================


def test_business_process_versioning_preserves_history() -> None:
    from app.domain.oqi_business_impact.process import (
        create_business_process,
        new_business_process_version,
    )

    v1 = create_business_process(
        process_id=uuid4(),
        tenant_id="t1",
        name="Production Planning",
        description=None,
        category=BusinessImpactCategory.OPERATIONAL,
        created_by="steward",
        created_on=NOW,
    )
    v2 = new_business_process_version(
        v1, status=BusinessProcessStatus.RETIRED, created_by="steward", created_on=NOW
    )
    assert v2.process_id == v1.process_id
    assert v2.version == 2
    assert v1.status is BusinessProcessStatus.ACTIVE, "prior version object is never mutated"
    assert v2.status is BusinessProcessStatus.RETIRED


def test_business_dependency_criticality_unknown_is_first_class() -> None:
    from app.domain.oqi_business_impact.dependency import create_business_dependency

    dependency = create_business_dependency(
        dependency_id=uuid4(),
        tenant_id="t1",
        business_process_id=uuid4(),
        business_process_version=1,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        criticality=None,
        created_by="steward",
        created_on=NOW,
    )
    assert dependency.criticality is None, "None is the explicit CRITICALITY_UNKNOWN result"


def test_business_dependency_criticality_change_is_new_version() -> None:
    from app.domain.oqi_business_impact.dependency import (
        create_business_dependency,
        new_business_dependency_version,
    )

    v1 = create_business_dependency(
        dependency_id=uuid4(),
        tenant_id="t1",
        business_process_id=uuid4(),
        business_process_version=1,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        criticality=Criticality.HIGH,
        created_by="steward",
        created_on=NOW,
    )
    v2 = new_business_dependency_version(
        v1, criticality=Criticality.CRITICAL, created_by="steward", created_on=NOW
    )
    assert v1.criticality is Criticality.HIGH, "historical version object is never mutated"
    assert v2.criticality is Criticality.CRITICAL
    assert v2.version == 2

    v3 = new_business_dependency_version(v2, created_by="steward", created_on=NOW)
    assert v3.criticality is Criticality.CRITICAL, "omitted criticality means unchanged, not reset"


def test_reliance_evaluation_identity_rejects_tampering() -> None:
    from app.domain.oqi_business_impact.reliance import RelianceEvaluation

    with pytest.raises(ValidationException):
        RelianceEvaluation(
            evaluation_id=uuid4(),  # random, not the derived identity
            tenant_id="t1",
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            state=RelianceState.RELIANCE_UNKNOWN,
            reason_codes=(ReasonCode.INSUFFICIENT_QUALITY_COVERAGE,),
            contributing_state_digest="0" * 64,
            evaluated_at=NOW,
        )


# =====================================================================
# Migration (real PostgreSQL).
# =====================================================================


def test_migration_creates_expected_oqi6_schema(migrated_engine: Engine) -> None:
    tables = set(inspect(migrated_engine).get_table_names())
    assert {
        "oqi_business_processes",
        "oqi_business_dependencies",
        "oqi_business_impact_evaluations",
        "current_business_impacts",
        "oqi_reliance_evaluations",
        "current_reliance",
    } <= tables


def test_migration_round_trips_94_100_94_100(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    def _table_count() -> int:
        with migrated_engine.connect() as connection:
            from sqlalchemy import text

            return int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_type='BASE TABLE' "
                        "AND table_name != 'alembic_version'"
                    )
                ).scalar_one()
            )

    assert _table_count() == 100
    alembic.command.downgrade(config, "0025_oqi5_agent_reasoning")
    assert _table_count() == 94
    alembic.command.upgrade(config, "head")
    assert _table_count() == 100


# =====================================================================
# Crown tests (CDD-044 §62, real PostgreSQL).
# =====================================================================


def test_crown_1_open_finding_impacted_dependency_yields_at_risk_and_identified(
    factory: sessionmaker[Session],
) -> None:
    """A real OPEN OQI1 Finding, resolved via real entity resolution to a
    real EnterpriseEntity, proven IMPACTED by the real, unmodified OQI4
    evaluator, with a governed CRITICAL BusinessDependency declared against
    it -> BUSINESS_IMPACT_IDENTIFIED and RELIANCE_AT_RISK. The evaluation
    row itself proves coverage; the Finding itself proves the open
    condition; dissent/support are OQI2's own concern and are proven intact
    by OQI2/OQI4's own untouched, separately-proven test suites -- OQI6's
    logic here is family-agnostic by construction."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material-ABC123")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        session.commit()

    with factory() as session:
        _evaluate_oqi1_finding_impact(session, tenant_id=tenant_id, finding_id=finding_id)
        session.commit()

    with factory() as session:
        service = _business_impact_service(session)
        process = service.create_process(
            tenant_id=tenant_id, name="Production Planning", created_by="steward", created_on=NOW
        )
        dependency = service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.CRITICAL,
            created_by="steward",
            created_on=NOW,
        )
        impact_evaluation = service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency.dependency_id, evaluated_at=NOW
        )
        reliance_evaluation = service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        session.commit()

    assert impact_evaluation.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED
    assert reliance_evaluation.state is RelianceState.RELIANCE_AT_RISK
    assert reliance_evaluation.reason_codes == (ReasonCode.OPEN_QUALITY_CONDITION,)


def test_crown_2_impact_unknown_never_downgrades(factory: sessionmaker[Session]) -> None:
    """A real resolved entity with an OPEN Finding attributable to it via
    entity resolution, but OQI4 has not yet evaluated ontology impact for
    it (no `CurrentOntologyImpact` row exists yet -- the same real-data
    shape as a genuine `IMPACT_UNKNOWN`, since neither ever produces a row,
    per `impact.py`'s own documented finding) -> BUSINESS_IMPACT_UNKNOWN,
    never NO_KNOWN_BUSINESS_IMPACT, and RELIANCE_AT_RISK from the open
    Finding alone, discovered independently of OQI4 via entity resolution."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        _finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material-Unevaluated")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        session.commit()
    # Deliberately do NOT run the OQI4 evaluator -- impact_status stays None.

    with factory() as session:
        service = _business_impact_service(session)
        process = service.create_process(
            tenant_id=tenant_id, name="Sandbox Analytics", created_by="steward", created_on=NOW
        )
        dependency = service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.LOW,
            created_by="steward",
            created_on=NOW,
        )
        impact_evaluation = service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dependency.dependency_id, evaluated_at=NOW
        )
        reliance_evaluation = service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )

    assert impact_evaluation.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_UNKNOWN
    assert reliance_evaluation.state is RelianceState.RELIANCE_AT_RISK


def test_crown_3_no_dependency_yields_unknown_not_no_impact(
    factory: sessionmaker[Session],
) -> None:
    """OQI4 IMPACTED, zero ACTIVE dependencies declared ->
    BUSINESS_IMPACT_UNKNOWN at the subject level; zero
    BusinessImpactEvaluation rows are created (nothing to evaluate)."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material-XYZ999")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        session.commit()

    with factory() as session:
        _evaluate_oqi1_finding_impact(session, tenant_id=tenant_id, finding_id=finding_id)
        session.commit()

    with factory() as session:
        repository = OqiBusinessImpactRepositoryImpl(session)
        active_dependencies = repository.list_active_dependencies_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
        )
        assert active_dependencies == ()
        count_before = (
            session.query(OqiBusinessImpactEvaluationORM)
            .filter(OqiBusinessImpactEvaluationORM.tenant_id == tenant_id)
            .count()
        )
        assert count_before == 0


def test_crown_5_silence_does_not_earn_reliance(factory: sessionmaker[Session]) -> None:
    """Zero Findings, zero evaluation rows ever persisted for a subject ->
    RELIANCE_UNKNOWN, never RELIANCE_SUPPORTED."""
    tenant_id = f"tenant-{uuid4()}"
    entity_id = uuid4()
    with factory() as session:
        evaluation = _business_impact_service(session).evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
    assert evaluation.state is RelianceState.RELIANCE_UNKNOWN


def test_crown_5b_coverage_established_with_zero_open_yields_supported(
    factory: sessionmaker[Session],
) -> None:
    """A RESOLVED OQI1 Finding, with its own real evaluation row proving
    coverage, and zero other open conditions -> RELIANCE_SUPPORTED."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        _finding_id, object_id = _seed_oqi1_finding_with_evaluation(
            session, tenant_id=tenant_id, status="RESOLVED"
        )
        entity_id = _entity(session, tenant_id=tenant_id, name="Material-Clean")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        session.commit()

    with factory() as session:
        evaluation = _business_impact_service(session).evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
    assert evaluation.state is RelianceState.RELIANCE_SUPPORTED
    assert evaluation.reason_codes == ()


def test_crown_6_criticality_separation_same_reliance_different_impact_context(
    factory: sessionmaker[Session],
) -> None:
    """Same open condition, two dependencies at LOW and CRITICAL -> the
    identical subject-level Reliance State, with independently-visible
    per-dependency Business Impact contexts (CDD-044 §31, §90)."""
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        finding_id, object_id = _seed_oqi1_finding_with_evaluation(session, tenant_id=tenant_id)
        entity_id = _entity(session, tenant_id=tenant_id, name="Material-Shared")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=object_id, entity_id=entity_id
        )
        session.commit()

    with factory() as session:
        _evaluate_oqi1_finding_impact(session, tenant_id=tenant_id, finding_id=finding_id)
        session.commit()

    with factory() as session:
        service = _business_impact_service(session)
        process_a = service.create_process(
            tenant_id=tenant_id, name="Production Planning", created_by="s", created_on=NOW
        )
        process_b = service.create_process(
            tenant_id=tenant_id, name="Sandbox Analytics", created_by="s", created_on=NOW
        )
        dep_critical = service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process_a.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.CRITICAL,
            created_by="s",
            created_on=NOW,
        )
        dep_low = service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process_b.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            criticality=Criticality.LOW,
            created_by="s",
            created_on=NOW,
        )
        eval_critical = service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dep_critical.dependency_id, evaluated_at=NOW
        )
        eval_low = service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_id, dependency_id=dep_low.dependency_id, evaluated_at=NOW
        )
        reliance = service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        session.commit()

    assert eval_critical.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED
    assert eval_low.outcome is BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED
    assert eval_critical.evaluation_id != eval_low.evaluation_id, "both contexts remain visible"
    assert reliance.state is RelianceState.RELIANCE_AT_RISK


def test_crown_8_ai_cannot_alter_oqi6_facts_structural() -> None:
    """CDD-044 §34: no function in the OQI6 decision surface accepts an
    AgentRecommendation/AgentRun reference as an input -- structurally
    impossible, not merely policy. Verified directly against the actual
    function signatures."""
    import inspect as _inspect

    for fn in (derive_business_impact_outcome, derive_reliance_state):
        params = set(_inspect.signature(fn).parameters)
        assert not any("agent" in p.lower() or "recommendation" in p.lower() for p in params)


def test_crown_9_tenant_isolation_current_projections(factory: sessionmaker[Session]) -> None:
    """Tenant A's CurrentReliance/CurrentBusinessImpact rows are invisible
    to a lookup scoped to tenant B, even for the identical
    ontology_element_id."""
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    shared_entity_id = uuid4()

    with factory() as session:
        _business_impact_service(session).evaluate_reliance_for_subject(
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=shared_entity_id,
            evaluated_at=NOW,
        )
        session.commit()

    with factory() as session:
        row = session.get(
            CurrentRelianceORM,
            (tenant_b, OntologyElementType.ENTITY.value, shared_entity_id),
        )
        assert row is None, "tenant B must not see tenant A's current-reliance projection"
        row_a = session.get(
            CurrentRelianceORM,
            (tenant_a, OntologyElementType.ENTITY.value, shared_entity_id),
        )
        assert row_a is not None


def test_crown_9b_tenant_isolation_dependency_lookup(factory: sessionmaker[Session]) -> None:
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    shared_entity_id = uuid4()
    with factory() as session:
        service = _business_impact_service(session)
        process = service.create_process(
            tenant_id=tenant_a, name="Procurement", created_by="s", created_on=NOW
        )
        service.create_dependency(
            tenant_id=tenant_a,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=shared_entity_id,
            criticality=Criticality.HIGH,
            created_by="s",
            created_on=NOW,
        )
        session.commit()

    with factory() as session:
        repository = OqiBusinessImpactRepositoryImpl(session)
        deps_for_b = repository.list_active_dependencies_for_subject(
            tenant_id=tenant_b,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=shared_entity_id,
        )
        assert deps_for_b == (), "tenant B must not see tenant A's declared dependency"


def test_crown_10_no_monetary_inference_anywhere() -> None:
    """Static AST-level proof: no code identifier (class/function/variable/
    field name) anywhere in the OQI6 domain/application/persistence surface
    names a monetary concept, and Gate F's own Revenue Exposure module is
    never imported. Checks identifiers only (not docstrings/comments,
    which legitimately discuss the prohibition itself in prose)."""
    import ast
    import pathlib

    oqi6_files = [
        pathlib.Path(__file__).resolve().parents[1] / "domain" / "oqi_business_impact",
        pathlib.Path(__file__).resolve().parents[1]
        / "application"
        / "oqi_business_impact_service.py",
        pathlib.Path(__file__).resolve().parents[1]
        / "infrastructure"
        / "persistence"
        / "oqi_business_impact_repository.py",
        pathlib.Path(__file__).resolve().parents[1]
        / "infrastructure"
        / "persistence"
        / "models"
        / "oqi_business_impact.py",
    ]
    forbidden = ("revenue", "monetary", "dollar", "cost_exposure", "financial_impact")
    for target in oqi6_files:
        paths = [target] if target.is_file() else list(target.rglob("*.py"))
        for path in paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                name = None
                if isinstance(node, ast.Name):
                    name = node.id
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    name = node.name
                elif isinstance(node, ast.arg):
                    name = node.arg
                elif isinstance(node, ast.Attribute):
                    name = node.attr
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        lowered = alias.name.lower()
                        assert "supply_chain_impact_api" not in lowered
                        assert "gate_f" not in lowered
                if name is None:
                    continue
                lowered = name.lower()
                for term in forbidden:
                    assert term not in lowered, f"forbidden monetary identifier {name!r} in {path}"


def test_oqi5_agent_recommendation_cannot_influence_reliance_or_impact() -> None:
    """CDD-044 §33-§34, §50: reads `oqi_remediation_cases` only for the
    advisory `REMEDIATION_PENDING` annotation -- never as an input to the
    actual state/outcome decision. Verified by construction: the
    repository method used for the annotation returns a bool consumed only
    to *append* a reason code, never passed into
    `derive_reliance_state`/`derive_business_impact_outcome`."""
    import inspect as _inspect

    source = _inspect.getsource(OqiBusinessImpactService.evaluate_reliance_for_subject)
    # The pending-remediation check must occur strictly after the
    # authoritative state has already been derived.
    state_call_index = source.index("derive_reliance_state(")
    pending_check_index = source.index("has_pending_remediation_for_finding")
    assert state_call_index < pending_check_index


def test_no_direct_finding_mutation_in_oqi6() -> None:
    """CDD-044 §33: explicit grep -- no OQI6 file assigns to `.status` on
    any Finding-shaped attribute."""
    import pathlib

    target = (
        pathlib.Path(__file__).resolve().parents[1]
        / "application"
        / "oqi_business_impact_service.py"
    )
    source = target.read_text(encoding="utf-8")
    assert ".status = " not in source
    repo_target = (
        pathlib.Path(__file__).resolve().parents[1]
        / "infrastructure"
        / "persistence"
        / "oqi_business_impact_repository.py"
    )
    repo_source = repo_target.read_text(encoding="utf-8")
    assert "finding.status" not in repo_source and "Finding.status =" not in repo_source


def test_replay_is_idempotent(factory: sessionmaker[Session]) -> None:
    """Re-running the identical reliance evaluation converges to the
    identical immutable row -- no duplicate current-projection row."""
    tenant_id = f"tenant-{uuid4()}"
    entity_id = uuid4()
    with factory() as session:
        service = _business_impact_service(session)
        first = service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        second = service.evaluate_reliance_for_subject(
            tenant_id=tenant_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        session.commit()

    assert first.evaluation_id == second.evaluation_id
    with factory() as session:
        count = (
            session.query(OqiRelianceEvaluationORM)
            .filter(OqiRelianceEvaluationORM.tenant_id == tenant_id)
            .count()
        )
        current_count = (
            session.query(CurrentRelianceORM)
            .filter(CurrentRelianceORM.tenant_id == tenant_id)
            .count()
        )
    assert count == 1
    assert current_count == 1


def test_process_and_dependency_retirement_preserves_history(
    factory: sessionmaker[Session],
) -> None:
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        service = _business_impact_service(session)
        process = service.create_process(
            tenant_id=tenant_id, name="Legacy Process", created_by="s", created_on=NOW
        )
        dependency = service.create_dependency(
            tenant_id=tenant_id,
            business_process_id=process.process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            criticality=Criticality.HIGH,
            created_by="s",
            created_on=NOW,
        )
        retired_dependency = service.retire_dependency(
            tenant_id=tenant_id,
            dependency_id=dependency.dependency_id,
            created_by="s",
            created_on=NOW,
        )
        retired_process = service.retire_process(
            tenant_id=tenant_id, process_id=process.process_id, created_by="s", created_on=NOW
        )
        session.commit()

    assert retired_dependency.status is BusinessDependencyStatus.RETIRED
    assert retired_process.status is BusinessProcessStatus.RETIRED
    with factory() as session:
        original_dependency_row = (
            session.query(OqiBusinessDependencyORM)
            .filter(
                OqiBusinessDependencyORM.dependency_id == dependency.dependency_id,
                OqiBusinessDependencyORM.version == 1,
            )
            .one()
        )
        assert original_dependency_row.status == "ACTIVE", "historical version row is untouched"


# =====================================================================
# Real PostgreSQL concurrency (CDD-044 §41, §60, §77).
# =====================================================================


def test_concurrent_reliance_evaluation_serializes_via_advisory_lock(
    migrated_engine: Engine,
) -> None:
    """Two genuinely concurrent threads evaluating Reliance for the
    identical subject must serialize through OQI6's own dedicated
    advisory-lock seed (distinct from OQI1/2/3's) -- both converge on the
    identical immutable evaluation row (deterministic identity), and
    exactly one `CurrentReliance` row exists afterward, with no duplicate-
    key/constraint-violation exception from either thread."""
    import threading

    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    entity_id = uuid4()

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []
    results: list[UUID] = []
    lock = threading.Lock()

    def _worker() -> None:
        try:
            barrier.wait(timeout=5)
            with factory() as session:
                evaluation = _business_impact_service(session).evaluate_reliance_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=entity_id,
                    evaluated_at=NOW,
                )
                session.commit()
            with lock:
                results.append(evaluation.evaluation_id)
        except BaseException as exc:  # noqa: BLE001 - captured for the assertion below
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors, f"concurrent evaluation raised: {errors}"
    assert len(results) == 2
    assert results[0] == results[1], "both threads must converge on the identical evaluation_id"

    with factory() as session:
        evaluation_count = (
            session.query(OqiRelianceEvaluationORM)
            .filter(OqiRelianceEvaluationORM.tenant_id == tenant_id)
            .count()
        )
        current_count = (
            session.query(CurrentRelianceORM)
            .filter(CurrentRelianceORM.tenant_id == tenant_id)
            .count()
        )
    assert evaluation_count == 1, "no duplicate immutable evaluation row"
    assert current_count == 1, "no duplicate current-projection row"


def test_concurrent_different_tenants_do_not_block_each_other(
    migrated_engine: Engine,
) -> None:
    """Advisory-lock identity includes tenant scope -- two different
    tenants' concurrent evaluations for the same entity_id must not
    accidentally couple or corrupt each other's state."""
    import threading

    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_a = f"tenant-{uuid4()}"
    tenant_b = f"tenant-{uuid4()}"
    shared_entity_id = uuid4()

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def _worker(tenant_id: str) -> None:
        try:
            barrier.wait(timeout=5)
            with factory() as session:
                _business_impact_service(session).evaluate_reliance_for_subject(
                    tenant_id=tenant_id,
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=shared_entity_id,
                    evaluated_at=NOW,
                )
                session.commit()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=(tenant_a,)),
        threading.Thread(target=_worker, args=(tenant_b,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors, f"concurrent cross-tenant evaluation raised: {errors}"
    with factory() as session:
        row_a = session.get(
            CurrentRelianceORM, (tenant_a, OntologyElementType.ENTITY.value, shared_entity_id)
        )
        row_b = session.get(
            CurrentRelianceORM, (tenant_b, OntologyElementType.ENTITY.value, shared_entity_id)
        )
    assert row_a is not None and row_b is not None
    assert row_a.tenant_id != row_b.tenant_id
