from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, text

from app.application.governance_engine import (
    ExceptionAuthorizationValidationModel,
    GovernanceApplicationService,
    GovernanceEvaluatedEvent,
    GovernanceEvaluationRequest,
)
from app.core.config import Settings
from app.domain.governance_engine import (
    CurrentGovernanceDeterminationService,
    ExceptionAuthorizationReference,
    GovernanceAttestationService,
    GovernanceConfidence,
    GovernanceConfidenceClassificationService,
    GovernanceConfidenceLevel,
    GovernanceEvaluationModel,
    GovernanceEvaluationRecord,
    GovernanceEvaluationService,
    GovernanceExplanation,
    GovernanceHistoryService,
    GovernanceOutcome,
    GovernedRecordReference,
    GoverningPolicyReference,
    HumanOverrideService,
    PolicyTraceabilityService,
    PolicyVersion,
)
from app.domain.governance_engine.configuration import (
    GovernanceConfigurationLoader,
    GovernanceConfigurationValidator,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.governance_repository import (
    GovernanceEvaluationRepositoryImpl,
    GovernancePersistenceModel,
)
from app.infrastructure.persistence.models.governance_evaluation import GovernanceEvaluationORM

NOW = datetime(2026, 1, 1, tzinfo=UTC)
POLICY = "DG-POL-021"
VERSION = "2.4"
AUTHORITY = "Enterprise Governance Council"


def _record(
    outcome: GovernanceOutcome = GovernanceOutcome.COMPLIANT,
    *,
    record_reference: UUID | None = None,
    effective_from: datetime = NOW,
    produced_timestamp: datetime = NOW,
    exception_reference: UUID | None = None,
    policy_satisfied: bool | None = None,
    human_review_required: bool = False,
) -> GovernanceEvaluationRecord:
    if policy_satisfied is None:
        policy_satisfied = outcome is GovernanceOutcome.COMPLIANT
    return GovernanceEvaluationService().evaluate(
        governed_record_reference=GovernedRecordReference(record_reference or uuid4()),
        governed_record_type="Knowledge Evaluation",
        outcome=outcome,
        confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
        explanation=GovernanceExplanation(
            ("Policy conditions evaluated",),
            "The governed record was evaluated against the governing policy.",
        ),
        policy_reference=GoverningPolicyReference(POLICY),
        policy_version=PolicyVersion(VERSION),
        exception_authorization_reference=(
            ExceptionAuthorizationReference(exception_reference)
            if exception_reference is not None
            else None
        ),
        policy_satisfied=policy_satisfied,
        human_review_required=human_review_required,
        effective_from=effective_from,
        produced_timestamp=produced_timestamp,
    )


@pytest.mark.parametrize(
    "outcome",
    [
        GovernanceOutcome.COMPLIANT,
        GovernanceOutcome.NON_COMPLIANT,
        GovernanceOutcome.EXCEPTION_GRANTED,
        GovernanceOutcome.REQUIRES_REVIEW,
    ],
)
def test_every_outcome_derives_exactly_one_outcome_neutral_attestation(
    outcome: GovernanceOutcome,
) -> None:
    record = _record(
        outcome,
        exception_reference=uuid4() if outcome is GovernanceOutcome.EXCEPTION_GRANTED else None,
        human_review_required=outcome is GovernanceOutcome.REQUIRES_REVIEW,
    )
    assert GovernanceAttestationService().derive(record) is outcome


def test_governance_outcome_rules_are_enforced() -> None:
    with pytest.raises(ValidationException, match="policy satisfaction"):
        _record(GovernanceOutcome.COMPLIANT, policy_satisfied=False)
    with pytest.raises(ValidationException, match="policy violation"):
        _record(GovernanceOutcome.NON_COMPLIANT, policy_satisfied=True)
    with pytest.raises(ValidationException, match="Exception Authorization"):
        _record(GovernanceOutcome.EXCEPTION_GRANTED)
    with pytest.raises(ValidationException, match="human governance review"):
        _record(GovernanceOutcome.REQUIRES_REVIEW)
    with pytest.raises(ValidationException, match="allowed only"):
        _record(GovernanceOutcome.COMPLIANT, exception_reference=uuid4())


@pytest.mark.parametrize(
    ("score", "level"),
    [
        (0.95, GovernanceConfidenceLevel.HIGH),
        (0.70, GovernanceConfidenceLevel.MEDIUM),
        (0.20, GovernanceConfidenceLevel.LOW),
    ],
)
def test_governance_confidence_classification(
    score: float, level: GovernanceConfidenceLevel
) -> None:
    service = GovernanceConfidenceClassificationService(high_threshold=0.9, medium_threshold=0.65)
    assert service.classify(score).level is level


def test_explanation_and_policy_traceability() -> None:
    record = _record()
    assert record.governance_explanation.structured_reasons
    assert record.governance_explanation.narrative
    assert PolicyTraceabilityService().trace(record) == (POLICY, VERSION)


def test_rfc_011_history_and_currentness() -> None:
    record_reference = uuid4()
    first = _record(record_reference=record_reference)
    second = _record(
        record_reference=record_reference,
        effective_from=NOW + timedelta(days=1),
        produced_timestamp=NOW + timedelta(days=1),
    )
    future = _record(
        record_reference=record_reference,
        effective_from=NOW + timedelta(days=10),
        produced_timestamp=NOW + timedelta(days=2),
    )
    records = (first, future, second)
    assert GovernanceHistoryService().order(records) == (future, second, first)
    assert (
        CurrentGovernanceDeterminationService().determine(records, as_of=NOW + timedelta(days=2))
        == second
    )


def test_human_override_creates_new_immutable_record() -> None:
    previous = GovernanceEvaluationModel(_record(GovernanceOutcome.NON_COMPLIANT))
    replacement = HumanOverrideService(GovernanceEvaluationService()).override(
        previous,
        outcome=GovernanceOutcome.COMPLIANT,
        confidence=GovernanceConfidence(GovernanceConfidenceLevel.HIGH),
        explanation=GovernanceExplanation(
            ("Authorized human override",), "Policy satisfaction was confirmed."
        ),
        policy_version=PolicyVersion("2.5"),
        exception_authorization_reference=None,
        policy_satisfied=True,
        human_review_required=False,
        effective_from=NOW + timedelta(days=1),
        produced_timestamp=NOW + timedelta(days=1),
    )
    assert replacement.record.record_identifier != previous.record.record_identifier
    assert previous.record.governance_outcome is GovernanceOutcome.NON_COMPLIANT


def test_configuration_loading_and_validation() -> None:
    configuration = GovernanceConfigurationLoader(
        Settings(
            governance_policy_reference=POLICY,
            governance_policy_version=VERSION,
            governance_authorized_exception_authorities=[AUTHORITY],
            governance_high_confidence_threshold=0.85,
            governance_medium_confidence_threshold=0.60,
        )
    ).load()
    GovernanceConfigurationValidator().validate(configuration)
    assert configuration.policy.reference == POLICY
    assert configuration.authorized_exception_authorities == (AUTHORITY,)


class _ScalarResult:
    def __init__(self, values: list[Any]) -> None:
        self.values = values

    def __iter__(self) -> Iterator[Any]:
        return iter(self.values)

    def first(self) -> Any | None:
        return self.values[0] if self.values else None


class _FakeSession:
    def __init__(self, values: list[Any] | None = None, *, governed_exists: bool = True) -> None:
        self.values = values or []
        self.governed_exists = governed_exists
        self.added: list[Any] = []

    def get(self, model_type: Any, identifier: Any) -> Any | None:
        del model_type, identifier
        return SimpleNamespace() if self.governed_exists else None

    def add(self, value: Any) -> None:
        self.added.append(value)

    def scalars(self, statement: Any) -> _ScalarResult:
        del statement
        return _ScalarResult(self.values)


def _orm(record: Any) -> GovernanceEvaluationORM:
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
        exception_authorization_reference=None,
        effective_from=record.effective_from,
        produced_timestamp=record.produced_timestamp,
    )


def test_repository_is_append_only_and_validates_governed_record() -> None:
    persistence = GovernancePersistenceModel(GovernanceEvaluationModel(_record()))
    session = _FakeSession()
    GovernanceEvaluationRepositoryImpl(cast(Any, session)).append(persistence)
    assert isinstance(session.added[0], GovernanceEvaluationORM)
    with pytest.raises(ValidationException, match="does not exist"):
        GovernanceEvaluationRepositoryImpl(cast(Any, _FakeSession(governed_exists=False))).append(
            persistence
        )


def test_repository_history_currentness_policy_trace_and_ordering() -> None:
    record = _record()
    repository = GovernanceEvaluationRepositoryImpl(cast(Any, _FakeSession([_orm(record)])))
    reference = record.governed_record_reference.value
    assert repository.history(reference, POLICY).records == (record,)
    assert repository.current(reference, POLICY, as_of=NOW).record == record
    trace_repository = GovernanceEvaluationRepositoryImpl(
        cast(Any, _FakeSession([record.record_identifier]))
    )
    assert trace_repository.policy_trace(POLICY, VERSION) == (record.record_identifier,)
    sql = str(
        repository._ordered_statement(reference, POLICY).compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    order = sql.split("ORDER BY", maxsplit=1)[1]
    assert order.index("effective_from DESC") < order.index("produced_timestamp DESC")
    assert order.index("produced_timestamp DESC") < order.index("record_identifier DESC")


def _exception() -> ExceptionAuthorizationValidationModel:
    return ExceptionAuthorizationValidationModel(
        exception_identifier=uuid4(),
        exception_authority=AUTHORITY,
        exception_reason="Temporary governed deviation",
        policy_reference=POLICY,
        policy_version=VERSION,
        effective_from=NOW - timedelta(days=1),
        expiration=NOW + timedelta(days=30),
        produced_timestamp=NOW - timedelta(days=2),
    )


def test_application_service_validates_exception_and_persists() -> None:
    session = _FakeSession()
    configuration = GovernanceConfigurationLoader(
        Settings(
            governance_policy_reference=POLICY,
            governance_policy_version=VERSION,
            governance_authorized_exception_authorities=[AUTHORITY],
        )
    ).load()
    response = GovernanceApplicationService(
        repository=GovernanceEvaluationRepositoryImpl(cast(Any, session)),
        configuration=configuration,
    ).evaluate(
        GovernanceEvaluationRequest(
            governed_record_reference=uuid4(),
            governed_record_type="Knowledge Evaluation",
            outcome=GovernanceOutcome.EXCEPTION_GRANTED,
            confidence_score=0.95,
            structured_reasons=("Valid exception authorization",),
            narrative_explanation="The governed deviation is authorized.",
            governing_policy_reference=POLICY,
            policy_version=VERSION,
            exception_authorization=_exception(),
            policy_satisfied=False,
            effective_from=NOW,
            produced_timestamp=NOW,
        )
    )
    assert response.governance_attestation is GovernanceOutcome.EXCEPTION_GRANTED
    assert len(session.added) == 1
    assert (
        GovernanceEvaluatedEvent(response.record_identifier, response.outcome, NOW).outcome
        is GovernanceOutcome.EXCEPTION_GRANTED
    )


def test_exception_authorization_rejects_expiry_authority_and_policy_mismatch() -> None:
    with pytest.raises(ValidationError, match="Expiration"):
        ExceptionAuthorizationValidationModel(
            exception_identifier=uuid4(),
            exception_authority=AUTHORITY,
            exception_reason="Invalid period",
            policy_reference=POLICY,
            policy_version=VERSION,
            effective_from=NOW,
            expiration=NOW,
            produced_timestamp=NOW,
        )
    request = GovernanceEvaluationRequest(
        governed_record_reference=uuid4(),
        governed_record_type="Decision Evaluation",
        outcome=GovernanceOutcome.EXCEPTION_GRANTED,
        confidence_score=0.7,
        structured_reasons=("Exception checked",),
        narrative_explanation="The exception cannot be accepted.",
        governing_policy_reference=POLICY,
        policy_version=VERSION,
        exception_authorization=_exception().model_copy(
            update={"exception_authority": "Unauthorized Authority"}
        ),
        policy_satisfied=False,
        effective_from=NOW,
        produced_timestamp=NOW,
    )
    configuration = GovernanceConfigurationLoader(
        Settings(
            governance_policy_reference=POLICY,
            governance_policy_version=VERSION,
            governance_authorized_exception_authorities=[AUTHORITY],
        )
    ).load()
    with pytest.raises(ValueError, match="not authorized"):
        GovernanceApplicationService(
            repository=GovernanceEvaluationRepositoryImpl(cast(Any, _FakeSession())),
            configuration=configuration,
        ).evaluate(request)


def test_governance_architecture_preserves_capability_boundaries() -> None:
    package = Path(__file__).parents[1] / "domain" / "governance_engine"
    source = "\n".join(path.read_text() for path in package.glob("*.py"))
    forbidden = ("identity_resolution", "semantic_resolution", "assertion_engine.service")
    assert not any(value in source for value in forbidden)
    assert not (Path(__file__).parents[1] / "api" / "governance").exists()
    assert "GovernanceAttestationORM" not in source
    assert "EnterpriseTrust" not in source


def test_governance_migration_and_immutability(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        trigger_count = connection.execute(
            text(
                "SELECT count(DISTINCT trigger_name) FROM information_schema.triggers "
                "WHERE trigger_name = 'governance_evaluation_records_immutable'"
            )
        ).scalar_one()
    assert revision == "0007_governance_eval"
    assert trigger_count == 1
