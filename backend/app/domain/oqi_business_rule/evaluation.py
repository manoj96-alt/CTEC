"""OQI3 `BusinessRuleEvaluation` (immutable ledger), `EvaluationOutcome`,
`ObservationType`/`BusinessRuleEvaluationObservation`, the role-keyed input
evidence digest, and their deterministic identity formulas (CDD-041 §13,
§16-§19). Deliberately not a reuse of OQI1's two-value `EvaluationOutcome`
(`app.domain.oqi.evaluation`) -- OQI3 has a genuine third persisted outcome,
`NOT_APPLICABLE` (CDD-041 §13), so a new, OQI3-scoped enum is the correct
closed set rather than silently widening a frozen OQI1 type.

`NOT_EVALUABLE` (CDD-041 §13) is a return value of the OQI3-I2 evaluation
service, never a member of this module's `EvaluationOutcome` and never a
row in `business_rule_evaluations` -- mirroring OQI2's `evaluate_* -> None`
non-persistence pattern exactly (`app.domain.oqi_cross_source.evaluation`).

`BusinessRuleEvaluationInputEntry` is both the pure-domain digest input and
the exact shape persisted as the immutable per-evaluation input snapshot
row -- one dataclass, two uses, mirroring OQI2's `ParticipantEvidenceEntry`
precedent. `evidence_id=None` means "a known subject, zero qualifying
evidence for this bound input" -- never a manufactured evidence row
(CDD-041 §18)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid5

from app.domain.oqi.evaluation import EvaluationMode, _length_prefixed, canonical_form
from app.domain.oqi_business_rule.rule import OQI_BUSINESS_RULE_NAMESPACE
from app.domain.shared.exceptions import ValidationException

SUBJECT_TYPE_SINGLE_RECORD = "SINGLE_RECORD"

_EVALUATION_IDENTITY_ALGORITHM_VERSION = "OQI_BUSINESS_RULE_EVALUATION_IDENTITY_V1"
_EMPTY_INPUT_EVIDENCE_SENTINEL = "EMPTY_INPUT_EVIDENCE"

_MAX_TENANT_ID_LENGTH = 200
_MAX_CONDITION_ID_LENGTH = 200
_MAX_ROLE_LENGTH = 64
_MAX_SUBJECT_IDENTITY_LENGTH = 1000


class EvaluationOutcome(StrEnum):
    """CDD-041 §13: exactly these three persisted outcomes. `NOT_EVALUABLE`
    is a fourth semantic result but is never a member here -- it produces
    no `BusinessRuleEvaluation` row at all (never collapsed with
    `NOT_APPLICABLE`, which is a positive, persisted fact)."""

    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ObservationType(StrEnum):
    """CDD-041 §19: closed, exactly these two members. No generic
    `RULE_FAILED` -- it would destroy explainability. No third type without
    a governance amendment."""

    REQUIRED_INPUT_MISSING = "REQUIRED_INPUT_MISSING"
    CLAUSE_VIOLATED = "CLAUSE_VIOLATED"


@dataclass(frozen=True, slots=True)
class BusinessRuleEvaluationObservation:
    """CDD-041 §19: one deterministic quality fact established by one
    `BusinessRuleEvaluation`. `clause_id` distinguishes *which* leaf failed
    when multiple leaves fail simultaneously -- new relative to OQI2's flat
    participant-role key, required because a compound predicate tree needs
    a stable sub-identity. Means "this deterministic clause/input fact was
    established" -- never "this input's source is wrong" (no blame, no
    winner, mirrors OQI2's conflict-participation discipline)."""

    clause_id: str
    observation_type: ObservationType
    input_role: str

    def __post_init__(self) -> None:
        if not isinstance(self.clause_id, str) or not self.clause_id.strip():
            raise ValidationException("clause_id must be non-blank text")
        if not isinstance(self.observation_type, ObservationType):
            raise ValidationException("observation_type must be an ObservationType")
        if not isinstance(self.input_role, str) or not (
            1 <= len(self.input_role) <= _MAX_ROLE_LENGTH
        ):
            raise ValidationException(
                f"input_role must be non-empty text of length <= {_MAX_ROLE_LENGTH}"
            )


@dataclass(frozen=True, slots=True)
class BusinessRuleEvaluationInputEntry:
    """CDD-041 §17-§18: one bound input's contribution to one Evaluation.
    `evidence_id=None` means a known subject with zero qualifying evidence
    for this bound input -- a legitimate, deterministic fact, never a
    manufactured `FieldValueEvidence` row."""

    input_role: str
    evidence_id: UUID | None

    def __post_init__(self) -> None:
        if not isinstance(self.input_role, str) or not (
            1 <= len(self.input_role) <= _MAX_ROLE_LENGTH
        ):
            raise ValidationException(
                f"input_role must be non-empty text of length <= {_MAX_ROLE_LENGTH}"
            )
        if self.evidence_id is not None and not isinstance(self.evidence_id, UUID):
            raise ValidationException("evidence_id must be a UUID or None")


def input_evidence_digest(inputs: Sequence[BusinessRuleEvaluationInputEntry]) -> str:
    """CDD-041 §17: role-sorted (not insertion-order), evidence-sensitive,
    explicit about zero-qualifying-evidence, deterministic -- generalizes
    OQI1/OQI2's evidence-digest pattern from "participant role" to "input
    role"."""
    ordered = sorted(inputs, key=lambda entry: entry.input_role)
    material = "".join(
        _length_prefixed(entry.input_role)
        + _length_prefixed(
            _EMPTY_INPUT_EVIDENCE_SENTINEL if entry.evidence_id is None else str(entry.evidence_id)
        )
        for entry in ordered
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def canonical_single_record_subject_identity(
    *, source_object_id: UUID, source_record_reference: str
) -> str:
    """CDD-041 §6: the `SINGLE_RECORD` subject is identified by the
    lineage alone (tenant is a separate identity dimension, mirrored from
    OQI1's `SourceRecordLineageIdentity`) -- never bound to one
    `source_field_id`, unlike OQI1's `EvaluationSubject`, since a
    `BusinessRule` binds many fields."""
    return _length_prefixed(canonical_form(source_object_id)) + _length_prefixed(
        source_record_reference
    )


def derive_business_rule_evaluation_id(
    *,
    tenant_id: str,
    business_condition_id: str,
    rule_version: int,
    subject_type: str,
    subject_identity: str,
    evaluation_mode: EvaluationMode,
    evaluation_horizon: datetime,
    input_evidence_digest_value: str,
) -> UUID:
    """CDD-041 §16's exact deterministic evaluation identity formula.
    Observation content is excluded -- observations are deterministic
    derivatives of these frozen inputs, exactly as OQI2 proved for its own
    Observation model."""
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    material = (
        _length_prefixed(_EVALUATION_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(business_condition_id)
        + _length_prefixed(str(rule_version))
        + _length_prefixed(subject_type)
        + _length_prefixed(subject_identity)
        + _length_prefixed(evaluation_mode.value)
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
        + _length_prefixed(input_evidence_digest_value)
    )
    return uuid5(OQI_BUSINESS_RULE_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class BusinessRuleEvaluation:
    """CDD-041 §16: the immutable, append-only Evaluation ledger record.
    Never updated, never deleted. Represents exactly one of `SATISFIED`,
    `VIOLATED`, `NOT_APPLICABLE` -- `NOT_EVALUABLE` never reaches this
    dataclass at all (enforced by the application service, not here)."""

    evaluation_id: UUID
    tenant_id: str
    business_condition_id: str
    rule_id: UUID
    rule_version: int
    subject_type: str
    subject_identity: str
    source_object_id: UUID
    source_record_reference: str
    evaluation_mode: EvaluationMode
    evaluation_horizon: datetime
    inputs: tuple[BusinessRuleEvaluationInputEntry, ...]
    outcome: EvaluationOutcome
    observations: tuple[BusinessRuleEvaluationObservation, ...]
    evaluated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.evaluation_id, UUID):
            raise ValidationException("evaluation_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.business_condition_id, str) or not (
            1 <= len(self.business_condition_id) <= _MAX_CONDITION_ID_LENGTH
        ):
            raise ValidationException("business_condition_id must be non-empty bounded text")
        if not isinstance(self.rule_id, UUID):
            raise ValidationException("rule_id must be a UUID")
        if (
            not isinstance(self.rule_version, int)
            or isinstance(self.rule_version, bool)
            or self.rule_version < 1
        ):
            raise ValidationException("rule_version must be a positive integer")
        if self.subject_type != SUBJECT_TYPE_SINGLE_RECORD:
            raise ValidationException(f"subject_type must be {SUBJECT_TYPE_SINGLE_RECORD!r}")
        if not isinstance(self.subject_identity, str) or not (
            1 <= len(self.subject_identity) <= _MAX_SUBJECT_IDENTITY_LENGTH
        ):
            raise ValidationException("subject_identity must be non-empty bounded text")
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if not isinstance(self.source_record_reference, str) or not (
            1 <= len(self.source_record_reference) <= _MAX_SUBJECT_IDENTITY_LENGTH
        ):
            raise ValidationException("source_record_reference must be non-empty bounded text")
        # CDD-041 §3.1 (OQI3-I2-R): source_object_id and source_record_reference
        # are the two constituents subject_identity was always computed from at
        # write time -- this is an internal-consistency check, not a new
        # identity formula. It does not change derive_business_rule_evaluation_id.
        expected_subject_identity = canonical_single_record_subject_identity(
            source_object_id=self.source_object_id,
            source_record_reference=self.source_record_reference,
        )
        if self.subject_identity != expected_subject_identity:
            raise ValidationException(
                "subject_identity is inconsistent with source_object_id/" "source_record_reference"
            )
        if not isinstance(self.evaluation_mode, EvaluationMode):
            raise ValidationException("evaluation_mode must be an EvaluationMode")
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if not isinstance(self.inputs, tuple) or not all(
            isinstance(entry, BusinessRuleEvaluationInputEntry) for entry in self.inputs
        ):
            raise ValidationException("inputs must be a tuple of BusinessRuleEvaluationInputEntry")
        roles = [entry.input_role for entry in self.inputs]
        if len(set(roles)) != len(roles):
            raise ValidationException("inputs must not repeat an input_role")
        if not isinstance(self.outcome, EvaluationOutcome):
            raise ValidationException("outcome must be an EvaluationOutcome")
        if not isinstance(self.observations, tuple) or not all(
            isinstance(observation, BusinessRuleEvaluationObservation)
            for observation in self.observations
        ):
            raise ValidationException(
                "observations must be a tuple of BusinessRuleEvaluationObservation"
            )
        observation_keys = [
            (observation.clause_id, observation.observation_type, observation.input_role)
            for observation in self.observations
        ]
        if len(set(observation_keys)) != len(observation_keys):
            raise ValidationException(
                "observations must not repeat (clause_id, observation_type, input_role)"
            )
        input_roles = set(roles)
        if not all(observation.input_role in input_roles for observation in self.observations):
            raise ValidationException(
                "every observation's input_role must belong to this evaluation's inputs"
            )
        if self.outcome is EvaluationOutcome.VIOLATED and not self.observations:
            raise ValidationException("a VIOLATED evaluation must carry at least one observation")
        if self.outcome is not EvaluationOutcome.VIOLATED and self.observations:
            raise ValidationException(
                "only a VIOLATED evaluation may carry observations "
                "(SATISFIED/NOT_APPLICABLE never do, CDD-041 §19)"
            )
        if self.evaluated_at is None or self.evaluated_at.tzinfo is None:
            raise ValidationException("evaluated_at must include a timezone")

        expected_digest = input_evidence_digest(self.inputs)
        expected_id = derive_business_rule_evaluation_id(
            tenant_id=self.tenant_id,
            business_condition_id=self.business_condition_id,
            rule_version=self.rule_version,
            subject_type=self.subject_type,
            subject_identity=self.subject_identity,
            evaluation_mode=self.evaluation_mode,
            evaluation_horizon=self.evaluation_horizon,
            input_evidence_digest_value=expected_digest,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )
