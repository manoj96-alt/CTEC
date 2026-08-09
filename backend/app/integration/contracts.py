from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

SUPPORTED_CONTROL_METADATA_VERSION = "1.0"
SUPPLIER_RISK_CONDITION_ID = UUID("cdbb90c4-6518-59cd-aa13-989d2717a256")
HAS_ACTIVE_RISK_CONDITION_ID = UUID("de39e820-d95c-51ce-9cd3-da98cb072a36")


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MATERIAL = "MATERIAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SourcingStatus(StrEnum):
    SINGLE_SOURCE = "SINGLE_SOURCE"
    DUAL_SOURCE = "DUAL_SOURCE"
    NO_QUALIFIED_SOURCE = "NO_QUALIFIED_SOURCE"
    INDETERMINATE = "INDETERMINATE"


class SourcingRecommendation(StrEnum):
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    QUALIFY_SECOND_SOURCE = "QUALIFY_SECOND_SOURCE"
    ACTIVATE_APPROVED_SECOND_SOURCE = "ACTIVATE_APPROVED_SECOND_SOURCE"
    ESCALATE_FOR_HUMAN_REVIEW = "ESCALATE_FOR_HUMAN_REVIEW"
    NO_AUTOMATED_RECOMMENDATION = "NO_AUTOMATED_RECOMMENDATION"


class GovernanceStanding(StrEnum):
    APPROVED = "APPROVED"
    CONDITIONALLY_APPROVED = "CONDITIONALLY_APPROVED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REJECTED = "REJECTED"
    INDETERMINATE = "INDETERMINATE"

    @property
    def actionable(self) -> bool:
        return self is GovernanceStanding.APPROVED


class GateOutcome(StrEnum):
    CONTINUE = "CONTINUE"
    BUSINESS_GATED = "BUSINESS_GATED"


class DiagnosticCode(StrEnum):
    IDENTITY_NOT_RESOLVED = "IDENTITY_NOT_RESOLVED"
    SEMANTICS_NOT_RESOLVED = "SEMANTICS_NOT_RESOLVED"
    EVIDENCE_INDETERMINATE = "EVIDENCE_INDETERMINATE"
    ASSERTION_NOT_ESTABLISHED = "ASSERTION_NOT_ESTABLISHED"
    KNOWLEDGE_NOT_INSTITUTIONALIZED = "KNOWLEDGE_NOT_INSTITUTIONALIZED"
    DECISION_NOT_VALID = "DECISION_NOT_VALID"
    GOVERNANCE_NON_ACTIONABLE = "GOVERNANCE_NON_ACTIONABLE"
    TECHNICAL_FAILURE = "TECHNICAL_FAILURE"


def _utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} must be timezone-aware UTC")


@dataclass(frozen=True, slots=True)
class AuthorityContext:
    principal_id: str
    principal_type: str
    organization_id: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    authorization_decision: str
    authorization_reference: str
    trust_source: str
    request_id: UUID
    correlation_id: UUID
    issued_at: datetime
    expires_at: datetime
    schema_version: str = SUPPORTED_CONTROL_METADATA_VERSION
    delegation_reference: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.principal_id,
            self.principal_type,
            self.organization_id,
            self.authorization_decision,
            self.authorization_reference,
            self.trust_source,
            self.schema_version,
        )
        if any(not value.strip() for value in required):
            raise ValueError("AuthorityContext required values cannot be empty")
        _utc(self.issued_at, "AuthorityContext.issued_at")
        _utc(self.expires_at, "AuthorityContext.expires_at")
        if self.expires_at <= self.issued_at:
            raise ValueError("AuthorityContext expiration must follow issuance")

    def validate_for(self, *, request_id: UUID, correlation_id: UUID, now: datetime) -> None:
        _utc(now, "trusted boundary time")
        if self.schema_version != SUPPORTED_CONTROL_METADATA_VERSION:
            raise ValueError("Unsupported AuthorityContext version")
        if self.request_id != request_id or self.correlation_id != correlation_id:
            raise ValueError("AuthorityContext identifiers conflict with invocation")
        if self.authorization_decision != "AUTHORIZED":
            raise PermissionError("AuthorityContext is not authorized")
        if not self.roles or not self.scopes or now < self.issued_at or now >= self.expires_at:
            raise PermissionError("AuthorityContext is incomplete, premature, or expired")


@dataclass(frozen=True, slots=True)
class SourceObservation:
    observation_id: UUID
    source_system_reference: UUID
    source_record_reference: str
    subject_type: str
    subject_id: UUID
    observation_type: str
    value: str
    severity: RiskSeverity
    observed_at: datetime
    received_at: datetime
    evidence_reference: str
    schema_version: str = "1.0"
    conflicting: bool = False

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (
                self.source_record_reference,
                self.subject_type,
                self.observation_type,
                self.value,
                self.evidence_reference,
                self.schema_version,
            )
        ):
            raise ValueError("SourceObservation required values cannot be empty")
        _utc(self.observed_at, "SourceObservation.observed_at")
        _utc(self.received_at, "SourceObservation.received_at")


@dataclass(frozen=True, slots=True)
class SupplierEligibility:
    supplier_entity_id: UUID
    qualified: bool
    approved: bool
    contractually_eligible: bool
    usable_capacity: bool
    operationally_ready: bool

    @property
    def eligible(self) -> bool:
        return (
            self.qualified
            and self.approved
            and self.contractually_eligible
            and self.usable_capacity
        )


@dataclass(frozen=True, slots=True)
class AcceptanceEvidenceInput:
    evidence_id: UUID
    authority: str
    policy_reference: str
    policy_version: str
    accepted_at: datetime


@dataclass(frozen=True, slots=True)
class SupplierRiskRequest:
    supplier_names: tuple[str, ...]
    source_object_ids: tuple[UUID, ...]
    enterprise_candidates: tuple[tuple[UUID, str], ...]
    semantic_terms: tuple[str, ...]
    semantic_candidates: tuple[tuple[UUID, str], ...]
    context_id: UUID
    material_id: UUID
    facility_or_region_id: UUID
    effective_at: datetime
    observations: tuple[SourceObservation, ...]
    supplier_eligibility: tuple[SupplierEligibility, ...]
    identity_score: float
    semantic_score: float
    assertion_score: float
    knowledge_score: float
    decision_score: float
    governance_score: float
    identity_policy_version: str
    semantic_policy_version: str
    assertion_policy_version: str
    knowledge_policy_version: str
    decision_policy_reference: str
    decision_policy_version: str
    decision_policy_rule: str
    governance_policy_reference: str
    governance_policy_version: str
    acceptance_evidence: AcceptanceEvidenceInput | None
    governance_conditions: tuple[str, ...] = ()
    verified_conditions: tuple[str, ...] = ()
    exceptional_policy_condition: bool = False

    def __post_init__(self) -> None:
        _utc(self.effective_at, "SupplierRiskRequest.effective_at")
        if not self.source_object_ids or not self.supplier_names:
            raise ValueError("Supplier risk request requires source objects and supplier names")


@dataclass(frozen=True, slots=True)
class PolicyTraceability:
    policy_identifier: str
    policy_version: str
    evaluated_rule: str
    relevant_inputs: tuple[str, ...]
    decision_outcome: str
    supporting_evidence_references: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProducedRecordReferences:
    entity_resolution: UUID | None = None
    semantic_resolution: UUID | None = None
    assertion: UUID | None = None
    knowledge_evaluation: UUID | None = None
    decision_evaluation: UUID | None = None
    governance_evaluation: UUID | None = None


@dataclass(frozen=True, slots=True)
class IntegrationEnvelope:
    request: SupplierRiskRequest
    references: ProducedRecordReferences = field(default_factory=ProducedRecordReferences)
    enterprise_entity_id: UUID | None = None
    institutional_concept_id: UUID | None = None
    sourcing_status: SourcingStatus | None = None
    recommendation: SourcingRecommendation | None = None
    governance_standing: GovernanceStanding | None = None
    conditions_verified: bool = False
    gate_outcome: GateOutcome = GateOutcome.CONTINUE
    diagnostic_code: DiagnosticCode | None = None
    policy_traceability: PolicyTraceability | None = None
    capability_timestamps: tuple[tuple[str, datetime, datetime], ...] = ()

    def gated(
        self, code: DiagnosticCode, *, standing: GovernanceStanding | None = None
    ) -> IntegrationEnvelope:
        return IntegrationEnvelope(
            **{
                **{
                    field.name: getattr(self, field.name)
                    for field in self.__dataclass_fields__.values()
                },
                "gate_outcome": GateOutcome.BUSINESS_GATED,
                "diagnostic_code": code,
                "governance_standing": standing,
            }
        )

    def to_bytes(self) -> bytes:
        return json.dumps(
            asdict(self), default=_json_default, sort_keys=True, separators=(",", ":")
        ).encode()

    @classmethod
    def from_bytes(cls, value: bytes) -> IntegrationEnvelope:
        raw = json.loads(value)
        request_raw = raw["request"]
        request_raw["source_object_ids"] = tuple(
            UUID(item) for item in request_raw["source_object_ids"]
        )
        request_raw["enterprise_candidates"] = tuple(
            (UUID(a), b) for a, b in request_raw["enterprise_candidates"]
        )
        request_raw["semantic_candidates"] = tuple(
            (UUID(a), b) for a, b in request_raw["semantic_candidates"]
        )
        for name in ("context_id", "material_id", "facility_or_region_id"):
            request_raw[name] = UUID(request_raw[name])
        request_raw["effective_at"] = datetime.fromisoformat(request_raw["effective_at"])
        request_raw["observations"] = tuple(
            _observation(item) for item in request_raw["observations"]
        )
        request_raw["supplier_eligibility"] = tuple(
            SupplierEligibility(
                UUID(item["supplier_entity_id"]),
                *[
                    item[name]
                    for name in (
                        "qualified",
                        "approved",
                        "contractually_eligible",
                        "usable_capacity",
                        "operationally_ready",
                    )
                ],
            )
            for item in request_raw["supplier_eligibility"]
        )
        evidence = request_raw.get("acceptance_evidence")
        if evidence:
            request_raw["acceptance_evidence"] = AcceptanceEvidenceInput(
                UUID(evidence["evidence_id"]),
                evidence["authority"],
                evidence["policy_reference"],
                evidence["policy_version"],
                datetime.fromisoformat(evidence["accepted_at"]),
            )
        for name in (
            "supplier_names",
            "semantic_terms",
            "governance_conditions",
            "verified_conditions",
        ):
            request_raw[name] = tuple(request_raw[name])
        refs = ProducedRecordReferences(
            **{key: UUID(item) if item else None for key, item in raw["references"].items()}
        )
        trace = raw.get("policy_traceability")
        policy_trace = (
            PolicyTraceability(
                **{
                    **trace,
                    "relevant_inputs": tuple(trace["relevant_inputs"]),
                    "supporting_evidence_references": tuple(
                        trace["supporting_evidence_references"]
                    ),
                }
            )
            if trace
            else None
        )
        timestamps = tuple(
            (name, datetime.fromisoformat(start), datetime.fromisoformat(end))
            for name, start, end in raw["capability_timestamps"]
        )
        return cls(
            request=SupplierRiskRequest(**request_raw),
            references=refs,
            enterprise_entity_id=(
                UUID(raw["enterprise_entity_id"]) if raw.get("enterprise_entity_id") else None
            ),
            institutional_concept_id=(
                UUID(raw["institutional_concept_id"])
                if raw.get("institutional_concept_id")
                else None
            ),
            sourcing_status=(
                SourcingStatus(raw["sourcing_status"]) if raw.get("sourcing_status") else None
            ),
            recommendation=(
                SourcingRecommendation(raw["recommendation"]) if raw.get("recommendation") else None
            ),
            governance_standing=(
                GovernanceStanding(raw["governance_standing"])
                if raw.get("governance_standing")
                else None
            ),
            conditions_verified=raw["conditions_verified"],
            gate_outcome=GateOutcome(raw["gate_outcome"]),
            diagnostic_code=(
                DiagnosticCode(raw["diagnostic_code"]) if raw.get("diagnostic_code") else None
            ),
            policy_traceability=policy_trace,
            capability_timestamps=timestamps,
        )


def _observation(item: dict[str, Any]) -> SourceObservation:
    return SourceObservation(
        observation_id=UUID(item["observation_id"]),
        source_system_reference=UUID(item["source_system_reference"]),
        source_record_reference=item["source_record_reference"],
        subject_type=item["subject_type"],
        subject_id=UUID(item["subject_id"]),
        observation_type=item["observation_type"],
        value=item["value"],
        severity=RiskSeverity(item["severity"]),
        observed_at=datetime.fromisoformat(item["observed_at"]),
        received_at=datetime.fromisoformat(item["received_at"]),
        evidence_reference=item["evidence_reference"],
        schema_version=item["schema_version"],
        conflicting=item["conflicting"],
    )


def _json_default(value: object) -> str:
    if isinstance(value, (UUID, datetime, StrEnum)):
        return str(value)
    raise TypeError(f"Unsupported integration value: {type(value).__name__}")
