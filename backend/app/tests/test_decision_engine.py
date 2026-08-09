from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text

from app.application.decision_engine import DecisionApplicationService, DecisionEvaluationRequest
from app.core.config import Settings
from app.domain.decision_engine import (
    BusinessContextReference,
    CurrentDecisionDeterminationService,
    DecisionConfidence,
    DecisionConfidenceClassificationService,
    DecisionConfidenceLevel,
    DecisionEvaluationModel,
    DecisionEvaluationRecord,
    DecisionEvaluationService,
    DecisionExplanation,
    DecisionHistoryService,
    DecisionRecommendation,
    EvaluationOutcome,
    GoverningPolicyReference,
    HumanOverrideService,
    PolicyTraceabilityService,
    PolicyVersion,
    SupportingKnowledgeReference,
)
from app.domain.decision_engine.configuration import (
    DecisionConfigurationLoader,
    DecisionConfigurationValidator,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.decision_repository import (
    DecisionEvaluationRepositoryImpl,
    DecisionPersistenceModel,
)
from app.infrastructure.persistence.models.decision_evaluation import DecisionEvaluationORM

NOW = datetime(2026, 1, 1, tzinfo=UTC)
POLICY = "SCM-Policy-014"
VERSION = "3.2"


def _record(
    outcome: EvaluationOutcome = EvaluationOutcome.RECOMMENDED,
    *,
    effective_from: datetime = NOW,
    produced_timestamp: datetime = NOW,
    policy_satisfied: bool = True,
    knowledge_id: UUID | None = None,
) -> DecisionEvaluationRecord:
    return DecisionEvaluationService().evaluate(
        knowledge_references=(SupportingKnowledgeReference(knowledge_id or uuid4()),),
        recommendation=DecisionRecommendation("Qualify Alternate Supplier"),
        outcome=outcome,
        confidence=DecisionConfidence(DecisionConfidenceLevel.HIGH),
        explanation=DecisionExplanation(
            ("Strategic supplier risk is High",),
            "The governed policy requires qualification of an alternate supplier.",
        ),
        policy_reference=GoverningPolicyReference(POLICY),
        policy_version=PolicyVersion(VERSION),
        policy_satisfied=policy_satisfied,
        effective_from=effective_from,
        produced_timestamp=produced_timestamp,
    )


def test_recommended_establishes_enterprise_decision() -> None:
    assert _record().establishes_enterprise_decision


@pytest.mark.parametrize("outcome", [EvaluationOutcome.CANDIDATE, EvaluationOutcome.REJECTED])
def test_non_recommended_outcomes_do_not_establish_enterprise_decision(
    outcome: EvaluationOutcome,
) -> None:
    assert not _record(outcome, policy_satisfied=False).establishes_enterprise_decision


def test_recommended_requires_policy_satisfaction() -> None:
    with pytest.raises(ValidationException, match="policy satisfaction"):
        _record(policy_satisfied=False)


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0.95, DecisionConfidenceLevel.HIGH),
        (0.7, DecisionConfidenceLevel.MEDIUM),
        (0.2, DecisionConfidenceLevel.LOW),
    ],
)
def test_decision_confidence_classification(score: float, level: DecisionConfidenceLevel) -> None:
    service = DecisionConfidenceClassificationService(high_threshold=0.9, medium_threshold=0.65)
    assert service.classify(score).level is level


def test_policy_traceability_and_explanation() -> None:
    record = _record()
    assert PolicyTraceabilityService().trace(record) == (POLICY, VERSION)
    assert record.decision_explanation.structured_reasons
    assert record.decision_explanation.narrative


def test_human_override_creates_new_immutable_record() -> None:
    previous = DecisionEvaluationModel(_record(EvaluationOutcome.CANDIDATE))
    replacement = HumanOverrideService(DecisionEvaluationService()).override(
        previous,
        recommendation=DecisionRecommendation("Qualify Alternate Supplier"),
        outcome=EvaluationOutcome.RECOMMENDED,
        confidence=DecisionConfidence(DecisionConfidenceLevel.HIGH),
        explanation=DecisionExplanation(
            ("Authorized human override",), "Supporting rationale is contained here."
        ),
        policy_reference=GoverningPolicyReference(POLICY),
        policy_version=PolicyVersion(VERSION),
        policy_satisfied=True,
        effective_from=NOW + timedelta(days=1),
        produced_timestamp=NOW + timedelta(days=1),
    )
    assert replacement.record.record_identifier != previous.record.record_identifier
    assert previous.record.evaluation_outcome is EvaluationOutcome.CANDIDATE


def test_rfc_011_ordering_and_currentness() -> None:
    first = _record(EvaluationOutcome.CANDIDATE, policy_satisfied=False)
    second = _record(
        effective_from=NOW + timedelta(days=1),
        produced_timestamp=NOW + timedelta(days=1),
    )
    future = _record(
        effective_from=NOW + timedelta(days=10),
        produced_timestamp=NOW + timedelta(days=2),
    )
    records = (first, future, second)
    assert DecisionHistoryService().order(records) == (future, second, first)
    assert (
        CurrentDecisionDeterminationService().determine(records, as_of=NOW + timedelta(days=2))
        == second
    )


def test_identity_includes_optional_business_context() -> None:
    record = _record()
    no_context = DecisionPersistenceModel(DecisionEvaluationModel(record), True)
    with_context = DecisionPersistenceModel(
        DecisionEvaluationModel(record, BusinessContextReference(uuid4())), True
    )
    assert no_context.identity_key != with_context.identity_key


def test_configuration_loading_and_validation() -> None:
    configuration = DecisionConfigurationLoader(
        Settings(
            decision_policy_reference=POLICY,
            decision_policy_version=VERSION,
            decision_high_confidence_threshold=0.85,
            decision_medium_confidence_threshold=0.6,
        )
    ).load()
    DecisionConfigurationValidator().validate(configuration)
    assert configuration.policy.reference == POLICY


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def __iter__(self) -> Iterator[Any]:
        return iter(self.values)

    def first(self) -> Any | None:
        return self.values[0] if self.values else None


class _FakeSession:
    def __init__(self, values: list[Any] | None = None, *, institutionalized: bool = True) -> None:
        self.values = values or []
        self.institutionalized = institutionalized
        self.added: list[Any] = []

    def get(self, model_type: Any, identifier: Any) -> Any:
        del model_type, identifier
        outcome = "Institutionalized" if self.institutionalized else "Candidate"
        return SimpleNamespace(outcome=outcome)

    def add(self, value: Any) -> None:
        self.added.append(value)

    def scalars(self, statement: Any) -> _ScalarResult:
        del statement
        return _ScalarResult(self.values)


def _orm(record: DecisionEvaluationRecord, identity_key: str) -> DecisionEvaluationORM:
    return DecisionEvaluationORM(
        record_identifier=record.record_identifier,
        knowledge_references=[str(value.value) for value in record.knowledge_references],
        decision_recommendation=record.decision_recommendation.value,
        evaluation_outcome=record.evaluation_outcome.value,
        decision_confidence=record.decision_confidence.level.value,
        structured_reasons=list(record.decision_explanation.structured_reasons),
        narrative_explanation=record.decision_explanation.narrative,
        governing_policy_reference=record.governing_policy_reference.value,
        policy_version=record.policy_version.value,
        effective_from=record.effective_from,
        produced_timestamp=record.produced_timestamp,
        decision_identity_key=identity_key,
        business_context_reference=None,
        enterprise_constraint_references=[],
        policy_satisfied=True,
    )


def test_repository_is_append_only_and_requires_institutional_knowledge() -> None:
    persistence = DecisionPersistenceModel(DecisionEvaluationModel(_record()), True)
    session = _FakeSession()
    DecisionEvaluationRepositoryImpl(cast(Any, session)).append(persistence)
    assert isinstance(session.added[0], DecisionEvaluationORM)
    with pytest.raises(ValidationException, match="Institutional Knowledge"):
        DecisionEvaluationRepositoryImpl(cast(Any, _FakeSession(institutionalized=False))).append(
            persistence
        )


def test_repository_history_currentness_and_rfc_ordering() -> None:
    persistence = DecisionPersistenceModel(DecisionEvaluationModel(_record()), True)
    model = _orm(persistence.evaluation.record, persistence.identity_key)
    repository = DecisionEvaluationRepositoryImpl(cast(Any, _FakeSession([model])))
    assert repository.history(persistence.identity_key).records[0] == persistence.evaluation.record
    assert (
        repository.current(persistence.identity_key, as_of=NOW).record
        == persistence.evaluation.record
    )
    sql = str(
        repository._ordered_statement(persistence.identity_key).compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    order = sql.split("ORDER BY", maxsplit=1)[1]
    assert order.index("effective_from DESC") < order.index("produced_timestamp DESC")
    assert order.index("produced_timestamp DESC") < order.index("record_identifier DESC")


def test_application_service_evaluates_and_persists() -> None:
    session = _FakeSession()
    repository = DecisionEvaluationRepositoryImpl(cast(Any, session))
    configuration = DecisionConfigurationLoader(
        Settings(decision_policy_reference=POLICY, decision_policy_version=VERSION)
    ).load()
    response = DecisionApplicationService(
        repository=repository, configuration=configuration
    ).evaluate(
        DecisionEvaluationRequest(
            knowledge_references=(uuid4(),),
            recommendation="Qualify Alternate Supplier",
            outcome=EvaluationOutcome.RECOMMENDED,
            confidence_score=0.95,
            structured_reasons=("Policy conditions satisfied",),
            narrative_explanation="Recommendation established under the governed policy.",
            governing_policy_reference=POLICY,
            policy_version=VERSION,
            policy_satisfied=True,
            effective_from=NOW,
            produced_timestamp=NOW,
        )
    )
    assert response.establishes_enterprise_decision
    assert len(session.added) == 1


def test_decision_architecture_does_not_bypass_prior_cognitive_capabilities() -> None:
    package = Path(__file__).parents[1] / "domain" / "decision_engine"
    source = "\n".join(path.read_text() for path in package.glob("*.py"))
    forbidden_dependencies = (
        "identity_resolution",
        "semantic_resolution",
        "assertion_engine",
        "knowledge_engine.service",
    )
    assert not any(value in source for value in forbidden_dependencies)
    assert not (Path(__file__).parents[1] / "api" / "decision").exists()


def test_decision_migration_and_immutability(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        trigger_count = connection.execute(
            text(
                "SELECT count(DISTINCT trigger_name) FROM information_schema.triggers "
                "WHERE trigger_name = 'decision_evaluation_records_immutable'"
            )
        ).scalar_one()
    assert revision == "0009_api_security_audit"
    assert trigger_count == 1
