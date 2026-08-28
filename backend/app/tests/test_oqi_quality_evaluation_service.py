"""Fake-repository application-service tests for
`OqiQualityEvaluationService` (CDD-039 §18, §22-§25, §30, §33; OQI1
Artifact Authorization §4)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.oqi_quality_evaluation_service import (
    OqiQualityEvaluationService,
    OqiRuleNotActiveError,
)
from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOutcome,
    EvaluationSubject,
    QualityEvaluation,
    SourceRecordLineageIdentity,
)
from app.domain.oqi.finding import QualityFinding, QualityFindingStatus
from app.domain.oqi.quality_rule import (
    OqiMalformedRuleError,
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
    ValidityPrimitive,
)

NOW = datetime.now(UTC)


class _FakeEvaluationRepository:
    def __init__(self) -> None:
        self.call_log: list[tuple[object, ...]] = []
        self.findings: dict[UUID, QualityFinding] = {}
        self.evaluations: dict[UUID, QualityEvaluation] = {}
        self.known_lineage: dict[tuple[UUID, str], UUID | None] = {}
        self.target_evidence: dict[tuple[UUID, str], tuple[UUID, ...]] = {}
        self.latest_value: dict[tuple[UUID, str], tuple[UUID, str] | None] = {}

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.call_log.append(("acquire_authority", identity))

    def get_finding(self, finding_id: UUID) -> QualityFinding | None:
        self.call_log.append(("get_finding", finding_id))
        return self.findings.get(finding_id)

    def insert_evaluation_idempotent(self, evaluation: QualityEvaluation) -> bool:
        self.call_log.append(("insert_evaluation", evaluation.evaluation_id))
        if evaluation.evaluation_id in self.evaluations:
            return False
        self.evaluations[evaluation.evaluation_id] = evaluation
        return True

    def upsert_finding(self, finding: QualityFinding) -> None:
        self.call_log.append(("upsert_finding", finding.finding_id))
        self.findings[finding.finding_id] = finding

    def select_known_lineage_evidence_id(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> UUID | None:
        self.call_log.append(("select_known_lineage", source_object_id, source_record_reference))
        return self.known_lineage.get((source_object_id, source_record_reference))

    def select_target_field_evidence_ids(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, ...]:
        self.call_log.append(("select_target_evidence", source_field_id, source_record_reference))
        return self.target_evidence.get((source_field_id, source_record_reference), ())

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        self.call_log.append(("select_latest_value", source_field_id, source_record_reference))
        return self.latest_value.get((source_field_id, source_record_reference))


def _subject(
    *,
    source_object_id: UUID | None = None,
    source_field_id: UUID | None = None,
    source_record_reference: str = "100045",
) -> EvaluationSubject:
    lineage = SourceRecordLineageIdentity(
        tenant_id="tenant-a",
        source_object_id=source_object_id or uuid4(),
        source_record_reference=source_record_reference,
    )
    return EvaluationSubject(lineage=lineage, source_field_id=source_field_id or uuid4())


def _completeness_rule(
    *,
    status: QualityRuleStatus = QualityRuleStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id="cond-completeness",
        version=1,
        dimension=QualityDimension.COMPLETENESS,
        finding_type=QualityFindingType.MISSING_VALUE,
        validity_primitive=None,
        information_element_requirement_id="req-1",
        rule_parameters={},
        status=status,
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


def _enum_rule(*, allowed_values: tuple[str, ...] = ("US", "CA")) -> QualityRule:
    return QualityRule.new(
        quality_condition_id="cond-enum",
        version=1,
        dimension=QualityDimension.VALIDITY,
        finding_type=QualityFindingType.ENUM_VIOLATION,
        validity_primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
        information_element_requirement_id="req-2",
        rule_parameters={"allowed_values": list(allowed_values)},
        status=QualityRuleStatus.ACTIVE,
        created_by="steward",
        created_on=NOW,
    )


def _clock_sequence(*horizons: datetime) -> Callable[[], datetime]:
    values = iter(horizons)

    def _clock() -> datetime:
        return next(values)

    return _clock


# --- HISTORICAL: never touches authority or Finding ---


def test_historical_never_acquires_authority() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = (uuid4(),)

    service.evaluate_historical(rule=_completeness_rule(), subject=subject, evaluation_horizon=NOW)

    assert all(call[0] != "acquire_authority" for call in repo.call_log)


def test_historical_never_creates_finding() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = ()

    evaluation = service.evaluate_historical(
        rule=_completeness_rule(), subject=subject, evaluation_horizon=NOW
    )

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert repo.findings == {}
    assert all(call[0] not in {"upsert_finding", "get_finding"} for call in repo.call_log)


def test_historical_persists_ledger_row() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = (uuid4(),)

    evaluation = service.evaluate_historical(
        rule=_completeness_rule(), subject=subject, evaluation_horizon=NOW
    )

    assert evaluation is not None
    assert evaluation.evaluation_id in repo.evaluations
    assert evaluation.evaluation_mode is EvaluationMode.HISTORICAL
    assert evaluation.applied_current_state_authority is False
    assert evaluation.state_revision_applied is None


def test_historical_unknown_lineage_produces_no_evaluation() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    # No entry in repo.known_lineage -> unknown lineage.

    evaluation = service.evaluate_historical(
        rule=_completeness_rule(), subject=subject, evaluation_horizon=NOW
    )

    assert evaluation is None
    assert repo.evaluations == {}


def test_historical_rejects_naive_horizon() -> None:
    from app.domain.shared.exceptions import ValidationException

    naive_horizon = datetime(2026, 1, 1, tzinfo=None)  # noqa: DTZ001 -- deliberately naive
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    with pytest.raises(ValidationException):
        service.evaluate_historical(
            rule=_completeness_rule(), subject=_subject(), evaluation_horizon=naive_horizon
        )


# --- CURRENT_STATE: eligibility, ordering, transitions ---


def test_current_state_rejects_retired_rule() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    retired = _completeness_rule(status=QualityRuleStatus.RETIRED, retired_on=NOW)
    with pytest.raises(OqiRuleNotActiveError):
        service.evaluate_current_state(rule=retired, subject=_subject())
    assert repo.call_log == []  # no authority acquired, no query issued


def test_current_state_acquires_authority_before_evidence_selection() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = ()

    service.evaluate_current_state(rule=_completeness_rule(), subject=subject)

    kinds = [str(call[0]) for call in repo.call_log]
    authority_index = kinds.index("acquire_authority")
    evidence_indices = [i for i, kind in enumerate(kinds) if kind.startswith("select_")]
    assert evidence_indices, "no evidence-selection call was made"
    assert all(
        authority_index < i for i in evidence_indices
    ), f"evidence selected before authority acquired: {kinds}"


def test_current_state_first_violation_creates_open_finding() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = ()

    evaluation = service.evaluate_current_state(rule=_completeness_rule(), subject=subject)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert evaluation.applied_current_state_authority is True
    assert len(repo.findings) == 1
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 1
    assert evaluation.state_revision_applied == 1


def test_current_state_satisfied_with_no_finding_creates_nothing() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = (uuid4(),)

    evaluation = service.evaluate_current_state(rule=_completeness_rule(), subject=subject)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert evaluation.state_revision_applied is None
    assert repo.findings == {}


def test_current_state_full_transition_sequence() -> None:
    repo = _FakeEvaluationRepository()
    horizons = [NOW + timedelta(hours=i) for i in range(4)]
    service = OqiQualityEvaluationService(
        evaluation_repository=repo, clock=_clock_sequence(*[h for h in horizons for _ in range(2)])
    )
    subject = _subject()
    rule = _completeness_rule()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()

    # t0: no evidence -> VIOLATED -> OPEN, revision 1
    repo.target_evidence[(subject.source_field_id, "100045")] = ()
    e0 = service.evaluate_current_state(rule=rule, subject=subject)
    assert e0 is not None
    finding = repo.findings[next(iter(repo.findings))]
    assert finding.status is QualityFindingStatus.OPEN and finding.state_revision == 1

    # t1: evidence arrives -> SATISFIED -> RESOLVED, revision 2
    repo.target_evidence[(subject.source_field_id, "100045")] = (uuid4(),)
    e1 = service.evaluate_current_state(rule=rule, subject=subject)
    assert e1 is not None
    finding = repo.findings[finding.finding_id]
    assert finding.status is QualityFindingStatus.RESOLVED and finding.state_revision == 2

    # t2: evidence removed again -> VIOLATED -> OPEN (reopen), revision 3
    repo.target_evidence[(subject.source_field_id, "100045")] = ()
    e2 = service.evaluate_current_state(rule=rule, subject=subject)
    assert e2 is not None
    finding = repo.findings[finding.finding_id]
    assert finding.status is QualityFindingStatus.OPEN and finding.state_revision == 3
    assert finding.occurrence_count == 2 and finding.reopen_count == 1

    assert len({e0.evaluation_id, e1.evaluation_id, e2.evaluation_id}) == 3


def test_rule_retirement_does_not_mutate_finding() -> None:
    """A RETIRED rule can never even reach evaluate_current_state (raises
    OqiRuleNotActiveError before any repository call), so an existing
    Finding is provably untouched by retirement."""
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = ()
    service.evaluate_current_state(rule=_completeness_rule(), subject=subject)
    finding_before = repo.findings[next(iter(repo.findings))]

    retired = _completeness_rule(status=QualityRuleStatus.RETIRED, retired_on=NOW)
    with pytest.raises(OqiRuleNotActiveError):
        service.evaluate_current_state(rule=retired, subject=subject)

    finding_after = repo.findings[next(iter(repo.findings))]
    assert finding_before == finding_after


def test_current_state_unknown_lineage_produces_no_finding() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    # No known_lineage entry.

    evaluation = service.evaluate_current_state(rule=_completeness_rule(), subject=subject)

    assert evaluation is None
    assert repo.findings == {}
    assert repo.evaluations == {}


# --- Validity via the service ---


def test_current_state_validity_no_qualifying_value_produces_no_evaluation() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    # No entry in repo.latest_value -> no qualifying value.

    evaluation = service.evaluate_current_state(rule=_enum_rule(), subject=subject)

    assert evaluation is None
    assert repo.findings == {}


def test_current_state_validity_violation_creates_finding() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    evidence_id = uuid4()
    repo.latest_value[(subject.source_field_id, "100045")] = (evidence_id, "MX")

    evaluation = service.evaluate_current_state(rule=_enum_rule(), subject=subject)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert evaluation.evidence_ids == (evidence_id,)
    finding = repo.findings[next(iter(repo.findings))]
    assert finding.finding_type is QualityFindingType.ENUM_VIOLATION


def test_missing_value_never_double_counted_as_validity() -> None:
    """Missingness belongs exclusively to Completeness (CDD-039 §32): a
    Validity rule on a field with zero qualifying evidence must never
    produce a Finding of its own -- proven by asserting no Validity
    Finding exists after evaluating an ENUM rule against a target that has
    no value at all."""
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()

    evaluation = service.evaluate_current_state(rule=_enum_rule(), subject=subject)

    assert evaluation is None
    assert repo.findings == {}


# --- idempotent replay ---


def test_current_state_idempotent_replay_does_not_double_mutate() -> None:
    repo = _FakeEvaluationRepository()
    fixed_horizon = NOW
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: fixed_horizon)
    subject = _subject()
    repo.known_lineage[(subject.lineage.source_object_id, "100045")] = uuid4()
    repo.target_evidence[(subject.source_field_id, "100045")] = ()

    first = service.evaluate_current_state(rule=_completeness_rule(), subject=subject)
    assert first is not None
    finding_after_first = repo.findings[next(iter(repo.findings))]
    assert finding_after_first.state_revision == 1
    assert finding_after_first.occurrence_count == 1

    # Byte-identical replay: same rule, same subject, same clock (so same
    # evaluation_horizon) -> same evaluation_id.
    second = service.evaluate_current_state(rule=_completeness_rule(), subject=subject)
    assert second is not None

    assert first.evaluation_id == second.evaluation_id
    assert len(repo.evaluations) == 1
    finding_after_second = repo.findings[next(iter(repo.findings))]
    assert finding_after_second.state_revision == 1
    assert finding_after_second.occurrence_count == 1
    assert finding_after_second.reopen_count == 0


# --- malformed rule fails closed (CDD-039 §33 point 3) ---


def test_malformed_persisted_rule_fails_closed_at_evaluation() -> None:
    repo = _FakeEvaluationRepository()
    service = OqiQualityEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject = _subject()
    repo.latest_value[(subject.source_field_id, "100045")] = (uuid4(), "US")

    valid_rule = _enum_rule()
    # Simulate out-of-band database corruption: __post_init__ already ran
    # correctly at construction, so this bypasses it directly on a frozen
    # dataclass to model a row that was corrupted after being written.
    object.__setattr__(valid_rule, "rule_parameters", {"unexpected": True})

    with pytest.raises(OqiMalformedRuleError):
        service.evaluate_current_state(rule=valid_rule, subject=subject)

    # No fabricated SATISFIED/VIOLATED outcome, no ledger row, no Finding.
    assert repo.evaluations == {}
    assert repo.findings == {}
