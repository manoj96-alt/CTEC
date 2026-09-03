"""OQI-H4 Structural Integrity (CDD-050 §10.1, §14-§16): evaluates one
`EnterpriseEntity` against one governed `RelationshipRequirement` under its
`ACTIVE` `IntegrityRelationshipCardinality` definition. Detects
`MISSING_REQUIRED_RELATIONSHIP` (zero qualifying targets where a minimum is
required) and `RELATIONSHIP_CARDINALITY_VIOLATION` (a qualifying-target count
below the governed minimum or above the governed maximum) -- never both for
one evaluation (CDD-050 §10.1 precedence).

Distinct OQI-family namespace (CDD-039 §20's own precedent, restated):
Finding/evaluation identity never collides with OQI1-6/H1-H3's own namespaces.

`IntegrityFindingType` is shared with `reference.py` (CDD-050 §14) -- a
single closed vocabulary spanning both Structural Finding types and
Reference Integrity's own `ORPHAN_REFERENCE`, even though no single physical
table ever carries all three values."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.shared.exceptions import ValidationException

#: CDD-050 §15: distinct from OQI_NAMESPACE, OQI_CROSS_SOURCE_NAMESPACE, and
#: every other governed OQI namespace -- no cross-family identity collision
#: is possible even adversarially.
OQI_INTEGRITY_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:integrity:v1")

_IDENTITY_ALGORITHM_VERSION = "OQI_INTEGRITY_STRUCTURAL_IDENTITY_V1"
_MAX_TENANT_ID_LENGTH = 200


class IntegrityFindingType(StrEnum):
    """CDD-050 §14: closed, exactly three. Shared across both Structural and
    Reference Integrity -- never a fourth type invented for symmetry."""

    MISSING_REQUIRED_RELATIONSHIP = "MISSING_REQUIRED_RELATIONSHIP"
    RELATIONSHIP_CARDINALITY_VIOLATION = "RELATIONSHIP_CARDINALITY_VIOLATION"
    ORPHAN_REFERENCE = "ORPHAN_REFERENCE"


class IntegrityFindingStatus(StrEnum):
    """Mirrors `QualityFindingStatus`'s exact closed shape (CDD-039 §27)."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to `app.domain.oqi.evaluation`'s own
    private helper, redefined locally per the established OQI2/OQI3
    per-family precedent of never importing another family's private
    symbols."""
    return f"{len(value.encode('utf-8'))}:{value}"


def structural_finding_identity_material(
    *, tenant_id: str, relationship_requirement_id: UUID, enterprise_entity_id: UUID
) -> str:
    """CDD-050 §15: the exact Finding-identity material, deliberately
    excluding the cardinality definition/version, min, max, evaluation
    horizon, and observed count -- a cardinality policy-version change never
    creates a duplicate current Finding for the same entity/requirement
    pair."""
    return (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(tenant_id)
        + _length_prefixed(str(relationship_requirement_id))
        + _length_prefixed(str(enterprise_entity_id))
    )


def derive_structural_finding_id(
    *, tenant_id: str, relationship_requirement_id: UUID, enterprise_entity_id: UUID
) -> UUID:
    return uuid5(
        OQI_INTEGRITY_NAMESPACE,
        structural_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
        ),
    )


def derive_structural_evaluation_id(
    *,
    tenant_id: str,
    relationship_requirement_id: UUID,
    enterprise_entity_id: UUID,
    integrity_relationship_cardinality_id: UUID,
    evaluation_horizon: datetime,
    qualifying_target_ids: tuple[UUID, ...],
) -> UUID:
    """CDD-050 §15: evaluation-row identity additionally folds in the
    consulted cardinality-definition version and the evaluation horizon plus
    a digest of the qualifying target set, so a repeated identical evaluation
    converges to the same row (idempotent replay) while a genuinely fresh
    evaluation (new horizon, or a changed graph state) always produces a new
    row -- mirroring `derive_evaluation_id`'s established discipline."""
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    target_digest = "|".join(sorted(str(target_id) for target_id in qualifying_target_ids))
    material = (
        structural_finding_identity_material(
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
        )
        + _length_prefixed(str(integrity_relationship_cardinality_id))
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
        + _length_prefixed(target_digest)
    )
    return uuid5(OQI_INTEGRITY_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class StructuralIntegrityEvaluation:
    """CDD-050 §12 table 2: the immutable, append-only Structural evaluation
    ledger record."""

    evaluation_id: UUID
    tenant_id: str
    relationship_requirement_id: UUID
    integrity_relationship_cardinality_id: UUID
    enterprise_entity_id: UUID
    qualifying_target_ids: tuple[UUID, ...]
    outcome: EvaluationOutcome
    evaluation_horizon: datetime
    evaluated_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.relationship_requirement_id, UUID):
            raise ValidationException("relationship_requirement_id must be a UUID")
        if not isinstance(self.integrity_relationship_cardinality_id, UUID):
            raise ValidationException("integrity_relationship_cardinality_id must be a UUID")
        if not isinstance(self.enterprise_entity_id, UUID):
            raise ValidationException("enterprise_entity_id must be a UUID")
        if not isinstance(self.qualifying_target_ids, tuple) or not all(
            isinstance(target_id, UUID) for target_id in self.qualifying_target_ids
        ):
            raise ValidationException("qualifying_target_ids must be a tuple of UUIDs")
        if len(set(self.qualifying_target_ids)) != len(self.qualifying_target_ids):
            raise ValidationException("qualifying_target_ids must not contain duplicates")
        if not isinstance(self.outcome, EvaluationOutcome):
            raise ValidationException("outcome must be an EvaluationOutcome")
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if self.evaluated_on is None or self.evaluated_on.tzinfo is None:
            raise ValidationException("evaluated_on must include a timezone")

        expected_id = derive_structural_evaluation_id(
            tenant_id=self.tenant_id,
            relationship_requirement_id=self.relationship_requirement_id,
            enterprise_entity_id=self.enterprise_entity_id,
            integrity_relationship_cardinality_id=self.integrity_relationship_cardinality_id,
            evaluation_horizon=self.evaluation_horizon,
            qualifying_target_ids=self.qualifying_target_ids,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class StructuralIntegrityFinding:
    finding_id: UUID
    tenant_id: str
    relationship_requirement_id: UUID
    enterprise_entity_id: UUID
    finding_type: IntegrityFindingType
    status: IntegrityFindingStatus
    state_revision: int
    first_seen_at: datetime
    last_seen_at: datetime
    last_evaluated_horizon: datetime
    occurrence_count: int
    reopen_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.relationship_requirement_id, UUID):
            raise ValidationException("relationship_requirement_id must be a UUID")
        if not isinstance(self.enterprise_entity_id, UUID):
            raise ValidationException("enterprise_entity_id must be a UUID")
        if self.finding_type not in (
            IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
            IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION,
        ):
            raise ValidationException(
                "StructuralIntegrityFinding.finding_type must be MISSING_REQUIRED_RELATIONSHIP "
                "or RELATIONSHIP_CARDINALITY_VIOLATION"
            )
        if not isinstance(self.status, IntegrityFindingStatus):
            raise ValidationException("status must be an IntegrityFindingStatus")
        if (
            not isinstance(self.state_revision, int)
            or isinstance(self.state_revision, bool)
            or self.state_revision < 1
        ):
            raise ValidationException("state_revision must be a positive integer")
        for label, value in (
            ("first_seen_at", self.first_seen_at),
            ("last_seen_at", self.last_seen_at),
            ("last_evaluated_horizon", self.last_evaluated_horizon),
        ):
            if value is None or value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
        if (
            not isinstance(self.occurrence_count, int)
            or isinstance(self.occurrence_count, bool)
            or self.occurrence_count < 1
        ):
            raise ValidationException("occurrence_count must be a positive integer")
        if (
            not isinstance(self.reopen_count, int)
            or isinstance(self.reopen_count, bool)
            or self.reopen_count < 0
        ):
            raise ValidationException("reopen_count must be a non-negative integer")
        if self.reopen_count + 1 > self.occurrence_count:
            raise ValidationException("reopen_count cannot exceed occurrence_count - 1")

        expected_id = derive_structural_finding_id(
            tenant_id=self.tenant_id,
            relationship_requirement_id=self.relationship_requirement_id,
            enterprise_entity_id=self.enterprise_entity_id,
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_structural_finding_transition(
    *,
    existing: StructuralIntegrityFinding | None,
    outcome: EvaluationOutcome,
    finding_type: IntegrityFindingType,
    evaluation_horizon: datetime,
    tenant_id: str,
    relationship_requirement_id: UUID,
    enterprise_entity_id: UUID,
) -> StructuralIntegrityFinding | None:
    """CDD-050 §16: identical transition-table shape to `apply_transition`
    (CDD-039 §30), applied to the Structural Integrity Finding lineage.
    `NOT_EVALUABLE` never reaches this function at all (CDD-050 §16, §9,
    §22) -- callers only invoke this for a genuine SATISFIED/VIOLATED
    evaluation."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")

    finding_id = derive_structural_finding_id(
        tenant_id=tenant_id,
        relationship_requirement_id=relationship_requirement_id,
        enterprise_entity_id=enterprise_entity_id,
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome is EvaluationOutcome.SATISFIED:
            return None
        return StructuralIntegrityFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            relationship_requirement_id=relationship_requirement_id,
            enterprise_entity_id=enterprise_entity_id,
            finding_type=finding_type,
            status=IntegrityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            occurrence_count=1,
            reopen_count=0,
        )

    if existing.status is IntegrityFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        return replace(
            existing,
            finding_type=finding_type,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
        )

    if existing.status is IntegrityFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        return replace(
            existing,
            status=IntegrityFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    if (
        existing.status is IntegrityFindingStatus.RESOLVED
        and outcome is EvaluationOutcome.SATISFIED
    ):
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    return replace(
        existing,
        finding_type=finding_type,
        status=IntegrityFindingStatus.OPEN,
        state_revision=existing.state_revision + 1,
        last_seen_at=evaluation_horizon,
        last_evaluated_horizon=evaluation_horizon,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
    )
