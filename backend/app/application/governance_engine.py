from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.governance_engine.configuration import GovernanceConfigurationSchema
from app.domain.governance_engine.model import (
    ExceptionAuthorizationReference,
    GovernanceEvaluationModel,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    PolicyVersion,
)
from app.domain.governance_engine.service import (
    GovernanceAttestationService,
    GovernanceConfidenceClassificationService,
    GovernanceEvaluationService,
    GovernanceExplanationService,
)
from app.infrastructure.persistence.governance_repository import (
    GovernanceEvaluationRepository,
    GovernancePersistenceModel,
)


class ExceptionAuthorizationValidationModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    exception_identifier: UUID
    exception_authority: str = Field(min_length=1)
    exception_reason: str = Field(min_length=1)
    policy_reference: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    effective_from: datetime
    expiration: datetime
    produced_timestamp: datetime

    @model_validator(mode="after")
    def validate_period(self) -> "ExceptionAuthorizationValidationModel":
        timestamps = (self.effective_from, self.expiration, self.produced_timestamp)
        if any(value.tzinfo is None for value in timestamps):
            raise ValueError("Exception Authorization timestamps must be timezone-aware")
        if self.expiration <= self.effective_from:
            raise ValueError("Exception Authorization Expiration must follow Effective From")
        return self


class GovernanceEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    governed_record_reference: UUID
    governed_record_type: str = Field(min_length=1)
    outcome: GovernanceOutcome
    confidence_score: float = Field(ge=0, le=1)
    structured_reasons: tuple[str, ...] = Field(min_length=1)
    narrative_explanation: str = Field(min_length=1)
    governing_policy_reference: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    exception_authorization: ExceptionAuthorizationValidationModel | None = None
    policy_satisfied: bool
    human_review_required: bool = False
    effective_from: datetime
    produced_timestamp: datetime


class GovernanceEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifier: UUID
    outcome: GovernanceOutcome
    confidence: str
    governance_attestation: GovernanceOutcome


class GovernanceHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifiers: tuple[UUID, ...]


class CurrentGovernanceResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifier: UUID | None
    governance_attestation: GovernanceOutcome | None


class GovernanceEvaluationResource(GovernanceEvaluationResponse):
    pass


@dataclass(frozen=True, slots=True)
class GovernanceEvaluatedEvent:
    record_identifier: UUID
    outcome: GovernanceOutcome
    produced_timestamp: datetime


class GovernanceValidationModel:
    AUTHORIZED_RECORD_TYPES = frozenset(
        {
            "Enterprise Entity Resolution",
            "Semantic Resolution",
            "Assertion",
            "Knowledge Evaluation",
            "Decision Evaluation",
        }
    )

    def validate(self, request: GovernanceEvaluationRequest) -> None:
        if request.governed_record_type not in self.AUTHORIZED_RECORD_TYPES:
            raise ValueError("Governed Record Type is not authorized")
        if request.effective_from.tzinfo is None or request.produced_timestamp.tzinfo is None:
            raise ValueError("Governance timestamps must be timezone-aware")
        if not all(reason.strip() for reason in request.structured_reasons):
            raise ValueError("Governance structured reasons must be non-empty")


class ExceptionAuthorizationValidationService:
    def validate(
        self,
        authorization: ExceptionAuthorizationValidationModel | None,
        *,
        outcome: GovernanceOutcome,
        policy_reference: str,
        policy_version: str,
        evaluation_effective_from: datetime,
        authorized_authorities: tuple[str, ...],
    ) -> ExceptionAuthorizationReference | None:
        if outcome is not GovernanceOutcome.EXCEPTION_GRANTED:
            if authorization is not None:
                raise ValueError("Exception Authorization is allowed only for Exception Granted")
            return None
        if authorization is None:
            raise ValueError("Exception Granted requires an Exception Authorization")
        if authorization.exception_authority not in authorized_authorities:
            raise ValueError("Exception Authority is not authorized")
        if (
            authorization.policy_reference != policy_reference
            or authorization.policy_version != policy_version
        ):
            raise ValueError("Exception Authorization does not match the governing policy")
        if not authorization.effective_from <= evaluation_effective_from < authorization.expiration:
            raise ValueError("Exception Authorization is not effective for this evaluation")
        return ExceptionAuthorizationReference(authorization.exception_identifier)


class ConfigurationValidationModel:
    def validate(self, configuration: GovernanceConfigurationSchema) -> None:
        if not configuration.policy.reference or not configuration.policy.version:
            raise ValueError("Governance policy configuration is incomplete")


class GovernanceApplicationService:
    def __init__(
        self,
        *,
        repository: GovernanceEvaluationRepository,
        configuration: GovernanceConfigurationSchema,
    ) -> None:
        self.repository = repository
        self.configuration = configuration

    def evaluate(self, request: GovernanceEvaluationRequest) -> GovernanceEvaluationResponse:
        GovernanceValidationModel().validate(request)
        ConfigurationValidationModel().validate(self.configuration)
        if request.governing_policy_reference != self.configuration.policy.reference:
            raise ValueError("Governing Policy Reference is not configured")
        if request.policy_version != self.configuration.policy.version:
            raise ValueError("Policy Version is not configured")
        exception_reference = ExceptionAuthorizationValidationService().validate(
            request.exception_authorization,
            outcome=request.outcome,
            policy_reference=request.governing_policy_reference,
            policy_version=request.policy_version,
            evaluation_effective_from=request.effective_from,
            authorized_authorities=self.configuration.authorized_exception_authorities,
        )
        explanation = GovernanceExplanationService().explain(
            request.structured_reasons, request.narrative_explanation
        )
        confidence = GovernanceConfidenceClassificationService(
            high_threshold=self.configuration.confidence.high_threshold,
            medium_threshold=self.configuration.confidence.medium_threshold,
        ).classify(request.confidence_score)
        record = GovernanceEvaluationService().evaluate(
            governed_record_reference=GovernedRecordReference(request.governed_record_reference),
            governed_record_type=request.governed_record_type,
            outcome=request.outcome,
            confidence=confidence,
            explanation=explanation,
            policy_reference=GoverningPolicyReference(request.governing_policy_reference),
            policy_version=PolicyVersion(request.policy_version),
            exception_authorization_reference=exception_reference,
            policy_satisfied=request.policy_satisfied,
            human_review_required=request.human_review_required,
            effective_from=request.effective_from,
            produced_timestamp=request.produced_timestamp,
        )
        self.repository.append(GovernancePersistenceModel(GovernanceEvaluationModel(record)))
        attestation = GovernanceAttestationService().derive(record)
        return GovernanceEvaluationResponse(
            record_identifier=record.record_identifier,
            outcome=record.governance_outcome,
            confidence=record.governance_confidence.level.value,
            governance_attestation=attestation,
        )
