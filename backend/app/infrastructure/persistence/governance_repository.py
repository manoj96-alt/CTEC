from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.governance_engine import (
    ExceptionAuthorizationReference,
    GovernanceConfidence,
    GovernanceConfidenceLevel,
    GovernanceEvaluationModel,
    GovernanceEvaluationRecord,
    GovernanceExplanation,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    PolicyVersion,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.assertion_record import AssertionRecordModel
from app.infrastructure.persistence.models.decision_evaluation import (
    DecisionEvaluationGroupORM,
    DecisionEvaluationORM,
)
from app.infrastructure.persistence.models.entity_resolution import (
    EnterpriseEntityResolutionRecordModel,
)
from app.infrastructure.persistence.models.governance_evaluation import GovernanceEvaluationORM
from app.infrastructure.persistence.models.knowledge_evaluation import (
    KnowledgeEvaluationRecordModel,
)
from app.infrastructure.persistence.models.semantic_resolution import SemanticResolutionRecordModel

GOVERNED_RECORD_MODELS: dict[str, type[object]] = {
    "Enterprise Entity Resolution": EnterpriseEntityResolutionRecordModel,
    "Semantic Resolution": SemanticResolutionRecordModel,
    "Assertion": AssertionRecordModel,
    "Knowledge Evaluation": KnowledgeEvaluationRecordModel,
    "Decision Evaluation": DecisionEvaluationORM,
    # Gate F (CDD-015 §16 item 5; merged Gate F Governed Impact Decision
    # Policy Clarification and Remediation Report, PR #69): the
    # `decision_evaluations` group row, referenced once per Gate F
    # evaluation by its single `governance_evaluation_records` row. No
    # other change to this dict, or to any other method in this file, is
    # authorized.
    "DecisionEvaluation": DecisionEvaluationGroupORM,
}


@dataclass(frozen=True, slots=True)
class GovernancePersistenceModel:
    evaluation: GovernanceEvaluationModel


@dataclass(frozen=True, slots=True)
class CurrentGovernanceProjection:
    governed_record_reference: UUID
    governing_policy_reference: str
    record: GovernanceEvaluationRecord | None


@dataclass(frozen=True, slots=True)
class GovernanceHistoryProjection:
    governed_record_reference: UUID
    governing_policy_reference: str
    records: tuple[GovernanceEvaluationRecord, ...]


class GovernanceEvaluationRepository(Protocol):
    def append(self, persistence: GovernancePersistenceModel) -> None: ...

    def history(
        self, governed_record_reference: UUID, governing_policy_reference: str
    ) -> GovernanceHistoryProjection: ...

    def current(
        self,
        governed_record_reference: UUID,
        governing_policy_reference: str,
        *,
        as_of: datetime,
    ) -> CurrentGovernanceProjection: ...

    def policy_trace(self, policy_reference: str, policy_version: str) -> tuple[UUID, ...]: ...


class GovernanceEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, persistence: GovernancePersistenceModel) -> None:
        record = persistence.evaluation.record
        model_type = GOVERNED_RECORD_MODELS.get(record.governed_record_type)
        if model_type is None:
            raise ValidationException("Governed Record Type is not authorized")
        if self.session.get(model_type, record.governed_record_reference.value) is None:
            raise ValidationException("Governed Record Reference does not exist")
        self.session.add(self._to_orm(record))

    def history(
        self, governed_record_reference: UUID, governing_policy_reference: str
    ) -> GovernanceHistoryProjection:
        records = tuple(
            self._to_domain(model)
            for model in self.session.scalars(
                self._ordered_statement(governed_record_reference, governing_policy_reference)
            )
        )
        return GovernanceHistoryProjection(
            governed_record_reference, governing_policy_reference, records
        )

    def current(
        self,
        governed_record_reference: UUID,
        governing_policy_reference: str,
        *,
        as_of: datetime,
    ) -> CurrentGovernanceProjection:
        if as_of.tzinfo is None:
            raise ValueError("Currentness timestamp must be timezone-aware")
        statement = self._ordered_statement(
            governed_record_reference, governing_policy_reference
        ).where(GovernanceEvaluationORM.effective_from <= as_of)
        value = self.session.scalars(statement.limit(1)).first()
        return CurrentGovernanceProjection(
            governed_record_reference,
            governing_policy_reference,
            self._to_domain(value) if value is not None else None,
        )

    def policy_trace(self, policy_reference: str, policy_version: str) -> tuple[UUID, ...]:
        statement = select(GovernanceEvaluationORM.record_identifier).where(
            GovernanceEvaluationORM.governing_policy_reference == policy_reference,
            GovernanceEvaluationORM.policy_version == policy_version,
        )
        return tuple(self.session.scalars(statement))

    @staticmethod
    def _ordered_statement(
        governed_record_reference: UUID, governing_policy_reference: str
    ) -> Select[tuple[GovernanceEvaluationORM]]:
        return (
            select(GovernanceEvaluationORM)
            .where(
                GovernanceEvaluationORM.governed_record_reference == governed_record_reference,
                GovernanceEvaluationORM.governing_policy_reference == governing_policy_reference,
            )
            .order_by(
                GovernanceEvaluationORM.effective_from.desc(),
                GovernanceEvaluationORM.produced_timestamp.desc(),
                GovernanceEvaluationORM.record_identifier.desc(),
            )
        )

    @staticmethod
    def _to_orm(record: GovernanceEvaluationRecord) -> GovernanceEvaluationORM:
        return GovernanceEvaluationORM(
            record_identifier=record.record_identifier,
            governed_record_reference=record.governed_record_reference.value,
            governed_record_type=record.governed_record_type,
            governance_outcome=record.governance_outcome.value,
            governance_confidence=record.governance_confidence.level.value,
            structured_reasons=list(record.governance_explanation.structured_reasons),
            narrative_explanation=record.governance_explanation.narrative,
            governing_policy_reference=record.governing_policy_reference.value,
            policy_version=record.policy_version.value,
            exception_authorization_reference=(
                record.exception_authorization_reference.value
                if record.exception_authorization_reference is not None
                else None
            ),
            effective_from=record.effective_from,
            produced_timestamp=record.produced_timestamp,
        )

    @staticmethod
    def _to_domain(model: GovernanceEvaluationORM) -> GovernanceEvaluationRecord:
        return GovernanceEvaluationRecord(
            record_identifier=model.record_identifier,
            governed_record_reference=GovernedRecordReference(model.governed_record_reference),
            governed_record_type=model.governed_record_type,
            governance_outcome=GovernanceOutcome(model.governance_outcome),
            governance_confidence=GovernanceConfidence(
                GovernanceConfidenceLevel(model.governance_confidence)
            ),
            governance_explanation=GovernanceExplanation(
                tuple(model.structured_reasons), model.narrative_explanation
            ),
            governing_policy_reference=GoverningPolicyReference(model.governing_policy_reference),
            policy_version=PolicyVersion(model.policy_version),
            exception_authorization_reference=(
                ExceptionAuthorizationReference(model.exception_authorization_reference)
                if model.exception_authorization_reference is not None
                else None
            ),
            effective_from=model.effective_from,
            produced_timestamp=model.produced_timestamp,
        )
