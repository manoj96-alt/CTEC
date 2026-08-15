"""PostgreSQL-backed concurrency proof for the Entity Resolution Steward
decision path (Increment 3A Gate C). Two independent sessions (real OS
threads, each with its own DB connection) attempt a decision against the
same case using the same based_on_record_id at the same time. The row lock
inside EntityResolutionStore.append_decision() (SELECT ... FOR UPDATE) must
make this race-free: exactly one succeeds, the other observes the
now-advanced current_record_identifier and raises StaleResolutionCaseError
before appending anything.
"""

import threading
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.bootstrap import BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.identity_resolution.evidence import SourceRepresentation
from app.domain.identity_resolution.model import EvidenceProfile, StewardDecisionAction
from app.domain.identity_resolution.policy import conservative_preset
from app.domain.identity_resolution.service import EvidenceResolutionEngine
from app.infrastructure.persistence.entity_resolution_store import (
    EntityResolutionStore,
    StaleResolutionCaseError,
)
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.resolution_policy_store import ResolutionPolicyStore

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def test_two_concurrent_decisions_on_the_same_based_on_record_id_exactly_one_succeeds(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-concurrency")
    with Session(migrated_engine) as session, session.begin():
        system_id = uuid4()
        session.add(
            SourceSystem(
                source_system_id=system_id,
                tenant_id=tenant_id,
                source_system_name=f"sys-{uuid4()}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
            )
        )
        session.flush()
        source_id = uuid4()
        session.add(
            SourceObject(
                source_object_id=source_id,
                tenant_id=tenant_id,
                source_object_name=f"obj-{uuid4()}",
                lifecycle_state="Active",
                effective_from=NOW,
                governance_status="Approved",
                created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
                created_on=NOW,
                source_system_id=system_id,
            )
        )
        session.flush()

        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
        rep = SourceRepresentation(
            source_object_id=source_id,
            source_system_name="CRM",
            display_name="Totally Unrelated Corp",
        )
        initial_record = engine.resolve(
            tenant_id=tenant_id,
            supporting_source_object_ids=(source_id,),
            representations=(rep,),
            candidate_name=CANDIDATE_NAME,
            candidate_enterprise_entity_id=None,
            produced_at=NOW,
        )
        EntityResolutionStore(session).append(initial_record)

    understanding_key = EntityResolutionStore.understanding_key((source_id,))
    based_on_record_id = initial_record.record_id
    policy_definition = policy

    results: dict[str, str] = {}
    barrier = threading.Barrier(2)

    def attempt(label: str) -> None:
        try:
            barrier.wait(timeout=10)
            with Session(migrated_engine) as session, session.begin():
                store = EntityResolutionStore(session)
                current = store.get_current_record(tenant_id, understanding_key)
                assert current is not None
                assert current.evidence_profile is not None
                profile = EvidenceProfile.from_record(current.evidence_profile)
                decision_engine = EvidenceResolutionEngine(policy_definition, policy_id=policy_id)
                new_record = decision_engine.decide_steward_action(
                    tenant_id=tenant_id,
                    supporting_source_object_ids=(source_id,),
                    evidence_profile=profile,
                    current_enterprise_entity_id=current.enterprise_entity_id,
                    action=StewardDecisionAction.MARK_UNRESOLVED,
                    actor_id=f"steward-{label}",
                    decision_rationale=f"Concurrent attempt {label}.",
                    produced_at=NOW,
                )
                store.append_decision(
                    new_record,
                    understanding_key=understanding_key,
                    based_on_record_id=based_on_record_id,
                )
            results[label] = "success"
        except StaleResolutionCaseError:
            results[label] = "stale"
        # Thread target: must not let an exception vanish silently -- record it
        # for the assertion below instead of letting the thread die quietly.
        except Exception as exc:  # noqa: BLE001
            results[label] = f"error: {exc!r}"

    thread_a = threading.Thread(target=attempt, args=("a",))
    thread_b = threading.Thread(target=attempt, args=("b",))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=30)
    thread_b.join(timeout=30)

    assert sorted(results.values()) == ["stale", "success"]

    with Session(migrated_engine) as session:
        history = EntityResolutionStore(session).get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier != based_on_record_id
        assert history.historical_record_references == [str(based_on_record_id)]
        record_ids = session.scalars(
            select(EnterpriseEntityResolutionRecordModel.record_id).where(
                EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id
            )
        ).all()
        # Exactly two records exist for this case: the original plus the
        # single winning decision. The losing attempt appended nothing.
        assert len(record_ids) == 2
