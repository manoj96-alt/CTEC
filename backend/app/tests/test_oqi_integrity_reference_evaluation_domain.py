"""Pure domain unit tests for `app.domain.oqi_integrity.reference`
(CDD-050 §10.2, §14-§16, PO-H4-04; Artifact Authorization row 18): the
Reference Integrity evaluation/Finding dataclasses, deterministic identity
derivation, and the Finding-lifecycle transition function -- all in
isolation, no PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.identity_resolution.model import ResolutionOutcome
from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi_integrity.reference import (
    ReferenceIntegrityEvaluation,
    ReferenceIntegrityFinding,
    apply_reference_finding_transition,
    derive_reference_evaluation_id,
    derive_reference_finding_id,
    reference_finding_identity_material,
)
from app.domain.oqi_integrity.structural import (
    IntegrityFindingStatus,
    IntegrityFindingType,
    derive_structural_finding_id,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT = "tenant-a"


# --- Deterministic identity ---


def test_reference_finding_identity_material_excludes_resolution_record_and_horizon() -> None:
    requirement_id, source_object_id = uuid4(), uuid4()
    a = reference_finding_identity_material(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    b = reference_finding_identity_material(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    assert a == b


def test_derive_reference_finding_id_is_deterministic_and_sensitive_to_each_input() -> None:
    requirement_id, source_object_id = uuid4(), uuid4()
    base = derive_reference_finding_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    replay = derive_reference_finding_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    assert base == replay
    assert base != derive_reference_finding_id(
        tenant_id="tenant-b",
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    assert base != derive_reference_finding_id(
        tenant_id=TENANT, relationship_requirement_id=uuid4(), source_object_id=source_object_id
    )
    assert base != derive_reference_finding_id(
        tenant_id=TENANT, relationship_requirement_id=requirement_id, source_object_id=uuid4()
    )


def test_reference_and_structural_finding_ids_never_collide_for_the_same_uuid_inputs() -> None:
    # CDD-050 §15: distinct identity-algorithm-version strings prevent a
    # Structural and a Reference Finding from ever sharing an id even if
    # every UUID input happened to be identical.
    shared_requirement_id = uuid4()
    shared_subject_id = uuid4()
    structural_id = derive_structural_finding_id(
        tenant_id=TENANT,
        relationship_requirement_id=shared_requirement_id,
        enterprise_entity_id=shared_subject_id,
    )
    reference_id = derive_reference_finding_id(
        tenant_id=TENANT,
        relationship_requirement_id=shared_requirement_id,
        source_object_id=shared_subject_id,
    )
    assert structural_id != reference_id


def test_derive_reference_evaluation_id_changes_with_resolution_record_and_horizon() -> None:
    requirement_id, source_object_id = uuid4(), uuid4()
    record_a, record_b = uuid4(), uuid4()
    base = derive_reference_evaluation_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_a,
        evaluation_horizon=NOW,
    )
    assert base == derive_reference_evaluation_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_a,
        evaluation_horizon=NOW,
    )
    assert base != derive_reference_evaluation_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_b,
        evaluation_horizon=NOW,
    )
    assert base != derive_reference_evaluation_id(
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_a,
        evaluation_horizon=NOW + timedelta(hours=1),
    )


def test_derive_reference_evaluation_id_rejects_naive_horizon() -> None:
    with pytest.raises(ValidationException):
        derive_reference_evaluation_id(
            tenant_id=TENANT,
            relationship_requirement_id=uuid4(),
            source_object_id=uuid4(),
            resolution_record_id=uuid4(),
            evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive
        )


# --- ReferenceIntegrityEvaluation: RESOLVED<->SATISFIED / UNRESOLVED<->VIOLATED lockstep ---


def _evaluation(
    *,
    resolution_outcome: ResolutionOutcome = ResolutionOutcome.RESOLVED,
    outcome: EvaluationOutcome = EvaluationOutcome.SATISFIED,
) -> ReferenceIntegrityEvaluation:
    tenant_id, requirement_id, source_object_id, record_id = TENANT, uuid4(), uuid4(), uuid4()
    evaluation_id = derive_reference_evaluation_id(
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_id,
        evaluation_horizon=NOW,
    )
    return ReferenceIntegrityEvaluation(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        resolution_record_id=record_id,
        resolution_outcome=resolution_outcome,
        outcome=outcome,
        evaluation_horizon=NOW,
        evaluated_on=NOW,
    )


def test_resolved_and_satisfied_is_a_consistent_pairing() -> None:
    evaluation = _evaluation(
        resolution_outcome=ResolutionOutcome.RESOLVED, outcome=EvaluationOutcome.SATISFIED
    )
    assert evaluation.outcome is EvaluationOutcome.SATISFIED


def test_unresolved_and_violated_is_a_consistent_pairing() -> None:
    evaluation = _evaluation(
        resolution_outcome=ResolutionOutcome.UNRESOLVED, outcome=EvaluationOutcome.VIOLATED
    )
    assert evaluation.outcome is EvaluationOutcome.VIOLATED


def test_resolved_and_violated_is_rejected_as_inconsistent() -> None:
    with pytest.raises(ValidationException):
        _evaluation(
            resolution_outcome=ResolutionOutcome.RESOLVED, outcome=EvaluationOutcome.VIOLATED
        )


def test_unresolved_and_satisfied_is_rejected_as_inconsistent() -> None:
    with pytest.raises(ValidationException):
        _evaluation(
            resolution_outcome=ResolutionOutcome.UNRESOLVED, outcome=EvaluationOutcome.SATISFIED
        )


def test_possible_resolution_outcome_can_never_be_persisted() -> None:
    # PO-H4-04: POSSIBLE is NOT_EVALUABLE -- zero row -- so the dataclass
    # itself must fail closed if anyone ever tries to construct one.
    with pytest.raises(ValidationException):
        _evaluation(
            resolution_outcome=ResolutionOutcome.POSSIBLE, outcome=EvaluationOutcome.SATISFIED
        )


def test_reference_evaluation_rejects_tampered_evaluation_id() -> None:
    evaluation = _evaluation()
    with pytest.raises(ValidationException):
        ReferenceIntegrityEvaluation(
            evaluation_id=uuid4(),
            tenant_id=evaluation.tenant_id,
            relationship_requirement_id=evaluation.relationship_requirement_id,
            source_object_id=evaluation.source_object_id,
            resolution_record_id=evaluation.resolution_record_id,
            resolution_outcome=evaluation.resolution_outcome,
            outcome=evaluation.outcome,
            evaluation_horizon=evaluation.evaluation_horizon,
            evaluated_on=evaluation.evaluated_on,
        )


# --- ReferenceIntegrityFinding shape ---


def _finding(
    *,
    status: IntegrityFindingStatus = IntegrityFindingStatus.OPEN,
    state_revision: int = 1,
    occurrence_count: int = 1,
    reopen_count: int = 0,
) -> ReferenceIntegrityFinding:
    requirement_id, source_object_id = uuid4(), uuid4()
    return ReferenceIntegrityFinding(
        finding_id=derive_reference_finding_id(
            tenant_id=TENANT,
            relationship_requirement_id=requirement_id,
            source_object_id=source_object_id,
        ),
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
        finding_type=IntegrityFindingType.ORPHAN_REFERENCE,
        status=status,
        state_revision=state_revision,
        first_seen_at=NOW,
        last_seen_at=NOW,
        last_evaluated_horizon=NOW,
        occurrence_count=occurrence_count,
        reopen_count=reopen_count,
    )


def test_reference_finding_type_is_fixed_to_orphan_reference() -> None:
    finding = _finding()
    assert finding.finding_type is IntegrityFindingType.ORPHAN_REFERENCE


def test_reference_finding_rejects_a_structural_finding_type() -> None:
    requirement_id, source_object_id = uuid4(), uuid4()
    with pytest.raises(ValidationException):
        ReferenceIntegrityFinding(
            finding_id=derive_reference_finding_id(
                tenant_id=TENANT,
                relationship_requirement_id=requirement_id,
                source_object_id=source_object_id,
            ),
            tenant_id=TENANT,
            relationship_requirement_id=requirement_id,
            source_object_id=source_object_id,
            finding_type=IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
            status=IntegrityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )


def test_reference_finding_rejects_reopen_count_exceeding_occurrence_minus_one() -> None:
    with pytest.raises(ValidationException):
        _finding(occurrence_count=1, reopen_count=1)


# --- apply_reference_finding_transition ---


def test_reference_transition_no_existing_and_satisfied_produces_no_finding() -> None:
    result = apply_reference_finding_transition(
        existing=None,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW,
        tenant_id=TENANT,
        relationship_requirement_id=uuid4(),
        source_object_id=uuid4(),
    )
    assert result is None


def test_reference_transition_no_existing_and_violated_opens_orphan_finding() -> None:
    requirement_id, source_object_id = uuid4(), uuid4()
    result = apply_reference_finding_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW,
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        source_object_id=source_object_id,
    )
    assert result is not None
    assert result.finding_type is IntegrityFindingType.ORPHAN_REFERENCE
    assert result.status is IntegrityFindingStatus.OPEN
    assert result.occurrence_count == 1
    assert result.reopen_count == 0


def test_reference_transition_open_and_satisfied_resolves() -> None:
    existing = _finding()
    result = apply_reference_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW + timedelta(hours=1),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        source_object_id=existing.source_object_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.RESOLVED
    assert result.state_revision == existing.state_revision + 1


def test_reference_transition_resolved_and_violated_reopens() -> None:
    existing = _finding(status=IntegrityFindingStatus.RESOLVED, state_revision=2)
    result = apply_reference_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.VIOLATED,
        evaluation_horizon=NOW + timedelta(hours=2),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        source_object_id=existing.source_object_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.OPEN
    assert result.occurrence_count == existing.occurrence_count + 1
    assert result.reopen_count == existing.reopen_count + 1


def test_reference_transition_resolved_and_satisfied_stays_resolved_idempotently() -> None:
    existing = _finding(status=IntegrityFindingStatus.RESOLVED, state_revision=2)
    result = apply_reference_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.SATISFIED,
        evaluation_horizon=NOW + timedelta(hours=2),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        source_object_id=existing.source_object_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.RESOLVED
    assert result.occurrence_count == existing.occurrence_count
    assert result.reopen_count == existing.reopen_count


def test_reference_transition_rejects_mismatched_existing_identity() -> None:
    existing = _finding()
    with pytest.raises(ValidationException):
        apply_reference_finding_transition(
            existing=existing,
            outcome=EvaluationOutcome.VIOLATED,
            evaluation_horizon=NOW,
            tenant_id=existing.tenant_id,
            relationship_requirement_id=uuid4(),
            source_object_id=existing.source_object_id,
        )


def test_reference_finding_id_type_check() -> None:
    with pytest.raises(ValidationException):
        ReferenceIntegrityFinding(
            finding_id="not-a-uuid",  # type: ignore[arg-type]
            tenant_id=TENANT,
            relationship_requirement_id=uuid4(),
            source_object_id=uuid4(),
            finding_type=IntegrityFindingType.ORPHAN_REFERENCE,
            status=IntegrityFindingStatus.OPEN,
            state_revision=1,
            first_seen_at=NOW,
            last_seen_at=NOW,
            last_evaluated_horizon=NOW,
            occurrence_count=1,
            reopen_count=0,
        )
