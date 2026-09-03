"""OQI-H4 Structural Integrity evaluation orchestration (CDD-050 §10.1,
§12, §16). Mirrors `OqiConformityEvaluationService`'s exact ordering
discipline: resolve the governed requirement/obligation -> resolve the
ACTIVE cardinality definition (`NOT_EVALUABLE`, zero row, if none exists --
CDD-050 §9) -> acquire the transaction-scoped advisory authority -> select
qualifying relationships -> count distinct qualifying targets -> compare
against governed cardinality -> persist the immutable ledger row (plus its
qualifying-relationship provenance links) idempotently -> mutate the
Structural Finding only when the ledger insert was genuinely new.

`CONDITIONAL` obligation is `NOT_EVALUABLE` (CDD-050 §9 -- H4 v1 has no
governed conditional-applicability engine). Outcome precedence (CDD-050
§10.1, §12): a zero qualifying-target count against a positive minimum is
`MISSING_REQUIRED_RELATIONSHIP`; any other cardinality violation (a
nonzero-but-insufficient count, or a count exceeding the governed maximum)
is `RELATIONSHIP_CARDINALITY_VIOLATION` -- never both for one evaluation."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_integrity.requirement import IntegrityRelationshipCardinality
from app.domain.oqi_integrity.structural import (
    IntegrityFindingType,
    StructuralIntegrityEvaluation,
    StructuralIntegrityFinding,
    apply_structural_finding_transition,
    derive_structural_evaluation_id,
    derive_structural_finding_id,
    structural_finding_identity_material,
)
from app.domain.shared.exceptions import DomainException

_CONDITIONAL_OBLIGATION = "CONDITIONAL"


class OqiIntegrityStructuralEvaluationError(DomainException):
    """Base exception for Structural Integrity evaluation-orchestration
    failures."""


class OqiIntegrityUnknownRequirementError(OqiIntegrityStructuralEvaluationError):
    """Raised if the caller-supplied `relationship_requirement_id` does not
    resolve to a real, governed `RelationshipRequirement` -- a genuine
    misconfiguration, never a runtime evaluability question (governed data
    is expected to always resolve)."""


class StructuralEvaluationRepository(Protocol):
    def acquire_evaluation_authority(self, identity: str) -> None: ...

    def get_relationship_requirement_info(
        self, relationship_requirement_id: UUID
    ) -> tuple[UUID, UUID, str] | None: ...

    def select_qualifying_relationships(
        self,
        *,
        tenant_id: str,
        enterprise_entity_id: UUID,
        relationship_type_id: UUID,
        target_entity_type_id: UUID,
    ) -> tuple[tuple[UUID, UUID], ...]: ...

    def get_finding(self, finding_id: UUID) -> StructuralIntegrityFinding | None: ...

    def insert_evaluation_idempotent(
        self,
        *,
        evaluation_id: UUID,
        tenant_id: str,
        relationship_requirement_id: UUID,
        integrity_relationship_cardinality_id: UUID,
        enterprise_entity_id: UUID,
        qualifying_relationships: tuple[tuple[UUID, UUID], ...],
        qualifying_target_count: int,
        outcome: str,
        evaluation_horizon: datetime,
        evaluated_on: datetime,
    ) -> bool: ...

    def upsert_finding(self, finding: StructuralIntegrityFinding) -> None: ...


class CardinalityLookup(Protocol):
    def get_active_cardinality_for_requirement(
        self, *, relationship_requirement_id: UUID
    ) -> IntegrityRelationshipCardinality | None: ...


class OqiIntegrityStructuralEvaluationService:
    def __init__(
        self,
        *,
        evaluation_repository: StructuralEvaluationRepository,
        cardinality_lookup: CardinalityLookup,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._evaluation_repository = evaluation_repository
        self._cardinality_lookup = cardinality_lookup
        self._clock = clock

    def evaluate_current_state(
        self, *, tenant_id: str, enterprise_entity_id: UUID, relationship_requirement_id: UUID
    ) -> StructuralIntegrityEvaluation | None:
        requirement_info = self._evaluation_repository.get_relationship_requirement_info(
            relationship_requirement_id
        )
        if requirement_info is None:
            raise OqiIntegrityUnknownRequirementError(
                f"relationship_requirement_id {relationship_requirement_id!r} does not resolve "
                "to a real, governed RelationshipRequirement"
            )
        relationship_type_id, target_entity_type_id, obligation = requirement_info

        if obligation == _CONDITIONAL_OBLIGATION:
            # CDD-050 §9: H4 v1 has no governed conditional-applicability
            # engine -- NOT_EVALUABLE, zero row, never silently REQUIRED or
            # OPTIONAL.
            return None

        cardinality = self._cardinality_lookup.get_active_cardinality_for_requirement(
            relationship_requirement_id=relationship_requirement_id
        )
        if cardinality is None:
            # CDD-050 §9 (Option B, frozen): absence of H4 configuration is
            # NOT_EVALUABLE, never fabricated certainty from bare Obligation
            # alone.
            return None

        horizon = self._clock()
        identity_material = structural_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
        )
        # CDD-039 §24-§25 precedent: authority MUST be acquired before
        # evidence/graph-state selection.
        self._evaluation_repository.acquire_evaluation_authority(identity_material)

        qualifying_relationships = self._evaluation_repository.select_qualifying_relationships(
            tenant_id=tenant_id,
            enterprise_entity_id=enterprise_entity_id,
            relationship_type_id=relationship_type_id,
            target_entity_type_id=target_entity_type_id,
        )
        # PO-H4-01: cardinality counts DISTINCT qualifying target entities,
        # never raw relationship-row count.
        distinct_target_ids = tuple(
            sorted({target_id for _relationship_id, target_id in qualifying_relationships}, key=str)
        )
        qualifying_target_count = len(distinct_target_ids)

        finding_type: IntegrityFindingType | None
        if qualifying_target_count == 0 and cardinality.min_cardinality > 0:
            outcome = EvaluationOutcome.VIOLATED
            finding_type = IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP
        elif (
            qualifying_target_count > 0
            and qualifying_target_count < cardinality.min_cardinality
            or (
                cardinality.max_cardinality is not None
                and qualifying_target_count > cardinality.max_cardinality
            )
        ):
            outcome = EvaluationOutcome.VIOLATED
            finding_type = IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION
        else:
            outcome = EvaluationOutcome.SATISFIED
            finding_type = None

        finding_id = derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
        )
        existing_finding = self._evaluation_repository.get_finding(finding_id)
        next_finding = apply_structural_finding_transition(
            existing=existing_finding,
            outcome=outcome,
            # finding_type is only consulted when a Finding is opened/kept
            # OPEN; apply_structural_finding_transition ignores it for the
            # SATISFIED/no-existing-Finding case.
            finding_type=finding_type or IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
            evaluation_horizon=horizon,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
        )

        evaluation_id = derive_structural_evaluation_id(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
            integrity_relationship_cardinality_id=(
                cardinality.integrity_relationship_cardinality_id
            ),
            evaluation_horizon=horizon,
            qualifying_target_ids=distinct_target_ids,
        )
        evaluation = StructuralIntegrityEvaluation(
            evaluation_id=evaluation_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            integrity_relationship_cardinality_id=(
                cardinality.integrity_relationship_cardinality_id
            ),
            enterprise_entity_id=enterprise_entity_id,
            qualifying_target_ids=distinct_target_ids,
            outcome=outcome,
            evaluation_horizon=horizon,
            evaluated_on=self._clock(),
        )

        # CDD-039 §20 precedent: idempotent replay -- a byte-identical
        # logical replay is a no-op, never a duplicate row and never a
        # second Finding mutation.
        newly_inserted = self._evaluation_repository.insert_evaluation_idempotent(
            evaluation_id=evaluation.evaluation_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            integrity_relationship_cardinality_id=(
                cardinality.integrity_relationship_cardinality_id
            ),
            enterprise_entity_id=enterprise_entity_id,
            qualifying_relationships=qualifying_relationships,
            qualifying_target_count=qualifying_target_count,
            outcome=outcome.value,
            evaluation_horizon=horizon,
            evaluated_on=evaluation.evaluated_on,
        )
        if newly_inserted and next_finding is not None:
            self._evaluation_repository.upsert_finding(next_finding)
        return evaluation
