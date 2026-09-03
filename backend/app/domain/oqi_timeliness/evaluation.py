"""OQI-H5 Governed Timeliness (CDD-051 §3-§4, §17-§19): evaluates whether a
single tenant's latest qualifying `FieldValueEvidence` for a governed
`(InformationElementRequirement, BusinessProcess)` anchor remains current
enough under its `ACTIVE` `TimelinessPolicy`. Exactly two Finding types,
each an entirely separate Finding lineage -- never reclassified into one
another, never merged:

    STALE_SOURCE_EVIDENCE          evaluation_horizon - observed_at
                                   >  freshness_window_seconds
    INGESTION_LATENCY_EXCEEDED     received_at - observed_at
                                   >  ingestion_sla_seconds

Threshold boundary is inclusive (CDD-051 §4): `age_seconds <=
threshold_seconds` is `SATISFIED`; strictly greater is `VIOLATED`.

Distinct OQI-family namespace (CDD-039 §20's own precedent, restated):
Finding/evaluation identity never collides with OQI1-6/H1-H4's own
namespaces."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.shared.exceptions import ValidationException

#: CDD-051 §17-§18: distinct from OQI_NAMESPACE, OQI_INTEGRITY_NAMESPACE, and
#: every other governed OQI namespace -- no cross-family identity collision
#: is possible even adversarially.
OQI_TIMELINESS_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:timeliness:v1")

_IDENTITY_ALGORITHM_VERSION = "OQI_TIMELINESS_IDENTITY_V1"
_MAX_TENANT_ID_LENGTH = 200


class TimelinessFindingType(StrEnum):
    """CDD-051 §4, §19: closed, exactly two. No generic third type."""

    STALE_SOURCE_EVIDENCE = "STALE_SOURCE_EVIDENCE"
    INGESTION_LATENCY_EXCEEDED = "INGESTION_LATENCY_EXCEEDED"


class TimelinessFindingStatus(StrEnum):
    """Mirrors `QualityFindingStatus`'s exact closed shape (CDD-039 §27)."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to `app.domain.oqi_integrity.structural`'s
    own private helper, redefined locally per the established per-family
    precedent of never importing another family's private symbols."""
    return f"{len(value.encode('utf-8'))}:{value}"


def timeliness_finding_identity_material(
    *,
    tenant_id: str,
    policy_id: UUID,
    finding_type: TimelinessFindingType,
    source_object_id: UUID,
) -> str:
    """CDD-051 §17: the exact Finding-identity material, deliberately
    excluding `policy_version`, `evaluation_horizon`, `evaluated_on`,
    computed age, and `field_value_evidence_id` -- a policy threshold
    tuning, or age advancing every minute, never creates a duplicate
    current Finding for the same governed subject. `finding_type` IS an
    identity input: the two Finding types are always entirely separate
    Finding lineages, never reclassified into one another for the same
    subject."""
    return (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(tenant_id)
        + _length_prefixed(str(policy_id))
        + _length_prefixed(finding_type.value)
        + _length_prefixed(str(source_object_id))
    )


def derive_timeliness_finding_id(
    *,
    tenant_id: str,
    policy_id: UUID,
    finding_type: TimelinessFindingType,
    source_object_id: UUID,
) -> UUID:
    return uuid5(
        OQI_TIMELINESS_NAMESPACE,
        timeliness_finding_identity_material(
            tenant_id=tenant_id,
            policy_id=policy_id,
            finding_type=finding_type,
            source_object_id=source_object_id,
        ),
    )


def derive_timeliness_evaluation_id(
    *,
    tenant_id: str,
    policy_id: UUID,
    policy_version: int,
    finding_type: TimelinessFindingType,
    source_object_id: UUID,
    field_value_evidence_id: UUID,
    evaluation_horizon: datetime,
) -> UUID:
    """CDD-051 §18: evaluation-row identity additionally folds in the
    consulted policy version, the specific evidence row considered, and the
    evaluation horizon, so a repeated identical evaluation converges to the
    same row (idempotent replay) while a genuinely fresh evaluation (new
    horizon, new evidence, or a changed policy version) always produces a
    new row -- mirroring `derive_structural_evaluation_id`'s established
    discipline exactly."""
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    material = (
        timeliness_finding_identity_material(
            tenant_id=tenant_id,
            policy_id=policy_id,
            finding_type=finding_type,
            source_object_id=source_object_id,
        )
        + _length_prefixed(str(policy_version))
        + _length_prefixed(str(field_value_evidence_id))
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
    )
    return uuid5(OQI_TIMELINESS_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class TimelinessEvaluation:
    """CDD-051 §8, §18: the immutable, append-only Timeliness evaluation
    ledger record."""

    evaluation_id: UUID
    tenant_id: str
    policy_id: UUID
    policy_version: int
    finding_type: TimelinessFindingType
    source_object_id: UUID
    field_value_evidence_id: UUID
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
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if (
            not isinstance(self.policy_version, int)
            or isinstance(self.policy_version, bool)
            or self.policy_version < 1
        ):
            raise ValidationException("policy_version must be a positive integer")
        if not isinstance(self.finding_type, TimelinessFindingType):
            raise ValidationException("finding_type must be a TimelinessFindingType")
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if not isinstance(self.field_value_evidence_id, UUID):
            raise ValidationException("field_value_evidence_id must be a UUID")
        if not isinstance(self.outcome, EvaluationOutcome):
            raise ValidationException("outcome must be an EvaluationOutcome")
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if self.evaluated_on is None or self.evaluated_on.tzinfo is None:
            raise ValidationException("evaluated_on must include a timezone")

        expected_id = derive_timeliness_evaluation_id(
            tenant_id=self.tenant_id,
            policy_id=self.policy_id,
            policy_version=self.policy_version,
            finding_type=self.finding_type,
            source_object_id=self.source_object_id,
            field_value_evidence_id=self.field_value_evidence_id,
            evaluation_horizon=self.evaluation_horizon,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


@dataclass(frozen=True, slots=True)
class TimelinessFinding:
    finding_id: UUID
    tenant_id: str
    policy_id: UUID
    finding_type: TimelinessFindingType
    source_object_id: UUID
    status: TimelinessFindingStatus
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
        if not isinstance(self.policy_id, UUID):
            raise ValidationException("policy_id must be a UUID")
        if not isinstance(self.finding_type, TimelinessFindingType):
            raise ValidationException("finding_type must be a TimelinessFindingType")
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if not isinstance(self.status, TimelinessFindingStatus):
            raise ValidationException("status must be a TimelinessFindingStatus")
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

        expected_id = derive_timeliness_finding_id(
            tenant_id=self.tenant_id,
            policy_id=self.policy_id,
            finding_type=self.finding_type,
            source_object_id=self.source_object_id,
        )
        if self.finding_id != expected_id:
            raise ValidationException(
                "finding_id is inconsistent with its own governed semantic identity inputs"
            )


def apply_timeliness_finding_transition(
    *,
    existing: TimelinessFinding | None,
    outcome: EvaluationOutcome,
    finding_type: TimelinessFindingType,
    evaluation_horizon: datetime,
    tenant_id: str,
    policy_id: UUID,
    source_object_id: UUID,
) -> TimelinessFinding | None:
    """CDD-051 §19: identical transition-table shape to
    `apply_structural_finding_transition` (CDD-050 §16), applied to the
    Timeliness Finding lineage. Unlike Structural Integrity, `finding_type`
    never changes across a transition for the same lineage -- a Finding's
    identity already fixes exactly which of the two Timeliness reason paths
    it represents (CDD-051 §17); the two types are always entirely separate
    lineages, never reclassified into one another. `NOT_EVALUABLE` never
    reaches this function at all (CDD-051 §6) -- callers only invoke this
    for a genuine SATISFIED/VIOLATED evaluation."""
    if evaluation_horizon is None or evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")

    finding_id = derive_timeliness_finding_id(
        tenant_id=tenant_id,
        policy_id=policy_id,
        finding_type=finding_type,
        source_object_id=source_object_id,
    )
    if existing is not None and existing.finding_id != finding_id:
        raise ValidationException(
            "existing Finding identity does not match the supplied identity arguments"
        )

    if existing is None:
        if outcome is EvaluationOutcome.SATISFIED:
            return None
        return TimelinessFinding(
            finding_id=finding_id,
            tenant_id=tenant_id,
            policy_id=policy_id,
            finding_type=finding_type,
            source_object_id=source_object_id,
            status=TimelinessFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=evaluation_horizon,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
            occurrence_count=1,
            reopen_count=0,
        )

    if existing.status is TimelinessFindingStatus.OPEN and outcome is EvaluationOutcome.VIOLATED:
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_seen_at=evaluation_horizon,
            last_evaluated_horizon=evaluation_horizon,
        )

    if existing.status is TimelinessFindingStatus.OPEN and outcome is EvaluationOutcome.SATISFIED:
        return replace(
            existing,
            status=TimelinessFindingStatus.RESOLVED,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    if (
        existing.status is TimelinessFindingStatus.RESOLVED
        and outcome is EvaluationOutcome.SATISFIED
    ):
        return replace(
            existing,
            state_revision=existing.state_revision + 1,
            last_evaluated_horizon=evaluation_horizon,
        )

    return replace(
        existing,
        status=TimelinessFindingStatus.OPEN,
        state_revision=existing.state_revision + 1,
        last_seen_at=evaluation_horizon,
        last_evaluated_horizon=evaluation_horizon,
        occurrence_count=existing.occurrence_count + 1,
        reopen_count=existing.reopen_count + 1,
    )
