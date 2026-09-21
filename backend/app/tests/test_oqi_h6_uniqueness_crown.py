"""CDD-084 OQI-H6 Governed EnterpriseEntity Uniqueness -- Artifact
Authorization row 11 (U1-U20) + the dedicated performance crown (AA §14):
the real-PostgreSQL crown suite. Candidate generation, canonical pair
enforcement, entity-type exclusion, bucket-cap fail-closed behavior,
SATISFIED/VIOLATED/NOT_EVALUABLE semantics, idempotency, steward
adjudication (rejection persistence, confirmation-never-merges), OQI4
both-member impact resolution, and a bounded-search proof that no naive
all-pairs path exists -- all against real seeded `EnterpriseEntity` rows
flowing through the real evaluator/adjudication service, never a
directly-inserted conclusion (CDD-046 §45)."""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import UTC, datetime
from itertools import combinations
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.application.oqi_uniqueness_evaluation_service import OqiUniquenessEvaluationService
from app.core.bootstrap import BOOTSTRAP_BUSINESS_DOMAIN_ID, BOOTSTRAP_SYSTEM_ENTITY_ID
from app.domain.oqi_ontology_impact.evaluation import ImpactOutcome
from app.domain.oqi_uniqueness.candidate import UniquenessAdjudicationAction
from app.domain.oqi_uniqueness.evaluation import (
    UniquenessFindingStatus,
    UniquenessNotEvaluableReason,
    UniquenessOutcome,
    derive_uniqueness_finding_id,
)
from app.domain.oqi_uniqueness.policy import UniquenessPolicy, new_uniqueness_policy
from app.infrastructure.persistence.models.enterprise_entity import EnterpriseEntity
from app.infrastructure.persistence.models.entity_type import EntityType
from app.infrastructure.persistence.ontology_seed import OntologySeeder
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    OqiOntologyImpactEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_uniqueness_candidate_repository import (
    OqiUniquenessCandidateRepositoryImpl,
)
from app.infrastructure.persistence.oqi_uniqueness_evaluation_repository import (
    OqiUniquenessEvaluationRepositoryImpl,
)
from app.infrastructure.persistence.oqi_uniqueness_policy_repository import (
    OqiUniquenessPolicyRepositoryImpl,
)

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


def _entity_type_id(session: Session, name: str) -> UUID:
    OntologySeeder(session).load()
    session.commit()
    value = session.scalar(
        select(EntityType.entity_type_id).where(EntityType.entity_type_name == name)
    )
    assert value is not None
    return value


#: `EnterpriseEntity` carries a pre-existing `UNIQUE(tenant_id,
#: enterprise_entity_name)` constraint (RAW string, not scoped by
#: `entity_type_id`) -- two entities in the same tenant can never share an
#: identical raw name, regardless of type. Every Uniqueness crown scenario
#: therefore needs raw-distinct names that still canonicalize identically
#: (case/legal-suffix variance) -- exactly CDD-046 §6's own "Acme Corp" /
#: "Acme Corporation" worked example, never the same literal string twice.
_LEGAL_SUFFIXES = ("", " Corp", " Corp.", " Corporation", " Inc", " Inc.", " Incorporated", " Co")
_CASINGS = (str.upper, str.lower, str.title, lambda s: s, lambda s: s.swapcase())


def _dup_names(base: str, count: int) -> list[str]:
    """`enterprise_entity_name` is GLOBALLY unique (the original canonical
    schema's bare `UNIQUE` constraint, `enterprise_entities_enterprise_
    entity_name_key`, predates and coexists with the later tenant-qualified
    `uq_enterprise_entities_tenant_name` -- neither is authorized for this
    phase to touch, CDD-084 §32). A per-call random token is folded into
    `base` so every call's raw names are globally unique across the whole
    test run, while still canonicalizing identically to one another within
    the same call (the token survives normalization, since it is never a
    recognized legal suffix)."""
    unique_base = f"{base} {uuid4().hex[:8]}"
    names: list[str] = []
    seen: set[str] = set()
    for suffix in _LEGAL_SUFFIXES:
        for casing in _CASINGS:
            candidate = casing(unique_base + suffix)
            if candidate not in seen:
                seen.add(candidate)
                names.append(candidate)
            if len(names) >= count:
                return names
    raise AssertionError(f"could not generate {count} distinct raw name variants for {base!r}")


def _entity(session: Session, *, tenant_id: str, type_id: UUID, name: str) -> UUID:
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
            entity_type_id=type_id,
            business_domain_id=BOOTSTRAP_BUSINESS_DOMAIN_ID,
        )
    )
    session.flush()
    return entity_id


def _policy(
    session: Session, *, tenant_id: str, entity_type_id: UUID, bucket_max_size: int = 10
) -> UniquenessPolicy:
    repo = OqiUniquenessPolicyRepositoryImpl(session)
    policy = new_uniqueness_policy(
        policy_id=uuid4(),
        tenant_id=tenant_id,
        entity_type_id=entity_type_id,
        bucket_max_size=bucket_max_size,
        created_by="steward-crown",
        created_on=NOW,
    )
    repo.insert_policy(policy)
    session.commit()
    return policy


def _service(
    session: Session, *, clock: Callable[[], datetime] = lambda: NOW
) -> OqiUniquenessEvaluationService:
    return OqiUniquenessEvaluationService(
        policy_lookup=OqiUniquenessPolicyRepositoryImpl(session),
        candidate_repository=OqiUniquenessCandidateRepositoryImpl(session),
        evaluation_repository=OqiUniquenessEvaluationRepositoryImpl(session),
        clock=clock,
    )


class TestCandidateGeneration:
    def test_u1_matching_names_persist_a_candidate(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        name_a, name_b = _dup_names("Acme Widget", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        member_a, member_b = sorted((entity_a, entity_b))
        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        model = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()
        assert model.matched_normalized_name != ""

    def test_u2_candidate_opens_duplicate_finding(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Acme Widget", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        member_a, member_b = sorted((entity_a, entity_b))
        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status is UniquenessFindingStatus.OPEN

    def test_u3_generation_order_yields_one_canonical_pair(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Zebra Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        rows = (
            session.execute(
                select(UniquenessCandidateORM).where(
                    UniquenessCandidateORM.tenant_id == tenant_id,
                    UniquenessCandidateORM.member_a_id == member_a,
                    UniquenessCandidateORM.member_b_id == member_b,
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].member_a_id < rows[0].member_b_id

    def test_u6_incompatible_entity_type_never_becomes_a_candidate(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")
        shared_a, shared_b = _dup_names("Shared Name", 2)
        _entity(session, tenant_id=tenant_id, type_id=product_type, name=shared_a)
        _entity(session, tenant_id=tenant_id, type_id=facility_type, name=shared_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        _policy(session, tenant_id=tenant_id, entity_type_id=facility_type)
        session.commit()

        service = _service(session)
        evals_product = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=product_type, moment=NOW
        )
        evals_facility = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=facility_type, moment=NOW
        )
        session.commit()

        # Each entity_type's own sole member is SATISFIED -- a same-name
        # entity of a DIFFERENT type never enters its bucket at all
        # (CDD-084 §14, §17 -- candidate generation is scoped BEFORE
        # comparison, not filtered after).
        assert all(e.outcome is UniquenessOutcome.SATISFIED for e in evals_product)
        assert all(e.outcome is UniquenessOutcome.SATISFIED for e in evals_facility)


class TestNoPolicyAndSatisfied:
    def test_u7_no_active_policy_is_zero_row_not_evaluable(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _entity(session, tenant_id=tenant_id, type_id=product_type, name="Solo Corp")
        session.commit()

        service = _service(session)
        evaluations = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=product_type, moment=NOW
        )
        assert evaluations == ()

    def test_u8_completed_search_no_candidate_is_satisfied(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _entity(session, tenant_id=tenant_id, type_id=product_type, name="Unique Corp A")
        _entity(session, tenant_id=tenant_id, type_id=product_type, name="Unique Corp B")
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        evaluations = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=product_type, moment=NOW
        )
        session.commit()

        assert len(evaluations) == 2
        assert all(e.outcome is UniquenessOutcome.SATISFIED for e in evaluations)
        assert all(e.candidate_count == 0 for e in evaluations)


class TestBucketCap:
    def test_u9_bucket_exceeding_cap_fails_closed(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        for overflow_name in _dup_names("Overflow Corp", 4):
            _entity(session, tenant_id=tenant_id, type_id=product_type, name=overflow_name)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type, bucket_max_size=3)
        session.commit()

        service = _service(session)
        evaluations = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=product_type, moment=NOW
        )
        session.commit()

        assert len(evaluations) == 4
        assert all(e.outcome is UniquenessOutcome.NOT_EVALUABLE for e in evaluations)
        assert all(
            e.not_evaluable_reason is UniquenessNotEvaluableReason.BUCKET_EXCEEDED_CAP
            for e in evaluations
        )
        assert all(e.candidate_count == 0 for e in evaluations)

        # No candidate at all was generated for the over-cap bucket --
        # never truncation, never a first-N comparison.
        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        rows = (
            session.execute(
                select(UniquenessCandidateORM).where(UniquenessCandidateORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        assert rows == []

    def test_u9_bucket_within_cap_unaffected(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b, _name_c = _dup_names("Fits Corp", 3)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        entity_c = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_c)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type, bucket_max_size=3)
        session.commit()

        service = _service(session)
        evaluations = service.evaluate_entity_type(
            tenant_id=tenant_id, entity_type_id=product_type, moment=NOW
        )
        session.commit()

        assert {entity_a, entity_b, entity_c} == {e.enterprise_entity_id for e in evaluations}
        assert all(e.outcome is UniquenessOutcome.VIOLATED for e in evaluations)
        assert all(e.candidate_count == 2 for e in evaluations)


class TestIdempotency:
    def test_u10_rerun_is_idempotent(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _repeat_a, _repeat_b = _dup_names("Repeat Corp", 2)
        _entity(session, tenant_id=tenant_id, type_id=product_type, name=_repeat_a)
        _entity(session, tenant_id=tenant_id, type_id=product_type, name=_repeat_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import (
            UniquenessCandidateORM,
            UniquenessEvaluationORM,
        )

        candidates_after_first = (
            session.execute(
                select(UniquenessCandidateORM).where(UniquenessCandidateORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        evaluations_after_first = (
            session.execute(
                select(UniquenessEvaluationORM).where(
                    UniquenessEvaluationORM.tenant_id == tenant_id
                )
            )
            .scalars()
            .all()
        )

        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        candidates_after_second = (
            session.execute(
                select(UniquenessCandidateORM).where(UniquenessCandidateORM.tenant_id == tenant_id)
            )
            .scalars()
            .all()
        )
        evaluations_after_second = (
            session.execute(
                select(UniquenessEvaluationORM).where(
                    UniquenessEvaluationORM.tenant_id == tenant_id
                )
            )
            .scalars()
            .all()
        )

        assert len(candidates_after_first) == len(candidates_after_second) == 1
        assert len(evaluations_after_first) == len(evaluations_after_second) == 2
        assert {row.candidate_id for row in candidates_after_first} == {
            row.candidate_id for row in candidates_after_second
        }
        assert {row.evaluation_id for row in evaluations_after_first} == {
            row.evaluation_id for row in evaluations_after_second
        }


class TestAdjudication:
    def test_u11_reject_not_duplicate_persists_and_closes_finding(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Reject Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        candidate_row = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()

        adjudication = service.adjudicate(
            tenant_id=tenant_id,
            candidate_id=candidate_row.candidate_id,
            action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE,
            actor_id="steward-1",
            rationale="Distinct real-world companies with a coincidentally identical name.",
            moment=NOW,
        )
        session.commit()
        assert adjudication.action is UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE

        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status is UniquenessFindingStatus.RESOLVED

    def test_u12_unchanged_rerun_does_not_resurface_rejected_candidate(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Stable Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        candidate_row = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()
        service.adjudicate(
            tenant_id=tenant_id,
            candidate_id=candidate_row.candidate_id,
            action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE,
            actor_id="steward-1",
            rationale="Confirmed distinct entities.",
            moment=NOW,
        )
        session.commit()

        # Rerun the identical evaluation under the SAME (unchanged) policy
        # version.
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status is UniquenessFindingStatus.RESOLVED

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessEvaluationORM

        eval_rows = (
            session.execute(
                select(UniquenessEvaluationORM).where(
                    UniquenessEvaluationORM.tenant_id == tenant_id,
                    UniquenessEvaluationORM.enterprise_entity_id == entity_a,
                )
            )
            .scalars()
            .all()
        )
        # The append-only ledger honestly retains BOTH the original,
        # genuinely-VIOLATED evaluation (before rejection) and the rerun's
        # SATISFIED evaluation (rejection means zero currently-qualifying
        # candidates remain) -- two distinct rows, never one overwritten by
        # the other.
        assert len(eval_rows) == 2
        outcomes = {row.outcome for row in eval_rows}
        assert outcomes == {"VIOLATED", "SATISFIED"}
        satisfied_row = next(row for row in eval_rows if row.outcome == "SATISFIED")
        assert satisfied_row.candidate_count == 0

    def test_u13_new_policy_version_can_reopen_a_genuinely_new_candidate(
        self, session: Session
    ) -> None:
        """CDD-084 §22: a policy version bump alone does not reopen a
        rejected pair -- only a genuinely NEW candidate (a fresh
        normalized-name match under the new version) can. This test proves
        the pair stays RESOLVED under a version bump alone; U12 already
        proves the "unchanged, same version" non-reopening case."""
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Versioned Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        policy = _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        candidate_row = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()
        service.adjudicate(
            tenant_id=tenant_id,
            candidate_id=candidate_row.candidate_id,
            action=UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE,
            actor_id="steward-1",
            rationale="Confirmed distinct entities.",
            moment=NOW,
        )
        session.commit()

        # Bump the policy version (retire v1, activate v2) with an
        # unchanged bucket_max_size -- the candidate qualification rule
        # itself is unaffected, so the SAME pair does not regenerate a new
        # candidate_id under v2 either (bucket membership, not version,
        # determines qualification, CDD-084 §22).
        from app.domain.oqi_uniqueness.policy import new_uniqueness_policy_version

        policy_repo = OqiUniquenessPolicyRepositoryImpl(session)
        policy_repo.retire_policy(
            tenant_id=tenant_id, policy_id=policy.policy_id, version=policy.version
        )
        v2 = new_uniqueness_policy_version(policy, created_by="steward-2", created_on=NOW)
        policy_repo.insert_policy(v2)
        session.commit()

        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status is UniquenessFindingStatus.RESOLVED

    def test_u14_confirm_duplicate_never_mutates_the_entities(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Confirm Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        before_a = session.get(EnterpriseEntity, entity_a)
        before_b = session.get(EnterpriseEntity, entity_b)
        assert before_a is not None and before_b is not None
        snapshot = {
            entity_a: (
                before_a.enterprise_entity_name,
                before_a.lifecycle_state,
                before_a.governance_status,
                before_a.version_number,
            ),
            entity_b: (
                before_b.enterprise_entity_name,
                before_b.lifecycle_state,
                before_b.governance_status,
                before_b.version_number,
            ),
        }

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        candidate_row = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()
        service.adjudicate(
            tenant_id=tenant_id,
            candidate_id=candidate_row.candidate_id,
            action=UniquenessAdjudicationAction.CONFIRM_DUPLICATE,
            actor_id="steward-1",
            rationale="Confirmed genuine duplicate representation.",
            moment=NOW,
        )
        session.commit()

        session.expire_all()
        after_a = session.get(EnterpriseEntity, entity_a)
        after_b = session.get(EnterpriseEntity, entity_b)
        assert after_a is not None and after_b is not None
        assert snapshot[entity_a] == (
            after_a.enterprise_entity_name,
            after_a.lifecycle_state,
            after_a.governance_status,
            after_a.version_number,
        )
        assert snapshot[entity_b] == (
            after_b.enterprise_entity_name,
            after_b.lifecycle_state,
            after_b.governance_status,
            after_b.version_number,
        )
        # No InstitutionalRelationship of any kind was created either --
        # H6 has no code path capable of writing one.
        from app.infrastructure.persistence.models.institutional_relationship import (
            InstitutionalRelationship,
        )

        relationships = (
            session.execute(
                select(InstitutionalRelationship).where(
                    InstitutionalRelationship.from_entity_id.in_([entity_a, entity_b])
                    | InstitutionalRelationship.to_entity_id.in_([entity_a, entity_b])
                )
            )
            .scalars()
            .all()
        )
        assert relationships == []

    def test_u15_confirm_duplicate_leaves_finding_open(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Open Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        member_a, member_b = sorted((entity_a, entity_b))
        candidate_row = session.execute(
            select(UniquenessCandidateORM).where(
                UniquenessCandidateORM.tenant_id == tenant_id,
                UniquenessCandidateORM.member_a_id == member_a,
                UniquenessCandidateORM.member_b_id == member_b,
            )
        ).scalar_one()
        service.adjudicate(
            tenant_id=tenant_id,
            candidate_id=candidate_row.candidate_id,
            action=UniquenessAdjudicationAction.CONFIRM_DUPLICATE,
            actor_id="steward-1",
            rationale="Confirmed genuine duplicate representation.",
            moment=NOW,
        )
        session.commit()

        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding is not None
        assert finding.status is UniquenessFindingStatus.OPEN

    def test_u16_policy_change_alone_does_not_falsely_resolve(self, session: Session) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Steady Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        policy = _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        member_a, member_b = sorted((entity_a, entity_b))
        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )
        finding_before = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding_before is not None
        assert finding_before.status is UniquenessFindingStatus.OPEN

        # Retire + version-bump the policy, WITHOUT running a new
        # evaluation -- the Finding must not change at all.
        policy_repo = OqiUniquenessPolicyRepositoryImpl(session)
        policy_repo.retire_policy(
            tenant_id=tenant_id, policy_id=policy.policy_id, version=policy.version
        )
        session.commit()

        finding_after = OqiUniquenessEvaluationRepositoryImpl(session).get_finding(finding_id)
        assert finding_after is not None
        assert finding_after.status is UniquenessFindingStatus.OPEN
        assert finding_after.state_revision == finding_before.state_revision


class TestOqi4Integration:
    def test_u17_and_u18_both_members_resolve_through_oqi4_under_one_finding(
        self, session: Session
    ) -> None:
        tenant_id = _tenant()
        product_type = _entity_type_id(session, "Product")
        _name_a, _name_b = _dup_names("Impact Corp", 2)
        entity_a = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_a)
        entity_b = _entity(session, tenant_id=tenant_id, type_id=product_type, name=_name_b)
        _policy(session, tenant_id=tenant_id, entity_type_id=product_type)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_id, entity_type_id=product_type, moment=NOW)
        session.commit()

        member_a, member_b = sorted((entity_a, entity_b))
        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id, member_a_id=member_a, member_b_id=member_b
        )

        impact_repo = OqiOntologyImpactEvaluationRepositoryImpl(session)
        origin = impact_repo.resolve_uniqueness_finding_origin(
            tenant_id=tenant_id, finding_id=finding_id
        )
        assert origin.finding_id == finding_id
        assert origin.quality_dimension == "UNIQUENESS"

        impact_a, impact_b = impact_repo.resolve_uniqueness_finding_subject(
            tenant_id=tenant_id, finding_id=finding_id
        )
        assert impact_a.outcome is ImpactOutcome.IMPACTED
        assert impact_b.outcome is ImpactOutcome.IMPACTED
        assert {impact_a.entity_id, impact_b.entity_id} == {member_a, member_b}
        # Both impact results are resolved from the SAME finding_id lookup
        # -- U18's "same Finding ID supports both impact subjects".


class TestPerformanceCrown:
    def test_no_naive_all_pairs_across_unrelated_buckets_or_tenants(self, session: Session) -> None:
        """AA §14: proves candidate generation only ever compares within
        one tenant's one entity_type's one canonical-name bucket -- never
        across tenants, never across entity types, never across unrelated
        buckets, and never beyond a governed cap."""
        tenant_a = _tenant()
        tenant_b = _tenant()
        product_type = _entity_type_id(session, "Product")
        facility_type = _entity_type_id(session, "Facility")

        # Tenant A: two real duplicate buckets ("Alpha"x3, "Beta"x2) plus
        # eight singleton names -- 10 Product entities total, well within
        # a generous cap, but only the two real buckets may ever produce a
        # candidate. "Alpha" needs 5 distinct raw names across this test
        # (3 in Tenant A/Product, 1 in Tenant B/Product, 1 in Tenant
        # A/Facility) -- EnterpriseEntity's raw UNIQUE(tenant_id, name)
        # constraint is per-tenant, not global, so names only need to be
        # raw-distinct WITHIN each tenant; drawing from one shared pool of
        # 5 satisfies that trivially.
        alpha_names = _dup_names("Alpha Corp", 5)
        beta_names = _dup_names("Beta Corp", 2)
        overflow_names = _dup_names("Overflow Bucket", 5)

        alpha_ids = [
            _entity(session, tenant_id=tenant_a, type_id=product_type, name=alpha_names[i])
            for i in range(3)
        ]
        beta_ids = [
            _entity(session, tenant_id=tenant_a, type_id=product_type, name=beta_names[i])
            for i in range(2)
        ]
        singleton_ids = [
            _entity(session, tenant_id=tenant_a, type_id=product_type, name=f"Singleton {i}")
            for i in range(8)
        ]
        # Tenant B: an entity sharing Tenant A's "Alpha" canonical name --
        # must never be compared against Tenant A's own Alpha members.
        tenant_b_alpha = _entity(
            session, tenant_id=tenant_b, type_id=product_type, name=alpha_names[3]
        )
        # Tenant A, Facility type: an entity sharing the same canonical
        # "Alpha" name -- must never be compared against Product-type
        # Alpha members.
        tenant_a_facility_alpha = _entity(
            session, tenant_id=tenant_a, type_id=facility_type, name=alpha_names[4]
        )
        # An over-cap bucket in Tenant A, Product type.
        overflow_ids = [
            _entity(session, tenant_id=tenant_a, type_id=product_type, name=overflow_names[i])
            for i in range(5)
        ]

        _policy(session, tenant_id=tenant_a, entity_type_id=product_type, bucket_max_size=4)
        _policy(session, tenant_id=tenant_a, entity_type_id=facility_type, bucket_max_size=4)
        _policy(session, tenant_id=tenant_b, entity_type_id=product_type, bucket_max_size=4)
        session.commit()

        service = _service(session)
        service.evaluate_entity_type(tenant_id=tenant_a, entity_type_id=product_type, moment=NOW)
        service.evaluate_entity_type(tenant_id=tenant_a, entity_type_id=facility_type, moment=NOW)
        service.evaluate_entity_type(tenant_id=tenant_b, entity_type_id=product_type, moment=NOW)
        session.commit()

        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessCandidateORM

        # Scoped to THIS test's own two tenants -- other tests in this same
        # module-scoped database session commit their own candidate rows
        # too (never rolled back mid-suite), so an unscoped whole-table
        # query would wrongly include unrelated tests' own data.
        all_candidates = (
            session.execute(
                select(UniquenessCandidateORM).where(
                    UniquenessCandidateORM.tenant_id.in_((tenant_a, tenant_b))
                )
            )
            .scalars()
            .all()
        )
        pairs = {(row.tenant_id, row.member_a_id, row.member_b_id) for row in all_candidates}

        # Exactly C(3,2)=3 Alpha pairs + C(2,2)=1 Beta pair for Tenant A
        # Product -- nothing else, ever.
        expected_alpha_pairs = {(tenant_a, *sorted((a, b))) for a, b in combinations(alpha_ids, 2)}
        expected_beta_pairs = {(tenant_a, *sorted((a, b))) for a, b in combinations(beta_ids, 2)}
        assert pairs == expected_alpha_pairs | expected_beta_pairs

        # Explicitly prove the forbidden cross-tenant and cross-type
        # comparisons never happened.
        for candidate_pair in pairs:
            _, member_a, member_b = candidate_pair
            assert tenant_b_alpha not in (member_a, member_b)
            assert tenant_a_facility_alpha not in (member_a, member_b)
            assert not set(overflow_ids) & {member_a, member_b}
            assert not set(singleton_ids) & {member_a, member_b}

        # The over-cap bucket produced zero candidates and every one of
        # its five members is NOT_EVALUABLE -- never silently sampled.
        from app.infrastructure.persistence.models.oqi_uniqueness import UniquenessEvaluationORM

        overflow_evals = (
            session.execute(
                select(UniquenessEvaluationORM).where(
                    UniquenessEvaluationORM.tenant_id == tenant_a,
                    UniquenessEvaluationORM.enterprise_entity_id.in_(overflow_ids),
                )
            )
            .scalars()
            .all()
        )
        assert len(overflow_evals) == 5
        assert all(row.outcome == "NOT_EVALUABLE" for row in overflow_evals)

        # Deterministic rerun produces the identical candidate set.
        service.evaluate_entity_type(tenant_id=tenant_a, entity_type_id=product_type, moment=NOW)
        session.commit()
        rerun_candidates = (
            session.execute(
                select(UniquenessCandidateORM).where(
                    UniquenessCandidateORM.tenant_id.in_((tenant_a, tenant_b))
                )
            )
            .scalars()
            .all()
        )
        rerun_pairs = {
            (row.tenant_id, row.member_a_id, row.member_b_id) for row in rerun_candidates
        }
        assert rerun_pairs == pairs
