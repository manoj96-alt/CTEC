"""OQI5-I2 `AgentAssessment`, `AgentRecommendation`, and
`AgentRecommendationValidator` (CDD-043 §20-§22) -- the release-critical
AI firewall (phase §34). `AgentRecommendationValidator` is plain code, not
a model call. It rejects -- never coerces or silently repairs -- any
model output that references an id outside the evidence packet's closed
universe, specifies a disallowed recommendation type, omits known
dissent, or attempts to inject an independent `proposed_value`. No
`AgentAssessment`/`AgentRecommendation` is ever constructed from rejected
output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from app.domain.oqi_remediation_agent.role import AgentRole, RecommendationType
from app.domain.oqi_remediation_agent.run import AgentEvidencePacket
from app.domain.shared.exceptions import ValidationException

_MAX_RATIONALE_LENGTH = 2000
_PROHIBITED_KEYS = frozenset({"proposed_value", "value", "new_value", "correction"})
_ALLOWED_KEYS = frozenset(
    {
        "recommendation_type",
        "candidate_id",
        "supporting_evidence_ids",
        "conflicting_evidence_ids",
        "impact_evaluation_ids",
        "rationale",
    }
)


class RejectionReason(StrEnum):
    """CDD-043 §21's rejection categories, closed. Exactly one reason is
    recorded per rejected output (phase §47/§52)."""

    MALFORMED_SCHEMA = "MALFORMED_SCHEMA"
    UNSUPPORTED_VALUE_INJECTION = "UNSUPPORTED_VALUE_INJECTION"
    DISALLOWED_RECOMMENDATION_TYPE = "DISALLOWED_RECOMMENDATION_TYPE"
    CANDIDATE_REQUIRED_FOR_TYPE = "CANDIDATE_REQUIRED_FOR_TYPE"
    CANDIDATE_FORBIDDEN_FOR_TYPE = "CANDIDATE_FORBIDDEN_FOR_TYPE"
    UNKNOWN_CANDIDATE = "UNKNOWN_CANDIDATE"
    UNKNOWN_EVIDENCE = "UNKNOWN_EVIDENCE"
    UNKNOWN_IMPACT = "UNKNOWN_IMPACT"
    DISSENT_OMISSION = "DISSENT_OMISSION"


@dataclass(frozen=True, slots=True)
class AgentAssessment:
    """CDD-043 §20: one specialist's own validated, structured output --
    never raw model text, and never consumed downstream until it has
    passed the identical validator every recommendation passes."""

    run_id: UUID
    role_id: str
    recommendation_type: RecommendationType
    candidate_id: UUID | None
    supporting_evidence_ids: tuple[UUID, ...]
    conflicting_evidence_ids: tuple[UUID, ...]
    impact_evaluation_ids: tuple[UUID, ...]
    rationale: str

    def __post_init__(self) -> None:
        _validate_common_recommendation_fields(
            recommendation_type=self.recommendation_type,
            candidate_id=self.candidate_id,
            supporting_evidence_ids=self.supporting_evidence_ids,
            conflicting_evidence_ids=self.conflicting_evidence_ids,
            impact_evaluation_ids=self.impact_evaluation_ids,
            rationale=self.rationale,
        )
        if not isinstance(self.run_id, UUID):
            raise ValidationException("run_id must be a UUID")
        if not isinstance(self.role_id, str) or not self.role_id:
            raise ValidationException("role_id must be non-blank text")


@dataclass(frozen=True, slots=True)
class AgentRecommendation:
    """CDD-043 §22: immutable, created only after successful validation.
    Composition into I1: `RemediationInstruction.agent_recommendation_id`
    may reference this row as provenance metadata only -- the
    instruction's `payload_digest` never includes any field of this
    dataclass (CDD-043 §22, §56)."""

    recommendation_id: UUID
    run_id: UUID
    case_id: UUID
    recommendation_type: RecommendationType
    candidate_id: UUID | None
    supporting_evidence_ids: tuple[UUID, ...]
    conflicting_evidence_ids: tuple[UUID, ...]
    rationale: str
    created_on: datetime

    def __post_init__(self) -> None:
        _validate_common_recommendation_fields(
            recommendation_type=self.recommendation_type,
            candidate_id=self.candidate_id,
            supporting_evidence_ids=self.supporting_evidence_ids,
            conflicting_evidence_ids=self.conflicting_evidence_ids,
            impact_evaluation_ids=(),
            rationale=self.rationale,
        )
        if not isinstance(self.recommendation_id, UUID):
            raise ValidationException("recommendation_id must be a UUID")
        if not isinstance(self.run_id, UUID):
            raise ValidationException("run_id must be a UUID")
        if not isinstance(self.case_id, UUID):
            raise ValidationException("case_id must be a UUID")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")


def _validate_common_recommendation_fields(
    *,
    recommendation_type: RecommendationType,
    candidate_id: UUID | None,
    supporting_evidence_ids: tuple[UUID, ...],
    conflicting_evidence_ids: tuple[UUID, ...],
    impact_evaluation_ids: tuple[UUID, ...],
    rationale: str,
) -> None:
    if not isinstance(recommendation_type, RecommendationType):
        raise ValidationException("recommendation_type must be a RecommendationType")
    if recommendation_type is RecommendationType.RECOMMEND_CANDIDATE:
        if candidate_id is None:
            raise ValidationException("RECOMMEND_CANDIDATE requires a candidate_id")
    elif candidate_id is not None:
        raise ValidationException(f"{recommendation_type.value} must not carry a candidate_id")
    for label, ids in (
        ("supporting_evidence_ids", supporting_evidence_ids),
        ("conflicting_evidence_ids", conflicting_evidence_ids),
        ("impact_evaluation_ids", impact_evaluation_ids),
    ):
        if not isinstance(ids, tuple) or not all(isinstance(e, UUID) for e in ids):
            raise ValidationException(f"{label} must be a tuple of UUIDs")
    if not isinstance(rationale, str) or not (1 <= len(rationale) <= _MAX_RATIONALE_LENGTH):
        raise ValidationException("rationale must be non-blank bounded text")


@dataclass(frozen=True, slots=True)
class ValidationRejection:
    reason: RejectionReason
    detail: str


@dataclass(frozen=True, slots=True)
class SpecialistValidationResult:
    assessment: AgentAssessment | None
    rejection: ValidationRejection | None

    @property
    def accepted(self) -> bool:
        return self.assessment is not None


@dataclass(frozen=True, slots=True)
class RecommendationValidationResult:
    recommendation_fields: ValidatedRecommendationFields | None
    rejection: ValidationRejection | None

    @property
    def accepted(self) -> bool:
        return self.recommendation_fields is not None


@dataclass(frozen=True, slots=True)
class ValidatedRecommendationFields:
    """The exact, already-validated field set a caller may safely use to
    construct an `AgentRecommendation` -- deliberately not the dataclass
    itself, since `run_id`/`case_id`/`recommendation_id`/`created_on` are
    caller-supplied identity/provenance, not model output."""

    recommendation_type: RecommendationType
    candidate_id: UUID | None
    supporting_evidence_ids: tuple[UUID, ...]
    conflicting_evidence_ids: tuple[UUID, ...]
    impact_evaluation_ids: tuple[UUID, ...]
    rationale: str


class AgentRecommendationValidator:
    """CDD-043 §21: the sole authority on whether raw structured model
    output may become anything consequential. Plain code -- never a model
    call. The same reference-checking logic backs both specialist and
    final-recommendation validation (CDD-043 §20: "Each specialist output
    passes through the deterministic validator independently... passes
    through the identical validator again")."""

    def validate_specialist_output(
        self,
        raw: Any,
        *,
        run_id: UUID,
        role: AgentRole,
        packet: AgentEvidencePacket,
    ) -> SpecialistValidationResult:
        result = _validate_structured_output(raw, role=role, packet=packet)
        if result.rejection is not None:
            return SpecialistValidationResult(assessment=None, rejection=result.rejection)
        fields = result.recommendation_fields
        assert fields is not None
        assessment = AgentAssessment(
            run_id=run_id,
            role_id=role.role_id.value,
            recommendation_type=fields.recommendation_type,
            candidate_id=fields.candidate_id,
            supporting_evidence_ids=fields.supporting_evidence_ids,
            conflicting_evidence_ids=fields.conflicting_evidence_ids,
            impact_evaluation_ids=fields.impact_evaluation_ids,
            rationale=fields.rationale,
        )
        return SpecialistValidationResult(assessment=assessment, rejection=None)

    def validate_recommendation_output(
        self,
        raw: Any,
        *,
        role: AgentRole,
        packet: AgentEvidencePacket,
    ) -> RecommendationValidationResult:
        return _validate_structured_output(raw, role=role, packet=packet)


def _validate_structured_output(
    raw: Any, *, role: AgentRole, packet: AgentEvidencePacket
) -> RecommendationValidationResult:
    if not isinstance(raw, dict):
        return _reject(RejectionReason.MALFORMED_SCHEMA, "top-level output was not a JSON object")

    unknown_keys = set(raw.keys()) - _ALLOWED_KEYS
    if unknown_keys & _PROHIBITED_KEYS:
        return _reject(
            RejectionReason.UNSUPPORTED_VALUE_INJECTION,
            f"output attempted to supply prohibited field(s): {sorted(unknown_keys & _PROHIBITED_KEYS)}",
        )
    if unknown_keys:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA,
            f"output contained unrecognized field(s): {sorted(unknown_keys)}",
        )
    missing_keys = _ALLOWED_KEYS - set(raw.keys())
    if missing_keys:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA,
            f"output missing required field(s): {sorted(missing_keys)}",
        )

    raw_type = raw.get("recommendation_type")
    if not isinstance(raw_type, str):
        return _reject(
            RejectionReason.MALFORMED_SCHEMA,
            "recommendation_type was not a recognized string value",
        )
    try:
        recommendation_type = RecommendationType(raw_type)
    except ValueError:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA,
            "recommendation_type was not a recognized string value",
        )
    if recommendation_type not in role.allowed_recommendation_types:
        return _reject(
            RejectionReason.DISALLOWED_RECOMMENDATION_TYPE,
            f"{recommendation_type.value} is not permitted for role {role.role_id.value}",
        )

    raw_candidate_id = raw.get("candidate_id")
    if raw_candidate_id is not None and not isinstance(raw_candidate_id, str):
        return _reject(RejectionReason.MALFORMED_SCHEMA, "candidate_id must be a string or null")
    candidate_id: UUID | None = None
    if raw_candidate_id is not None:
        try:
            candidate_id = UUID(raw_candidate_id)
        except (ValueError, AttributeError, TypeError):
            return _reject(
                RejectionReason.MALFORMED_SCHEMA, "candidate_id was not a valid UUID string"
            )

    if recommendation_type is RecommendationType.RECOMMEND_CANDIDATE:
        if candidate_id is None:
            return _reject(
                RejectionReason.CANDIDATE_REQUIRED_FOR_TYPE,
                "RECOMMEND_CANDIDATE requires a non-null candidate_id",
            )
        if candidate_id not in packet.known_candidate_ids():
            return _reject(
                RejectionReason.UNKNOWN_CANDIDATE,
                f"candidate_id {candidate_id} is not present in the evidence packet",
            )
    elif candidate_id is not None:
        return _reject(
            RejectionReason.CANDIDATE_FORBIDDEN_FOR_TYPE,
            f"{recommendation_type.value} must not carry a candidate_id",
        )

    supporting_ids_result = _parse_id_list(raw.get("supporting_evidence_ids"))
    if supporting_ids_result is None:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA, "supporting_evidence_ids must be a list of id strings"
        )
    known_evidence = packet.known_evidence_ids()
    for evidence_id in supporting_ids_result:
        if evidence_id not in known_evidence:
            return _reject(
                RejectionReason.UNKNOWN_EVIDENCE,
                f"evidence_id {evidence_id} is not present in the evidence packet",
            )

    conflicting_ids_result = _parse_id_list(raw.get("conflicting_evidence_ids"))
    if conflicting_ids_result is None:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA,
            "conflicting_evidence_ids must be a list of id strings",
        )
    for evidence_id in conflicting_ids_result:
        if evidence_id not in known_evidence:
            return _reject(
                RejectionReason.UNKNOWN_EVIDENCE,
                f"evidence_id {evidence_id} is not present in the evidence packet",
            )

    impact_ids_result = _parse_id_list(raw.get("impact_evaluation_ids"))
    if impact_ids_result is None:
        return _reject(
            RejectionReason.MALFORMED_SCHEMA, "impact_evaluation_ids must be a list of id strings"
        )
    known_impacts = packet.known_impact_evaluation_ids()
    for impact_id in impact_ids_result:
        if impact_id not in known_impacts:
            return _reject(
                RejectionReason.UNKNOWN_IMPACT,
                f"impact_evaluation_id {impact_id} is not present in the evidence packet",
            )

    if candidate_id is not None:
        real_candidate = packet.candidate_by_id(candidate_id)
        assert real_candidate is not None
        real_conflicts = set(real_candidate.conflicting_evidence_ids)
        model_conflicts = set(conflicting_ids_result)
        if real_conflicts and model_conflicts < real_conflicts:
            return _reject(
                RejectionReason.DISSENT_OMISSION,
                "output omitted known conflicting evidence the candidate itself carries",
            )

    rationale = raw.get("rationale")
    if not isinstance(rationale, str) or not (1 <= len(rationale) <= _MAX_RATIONALE_LENGTH):
        return _reject(
            RejectionReason.MALFORMED_SCHEMA, "rationale must be a non-blank bounded string"
        )

    fields = ValidatedRecommendationFields(
        recommendation_type=recommendation_type,
        candidate_id=candidate_id,
        supporting_evidence_ids=tuple(sorted(supporting_ids_result, key=str)),
        conflicting_evidence_ids=tuple(sorted(conflicting_ids_result, key=str)),
        impact_evaluation_ids=tuple(sorted(impact_ids_result, key=str)),
        rationale=rationale,
    )
    return RecommendationValidationResult(recommendation_fields=fields, rejection=None)


def _parse_id_list(value: Any) -> list[UUID] | None:
    if not isinstance(value, list):
        return None
    ids: list[UUID] = []
    for item in value:
        if not isinstance(item, str):
            return None
        try:
            ids.append(UUID(item))
        except (ValueError, AttributeError, TypeError):
            return None
    return ids


def _reject(reason: RejectionReason, detail: str) -> RecommendationValidationResult:
    return RecommendationValidationResult(
        recommendation_fields=None, rejection=ValidationRejection(reason=reason, detail=detail)
    )
