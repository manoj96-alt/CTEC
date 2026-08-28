"""OQI evaluation subject identity and the deterministic
Completeness/Validity evaluation primitives (CDD-039 §12-§14, §19-§20,
§25, §31-§32). `SourceRecordLineageIdentity` is a non-persisted value
object representing the continuing occupancy of a source-system record key
within one `SourceObject` and tenant (§13) -- it never claims verified
real-world physical incarnation or current source-system existence.
`EvaluationSubject` composes it with a `source_field_id` (§14). Canonical
identity serialization uses length-prefixed, self-delimiting encoding
(mirroring `app.domain.integration.field_value_evidence`'s own
`_length_prefixed` technique) rather than naive delimiter-joining, so no
raw component (a governed rule id, or an arbitrary `source_record_reference`
string per CDD-022 §10) can ever forge an identity collision by containing
a delimiter character."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid5

from app.domain.oqi.quality_rule import OQI_NAMESPACE, OqiMalformedRuleError, ValidityPrimitive
from app.domain.shared.exceptions import ValidationException

SUBJECT_TYPE_SOURCE_FIELD_RECORD = "SOURCE_FIELD_RECORD"

_EVALUATION_IDENTITY_ALGORITHM_VERSION = "OQI_EVALUATION_IDENTITY_V1"
_FINDING_IDENTITY_ALGORITHM_VERSION = "OQI_FINDING_IDENTITY_V1"
_EMPTY_EVIDENCE_SENTINEL = "EMPTY_EVIDENCE_SET"

_MAX_TENANT_ID_LENGTH = 200
_MAX_CONDITION_ID_LENGTH = 200


class EvaluationMode(StrEnum):
    """CDD-039 §19: exactly these two, closed."""

    HISTORICAL = "HISTORICAL"
    CURRENT_STATE = "CURRENT_STATE"


class EvaluationOutcome(StrEnum):
    """CDD-039 §19: exactly these two, closed. No fuzzy/UNKNOWN outcome."""

    SATISFIED = "SATISFIED"
    VIOLATED = "VIOLATED"


class EvaluationOrigin(StrEnum):
    """CDD-039 §19: exactly one member in OQI1 -- no AI origin yet."""

    RULE_DETERMINISTIC = "RULE_DETERMINISTIC"


def canonical_form(value: UUID | str) -> str:
    """CDD-039 §20: UUIDs render as their lowercase-hyphenated string form;
    strings are used exactly as given -- `source_record_reference` is never
    trimmed, cased, or otherwise normalized (CDD-022 §10 byte-exactness)."""
    return str(value)


def _length_prefixed(value: str) -> str:
    """Self-delimiting encoding: UTF-8 byte length, never Python character
    count -- identical technique to
    `app.domain.integration.field_value_evidence._length_prefixed`."""
    return f"{len(value.encode('utf-8'))}:{value}"


@dataclass(frozen=True, slots=True)
class SourceRecordLineageIdentity:
    """CDD-039 §12-§13: a non-persisted value object representing the
    continuing occupancy of a source-system record key within one
    `SourceObject` and tenant. Never persisted as its own table."""

    tenant_id: str
    source_object_id: UUID
    source_record_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException(
                f"tenant_id must be non-empty text of length <= {_MAX_TENANT_ID_LENGTH}"
            )
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if (
            not isinstance(self.source_record_reference, str)
            or not self.source_record_reference.strip()
        ):
            raise ValidationException("source_record_reference must be non-empty text")


@dataclass(frozen=True, slots=True)
class EvaluationSubject:
    """CDD-039 §14: `SourceRecordLineageIdentity + source_field_id`. The
    sole OQI1 subject type is `SOURCE_FIELD_RECORD`."""

    lineage: SourceRecordLineageIdentity
    source_field_id: UUID
    subject_type: str = SUBJECT_TYPE_SOURCE_FIELD_RECORD

    def __post_init__(self) -> None:
        if not isinstance(self.lineage, SourceRecordLineageIdentity):
            raise ValidationException("lineage must be a SourceRecordLineageIdentity")
        if not isinstance(self.source_field_id, UUID):
            raise ValidationException("source_field_id must be a UUID")
        if self.subject_type != SUBJECT_TYPE_SOURCE_FIELD_RECORD:
            raise ValidationException(f"subject_type must be {SUBJECT_TYPE_SOURCE_FIELD_RECORD!r}")


def canonical_subject_identity(subject: EvaluationSubject) -> str:
    """CDD-039 §20: the canonical, collision-safe serialization of an
    `EvaluationSubject`'s identity components, used as one input to both
    the evaluation identity (§20) and the Finding identity (§28)."""
    return (
        _length_prefixed(canonical_form(subject.lineage.tenant_id))
        + _length_prefixed(canonical_form(subject.lineage.source_object_id))
        + _length_prefixed(subject.lineage.source_record_reference)
        + _length_prefixed(canonical_form(subject.source_field_id))
    )


def evidence_set_digest(evidence_ids: Sequence[UUID]) -> str:
    """CDD-039 §20, §25: deterministic, order-independent (canonically
    sorted before hashing) evidence-set digest, with a fixed sentinel for
    the legitimate zero-evidence case."""
    if not evidence_ids:
        canonical_material = _EMPTY_EVIDENCE_SENTINEL
    else:
        canonical_material = "|".join(sorted(str(evidence_id) for evidence_id in evidence_ids))
    return hashlib.sha256(canonical_material.encode("utf-8")).hexdigest()


def derive_evaluation_id(
    *,
    tenant_id: str,
    quality_condition_id: str,
    rule_version: int,
    subject_type: str,
    subject_identity: str,
    evaluation_mode: EvaluationMode,
    evaluation_horizon: datetime,
    evidence_digest: str,
) -> UUID:
    """CDD-039 §20's exact deterministic evaluation identity formula,
    collision-safe length-prefixed encoding. `state_revision` never
    participates (CDD-039 §20, §26)."""
    if evaluation_horizon.tzinfo is None:
        raise ValidationException("evaluation_horizon must include a timezone")
    material = (
        _length_prefixed(_EVALUATION_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(quality_condition_id)
        + _length_prefixed(str(rule_version))
        + _length_prefixed(subject_type)
        + _length_prefixed(subject_identity)
        + _length_prefixed(evaluation_mode.value)
        + _length_prefixed(evaluation_horizon.astimezone(UTC).isoformat())
        + _length_prefixed(evidence_digest)
    )
    return uuid5(OQI_NAMESPACE, material)


def finding_identity_material(
    *,
    tenant_id: str,
    quality_condition_id: str,
    subject_type: str,
    subject_identity: str,
) -> str:
    """CDD-039 §28's exact Finding-identity pre-hash material, exposed as
    its own function so it can be reused verbatim as the PostgreSQL
    advisory-lock `:identity` text input (Concurrency Hardening Amendment
    §11: "the exact same delimited string already required to compute
    quality_finding_id... produced by one shared string-construction
    function"). `derive_quality_finding_id` hashes this string into a
    `uuid5`; `OqiQualityEvaluationRepository.acquire_evaluation_authority`
    passes this exact same string to PostgreSQL's `hashtextextended`. The
    two can never silently drift apart."""
    return (
        _length_prefixed(_FINDING_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(quality_condition_id)
        + _length_prefixed(subject_type)
        + _length_prefixed(subject_identity)
    )


def derive_quality_finding_id(
    *,
    tenant_id: str,
    quality_condition_id: str,
    subject_type: str,
    subject_identity: str,
) -> UUID:
    """CDD-039 §28's exact deterministic Finding identity formula.
    Excludes `rule_version`, `evaluation_horizon`, `finding_type`, `status`,
    `state_revision`, `occurrence_count`, `reopen_count` -- one continuing
    quality condition on one governed subject produces exactly one
    continuing Finding lineage."""
    material = finding_identity_material(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        subject_type=subject_type,
        subject_identity=subject_identity,
    )
    return uuid5(OQI_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class QualityEvaluation:
    """CDD-039 §19, §21: the immutable, append-only canonical evaluation
    ledger record. Never updated, never deleted."""

    evaluation_id: UUID
    tenant_id: str
    quality_condition_id: str
    rule_id: UUID
    rule_version: int
    subject: EvaluationSubject
    evaluation_mode: EvaluationMode
    evaluation_origin: EvaluationOrigin
    evaluation_horizon: datetime
    evidence_ids: tuple[UUID, ...]
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
        if not isinstance(self.subject, EvaluationSubject):
            raise ValidationException("subject must be an EvaluationSubject")
        if not isinstance(self.evaluation_mode, EvaluationMode):
            raise ValidationException("evaluation_mode must be an EvaluationMode")
        if not isinstance(self.evaluation_origin, EvaluationOrigin):
            raise ValidationException("evaluation_origin must be an EvaluationOrigin")
        if self.evaluation_horizon is None or self.evaluation_horizon.tzinfo is None:
            raise ValidationException("evaluation_horizon must include a timezone")
        if not isinstance(self.evidence_ids, tuple) or not all(
            isinstance(evidence_id, UUID) for evidence_id in self.evidence_ids
        ):
            raise ValidationException("evidence_ids must be a tuple of UUIDs")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValidationException("evidence_ids must not contain duplicates")
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

        expected_digest = evidence_set_digest(self.evidence_ids)
        expected_id = derive_evaluation_id(
            tenant_id=self.tenant_id,
            quality_condition_id=self.quality_condition_id,
            rule_version=self.rule_version,
            subject_type=self.subject.subject_type,
            subject_identity=canonical_subject_identity(self.subject),
            evaluation_mode=self.evaluation_mode,
            evaluation_horizon=self.evaluation_horizon,
            evidence_digest=expected_digest,
        )
        if self.evaluation_id != expected_id:
            raise ValidationException(
                "evaluation_id is inconsistent with its own governed semantic identity inputs"
            )


def evaluate_completeness(*, qualifying_target_evidence_ids: Sequence[UUID]) -> EvaluationOutcome:
    """CDD-039 §12: assumes the caller has already established the
    subject's source-record lineage is known (§12) -- this function decides
    only whether the *target* SourceField has qualifying evidence."""
    return (
        EvaluationOutcome.SATISFIED
        if qualifying_target_evidence_ids
        else EvaluationOutcome.VIOLATED
    )


def evaluate_enum_membership(*, value: str, allowed_values: Sequence[str]) -> EvaluationOutcome:
    """CDD-039 §31: exact, case-sensitive, no-trim comparison."""
    return EvaluationOutcome.SATISFIED if value in allowed_values else EvaluationOutcome.VIOLATED


def evaluate_format(*, value: str, pattern: str) -> EvaluationOutcome:
    """CDD-039 §31: `re.fullmatch`, no coercion."""
    import re

    return (
        EvaluationOutcome.SATISFIED if re.fullmatch(pattern, value) else EvaluationOutcome.VIOLATED
    )


def _coerce_numeric(value: str) -> float | None:
    """CDD-039 §31: strip whitespace, then int(), then float() -- the first
    that succeeds. An unparseable value is a genuine VIOLATED outcome, not a
    malformed-rule error and not a skipped evaluation."""
    stripped = value.strip()
    try:
        return float(int(stripped))
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return None


def evaluate_range(
    *, value: str, minimum: float | None, maximum: float | None
) -> EvaluationOutcome:
    """CDD-039 §31: both bounds inclusive."""
    parsed = _coerce_numeric(value)
    if parsed is None:
        return EvaluationOutcome.VIOLATED
    if minimum is not None and parsed < minimum:
        return EvaluationOutcome.VIOLATED
    if maximum is not None and parsed > maximum:
        return EvaluationOutcome.VIOLATED
    return EvaluationOutcome.SATISFIED


def evaluate_validity(
    *, primitive: ValidityPrimitive, value: str, rule_parameters: Mapping[str, Any]
) -> EvaluationOutcome:
    """CDD-039 §17, §31-§32 dispatcher. Callers MUST only invoke this when
    a qualifying (non-empty) target value exists -- missingness belongs
    exclusively to Completeness (§32); this function has no "no value"
    case."""
    if primitive is ValidityPrimitive.ENUM_MEMBERSHIP:
        return evaluate_enum_membership(
            value=value, allowed_values=rule_parameters["allowed_values"]
        )
    if primitive is ValidityPrimitive.FORMAT_VIOLATION:
        return evaluate_format(value=value, pattern=rule_parameters["pattern"])
    if primitive is ValidityPrimitive.RANGE_VIOLATION:
        return evaluate_range(
            value=value, minimum=rule_parameters.get("min"), maximum=rule_parameters.get("max")
        )
    raise OqiMalformedRuleError(f"Unknown validity primitive: {primitive!r}")
