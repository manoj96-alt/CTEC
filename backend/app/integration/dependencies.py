from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.orm import Session, sessionmaker

from app.domain.assertion_engine import AssertionEngine, AssertionRecord
from app.domain.decision_engine import (
    DecisionConfidenceClassificationService,
    DecisionEvaluationModel,
    DecisionEvaluationService,
)
from app.domain.governance_engine import (
    GovernanceConfidenceClassificationService,
    GovernanceEvaluationModel,
    GovernanceEvaluationService,
)
from app.domain.identity_resolution import EnterpriseEntityResolutionRecord, EntityResolutionEngine
from app.domain.knowledge_engine import KnowledgeEngine, KnowledgeEvaluationRecord
from app.domain.semantic_resolution import SemanticResolutionEngine, SemanticResolutionRecord
from app.infrastructure.persistence.assertion_record_store import AssertionRecordStore
from app.infrastructure.persistence.decision_repository import (
    DecisionEvaluationRepositoryImpl,
    DecisionPersistenceModel,
)
from app.infrastructure.persistence.entity_resolution_store import EntityResolutionStore
from app.infrastructure.persistence.governance_repository import (
    GovernanceEvaluationRepositoryImpl,
    GovernancePersistenceModel,
)
from app.infrastructure.persistence.knowledge_evaluation_store import KnowledgeEvaluationStore
from app.infrastructure.persistence.semantic_resolution_store import SemanticResolutionStore


class CapabilityPersistence(Protocol):
    def entity_resolution(self, record: EnterpriseEntityResolutionRecord) -> None: ...
    def semantic_resolution(self, record: SemanticResolutionRecord) -> None: ...
    def assertion(self, record: AssertionRecord) -> None: ...
    def knowledge(self, record: KnowledgeEvaluationRecord) -> None: ...
    def decision(self, model: DecisionEvaluationModel, *, policy_satisfied: bool) -> None: ...
    def governance(self, model: GovernanceEvaluationModel) -> None: ...


@dataclass(frozen=True, slots=True)
class IntegrationDependencies:
    entity_resolution: EntityResolutionEngine
    semantic_resolution: SemanticResolutionEngine
    assertion: AssertionEngine
    knowledge: KnowledgeEngine
    decision: DecisionEvaluationService
    decision_confidence: DecisionConfidenceClassificationService
    governance: GovernanceEvaluationService
    governance_confidence: GovernanceConfidenceClassificationService
    persistence: CapabilityPersistence
    clock: Callable[[], datetime]


class SqlAlchemyCapabilityPersistence:
    """Capability-local transactions over the existing immutable record stores."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def _write(self, operation: Callable[[Session], None]) -> None:
        session = self._session_factory()
        try:
            operation(session)
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def entity_resolution(self, record: EnterpriseEntityResolutionRecord) -> None:
        self._write(lambda session: EntityResolutionStore(session).append(record))

    def semantic_resolution(self, record: SemanticResolutionRecord) -> None:
        self._write(lambda session: SemanticResolutionStore(session).append(record))

    def assertion(self, record: AssertionRecord) -> None:
        self._write(lambda session: AssertionRecordStore(session).append(record))

    def knowledge(self, record: KnowledgeEvaluationRecord) -> None:
        self._write(lambda session: KnowledgeEvaluationStore(session).append(record))

    def decision(self, model: DecisionEvaluationModel, *, policy_satisfied: bool) -> None:
        self._write(
            lambda session: DecisionEvaluationRepositoryImpl(session).append(
                DecisionPersistenceModel(model, policy_satisfied)
            )
        )

    def governance(self, model: GovernanceEvaluationModel) -> None:
        self._write(
            lambda session: GovernanceEvaluationRepositoryImpl(session).append(
                GovernancePersistenceModel(model)
            )
        )
