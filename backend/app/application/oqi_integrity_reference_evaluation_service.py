"""OQI-H4 Reference Integrity evaluation orchestration (CDD-050 §10.2, §12,
§16, PO-H4-04). Mirrors `OqiConformityEvaluationService`'s exact ordering
discipline: derive Finding-identity material -> acquire the
transaction-scoped advisory authority -> only then consult the persisted
`ResolutionOutcome` -> compare -> persist the immutable ledger row
idempotently -> mutate the Reference Finding only when the ledger insert was
genuinely new.

Reads a persisted, governed `ResolutionOutcome` -- never runs Entity
Resolution matching, never infers a target, never promotes `POSSIBLE` to a
decision (PO-H4-04, CDD-050 crown invariant `INTEGRITY EVALUATION != ENTITY
RESOLUTION`). `UNRESOLVED` -> `VIOLATED`/`ORPHAN_REFERENCE`; `POSSIBLE` and
"no outcome at all" -> `NOT_EVALUABLE`, zero row; `RESOLVED` -> `SATISFIED`
(a real, persisted row -- proves nothing about whether the corresponding
ontology relationship was ever materialized, `RESOLVED REFERENCE !=
MATERIALIZED RELATIONSHIP`)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.identity_resolution.model import ResolutionOutcome
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_integrity.reference import (
    ReferenceIntegrityEvaluation,
    ReferenceIntegrityFinding,
    apply_reference_finding_transition,
    derive_reference_evaluation_id,
    derive_reference_finding_id,
    reference_finding_identity_material,
)


class ReferenceEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_latest_resolution_record_for_source_object(
        self, *, tenant_id: str, source_object_id: UUID
    ) -> tuple[UUID, ResolutionOutcome] | None: ...

    def get_finding(self, finding_id: UUID) -> ReferenceIntegrityFinding | None: ...

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        relationship_requirement_id: UUID,
        source_object_id: UUID,
        resolution_record_id: UUID,
        resolution_outcome: str,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool: ...

    def upsert_finding(self, finding: ReferenceIntegrityFinding) -> None: ...


class OqiIntegrityReferenceEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: ReferenceEvaluationRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._clock = clock

    def evaluate_current_state(
        self, *, tenant_id: str, source_object_id: UUID, relationship_requirement_id: UUID
    ) -> ReferenceIntegrityEvaluation | None:
        horizon = self._clock()
        identity_material = reference_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
        )
        # CDD-039 §24-§25 precedent: authority MUST be acquired before
        # resolution-state selection.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        latest = self._evaluation_repository.get_latest_resolution_record_for_source_object(
            tenant_id=tenant_id, source_object_id=source_object_id
        )
        if latest is None:
            # No ER outcome exists at all -- NOT_EVALUABLE, zero row
            # (PO-H4-04).
            return None
        resolution_record_id, resolution_outcome = latest

        if resolution_outcome is ResolutionOutcome.POSSIBLE:
            # Ambiguous -- NOT_EVALUABLE, zero row. Never orphan.
            return None
        if resolution_outcome not in (ResolutionOutcome.RESOLVED, ResolutionOutcome.UNRESOLVED):
            # Any other/unexpected persisted outcome value fails closed
            # identically to POSSIBLE -- never guessed at.
            return None

        outcome = (
            EvaluationOutcome.SATISFIED
            if resolution_outcome is ResolutionOutcome.RESOLVED
            else EvaluationOutcome.VIOLATED
        )

        finding_id = derive_reference_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)
        next_finding = apply_reference_finding_transition(
            existing=existing_finding,
            outcome=outcome,
            evaluation_horizon=horizon,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
        )

        evaluation_id = derive_reference_evaluation_id(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
            resolution_record_id=resolution_record_id,
            evaluation_horizon=horizon,
        )
        evaluation = ReferenceIntegrityEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
            resolution_record_id=resolution_record_id,
            resolution_outcome=resolution_outcome,
            outcome=outcome,
            evaluation_horizon=horizon,
            evaluated_on=self._clock(),
        )

        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            source_object_id=source_object_id,
            resolution_record_id=resolution_record_id,
            resolution_outcome=resolution_outcome.value,
            outcome=outcome.value,
            evaluation_horizon=horizon,
            evaluated_on=evaluation.evaluated_on,
        )
        if newly_inserted and next_finding is not None:
            self._evaluation_repository.upsert_finding(next_finding)
        return evaluation
