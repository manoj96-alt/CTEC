from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.decision_engine import (
    DecisionConfidence,
    DecisionConfidenceLevel,
    DecisionEvaluationGroupModel,
    DecisionEvaluationModel,
    DecisionEvaluationRecord,
    DecisionExplanation,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.models.decision_evaluation import (
    DecisionEvaluationGroupORM,
    DecisionEvaluationORM,
)
from app.infrastructure.persistence.models.knowledge_evaluation import (
    KnowledgeEvaluationRecordModel,
)


@dataclass(frozen=True, slots=True)
class DecisionPersistenceModel:
    evaluation: DecisionEvaluationModel
    policy_satisfied: bool

    @property
    def identity_key(self) -> str:
        record = self.evaluation.record
        knowledge = ",".join(sorted(str(item.value) for item in record.knowledge_references))
        context = (
            str(self.evaluation.business_context_reference.value)
            if self.evaluation.business_context_reference is not None
            else ""
        )
        raw = f"{knowledge}|{record.decision_recommendation.value}|{context}"
        return sha256(raw.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class CurrentDecisionProjection:
    decision_identity_key: str
    record: DecisionEvaluationRecord | None


@dataclass(frozen=True, slots=True)
class DecisionHistoryProjection:
    decision_identity_key: str
    records: tuple[DecisionEvaluationRecord, ...]


class DecisionEvaluationRepository(Protocol):
    """Append-only repository governed by RFC-011 ordering and currentness."""

    def append(self, persistence: DecisionPersistenceModel) -> None: ...

    def history(self, decision_identity_key: str) -> DecisionHistoryProjection:
        """Return the complete ordered immutable record history."""
        ...

    def current(self, decision_identity_key: str, *, as_of: datetime) -> CurrentDecisionProjection:
        """Determine currentness externally without changing record state."""
        ...

    def policy_trace(self, policy_reference: str, policy_version: str) -> tuple[UUID, ...]: ...

    def create_group(self, group: DecisionEvaluationGroupModel) -> None:
        """Persist a new `decision_evaluations` group row (CDD-015 §16 item 1)."""
        ...

    def group_by_id(
        self, decision_evaluation_id: UUID, *, tenant_id: str
    ) -> DecisionEvaluationGroupModel | None:
        """Tenant-scoped lookup. Returns None for a cross-tenant identifier,
        never distinguishing "does not exist" from "belongs to another
        tenant" (CDD-015 §33 tenant isolation requirement)."""
        ...

    def records_for_group(
        self, decision_evaluation_id: UUID, *, tenant_id: str
    ) -> tuple[DecisionEvaluationRecord, ...]:
        """Records belonging to one group, tenant-scoped through the group
        itself. Returns an empty tuple if the group does not exist or does
        not belong to `tenant_id`."""
        ...

    def group_by_logical_execution_id(
        self, logical_execution_id: UUID, *, tenant_id: str
    ) -> DecisionEvaluationGroupModel | None:
        """Tenant-scoped lookup by the audit-trail `logical_execution_id`
        column (CDD-015 §20 F2.2 addition): a future replay/resume caller
        must look up and reuse the same `decision_evaluation_id` for a
        logical decision rather than minting a new one."""
        ...

    def append_group_member(self, persistence: DecisionPersistenceModel) -> None:
        """Persist a `decision_evaluation_records` row belonging to a
        `decision_evaluations` group (CDD-015 §16 item 4), through this
        repository's PUBLIC contract. Distinct from `append()`: Gate F's
        `knowledge_references` point directly at governed
        `assertions`/`institutional_relationships` (CDD-015 §15), not at
        CDD-011's Institutional-Knowledge pipeline, so `append()`'s
        Institutional-Knowledge gate does not apply -- this method requires
        `decision_evaluation_id` to be set instead, and fails closed if the
        referenced group does not exist."""
        ...


class DecisionEvaluationRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def append(self, persistence: DecisionPersistenceModel) -> None:
        record = persistence.evaluation.record
        for reference in record.knowledge_references:
            knowledge = self.session.get(KnowledgeEvaluationRecordModel, reference.value)
            if knowledge is None or knowledge.outcome != "Institutionalized":
                raise ValidationException(
                    "Decision Evaluation requires existing Institutional Knowledge"
                )
        self.session.add(self._to_orm(persistence))

    def history(self, decision_identity_key: str) -> DecisionHistoryProjection:
        values = tuple(
            self._to_domain(model)
            for model in self.session.scalars(self._ordered_statement(decision_identity_key))
        )
        return DecisionHistoryProjection(decision_identity_key, values)

    def current(self, decision_identity_key: str, *, as_of: datetime) -> CurrentDecisionProjection:
        if as_of.tzinfo is None:
            raise ValueError("Currentness timestamp must be timezone-aware")
        statement = self._ordered_statement(decision_identity_key).where(
            DecisionEvaluationORM.effective_from <= as_of
        )
        value = self.session.scalars(statement.limit(1)).first()
        return CurrentDecisionProjection(
            decision_identity_key,
            self._to_domain(value) if value is not None else None,
        )

    def policy_trace(self, policy_reference: str, policy_version: str) -> tuple[UUID, ...]:
        statement = select(DecisionEvaluationORM.record_identifier).where(
            DecisionEvaluationORM.governing_policy_reference == policy_reference,
            DecisionEvaluationORM.policy_version == policy_version,
        )
        return tuple(self.session.scalars(statement))

    def create_group(self, group: DecisionEvaluationGroupModel) -> None:
        self.session.add(
            DecisionEvaluationGroupORM(
                decision_evaluation_id=group.decision_evaluation_id,
                tenant_id=group.tenant_id,
                logical_execution_id=group.logical_execution_id,
                created_at=group.created_at,
            )
        )

    def group_by_id(
        self, decision_evaluation_id: UUID, *, tenant_id: str
    ) -> DecisionEvaluationGroupModel | None:
        statement = select(DecisionEvaluationGroupORM).where(
            DecisionEvaluationGroupORM.decision_evaluation_id == decision_evaluation_id,
            DecisionEvaluationGroupORM.tenant_id == tenant_id,
        )
        model = self.session.scalars(statement).first()
        return self._group_to_domain(model) if model is not None else None

    def records_for_group(
        self, decision_evaluation_id: UUID, *, tenant_id: str
    ) -> tuple[DecisionEvaluationRecord, ...]:
        if self.group_by_id(decision_evaluation_id, tenant_id=tenant_id) is None:
            return ()
        statement = select(DecisionEvaluationORM).where(
            DecisionEvaluationORM.decision_evaluation_id == decision_evaluation_id
        )
        return tuple(self._to_domain(model) for model in self.session.scalars(statement))

    def group_by_logical_execution_id(
        self, logical_execution_id: UUID, *, tenant_id: str
    ) -> DecisionEvaluationGroupModel | None:
        statement = select(DecisionEvaluationGroupORM).where(
            DecisionEvaluationGroupORM.logical_execution_id == logical_execution_id,
            DecisionEvaluationGroupORM.tenant_id == tenant_id,
        )
        model = self.session.scalars(statement).first()
        return self._group_to_domain(model) if model is not None else None

    def append_group_member(self, persistence: DecisionPersistenceModel) -> None:
        model = persistence.evaluation
        if model.decision_evaluation_id is None:
            raise ValidationException("append_group_member requires a decision_evaluation_id")
        if self.session.get(DecisionEvaluationGroupORM, model.decision_evaluation_id.value) is None:
            raise ValidationException("Governed Record Reference does not exist")
        self.session.add(self._to_orm(persistence))

    @staticmethod
    def _group_to_domain(model: DecisionEvaluationGroupORM) -> DecisionEvaluationGroupModel:
        return DecisionEvaluationGroupModel(
            decision_evaluation_id=model.decision_evaluation_id,
            tenant_id=model.tenant_id,
            created_at=model.created_at,
            logical_execution_id=model.logical_execution_id,
        )

    @staticmethod
    def _ordered_statement(identity_key: str) -> Select[tuple[DecisionEvaluationORM]]:
        return (
            select(DecisionEvaluationORM)
            .where(DecisionEvaluationORM.decision_identity_key == identity_key)
            .order_by(
                DecisionEvaluationORM.effective_from.desc(),
                DecisionEvaluationORM.produced_timestamp.desc(),
                DecisionEvaluationORM.record_identifier.desc(),
            )
        )

    @staticmethod
    def _to_orm(persistence: DecisionPersistenceModel) -> DecisionEvaluationORM:
        model = persistence.evaluation
        record = model.record
        return DecisionEvaluationORM(
            record_identifier=record.record_identifier,
            knowledge_references=[str(item.value) for item in record.knowledge_references],
            decision_recommendation=record.decision_recommendation.value,
            evaluation_outcome=record.evaluation_outcome.value,
            decision_confidence=record.decision_confidence.level.value,
            structured_reasons=list(record.decision_explanation.structured_reasons),
            narrative_explanation=record.decision_explanation.narrative,
            governing_policy_reference=record.governing_policy_reference.value,
            policy_version=record.policy_version.value,
            effective_from=record.effective_from,
            produced_timestamp=record.produced_timestamp,
            decision_identity_key=persistence.identity_key,
            business_context_reference=(
                model.business_context_reference.value
                if model.business_context_reference is not None
                else None
            ),
            enterprise_constraint_references=[
                item.value for item in model.enterprise_constraint_references
            ],
            policy_satisfied=persistence.policy_satisfied,
            decision_evaluation_id=(
                model.decision_evaluation_id.value
                if model.decision_evaluation_id is not None
                else None
            ),
        )

    @staticmethod
    def _to_domain(model: DecisionEvaluationORM) -> DecisionEvaluationRecord:
        return DecisionEvaluationRecord(
            record_identifier=model.record_identifier,
            knowledge_references=tuple(
                SupportingKnowledgeReference(UUID(value)) for value in model.knowledge_references
            ),
            decision_recommendation=DecisionRecommendation(model.decision_recommendation),
            evaluation_outcome=EvaluationOutcome(model.evaluation_outcome),
            decision_confidence=DecisionConfidence(
                DecisionConfidenceLevel(model.decision_confidence)
            ),
            decision_explanation=DecisionExplanation(
                tuple(model.structured_reasons), model.narrative_explanation
            ),
            governing_policy_reference=GoverningPolicyReference(model.governing_policy_reference),
            policy_version=PolicyVersion(model.policy_version),
            effective_from=model.effective_from,
            produced_timestamp=model.produced_timestamp,
        )
