"""Fake-repository application-service tests for
`OqiCrossSourceEvaluationService` (CDD-040 §14-§50; Artifact Authorization
§8 epistemic matrix)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.application.oqi_cross_source_evaluation_service import (
    OqiCorrespondenceNotActiveError,
    OqiCrossSourceEvaluationService,
    OqiRuleNotActiveError,
)
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi.quality_rule import (
    QualityDimension,
    QualityFindingType,
    QualityRule,
    QualityRuleStatus,
)
from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.domain.oqi_cross_source.evaluation import (
    ComparisonObservation,
    ComparisonObservationType,
    QualityComparisonEvaluation,
)
from app.domain.oqi_cross_source.finding import QualityComparisonFinding

NOW = datetime.now(UTC)


def _missing(role: str) -> ComparisonObservation:
    return ComparisonObservation(
        observation_type=ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING,
        participant_role=role,
    )


def _conflict(role: str) -> ComparisonObservation:
    return ComparisonObservation(
        observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
        participant_role=role,
    )


class _FakeRepository:
    def __init__(self) -> None:
        self.call_log: list[tuple[object, ...]] = []
        self.findings: dict[UUID, QualityComparisonFinding] = {}
        self.evaluations: dict[UUID, QualityComparisonEvaluation] = {}
        self.known_lineage: dict[tuple[UUID, str], bool] = {}
        self.latest_value: dict[tuple[UUID, str], tuple[UUID, str] | None] = {}

    def acquire_evaluation_authority(self, identity: str) -> None:
        self.call_log.append(("acquire_authority", identity))

    def get_finding(self, finding_id: UUID) -> QualityComparisonFinding | None:
        self.call_log.append(("get_finding", finding_id))
        return self.findings.get(finding_id)

    def insert_evaluation_idempotent(self, evaluation: QualityComparisonEvaluation) -> bool:
        self.call_log.append(("insert_evaluation", evaluation.evaluation_id))
        if evaluation.evaluation_id in self.evaluations:
            return False
        self.evaluations[evaluation.evaluation_id] = evaluation
        return True

    def upsert_finding(self, finding: QualityComparisonFinding) -> None:
        self.call_log.append(("upsert_finding", finding.finding_id))
        self.findings[finding.finding_id] = finding

    def select_known_lineage(
        self, *, source_object_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> bool:
        self.call_log.append(("select_known_lineage", source_object_id, source_record_reference))
        return self.known_lineage.get((source_object_id, source_record_reference), False)

    def select_latest_target_field_value(
        self, *, source_field_id: UUID, source_record_reference: str, evaluation_horizon: datetime
    ) -> tuple[UUID, str] | None:
        self.call_log.append(("select_latest_value", source_field_id, source_record_reference))
        return self.latest_value.get((source_field_id, source_record_reference))


def _participant(
    *,
    role: str,
    source_field_id: UUID,
    eligible: bool = True,
    expected: bool = True,
    authoritative: bool = False,
) -> dict[str, object]:
    return {
        "role": role,
        "source_field_id": str(source_field_id),
        "eligible": eligible,
        "expected": expected,
        "authoritative": authoritative,
    }


def _rule(
    *,
    condition_id: str = "cond-mpn",
    version: int = 1,
    participants: list[dict[str, object]],
    status: QualityRuleStatus = QualityRuleStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> QualityRule:
    return QualityRule.new(
        quality_condition_id=condition_id,
        version=version,
        dimension=QualityDimension.CONSISTENCY,
        finding_type=QualityFindingType.CROSS_SOURCE_VALUE_CONFLICT,
        validity_primitive=None,
        information_element_requirement_id="ier-mpn",
        rule_parameters={"participants": participants},
        status=status,
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


def _correspondence(
    *,
    tenant_id: str = "tenant-a",
    subject_id: UUID,
    members: tuple[ComparisonSubjectCorrespondenceMember, ...],
    status: ComparisonSubjectCorrespondenceStatus = ComparisonSubjectCorrespondenceStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> ComparisonSubjectCorrespondence:
    return ComparisonSubjectCorrespondence.new(
        comparison_subject_id=subject_id,
        tenant_id=tenant_id,
        version=1,
        status=status,
        members=members,
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


def _member(
    *, role: str, source_object_id: UUID, reference: str
) -> ComparisonSubjectCorrespondenceMember:
    return ComparisonSubjectCorrespondenceMember(
        participant_role=role, source_object_id=source_object_id, source_record_reference=reference
    )


# --- HISTORICAL: never touches authority or Finding ---


def test_historical_never_acquires_authority() -> None:
    repo = _FakeRepository()
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    sap_field, plm_field = uuid4(), uuid4()
    sap_object, plm_object = uuid4(), uuid4()
    subject_id = uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field),
            _participant(role="PLM", source_field_id=plm_field),
        ]
    )
    correspondence = _correspondence(
        subject_id=subject_id,
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
        ),
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service.evaluate_historical(rule=rule, correspondence=correspondence, evaluation_horizon=NOW)

    assert all(call[0] != "acquire_authority" for call in repo.call_log)
    assert repo.findings == {}


# --- CURRENT_STATE: eligibility, ordering ---


def test_current_state_rejects_retired_rule() -> None:
    repo = _FakeRepository()
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    subject_id = uuid4()
    retired_rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=uuid4()),
            _participant(role="PLM", source_field_id=uuid4()),
        ],
        status=QualityRuleStatus.RETIRED,
        retired_on=NOW,
    )
    correspondence = _correspondence(
        subject_id=subject_id,
        members=(
            _member(role="SAP", source_object_id=uuid4(), reference="R1"),
            _member(role="PLM", source_object_id=uuid4(), reference="R2"),
        ),
    )
    with pytest.raises(OqiRuleNotActiveError):
        service.evaluate_current_state(rule=retired_rule, correspondence=correspondence)
    assert repo.call_log == []


def test_current_state_rejects_retired_correspondence() -> None:
    repo = _FakeRepository()
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=uuid4()),
            _participant(role="PLM", source_field_id=uuid4()),
        ]
    )
    retired_correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=uuid4(), reference="R1"),
            _member(role="PLM", source_object_id=uuid4(), reference="R2"),
        ),
        status=ComparisonSubjectCorrespondenceStatus.RETIRED,
        retired_on=NOW,
    )
    with pytest.raises(OqiCorrespondenceNotActiveError):
        service.evaluate_current_state(rule=rule, correspondence=retired_correspondence)
    assert repo.call_log == []


def test_current_state_acquires_authority_before_evidence_selection() -> None:
    repo = _FakeRepository()
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    sap_field, plm_field = uuid4(), uuid4()
    sap_object, plm_object = uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field),
            _participant(role="PLM", source_field_id=plm_field),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
        ),
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service.evaluate_current_state(rule=rule, correspondence=correspondence)

    kinds = [str(call[0]) for call in repo.call_log]
    authority_index = kinds.index("acquire_authority")
    evidence_indices = [i for i, kind in enumerate(kinds) if kind.startswith("select_")]
    assert evidence_indices
    assert all(authority_index < i for i in evidence_indices)


# --- epistemic matrix (CDD-040 §29, AA §8) ---


def _two_participant_setup(
    *, sap_expected: bool = True, plm_expected: bool = True, plm_authoritative: bool = False
) -> tuple[QualityRule, ComparisonSubjectCorrespondence, _FakeRepository, UUID, UUID, UUID, UUID]:
    sap_field, plm_field = uuid4(), uuid4()
    sap_object, plm_object = uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field, expected=sap_expected),
            _participant(
                role="PLM",
                source_field_id=plm_field,
                expected=plm_expected,
                authoritative=plm_authoritative,
            ),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
        ),
    )
    repo = _FakeRepository()
    return rule, correspondence, repo, sap_field, plm_field, sap_object, plm_object


def test_two_agreeing_values_satisfied() -> None:
    rule, correspondence, repo, sap_field, plm_field, sap_object, plm_object = (
        _two_participant_setup()
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert repo.findings == {}


def test_two_conflicting_values_violated() -> None:
    rule, correspondence, repo, sap_field, plm_field, sap_object, plm_object = (
        _two_participant_setup()
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "XYZ999")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert set(evaluation.observations) == {_conflict("SAP"), _conflict("PLM")}


def test_authority_does_not_override_conflict_detection() -> None:
    """CDD-040 §23: PLM authoritative but disagreeing with SAP is still
    VIOLATED -- authority never suppresses a detected disagreement."""
    rule, correspondence, repo, sap_field, plm_field, sap_object, plm_object = (
        _two_participant_setup(plm_authoritative=True)
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "XYZ999")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED


def test_case1_known_lineage_expected_zero_target_evidence_is_violated_missing() -> None:
    rule, correspondence, repo, sap_field, _plm_field, sap_object, plm_object = (
        _two_participant_setup()
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    # PLM: known lineage but no qualifying target-field value at all.

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert evaluation.observations == (_missing("PLM"),)


def test_case2_known_lineage_optional_zero_target_evidence_is_excluded_not_violated() -> None:
    """A third, always-agreeing participant proves the optional-and-absent
    participant is excluded rather than blocking or fabricating a finding."""
    sap_field, plm_field, portal_field = uuid4(), uuid4(), uuid4()
    sap_object, plm_object, portal_object = uuid4(), uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field),
            _participant(role="PLM", source_field_id=plm_field),
            _participant(role="Portal", source_field_id=portal_field, expected=False),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
            _member(role="Portal", source_object_id=portal_object, reference="X-77"),
        ),
    )
    repo = _FakeRepository()
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.known_lineage[(portal_object, "X-77")] = True  # known, but no target evidence
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert repo.findings == {}


def test_case3_role_absent_from_correspondence_is_excluded_regardless_of_expected() -> None:
    sap_field, plm_field, portal_field = uuid4(), uuid4(), uuid4()
    sap_object, plm_object = uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field),
            _participant(role="PLM", source_field_id=plm_field),
            # Portal is configured expected=True in the rule, but the
            # correspondence below never names it for this subject.
            _participant(role="Portal", source_field_id=portal_field, expected=True),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
        ),
    )
    repo = _FakeRepository()
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert repo.findings == {}


def test_case4_correspondence_names_lineage_unknown_expected_is_violated_missing() -> None:
    rule, correspondence, repo, sap_field, _plm_field, sap_object, _plm_object = (
        _two_participant_setup()
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    # PLM lineage entirely unknown -- no repo.known_lineage entry.

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert evaluation.observations == (_missing("PLM"),)


def test_case5_correspondence_names_lineage_unknown_optional_is_excluded() -> None:
    sap_field, plm_field, portal_field = uuid4(), uuid4(), uuid4()
    sap_object, plm_object, portal_object = uuid4(), uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field),
            _participant(role="PLM", source_field_id=plm_field),
            _participant(role="Portal", source_field_id=portal_field, expected=False),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
            _member(role="Portal", source_object_id=portal_object, reference="X-77"),
        ),
    )
    repo = _FakeRepository()
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.known_lineage[(plm_object, "P-442")] = True
    # Portal lineage entirely unknown.
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    repo.latest_value[(plm_field, "P-442")] = (uuid4(), "ABC123")

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert repo.findings == {}


def test_single_known_value_is_not_evaluable() -> None:
    """CDD-040 §30: a single observed value cannot prove or disprove
    cross-source consistency."""
    sap_field, plm_field = uuid4(), uuid4()
    sap_object, plm_object = uuid4(), uuid4()
    rule = _rule(
        participants=[
            _participant(role="SAP", source_field_id=sap_field, expected=False),
            _participant(role="PLM", source_field_id=plm_field, expected=False),
        ]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=(
            _member(role="SAP", source_object_id=sap_object, reference="MAT-100"),
            _member(role="PLM", source_object_id=plm_object, reference="P-442"),
        ),
    )
    repo = _FakeRepository()
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    # PLM: unknown lineage, optional -- excluded, leaving only 1 known value.

    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is None
    assert repo.evaluations == {}
    assert repo.findings == {}


# --- idempotent replay ---


def test_current_state_idempotent_replay_does_not_double_mutate() -> None:
    fixed_horizon = NOW
    rule, correspondence, repo, sap_field, _plm_field, sap_object, _plm_object = (
        _two_participant_setup()
    )
    repo.known_lineage[(sap_object, "MAT-100")] = True
    repo.latest_value[(sap_field, "MAT-100")] = (uuid4(), "ABC123")
    # PLM lineage unknown, expected -> VIOLATED / MISSING, deterministically.

    service = OqiCrossSourceEvaluationService(
        evaluation_repository=repo, clock=lambda: fixed_horizon
    )
    first = service.evaluate_current_state(rule=rule, correspondence=correspondence)
    assert first is not None
    finding_after_first = repo.findings[next(iter(repo.findings))]
    assert finding_after_first.state_revision == 1

    second = service.evaluate_current_state(rule=rule, correspondence=correspondence)
    assert second is not None
    assert first.evaluation_id == second.evaluation_id
    assert len(repo.evaluations) == 1
    finding_after_second = repo.findings[next(iter(repo.findings))]
    assert finding_after_second.state_revision == 1


# --- N-Source Finding Representation Amendment §13: mandatory
# simultaneous-condition test matrix (Artifact Authorization Amendment
# §9-14). Closes the OQI2-VN P1: value conflict among known participants
# must never be suppressed merely because another participant is also
# missing, and vice versa. ---


def _n_participant_scenario(
    role_values: dict[str, str | None],
) -> tuple[QualityRule, ComparisonSubjectCorrespondence, _FakeRepository]:
    """Builds an N-participant rule/correspondence/repo where a `None`
    value means "known lineage, zero qualifying target evidence" (CDD-040
    §29 Case 1) -- every role here is `expected=True`, so `None` is always
    deterministically missing."""
    fields = {role: uuid4() for role in role_values}
    objects = {role: uuid4() for role in role_values}
    rule = _rule(
        participants=[_participant(role=role, source_field_id=fields[role]) for role in role_values]
    )
    correspondence = _correspondence(
        subject_id=uuid4(),
        members=tuple(
            _member(role=role, source_object_id=objects[role], reference=f"REF-{role}")
            for role in role_values
        ),
    )
    repo = _FakeRepository()
    for role, value in role_values.items():
        repo.known_lineage[(objects[role], f"REF-{role}")] = True
        if value is not None:
            repo.latest_value[(fields[role], f"REF-{role}")] = (uuid4(), value)
    return rule, correspondence, repo


def test_9_conflict_plus_single_missing() -> None:
    rule, correspondence, repo = _n_participant_scenario(
        {"A": "ABC", "B": "ABC", "C": "XYZ", "D": None}
    )
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert set(evaluation.observations) == {
        _missing("D"),
        _conflict("A"),
        _conflict("B"),
        _conflict("C"),
    }


def test_10_multiple_missing_no_conflict() -> None:
    rule, correspondence, repo = _n_participant_scenario(
        {"A": "ABC", "B": "ABC", "C": "ABC", "D": None, "E": None}
    )
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert set(evaluation.observations) == {_missing("D"), _missing("E")}


def test_11_multiple_missing_plus_conflict() -> None:
    rule, correspondence, repo = _n_participant_scenario(
        {"A": "ABC", "B": "ABC", "C": "XYZ", "D": None, "E": None}
    )
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    assert set(evaluation.observations) == {
        _conflict("A"),
        _conflict("B"),
        _conflict("C"),
        _missing("D"),
        _missing("E"),
    }


def test_12_conflict_resolves_while_missing_persists_sequential() -> None:
    rule, correspondence, repo = _n_participant_scenario(
        {"A": "ABC", "B": "ABC", "C": "XYZ", "D": None}
    )
    service = OqiCrossSourceEvaluationService(
        evaluation_repository=repo, clock=lambda: NOW.replace(microsecond=1)
    )
    t1 = service.evaluate_current_state(rule=rule, correspondence=correspondence)
    assert t1 is not None
    assert set(t1.observations) == {_missing("D"), _conflict("A"), _conflict("B"), _conflict("C")}

    # C now agrees; D remains missing.
    c_field = next(f for f in rule.rule_parameters["participants"] if f["role"] == "C")[
        "source_field_id"
    ]
    repo.latest_value[(UUID(c_field), "REF-C")] = (uuid4(), "ABC")
    service_t2 = OqiCrossSourceEvaluationService(
        evaluation_repository=repo, clock=lambda: NOW.replace(microsecond=2)
    )
    t2 = service_t2.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert t2 is not None
    assert t2.observations == (_missing("D"),)
    assert t2.outcome is EvaluationOutcome.VIOLATED
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 2
    assert finding.occurrence_count == 1


def test_13_missing_resolves_while_conflict_persists_sequential() -> None:
    """AA Amendment §13's illustrative narrative for this scenario states
    "CONFLICT/A, CONFLICT/B only" once C=ABC arrives, but that contradicts
    the amendment's own binding rules: §5 flags *every* known participant
    in a disagreement with no attribution/clustering, and §20's worked
    example flags all four participants in an analogous case (including
    the three that agree with each other). Persisting a majority/clustering
    computation to selectively exclude C would violate §12 (Majority !=
    Truth) and §16 (no agreement clusters). This test asserts the
    architecturally-consistent result -- CONFLICT for all three known
    participants -- and the discrepancy in the illustrative narrative is
    reported to the Product Owner as a documentation note, not implemented
    literally."""
    rule, correspondence, repo = _n_participant_scenario({"A": "ABC", "B": "XYZ", "C": None})
    service = OqiCrossSourceEvaluationService(
        evaluation_repository=repo, clock=lambda: NOW.replace(microsecond=1)
    )
    t1 = service.evaluate_current_state(rule=rule, correspondence=correspondence)
    assert t1 is not None
    assert set(t1.observations) == {_missing("C"), _conflict("A"), _conflict("B")}

    c_field = next(f for f in rule.rule_parameters["participants"] if f["role"] == "C")[
        "source_field_id"
    ]
    repo.latest_value[(UUID(c_field), "REF-C")] = (uuid4(), "ABC")
    service_t2 = OqiCrossSourceEvaluationService(
        evaluation_repository=repo, clock=lambda: NOW.replace(microsecond=2)
    )
    t2 = service_t2.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert t2 is not None
    assert set(t2.observations) == {_conflict("A"), _conflict("B"), _conflict("C")}
    assert t2.outcome is EvaluationOutcome.VIOLATED
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 2


def test_14_full_lifecycle_conflict_missing_then_missing_then_resolved_then_reopened() -> None:
    rule, correspondence, repo = _n_participant_scenario(
        {"A": "ABC", "B": "ABC", "C": "XYZ", "D": None}
    )

    def _field_id(role: str) -> UUID:
        return UUID(
            next(p for p in rule.rule_parameters["participants"] if p["role"] == role)[
                "source_field_id"
            ]
        )

    c_field, d_field = _field_id("C"), _field_id("D")

    def _step(horizon: datetime) -> QualityComparisonEvaluation | None:
        service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: horizon)
        return service.evaluate_current_state(rule=rule, correspondence=correspondence)

    # T1: conflict + missing -> OPEN, rev=1, occurrence=1
    t1 = _step(NOW.replace(microsecond=1))
    assert t1 is not None
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 1
    assert finding.occurrence_count == 1

    # T2: missing only -> OPEN, rev=2 (unchanged occurrence)
    repo.latest_value[(c_field, "REF-C")] = (uuid4(), "ABC")
    t2 = _step(NOW.replace(microsecond=2))
    assert t2 is not None
    assert t2.observations == (_missing("D"),)
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 2
    assert finding.occurrence_count == 1

    # T3: all agree, D now present -> RESOLVED, rev=3
    repo.latest_value[(d_field, "REF-D")] = (uuid4(), "ABC")
    t3 = _step(NOW.replace(microsecond=3))
    assert t3 is not None
    assert t3.observations == ()
    assert t3.outcome is EvaluationOutcome.SATISFIED
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.state_revision == 3

    # T4: D disagrees again -> OPEN (reopened), rev=4, occurrence=2, reopen=1
    repo.latest_value[(d_field, "REF-D")] = (uuid4(), "ZZZ")
    t4 = _step(NOW.replace(microsecond=4))
    assert t4 is not None
    assert set(t4.observations) == {_conflict("A"), _conflict("B"), _conflict("C"), _conflict("D")}
    finding = next(iter(repo.findings.values()))
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 4
    assert finding.occurrence_count == 2
    assert finding.reopen_count == 1


# --- N-Source Finding Representation Artifact Authorization Amendment
# §20: mandatory N=10 regression -- proves repaired Observation generation
# has no binary/two-participant cardinality assumption reintroduced by the
# repair, at a cardinality double the largest case in the §9-14 matrix
# above. ---

_TEN_ROLES = tuple(f"S{i:02d}" for i in range(1, 11))


def test_n10_a_all_agree_is_satisfied_with_zero_observations() -> None:
    rule, correspondence, repo = _n_participant_scenario({role: "ABC123" for role in _TEN_ROLES})
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.SATISFIED
    assert evaluation.observations == ()
    assert repo.findings == {}


def test_n10_b_nine_agree_one_dissents_flags_all_ten_no_winner() -> None:
    """9 of 10 known participants agree; 1 dissents. All 10 -- including
    the 9 that agree with each other -- are conflict participants, because
    conflict-participation records deterministic disagreement, not blame.
    The dissenting participant (S10) is not uniquely marked wrong, and no
    participant is marked "correct" for agreeing with the majority."""
    role_values: dict[str, str | None] = {role: "ABC123" for role in _TEN_ROLES[:9]}
    role_values[_TEN_ROLES[9]] = "XYZ999"
    rule, correspondence, repo = _n_participant_scenario(role_values)
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    conflict_roles = {
        obs.participant_role
        for obs in evaluation.observations
        if obs.observation_type is ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT
    }
    missing_roles = {
        obs.participant_role
        for obs in evaluation.observations
        if obs.observation_type is ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING
    }
    assert conflict_roles == set(_TEN_ROLES)
    assert missing_roles == set()
    assert len(evaluation.observations) == 10
    # The dissenting participant is not uniquely singled out: it is one
    # conflict observation among ten, not a distinct observation type.
    assert set(evaluation.observations) == {_conflict(role) for role in _TEN_ROLES}


def test_n10_c_eight_agree_one_dissents_one_missing() -> None:
    role_values: dict[str, str | None] = {role: "ABC123" for role in _TEN_ROLES[:8]}
    role_values[_TEN_ROLES[8]] = "XYZ999"
    role_values[_TEN_ROLES[9]] = None
    rule, correspondence, repo = _n_participant_scenario(role_values)
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    expected_conflicts = {_conflict(role) for role in _TEN_ROLES[:9]}
    expected_missing = {_missing(_TEN_ROLES[9])}
    assert set(evaluation.observations) == expected_conflicts | expected_missing
    assert len(evaluation.observations) == 10
    assert (
        sum(
            1
            for obs in evaluation.observations
            if obs.observation_type is ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT
        )
        == 9
    )
    assert (
        sum(
            1
            for obs in evaluation.observations
            if obs.observation_type
            is ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING
        )
        == 1
    )


def test_n10_d_seven_agree_one_dissents_two_missing() -> None:
    role_values: dict[str, str | None] = {role: "ABC123" for role in _TEN_ROLES[:7]}
    role_values[_TEN_ROLES[7]] = "XYZ999"
    role_values[_TEN_ROLES[8]] = None
    role_values[_TEN_ROLES[9]] = None
    rule, correspondence, repo = _n_participant_scenario(role_values)
    service = OqiCrossSourceEvaluationService(evaluation_repository=repo, clock=lambda: NOW)
    evaluation = service.evaluate_current_state(rule=rule, correspondence=correspondence)

    assert evaluation is not None
    assert evaluation.outcome is EvaluationOutcome.VIOLATED
    expected_conflicts = {_conflict(role) for role in _TEN_ROLES[:8]}
    # Both missing participants are recorded independently -- not
    # collapsed into a single generic missing observation.
    expected_missing = {_missing(_TEN_ROLES[8]), _missing(_TEN_ROLES[9])}
    assert set(evaluation.observations) == expected_conflicts | expected_missing
    assert len(evaluation.observations) == 10
    assert (
        sum(
            1
            for obs in evaluation.observations
            if obs.observation_type
            is ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING
        )
        == 2
    )
