from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text

from app.core.config import Settings
from app.domain.knowledge_engine import (
    AcceptanceEvidence,
    AcceptanceEvidenceValidator,
    KnowledgeConfidence,
    KnowledgeEngine,
    KnowledgeEvaluationRecord,
    KnowledgeOutcome,
    KnowledgePolicy,
)
from app.domain.shared.exceptions import ValidationException
from app.infrastructure.persistence.knowledge_evaluation_store import (
    KnowledgeEvaluationStore,
)
from app.infrastructure.persistence.models.knowledge_evaluation import (
    KnowledgeEvaluationRecordModel,
)
from app.infrastructure.persistence.repositories import REPOSITORY_TYPES

NOW = datetime(2026, 1, 1, tzinfo=UTC)
AUTHORITY = "Supply Chain Governance"
POLICY_VERSION = "knowledge-policy-v1"


def _policy() -> KnowledgePolicy:
    return KnowledgePolicy(POLICY_VERSION, frozenset({AUTHORITY}))


def _evidence(
    assertion_record_id: UUID | None = None,
    *,
    acceptance_authority: str = AUTHORITY,
    policy_version: str = POLICY_VERSION,
) -> AcceptanceEvidence:
    return AcceptanceEvidence(
        evidence_id=uuid4(),
        assertion_record_id=assertion_record_id or uuid4(),
        acceptance_authority=acceptance_authority,
        policy_reference="Supply Chain Knowledge Policy",
        policy_version=policy_version,
        acceptance_timestamp=NOW,
    )


def _evaluate(
    outcome: KnowledgeOutcome,
    *,
    assertion_record_id: UUID | None = None,
    acceptance_evidence: AcceptanceEvidence | None = None,
    rejection_explanation: str | None = None,
) -> KnowledgeEvaluationRecord:
    assertion_id = assertion_record_id or uuid4()
    evidence = acceptance_evidence
    if outcome is KnowledgeOutcome.INSTITUTIONALIZED and evidence is None:
        evidence = _evidence(assertion_id)
    rejection = rejection_explanation
    if outcome is KnowledgeOutcome.REJECTED and rejection_explanation is None:
        rejection = "The Assertion did not satisfy policy"
    return KnowledgeEngine(_policy()).evaluate(
        assertion_record_id=assertion_id,
        outcome=outcome,
        confidence_score=0.95,
        structured_reasons=("Policy evaluation completed",),
        narrative_explanation="The Assertion was evaluated under the configured policy.",
        effective_from=NOW,
        produced_at=NOW,
        acceptance_evidence=evidence,
        rejection_explanation=rejection,
    )


def test_institutionalized_requires_valid_acceptance_evidence() -> None:
    record = _evaluate(KnowledgeOutcome.INSTITUTIONALIZED)
    assert record.establishes_institutional_knowledge
    assert record.acceptance_evidence_id is not None


def test_candidate_does_not_create_institutional_knowledge() -> None:
    record = _evaluate(KnowledgeOutcome.CANDIDATE)
    assert not record.establishes_institutional_knowledge
    assert record.acceptance_evidence_id is None


def test_rejected_requires_rejection_explanation() -> None:
    with pytest.raises(ValidationException, match="Rejection Explanation"):
        KnowledgeEngine(_policy()).evaluate(
            assertion_record_id=uuid4(),
            outcome=KnowledgeOutcome.REJECTED,
            confidence_score=0.2,
            structured_reasons=("Policy evaluation completed",),
            narrative_explanation="Rejected evaluation.",
            effective_from=NOW,
            produced_at=NOW,
        )


def test_institutionalized_rejects_missing_evidence() -> None:
    with pytest.raises(ValidationException, match="Acceptance Evidence"):
        KnowledgeEngine(_policy()).evaluate(
            assertion_record_id=uuid4(),
            outcome=KnowledgeOutcome.INSTITUTIONALIZED,
            confidence_score=0.95,
            structured_reasons=("Policy evaluation completed",),
            narrative_explanation="Institutionalized evaluation.",
            effective_from=NOW,
            produced_at=NOW,
        )


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.95, KnowledgeConfidence.HIGH),
        (0.7, KnowledgeConfidence.MEDIUM),
        (0.2, KnowledgeConfidence.LOW),
    ],
)
def test_confidence_classification(score: float, expected: KnowledgeConfidence) -> None:
    assert KnowledgeEngine(_policy()).classify_confidence(score) is expected


def test_acceptance_evidence_must_reference_same_assertion() -> None:
    evidence = _evidence()
    with pytest.raises(ValidationException, match="same Assertion"):
        AcceptanceEvidenceValidator(frozenset({AUTHORITY})).validate(
            evidence, assertion_record_id=uuid4(), policy_version=POLICY_VERSION
        )


def test_acceptance_evidence_requires_authorized_authority() -> None:
    assertion_id = uuid4()
    with pytest.raises(ValidationException, match="not authorized"):
        AcceptanceEvidenceValidator(frozenset()).validate(
            _evidence(assertion_id),
            assertion_record_id=assertion_id,
            policy_version=POLICY_VERSION,
        )


def test_acceptance_evidence_requires_matching_policy_version() -> None:
    assertion_id = uuid4()
    with pytest.raises(ValidationException, match="policy version"):
        AcceptanceEvidenceValidator(frozenset({AUTHORITY})).validate(
            _evidence(assertion_id),
            assertion_record_id=assertion_id,
            policy_version="different-policy",
        )


def test_human_override_creates_new_immutable_record() -> None:
    previous = _evaluate(KnowledgeOutcome.CANDIDATE)
    evidence = _evidence(previous.assertion_record_id)
    replacement = KnowledgeEngine(_policy()).override(
        previous,
        outcome=KnowledgeOutcome.INSTITUTIONALIZED,
        confidence_score=0.95,
        structured_reasons=("Governance evidence received",),
        narrative_explanation="Acceptance has now been demonstrated.",
        effective_from=NOW + timedelta(days=1),
        produced_at=NOW + timedelta(days=1),
        acceptance_evidence=evidence,
    )
    assert replacement.record_id != previous.record_id
    assert replacement.assertion_record_id == previous.assertion_record_id
    assert replacement.structured_reasons[0] == "Authorized human override"
    assert replacement.establishes_institutional_knowledge


def test_policy_configuration_validation() -> None:
    with pytest.raises(ValueError, match="High confidence"):
        KnowledgePolicy("policy", frozenset(), 0.5, 0.8)


def test_knowledge_configuration_loading_and_validation() -> None:
    settings = Settings(
        knowledge_policy_version="configured-v2",
        knowledge_authorized_acceptance_authorities=[AUTHORITY],
        knowledge_high_confidence_threshold=0.85,
        knowledge_medium_confidence_threshold=0.6,
    )
    policy = KnowledgePolicy(
        settings.knowledge_policy_version,
        frozenset(settings.knowledge_authorized_acceptance_authorities),
        settings.knowledge_high_confidence_threshold,
        settings.knowledge_medium_confidence_threshold,
    )
    assert policy.version == "configured-v2"
    assert AUTHORITY in policy.authorized_acceptance_authorities


class _ScalarResult:
    def __init__(self, values: list[KnowledgeEvaluationRecordModel]) -> None:
        self.values = values

    def __iter__(self) -> Iterator[KnowledgeEvaluationRecordModel]:
        return iter(self.values)

    def first(self) -> KnowledgeEvaluationRecordModel | None:
        return self.values[0] if self.values else None


class _FakeSession:
    def __init__(
        self,
        *,
        assertion_exists: bool = True,
        values: list[KnowledgeEvaluationRecordModel] | None = None,
    ) -> None:
        self.assertion_exists = assertion_exists
        self.values = values or []
        self.added: list[object] = []

    def get(self, model_type: Any, identifier: Any) -> object | None:
        del model_type, identifier
        return object() if self.assertion_exists else None

    def add(self, value: object) -> None:
        self.added.append(value)

    def scalars(self, statement: Any) -> _ScalarResult:
        del statement
        return _ScalarResult(self.values)


def _persistence_model(record: KnowledgeEvaluationRecord) -> KnowledgeEvaluationRecordModel:
    return KnowledgeEvaluationRecordModel(
        record_id=record.record_id,
        assertion_record_id=record.assertion_record_id,
        outcome=record.outcome.value,
        structured_reasons="\n".join(record.structured_reasons),
        narrative_explanation=record.narrative_explanation,
        acceptance_evidence_id=record.acceptance_evidence_id,
        rejection_explanation=record.rejection_explanation,
        knowledge_confidence=record.knowledge_confidence.value,
        policy_version=record.policy_version,
        effective_from=record.effective_from,
        produced_at=record.produced_at,
    )


def test_store_is_append_only_and_requires_existing_assertion() -> None:
    record = _evaluate(KnowledgeOutcome.CANDIDATE)
    session = _FakeSession()
    KnowledgeEvaluationStore(cast(Any, session)).append(record)
    assert len(session.added) == 1
    assert isinstance(session.added[0], KnowledgeEvaluationRecordModel)

    with pytest.raises(ValidationException, match="existing Assertion"):
        KnowledgeEvaluationStore(cast(Any, _FakeSession(assertion_exists=False))).append(record)


def test_store_returns_ordered_history_and_current_projection() -> None:
    assertion_id = uuid4()
    first = _evaluate(KnowledgeOutcome.CANDIDATE, assertion_record_id=assertion_id)
    second = KnowledgeEngine(_policy()).override(
        first,
        outcome=KnowledgeOutcome.REJECTED,
        confidence_score=0.2,
        structured_reasons=("Policy rejection",),
        narrative_explanation="The Assertion was rejected.",
        rejection_explanation="Acceptance requirements were not met.",
        effective_from=NOW + timedelta(days=1),
        produced_at=NOW + timedelta(days=1),
    )
    session = _FakeSession(values=[_persistence_model(second), _persistence_model(first)])
    store = KnowledgeEvaluationStore(cast(Any, session))
    assert [x.record_id for x in store.history(assertion_id)] == [
        second.record_id,
        first.record_id,
    ]
    assert store.current(assertion_id, as_of=NOW + timedelta(days=2)) == second
    with pytest.raises(ValueError, match="timezone-aware"):
        store.current(assertion_id, as_of=datetime(2026, 1, 1))  # noqa: DTZ001


def test_rfc_011_query_orders_by_effective_produced_and_identifier() -> None:
    statement = KnowledgeEvaluationStore._ordered_statement(uuid4())
    sql = str(statement.compile(compile_kwargs={"literal_binds": True}))
    order_clause = sql.split("ORDER BY", maxsplit=1)[1]
    assert order_clause.index("effective_from DESC") < order_clause.index("produced_at DESC")
    assert order_clause.index("produced_at DESC") < order_clause.index("record_id DESC")


def test_knowledge_evaluation_uses_its_dedicated_append_only_store() -> None:
    assert KnowledgeEvaluationRecordModel not in REPOSITORY_TYPES


def test_knowledge_migration_and_immutability(migrated_engine: Engine) -> None:
    with migrated_engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        trigger_count = connection.execute(
            text(
                "SELECT count(DISTINCT trigger_name) FROM information_schema.triggers "
                "WHERE trigger_name = 'knowledge_evaluation_records_immutable'"
            )
        ).scalar_one()
    assert revision == "0013_decision_evaluation_group"
    assert trigger_count == 1
