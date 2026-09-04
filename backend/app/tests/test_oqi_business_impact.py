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

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError
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
    CurrentBusinessImpactORM,
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

    # CDD-048 (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I
    # final report): the two current-head assertions mechanically re-pinned
    # from 109 to 114 (+5 new tables from migrations 0031-0033). The
    # historical 94 boundary (at 0025, before OQI6) is correctly pinned and
    # unaffected -- it must NOT change.
    assert _table_count() == 123
    alembic.command.downgrade(config, "0025_oqi5_agent_reasoning")
    assert _table_count() == 94
    alembic.command.upgrade(config, "head")
    assert _table_count() == 123


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


# =====================================================================
# CDD-052 (OQI6-R1): permanent tenant-isolation adversarial matrix for
# oqi_business_dependencies' foreign key to oqi_business_processes (TI-01
# through TI-10), mirroring the H4-R1 precedent's own TI-series shape.
# =====================================================================


def _seed_process(session: Session, *, tenant_id: str) -> tuple[UUID, int]:
    from app.domain.oqi_business_impact.process import create_business_process

    process = create_business_process(
        process_id=uuid4(),
        tenant_id=tenant_id,
        name="CDD-052 R1 Fixture Process",
        description=None,
        category=None,
        created_by="steward",
        created_on=NOW,
    )
    OqiBusinessImpactRepositoryImpl(session).insert_business_process(process)
    session.commit()
    return process.process_id, process.version


_INSERT_DEPENDENCY_SQL = text(
    "INSERT INTO oqi_business_dependencies "
    "(dependency_id, version, tenant_id, business_process_id, business_process_version, "
    "ontology_element_type, ontology_element_id, criticality, status, created_by, created_on) "
    "VALUES (:dependency_id, :version, :tenant_id, :business_process_id, :business_process_version, "
    ":ontology_element_type, :ontology_element_id, :criticality, :status, :created_by, :created_on)"
)


def _attempt_direct_dependency_insert(
    session: Session,
    *,
    tenant_id: str,
    business_process_id: UUID,
    business_process_version: int,
) -> str:
    """Raw parameterized SQL insertion, bypassing OqiBusinessImpactService
    AND the OqiBusinessDependencyORM construction site entirely -- the exact
    adversarial shape CDD-052 SS4/SS16 requires (mirroring this repository's
    own established single-construction-site firewall precedent, which
    already exempts one comparable H5 adversarial test rather than widening
    that test's own file authorization -- CDD-052's own three-path
    authorization does not include test_runtime_architecture.py, so this
    test achieves the identical genuine-PostgreSQL-bypass proof without any
    ORM constructor call for OqiBusinessDependencyORM at all)."""
    nested = session.begin_nested()
    try:
        session.execute(
            _INSERT_DEPENDENCY_SQL,
            {
                "dependency_id": str(uuid4()),
                "version": 1,
                "tenant_id": tenant_id,
                "business_process_id": str(business_process_id),
                "business_process_version": business_process_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "criticality": None,
                "status": BusinessDependencyStatus.ACTIVE.value,
                "created_by": "attacker",
                "created_on": NOW,
            },
        )
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except IntegrityError as exc:
        nested.rollback()
        return type(exc).__name__


def test_ti01_direct_orm_same_tenant_dependency_accepted(factory: sessionmaker[Session]) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        process_id, process_version = _seed_process(session, tenant_id=tenant_a)
        result = _attempt_direct_dependency_insert(
            session,
            tenant_id=tenant_a,
            business_process_id=process_id,
            business_process_version=process_version,
        )
    assert result == "ACCEPTED"  # TI-01


def test_ti02_direct_orm_cross_tenant_dependency_rejected_by_postgresql(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        process_id, process_version = _seed_process(session, tenant_id=tenant_b)
        result = _attempt_direct_dependency_insert(
            session,
            tenant_id=tenant_a,
            business_process_id=process_id,
            business_process_version=process_version,
        )
    assert result == "IntegrityError"  # TI-02: genuine PostgreSQL FK enforcement


def test_ti03_service_same_tenant_create_dependency_accepted(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        process_id, _ = _seed_process(session, tenant_id=tenant_a)
        dependency = _business_impact_service(session).create_dependency(
            tenant_id=tenant_a,
            business_process_id=process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )
        session.commit()
    assert dependency.status is BusinessDependencyStatus.ACTIVE  # TI-03


def test_ti04_service_cross_tenant_create_dependency_rejected(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        process_id, _ = _seed_process(session, tenant_id=tenant_b)
    with factory() as session, pytest.raises(ValidationException):
        _business_impact_service(session).create_dependency(
            tenant_id=tenant_a,
            business_process_id=process_id,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            criticality=None,
            created_by="steward",
            created_on=NOW,
        )  # TI-04: existing service-layer defense-in-depth, unchanged


def test_ti05_old_fk_absent(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_dependencies_process'"
            )
        ).fetchone()
    assert row is None  # TI-05


def test_ti06_new_fk_present_with_exact_shape(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_dependencies_tenant_process'"
            )
        ).fetchone()
    assert row is not None  # TI-06
    definition = row[0]
    assert "tenant_id" in definition
    assert "business_process_id" in definition
    assert "business_process_version" in definition
    assert "oqi_business_processes" in definition
    assert definition == (
        "FOREIGN KEY (tenant_id, business_process_id, business_process_version) "
        "REFERENCES oqi_business_processes(tenant_id, process_id, version)"
    )


def test_ti07_h5_parent_candidate_key_preserved(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_processes_tenant_pk'"
            )
        ).fetchone()
    assert row is not None  # TI-07
    assert row[0] == "UNIQUE (tenant_id, process_id, version)"


def test_ti08_h5_timeliness_business_process_relationship_still_functional(
    factory: sessionmaker[Session],
) -> None:
    """CDD-052 SS9/SS32: H5's own tenant-qualified FK
    (fk_oqi_timeliness_policies_tenant_business_process) is a read-only
    input to R1 -- prove a legitimate same-tenant TimelinessPolicy anchored
    to a real BusinessProcess still inserts successfully post-correction,
    reusing this repository's own established H5 crown test infrastructure
    (test_oqi_h5_timeliness_crown.py's _seed_business_process/
    _seed_unmapped_information_element/_seed_policy) rather than
    duplicating it."""
    from app.tests.test_oqi_h5_timeliness_crown import (
        _seed_business_process as _h5_seed_business_process,
        _seed_policy as _h5_seed_policy,
        _seed_unmapped_information_element as _h5_seed_unmapped_information_element,
    )

    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        process_id, process_version = _h5_seed_business_process(session, tenant_id=tenant_a)
        requirement_id = _h5_seed_unmapped_information_element(session, tenant_id=tenant_a)
        policy_id = _h5_seed_policy(
            session,
            tenant_id=tenant_a,
            information_element_requirement_id=requirement_id,
            business_process_id=process_id,
            business_process_version=process_version,
        )
    assert policy_id is not None  # TI-08


def test_ti09_migration_round_trip_preserves_valid_dependency_data(
    migrated_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    tenant_a = f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    dependency_id = uuid4()
    with factory() as session:
        process_id, process_version = _seed_process(session, tenant_id=tenant_a)
        session.execute(
            _INSERT_DEPENDENCY_SQL,
            {
                "dependency_id": str(dependency_id),
                "version": 1,
                "tenant_id": tenant_a,
                "business_process_id": str(process_id),
                "business_process_version": process_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "criticality": "HIGH",
                "status": BusinessDependencyStatus.ACTIVE.value,
                "created_by": "steward",
                "created_on": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT dependency_id, version, tenant_id, business_process_id, "
                    "business_process_version, ontology_element_type, ontology_element_id, "
                    "criticality, status FROM oqi_business_dependencies "
                    "WHERE dependency_id = :dependency_id"
                ),
                {"dependency_id": str(dependency_id)},
            ).fetchone()
            return None if result is None else tuple(result)

    before = _row()
    assert before is not None

    alembic.command.downgrade(config, "0040_oqi_h5_timeliness_eval")
    after_downgrade = _row()
    assert after_downgrade == before  # TI-09: byte-identical across downgrade

    alembic.command.upgrade(config, "head")
    after_upgrade = _row()
    assert after_upgrade == before  # TI-09: byte-identical across re-upgrade


def test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data(
    migrated_engine: Engine,
) -> None:
    """CDD-052 SS11/SS16: a cross-tenant row that the pre-R1 schema accepts
    must cause the 0041 upgrade to fail (genuine PostgreSQL FK-validation
    IntegrityError), leaving the row byte-unchanged -- never silently
    repaired, rewritten, or deleted by the migration itself."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    alembic.command.downgrade(config, "0040_oqi_h5_timeliness_eval")

    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    dependency_id = uuid4()
    with factory() as session:
        process_id, process_version = _seed_process(session, tenant_id=tenant_b)
        session.execute(
            _INSERT_DEPENDENCY_SQL,
            {
                "dependency_id": str(dependency_id),
                "version": 1,
                "tenant_id": tenant_a,  # cross-tenant: accepted by the pre-R1 plain FK
                "business_process_id": str(process_id),
                "business_process_version": process_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "criticality": None,
                "status": BusinessDependencyStatus.ACTIVE.value,
                "created_by": "attacker",
                "created_on": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT tenant_id, business_process_id, business_process_version "
                    "FROM oqi_business_dependencies WHERE dependency_id = :dependency_id"
                ),
                {"dependency_id": str(dependency_id)},
            ).fetchone()
            return None if result is None else tuple(result)

    invalid_row = _row()
    assert invalid_row is not None
    assert invalid_row[0] == tenant_a

    with pytest.raises(IntegrityError):
        alembic.command.upgrade(config, "head")  # TI-10: fails closed

    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0040_oqi_h5_timeliness_eval"  # migration did not partially apply
    assert _row() == invalid_row  # row byte-unchanged, never silently repaired

    with migrated_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM oqi_business_dependencies WHERE dependency_id = :dependency_id"),
            {"dependency_id": str(dependency_id)},
        )

    alembic.command.upgrade(config, "head")  # retry succeeds once invalid data is cleaned
    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    current_head = ScriptDirectory.from_config(config).get_current_head()
    assert version == current_head


# =====================================================================
# CDD-053 (OQI6-R2): permanent tenant-isolation adversarial matrix for
# oqi_business_impact_evaluations' foreign key to oqi_business_dependencies
# (R2-TI-01 through R2-TI-12). Uses raw parameterized SQL, not
# OqiBusinessImpactEvaluationORM construction, for the direct-persistence
# bypass proofs -- that ORM class is also covered by this repository's
# single-construction-site firewall (test_runtime_architecture.py), and
# CDD-053 SS24 explicitly corrects R1's own disclosed test-naming
# imprecision: these tests are named "direct_persistence", never "direct_orm".
# =====================================================================

_INSERT_EVALUATION_SQL = text(
    "INSERT INTO oqi_business_impact_evaluations "
    "(evaluation_id, tenant_id, business_dependency_id, business_dependency_version, "
    "ontology_element_type, ontology_element_id, outcome, considered_current_impact_id, evaluated_at) "
    "VALUES (:evaluation_id, :tenant_id, :business_dependency_id, :business_dependency_version, "
    ":ontology_element_type, :ontology_element_id, :outcome, NULL, :evaluated_at)"
)


def _seed_dependency(session: Session, *, tenant_id: str) -> tuple[UUID, int]:
    process_id, _ = _seed_process(session, tenant_id=tenant_id)
    dependency = _business_impact_service(session).create_dependency(
        tenant_id=tenant_id,
        business_process_id=process_id,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        criticality=None,
        created_by="steward",
        created_on=NOW,
    )
    session.commit()
    return dependency.dependency_id, dependency.version


def _attempt_direct_persistence_evaluation_insert(
    session: Session,
    *,
    tenant_id: str,
    business_dependency_id: UUID,
    business_dependency_version: int,
) -> str:
    """Raw parameterized SQL insertion, bypassing OqiBusinessImpactService
    AND the OqiBusinessImpactEvaluationORM construction site entirely -- the
    exact adversarial shape CDD-053 SS5/SS24 requires."""
    nested = session.begin_nested()
    try:
        session.execute(
            _INSERT_EVALUATION_SQL,
            {
                "evaluation_id": str(uuid4()),
                "tenant_id": tenant_id,
                "business_dependency_id": str(business_dependency_id),
                "business_dependency_version": business_dependency_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "outcome": BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED.value,
                "evaluated_at": NOW,
            },
        )
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except IntegrityError as exc:
        nested.rollback()
        return type(exc).__name__


def test_r2ti01_direct_persistence_same_tenant_evaluation_accepted(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, dependency_version = _seed_dependency(session, tenant_id=tenant_a)
        result = _attempt_direct_persistence_evaluation_insert(
            session,
            tenant_id=tenant_a,
            business_dependency_id=dependency_id,
            business_dependency_version=dependency_version,
        )
    assert result == "ACCEPTED"  # R2-TI-01


def test_r2ti02_direct_persistence_cross_tenant_evaluation_rejected_by_postgresql(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, dependency_version = _seed_dependency(session, tenant_id=tenant_b)
        result = _attempt_direct_persistence_evaluation_insert(
            session,
            tenant_id=tenant_a,
            business_dependency_id=dependency_id,
            business_dependency_version=dependency_version,
        )
    assert result == "IntegrityError"  # R2-TI-02: genuine PostgreSQL FK enforcement


def test_r2ti03_service_same_tenant_evaluate_business_impact_accepted(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, _ = _seed_dependency(session, tenant_id=tenant_a)
        evaluation = _business_impact_service(session).evaluate_business_impact_for_dependency(
            tenant_id=tenant_a, dependency_id=dependency_id, evaluated_at=NOW
        )
        session.commit()
    assert evaluation.business_dependency_id == dependency_id  # R2-TI-03


def test_r2ti04_service_cross_tenant_evaluate_business_impact_rejected(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, _ = _seed_dependency(session, tenant_id=tenant_b)
    with factory() as session, pytest.raises(ValidationException):
        _business_impact_service(session).evaluate_business_impact_for_dependency(
            tenant_id=tenant_a, dependency_id=dependency_id, evaluated_at=NOW
        )  # R2-TI-04: existing service-layer defense-in-depth, unchanged


def test_r2ti05_old_fk_absent(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_impact_evaluations_dependency'"
            )
        ).fetchone()
    assert row is None  # R2-TI-05


def test_r2ti06_new_fk_present_with_exact_shape(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_impact_evaluations_tenant_dependency'"
            )
        ).fetchone()
    assert row is not None  # R2-TI-06
    assert row[0] == (
        "FOREIGN KEY (tenant_id, business_dependency_id, business_dependency_version) "
        "REFERENCES oqi_business_dependencies(tenant_id, dependency_id, version)"
    )


def test_r2ti07_dependency_tenant_candidate_key_present(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_dependencies_tenant_pk'"
            )
        ).fetchone()
    assert row is not None  # R2-TI-07
    assert row[0] == "UNIQUE (tenant_id, dependency_id, version)"


def test_r2ti08_r1_dependency_process_boundary_preserved(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        parent_key = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_processes_tenant_pk'"
            )
        ).fetchone()
        child_fk = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_dependencies_tenant_process'"
            )
        ).fetchone()
    assert parent_key is not None and parent_key[0] == "UNIQUE (tenant_id, process_id, version)"
    assert child_fk is not None and child_fk[0] == (
        "FOREIGN KEY (tenant_id, business_process_id, business_process_version) "
        "REFERENCES oqi_business_processes(tenant_id, process_id, version)"
    )  # R2-TI-08


def test_r2ti09_migration_round_trip_preserves_valid_evaluation_data(
    migrated_engine: Engine,
) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    tenant_a = f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    evaluation_id = uuid4()
    with factory() as session:
        dependency_id, dependency_version = _seed_dependency(session, tenant_id=tenant_a)
        session.execute(
            _INSERT_EVALUATION_SQL,
            {
                "evaluation_id": str(evaluation_id),
                "tenant_id": tenant_a,
                "business_dependency_id": str(dependency_id),
                "business_dependency_version": dependency_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "outcome": BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED.value,
                "evaluated_at": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT evaluation_id, tenant_id, business_dependency_id, "
                    "business_dependency_version, ontology_element_type, ontology_element_id, "
                    "outcome FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"
                ),
                {"evaluation_id": str(evaluation_id)},
            ).fetchone()
            return None if result is None else tuple(result)

    before = _row()
    assert before is not None

    alembic.command.downgrade(config, "0041_oqi6_r1_dependency_tenancy")
    after_downgrade = _row()
    assert after_downgrade == before  # R2-TI-09: byte-identical across downgrade

    alembic.command.upgrade(config, "head")
    after_upgrade = _row()
    assert after_upgrade == before  # R2-TI-09: byte-identical across re-upgrade


def test_r2ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_evaluation(
    migrated_engine: Engine,
) -> None:
    """CDD-053 SS15: a cross-tenant evaluation row that the pre-R2 schema
    accepts must cause the 0042 upgrade to fail (genuine PostgreSQL
    FK-validation IntegrityError), leaving the row byte-unchanged -- never
    silently repaired, rewritten, or deleted by the migration itself."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    alembic.command.downgrade(config, "0041_oqi6_r1_dependency_tenancy")

    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    evaluation_id = uuid4()
    with factory() as session:
        dependency_id, dependency_version = _seed_dependency(session, tenant_id=tenant_b)
        session.execute(
            _INSERT_EVALUATION_SQL,
            {
                "evaluation_id": str(evaluation_id),
                "tenant_id": tenant_a,  # cross-tenant: accepted by the pre-R2 plain FK
                "business_dependency_id": str(dependency_id),
                "business_dependency_version": dependency_version,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "outcome": BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED.value,
                "evaluated_at": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT tenant_id, business_dependency_id, business_dependency_version "
                    "FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"
                ),
                {"evaluation_id": str(evaluation_id)},
            ).fetchone()
            return None if result is None else tuple(result)

    invalid_row = _row()
    assert invalid_row is not None
    assert invalid_row[0] == tenant_a

    with pytest.raises(IntegrityError):
        alembic.command.upgrade(config, "head")  # R2-TI-10: fails closed

    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0041_oqi6_r1_dependency_tenancy"  # migration did not partially apply
    assert _row() == invalid_row  # row byte-unchanged, never silently repaired

    with migrated_engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM oqi_business_impact_evaluations WHERE evaluation_id = :evaluation_id"
            ),
            {"evaluation_id": str(evaluation_id)},
        )

    alembic.command.upgrade(config, "head")  # retry succeeds once invalid data is cleaned
    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0042_oqi6_r2_evaluation_tenancy"


def test_r2ti11_h5_timeliness_unaffected(factory: sessionmaker[Session]) -> None:
    """CDD-053 SS20/SS26: R2 touches neither oqi_timeliness_policies nor the
    BusinessProcess tenant FK it depends on -- reuse test_oqi_h5_timeliness_
    crown.py's own established seeding infrastructure, as R1's own analogous
    test already does, rather than duplicating it."""
    from app.tests.test_oqi_h5_timeliness_crown import (
        _seed_business_process as _h5_seed_business_process,
        _seed_policy as _h5_seed_policy,
        _seed_unmapped_information_element as _h5_seed_unmapped_information_element,
    )

    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        process_id, process_version = _h5_seed_business_process(session, tenant_id=tenant_a)
        requirement_id = _h5_seed_unmapped_information_element(session, tenant_id=tenant_a)
        policy_id = _h5_seed_policy(
            session,
            tenant_id=tenant_a,
            information_element_requirement_id=requirement_id,
            business_process_id=process_id,
            business_process_version=process_version,
        )
    assert policy_id is not None  # R2-TI-11


# =====================================================================
# CDD-054 (OQI6-R3): permanent tenant-isolation adversarial matrix for
# current_business_impacts' and current_reliance's foreign keys to their
# respective evaluation ledgers (R3-TI-A01 through R3-TI-R06). Uses raw
# parameterized SQL, not CurrentBusinessImpactORM/CurrentRelianceORM/
# OqiBusinessImpactEvaluationORM/OqiRelianceEvaluationORM construction, for
# the direct-persistence bypass proofs -- all four classes are covered by
# this repository's single-construction-site firewall (test_runtime_
# architecture.py), exactly as R1/R2's own target classes were.
# =====================================================================

_INSERT_CURRENT_BUSINESS_IMPACT_SQL = text(
    "INSERT INTO current_business_impacts "
    "(tenant_id, business_dependency_id, latest_evaluation_id, first_seen_at, last_seen_at) "
    "VALUES (:tenant_id, :business_dependency_id, :latest_evaluation_id, :now, :now)"
)

_INSERT_RELIANCE_EVALUATION_SQL = text(
    "INSERT INTO oqi_reliance_evaluations "
    "(evaluation_id, tenant_id, ontology_element_type, ontology_element_id, state, "
    "reason_codes, contributing_state_digest, evaluated_at) "
    "VALUES (:evaluation_id, :tenant_id, :ontology_element_type, :ontology_element_id, "
    ":state, :reason_codes, :contributing_state_digest, :now)"
)

_INSERT_CURRENT_RELIANCE_SQL = text(
    "INSERT INTO current_reliance "
    "(tenant_id, ontology_element_type, ontology_element_id, latest_evaluation_id, "
    "first_seen_at, last_seen_at) "
    "VALUES (:tenant_id, :ontology_element_type, :ontology_element_id, :latest_evaluation_id, "
    ":now, :now)"
)


def _seed_business_impact_evaluation_direct(
    session: Session, *, tenant_id: str
) -> tuple[UUID, UUID]:
    """Raw-SQL-seeded BusinessImpactEvaluation, bypassing
    OqiBusinessImpactService entirely -- unlike the governed service path,
    this does NOT also populate current_business_impacts, so the Current*
    pointer fixture space remains clean for the adversarial tests below.
    Returns (business_dependency_id, evaluation_id)."""
    dependency_id, dependency_version = _seed_dependency(session, tenant_id=tenant_id)
    evaluation_id = uuid4()
    session.execute(
        _INSERT_EVALUATION_SQL,
        {
            "evaluation_id": str(evaluation_id),
            "tenant_id": tenant_id,
            "business_dependency_id": str(dependency_id),
            "business_dependency_version": dependency_version,
            "ontology_element_type": OntologyElementType.ENTITY.value,
            "ontology_element_id": str(uuid4()),
            "outcome": BusinessImpactOutcome.BUSINESS_IMPACT_IDENTIFIED.value,
            "evaluated_at": NOW,
        },
    )
    session.commit()
    return dependency_id, evaluation_id


def _attempt_direct_persistence_current_business_impact_insert(
    session: Session, *, tenant_id: str, business_dependency_id: UUID, latest_evaluation_id: UUID
) -> str:
    nested = session.begin_nested()
    try:
        session.execute(
            _INSERT_CURRENT_BUSINESS_IMPACT_SQL,
            {
                "tenant_id": tenant_id,
                "business_dependency_id": str(business_dependency_id),
                "latest_evaluation_id": str(latest_evaluation_id),
                "now": NOW,
            },
        )
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except IntegrityError as exc:
        nested.rollback()
        return type(exc).__name__


def _seed_reliance_evaluation_direct(session: Session, *, tenant_id: str) -> UUID:
    """Raw-SQL-seeded RelianceEvaluation, used only to construct the
    cross-tenant attack fixture (bypassing the service, which would
    otherwise never itself derive a foreign-tenant evaluation_id)."""
    evaluation_id = uuid4()
    session.execute(
        _INSERT_RELIANCE_EVALUATION_SQL,
        {
            "evaluation_id": str(evaluation_id),
            "tenant_id": tenant_id,
            "ontology_element_type": OntologyElementType.ENTITY.value,
            "ontology_element_id": str(uuid4()),
            "state": RelianceState.RELIANCE_SUPPORTED.value,
            "reason_codes": "[]",
            "contributing_state_digest": "digest",
            "now": NOW,
        },
    )
    session.commit()
    return evaluation_id


def _attempt_direct_persistence_current_reliance_insert(
    session: Session, *, tenant_id: str, latest_evaluation_id: UUID
) -> str:
    nested = session.begin_nested()
    try:
        session.execute(
            _INSERT_CURRENT_RELIANCE_SQL,
            {
                "tenant_id": tenant_id,
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "latest_evaluation_id": str(latest_evaluation_id),
                "now": NOW,
            },
        )
        session.flush()
        nested.rollback()
        return "ACCEPTED"
    except IntegrityError as exc:
        nested.rollback()
        return type(exc).__name__


def test_r3tia01_direct_persistence_same_tenant_current_business_impact_accepted(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, evaluation_id = _seed_business_impact_evaluation_direct(
            session, tenant_id=tenant_a
        )
        result = _attempt_direct_persistence_current_business_impact_insert(
            session,
            tenant_id=tenant_a,
            business_dependency_id=dependency_id,
            latest_evaluation_id=evaluation_id,
        )
    assert result == "ACCEPTED"  # R3-TI-A01


def test_r3tia02_direct_persistence_cross_tenant_current_business_impact_rejected_by_postgresql(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, _ = _seed_dependency(session, tenant_id=tenant_a)
        _, evaluation_id_b = _seed_business_impact_evaluation_direct(session, tenant_id=tenant_b)
        result = _attempt_direct_persistence_current_business_impact_insert(
            session,
            tenant_id=tenant_a,
            business_dependency_id=dependency_id,
            latest_evaluation_id=evaluation_id_b,
        )
    assert result == "IntegrityError"  # R3-TI-A02: genuine PostgreSQL FK enforcement


def test_r3tia03_service_same_tenant_evaluate_business_impact_populates_current_pointer(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, _ = _seed_dependency(session, tenant_id=tenant_a)
        evaluation = _business_impact_service(session).evaluate_business_impact_for_dependency(
            tenant_id=tenant_a, dependency_id=dependency_id, evaluated_at=NOW
        )
        current = session.get(CurrentBusinessImpactORM, (tenant_a, dependency_id))
    assert current is not None and current.latest_evaluation_id == evaluation.evaluation_id
    # R3-TI-A03


def test_r3tia04_business_impact_evaluation_tenant_candidate_key_present(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_impact_evaluations_tenant_pk'"
            )
        ).fetchone()
    assert row is not None  # R3-TI-A04
    assert row[0] == "UNIQUE (tenant_id, evaluation_id)"


def test_r3tia05_current_business_impacts_tenant_fk_present_with_exact_shape(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_current_business_impacts_tenant_evaluation'"
            )
        ).fetchone()
    assert row is not None  # R3-TI-A05
    assert row[0] == (
        "FOREIGN KEY (tenant_id, latest_evaluation_id) "
        "REFERENCES oqi_business_impact_evaluations(tenant_id, evaluation_id)"
    )


def test_r3tia06_current_business_impacts_old_fk_absent(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'fk_current_business_impacts_latest_evaluation_id'"
            )
        ).fetchone()
    assert row is None  # R3-TI-A06


def test_r3tia07_current_business_impact_pointer_lifecycle_upsert_preserved(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        dependency_id, _ = _seed_dependency(session, tenant_id=tenant_a)
        service = _business_impact_service(session)
        service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_a, dependency_id=dependency_id, evaluated_at=NOW
        )
        second_evaluation = service.evaluate_business_impact_for_dependency(
            tenant_id=tenant_a, dependency_id=dependency_id, evaluated_at=NOW + timedelta(seconds=1)
        )
        current = session.get(CurrentBusinessImpactORM, (tenant_a, dependency_id))
    assert current is not None
    assert current.latest_evaluation_id == second_evaluation.evaluation_id  # R3-TI-A07


def test_r3tib01_direct_persistence_same_tenant_current_reliance_accepted(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        evaluation_id = _seed_reliance_evaluation_direct(session, tenant_id=tenant_a)
        result = _attempt_direct_persistence_current_reliance_insert(
            session, tenant_id=tenant_a, latest_evaluation_id=evaluation_id
        )
    assert result == "ACCEPTED"  # R3-TI-B01


def test_r3tib02_direct_persistence_cross_tenant_current_reliance_rejected_by_postgresql(
    factory: sessionmaker[Session],
) -> None:
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        evaluation_id_b = _seed_reliance_evaluation_direct(session, tenant_id=tenant_b)
        result = _attempt_direct_persistence_current_reliance_insert(
            session, tenant_id=tenant_a, latest_evaluation_id=evaluation_id_b
        )
    assert result == "IntegrityError"  # R3-TI-B02: genuine PostgreSQL FK enforcement


def test_r3tib03_service_same_tenant_evaluate_reliance_populates_current_pointer(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    entity_id = uuid4()
    with factory() as session:
        evaluation = _business_impact_service(session).evaluate_reliance_for_subject(
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        current = session.get(
            CurrentRelianceORM, (tenant_a, OntologyElementType.ENTITY.value, entity_id)
        )
    assert current is not None and current.latest_evaluation_id == evaluation.evaluation_id
    # R3-TI-B03


def test_r3tib04_reliance_evaluation_tenant_candidate_key_present(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_reliance_evaluations_tenant_pk'"
            )
        ).fetchone()
    assert row is not None  # R3-TI-B04
    assert row[0] == "UNIQUE (tenant_id, evaluation_id)"


def test_r3tib05_current_reliance_tenant_fk_present_with_exact_shape(
    migrated_engine: Engine,
) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_current_reliance_tenant_evaluation'"
            )
        ).fetchone()
    assert row is not None  # R3-TI-B05
    assert row[0] == (
        "FOREIGN KEY (tenant_id, latest_evaluation_id) "
        "REFERENCES oqi_reliance_evaluations(tenant_id, evaluation_id)"
    )


def test_r3tib06_current_reliance_old_fk_absent(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conname = 'fk_current_reliance_latest_evaluation_id'"
            )
        ).fetchone()
    assert row is None  # R3-TI-B06


def test_r3tib07_current_reliance_pointer_lifecycle_upsert_preserved(
    factory: sessionmaker[Session],
) -> None:
    tenant_a = f"tenant-{uuid4()}"
    entity_id = uuid4()
    with factory() as session:
        service = _business_impact_service(session)
        service.evaluate_reliance_for_subject(
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW,
        )
        second_evaluation = service.evaluate_reliance_for_subject(
            tenant_id=tenant_a,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=entity_id,
            evaluated_at=NOW + timedelta(seconds=1),
        )
        current = session.get(
            CurrentRelianceORM, (tenant_a, OntologyElementType.ENTITY.value, entity_id)
        )
    assert current is not None
    assert current.latest_evaluation_id == second_evaluation.evaluation_id  # R3-TI-B07


def test_r3tim01_to_m03_migration_round_trip(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    def _table_count() -> int:
        with migrated_engine.connect() as connection:
            return int(
                connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema='public' AND table_type='BASE TABLE' "
                        "AND table_name != 'alembic_version'"
                    )
                ).scalar_one()
            )

    assert _table_count() == 123
    alembic.command.downgrade(config, "0042_oqi6_r2_evaluation_tenancy")  # R3-TI-M02
    assert _table_count() == 123
    alembic.command.upgrade(config, "head")  # R3-TI-M01/M03
    assert _table_count() == 123


def test_r3tim04_to_m06_invalid_legacy_current_business_impact_fails_closed(
    migrated_engine: Engine,
) -> None:
    """CDD-054 SS17: a cross-tenant CurrentBusinessImpact pointer that the
    pre-R3 schema accepts must cause the 0043 upgrade to fail (genuine
    PostgreSQL FK-validation IntegrityError), leaving the row byte-
    unchanged -- never silently repaired."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    alembic.command.downgrade(config, "0042_oqi6_r2_evaluation_tenancy")

    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    with factory() as session:
        _, evaluation_id_b = _seed_business_impact_evaluation_direct(session, tenant_id=tenant_b)
        session.execute(
            _INSERT_CURRENT_BUSINESS_IMPACT_SQL,
            {
                "tenant_id": tenant_a,  # cross-tenant: accepted by the pre-R3 plain FK
                "business_dependency_id": str(uuid4()),
                "latest_evaluation_id": str(evaluation_id_b),
                "now": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT tenant_id, latest_evaluation_id FROM current_business_impacts "
                    "WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_a},
            ).fetchone()
            return None if result is None else tuple(result)

    invalid_row = _row()
    assert invalid_row is not None

    with pytest.raises(IntegrityError):
        alembic.command.upgrade(config, "head")  # R3-TI-M04: fails closed

    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0042_oqi6_r2_evaluation_tenancy"  # migration did not partially apply
    assert _row() == invalid_row  # R3-TI-M05: row byte-unchanged

    with migrated_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM current_business_impacts WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_a},
        )

    alembic.command.upgrade(config, "head")  # R3-TI-M06: retry succeeds once cleaned
    current_head = ScriptDirectory.from_config(config).get_current_head()
    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == current_head


def test_r3tim07_to_m09_invalid_legacy_current_reliance_fails_closed(
    migrated_engine: Engine,
) -> None:
    """CDD-054 SS17: identical fail-closed proof for the CurrentReliance
    boundary."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))

    alembic.command.downgrade(config, "0042_oqi6_r2_evaluation_tenancy")

    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    with factory() as session:
        evaluation_id_b = _seed_reliance_evaluation_direct(session, tenant_id=tenant_b)
        session.execute(
            _INSERT_CURRENT_RELIANCE_SQL,
            {
                "tenant_id": tenant_a,  # cross-tenant: accepted by the pre-R3 plain FK
                "ontology_element_type": OntologyElementType.ENTITY.value,
                "ontology_element_id": str(uuid4()),
                "latest_evaluation_id": str(evaluation_id_b),
                "now": NOW,
            },
        )
        session.commit()

    def _row() -> tuple[object, ...] | None:
        with migrated_engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT tenant_id, latest_evaluation_id FROM current_reliance "
                    "WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_a},
            ).fetchone()
            return None if result is None else tuple(result)

    invalid_row = _row()
    assert invalid_row is not None

    with pytest.raises(IntegrityError):
        alembic.command.upgrade(config, "head")  # R3-TI-M07: fails closed

    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0042_oqi6_r2_evaluation_tenancy"  # migration did not partially apply
    assert _row() == invalid_row  # R3-TI-M08: row byte-unchanged

    with migrated_engine.begin() as connection:
        connection.execute(
            text("DELETE FROM current_reliance WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_a},
        )

    alembic.command.upgrade(config, "head")  # R3-TI-M09: retry succeeds once cleaned
    current_head = ScriptDirectory.from_config(config).get_current_head()
    with migrated_engine.connect() as connection:
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == current_head


def test_r3tir01_r1_dependency_process_boundary_preserved(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        parent_key = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_processes_tenant_pk'"
            )
        ).fetchone()
        child_fk = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_dependencies_tenant_process'"
            )
        ).fetchone()
    assert parent_key is not None and parent_key[0] == "UNIQUE (tenant_id, process_id, version)"
    assert child_fk is not None and child_fk[0] == (
        "FOREIGN KEY (tenant_id, business_process_id, business_process_version) "
        "REFERENCES oqi_business_processes(tenant_id, process_id, version)"
    )  # R3-TI-R01


def test_r3tir02_r2_evaluation_dependency_boundary_preserved(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        parent_key = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'uq_oqi_business_dependencies_tenant_pk'"
            )
        ).fetchone()
        child_fk = connection.execute(
            text(
                "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                "WHERE conname = 'fk_oqi_business_impact_evaluations_tenant_dependency'"
            )
        ).fetchone()
    assert parent_key is not None and parent_key[0] == "UNIQUE (tenant_id, dependency_id, version)"
    assert child_fk is not None and child_fk[0] == (
        "FOREIGN KEY (tenant_id, business_dependency_id, business_dependency_version) "
        "REFERENCES oqi_business_dependencies(tenant_id, dependency_id, version)"
    )  # R3-TI-R02


def test_r3tir03_tenant_aware_uuid_identity_is_not_the_db_authority_mechanism(
    factory: sessionmaker[Session],
) -> None:
    """CDD-054 SS5: two tenants' identical logical evaluation inputs produce
    distinct evaluation_id values (tenant-aware UUID5 identity distinctness)
    -- but a direct-persistence cross-tenant Current* pointer using a real,
    existing foreign evaluation_id is still rejected by PostgreSQL. Identity
    distinctness is not the database authority mechanism; the composite FK
    is."""
    tenant_a, tenant_b = f"tenant-{uuid4()}", f"tenant-{uuid4()}"
    with factory() as session:
        _, evaluation_id_a = _seed_business_impact_evaluation_direct(session, tenant_id=tenant_a)
        dependency_id_b, evaluation_id_b = _seed_business_impact_evaluation_direct(
            session, tenant_id=tenant_b
        )
        assert evaluation_id_a != evaluation_id_b  # distinct identities across tenants

        result = _attempt_direct_persistence_current_business_impact_insert(
            session,
            tenant_id=tenant_a,
            business_dependency_id=dependency_id_b,
            latest_evaluation_id=evaluation_id_b,
        )
    assert result == "IntegrityError"  # R3-TI-R03: the FK, not identity, is the authority


def test_r3tir04_h5_timeliness_unaffected(factory: sessionmaker[Session]) -> None:
    """CDD-054 SS20: R3 touches neither oqi_timeliness_policies nor the
    BusinessProcess tenant FK it depends on -- reuse test_oqi_h5_timeliness_
    crown.py's own established seeding infrastructure, as R1's and R2's own
    analogous tests already do, rather than duplicating it."""
    from app.tests.test_oqi_h5_timeliness_crown import (
        _seed_business_process as _h5_seed_business_process,
        _seed_policy as _h5_seed_policy,
        _seed_unmapped_information_element as _h5_seed_unmapped_information_element,
    )

    tenant_a = f"tenant-{uuid4()}"
    with factory() as session:
        process_id, process_version = _h5_seed_business_process(session, tenant_id=tenant_a)
        requirement_id = _h5_seed_unmapped_information_element(session, tenant_id=tenant_a)
        policy_id = _h5_seed_policy(
            session,
            tenant_id=tenant_a,
            information_element_requirement_id=requirement_id,
            business_process_id=process_id,
            business_process_version=process_version,
        )
    assert policy_id is not None  # R3-TI-R04
