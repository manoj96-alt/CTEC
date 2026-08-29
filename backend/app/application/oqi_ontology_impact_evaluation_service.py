"""CDD-042: orchestration -- load Finding via the Finding-family adapter,
resolve direct impact via governed entity resolution, run the single
recursive-CTE propagation statement, derive the deterministic outcome,
persist the immutable ledger, and update the mutable current-impact
projection. OQI4 owns its own transaction boundary and never mutates the
underlying OQI1/OQI2/OQI3 Finding (CDD-042 §13)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.oqi_ontology_impact.evaluation import (
    CurrentImpactStatus,
    CurrentOntologyImpact,
    FindingFamily,
    ImpactBasis,
    ImpactClass,
    ImpactOutcome,
    OntologyElementType,
    OntologyImpactEvaluation,
    OntologyImpactObservation,
    OntologyImpactPath,
    compute_traversed_state_digest,
    derive_current_ontology_impact_id,
    derive_ontology_impact_evaluation_id,
)
from app.infrastructure.persistence.oqi_ontology_impact_evaluation_repository import (
    MAX_RETAINED_PATHS_PER_ELEMENT,
    OqiOntologyImpactEvaluationRepository,
    PropagatedPathCandidate,
)


@dataclass(frozen=True, slots=True)
class _RetainedElementPaths:
    element_id: UUID
    depth: int
    retained_paths: tuple[PropagatedPathCandidate, ...]


def _deduplicate_and_cap_paths(
    candidates: tuple[PropagatedPathCandidate, ...],
) -> tuple[_RetainedElementPaths, ...]:
    """CDD-042 §9: one current-impact row per impacted element regardless
    of path count; path evidence deduplicated by node-set (two paths that
    visit the identical set of intermediate entities are the same proof)
    and capped at the shortest 3 distinct paths per element. Fully
    deterministic post-processing of an already-snapshotted result set --
    performing this in Python does not reopen the one-statement snapshot
    invariant, since no further database read occurs here."""
    by_element: dict[UUID, list[PropagatedPathCandidate]] = {}
    for candidate in candidates:
        by_element.setdefault(candidate.entity_id, []).append(candidate)

    result: list[_RetainedElementPaths] = []
    for element_id, element_candidates in sorted(by_element.items(), key=lambda pair: str(pair[0])):
        seen_node_sets: set[frozenset[UUID]] = set()
        deduped: list[PropagatedPathCandidate] = []
        # Deterministic ordering: shortest depth first, then canonical
        # relationship-id sequence -- database row order never matters.
        for candidate in sorted(
            element_candidates,
            key=lambda c: (c.depth, tuple(str(r) for r in c.relationship_ids)),
        ):
            node_set = frozenset(candidate.relationship_ids)
            if node_set in seen_node_sets:
                continue
            seen_node_sets.add(node_set)
            deduped.append(candidate)
        retained = tuple(deduped[:MAX_RETAINED_PATHS_PER_ELEMENT])
        result.append(
            _RetainedElementPaths(
                element_id=element_id,
                depth=min(c.depth for c in retained),
                retained_paths=retained,
            )
        )
    return tuple(result)


class OqiOntologyImpactEvaluationService:
    def __init__(
        self,
        repository: OqiOntologyImpactEvaluationRepository,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._clock = clock

    def evaluate_current_state(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> OntologyImpactEvaluation | None:
        """CDD-042 §12 (Finding OPEN case). Returns the persisted
        (possibly replayed) immutable Evaluation, or `None` only if a
        genuinely new logical evaluation happened to be a no-op replay of
        an already-persisted one -- callers needing the ledger row can
        always re-fetch by the deterministic evaluation_id."""
        subject = self._repository.resolve_finding_subject(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )
        direct = self._repository.resolve_direct_impact(
            tenant_id=tenant_id, source_object_ids=subject.source_object_ids
        )

        observations: list[OntologyImpactObservation] = []
        paths: list[OntologyImpactPath] = []
        traversed_relationships: list[tuple[UUID, int]] = []
        applied_policies: dict[UUID, int] = {}

        if direct.outcome is ImpactOutcome.IMPACTED:
            assert direct.entity_id is not None
            observations.append(
                OntologyImpactObservation(
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=direct.entity_id,
                    impact_kind=ImpactClass.DIRECT,
                    basis=ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE,
                    depth=0,
                )
            )
            candidates = self._repository.traverse_propagation(
                tenant_id=tenant_id, direct_entity_id=direct.entity_id
            )
            for element in _deduplicate_and_cap_paths(candidates):
                observations.append(
                    OntologyImpactObservation(
                        ontology_element_type=OntologyElementType.ENTITY,
                        ontology_element_id=element.element_id,
                        impact_kind=ImpactClass.PROPAGATED,
                        basis=ImpactBasis.GOVERNED_RELATIONSHIP_PROPAGATION,
                        depth=element.depth,
                    )
                )
                for path_index, candidate in enumerate(element.retained_paths):
                    for hop_index, (rel_id, policy_id, policy_version, direction) in enumerate(
                        zip(
                            candidate.relationship_ids,
                            candidate.policy_ids,
                            candidate.policy_versions,
                            candidate.directions,
                            strict=True,
                        )
                    ):
                        paths.append(
                            OntologyImpactPath(
                                ontology_element_id=element.element_id,
                                path_ordinal=path_index * 100 + hop_index,
                                institutional_relationship_id=rel_id,
                                direction=direction,
                                policy_id=policy_id,
                                policy_version_number=policy_version,
                            )
                        )
                        traversed_relationships.append((rel_id, 1))
                        applied_policies[policy_id] = policy_version

        digest = compute_traversed_state_digest(
            resolution_record_id=direct.resolution_record_id,
            resolution_outcome=direct.outcome.value,
            traversed_relationships=tuple(traversed_relationships),
            applied_policies=tuple(applied_policies.items()),
        )
        evaluation_id = derive_ontology_impact_evaluation_id(
            tenant_id=tenant_id,
            finding_family=finding_family,
            finding_id=finding_id,
            finding_state_revision=subject.finding_state_revision,
            traversed_state_digest=digest,
        )
        evaluation = OntologyImpactEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            finding_family=finding_family,
            finding_id=finding_id,
            finding_state_revision=subject.finding_state_revision,
            outcome=direct.outcome,
            resolution_record_id=direct.resolution_record_id,
            traversed_state_digest=digest,
            evaluated_at=self._clock(),
            observations=tuple(observations),
            paths=tuple(paths),
        )
        newly_inserted = self._repository.insert_evaluation_idempotent(evaluation)
        if newly_inserted:
            self._apply_current_projection(evaluation)
        return evaluation

    def evaluate_historical(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> OntologyImpactEvaluation | None:
        """CDD-042: HISTORICAL evaluation persists the same immutable
        ledger shape but never touches `current_ontology_impacts` --
        mirroring OQI1/2/3's own HISTORICAL/CURRENT_STATE firewall
        exactly."""
        subject = self._repository.resolve_finding_subject(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        )
        direct = self._repository.resolve_direct_impact(
            tenant_id=tenant_id, source_object_ids=subject.source_object_ids
        )
        observations: list[OntologyImpactObservation] = []
        if direct.outcome is ImpactOutcome.IMPACTED:
            assert direct.entity_id is not None
            observations.append(
                OntologyImpactObservation(
                    ontology_element_type=OntologyElementType.ENTITY,
                    ontology_element_id=direct.entity_id,
                    impact_kind=ImpactClass.DIRECT,
                    basis=ImpactBasis.DIRECT_ENTITY_IDENTITY_LINEAGE,
                    depth=0,
                )
            )
        digest = compute_traversed_state_digest(
            resolution_record_id=direct.resolution_record_id,
            resolution_outcome=direct.outcome.value,
            traversed_relationships=(),
            applied_policies=(),
        )
        evaluation_id = derive_ontology_impact_evaluation_id(
            tenant_id=tenant_id,
            finding_family=finding_family,
            finding_id=finding_id,
            finding_state_revision=subject.finding_state_revision,
            traversed_state_digest=digest,
        )
        evaluation = OntologyImpactEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            finding_family=finding_family,
            finding_id=finding_id,
            finding_state_revision=subject.finding_state_revision,
            outcome=direct.outcome,
            resolution_record_id=direct.resolution_record_id,
            traversed_state_digest=digest,
            evaluated_at=self._clock(),
            observations=tuple(observations),
            paths=(),
        )
        self._repository.insert_evaluation_idempotent(evaluation)
        return evaluation

    def close_for_resolved_finding(
        self, *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
    ) -> None:
        """CDD-042 §12 (Finding RESOLVED case): prior ACTIVE current-impact
        rows transition to RESOLVED (never deleted); historical Evaluations/
        Observations/Paths are untouched."""
        now = self._clock()
        for current in self._repository.get_current_impacts_for_finding(
            tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
        ):
            if current.status is CurrentImpactStatus.ACTIVE:
                self._repository.upsert_current_impact(
                    CurrentOntologyImpact(
                        current_impact_id=current.current_impact_id,
                        tenant_id=current.tenant_id,
                        finding_family=current.finding_family,
                        finding_id=current.finding_id,
                        ontology_element_type=current.ontology_element_type,
                        ontology_element_id=current.ontology_element_id,
                        impact_kind=current.impact_kind,
                        status=CurrentImpactStatus.RESOLVED,
                        latest_evaluation_id=current.latest_evaluation_id,
                        first_seen_at=current.first_seen_at,
                        last_seen_at=now,
                    )
                )

    def _apply_current_projection(self, evaluation: OntologyImpactEvaluation) -> None:
        existing = self._repository.get_current_impacts_for_finding(
            tenant_id=evaluation.tenant_id,
            finding_family=evaluation.finding_family,
            finding_id=evaluation.finding_id,
        )
        existing_by_key = {
            (item.ontology_element_type, item.ontology_element_id, item.impact_kind): item
            for item in existing
        }

        if evaluation.outcome is ImpactOutcome.IMPACT_UNKNOWN:
            # "Absence of knowledge is not knowledge of absence": an
            # IMPACT_UNKNOWN result must never retract a previously-proven
            # ACTIVE impact. Leave the current projection untouched.
            return

        target_keys: set[tuple[OntologyElementType, UUID, ImpactClass]] = set()
        if evaluation.outcome is ImpactOutcome.IMPACTED:
            for observation in evaluation.observations:
                key = (
                    observation.ontology_element_type,
                    observation.ontology_element_id,
                    observation.impact_kind,
                )
                target_keys.add(key)
                current_impact_id = derive_current_ontology_impact_id(
                    tenant_id=evaluation.tenant_id,
                    finding_family=evaluation.finding_family,
                    finding_id=evaluation.finding_id,
                    ontology_element_type=observation.ontology_element_type,
                    ontology_element_id=observation.ontology_element_id,
                    impact_kind=observation.impact_kind,
                )
                previous = existing_by_key.get(key)
                self._repository.upsert_current_impact(
                    CurrentOntologyImpact(
                        current_impact_id=current_impact_id,
                        tenant_id=evaluation.tenant_id,
                        finding_family=evaluation.finding_family,
                        finding_id=evaluation.finding_id,
                        ontology_element_type=observation.ontology_element_type,
                        ontology_element_id=observation.ontology_element_id,
                        impact_kind=observation.impact_kind,
                        status=CurrentImpactStatus.ACTIVE,
                        latest_evaluation_id=evaluation.evaluation_id,
                        first_seen_at=(
                            previous.first_seen_at
                            if previous is not None
                            else evaluation.evaluated_at
                        ),
                        last_seen_at=evaluation.evaluated_at,
                    )
                )

        # NO_IMPACT, or IMPACTED with a shrunk element set: any previously
        # ACTIVE current impact no longer in the target set is a genuinely
        # proven non-impact and transitions to RESOLVED.
        for key, previous in existing_by_key.items():
            if key in target_keys or previous.status is not CurrentImpactStatus.ACTIVE:
                continue
            self._repository.upsert_current_impact(
                CurrentOntologyImpact(
                    current_impact_id=previous.current_impact_id,
                    tenant_id=previous.tenant_id,
                    finding_family=previous.finding_family,
                    finding_id=previous.finding_id,
                    ontology_element_type=previous.ontology_element_type,
                    ontology_element_id=previous.ontology_element_id,
                    impact_kind=previous.impact_kind,
                    status=CurrentImpactStatus.RESOLVED,
                    latest_evaluation_id=evaluation.evaluation_id,
                    first_seen_at=previous.first_seen_at,
                    last_seen_at=evaluation.evaluated_at,
                )
            )
