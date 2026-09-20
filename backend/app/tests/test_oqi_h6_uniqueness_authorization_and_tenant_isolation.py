"""CDD-084 OQI-H6 Governed EnterpriseEntity Uniqueness -- Artifact
Authorization row 12: real-PostgreSQL adversarial tenant-isolation proof
for every composite tenant-qualified FK introduced by H6 (AA §9, nine
total), plus the canonical-pair CHECK constraint's own adversarial proof
(AA §7.3/§7.5). Mirrors `test_oqi_h5_timeliness_authorization_and_tenant_
isolation.py`'s exact structure: direct `session.add()`+`flush()` insertion
that deliberately bypasses the service layer, proving PostgreSQL itself
(not application code) rejects every cross-tenant reference and every
non-canonical pair. Positive same-tenant, canonical-pair controls prove the
legitimate path still works."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.models.oqi_uniqueness import (
    UniquenessAdjudicationORM,
    UniquenessCandidateORM,
    UniquenessEvaluationORM,
    UniquenessFindingORM,
    UniquenessPolicyORM,
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


def _entity_type_id(session: Session, name: str = "Product") -> UUID:
    OntologySeeder(session).load()
    session.commit()
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


def _entity(session: Session, *, tenant_id: str, type_id: UUID) -> UUID:
    entity_id = uuid4()
    session.add(
        EnterpriseEntity(
            enterprise_entity_id=entity_id,
            tenant_id=tenant_id,
            enterprise_entity_name=f"TI Entity {entity_id}",
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


def _policy(session: Session, *, tenant_id: str, entity_type_id: UUID) -> tuple[UUID, int]:
    policy_id = uuid4()
    session.add(
        UniquenessPolicyORM(
            policy_id=policy_id,
            version=1,
            tenant_id=tenant_id,
            entity_type_id=entity_type_id,
            bucket_max_size=10,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    session.flush()
    return policy_id, 1


def _candidate(
    session: Session,
    *,
    tenant_id: str,
    member_a_id: UUID,
    member_b_id: UUID,
    policy_id: UUID,
    policy_version: int,
) -> UUID:
    candidate_id = uuid4()
    session.add(
        UniquenessCandidateORM(
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            member_a_id=member_a_id,
            member_b_id=member_b_id,
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    session.flush()
    return candidate_id


# =====================================================================
# TI-01/02: UniquenessEvaluation -> EnterpriseEntity.
# =====================================================================


def test_ti01_same_tenant_evaluation_to_entity_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_id = _entity(session, tenant_id=tenant_id, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    session.add(
        UniquenessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
            enterprise_entity_id=entity_id,
            outcome="SATISFIED",
            not_evaluable_reason=None,
            candidate_count=0,
            evaluated_on=NOW,
        )
    )
    session.flush()  # no raise


def test_ti02_cross_tenant_evaluation_to_entity_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_b = _entity(session, tenant_id=tenant_b, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_a, entity_type_id=type_id)
    session.add(
        UniquenessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_a,  # claims tenant A
            policy_id=policy_id,
            policy_version=policy_version,
            enterprise_entity_id=entity_b,  # but points at tenant B's entity
            outcome="SATISFIED",
            not_evaluable_reason=None,
            candidate_count=0,
            evaluated_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-03/04: UniquenessEvaluation -> UniquenessPolicy.
# =====================================================================


def test_ti03_same_tenant_evaluation_to_policy_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_id = _entity(session, tenant_id=tenant_id, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    session.add(
        UniquenessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_id,
            policy_id=policy_id,
            policy_version=policy_version,
            enterprise_entity_id=entity_id,
            outcome="SATISFIED",
            not_evaluable_reason=None,
            candidate_count=0,
            evaluated_on=NOW,
        )
    )
    session.flush()  # no raise


def test_ti04_cross_tenant_evaluation_to_policy_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_a = _entity(session, tenant_id=tenant_a, type_id=type_id)
    policy_id_b, policy_version_b = _policy(session, tenant_id=tenant_b, entity_type_id=type_id)
    session.add(
        UniquenessEvaluationORM(
            evaluation_id=uuid4(),
            tenant_id=tenant_a,
            policy_id=policy_id_b,  # tenant B's policy
            policy_version=policy_version_b,
            enterprise_entity_id=entity_a,
            outcome="SATISFIED",
            not_evaluable_reason=None,
            candidate_count=0,
            evaluated_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-05/06: UniquenessCandidate -> EnterpriseEntity (member_a).
# =====================================================================


def test_ti05_same_tenant_candidate_member_a_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )  # no raise


def test_ti06_cross_tenant_candidate_member_a_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_from_b = _entity(session, tenant_id=tenant_b, type_id=type_id)
    entity_in_a = _entity(session, tenant_id=tenant_a, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_a, entity_type_id=type_id)
    member_a, member_b = sorted((entity_from_b, entity_in_a))
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_a,
            member_a_id=member_a,
            member_b_id=member_b,
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-07/08: UniquenessCandidate -> EnterpriseEntity (member_b).
# =====================================================================


def test_ti07_same_tenant_candidate_member_b_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )  # no raise


def test_ti08_cross_tenant_candidate_member_b_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_in_a = _entity(session, tenant_id=tenant_a, type_id=type_id)
    entity_from_b = _entity(session, tenant_id=tenant_b, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_a, entity_type_id=type_id)
    member_a, member_b = sorted((entity_in_a, entity_from_b))
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_a,
            member_a_id=member_a,
            member_b_id=member_b,
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-09/10: UniquenessCandidate -> UniquenessPolicy.
# =====================================================================


def test_ti09_same_tenant_candidate_to_policy_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )  # no raise


def test_ti10_cross_tenant_candidate_to_policy_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_a, type_id=type_id),
            _entity(session, tenant_id=tenant_a, type_id=type_id),
        )
    )
    policy_id_b, policy_version_b = _policy(session, tenant_id=tenant_b, entity_type_id=type_id)
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_a,
            member_a_id=entity_a,
            member_b_id=entity_b,
            policy_id=policy_id_b,  # tenant B's policy
            policy_version=policy_version_b,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-11/12: UniquenessAdjudication -> UniquenessCandidate.
# =====================================================================


def test_ti11_same_tenant_adjudication_to_candidate_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    candidate_id = _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )
    session.add(
        UniquenessAdjudicationORM(
            adjudication_id=uuid4(),
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            action="REJECT_NOT_DUPLICATE",
            actor_id="steward",
            rationale="Distinct entities.",
            decided_on=NOW,
        )
    )
    session.flush()  # no raise


def test_ti12_cross_tenant_adjudication_to_candidate_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_b, type_id=type_id),
            _entity(session, tenant_id=tenant_b, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_b, entity_type_id=type_id)
    candidate_id_b = _candidate(
        session,
        tenant_id=tenant_b,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )
    session.add(
        UniquenessAdjudicationORM(
            adjudication_id=uuid4(),
            tenant_id=tenant_a,  # claims tenant A
            candidate_id=candidate_id_b,  # but points at tenant B's candidate
            action="REJECT_NOT_DUPLICATE",
            actor_id="steward",
            rationale="Distinct entities.",
            decided_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-13/14: UniquenessFinding -> UniquenessCandidate.
# =====================================================================


def _seeded_candidate(session: Session, *, tenant_id: str) -> tuple[UUID, UUID, UUID, int, UUID]:
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    candidate_id = _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )
    return entity_a, entity_b, candidate_id, policy_version, policy_id


def test_ti13_same_tenant_finding_to_candidate_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    entity_a, entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=entity_a,
            member_b_id=entity_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    session.flush()  # no raise


def test_ti14_cross_tenant_finding_to_candidate_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    entity_a, entity_b, candidate_id_b, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_b)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,  # claims tenant A
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id_b,  # but points at tenant B's candidate
            member_a_id=entity_a,
            member_b_id=entity_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-15/16: UniquenessFinding -> EnterpriseEntity (member_a).
# =====================================================================


def test_ti15_same_tenant_finding_member_a_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    entity_a, entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=entity_a,
            member_b_id=entity_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    session.flush()  # no raise


def test_ti16_cross_tenant_finding_member_a_rejected(session: Session) -> None:
    """A Finding claiming tenant A, correctly pointing at a tenant-A
    candidate, but whose denormalized `member_a_id` names a DIFFERENT
    tenant's entity -- the composite FK on `member_a_id` alone must still
    reject it, independent of the candidate FK."""
    tenant_a, tenant_b = _tenant(), _tenant()
    _entity_a, entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_a)
    type_id = _entity_type_id(session)
    foreign_entity = _entity(session, tenant_id=tenant_b, type_id=type_id)
    member_a, member_b = sorted((foreign_entity, entity_b))
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=member_a,
            member_b_id=member_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# TI-17/18: UniquenessFinding -> EnterpriseEntity (member_b).
# =====================================================================


def test_ti17_same_tenant_finding_member_b_is_accepted(session: Session) -> None:
    tenant_id = _tenant()
    entity_a, entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=entity_a,
            member_b_id=entity_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    session.flush()  # no raise


def test_ti18_cross_tenant_finding_member_b_rejected(session: Session) -> None:
    tenant_a, tenant_b = _tenant(), _tenant()
    entity_a, _entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_a)
    type_id = _entity_type_id(session)
    foreign_entity = _entity(session, tenant_id=tenant_b, type_id=type_id)
    member_a, member_b = sorted((entity_a, foreign_entity))
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_a,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=member_a,
            member_b_id=member_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


# =====================================================================
# Canonical-pair CHECK constraint (AA §7.3/§7.5) -- CDD-084 §12, U4/U40.
# =====================================================================


def test_cp01_self_pair_candidate_rejected_by_db(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_id = _entity(session, tenant_id=tenant_id, type_id=type_id)
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_id,
            member_a_id=entity_id,
            member_b_id=entity_id,  # A == A
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp02_reversed_pair_candidate_rejected_by_db(session: Session) -> None:
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_id,
            member_a_id=entity_b,  # reversed: larger UUID first
            member_b_id=entity_a,
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp03_duplicate_canonical_pair_under_same_policy_version_rejected(
    session: Session,
) -> None:
    """AA §7.3's `uq_oqi_uniqueness_candidates_idempotent` -- a second,
    independently-inserted row for the identical natural key is a real
    constraint violation at the DB layer (the application's own
    `insert_candidate_idempotent` avoids ever attempting this; this test
    proves the DB itself would refuse it even if application code did
    not)."""
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    entity_a, entity_b = sorted(
        (
            _entity(session, tenant_id=tenant_id, type_id=type_id),
            _entity(session, tenant_id=tenant_id, type_id=type_id),
        )
    )
    policy_id, policy_version = _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    _candidate(
        session,
        tenant_id=tenant_id,
        member_a_id=entity_a,
        member_b_id=entity_b,
        policy_id=policy_id,
        policy_version=policy_version,
    )
    session.add(
        UniquenessCandidateORM(
            candidate_id=uuid4(),
            tenant_id=tenant_id,
            member_a_id=entity_a,
            member_b_id=entity_b,
            policy_id=policy_id,
            policy_version=policy_version,
            matched_normalized_name="ti entity",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp04_self_pair_finding_rejected_by_db(session: Session) -> None:
    tenant_id = _tenant()
    entity_a, _entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
            candidate_id=candidate_id,
            member_a_id=entity_a,
            member_b_id=entity_a,  # A == A
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp05_one_active_policy_per_entity_type_enforced_by_db(session: Session) -> None:
    """AA §7.1's partial unique index -- a second ACTIVE policy for the
    identical `(tenant_id, entity_type_id)` anchor is rejected."""
    tenant_id = _tenant()
    type_id = _entity_type_id(session)
    _policy(session, tenant_id=tenant_id, entity_type_id=type_id)
    session.add(
        UniquenessPolicyORM(
            policy_id=uuid4(),
            version=1,
            tenant_id=tenant_id,
            entity_type_id=type_id,
            bucket_max_size=5,
            status="ACTIVE",
            created_by="steward",
            created_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp06_finding_type_check_rejects_unauthorized_value(session: Session) -> None:
    tenant_id = _tenant()
    entity_a, entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessFindingORM(
            finding_id=uuid4(),
            tenant_id=tenant_id,
            finding_type="DUPLICATE_SOURCE_RECORD_CANDIDATE",  # not implemented, CDD-084 §3
            candidate_id=candidate_id,
            member_a_id=entity_a,
            member_b_id=entity_b,
            status="OPEN",
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_cp07_adjudication_action_check_rejects_merge(session: Session) -> None:
    tenant_id = _tenant()
    _entity_a, _entity_b, candidate_id, _pv, _pid = _seeded_candidate(session, tenant_id=tenant_id)
    session.add(
        UniquenessAdjudicationORM(
            adjudication_id=uuid4(),
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            action="MERGE_ENTITY",  # never authorized, CDD-084 §2 PO-2
            actor_id="steward",
            rationale="attempted",
            decided_on=NOW,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
