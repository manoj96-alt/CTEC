"""Pure domain unit tests for `app.domain.oqi_cross_source.evaluation` and
`app.domain.oqi_cross_source.finding` (CDD-040 §25, §31-§33, §40-§43;
Artifact Authorization §8 identity adversarial matrix)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOrigin,
    EvaluationOutcome,
    SourceRecordLineageIdentity,
)
from app.domain.oqi.finding import QualityFindingStatus
from app.domain.oqi_cross_source.evaluation import (
    ComparisonObservation,
    ComparisonObservationType,
    ParticipantEvidenceEntry,
    QualityComparisonEvaluation,
    derive_comparison_evaluation_id,
    derive_comparison_finding_id,
    evaluate_consistency,
    participant_evidence_digest,
)
from app.domain.oqi_cross_source.finding import (
    QualityComparisonFinding,
    apply_correspondence_finding_transition,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime.now(UTC)


def _lineage(*, tenant_id: str = "tenant-a", reference: str = "R1") -> SourceRecordLineageIdentity:
    return SourceRecordLineageIdentity(
        tenant_id=tenant_id, source_object_id=uuid4(), source_record_reference=reference
    )


def _entry(
    *,
    role: str = "SAP",
    lineage: SourceRecordLineageIdentity | None = None,
    source_field_id: UUID | None = None,
    expected: bool = True,
    authoritative: bool = False,
    evidence_ids: tuple[UUID, ...] = (),
) -> ParticipantEvidenceEntry:
    return ParticipantEvidenceEntry(
        role=role,
        lineage=lineage or _lineage(reference=role),
        source_field_id=source_field_id or uuid4(),
        expected=expected,
        authoritative=authoritative,
        evidence_ids=evidence_ids,
    )


# --- evaluate_consistency (exact-match v1) ---


def test_agreeing_values_are_satisfied() -> None:
    assert (
        evaluate_consistency(participant_values={"SAP": "ABC123", "PLM": "ABC123"})
        is EvaluationOutcome.SATISFIED
    )


def test_conflicting_values_are_violated() -> None:
    assert (
        evaluate_consistency(participant_values={"SAP": "ABC123", "PLM": "XYZ999"})
        is EvaluationOutcome.VIOLATED
    )


def test_three_agreeing_values_are_satisfied() -> None:
    assert (
        evaluate_consistency(participant_values={"SAP": "ABC", "PLM": "ABC", "Portal": "ABC"})
        is EvaluationOutcome.SATISFIED
    )


def test_majority_agreement_does_not_override_minority_disagreement() -> None:
    """CDD-040 §24: two sources agreeing must not establish truth over a
    third -- the outcome is VIOLATED, no winner is chosen."""
    assert (
        evaluate_consistency(participant_values={"SAP": "XYZ", "PLM": "ABC", "Portal": "XYZ"})
        is EvaluationOutcome.VIOLATED
    )


def test_exact_match_is_whitespace_trimmed() -> None:
    assert (
        evaluate_consistency(participant_values={"SAP": " ABC ", "PLM": "ABC"})
        is EvaluationOutcome.SATISFIED
    )


def test_exact_match_is_case_sensitive() -> None:
    """CDD-040 §25: case-preserving, no case-folding."""
    assert (
        evaluate_consistency(participant_values={"SAP": "abc", "PLM": "ABC"})
        is EvaluationOutcome.VIOLATED
    )


# --- participant-keyed digest ---


def test_digest_is_deterministic() -> None:
    entries = (_entry(role="SAP"), _entry(role="PLM"))
    assert participant_evidence_digest(entries) == participant_evidence_digest(entries)


def test_digest_is_input_order_independent() -> None:
    sap, plm = _entry(role="SAP"), _entry(role="PLM")
    assert participant_evidence_digest((sap, plm)) == participant_evidence_digest((plm, sap))


def test_digest_is_role_sensitive_not_flat() -> None:
    """The critical fix over a naive flat evidence-set digest: swapping
    which evidence belongs to which participant must change the digest."""
    evidence_a, evidence_b = uuid4(), uuid4()
    normal = (
        _entry(role="SAP", evidence_ids=(evidence_a,)),
        _entry(role="PLM", evidence_ids=(evidence_b,)),
    )
    swapped = (
        _entry(role="SAP", evidence_ids=(evidence_b,)),
        _entry(role="PLM", evidence_ids=(evidence_a,)),
    )
    assert participant_evidence_digest(normal) != participant_evidence_digest(swapped)


def test_digest_is_subject_sensitive() -> None:
    entry_a = _entry(role="SAP", lineage=_lineage(reference="R1"))
    entry_b = _entry(role="SAP", lineage=_lineage(reference="R2"))
    assert participant_evidence_digest((entry_a,)) != participant_evidence_digest((entry_b,))


def test_digest_distinguishes_zero_evidence_participant_from_absent_participant() -> None:
    present_with_sentinel = (_entry(role="SAP", evidence_ids=()),)
    absent_entirely: tuple[ParticipantEvidenceEntry, ...] = ()
    assert participant_evidence_digest(present_with_sentinel) != participant_evidence_digest(
        absent_entirely
    )


# --- Finding identity: adversarial matrix ---


def test_finding_id_deterministic() -> None:
    subject_id = uuid4()
    a = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=subject_id
    )
    b = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=subject_id
    )
    assert a == b


def test_finding_id_differs_by_tenant() -> None:
    subject_id = uuid4()
    a = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=subject_id
    )
    b = derive_comparison_finding_id(
        tenant_id="tenant-b", quality_condition_id="cond-1", comparison_subject_id=subject_id
    )
    assert a != b


def test_finding_id_differs_by_condition() -> None:
    subject_id = uuid4()
    a = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=subject_id
    )
    b = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-2", comparison_subject_id=subject_id
    )
    assert a != b


def test_finding_id_differs_by_subject() -> None:
    a = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=uuid4()
    )
    b = derive_comparison_finding_id(
        tenant_id="tenant-a", quality_condition_id="cond-1", comparison_subject_id=uuid4()
    )
    assert a != b


# --- Evaluation identity: adversarial matrix (CDD-040 §42-§43) ---


def _eval_id(
    *,
    tenant_id: str = "tenant-a",
    quality_condition_id: str = "cond-1",
    rule_version: int = 1,
    comparison_subject_id: UUID | None = None,
    evaluation_mode: EvaluationMode = EvaluationMode.CURRENT_STATE,
    evaluation_horizon: datetime = NOW,
    participant_digest: str = "digest",
    comparison_subject_correspondence_id: UUID | None = None,
) -> UUID:
    return derive_comparison_evaluation_id(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        rule_version=rule_version,
        comparison_subject_id=comparison_subject_id or uuid4(),
        evaluation_mode=evaluation_mode,
        evaluation_horizon=evaluation_horizon,
        participant_digest=participant_digest,
        comparison_subject_correspondence_id=comparison_subject_correspondence_id or uuid4(),
    )


def test_evaluation_id_differs_by_rule_version() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        rule_version=1,
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    b = _eval_id(
        rule_version=2,
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    assert a != b


def test_evaluation_id_differs_by_correspondence_version() -> None:
    """Unlike Finding identity, Evaluation identity DOES include the
    correspondence version (CDD-040 §42)."""
    subject_id = uuid4()
    a = _eval_id(comparison_subject_id=subject_id, comparison_subject_correspondence_id=uuid4())
    b = _eval_id(comparison_subject_id=subject_id, comparison_subject_correspondence_id=uuid4())
    assert a != b


def test_evaluation_id_differs_by_mode() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
    )
    b = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        evaluation_mode=EvaluationMode.HISTORICAL,
    )
    assert a != b


def test_evaluation_id_differs_by_horizon() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        evaluation_horizon=NOW,
    )
    b = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        evaluation_horizon=NOW + timedelta(seconds=1),
    )
    assert a != b


def test_evaluation_id_differs_by_participant_digest() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        participant_digest="digest-a",
    )
    b = _eval_id(
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        participant_digest="digest-b",
    )
    assert a != b


def test_evaluation_id_differs_by_condition() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        quality_condition_id="cond-a",
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    b = _eval_id(
        quality_condition_id="cond-b",
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    assert a != b


def test_evaluation_id_differs_by_tenant() -> None:
    subject_id, correspondence_id = uuid4(), uuid4()
    a = _eval_id(
        tenant_id="tenant-a",
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    b = _eval_id(
        tenant_id="tenant-b",
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    assert a != b


def test_evaluation_id_rejects_naive_horizon() -> None:
    with pytest.raises(ValidationException):
        derive_comparison_evaluation_id(
            tenant_id="tenant-a",
            quality_condition_id="cond-1",
            rule_version=1,
            comparison_subject_id=uuid4(),
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=datetime(2026, 1, 1, tzinfo=None),  # noqa: DTZ001
            participant_digest="digest",
            comparison_subject_correspondence_id=uuid4(),
        )


# --- QualityComparisonEvaluation construction consistency ---


def test_evaluation_rejects_inconsistent_id() -> None:
    with pytest.raises(ValidationException):
        QualityComparisonEvaluation(
            evaluation_id=uuid4(),  # wrong, unrelated id
            tenant_id="tenant-a",
            quality_condition_id="cond-1",
            rule_id=uuid4(),
            rule_version=1,
            comparison_subject_id=uuid4(),
            comparison_subject_correspondence_id=uuid4(),
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
            evaluation_horizon=NOW,
            participants=(_entry(),),
            outcome=EvaluationOutcome.SATISFIED,
            applied_current_state_authority=False,
            state_revision_applied=None,
            evaluated_on=NOW,
        )


# --- ComparisonObservation (N-Source Finding Representation Amendment
# §5-§10): construction, and proof observations do not enter Evaluation
# identity ---


def _valid_evaluation(
    *,
    participants: tuple[ParticipantEvidenceEntry, ...],
    observations: tuple[ComparisonObservation, ...] = (),
    tenant_id: str = "tenant-a",
    quality_condition_id: str = "cond-1",
    comparison_subject_id: UUID | None = None,
    comparison_subject_correspondence_id: UUID | None = None,
    rule_version: int = 1,
) -> QualityComparisonEvaluation:
    subject_id = comparison_subject_id or uuid4()
    correspondence_id = comparison_subject_correspondence_id or uuid4()
    digest = participant_evidence_digest(participants)
    evaluation_id = derive_comparison_evaluation_id(
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        rule_version=rule_version,
        comparison_subject_id=subject_id,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        participant_digest=digest,
        comparison_subject_correspondence_id=correspondence_id,
    )
    return QualityComparisonEvaluation(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id,
        quality_condition_id=quality_condition_id,
        rule_id=uuid4(),
        rule_version=rule_version,
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_origin=EvaluationOrigin.RULE_DETERMINISTIC,
        evaluation_horizon=NOW,
        participants=participants,
        outcome=EvaluationOutcome.VIOLATED if observations else EvaluationOutcome.SATISFIED,
        applied_current_state_authority=False,
        state_revision_applied=None,
        evaluated_on=NOW,
        observations=observations,
    )


def test_comparison_observation_construction() -> None:
    observation = ComparisonObservation(
        observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
        participant_role="SAP",
    )
    assert observation.observation_type is ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT
    assert observation.participant_role == "SAP"


def test_comparison_observation_rejects_blank_role() -> None:
    with pytest.raises(ValidationException):
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="",
        )


def test_evaluation_accepts_multiple_simultaneous_observations() -> None:
    """The critical N-source repair: one Evaluation may establish a
    conflict observation and a missing observation simultaneously --
    neither suppresses the other."""
    sap, plm, portal = _entry(role="SAP"), _entry(role="PLM"), _entry(role="Portal")
    observations = (
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_PARTICIPANT_VALUE_MISSING,
            participant_role="Portal",
        ),
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="SAP",
        ),
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="PLM",
        ),
    )
    evaluation = _valid_evaluation(participants=(sap, plm, portal), observations=observations)
    assert len(evaluation.observations) == 3


def test_evaluation_rejects_duplicate_observation_key() -> None:
    sap = _entry(role="SAP")
    duplicate = (
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="SAP",
        ),
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="SAP",
        ),
    )
    with pytest.raises(ValidationException):
        _valid_evaluation(participants=(sap,), observations=duplicate)


def test_evaluation_rejects_observation_for_role_not_a_participant() -> None:
    sap = _entry(role="SAP")
    orphan = (
        ComparisonObservation(
            observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
            participant_role="NotAParticipant",
        ),
    )
    with pytest.raises(ValidationException):
        _valid_evaluation(participants=(sap,), observations=orphan)


def test_observations_do_not_enter_evaluation_identity() -> None:
    """N-Source Finding Representation Amendment §8: Evaluation identity is
    unchanged -- observations are a deterministic derivative of the same
    inputs, computing more facts about one evaluation does not change what
    was evaluated."""
    sap, plm = _entry(role="SAP"), _entry(role="PLM")
    subject_id, correspondence_id = uuid4(), uuid4()

    without_observations = _valid_evaluation(
        participants=(sap, plm),
        observations=(),
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    with_observations = _valid_evaluation(
        participants=(sap, plm),
        observations=(
            ComparisonObservation(
                observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
                participant_role="SAP",
            ),
            ComparisonObservation(
                observation_type=ComparisonObservationType.CROSS_SOURCE_VALUE_CONFLICT,
                participant_role="PLM",
            ),
        ),
        comparison_subject_id=subject_id,
        comparison_subject_correspondence_id=correspondence_id,
    )
    assert without_observations.evaluation_id == with_observations.evaluation_id


# --- QualityComparisonFinding transition table (mechanically mirrors
# CDD-039 §30's six rows) ---


def _finding_transition(
    *,
    existing: QualityComparisonFinding | None,
    outcome: EvaluationOutcome,
    subject_id: UUID | None = None,
    condition_id: str = "cond-1",
    horizon: datetime = NOW,
) -> QualityComparisonFinding | None:
    return apply_correspondence_finding_transition(
        existing=existing,
        outcome=outcome,
        evaluation_horizon=horizon,
        tenant_id="tenant-a",
        quality_condition_id=condition_id,
        comparison_subject_id=subject_id or uuid4(),
        evaluation_id=uuid4(),
    )


def test_no_finding_satisfied_yields_no_finding() -> None:
    assert _finding_transition(existing=None, outcome=EvaluationOutcome.SATISFIED) is None


def test_no_finding_violated_creates_open_revision_one() -> None:
    finding = _finding_transition(existing=None, outcome=EvaluationOutcome.VIOLATED)
    assert finding is not None
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 1
    assert finding.occurrence_count == 1
    assert finding.reopen_count == 0


def test_open_violated_remains_open_increments_revision() -> None:
    subject_id = uuid4()
    first = _finding_transition(
        existing=None, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert first is not None
    second = _finding_transition(
        existing=first, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert second is not None
    assert second.status is QualityFindingStatus.OPEN
    assert second.state_revision == 2
    assert second.occurrence_count == 1  # not a reopen


def test_open_satisfied_resolves() -> None:
    subject_id = uuid4()
    open_finding = _finding_transition(
        existing=None, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert open_finding is not None
    resolved = _finding_transition(
        existing=open_finding, outcome=EvaluationOutcome.SATISFIED, subject_id=subject_id
    )
    assert resolved is not None
    assert resolved.status is QualityFindingStatus.RESOLVED
    assert resolved.state_revision == 2


def test_resolved_satisfied_remains_resolved() -> None:
    subject_id = uuid4()
    open_finding = _finding_transition(
        existing=None, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert open_finding is not None
    resolved = _finding_transition(
        existing=open_finding, outcome=EvaluationOutcome.SATISFIED, subject_id=subject_id
    )
    assert resolved is not None
    reconfirmed = _finding_transition(
        existing=resolved, outcome=EvaluationOutcome.SATISFIED, subject_id=subject_id
    )
    assert reconfirmed is not None
    assert reconfirmed.status is QualityFindingStatus.RESOLVED
    assert reconfirmed.state_revision == 3


def test_resolved_violated_reopens() -> None:
    subject_id = uuid4()
    open_finding = _finding_transition(
        existing=None, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert open_finding is not None
    resolved = _finding_transition(
        existing=open_finding, outcome=EvaluationOutcome.SATISFIED, subject_id=subject_id
    )
    assert resolved is not None
    reopened = _finding_transition(
        existing=resolved, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert reopened is not None
    assert reopened.status is QualityFindingStatus.OPEN
    assert reopened.state_revision == 3
    assert reopened.occurrence_count == 2
    assert reopened.reopen_count == 1


def test_finding_transition_is_driven_by_outcome_alone() -> None:
    """N-Source Finding Representation Amendment §14: observation
    composition may freely change while the Finding remains OPEN --
    the transition table itself has no `finding_type` concept anymore."""
    subject_id = uuid4()
    first = _finding_transition(
        existing=None, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert first is not None
    second = _finding_transition(
        existing=first, outcome=EvaluationOutcome.VIOLATED, subject_id=subject_id
    )
    assert second is not None
    assert second.status is QualityFindingStatus.OPEN
    assert second.state_revision == 2


def test_latest_evaluation_id_updates_on_every_transition() -> None:
    subject_id = uuid4()
    first_eval_id = uuid4()
    first = apply_correspondence_finding_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        comparison_subject_id=subject_id,
        evaluation_id=first_eval_id,
    )
    assert first is not None
    assert first.latest_evaluation_id == first_eval_id

    second_eval_id = uuid4()
    second = apply_correspondence_finding_transition(
        existing=first,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        comparison_subject_id=subject_id,
        evaluation_id=second_eval_id,
    )
    assert second is not None
    assert second.latest_evaluation_id == second_eval_id
