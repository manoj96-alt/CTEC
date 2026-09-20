"""Repository for OQI-H6 Uniqueness evaluation + Finding persistence
(CDD-084 §19-§20, §24-§25, §28; Artifact Authorization row 9).

`has_qualifying_coverage` (CDD-084 §28) is created now, alongside the rest
of this I1-authorized file, so I2's dispatch-only change to
`oqi_quality_coverage_policy_repository.py` needs no further MODIFY to this
file -- mirroring `OqiTimelinessEvaluationRepositoryImpl.has_qualifying_
coverage`'s identical precedent (CDD-051 §25) exactly. It is not wired into
any I2 dispatch point by this phase; its existence here is not I2 scope
creep, since the repository FILE itself is entirely I1-authorized.

`acquire_evaluation_authority` reuses a dedicated seed (15), distinct from
the policy repository's own seed (13), the candidate repository's own seed
(14), and every other existing OQI seed (1-12)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_uniqueness.evaluation import (
    UniquenessFinding,
    UniquenessFindingStatus,
)
from app.infrastructure.persistence.models.oqi_uniqueness import (
    UniquenessEvaluationORM,
    UniquenessFindingORM,
)

#: CDD-084 §19: next available value in the OQI advisory-lock seed
#: registry, distinct from the policy repository's own seed (13), the
#: candidate repository's own seed (14), and every existing OQI seed (1-12).
OQI_UNIQUENESS_EVALUATION_ADVISORY_LOCK_SEED = 15


class OqiUniquenessEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_UNIQUENESS_EVALUATION_ADVISORY_LOCK_SEED},
        )

    def get_finding(self, finding_id: UUID) -> UniquenessFinding | None:
        model = self.session.get(UniquenessFindingORM, finding_id)
        return None if model is None else _finding_to_domain(model)

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        policy_id: UUID,
        policy_version: int,
        enterprise_entity_id: UUID,
        outcome: str,
        not_evaluable_reason: str | None,
        candidate_count: int,
        evaluated_on: datetime,
    ) -> bool:
        existing = self.session.get(UniquenessEvaluationORM, evaluation_id)
        if existing is not None:
            return False
        self.session.add(
            UniquenessEvaluationORM(
                evaluation_id=evaluation_id,
                tenant_id=tenant_id,
                policy_id=policy_id,
                policy_version=policy_version,
                enterprise_entity_id=enterprise_entity_id,
                outcome=outcome,
                not_evaluable_reason=not_evaluable_reason,
                candidate_count=candidate_count,
                evaluated_on=evaluated_on,
            )
        )
        self.session.flush()
        return True

    def upsert_finding(self, finding: UniquenessFinding) -> None:
        model = self.session.get(UniquenessFindingORM, finding.finding_id)
        if model is None:
            self.session.add(_finding_to_orm(finding))
            return
        model.candidate_id = finding.candidate_id
        model.status = finding.status.value
        model.state_revision = finding.state_revision
        model.last_seen_at = finding.last_seen_at
        model.occurrence_count = finding.occurrence_count
        model.reopen_count = finding.reopen_count

    def has_qualifying_coverage(
        self, *, tenant_id: str, enterprise_entity_ids: tuple[UUID, ...]
    ) -> bool:
        """CDD-084 §28 (I2 Coverage dispatch will consume this): existence-
        only, subject-scoped -- at least one Uniqueness evaluation row
        (`SATISFIED`, `VIOLATED`, or a persisted `NOT_EVALUABLE` row) exists
        for one of the caller-supplied `enterprise_entity_id`s. A zero-row
        state (no ACTIVE policy at all, CDD-084 §20) is correctly excluded
        -- there is no row to find."""
        if not enterprise_entity_ids:
            return False
        return (
            self.session.execute(
                select(UniquenessEvaluationORM.evaluation_id)
                .where(
                    UniquenessEvaluationORM.tenant_id == tenant_id,
                    UniquenessEvaluationORM.enterprise_entity_id.in_(enterprise_entity_ids),
                )
                .limit(1)
            ).first()
            is not None
        )

    def get_open_findings_for_entity_type(
        self, *, tenant_id: str, entity_ids: tuple[UUID, ...]
    ) -> tuple[UniquenessFinding, ...]:
        """CDD-084 §25: every currently-OPEN Uniqueness Finding whose pair
        includes at least one of the given entities -- used by the
        evaluator service to reconcile Findings whose candidate no longer
        qualifies (CDD-084 §25's "fresh re-evaluation demonstrates the
        duplicate condition no longer exists" closing path)."""
        if not entity_ids:
            return ()
        models = (
            self.session.execute(
                select(UniquenessFindingORM).where(
                    UniquenessFindingORM.tenant_id == tenant_id,
                    UniquenessFindingORM.status == UniquenessFindingStatus.OPEN.value,
                    (
                        UniquenessFindingORM.member_a_id.in_(entity_ids)
                        | UniquenessFindingORM.member_b_id.in_(entity_ids)
                    ),
                )
            )
            .scalars()
            .all()
        )
        return tuple(_finding_to_domain(model) for model in models)


def _finding_to_orm(finding: UniquenessFinding) -> UniquenessFindingORM:
    return UniquenessFindingORM(
        finding_id=finding.finding_id,
        tenant_id=finding.tenant_id,
        finding_type="DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE",
        candidate_id=finding.candidate_id,
        member_a_id=finding.member_a_id,
        member_b_id=finding.member_b_id,
        status=finding.status.value,
        state_revision=finding.state_revision,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        occurrence_count=finding.occurrence_count,
        reopen_count=finding.reopen_count,
    )


def _finding_to_domain(model: UniquenessFindingORM) -> UniquenessFinding:
    return UniquenessFinding(
        finding_id=model.finding_id,
        tenant_id=model.tenant_id,
        candidate_id=model.candidate_id,
        member_a_id=model.member_a_id,
        member_b_id=model.member_b_id,
        status=UniquenessFindingStatus(model.status),
        state_revision=model.state_revision,
        first_seen_at=model.first_seen_at,
        last_seen_at=model.last_seen_at,
        occurrence_count=model.occurrence_count,
        reopen_count=model.reopen_count,
    )
