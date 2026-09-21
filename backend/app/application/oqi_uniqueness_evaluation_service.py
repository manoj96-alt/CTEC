"""OQI-H6 Governed EnterpriseEntity Uniqueness evaluation orchestration
(CDD-084 §15-§29). `evaluate_entity_type` is the single entry point: resolve
the governed `ACTIVE` `UniquenessPolicy` for `(tenant_id, entity_type_id)`
(zero rows, no evaluation at all, if none exists -- CDD-084 §20's no-policy
case) -> fetch the bounded, already-tenant-and-type-scoped population
(CDD-084 §16) -> bucket it by `canonical_name(enterprise_entity_name)`
equality (the fixed, non-configurable H6 v1 blocking key, CDD-084 §16 --
`NORMALIZED FOR MATCHING ≠ GOVERNED CANONICAL`) -> for each bucket, either
fail closed with a persisted `NOT_EVALUABLE`/`BUCKET_EXCEEDED_CAP`
evaluation row per member if the bucket exceeds `bucket_max_size` (CDD-084
§17 -- never truncate, never sample, never fall back to a wider scan), or
generate every within-bucket canonical pair as an idempotent candidate
(CDD-084 §18, §23) and open/reopen/reaffirm its Finding UNLESS the
candidate's latest adjudication is `REJECT_NOT_DUPLICATE` (CDD-084 §21-§22)
-> persist one evaluation ledger row per entity, `SATISFIED` if it has zero
currently-qualifying (non-rejected) candidates, `VIOLATED` if it has at
least one (CDD-084 §20) -> reconcile every previously-OPEN Finding for this
entity_type whose pair no longer appears in this run's qualifying set,
closing it (CDD-084 §25's "fresh re-evaluation demonstrates the duplicate
condition no longer exists" path).

Candidate generation is bounded by construction: the only population ever
compared is one `(tenant_id, entity_type_id)` scope's own bucket contents,
never the whole tenant's entity graph and never a cross-type population
(CDD-084 §13-§14, §16-§17) -- there is no code path in this module capable
of an unbounded, tenant-wide, all-pairs comparison."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from itertools import combinations
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.identity_resolution.normalization import canonical_name
from app.domain.oqi_uniqueness.candidate import (
    UniquenessAdjudication,
    UniquenessAdjudicationAction,
    UniquenessCandidate,
    canonicalize_pair,
)
from app.domain.oqi_uniqueness.evaluation import (
    UniquenessEvaluation,
    UniquenessFinding,
    UniquenessNotEvaluableReason,
    UniquenessOutcome,
    apply_uniqueness_adjudication_transition,
    apply_uniqueness_finding_transition,
    derive_uniqueness_evaluation_id,
    derive_uniqueness_finding_id,
    uniqueness_finding_identity_material,
)
from app.domain.oqi_uniqueness.policy import UniquenessPolicy
from app.domain.shared.exceptions import ValidationException


class UniquenessPolicyLookup(Protocol):
    def get_active_policy_for_entity_type(
        self, *, tenant_id: str, entity_type_id: UUID
    ) -> UniquenessPolicy | None: ...


class UniquenessCandidateRepository(Protocol):
    def acquire_candidate_authority(self, identity: str) -> None: ...

    def fetch_population(
        self, *, tenant_id: str, entity_type_id: UUID
    ) -> tuple[tuple[UUID, str], ...]: ...

    def insert_candidate_idempotent(
        self, candidate: UniquenessCandidate
    ) -> UniquenessCandidate: ...

    def get_candidate(
        self, *, tenant_id: str, candidate_id: UUID
    ) -> UniquenessCandidate | None: ...

    def insert_adjudication(self, adjudication: UniquenessAdjudication) -> None: ...

    def get_latest_adjudication(
        self, *, tenant_id: str, candidate_id: UUID
    ) -> UniquenessAdjudication | None: ...

    def get_latest_adjudication_for_pair(
        self, *, tenant_id: str, member_a_id: UUID, member_b_id: UUID
    ) -> tuple[UniquenessAdjudication, str] | None: ...


class UniquenessEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_finding(self, finding_id: UUID) -> UniquenessFinding | None: ...

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
    ) -> bool: ...

    def upsert_finding(self, finding: UniquenessFinding) -> None: ...

    def get_open_findings_for_entity_type(
        self, *, tenant_id: str, entity_ids: tuple[UUID, ...]
    ) -> tuple[UniquenessFinding, ...]: ...


class OqiUniquenessEvaluationService:
    def __init__(
        self,
        *,
        policy_lookup: UniquenessPolicyLookup,
        candidate_repository: UniquenessCandidateRepository,
        evaluation_repository: UniquenessEvaluationRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._policy_lookup = policy_lookup
        self._candidate_repository = candidate_repository
        self._evaluation_repository = evaluation_repository
        self._clock = clock

    def evaluate_entity_type(
        self, *, tenant_id: str, entity_type_id: UUID, moment: datetime | None = None
    ) -> tuple[UniquenessEvaluation, ...]:
        run_moment = self._clock() if moment is None else moment
        if run_moment.tzinfo is None:
            raise ValidationException("moment must include a timezone")

        policy = self._policy_lookup.get_active_policy_for_entity_type(
            tenant_id=tenant_id, entity_type_id=entity_type_id
        )
        if policy is None:
            # CDD-084 §20: no ACTIVE UniquenessPolicy for this entity_type
            # -- NOT_EVALUABLE, zero row, never a fabricated default.
            return ()

        population = self._candidate_repository.fetch_population(
            tenant_id=tenant_id, entity_type_id=entity_type_id
        )
        if not population:
            return ()

        buckets: dict[str, list[tuple[UUID, str]]] = {}
        for entity_id, name in population:
            buckets.setdefault(canonical_name(name), []).append((entity_id, name))

        evaluations: list[UniquenessEvaluation] = []
        qualifying_pairs_this_run: set[tuple[UUID, UUID]] = set()
        touched_entities: set[UUID] = {entity_id for entity_id, _ in population}

        for normalized_name, members in buckets.items():
            if len(members) > policy.bucket_max_size:
                # CDD-084 §17: fail closed -- never truncate, never sample,
                # never fall back to a wider scan.
                for entity_id, _ in members:
                    evaluations.append(
                        self._persist_evaluation(
                            tenant_id=tenant_id,
                            policy=policy,
                            entity_id=entity_id,
                            outcome=UniquenessOutcome.NOT_EVALUABLE,
                            not_evaluable_reason=UniquenessNotEvaluableReason.BUCKET_EXCEEDED_CAP,
                            candidate_count=0,
                            moment=run_moment,
                        )
                    )
                continue

            if len(members) == 1:
                entity_id, _ = members[0]
                evaluations.append(
                    self._persist_evaluation(
                        tenant_id=tenant_id,
                        policy=policy,
                        entity_id=entity_id,
                        outcome=UniquenessOutcome.SATISFIED,
                        not_evaluable_reason=None,
                        candidate_count=0,
                        moment=run_moment,
                    )
                )
                continue

            # Within-cap bucket with >=2 members: every pair is a
            # candidate-generation attempt (CDD-084 §18). No naive
            # tenant-wide all-pairs path exists -- this loop only ever
            # ranges over one bucket's own bounded membership.
            qualifying_count: dict[UUID, int] = {entity_id: 0 for entity_id, _ in members}
            for (a_id, _a_name), (b_id, _b_name) in combinations(members, 2):
                member_a_id, member_b_id = canonicalize_pair(a_id, b_id)
                identity_material = uniqueness_finding_identity_material(
                    tenant_id=tenant_id, member_a_id=member_a_id, member_b_id=member_b_id
                )
                self._candidate_repository.acquire_candidate_authority(identity_material)

                candidate = self._candidate_repository.insert_candidate_idempotent(
                    UniquenessCandidate(
                        candidate_id=uuid4(),
                        tenant_id=tenant_id,
                        member_a_id=member_a_id,
                        member_b_id=member_b_id,
                        policy_id=policy.policy_id,
                        policy_version=policy.version,
                        matched_normalized_name=normalized_name,
                        created_on=run_moment,
                    )
                )

                # CDD-084 §22: checked across EVERY policy version ever
                # generated for this canonical pair, not merely the current
                # version's own candidate row -- a candidate's identity
                # includes `policy_version` (§23), so a bare version bump
                # would otherwise always look like a "new" candidate,
                # silently bypassing a real, unchanged rejection every time
                # the policy is reversioned. Suppression applies only when
                # the REJECTED candidate's own matched name is identical to
                # THIS run's match -- a genuinely different normalized-name
                # match (the underlying names actually changed) is never
                # suppressed, exactly as CDD-084 §22 requires.
                latest_for_pair = self._candidate_repository.get_latest_adjudication_for_pair(
                    tenant_id=tenant_id, member_a_id=member_a_id, member_b_id=member_b_id
                )
                rejected = (
                    latest_for_pair is not None
                    and latest_for_pair[0].action
                    is UniquenessAdjudicationAction.REJECT_NOT_DUPLICATE
                    and latest_for_pair[1] == normalized_name
                )
                if rejected:
                    continue

                qualifying_count[member_a_id] += 1
                qualifying_count[member_b_id] += 1
                qualifying_pairs_this_run.add((member_a_id, member_b_id))

                existing_finding = self._evaluation_repository.get_finding(
                    derive_uniqueness_finding_id(
                        tenant_id=tenant_id, member_a_id=member_a_id, member_b_id=member_b_id
                    )
                )
                next_finding = apply_uniqueness_finding_transition(
                    existing=existing_finding,
                    candidate_qualifies=True,
                    candidate_id=candidate.candidate_id,
                    moment=run_moment,
                    tenant_id=tenant_id,
                    member_a_id=member_a_id,
                    member_b_id=member_b_id,
                )
                if next_finding is not None:
                    self._evaluation_repository.upsert_finding(next_finding)

            for entity_id, _ in members:
                count = qualifying_count[entity_id]
                evaluations.append(
                    self._persist_evaluation(
                        tenant_id=tenant_id,
                        policy=policy,
                        entity_id=entity_id,
                        outcome=(
                            UniquenessOutcome.VIOLATED
                            if count >= 1
                            else UniquenessOutcome.SATISFIED
                        ),
                        not_evaluable_reason=None,
                        candidate_count=count,
                        moment=run_moment,
                    )
                )

        # CDD-084 §25: reconcile every previously-OPEN Finding for this
        # entity_type whose pair no longer qualifies this run (e.g. one
        # member's name was independently corrected, moving it to a
        # different bucket) -- closes it via a genuine fresh re-evaluation,
        # never via policy change alone.
        for finding in self._evaluation_repository.get_open_findings_for_entity_type(
            tenant_id=tenant_id, entity_ids=tuple(touched_entities)
        ):
            pair = (finding.member_a_id, finding.member_b_id)
            if pair in qualifying_pairs_this_run:
                continue
            self._evaluation_repository.acquire_evaluation_authority(
                uniqueness_finding_identity_material(
                    tenant_id=tenant_id,
                    member_a_id=finding.member_a_id,
                    member_b_id=finding.member_b_id,
                )
            )
            closed = apply_uniqueness_finding_transition(
                existing=finding,
                candidate_qualifies=False,
                candidate_id=finding.candidate_id,
                moment=run_moment,
                tenant_id=tenant_id,
                member_a_id=finding.member_a_id,
                member_b_id=finding.member_b_id,
            )
            if closed is not None:
                self._evaluation_repository.upsert_finding(closed)

        return tuple(evaluations)

    def adjudicate(
        self,
        *,
        tenant_id: str,
        candidate_id: UUID,
        action: UniquenessAdjudicationAction,
        actor_id: str,
        rationale: str,
        moment: datetime | None = None,
    ) -> UniquenessAdjudication:
        """CDD-084 §21, §25, §28: a steward decision takes effect
        immediately -- never waiting for the next `evaluate_entity_type`
        sweep. `REJECT_NOT_DUPLICATE` closes the Finding now;
        `CONFIRM_DUPLICATE` records governed human evidence and leaves the
        Finding OPEN (`CONFIRMED DUPLICATE ≠ RESOLVED DUPLICATE
        REPRESENTATION`) -- neither action mutates any `EnterpriseEntity`
        or relationship (CDD-084 §2 PO-2, §28)."""
        run_moment = self._clock() if moment is None else moment
        if run_moment.tzinfo is None:
            raise ValidationException("moment must include a timezone")

        candidate = self._candidate_repository.get_candidate(
            tenant_id=tenant_id, candidate_id=candidate_id
        )
        if candidate is None:
            raise ValidationException(
                f"no UniquenessCandidate {candidate_id} for tenant {tenant_id!r}"
            )

        identity_material = uniqueness_finding_identity_material(
            tenant_id=tenant_id,
            member_a_id=candidate.member_a_id,
            member_b_id=candidate.member_b_id,
        )
        self._candidate_repository.acquire_candidate_authority(identity_material)

        adjudication = UniquenessAdjudication(
            adjudication_id=uuid4(),
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            action=action,
            actor_id=actor_id,
            rationale=rationale,
            decided_on=run_moment,
        )
        self._candidate_repository.insert_adjudication(adjudication)

        self._evaluation_repository.acquire_evaluation_authority(identity_material)
        finding_id = derive_uniqueness_finding_id(
            tenant_id=tenant_id,
            member_a_id=candidate.member_a_id,
            member_b_id=candidate.member_b_id,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)
        if existing_finding is not None:
            next_finding = apply_uniqueness_adjudication_transition(
                existing=existing_finding, action=action, moment=run_moment
            )
            self._evaluation_repository.upsert_finding(next_finding)

        return adjudication

    def _persist_evaluation(
        self,
        *,
        tenant_id: str,
        policy: UniquenessPolicy,
        entity_id: UUID,
        outcome: UniquenessOutcome,
        not_evaluable_reason: UniquenessNotEvaluableReason | None,
        candidate_count: int,
        moment: datetime,
    ) -> UniquenessEvaluation:
        self._evaluation_repository.acquire_evaluation_authority(
            f"UNIQUENESS_EVAL|{tenant_id}|{policy.policy_id}|{entity_id}"
        )
        evaluated_on = self._clock()
        evaluation_id = derive_uniqueness_evaluation_id(
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            enterprise_entity_id=entity_id,
            outcome=outcome,
            candidate_count=candidate_count,
            not_evaluable_reason=not_evaluable_reason,
        )
        evaluation = UniquenessEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            enterprise_entity_id=entity_id,
            outcome=outcome,
            not_evaluable_reason=not_evaluable_reason,
            candidate_count=candidate_count,
            evaluated_on=evaluated_on,
        )
        self._evaluation_repository.insert_evaluation_idempotent(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=tenant_id,
            policy_id=policy.policy_id,
            policy_version=policy.version,
            enterprise_entity_id=entity_id,
            outcome=outcome.value,
            not_evaluable_reason=(
                not_evaluable_reason.value if not_evaluable_reason is not None else None
            ),
            candidate_count=candidate_count,
            evaluated_on=evaluated_on,
        )
        return evaluation
