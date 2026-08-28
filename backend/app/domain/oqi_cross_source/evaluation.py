"""OQI2 cross-source evaluation identity and the deterministic exact-match
comparison primitive (CDD-040 §25, §32, §40-§43). Reuses OQI1's
`EvaluationMode`/`EvaluationOutcome`/`EvaluationOrigin`/
`SourceRecordLineageIdentity`/`canonical_subject_identity`/
`evidence_set_digest` and its exact length-prefixed canonical encoding --
never reimplemented (CDD-040 §11, §40).

`ParticipantEvidenceEntry` is both the pure-domain digest input and the
exact shape persisted as the immutable evaluation-participant snapshot
(CDD-040 §37) -- one dataclass, two uses, no duplication. The
participant-keyed digest (§40) is role-ordered and role-/subject-/
evidence-sensitive, closing the flat-digest collision risk a naive reuse of
OQI1's `evidence_set_digest` alone would introduce."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOrigin,
    EvaluationOutcome,
    EvaluationSubject,
    SourceRecordLineageIdentity,
    _length_prefixed,
    canonical_form,
    canonical_subject_identity,
    evidence_set_digest,
)
from app.domain.oqi_cross_source.correspondence import OQI_CROSS_SOURCE_NAMESPACE
from app.domain.shared.exceptions import ValidationException

SUBJECT_TYPE_CROSS_SOURCE_COMPARISON = "CROSS_SOURCE_COMPARISON"

_EVALUATION_IDENTITY_ALGORITHM_VERSION = "OQI_CROSS_SOURCE_EVALUATION_IDENTITY_V1"
_FINDING_IDENTITY_ALGORITHM_VERSION = "OQI_CROSS_SOURCE_FINDING_IDENTITY_V1"

_MAX_TENANT_ID_LENGTH = 200
_MAX_CONDITION_ID_LENGTH = 200
_MAX_ROLE_LENGTH = 64


@dataclass(frozen=True, slots=True)
class ParticipantEvidenceEntry:
    """CDD-040 §37, §40-§41: one participant's contribution to one
    Evaluation. `evidence_ids` empty means either "known lineage, zero
    qualifying target evidence" or "unknown lineage, expected" (CDD-040
    §29 Cases 1/2/4) -- both are legitimately present entries carrying the
    `EMPTY_EVIDENCE_SET` sentinel in the digest, distinct from a role being
    entirely absent from this tuple (Cases 3/5, §41)."""

    role: str
    lineage: SourceRecordLineageIdentity
    source_field_id: UUID
    expected: bool
    authoritative: bool
    evidence_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not (1 <= len(self.role) <= _MAX_ROLE_LENGTH):
            raise ValidationException(
                f"role must be non-empty text of length <= {_MAX_ROLE_LENGTH}"
            )
        if not isinstance(self.lineage, SourceRecordLineageIdentity):
            raise ValidationException("lineage must be a SourceRecordLineageIdentity")
        if not isinstance(self.source_field_id, UUID):
            raise ValidationException("source_field_id must be a UUID")
        if not isinstance(self.expected, bool):
            raise ValidationException("expected must be an explicit bool")
        if not isinstance(self.authoritative, bool):
            raise ValidationException("authoritative must be an explicit bool")
        if not isinstance(self.evidence_ids, tuple) or not all(
            isinstance(evidence_id, UUID) for evidence_id in self.evidence_ids
        ):
            raise ValidationException("evidence_ids must be a tuple of UUIDs")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValidationException("evidence_ids must not contain duplicates")

    def subject_identity(self) -> str:
        return canonical_subject_identity(
            EvaluationSubject(lineage=self.lineage, source_field_id=self.source_field_id)
        )


def participant_evidence_digest(participants: Sequence[ParticipantEvidenceEntry]) -> str:
    """CDD-040 §40: deterministic, role-ordered, role-/subject-/
    evidence-sensitive, input-order-independent. Reuses OQI1's
    `evidence_set_digest` as the per-participant evidence-set digest
    (including its `EMPTY_EVIDENCE_SET` sentinel, CDD-040 §41)."""
    ordered = sorted(participants, key=lambda entry: entry.role)
    material = "".join(
        _length_prefixed(entry.role)
        + _length_prefixed(entry.subject_identity())
        + _length_prefixed(evidence_set_digest(entry.evidence_ids))
        for entry in ordered
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def finding_identity_material(
    *, tenant_id: str, quality_condition_id: str, comparison_subject_id: UUID
) -> str:
    """CDD-040 §32's exact Finding-identity pre-hash material, exposed for
    reuse verbatim as the PostgreSQL advisory-lock `:identity` text input
    (CDD-040 §46, mirroring OQI1's `finding_identity_material` discipline
    exactly) -- so the lock's authority domain can never drift from the
    Finding identity domain it must match."""
    return (
        _length_prefixed(_FINDING_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(quality_condition_id)
        + _length_prefixed(SUBJECT_TYPE_CROSS_SOURCE_COMPARISON)
        + _length_prefixed(canonical_form(comparison_subject_id))
    )


def derive_comparison_finding_id(
    *, tenant_id: str, quality_condition_id: str, comparison_subject_id: UUID
) -> UUID:
    """CDD-040 §32's exact deterministic Finding identity formula.
    Excludes rule_version, participant membership, participant order,
    authority, evidence IDs/values, evaluation_horizon, and
    correspondence_version -- every exclusion justified in CDD-040 §32."""
    return uuid5(
        OQI_CROSS_SOURCE_NAMESPACE,
        finding_identity_material(
            tenant_id=tenant_id,
            quality_condition_id=quality_condition_id,
            comparison_subject_id=comparison_subject_id,
        ),
    )


def derive_comparison_evaluation_id(
    *,
    tenant_id: str,
    quality_condition_id: str,
    rule_version: int,
    comparison_subject_id: UUID,
    evaluation_mode: EvaluationMode,
    evaluation_horizon: datetime,
    participant_digest: str,
    comparison_subject_correspondence_id: UUID,
) -> UUID:
    """CDD-040 §42's exact deterministic evaluation identity formula.
    Unlike Finding identity, `comparison_subject_correspondence_id`
    participates here -- an Evaluation is a historical fact tied to the
    specific correspondence version it relied on (CDD-040 §42)."""
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    material = (
        _length_prefixed(_EVALUATION_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(quality_condition_id)
        + _length_prefixed(str(rule_version))
        + _length_prefixed(SUBJECT_TYPE_CROSS_SOURCE_COMPARISON)
        + _length_prefixed(canonical_form(comparison_subject_id))
        + _length_prefixed(evaluation_mode.value)
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
        + _length_prefixed(participant_digest)
        + _length_prefixed(canonical_form(comparison_subject_correspondence_id))
    )
    return uuid5(OQI_CROSS_SOURCE_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class QualityComparisonEvaluation:
    """CDD-040 §27, §39: the immutable, append-only cross-source evaluation
    ledger record. Never updated, never deleted."""

    evaluation_id: UUID
    tenant_id: str
    quality_condition_id: str
    rule_id: UUID
    rule_version: int
    comparison_subject_id: UUID
    comparison_subject_correspondence_id: UUID
    evaluation_mode: EvaluationMode
    evaluation_origin: EvaluationOrigin
    evaluation_horizon: datetime
    participants: tuple[ParticipantEvidenceEntry, ...]
    outcome: EvaluationOutcome
    applied_current_state_authority: bool
    state_revision_applied: int | None
    evaluated_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.quality_condition_id, str) or not (
            1 <= len(self.quality_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException("quality_condition_id must be non-empty bounded text")
        if not isinstance(self.rule_id, UUID):
            raise ValidationException("rule_id must be a UUID")
        if (
            not isinstance(self.rule_version, int)
            or isinstance(self.rule_version, bool)
            or self.rule_version < 1
        ):
            raise ValidationException("rule_version must be a positive integer")
        if not isinstance(self.comparison_subject_id, UUID):
            raise ValidationException("comparison_subject_id must be a UUID")
        if not isinstance(self.comparison_subject_correspondence_id, UUID):
            raise ValidationException("comparison_subject_correspondence_id must be a UUID")
        if not isinstance(self.evaluation_mode, EvaluationMode):
            raise ValidationException("evaluation_mode must be an EvaluationMode")
        if not isinstance(self.evaluation_origin, EvaluationOrigin):
            raise ValidationException("evaluation_origin must be an EvaluationOrigin")
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if not isinstance(self.participants, tuple) or not all(
            isinstance(entry, ParticipantEvidenceEntry) for entry in self.participants
        ):
            raise ValidationException("participants must be a tuple of ParticipantEvidenceEntry")
        roles = [entry.role for entry in self.participants]
        if len(set(roles)) != len(roles):
            raise ValidationException("participants must not repeat a role")
        if not isinstance(self.outcome, EvaluationOutcome):
            raise ValidationException("outcome must be an EvaluationOutcome")
        if not isinstance(self.applied_current_state_authority, bool):
            raise ValidationException("applied_current_state_authority must be a bool")
        if (
            self.applied_current_state_authority
            and self.evaluation_mode is not EvaluationMode.CURRENT_STATE
        ):
            raise ValidationException(
                "applied_current_state_authority requires evaluation_mode=CURRENT_STATE"
            )
        if not self.applied_current_state_authority and self.state_revision_applied is not None:
            raise ValidationException(
                "state_revision_applied requires applied_current_state_authority=True"
            )
        if self.evaluated_on is None or self.evaluated_on.tzinfo is None:
            raise ValidationException("evaluated_on must include a timezone")

        expected_digest = participant_evidence_digest(self.participants)
        expected_id = derive_comparison_evaluation_id(
            tenant_id=self.tenant_id,
            quality_condition_id=self.quality_condition_id,
            rule_version=self.rule_version,
            comparison_subject_id=self.comparison_subject_id,
            evaluation_mode=self.evaluation_mode,
            evaluation_horizon=self.evaluation_horizon,
            participant_digest=expected_digest,
            comparison_subject_correspondence_id=self.comparison_subject_correspondence_id,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


def evaluate_consistency(*, participant_values: Mapping[str, str]) -> EvaluationOutcome:
    """CDD-040 §25, §33: exact-match v1 -- whitespace-trim, case-preserving
    equality. Caller must supply >= 2 entries (CDD-040 §30's minimum
    evaluable set is enforced by the orchestrating service, not here)."""
    trimmed = {value.strip() for value in participant_values.values()}
    return EvaluationOutcome.SATISFIED if len(trimmed) <= 1 else EvaluationOutcome.VIOLATED
