from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.decision_engine.configuration import DecisionConfigurationSchema
from app.domain.decision_engine.model import (
    BusinessContextReference,
    DecisionEvaluationGroupReference,
    DecisionEvaluationModel,
    EnterpriseConstraintReference,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.decision_engine.service import (
    DecisionConfidenceClassificationService,
    DecisionEvaluationService,
    DecisionExplanationService,
    DecisionRecommendationService,
)
from app.infrastructure.persistence.decision_repository import (
    DecisionEvaluationRepository,
    DecisionPersistenceModel,
)


class DecisionEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    knowledge_references: tuple[UUID, ...] = Field(min_length=1)
    recommendation: str = Field(min_length=1)
    outcome: EvaluationOutcome
    confidence_score: float = Field(ge=0, le=1)
    structured_reasons: tuple[str, ...] = Field(min_length=1)
    narrative_explanation: str = Field(min_length=1)
    governing_policy_reference: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    policy_satisfied: bool
    effective_from: datetime
    produced_timestamp: datetime
    business_context_reference: UUID | None = None
    enterprise_constraint_references: tuple[str, ...] = ()
    decision_evaluation_id: UUID | None = None


class DecisionEvaluationResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifier: UUID
    outcome: EvaluationOutcome
    confidence: str
    establishes_enterprise_decision: bool


class DecisionHistoryResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifiers: tuple[UUID, ...]


class CurrentDecisionResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_identifier: UUID | None
    establishes_enterprise_decision: bool


class DecisionEvaluationResource(DecisionEvaluationResponse):
    pass


@dataclass(frozen=True, slots=True)
class DecisionEvaluatedEvent:
    record_identifier: UUID
    outcome: EvaluationOutcome
    produced_timestamp: datetime


class DecisionValidationModel:
    def validate(self, request: DecisionEvaluationRequest) -> None:
        if request.effective_from.tzinfo is None or request.produced_timestamp.tzinfo is None:
            raise ValueError("Decision timestamps must be timezone-aware")
        if len(set(request.knowledge_references)) != len(request.knowledge_references):
            raise ValueError("Knowledge References must be unique")


class PolicyValidationModel:
    def validate(
        self, request: DecisionEvaluationRequest, configuration: DecisionConfigurationSchema
    ) -> None:
        if request.governing_policy_reference != configuration.policy.reference:
            raise ValueError("Governing Policy Reference is not configured")
        if request.policy_version != configuration.policy.version:
            raise ValueError("Policy Version is not configured")


class ConfigurationValidationModel:
    def validate(self, configuration: DecisionConfigurationSchema) -> None:
        if not configuration.policy.reference or not configuration.policy.version:
            raise ValueError("Decision policy configuration is incomplete")


class DecisionApplicationService:
    def __init__(
        self,
        *,
        repository: DecisionEvaluationRepository,
        configuration: DecisionConfigurationSchema,
    ) -> None:
        self.repository = repository
        self.configuration = configuration

    def evaluate(self, request: DecisionEvaluationRequest) -> DecisionEvaluationResponse:
        DecisionValidationModel().validate(request)
        PolicyValidationModel().validate(request, self.configuration)
        ConfigurationValidationModel().validate(self.configuration)
        recommendation = DecisionRecommendationService().recommend(request.recommendation)
        explanation = DecisionExplanationService().explain(
            request.structured_reasons, request.narrative_explanation
        )
        confidence = DecisionConfidenceClassificationService(
            high_threshold=self.configuration.confidence.high_threshold,
            medium_threshold=self.configuration.confidence.medium_threshold,
        ).classify(request.confidence_score)
        record = DecisionEvaluationService().evaluate(
            knowledge_references=tuple(
                SupportingKnowledgeReference(value) for value in request.knowledge_references
            ),
            recommendation=recommendation,
            outcome=request.outcome,
            confidence=confidence,
            explanation=explanation,
            policy_reference=GoverningPolicyReference(request.governing_policy_reference),
            policy_version=PolicyVersion(request.policy_version),
            policy_satisfied=request.policy_satisfied,
            effective_from=request.effective_from,
            produced_timestamp=request.produced_timestamp,
        )
        evaluation = DecisionEvaluationModel(
            record=record,
            business_context_reference=(
                BusinessContextReference(request.business_context_reference)
                if request.business_context_reference is not None
                else None
            ),
            enterprise_constraint_references=tuple(
                EnterpriseConstraintReference(value)
                for value in request.enterprise_constraint_references
            ),
            decision_evaluation_id=(
                DecisionEvaluationGroupReference(request.decision_evaluation_id)
                if request.decision_evaluation_id is not None
                else None
            ),
        )
        self.repository.append(DecisionPersistenceModel(evaluation, request.policy_satisfied))
        return DecisionEvaluationResponse(
            record_identifier=record.record_identifier,
            outcome=record.evaluation_outcome,
            confidence=record.decision_confidence.level.value,
            establishes_enterprise_decision=record.establishes_enterprise_decision,
        )
