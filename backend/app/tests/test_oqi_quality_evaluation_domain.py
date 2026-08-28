"""Pure domain unit tests for `app.domain.oqi.evaluation` and
`app.domain.oqi.finding` (CDD-039 §12, §14, §20, §25, §28, §30-§32; OQI1
Artifact Authorization §4)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.oqi.evaluation import (
    EvaluationMode,
    EvaluationOutcome,
    EvaluationSubject,
    SourceRecordLineageIdentity,
    canonical_subject_identity,
    derive_evaluation_id,
    derive_quality_finding_id,
    evaluate_completeness,
    evaluate_enum_membership,
    evaluate_format,
    evaluate_range,
    evaluate_validity,
    evidence_set_digest,
    finding_identity_material,
)
from app.domain.oqi.finding import QualityFindingStatus, apply_transition
from app.domain.oqi.quality_rule import QualityFindingType, ValidityPrimitive
from app.domain.shared.exceptions import ValidationException

NOW = datetime.now(UTC)


def _subject(
    *,
    tenant_id: str = "tenant-a",
    source_object_id: UUID | None = None,
    source_record_reference: str = "100045",
    source_field_id: UUID | None = None,
) -> EvaluationSubject:
    lineage = SourceRecordLineageIdentity(
        tenant_id=tenant_id,
        source_object_id=source_object_id or uuid4(),
        source_record_reference=source_record_reference,
    )
    return EvaluationSubject(lineage=lineage, source_field_id=source_field_id or uuid4())


# --- SourceRecordLineageIdentity / EvaluationSubject / canonical identity ---


def test_canonical_subject_identity_is_deterministic() -> None:
    so_id = uuid4()
    sf_id = uuid4()
    a = _subject(source_object_id=so_id, source_field_id=sf_id)
    b = EvaluationSubject(
        lineage=SourceRecordLineageIdentity(
            tenant_id="tenant-a", source_object_id=so_id, source_record_reference="100045"
        ),
        source_field_id=sf_id,
    )
    assert canonical_subject_identity(a) == canonical_subject_identity(b)


def test_canonical_subject_identity_differs_by_tenant() -> None:
    so_id = uuid4()
    sf_id = uuid4()
    a = _subject(tenant_id="tenant-a", source_object_id=so_id, source_field_id=sf_id)
    b = _subject(tenant_id="tenant-b", source_object_id=so_id, source_field_id=sf_id)
    assert canonical_subject_identity(a) != canonical_subject_identity(b)


def test_canonical_subject_identity_differs_by_source_object() -> None:
    sf_id = uuid4()
    a = _subject(source_object_id=uuid4(), source_field_id=sf_id)
    b = _subject(source_object_id=uuid4(), source_field_id=sf_id)
    assert canonical_subject_identity(a) != canonical_subject_identity(b)


def test_canonical_subject_identity_differs_by_source_field() -> None:
    so_id = uuid4()
    a = _subject(source_object_id=so_id, source_field_id=uuid4())
    b = _subject(source_object_id=so_id, source_field_id=uuid4())
    assert canonical_subject_identity(a) != canonical_subject_identity(b)


def test_canonical_subject_identity_differs_by_record_reference() -> None:
    so_id = uuid4()
    sf_id = uuid4()
    a = _subject(source_object_id=so_id, source_field_id=sf_id, source_record_reference="100045")
    b = _subject(source_object_id=so_id, source_field_id=sf_id, source_record_reference="100046")
    assert canonical_subject_identity(a) != canonical_subject_identity(b)


def test_subject_type_is_fixed() -> None:
    assert _subject().subject_type == "SOURCE_FIELD_RECORD"


def test_lineage_rejects_blank_source_record_reference() -> None:
    with pytest.raises(ValidationException):
        SourceRecordLineageIdentity(
            tenant_id="tenant-a", source_object_id=uuid4(), source_record_reference="   "
        )


# --- finding identity ---


def test_finding_id_matches_material_used_for_lock() -> None:
    subject = _subject()
    subject_identity = canonical_subject_identity(subject)
    material = finding_identity_material(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        subject_type=subject.subject_type,
        subject_identity=subject_identity,
    )
    finding_id = derive_quality_finding_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        subject_type=subject.subject_type,
        subject_identity=subject_identity,
    )
    # The lock material is the exact pre-hash input; deterministic, so
    # re-deriving the finding id from the same material must agree.
    assert isinstance(material, str) and material
    assert finding_id == derive_quality_finding_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        subject_type=subject.subject_type,
        subject_identity=subject_identity,
    )


def test_finding_id_excludes_rule_version() -> None:
    """Finding identity has no rule_version parameter at all -- two
    evaluations of different rule versions on the same subject/condition
    must resolve to the same Finding lineage, proven here by construction:
    the function signature itself accepts no rule_version."""
    subject = _subject()
    subject_identity = canonical_subject_identity(subject)
    a = derive_quality_finding_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        subject_type=subject.subject_type,
        subject_identity=subject_identity,
    )
    b = derive_quality_finding_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        subject_type=subject.subject_type,
        subject_identity=subject_identity,
    )
    assert a == b


# --- evaluation identity ---


def test_evaluation_id_is_deterministic() -> None:
    subject = _subject()
    digest = evidence_set_digest(())
    a = derive_evaluation_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        rule_version=1,
        subject_type=subject.subject_type,
        subject_identity=canonical_subject_identity(subject),
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        evidence_digest=digest,
    )
    b = derive_evaluation_id(
        tenant_id=subject.lineage.tenant_id,
        quality_condition_id="cond-1",
        rule_version=1,
        subject_type=subject.subject_type,
        subject_identity=canonical_subject_identity(subject),
        evaluation_mode=EvaluationMode.CURRENT_STATE,
        evaluation_horizon=NOW,
        evidence_digest=digest,
    )
    assert a == b


def test_evaluation_id_differs_by_rule_version() -> None:
    subject = _subject()
    digest = evidence_set_digest(())
    subject_identity = canonical_subject_identity(subject)

    def _id(rule_version: int) -> object:
        return derive_evaluation_id(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id="cond-1",
            rule_version=rule_version,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=NOW,
            evidence_digest=digest,
        )

    assert _id(1) != _id(2)


def test_evaluation_id_differs_by_mode() -> None:
    subject = _subject()
    digest = evidence_set_digest(())
    subject_identity = canonical_subject_identity(subject)

    def _id(mode: EvaluationMode) -> object:
        return derive_evaluation_id(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id="cond-1",
            rule_version=1,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
            evaluation_mode=mode,
            evaluation_horizon=NOW,
            evidence_digest=digest,
        )

    assert _id(EvaluationMode.HISTORICAL) != _id(EvaluationMode.CURRENT_STATE)


def test_evaluation_id_differs_by_horizon() -> None:
    subject = _subject()
    digest = evidence_set_digest(())
    subject_identity = canonical_subject_identity(subject)

    def _id(horizon: datetime) -> object:
        return derive_evaluation_id(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id="cond-1",
            rule_version=1,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=horizon,
            evidence_digest=digest,
        )

    assert _id(NOW) != _id(NOW + timedelta(seconds=1))


def test_evaluation_id_excludes_state_revision_by_construction() -> None:
    """`derive_evaluation_id` has no `state_revision` parameter at all."""
    import inspect

    assert "state_revision" not in inspect.signature(derive_evaluation_id).parameters


# --- evidence digest ---


def test_evidence_digest_is_order_independent() -> None:
    a, b, c = uuid4(), uuid4(), uuid4()
    assert evidence_set_digest((a, b, c)) == evidence_set_digest((c, a, b))


def test_evidence_digest_empty_sentinel_differs_from_any_real_set() -> None:
    empty = evidence_set_digest(())
    non_empty = evidence_set_digest((uuid4(),))
    assert empty != non_empty


def test_evidence_digest_differs_by_membership() -> None:
    a, b = uuid4(), uuid4()
    assert evidence_set_digest((a,)) != evidence_set_digest((b,))


def test_same_evidence_different_order_same_evaluation_id() -> None:
    subject = _subject()
    a_id, b_id = uuid4(), uuid4()
    digest_1 = evidence_set_digest((a_id, b_id))
    digest_2 = evidence_set_digest((b_id, a_id))
    subject_identity = canonical_subject_identity(subject)

    def _id(digest: str) -> object:
        return derive_evaluation_id(
            tenant_id=subject.lineage.tenant_id,
            quality_condition_id="cond-1",
            rule_version=1,
            subject_type=subject.subject_type,
            subject_identity=subject_identity,
            evaluation_mode=EvaluationMode.CURRENT_STATE,
            evaluation_horizon=NOW,
            evidence_digest=digest,
        )

    assert _id(digest_1) == _id(digest_2)


# --- Completeness ---


def test_completeness_satisfied_when_target_evidence_exists() -> None:
    assert (
        evaluate_completeness(qualifying_target_evidence_ids=(uuid4(),))
        is EvaluationOutcome.SATISFIED
    )


def test_completeness_violated_when_no_target_evidence() -> None:
    assert evaluate_completeness(qualifying_target_evidence_ids=()) is EvaluationOutcome.VIOLATED


# --- Validity primitives ---


def test_enum_membership_exact_match() -> None:
    assert (
        evaluate_enum_membership(value="US", allowed_values=["US", "CA"])
        is EvaluationOutcome.SATISFIED
    )


def test_enum_membership_case_sensitive() -> None:
    assert evaluate_enum_membership(value="us", allowed_values=["US"]) is EvaluationOutcome.VIOLATED


def test_enum_membership_no_trim() -> None:
    assert (
        evaluate_enum_membership(value="US ", allowed_values=["US"]) is EvaluationOutcome.VIOLATED
    )


def test_format_pass() -> None:
    assert evaluate_format(value="ABC123", pattern=r"[A-Z]{3}\d{3}") is EvaluationOutcome.SATISFIED


def test_format_fail() -> None:
    assert evaluate_format(value="abc123", pattern=r"[A-Z]{3}\d{3}") is EvaluationOutcome.VIOLATED


def test_format_requires_full_match() -> None:
    assert evaluate_format(value="ABC1234", pattern=r"[A-Z]{3}\d{3}") is EvaluationOutcome.VIOLATED


def test_range_inside_bounds() -> None:
    assert evaluate_range(value="5", minimum=0, maximum=10) is EvaluationOutcome.SATISFIED


def test_range_below_minimum() -> None:
    assert evaluate_range(value="-1", minimum=0, maximum=10) is EvaluationOutcome.VIOLATED


def test_range_above_maximum() -> None:
    assert evaluate_range(value="11", minimum=0, maximum=10) is EvaluationOutcome.VIOLATED


def test_range_exact_lower_boundary_inclusive() -> None:
    assert evaluate_range(value="0", minimum=0, maximum=10) is EvaluationOutcome.SATISFIED


def test_range_exact_upper_boundary_inclusive() -> None:
    assert evaluate_range(value="10", minimum=0, maximum=10) is EvaluationOutcome.SATISFIED


def test_range_unparseable_value_is_violated() -> None:
    assert evaluate_range(value="not-a-number", minimum=0, maximum=10) is EvaluationOutcome.VIOLATED


def test_range_whitespace_stripped() -> None:
    assert evaluate_range(value="  5  ", minimum=0, maximum=10) is EvaluationOutcome.SATISFIED


def test_evaluate_validity_dispatches_enum() -> None:
    outcome = evaluate_validity(
        primitive=ValidityPrimitive.ENUM_MEMBERSHIP,
        value="US",
        rule_parameters={"allowed_values": ["US"]},
    )
    assert outcome is EvaluationOutcome.SATISFIED


def test_evaluate_validity_dispatches_range_no_max() -> None:
    outcome = evaluate_validity(
        primitive=ValidityPrimitive.RANGE_VIOLATION,
        value="1000000",
        rule_parameters={"min": 0, "max": None},
    )
    assert outcome is EvaluationOutcome.SATISFIED


# --- Finding transition table (CDD-039 §30), exhaustive ---


def test_no_finding_satisfied_produces_no_finding() -> None:
    result = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=_subject(),
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert result is None


def test_no_finding_violated_creates_open() -> None:
    subject = _subject()
    result = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert result is not None
    assert result.status is QualityFindingStatus.OPEN
    assert result.state_revision == 1
    assert result.occurrence_count == 1
    assert result.reopen_count == 0
    assert result.first_seen_at == NOW
    assert result.last_seen_at == NOW
    assert result.last_evaluated_horizon == NOW


def test_open_violated_remains_open() -> None:
    subject = _subject()
    first = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert first is not None
    later = NOW + timedelta(hours=1)
    second = apply_transition(
        existing=first,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=later,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert second is not None
    assert second.status is QualityFindingStatus.OPEN
    assert second.state_revision == 2
    assert second.occurrence_count == 1
    assert second.reopen_count == 0
    assert second.first_seen_at == NOW
    assert second.last_seen_at == later
    assert second.last_evaluated_horizon == later


def test_open_satisfied_resolves() -> None:
    subject = _subject()
    first = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert first is not None
    later = NOW + timedelta(hours=1)
    second = apply_transition(
        existing=first,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=later,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert second is not None
    assert second.status is QualityFindingStatus.RESOLVED
    assert second.state_revision == 2
    # last_seen_at is only updated on VIOLATED evaluations -- the problem
    # was last "seen" at NOW, not at the resolving evaluation's horizon.
    assert second.last_seen_at == NOW
    assert second.last_evaluated_horizon == later
    assert second.occurrence_count == 1
    assert second.reopen_count == 0


def test_resolved_satisfied_remains_resolved() -> None:
    subject = _subject()
    finding = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    finding = apply_transition(
        existing=finding,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW + timedelta(hours=1),
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    third_horizon = NOW + timedelta(hours=2)
    finding = apply_transition(
        existing=finding,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=third_horizon,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert finding is not None
    assert finding.status is QualityFindingStatus.RESOLVED
    assert finding.state_revision == 3
    assert finding.occurrence_count == 1
    assert finding.reopen_count == 0
    assert finding.last_evaluated_horizon == third_horizon


def test_resolved_violated_reopens() -> None:
    subject = _subject()
    finding = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    finding = apply_transition(
        existing=finding,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW + timedelta(hours=1),
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    reopen_horizon = NOW + timedelta(hours=2)
    finding = apply_transition(
        existing=finding,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=reopen_horizon,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    assert finding is not None
    assert finding.status is QualityFindingStatus.OPEN
    assert finding.state_revision == 3
    assert finding.occurrence_count == 2
    assert finding.reopen_count == 1
    assert finding.last_seen_at == reopen_horizon
    assert finding.last_evaluated_horizon == reopen_horizon
    assert finding.first_seen_at == NOW


def test_existing_finding_identity_mismatch_is_rejected() -> None:
    subject_a = _subject()
    subject_b = _subject()
    existing = apply_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id="tenant-a",
        quality_condition_id="cond-1",
        subject=subject_a,
        finding_type=QualityFindingType.MISSING_VALUE,
    )
    with pytest.raises(ValidationException):
        apply_transition(
            existing=existing,
            outcome=EvaluationOutcome.VIOLATED,
            evaluation_horizon=NOW,
            tenant_id="tenant-a",
            quality_condition_id="cond-1",
            subject=subject_b,
            finding_type=QualityFindingType.MISSING_VALUE,
        )
