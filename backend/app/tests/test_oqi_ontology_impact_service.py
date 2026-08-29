"""CDD-042 fake-repo orchestration tests: outcome-to-projection lifecycle,
IMPACT_UNKNOWN/NO_IMPACT firewalls, replay idempotency, and the compound-
propagation dedup/cap logic. Real per-Finding-family adapter resolution and
the recursive-CTE traversal itself are proven against real PostgreSQL in
`test_oqi_ontology_impact_postgres.py`. Artifact Authorization §2 row 11."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.application.oqi_ontology_impact_evaluation_service import (
    OqiOntologyImpactEvaluationService,
    _deduplicate_and_cap_paths,
)
from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    CurrentOntologyImpact,
    FindingFamily,
    ImpactOutcome,
    OntologyImpactEvaluation,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    DirectImpactResult,
    PropagatedPathCandidate,
    ResolvedFindingSubject,
)

TENANT = "tenant-a"


@dataclass
class _FakeRepository:
    subject: ResolvedFindingSubject
    direct: DirectImpactResult
    propagation: tuple[PropagatedPathCandidate, ...] = ()
    evaluations: dict[UUID, OntologyImpactEvaluation] = field(default_factory=dict)
    current_impacts: dict[UUID, CurrentOntologyImpact] = field(default_factory=dict)
    force_replay: bool = False

    def resolve_finding_subject(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> ResolvedFindingSubject:
        return self.subject

    def resolve_direct_impact(
        self, *, tenant_id: str, source_object_ids: tuple[UUID, ...]
    ) -> DirectImpactResult:
        return self.direct

    def traverse_propagation(
        self,
        *,
        tenant_id: str,
        direct_entity_id: UUID,
        _test_only_delay_seconds: float | None = None,
    ) -> tuple[PropagatedPathCandidate, ...]:
        return self.propagation

    def insert_evaluation_idempotent(self, evaluation: OntologyImpactEvaluation) -> bool:
        if self.force_replay or evaluation.evaluation_id in self.evaluations:
            return False
        self.evaluations[evaluation.evaluation_id] = evaluation
        return True

    def get_current_impacts_for_finding(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> tuple[CurrentOntologyImpact, ...]:
        return tuple(
            item
            for item in self.current_impacts.values()
            if item.tenant_id == tenant_id
            and item.finding_family == finding_family
            and item.finding_id == finding_id
        )

    def upsert_current_impact(self, current_impact: CurrentOntologyImpact) -> None:
        self.current_impacts[current_impact.current_impact_id] = current_impact


def _clock() -> datetime:
    return datetime.now(UTC)


def _subject(*, revision: int = 1) -> ResolvedFindingSubject:
    return ResolvedFindingSubject(
        finding_state_revision=revision,
        source_object_ids=(uuid4(),),
        source_record_references=("REC-1",),
    )


class TestImpactedLifecycle:
    def test_impacted_creates_active_current_impact(self) -> None:
        entity_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()

        evaluation = service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )

        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.IMPACTED
        current = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert len(current) == 1
        assert current[0].status is CurrentImpactStatus.ACTIVE
        assert current[0].ontology_element_id == entity_id

    def test_replay_does_not_double_apply_projection(self) -> None:
        entity_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()

        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        first_seen = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )[0].first_seen_at

        # Same logical inputs -> same deterministic Evaluation ID -> the
        # fake repository's own natural-key dedup makes this a no-op
        # replay, exactly mirroring the real parent-gated insert.
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        after_replay = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert len(after_replay) == 1
        assert after_replay[0].first_seen_at == first_seen


class TestImpactUnknownFirewall:
    def test_unknown_never_retracts_prior_active_impact(self) -> None:
        entity_id = uuid4()
        record_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(revision=1),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, record_id, entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert (
            repo.get_current_impacts_for_finding(
                tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
            )[0].status
            is CurrentImpactStatus.ACTIVE
        )

        # A later revision resolves lineage is now unknown (e.g. resolution
        # record became POSSIBLE). "Absence of knowledge is not knowledge
        # of absence": the prior proven ACTIVE impact must survive.
        repo.subject = _subject(revision=2)
        repo.direct = DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, record_id, None)
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        still_active = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert len(still_active) == 1
        assert still_active[0].status is CurrentImpactStatus.ACTIVE

    def test_unknown_produces_no_observations_and_persists(self) -> None:
        repo = _FakeRepository(
            subject=_subject(),
            direct=DirectImpactResult(ImpactOutcome.IMPACT_UNKNOWN, None, None),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        evaluation = service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=uuid4()
        )
        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.IMPACT_UNKNOWN
        assert evaluation.observations == ()


class TestNoImpactFirewall:
    def test_no_impact_resolves_prior_active_impact(self) -> None:
        entity_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(revision=1),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )

        # A positive proof of non-impact (e.g. resolution record became
        # UNRESOLVED/BLOCKED_CONFLICT) -- unlike IMPACT_UNKNOWN, this is a
        # genuine governed fact and must resolve the prior current impact.
        repo.subject = _subject(revision=2)
        repo.direct = DirectImpactResult(ImpactOutcome.NO_IMPACT, uuid4(), None)
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        current = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert len(current) == 1
        assert current[0].status is CurrentImpactStatus.RESOLVED


class TestImpactSetShrinkAndExpansion:
    def test_shrink_resolves_dropped_element_keeps_remaining_active(self) -> None:
        entity_a, entity_b = uuid4(), uuid4()
        repo = _FakeRepository(
            subject=_subject(revision=1),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_a),
            propagation=(
                PropagatedPathCandidate(
                    entity_id=entity_b,
                    depth=1,
                    relationship_ids=(uuid4(),),
                    policy_ids=(uuid4(),),
                    policy_versions=(1,),
                    directions=("FORWARD",),
                ),
            ),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert (
            len(
                repo.get_current_impacts_for_finding(
                    tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
                )
            )
            == 2
        )

        # Policy/ontology change removes the propagated element.
        repo.subject = _subject(revision=2)
        repo.propagation = ()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        current = {
            item.ontology_element_id: item
            for item in repo.get_current_impacts_for_finding(
                tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
            )
        }
        assert current[entity_a].status is CurrentImpactStatus.ACTIVE
        assert current[entity_b].status is CurrentImpactStatus.RESOLVED

    def test_expansion_adds_new_active_element(self) -> None:
        entity_a, entity_b = uuid4(), uuid4()
        repo = _FakeRepository(
            subject=_subject(revision=1),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_a),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )

        repo.subject = _subject(revision=2)
        repo.propagation = (
            PropagatedPathCandidate(
                entity_id=entity_b,
                depth=1,
                relationship_ids=(uuid4(),),
                policy_ids=(uuid4(),),
                policy_versions=(1,),
                directions=("FORWARD",),
            ),
        )
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        current = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert {item.status for item in current} == {CurrentImpactStatus.ACTIVE}
        assert len(current) == 2


class TestFindingResolvedClosure:
    def test_close_resolves_all_active_impacts(self) -> None:
        entity_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        service.evaluate_current_state(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        service.close_for_resolved_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        current = repo.get_current_impacts_for_finding(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert all(item.status is CurrentImpactStatus.RESOLVED for item in current)


class TestHistoricalFirewall:
    def test_historical_never_touches_current_projection(self) -> None:
        entity_id = uuid4()
        repo = _FakeRepository(
            subject=_subject(),
            direct=DirectImpactResult(ImpactOutcome.IMPACTED, uuid4(), entity_id),
        )
        service = OqiOntologyImpactEvaluationService(repo, clock=_clock)
        finding_id = uuid4()
        evaluation = service.evaluate_historical(
            tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
        )
        assert evaluation is not None
        assert evaluation.outcome is ImpactOutcome.IMPACTED
        assert (
            repo.get_current_impacts_for_finding(
                tenant_id=TENANT, finding_family=FindingFamily.OQI1, finding_id=finding_id
            )
            == ()
        )


class TestPathDeduplicationAndCap:
    def test_diamond_produces_two_distinct_paths(self) -> None:
        target = uuid4()
        candidates = (
            PropagatedPathCandidate(
                entity_id=target,
                depth=2,
                relationship_ids=(uuid4(), uuid4()),
                policy_ids=(uuid4(), uuid4()),
                policy_versions=(1, 1),
                directions=("FORWARD", "FORWARD"),
            ),
            PropagatedPathCandidate(
                entity_id=target,
                depth=2,
                relationship_ids=(uuid4(), uuid4()),
                policy_ids=(uuid4(), uuid4()),
                policy_versions=(1, 1),
                directions=("FORWARD", "FORWARD"),
            ),
        )
        result = _deduplicate_and_cap_paths(candidates)
        assert len(result) == 1
        assert len(result[0].retained_paths) == 2

    def test_exact_duplicate_ordered_path_deduplicates_to_one(self) -> None:
        """CDD-042 §9 (Ordered Relationship-Instance Path clarification):
        the exact same ordered relationship-instance sequence discovered
        twice by query mechanics must dedupe to one path proof."""
        target = uuid4()
        rel_a, rel_b = uuid4(), uuid4()
        policy = uuid4()

        def make() -> PropagatedPathCandidate:
            return PropagatedPathCandidate(
                entity_id=target,
                depth=2,
                relationship_ids=(rel_a, rel_b),
                policy_ids=(policy, policy),
                policy_versions=(1, 1),
                directions=("FORWARD", "FORWARD"),
            )

        result = _deduplicate_and_cap_paths((make(), make()))
        assert len(result) == 1
        assert len(result[0].retained_paths) == 1

    def test_same_edges_different_order_are_distinct_paths(self) -> None:
        """CDD-042 §9 (Ordered Relationship-Instance Path clarification):
        path identity is order-sensitive. Two candidates sharing the exact
        same relationship-instance membership but traversed in a different
        order are distinct proofs, not the same proof -- this is precisely
        what distinguishes an ordered relationship-instance sequence from
        an unordered edge-set (or a literal node-set)."""
        target = uuid4()
        rel_a, rel_b = uuid4(), uuid4()
        policy = uuid4()
        forward = PropagatedPathCandidate(
            entity_id=target,
            depth=2,
            relationship_ids=(rel_a, rel_b),
            policy_ids=(policy, policy),
            policy_versions=(1, 1),
            directions=("FORWARD", "FORWARD"),
        )
        reversed_order = PropagatedPathCandidate(
            entity_id=target,
            depth=2,
            relationship_ids=(rel_b, rel_a),
            policy_ids=(policy, policy),
            policy_versions=(1, 1),
            directions=("FORWARD", "FORWARD"),
        )
        result = _deduplicate_and_cap_paths((forward, reversed_order))
        assert len(result) == 1
        assert len(result[0].retained_paths) == 2

    def test_more_than_three_paths_capped_deterministically(self) -> None:
        target = uuid4()
        candidates = tuple(
            PropagatedPathCandidate(
                entity_id=target,
                depth=1,
                relationship_ids=(uuid4(),),
                policy_ids=(uuid4(),),
                policy_versions=(1,),
                directions=("FORWARD",),
            )
            for _ in range(5)
        )
        result = _deduplicate_and_cap_paths(candidates)
        assert len(result) == 1
        assert len(result[0].retained_paths) == 3

        # Re-running on the identical (reordered) candidate set must retain
        # the same 3 -- deterministic, not incidental input order.
        reordered = tuple(reversed(candidates))
        result_2 = _deduplicate_and_cap_paths(reordered)
        assert {
            tuple(str(r) for r in path.relationship_ids) for path in result[0].retained_paths
        } == {tuple(str(r) for r in path.relationship_ids) for path in result_2[0].retained_paths}

    def test_element_depth_is_shortest_retained(self) -> None:
        target = uuid4()
        candidates = (
            PropagatedPathCandidate(
                entity_id=target,
                depth=3,
                relationship_ids=(uuid4(), uuid4(), uuid4()),
                policy_ids=(uuid4(), uuid4(), uuid4()),
                policy_versions=(1, 1, 1),
                directions=("FORWARD", "FORWARD", "FORWARD"),
            ),
            PropagatedPathCandidate(
                entity_id=target,
                depth=1,
                relationship_ids=(uuid4(),),
                policy_ids=(uuid4(),),
                policy_versions=(1,),
                directions=("FORWARD",),
            ),
        )
        result = _deduplicate_and_cap_paths(candidates)
        assert result[0].depth == 1


class TestFindingMutationFirewall:
    def test_service_never_imports_finding_lifecycle_code(self) -> None:
        """CDD-042 §13/§16: OQI4 must never mutate the underlying Finding.
        Proven by absence -- the service module imports nothing from any
        OQI1/OQI2/OQI3 Finding-lifecycle module."""
        import inspect

        from app.application import oqi_ontology_impact_evaluation_service as module

        source = inspect.getsource(module)
        for forbidden in (
            "apply_transition",
            "upsert_finding",
            "acquire_evaluation_authority",
            "apply_business_rule_finding_transition",
        ):
            assert forbidden not in source, f"service module references {forbidden!r}"


class TestNoTruthSelectionFirewall:
    def test_service_never_selects_a_canonical_value(self) -> None:
        """Firewall by absence: no majority/authority/trust vocabulary
        anywhere in the orchestration module."""
        import inspect

        from app.application import oqi_ontology_impact_evaluation_service as module

        source = inspect.getsource(module).lower()
        for forbidden in (
            "majority",
            "canonical_value",
            "trust_score",
            "criticality",
            "severity",
            "confidence_score",
        ):
            assert forbidden not in source, f"service module references {forbidden!r}"
