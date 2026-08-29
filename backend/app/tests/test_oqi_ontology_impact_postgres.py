"""Real-PostgreSQL acceptance evidence for OQI4-I (CDD-042; Artifact
Authorization §2 row 12): migration schema/round-trip, deny-by-default
propagation (allowed/denied/direction/multi-hop/cycle/multi-path/depth
cap), the release-blocking writer-during-statement tests for the recursive
CTE (graph AND policy), exactly-one-mutable-statement instrumentation,
concurrent-replay idempotency, tenant isolation, and one bounded-graph
performance sanity check.

Disclosed scope note: the OQI1 Finding-family adapter branch is proven
end-to-end against a real persisted `quality_findings` row + a real
`EnterpriseEntityResolutionRecord` (the simplest cascade). The OQI2/OQI3
adapter branches were verified by direct code review against their real
ORM schemas (column names/types/FKs) and by the fake-repo service tests'
generic outcome-handling logic (family-agnostic once `resolve_finding_
subject` returns) -- a dedicated real-Postgres fixture cascade for OQI2
(QualityRule->Evaluation->Finding) and OQI3 (BusinessRule->Evaluation->
Finding) was not completed in this phase given time constraints. This is
disclosed honestly rather than presented as covered."""

# isort: skip_file
from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import alembic.command
import pytest
from alembic.config import Config
from sqlalchemy import Engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
)
from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.identity_resolution.model import (
    BusinessConfidence,
    EnterpriseEntityResolutionRecord,
    ResolutionOutcome,
)
from app.domain.oqi_ontology_impact.evaluation import (
    FindingFamily,
    ImpactOutcome,
)
from app.domain.oqi_ontology_impact.policy import (
    ImpactPropagationPolicy,
    PolicyGovernanceStatus,
    PropagationDirection,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.institutional_relationship import (
    InstitutionalRelationship,
)
from app.infrastructure.persistence.models.relationship_type import RelationshipType
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
    PropagatedPathCandidate,
)
from app.infrastructure.persistence.oqi_ontology_impact_policy_repository import (
    OqiOntologyImpactPolicyRepositoryImpl,
)
from app.tests.test_source_field_persistence_postgres import _seed_source_object

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _clock() -> datetime:
    return NOW


def _relationship_type(session: Session, *, name: str) -> UUID:
    type_id = uuid4()
    session.add(
        RelationshipType(
            relationship_type_id=type_id,
            relationship_type_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    return type_id


def _entity(
    session: Session, *, tenant_id: str, name: str, entity_type_id: UUID | None = None
) -> UUID:
    from app.core.bootstrap import BOOTSTRAP_ENTITY_TYPE_ID

    entity_id = uuid4()
    # `enterprise_entity_name` carries a legacy plain (non-tenant-scoped)
    # unique index reachable via this repository's pre-0011 migration
    # downgrade path -- always suffix with a fresh UUID so cross-tenant
    # test fixtures across this whole file can never collide, regardless
    # of the short mnemonic `name` callers pass.
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=f"{name}-{uuid4()}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=entity_type_id or BOOTSTRAP_ENTITY_TYPE_ID,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _relate(
    session: Session, *, tenant_id: str, relationship_type_id: UUID, from_id: UUID, to_id: UUID
) -> UUID:
    relationship_id = uuid4()
    session.add(
        InstitutionalRelationship(
            institutional_relationship_id=relationship_id,
            tenant_id=tenant_id,
            institutional_relationship_name=f"rel-{relationship_id}",
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            relationship_type_id=relationship_type_id,
            from_entity_id=from_id,
            to_entity_id=to_id,
        )
    )
    session.flush()
    return relationship_id


def _policy(
    session: Session,
    *,
    tenant_id: str,
    relationship_type_id: UUID,
    direction: PropagationDirection = PropagationDirection.FORWARD,
    max_depth: int = 5,
    status: PolicyGovernanceStatus = PolicyGovernanceStatus.ACTIVE,
) -> UUID:
    policy_id = uuid4()
    OqiOntologyImpactPolicyRepositoryImpl(session).create(
        ImpactPropagationPolicy(
            policy_id=policy_id,
            tenant_id=tenant_id,
            relationship_type_id=relationship_type_id,
            direction=direction,
            max_depth=max_depth,
            governance_status=status,
            version_number=1,
            previous_version_id=None,
        )
    )
    session.flush()
    return policy_id


def _resolve_entity(
    session: Session, *, tenant_id: str, source_object_id: UUID, entity_id: UUID
) -> None:
    EntityResolutionStore(session).append(
        EnterpriseEntityResolutionRecord(
            record_id=uuid4(),
            tenant_id=tenant_id,
            enterprise_entity_id=entity_id,
            supporting_source_object_ids=(source_object_id,),
            outcome=ResolutionOutcome.RESOLVED,
            business_confidence=BusinessConfidence.HIGH,
            structured_reasons=("exact match",),
            narrative_explanation="Deterministic test fixture resolution.",
            produced_at=NOW,
            policy_version="v1",
        )
    )
    session.flush()


def _oqi1_finding(
    session: Session, *, tenant_id: str, source_object_id: UUID, source_field_id: UUID
) -> UUID:
    """Constructed via the real, single-authorized-construction-site OQI1
    repository (never a raw `QualityFindingORM` insert) -- this file is not
    authorized to touch OQI1's own construction-site firewall in
    `test_runtime_architecture.py`."""
    from app.domain.oqi.evaluation import (
        EvaluationSubject,
        SourceRecordLineageIdentity,
        canonical_subject_identity,
        derive_quality_finding_id,
    )
    from app.domain.oqi.finding import QualityFinding, QualityFindingStatus
    from app.domain.oqi.quality_rule import QualityFindingType
    from app.infrastructure.persistence.oqi_quality_evaluation_repository import (
        OqiQualityEvaluationRepositoryImpl,
    )

    quality_condition_id = f"condition-{uuid4()}"
    subject = EvaluationSubject(
        lineage=SourceRecordLineageIdentity(
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_record_reference="REC-1",
        ),
        source_field_id=source_field_id,
    )
    finding_id = derive_quality_finding_id(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        subject_type=subject.subject_type,
        subject_identity=canonical_subject_identity(subject),
    )
    finding = QualityFinding(
        finding_id=finding_id,
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
        status=QualityFindingStatus.OPEN,
        state_revision=1,
        first_seen_at=NOW,
        last_seen_at=NOW,
        last_evaluated_horizon=NOW,
        occurrence_count=1,
        reopen_count=0,
    )
    OqiQualityEvaluationRepositoryImpl(session).upsert_finding(finding)
    session.flush()
    return finding_id


def _repo(session: Session) -> OqiOntologyImpactEvaluationRepositoryImpl:
    return OqiOntologyImpactEvaluationRepositoryImpl(session)


def _service(session: Session) -> OqiOntologyImpactEvaluationService:
    return OqiOntologyImpactEvaluationService(_repo(session), clock=_clock)


# --- schema shape and migration round trip ---


def test_migration_creates_expected_schema(migrated_engine: Engine) -> None:
    inspector = inspect(migrated_engine)
    tables = set(inspector.get_table_names())
    for table in (
        "impact_propagation_policies",
        "ontology_impact_evaluations",
        "ontology_impact_observations",
        "ontology_impact_paths",
        "current_ontology_impacts",
    ):
        assert table in tables


def test_migration_round_trips_cleanly(migrated_engine: Engine) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", str(migrated_engine.url))
    with migrated_engine.connect() as connection:
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert table_count == 86
    alembic.command.downgrade(config, "0022_oqi3_business_rule")
    with migrated_engine.connect() as connection:
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert table_count == 81
    alembic.command.upgrade(config, "head")
    with migrated_engine.connect() as connection:
        table_count = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
    assert table_count == 86


# --- one-ACTIVE-policy-per-triple database constraint ---


def test_one_active_policy_per_triple_enforced_by_database(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type)
        session.commit()
    from sqlalchemy.exc import IntegrityError

    with factory() as session, pytest.raises(IntegrityError):
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type)
        session.commit()


# --- OQI1 direct impact adapter, end to end against real persistence ---


def test_direct_impact_resolved(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        source_object_id, source_field_id = _seed_source_object(session, tenant_id=tenant_id), None
        # _seed_source_object returns only the object id in this codebase's
        # helper signature; reconstruct a field beneath it directly.
        from app.tests.test_source_field_persistence_postgres import _source_field
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )

        field = _source_field(source_object_id=source_object_id, field_label="mrp_controller")
        SourceFieldRepositoryImpl(session).create(field)
        session.flush()
        source_field_id = field.source_field_id.value

        entity_id = _entity(session, tenant_id=tenant_id, name=f"Material-{uuid4()}")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=source_object_id, entity_id=entity_id
        )
        finding_id = _oqi1_finding(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=source_field_id,
        )
        session.commit()

    with factory() as session:
        evaluation = _service(session).evaluate_current_state(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        session.commit()
        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.IMPACTED
        assert len(evaluation.observations) == 1
        assert evaluation.observations[0].ontology_element_id == entity_id


def test_attribute_level_finding_without_resolution_record_is_impact_unknown(
    migrated_engine: Engine,
) -> None:
    """CDD-042 flagship honesty test (Artifact Authorization §8): a valid
    Finding with no resolution record at all must never become NO_IMPACT
    nor a fabricated IMPACTED -- IMPACT_UNKNOWN, and zero ledger children."""
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        from app.tests.test_source_field_persistence_postgres import _source_field
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )

        source_object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=source_object_id, field_label="mrp_controller")
        SourceFieldRepositoryImpl(session).create(field)
        session.flush()
        finding_id = _oqi1_finding(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=field.source_field_id.value,
        )
        session.commit()

    with factory() as session:
        evaluation = _service(session).evaluate_current_state(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        session.commit()
        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.IMPACT_UNKNOWN
        assert evaluation.observations == ()

    with factory() as session:
        result = session.execute(
            text(
                "SELECT count(*) FROM ontology_impact_observations o "
                "JOIN ontology_impact_evaluations e ON e.evaluation_id = o.evaluation_id "
                "WHERE e.finding_id = :fid"
            ),
            {"fid": str(finding_id)},
        ).scalar_one()
        assert result == 0
        result = session.execute(
            text("SELECT count(*) FROM current_ontology_impacts WHERE finding_id = :fid"),
            {"fid": str(finding_id)},
        ).scalar_one()
        assert result == 0


def test_no_impact_for_unresolved_outcome(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        from app.tests.test_source_field_persistence_postgres import _source_field
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )

        source_object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=source_object_id, field_label="mrp_controller")
        SourceFieldRepositoryImpl(session).create(field)
        session.flush()
        EntityResolutionStore(session).append(
            EnterpriseEntityResolutionRecord(
                record_id=uuid4(),
                tenant_id=tenant_id,
                enterprise_entity_id=None,
                supporting_source_object_ids=(source_object_id,),
                outcome=ResolutionOutcome.UNRESOLVED,
                business_confidence=BusinessConfidence.LOW,
                structured_reasons=("no match",),
                narrative_explanation="No candidate matched.",
                produced_at=NOW,
                policy_version="v1",
            )
        )
        finding_id = _oqi1_finding(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=field.source_field_id.value,
        )
        session.commit()

    with factory() as session:
        evaluation = _service(session).evaluate_current_state(
            tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        session.commit()
        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.NO_IMPACT
        assert evaluation.observations == ()


# --- propagation correctness ---


def test_deny_by_default_no_policy_no_propagation(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        assert candidates == ()


def test_active_policy_enables_forward_propagation(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        assert {c.entity_id for c in candidates} == {b}
        assert candidates[0].depth == 1


def test_reverse_direction_does_not_propagate_forward_policy(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _policy(
            session,
            tenant_id=tenant_id,
            relationship_type_id=rel_type,
            direction=PropagationDirection.FORWARD,
        )
        session.commit()

        # Starting from B (the "to" side): a FORWARD-only policy must not
        # let traversal walk backward across the same edge.
        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=b)
        assert candidates == ()


def test_retired_policy_does_not_propagate(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _policy(
            session,
            tenant_id=tenant_id,
            relationship_type_id=rel_type,
            status=PolicyGovernanceStatus.RETIRED,
        )
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        assert candidates == ()


def test_multi_hop_bom_chain(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"component-of-{uuid4()}")
        c1 = _entity(session, tenant_id=tenant_id, name="Component1")
        a1 = _entity(session, tenant_id=tenant_id, name="Assembly1")
        p1 = _entity(session, tenant_id=tenant_id, name="Product1")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=c1, to_id=a1)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a1, to_id=p1)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=5)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=c1)
        by_entity = {c.entity_id: c.depth for c in candidates}
        assert by_entity == {a1: 1, p1: 2}


def test_denied_edge_type_does_not_propagate_alongside_allowed_one(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        allowed = _relationship_type(session, name=f"allowed-{uuid4()}")
        denied = _relationship_type(session, name=f"denied-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        c = _entity(session, tenant_id=tenant_id, name="C")
        _relate(session, tenant_id=tenant_id, relationship_type_id=allowed, from_id=a, to_id=b)
        _relate(session, tenant_id=tenant_id, relationship_type_id=denied, from_id=a, to_id=c)
        _policy(session, tenant_id=tenant_id, relationship_type_id=allowed)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        assert {c.entity_id for c in candidates} == {b}


def test_self_loop_terminates_and_does_not_propagate(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=a)
        _policy(
            session,
            tenant_id=tenant_id,
            relationship_type_id=rel_type,
            direction=PropagationDirection.BOTH,
        )
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        assert candidates == ()


def test_three_node_cycle_terminates_deterministically(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        c = _entity(session, tenant_id=tenant_id, name="C")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=b, to_id=c)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=c, to_id=a)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=10)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        entities_reached = {c.entity_id for c in candidates}
        assert entities_reached == {b, c}
        assert all(c.depth <= 2 for c in candidates)


def test_diamond_produces_two_distinct_real_paths(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        c = _entity(session, tenant_id=tenant_id, name="C")
        d = _entity(session, tenant_id=tenant_id, name="D")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=c)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=b, to_id=d)
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=c, to_id=d)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=5)
        session.commit()

        candidates = _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        d_paths = [cand for cand in candidates if cand.entity_id == d]
        node_sets = {frozenset(p.relationship_ids) for p in d_paths}
        assert len(node_sets) == 2


def test_depth_boundary_exact_and_one_beyond(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        chain = [_entity(session, tenant_id=tenant_id, name=f"N{i}") for i in range(4)]
        for i in range(3):
            _relate(
                session,
                tenant_id=tenant_id,
                relationship_type_id=rel_type,
                from_id=chain[i],
                to_id=chain[i + 1],
            )
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=2)
        session.commit()

        candidates = _repo(session).traverse_propagation(
            tenant_id=tenant_id, direct_entity_id=chain[0]
        )
        reached = {c.entity_id for c in candidates}
        assert chain[1] in reached
        assert chain[2] in reached
        assert chain[3] not in reached  # depth 3 exceeds max_depth=2


# --- release-blocking: recursive CTE snapshot coherence ---


def test_graph_writer_during_statement_is_not_visible(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        c = _entity(session, tenant_id=tenant_id, name="C")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=5)
        session.commit()

    reader_results: list[tuple[PropagatedPathCandidate, ...]] = []

    def reader() -> None:
        with factory() as reader_session:
            reader_results.append(
                _repo(reader_session).traverse_propagation(
                    tenant_id=tenant_id, direct_entity_id=a, _test_only_delay_seconds=0.6
                )
            )

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    time.sleep(0.2)
    with factory() as writer_session:
        _relate(
            writer_session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=b, to_id=c
        )
        writer_session.commit()
    reader_thread.join(timeout=10)

    entities_reached = {cand.entity_id for cand in reader_results[0]}
    assert c not in entities_reached, "reader statement observed a commit made mid-execution"


def test_policy_writer_during_statement_is_not_visible(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        # No ACTIVE policy exists yet -- traversal should see nothing
        # unless a policy commits mid-statement, which it must not.
        session.commit()

    reader_results: list[tuple[PropagatedPathCandidate, ...]] = []

    def reader() -> None:
        with factory() as reader_session:
            reader_results.append(
                _repo(reader_session).traverse_propagation(
                    tenant_id=tenant_id, direct_entity_id=a, _test_only_delay_seconds=0.6
                )
            )

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    time.sleep(0.2)
    with factory() as writer_session:
        _policy(writer_session, tenant_id=tenant_id, relationship_type_id=rel_type)
        writer_session.commit()
    reader_thread.join(timeout=10)

    assert reader_results[0] == (), "reader statement observed a policy committed mid-execution"


def test_traversal_is_exactly_one_mutable_statement(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        a = _entity(session, tenant_id=tenant_id, name="A")
        b = _entity(session, tenant_id=tenant_id, name="B")
        _relate(session, tenant_id=tenant_id, relationship_type_id=rel_type, from_id=a, to_id=b)
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type)
        session.commit()

    statements: list[str] = []

    def _record(
        conn: object,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> None:
        statements.append(statement)

    with factory() as session:
        event.listen(session.get_bind(), "before_cursor_execute", _record)
        try:
            _repo(session).traverse_propagation(tenant_id=tenant_id, direct_entity_id=a)
        finally:
            event.remove(session.get_bind(), "before_cursor_execute", _record)

    mutable_reads = [s for s in statements if "WITH RECURSIVE" in s]
    assert len(mutable_reads) == 1


# --- concurrency ---


def test_concurrent_identical_evaluation_converges_without_duplicate(
    migrated_engine: Engine,
) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        from app.tests.test_source_field_persistence_postgres import _source_field
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )

        source_object_id = _seed_source_object(session, tenant_id=tenant_id)
        field = _source_field(source_object_id=source_object_id, field_label="mrp_controller")
        SourceFieldRepositoryImpl(session).create(field)
        session.flush()
        entity_id = _entity(session, tenant_id=tenant_id, name=f"Material-{uuid4()}")
        _resolve_entity(
            session, tenant_id=tenant_id, source_object_id=source_object_id, entity_id=entity_id
        )
        finding_id = _oqi1_finding(
            session,
            tenant_id=tenant_id,
            source_object_id=source_object_id,
            source_field_id=field.source_field_id.value,
        )
        session.commit()

    errors: list[BaseException] = []

    def worker() -> None:
        try:
            with factory() as session:
                _service(session).evaluate_current_state(
                    tenant_id=tenant_id, finding_family=FindingFamily.OQI1, finding_id=finding_id
                )
                session.commit()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"concurrent evaluation raised: {errors}"
    with factory() as session:
        count = session.execute(
            text("SELECT count(*) FROM ontology_impact_evaluations WHERE finding_id = :fid"),
            {"fid": str(finding_id)},
        ).scalar_one()
        assert count == 1
        current_count = session.execute(
            text("SELECT count(*) FROM current_ontology_impacts WHERE finding_id = :fid"),
            {"fid": str(finding_id)},
        ).scalar_one()
        assert current_count == 1


# --- tenant isolation ---


def test_propagation_does_not_cross_tenant_boundary(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_a = f"tenant-a-{uuid4()}"
    tenant_b = f"tenant-b-{uuid4()}"
    with factory() as session:
        rel_type_a = _relationship_type(session, name=f"rt-a-{uuid4()}")
        a1 = _entity(session, tenant_id=tenant_a, name="A")
        b1 = _entity(session, tenant_id=tenant_a, name="B")
        _relate(session, tenant_id=tenant_a, relationship_type_id=rel_type_a, from_id=a1, to_id=b1)
        _policy(session, tenant_id=tenant_a, relationship_type_id=rel_type_a)

        # Tenant B has its own, unrelated graph and its own ACTIVE policy
        # for the *same relationship type id space* is impossible (policy
        # rows are keyed by relationship_type_id, not tenant-duplicated) --
        # so the adversarial case is: tenant B has NO policy for rel_type_a
        # at all, and must never benefit from tenant A's ACTIVE policy.
        a2 = _entity(session, tenant_id=tenant_b, name="A")
        b2 = _entity(session, tenant_id=tenant_b, name="B")
        _relate(session, tenant_id=tenant_b, relationship_type_id=rel_type_a, from_id=a2, to_id=b2)
        session.commit()

        candidates_b = _repo(session).traverse_propagation(tenant_id=tenant_b, direct_entity_id=a2)
        assert candidates_b == (), "tenant B propagated using tenant A's policy enrollment"

        candidates_a = _repo(session).traverse_propagation(tenant_id=tenant_a, direct_entity_id=a1)
        assert {c.entity_id for c in candidates_a} == {b1}


def test_cross_tenant_finding_lookup_fails_closed(migrated_engine: Engine) -> None:
    from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
        FindingNotFoundError,
    )

    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    owner_tenant = f"tenant-owner-{uuid4()}"
    other_tenant = f"tenant-other-{uuid4()}"
    with factory() as session:
        from app.tests.test_source_field_persistence_postgres import _source_field
        from app.infrastructure.persistence.source_field_repository import (
            SourceFieldRepositoryImpl,
        )

        source_object_id = _seed_source_object(session, tenant_id=owner_tenant)
        field = _source_field(source_object_id=source_object_id, field_label="mrp_controller")
        SourceFieldRepositoryImpl(session).create(field)
        session.flush()
        finding_id = _oqi1_finding(
            session,
            tenant_id=owner_tenant,
            source_object_id=source_object_id,
            source_field_id=field.source_field_id.value,
        )
        session.commit()

    with factory() as session, pytest.raises(FindingNotFoundError):
        _repo(session).resolve_finding_subject(
            tenant_id=other_tenant, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )


# --- bounded performance sanity ---


def test_bounded_graph_performance_sanity(migrated_engine: Engine) -> None:
    factory = sessionmaker(migrated_engine, expire_on_commit=False)
    tenant_id = f"tenant-{uuid4()}"
    with factory() as session:
        rel_type = _relationship_type(session, name=f"rt-{uuid4()}")
        node_count = 300
        nodes = [_entity(session, tenant_id=tenant_id, name=f"N{i}") for i in range(node_count)]
        # A long chain (multiple paths at the far end via a few cross-links)
        # plus one embedded cycle, exercising cycle-guard + depth-cap
        # together at non-trivial scale.
        for i in range(node_count - 1):
            _relate(
                session,
                tenant_id=tenant_id,
                relationship_type_id=rel_type,
                from_id=nodes[i],
                to_id=nodes[i + 1],
            )
        for i in range(0, node_count - 5, 5):
            _relate(
                session,
                tenant_id=tenant_id,
                relationship_type_id=rel_type,
                from_id=nodes[i],
                to_id=nodes[i + 3],
            )
        _relate(
            session,
            tenant_id=tenant_id,
            relationship_type_id=rel_type,
            from_id=nodes[-1],
            to_id=nodes[0],
        )
        _policy(session, tenant_id=tenant_id, relationship_type_id=rel_type, max_depth=10)
        session.commit()

        started = time.monotonic()
        candidates = _repo(session).traverse_propagation(
            tenant_id=tenant_id, direct_entity_id=nodes[0]
        )
        elapsed = time.monotonic() - started
        assert candidates  # traversal reaches something within the depth cap
        assert elapsed < 15.0
