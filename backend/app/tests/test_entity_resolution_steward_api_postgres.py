"""Focused PostgreSQL-backed proof of the Entity Resolution Steward
application service (Increment 3A Gate C): tenant-scoped reads, explicit
(never silent) handling of missing source provenance, deterministic
source-representation ordering, immutable successor-record append with
history-pointer movement, stale-decision rejection before any append,
confirm_match's veto guard enforced through real persisted data, preview's
non-persistence, and the fingerprint-only guarantee for sensitive evidence.

Every tenant id is generated fresh per test (never a literal) because
`migrated_engine` is a session-scoped fixture shared across the whole test
session.
"""

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.api.entity_resolution.schemas import DecisionRequest
from app.api.supplier_risk.authentication import TrustedPrincipal
from app.application.entity_resolution_steward_api import (
    CaseNotFoundError,
    EntityResolutionStewardApiService,
    IncompleteSourceProvenanceError,
    PolicyNotFoundError,
)
from app.core.bootstrap import (
    BOOTSTRAP_BUSINESS_DOMAIN_ID,
    BOOTSTRAP_ENTITY_TYPE_ID,
    BOOTSTRAP_SYSTEM_ENTITY_ID,
)
from app.domain.identity_resolution.evidence import SourceRepresentation
from app.domain.identity_resolution.model import EvidenceType
from app.domain.identity_resolution.policy import ResolutionPolicyDefinition, conservative_preset
from app.domain.identity_resolution.service import (
    EvidenceResolutionEngine,
    OverrideNotPermittedError,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.entity_resolution_store import (
    EntityResolutionStore,
    StaleResolutionCaseError,
)
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.source_object import SourceObject
from app.infrastructure.persistence.models.source_system import SourceSystem
from app.infrastructure.persistence.resolution_policy_store import ResolutionPolicyStore

NOW = datetime(2026, 1, 1, tzinfo=UTC)
CANDIDATE_NAME = "Taiwan Semiconductor Manufacturing Company Limited"
RAW_TAX_ID = "SECRET-TAX-ID-24894001"


def _tenant(label: str) -> str:
    return f"{label}-{uuid4()}"


def _principal(tenant_id: str, principal_id: str = "steward-jane") -> TrustedPrincipal:
    return TrustedPrincipal(
        principal_id=principal_id,
        tenant_id=tenant_id,
        scopes=("entity-resolution:read", "entity-resolution:decide"),
        roles=("steward",),
        issuer="issuer",
        issued_at=NOW - timedelta(seconds=1),
        expires_at=NOW + timedelta(hours=1),
    )


def _seed_enterprise_entity(session: Session, *, tenant_id: str, name: str) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            entity_type_id=BOOTSTRAP_ENTITY_TYPE_ID,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _seed_source_system(session: Session, *, tenant_id: str, name: str) -> UUID:
    system_id = uuid4()
    session.add(
        SourceSystem(
            source_system_id=system_id,
            tenant_id=tenant_id,
            source_system_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
        )
    )
    session.flush()
    return system_id


def _seed_source_object(
    session: Session, *, tenant_id: str, source_system_id: UUID, name: str
) -> UUID:
    object_id = uuid4()
    session.add(
        SourceObject(
            source_object_id=object_id,
            tenant_id=tenant_id,
            source_object_name=name,
            lifecycle_state="Active",
            effective_from=NOW,
            governance_status="Approved",
            created_by=BOOTSTRAP_SYSTEM_ENTITY_ID,
            created_on=NOW,
            source_system_id=source_system_id,
        )
    )
    session.flush()
    return object_id


def _service(migrated_engine: Engine) -> EntityResolutionStewardApiService:
    return EntityResolutionStewardApiService(sessionmaker(migrated_engine))


def _seed_case(
    session: Session,
    *,
    tenant_id: str,
    policy_id: UUID,
    policy: ResolutionPolicyDefinition,
    source_object_ids: tuple[UUID, ...],
    with_conflicting_tax_id: bool = False,
    with_matching_tax_id: bool = False,
) -> tuple[str, UUID]:
    """Builds and appends one Gate B evidence-bearing resolution record.
    Returns (understanding_key, record_id)."""
    count = len(source_object_ids)
    if with_conflicting_tax_id:
        tax_ids: tuple[str, ...] = tuple(
            RAW_TAX_ID if i == 0 else f"{RAW_TAX_ID}-CONFLICT" for i in range(count)
        )
    elif with_matching_tax_id:
        tax_ids = tuple(RAW_TAX_ID for _ in range(count))
    else:
        tax_ids = ()

    def _strong_identifiers(index: int) -> tuple[tuple[EvidenceType, str], ...]:
        if index >= len(tax_ids):
            return ()
        return ((EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION, tax_ids[index]),)

    reps = tuple(
        SourceRepresentation(
            source_object_id=source_object_ids[i],
            source_system_name=f"system-{i}-{uuid4()}",
            display_name=CANDIDATE_NAME,
            website_domain="tsmc.com",
            country="Taiwan",
            strong_identifiers=_strong_identifiers(i),
        )
        for i in range(len(source_object_ids))
    )
    entity_id = _seed_enterprise_entity(session, tenant_id=tenant_id, name=f"Entity-{uuid4()}")
    engine = EvidenceResolutionEngine(policy, policy_id=policy_id)
    record = engine.resolve(
        tenant_id=tenant_id,
        supporting_source_object_ids=source_object_ids,
        representations=reps,
        candidate_name=CANDIDATE_NAME,
        candidate_enterprise_entity_id=entity_id,
        produced_at=NOW,
        candidate_country="Taiwan",
    )
    EntityResolutionStore(session).append(record)
    understanding_key = EntityResolutionStore.understanding_key(source_object_ids)
    return understanding_key, record.record_id


# ---------------------------------------------------------------------------
# Tenant-scoped reads / non-disclosure
# ---------------------------------------------------------------------------


def test_list_cases_excludes_another_tenants_cases(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_b, policy, preset_kind="Conservative"
        )
        system_id = _seed_source_system(session, tenant_id=tenant_b, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_b, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        _seed_case(
            session,
            tenant_id=tenant_b,
            policy_id=policy_row.policy_id,
            policy=policy,
            source_object_ids=(source_id,),
        )

    service = _service(migrated_engine)
    result = service.list_cases(_principal(tenant_a))
    assert result.items == []


def test_get_case_returns_none_for_another_tenants_understanding_key(
    migrated_engine: Engine,
) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_b, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_b, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_b, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, _record_id = _seed_case(
            session,
            tenant_id=tenant_b,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_id,),
        )

    service = _service(migrated_engine)
    assert service.get_case(_principal(tenant_a), understanding_key) is None
    # Sanity: tenant B itself can still see its own case.
    own = service.get_case(_principal(tenant_b), understanding_key)
    assert own is not None


def test_preview_rejects_a_policy_id_owned_by_another_tenant(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row_a = ResolutionPolicyStore(session).materialize(
            tenant_a, policy, preset_kind="Conservative"
        )
        policy_id_a = policy_row_a.policy_id
        policy_row_b = ResolutionPolicyStore(session).materialize(
            tenant_b, policy, preset_kind="Conservative"
        )
        policy_id_b = policy_row_b.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_a, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_a, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, _ = _seed_case(
            session,
            tenant_id=tenant_a,
            policy_id=policy_id_a,
            policy=policy,
            source_object_ids=(source_id,),
        )

    service = _service(migrated_engine)
    with pytest.raises(PolicyNotFoundError):
        service.preview(_principal(tenant_a), understanding_key, policy_id_b)


def test_decide_rejects_a_policy_id_owned_by_another_tenant(migrated_engine: Engine) -> None:
    tenant_a, tenant_b = _tenant("tenant-a"), _tenant("tenant-b")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row_a = ResolutionPolicyStore(session).materialize(
            tenant_a, policy, preset_kind="Conservative"
        )
        policy_id_a = policy_row_a.policy_id
        policy_row_b = ResolutionPolicyStore(session).materialize(
            tenant_b, policy, preset_kind="Conservative"
        )
        policy_id_b = policy_row_b.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_a, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_a, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, record_id = _seed_case(
            session,
            tenant_id=tenant_a,
            policy_id=policy_id_a,
            policy=policy,
            source_object_ids=(source_id,),
        )

    service = _service(migrated_engine)
    with pytest.raises(PolicyNotFoundError):
        service.decide_case(
            _principal(tenant_a),
            understanding_key,
            DecisionRequest(
                action="mark_unresolved",
                rationale="attempting cross-tenant policy",
                based_on_record_id=record_id,
                policy_id=policy_id_b,
            ),
        )


def test_decide_on_an_unknown_case_raises_case_not_found(migrated_engine: Engine) -> None:
    tenant_a = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_a, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id

    service = _service(migrated_engine)
    with pytest.raises(CaseNotFoundError):
        service.decide_case(
            _principal(tenant_a),
            "not-a-real-understanding-key",
            DecisionRequest(
                action="mark_unresolved",
                rationale="no such case",
                based_on_record_id=uuid4(),
                policy_id=policy_id,
            ),
        )


# ---------------------------------------------------------------------------
# Source representations: explicit failure, deterministic ordering
# ---------------------------------------------------------------------------


def test_source_representations_are_deterministically_ordered(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        # Seed in one order, but store the record's supporting_source_object_ids
        # in a deliberately different (reversed) order.
        first = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-A-{uuid4()}"
        )
        second = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-B-{uuid4()}"
        )
        third = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-C-{uuid4()}"
        )
        reversed_order = (third, first, second)
        understanding_key, _ = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_row.policy_id,
            policy=policy,
            source_object_ids=reversed_order,
        )

    service = _service(migrated_engine)
    detail_first = service.get_case(_principal(tenant_id), understanding_key)
    detail_second = service.get_case(_principal(tenant_id), understanding_key)
    assert detail_first is not None and detail_second is not None
    observed_order = tuple(r.source_object_id for r in detail_first.source_representations)
    assert observed_order == reversed_order
    # Deterministic across repeated reads.
    assert observed_order == tuple(r.source_object_id for r in detail_second.source_representations)


def test_missing_source_object_fails_explicitly_not_silently(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, _ = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_row.policy_id,
            policy=policy,
            source_object_ids=(source_id,),
        )

    # Simulate out-of-band data loss: supporting_source_object_ids is a JSON
    # array (see entity_resolution_store.py), not a foreign key, so deleting
    # the SourceObject row afterward is possible and must be handled
    # explicitly, not silently, by the read path.
    with Session(migrated_engine) as session, session.begin():
        session.execute(delete(SourceObject).where(SourceObject.source_object_id == source_id))

    service = _service(migrated_engine)
    with pytest.raises(IncompleteSourceProvenanceError):
        service.get_case(_principal(tenant_id), understanding_key)


def test_source_system_referenced_by_a_source_object_cannot_be_deleted(
    migrated_engine: Engine,
) -> None:
    """Proves fk_source_objects_tenant_source_system actually protects the
    database at the schema level: a SourceSystem referenced by a
    SourceObject can never be deleted through an ordinary statement. This
    is what makes the "missing SourceSystem" state the application-service
    guard defends against (see
    test_entity_resolution_steward_provenance_guard.py, a pure unit test
    against an isolated in-memory database) structurally unreachable during
    real operation -- so that guard is intentionally never exercised
    against this shared PostgreSQL database.

    Because the DELETE is expected to fail and roll back, this test leaves
    the seeded SourceSystem and SourceObject rows fully valid and linked --
    no cleanup is required, and the shared database is left exactly as
    consistent as it was before the test ran.
    """
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-{uuid4()}"
        )

    with pytest.raises(IntegrityError), Session(migrated_engine) as session, session.begin():
        session.execute(delete(SourceSystem).where(SourceSystem.source_system_id == system_id))

    with Session(migrated_engine) as session:
        # The failed DELETE rolled back: both rows are exactly as seeded.
        assert session.get(SourceSystem, system_id) is not None


# ---------------------------------------------------------------------------
# Immutable append + history-pointer movement
# ---------------------------------------------------------------------------


def test_decision_appends_an_immutable_successor_and_moves_the_history_pointer(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, original_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_id,),
        )

    with Session(migrated_engine) as session:
        original_snapshot = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original_snapshot is not None
        original_outcome = original_snapshot.outcome

    service = _service(migrated_engine)
    result = service.decide_case(
        _principal(tenant_id),
        understanding_key,
        DecisionRequest(
            action="mark_unresolved",
            rationale="Deferring for further investigation.",
            based_on_record_id=original_record_id,
            policy_id=policy_id,
        ),
    )

    assert result.record_id != original_record_id

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == result.record_id
        assert str(original_record_id) in history.historical_record_references

        # The original record is untouched -- immutable.
        original_after = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original_after is not None
        assert original_after.outcome == original_outcome

        new_row = session.get(EnterpriseEntityResolutionRecordModel, result.record_id)
        assert new_row is not None
        assert new_row.outcome == "Unresolved"
        assert new_row.actor_id == "steward-jane"


def test_stale_decision_is_rejected_and_appends_no_record(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, real_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_id,),
        )

    with Session(migrated_engine) as session:
        records_before = session.scalars(
            select(EnterpriseEntityResolutionRecordModel.record_id).where(
                EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id
            )
        ).all()

    service = _service(migrated_engine)
    wrong_based_on = uuid4()
    with pytest.raises(StaleResolutionCaseError):
        service.decide_case(
            _principal(tenant_id),
            understanding_key,
            DecisionRequest(
                action="mark_unresolved",
                rationale="Stale attempt.",
                based_on_record_id=wrong_based_on,
                policy_id=policy_id,
            ),
        )

    with Session(migrated_engine) as session:
        records_after = session.scalars(
            select(EnterpriseEntityResolutionRecordModel.record_id).where(
                EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id
            )
        ).all()
        history = EntityResolutionStore(session).get_history(tenant_id, understanding_key)

    assert set(records_after) == set(records_before)
    assert history is not None
    assert history.current_record_identifier == real_record_id
    assert history.historical_record_references == []


# ---------------------------------------------------------------------------
# confirm_match cannot bypass persisted veto evidence (end-to-end)
# ---------------------------------------------------------------------------


def test_confirm_match_cannot_bypass_persisted_veto_evidence(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
            with_conflicting_tax_id=True,
        )

    with Session(migrated_engine) as session:
        row = session.get(EnterpriseEntityResolutionRecordModel, record_id)
        assert row is not None
        assert row.outcome == "Blocked Conflict"

    service = _service(migrated_engine)
    with pytest.raises(OverrideNotPermittedError):
        service.decide_case(
            _principal(tenant_id),
            understanding_key,
            DecisionRequest(
                action="confirm_match",
                rationale="Trying to force a resolution despite the conflict.",
                based_on_record_id=record_id,
                policy_id=policy_id,
            ),
        )

    with Session(migrated_engine) as session:
        history = EntityResolutionStore(session).get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == record_id
        assert history.historical_record_references == []


# ---------------------------------------------------------------------------
# preview() never persists
# ---------------------------------------------------------------------------


def test_preview_never_appends_or_mutates_anything(migrated_engine: Engine) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        conservative = conservative_preset()
        conservative_row = ResolutionPolicyStore(session).materialize(
            tenant_id, conservative, preset_kind="Conservative"
        )
        conservative_policy_id = conservative_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_id = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-{uuid4()}"
        )
        understanding_key, record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=conservative_policy_id,
            policy=conservative,
            source_object_ids=(source_id,),
        )

    service = _service(migrated_engine)
    # Preview against the same policy repeatedly.
    for _ in range(3):
        service.preview(_principal(tenant_id), understanding_key, conservative_policy_id)

    with Session(migrated_engine) as session:
        history = EntityResolutionStore(session).get_history(tenant_id, understanding_key)
        record_count = len(
            session.scalars(
                select(EnterpriseEntityResolutionRecordModel.record_id).where(
                    EnterpriseEntityResolutionRecordModel.tenant_id == tenant_id
                )
            ).all()
        )

    assert history is not None
    assert history.current_record_identifier == record_id
    assert history.historical_record_references == []
    assert record_count == 1


# ---------------------------------------------------------------------------
# Sensitive identifiers never appear raw
# ---------------------------------------------------------------------------


def test_raw_sensitive_identifier_never_appears_in_persisted_row_or_api_projection(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_row.policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
            with_matching_tax_id=True,
        )

    with Session(migrated_engine) as session:
        row = session.get(EnterpriseEntityResolutionRecordModel, record_id)
        assert row is not None
        raw_column_text = json.dumps(row.evidence_profile)
        assert RAW_TAX_ID not in raw_column_text

    service = _service(migrated_engine)
    detail = service.get_case(_principal(tenant_id), understanding_key)
    assert detail is not None
    assert RAW_TAX_ID not in detail.model_dump_json()


# ---------------------------------------------------------------------------
# reject_match / mark_unresolved / block_conflict through the service
# ---------------------------------------------------------------------------


def test_reject_match_through_the_service_clears_the_candidate_and_stays_available_for_review(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, original_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
        )

    with Session(migrated_engine) as session:
        original = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original is not None
        # No strong identifier -> natural decide() is Possible, not Blocked.
        assert original.outcome == "Possible Resolution"
        assert original.enterprise_entity_id is not None

    service = _service(migrated_engine)
    result = service.decide_case(
        _principal(tenant_id),
        understanding_key,
        DecisionRequest(
            action="reject_match",
            rationale="This candidate is a different legal entity.",
            based_on_record_id=original_record_id,
            policy_id=policy_id,
        ),
    )

    assert result.record_id != original_record_id
    assert result.outcome in ("Possible Resolution", "Unresolved")

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == result.record_id
        assert str(original_record_id) in history.historical_record_references

        original_after = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original_after is not None
        assert original_after.outcome == "Possible Resolution"  # immutable

        new_row = session.get(EnterpriseEntityResolutionRecordModel, result.record_id)
        assert new_row is not None
        assert new_row.enterprise_entity_id is None
        assert new_row.actor_id == "steward-jane"
        assert new_row.decision_rationale == "This candidate is a different legal entity."


def test_mark_unresolved_through_the_service_overrides_a_would_be_resolved_case(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, original_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
            with_matching_tax_id=True,
        )

    with Session(migrated_engine) as session:
        original = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original is not None
        assert original.outcome == "Resolved"

    service = _service(migrated_engine)
    result = service.decide_case(
        _principal(tenant_id),
        understanding_key,
        DecisionRequest(
            action="mark_unresolved",
            rationale="Steward wants a second opinion before resolving.",
            based_on_record_id=original_record_id,
            policy_id=policy_id,
        ),
    )

    assert result.outcome == "Unresolved"

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == result.record_id
        assert str(original_record_id) in history.historical_record_references

        original_after = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original_after is not None
        assert original_after.outcome == "Resolved"  # immutable, unaffected

        new_row = session.get(EnterpriseEntityResolutionRecordModel, result.record_id)
        assert new_row is not None
        assert new_row.enterprise_entity_id is None
        assert new_row.actor_id == "steward-jane"
        assert new_row.decision_rationale == "Steward wants a second opinion before resolving."


def test_block_conflict_through_the_service_succeeds_when_veto_evidence_is_persisted(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, original_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
            with_conflicting_tax_id=True,
        )

    with Session(migrated_engine) as session:
        original = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original is not None
        assert original.outcome == "Blocked Conflict"
        assert original.actor_id is None  # produced by the automatic engine, not a steward

    service = _service(migrated_engine)
    result = service.decide_case(
        _principal(tenant_id),
        understanding_key,
        DecisionRequest(
            action="block_conflict",
            rationale="Confirmed conflicting tax registration numbers with source teams.",
            based_on_record_id=original_record_id,
            policy_id=policy_id,
        ),
    )

    assert result.outcome == "Blocked Conflict"
    assert result.record_id != original_record_id
    assert result.structured_reasons

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        assert history.current_record_identifier == result.record_id
        assert str(original_record_id) in history.historical_record_references

        original_after = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original_after is not None
        assert original_after.outcome == "Blocked Conflict"  # immutable

        new_row = session.get(EnterpriseEntityResolutionRecordModel, result.record_id)
        assert new_row is not None
        assert new_row.enterprise_entity_id is None
        assert new_row.actor_id == "steward-jane"
        assert (
            new_row.decision_rationale
            == "Confirmed conflicting tax registration numbers with source teams."
        )


def test_block_conflict_through_the_service_is_rejected_without_persisted_veto_evidence(
    migrated_engine: Engine,
) -> None:
    tenant_id = _tenant("tenant-a")
    with Session(migrated_engine) as session, session.begin():
        policy = conservative_preset()
        policy_row = ResolutionPolicyStore(session).materialize(
            tenant_id, policy, preset_kind="Conservative"
        )
        policy_id = policy_row.policy_id
        system_id = _seed_source_system(session, tenant_id=tenant_id, name=f"sys-{uuid4()}")
        source_a = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-a-{uuid4()}"
        )
        source_b = _seed_source_object(
            session, tenant_id=tenant_id, source_system_id=system_id, name=f"obj-b-{uuid4()}"
        )
        understanding_key, original_record_id = _seed_case(
            session,
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy=policy,
            source_object_ids=(source_a, source_b),
        )

    with Session(migrated_engine) as session:
        original = session.get(EnterpriseEntityResolutionRecordModel, original_record_id)
        assert original is not None
        assert original.outcome != "Blocked Conflict"

    service = _service(migrated_engine)
    with pytest.raises(ValidationException):
        service.decide_case(
            _principal(tenant_id),
            understanding_key,
            DecisionRequest(
                action="block_conflict",
                rationale="Trying to block a case with no real conflict.",
                based_on_record_id=original_record_id,
                policy_id=policy_id,
            ),
        )

    with Session(migrated_engine) as session:
        store = EntityResolutionStore(session)
        history = store.get_history(tenant_id, understanding_key)
        assert history is not None
        # Nothing was appended: history still points at the original record.
        assert history.current_record_identifier == original_record_id
        assert history.historical_record_references == []
