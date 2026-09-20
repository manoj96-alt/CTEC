"""Repository for OQI-H6 governed Uniqueness candidate + steward
adjudication persistence (CDD-084 §12-§13, §16, §18, §21, §23; Artifact
Authorization row 8).

`fetch_population` is the ONLY query that reaches into `EnterpriseEntity`
data for candidate generation -- it returns `(enterprise_entity_id,
enterprise_entity_name)` pairs scoped to exactly one `(tenant_id,
entity_type_id)`, mirroring `EntityResolutionEngine.discover_candidates`'s
own caller-supplied-population shape (CDD-084 §16's own discovery: neither
this repository nor Entity Resolution performs indexed blocking at the
database level -- bucketing by `canonical_name()` happens in the
application layer, on this bounded, already-tenant-and-type-scoped
population, never on the whole tenant's entity graph). Seed `14` is the
next available value in the OQI advisory-lock seed registry, distinct from
every existing seed (1-13)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.domain.oqi_uniqueness.candidate import (
    UniquenessAdjudication,
    UniquenessAdjudicationAction,
    UniquenessCandidate,
)
from app.infrastructure.persistence.models.enterprise_entity import (
    EnterpriseEntity as EnterpriseEntityORM,
)
from app.infrastructure.persistence.models.oqi_uniqueness import (
    UniquenessAdjudicationORM,
    UniquenessCandidateORM,
)

#: CDD-084 §16, §21: next available value in the OQI advisory-lock seed
#: registry, distinct from every existing OQI seed (1-13).
OQI_UNIQUENESS_CANDIDATE_ADVISORY_LOCK_SEED = 14


class OqiUniquenessCandidateRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def acquire_candidate_authority(self, identity: str) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))"),
            {"identity": identity, "seed": OQI_UNIQUENESS_CANDIDATE_ADVISORY_LOCK_SEED},
        )

    def fetch_population(
        self, *, tenant_id: str, entity_type_id: UUID
    ) -> tuple[tuple[UUID, str], ...]:
        """CDD-084 §16: the bounded, already-scoped population a bucket is
        computed over -- exactly one tenant, exactly one `entity_type_id`.
        No blocking index exists or is authorized; the caller (the
        application-layer evaluator service) is responsible for grouping
        this tuple by `canonical_name()` and enforcing `bucket_max_size`
        (CDD-084 §17) -- this method itself never truncates or samples."""
        rows = self.session.execute(
            select(
                EnterpriseEntityORM.enterprise_entity_id, EnterpriseEntityORM.enterprise_entity_name
            ).where(
                EnterpriseEntityORM.tenant_id == tenant_id,
                EnterpriseEntityORM.entity_type_id == entity_type_id,
            )
        ).all()
        return tuple((row[0], row[1]) for row in rows)

    def get_candidate_for_pair(
        self,
        *,
        tenant_id: str,
        member_a_id: UUID,
        member_b_id: UUID,
        policy_id: UUID,
        policy_version: int,
    ) -> UniquenessCandidate | None:
        """CDD-084 §23: the exact idempotency lookup -- `(tenant_id,
        member_a_id, member_b_id, policy_id, policy_version)` is the
        candidate's own natural key (enforced by the database's own
        `uq_oqi_uniqueness_candidates_idempotent` unique constraint,
        AA §7.3)."""
        model = self.session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a_id,
                UniquenessCandidateORM.member_b_id == member_b_id,
                UniquenessCandidateORM.policy_id == policy_id,
                UniquenessCandidateORM.policy_version == policy_version,
            )
        ).scalar_one_or_none()
        return None if model is None else _candidate_to_domain(model)

    def insert_candidate_idempotent(self, candidate: UniquenessCandidate) -> UniquenessCandidate:
        """Returns the persisted candidate -- either the one just inserted,
        or the pre-existing row for the identical natural key (CDD-084
        §23's idempotency, U10). Never raises `IntegrityError` on a genuine
        replay; a genuinely different `candidate_id` for the same natural
        key would indicate a caller bug (never expected in practice, since
        `candidate_id` is always freshly generated here, not
        caller-supplied) and is intentionally left to surface as a real
        `IntegrityError` rather than silently reconciled."""
        existing = self.get_candidate_for_pair(
            tenant_id=candidate.tenant_id,
            member_a_id=candidate.member_a_id,
            member_b_id=candidate.member_b_id,
            policy_id=candidate.policy_id,
            policy_version=candidate.policy_version,
        )
        if existing is not None:
            return existing
        self.session.add(
            UniquenessCandidateORM(
                candidate_id=candidate.candidate_id,
                tenant_id=candidate.tenant_id,
                member_a_id=candidate.member_a_id,
                member_b_id=candidate.member_b_id,
                policy_id=candidate.policy_id,
                policy_version=candidate.policy_version,
                matched_normalized_name=candidate.matched_normalized_name,
                created_on=candidate.created_on,
            )
        )
        self.session.flush()
        return candidate

    def get_candidate(self, *, tenant_id: str, candidate_id: UUID) -> UniquenessCandidate | None:
        model = self.session.get(UniquenessCandidateORM, candidate_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        return _candidate_to_domain(model)

    def insert_adjudication(self, adjudication: UniquenessAdjudication) -> None:
        """Append-only -- no update, no delete authorized on this table by
        any implementation code (CDD-084 §21)."""
        self.session.add(
            UniquenessAdjudicationORM(
                adjudication_id=adjudication.adjudication_id,
                tenant_id=adjudication.tenant_id,
                candidate_id=adjudication.candidate_id,
                action=adjudication.action.value,
                actor_id=adjudication.actor_id,
                rationale=adjudication.rationale,
                decided_on=adjudication.decided_on,
            )
        )
        self.session.flush()

    def get_latest_adjudication_for_pair(
        self, *, tenant_id: str, member_a_id: UUID, member_b_id: UUID
    ) -> tuple[UniquenessAdjudication, str] | None:
        """CDD-084 §22: because a candidate's own identity includes
        `policy_version` (§23), a policy version bump always produces a
        logically distinct `candidate_id` for the same canonical pair --
        `get_latest_adjudication` alone (keyed to one specific
        `candidate_id`) would therefore never see a rejection recorded
        against an EARLIER version's candidate row, silently reopening
        every rejected pair on the next policy version bump regardless of
        whether the underlying evidence changed. This method instead finds
        the latest adjudication across EVERY candidate row ever generated
        for this canonical pair (any policy version), paired with that
        specific candidate's own `matched_normalized_name` -- the caller
        compares it against the CURRENT run's own matched name (CDD-084
        §22: only a genuinely new normalized-name match, not a version
        bump alone, may make a rejected pair reviewable again)."""
        row = self.session.execute(
            select(UniquenessAdjudicationORM, UniquenessCandidateORM.matched_normalized_name)
            .join(
                UniquenessCandidateORM,
                UniquenessCandidateORM.candidate_id == UniquenessAdjudicationORM.candidate_id,
            )
            .where(
                UniquenessAdjudicationORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a_id,
                UniquenessCandidateORM.member_b_id == member_b_id,
            )
            .order_by(
                UniquenessAdjudicationORM.decided_on.desc(),
                UniquenessAdjudicationORM.adjudication_id.desc(),
            )
            .limit(1)
        ).first()
        if row is None:
            return None
        adjudication_model, matched_normalized_name = row
        return _adjudication_to_domain(adjudication_model), matched_normalized_name

    def get_latest_adjudication(
        self, *, tenant_id: str, candidate_id: UUID
    ) -> UniquenessAdjudication | None:
        """CDD-084 §21: current disposition is always derived from the
        latest adjudication row for a candidate -- ordered by `decided_on`,
        `adjudication_id` as a deterministic tie-break."""
        model = self.session.execute(
            select(UniquenessAdjudicationORM)
            .where(
                UniquenessAdjudicationORM.tenant_id == tenant_id,
                UniquenessAdjudicationORM.candidate_id == candidate_id,
            )
            .order_by(
                UniquenessAdjudicationORM.decided_on.desc(),
                UniquenessAdjudicationORM.adjudication_id.desc(),
            )
            .limit(1)
        ).scalar_one_or_none()
        return None if model is None else _adjudication_to_domain(model)


def _candidate_to_domain(model: UniquenessCandidateORM) -> UniquenessCandidate:
    return UniquenessCandidate(
        candidate_id=model.candidate_id,
        tenant_id=model.tenant_id,
        member_a_id=model.member_a_id,
        member_b_id=model.member_b_id,
        policy_id=model.policy_id,
        policy_version=model.policy_version,
        matched_normalized_name=model.matched_normalized_name,
        created_on=model.created_on,
    )


def _adjudication_to_domain(model: UniquenessAdjudicationORM) -> UniquenessAdjudication:
    return UniquenessAdjudication(
        adjudication_id=model.adjudication_id,
        tenant_id=model.tenant_id,
        candidate_id=model.candidate_id,
        action=UniquenessAdjudicationAction(model.action),
        actor_id=model.actor_id,
        rationale=model.rationale,
        decided_on=model.decided_on,
    )
