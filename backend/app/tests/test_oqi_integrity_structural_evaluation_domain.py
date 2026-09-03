"""Pure domain unit tests for `app.domain.oqi_integrity.requirement` and
`app.domain.oqi_integrity.structural` (CDD-050 §7, §10.1, §14-§16;
Artifact Authorization row 17): the governed cardinality envelope, the
Structural Integrity evaluation/Finding dataclasses, deterministic identity
derivation, and the Finding-lifecycle transition function -- all in
isolation, no PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.oqi.evaluation import EvaluationOutcome
from app.domain.oqi.quality_rule import OQI_NAMESPACE
from app.domain.oqi_cross_source.correspondence import OQI_CROSS_SOURCE_NAMESPACE
from app.domain.oqi_integrity.requirement import (
    IntegrityRelationshipCardinality,
    IntegrityRelationshipCardinalityStatus,
    activate_new_cardinality_version,
)
from app.domain.oqi_integrity.structural import (
    OQI_INTEGRITY_NAMESPACE,
    IntegrityFindingStatus,
    IntegrityFindingType,
    StructuralIntegrityEvaluation,
    StructuralIntegrityFinding,
    apply_structural_finding_transition,
    derive_structural_evaluation_id,
    derive_structural_finding_id,
    structural_finding_identity_material,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT = "tenant-a"


def _cardinality(
    *,
    cardinality_id: UUID | None = None,
    requirement_id: UUID | None = None,
    min_cardinality: int = 1,
    max_cardinality: int | None = 1,
    version_number: int = 1,
    previous_version_id: UUID | None = None,
    status: IntegrityRelationshipCardinalityStatus = IntegrityRelationshipCardinalityStatus.ACTIVE,
    retired_on: datetime | None = None,
) -> IntegrityRelationshipCardinality:
    return IntegrityRelationshipCardinality(
        integrity_relationship_cardinality_id=cardinality_id or uuid4(),
        relationship_requirement_id=requirement_id or uuid4(),
        min_cardinality=min_cardinality,
        max_cardinality=max_cardinality,
        version_number=version_number,
        previous_version_id=previous_version_id,
        status=status,
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


# --- IntegrityRelationshipCardinality validation (P-series: policy) ---


def test_cardinality_rejects_negative_min() -> None:
    with pytest.raises(ValidationException):
        _cardinality(min_cardinality=-1, max_cardinality=None)


def test_cardinality_allows_unbounded_max() -> None:
    assert _cardinality(min_cardinality=0, max_cardinality=None).max_cardinality is None


def test_cardinality_rejects_max_below_min() -> None:
    with pytest.raises(ValidationException):
        _cardinality(min_cardinality=2, max_cardinality=1)


def test_cardinality_allows_max_equal_min() -> None:
    assert _cardinality(min_cardinality=1, max_cardinality=1).max_cardinality == 1


def test_cardinality_allows_min_zero() -> None:
    # PO-H4-03: OPTIONAL obligation is compatible with min_cardinality=0.
    assert _cardinality(min_cardinality=0, max_cardinality=None).min_cardinality == 0


def test_cardinality_version_one_must_not_carry_previous_version_id() -> None:
    with pytest.raises(ValidationException):
        _cardinality(version_number=1, previous_version_id=uuid4())


def test_cardinality_version_above_one_requires_previous_version_id() -> None:
    with pytest.raises(ValidationException):
        _cardinality(version_number=2, previous_version_id=None)


def test_cardinality_active_must_not_carry_retired_on() -> None:
    with pytest.raises(ValidationException):
        _cardinality(status=IntegrityRelationshipCardinalityStatus.ACTIVE, retired_on=NOW)


def test_cardinality_retired_requires_retired_on() -> None:
    with pytest.raises(ValidationException):
        _cardinality(status=IntegrityRelationshipCardinalityStatus.RETIRED, retired_on=None)


def test_activate_new_cardinality_version_first_version() -> None:
    requirement_id = uuid4()
    new = activate_new_cardinality_version(
        existing_active=None,
        integrity_relationship_cardinality_id=uuid4(),
        relationship_requirement_id=requirement_id,
        min_cardinality=1,
        max_cardinality=1,
        created_by="steward",
        created_on=NOW,
    )
    assert new.version_number == 1
    assert new.previous_version_id is None
    assert new.status is IntegrityRelationshipCardinalityStatus.ACTIVE


def test_activate_new_cardinality_version_increments_from_existing() -> None:
    existing = _cardinality(version_number=1, previous_version_id=None)
    new = activate_new_cardinality_version(
        existing_active=existing,
        integrity_relationship_cardinality_id=uuid4(),
        relationship_requirement_id=existing.relationship_requirement_id,
        min_cardinality=2,
        max_cardinality=2,
        created_by="steward",
        created_on=NOW,
    )
    assert new.version_number == 2
    assert new.previous_version_id == existing.integrity_relationship_cardinality_id


# --- Deterministic identity (mirrors CDD-039 §20's own precedent) ---


def test_structural_namespace_is_distinct_from_every_other_oqi_namespace() -> None:
    assert OQI_INTEGRITY_NAMESPACE != OQI_NAMESPACE
    assert OQI_INTEGRITY_NAMESPACE != OQI_CROSS_SOURCE_NAMESPACE


def test_structural_finding_identity_material_excludes_cardinality_and_horizon() -> None:
    tenant_id, requirement_id, entity_id = TENANT, uuid4(), uuid4()
    material_a = structural_finding_identity_material(
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
    )
    material_b = structural_finding_identity_material(
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
    )
    assert material_a == material_b


def test_derive_structural_finding_id_is_deterministic_and_sensitive_to_each_input() -> None:
    requirement_id, entity_id = uuid4(), uuid4()
    base = derive_structural_finding_id(
        tenant_id=TENANT, relationship_requirement_id=requirement_id, enterprise_entity_id=entity_id
    )
    replay = derive_structural_finding_id(
        tenant_id=TENANT, relationship_requirement_id=requirement_id, enterprise_entity_id=entity_id
    )
    assert base == replay
    assert base != derive_structural_finding_id(
        tenant_id="tenant-b",
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
    )
    assert base != derive_structural_finding_id(
        tenant_id=TENANT, relationship_requirement_id=uuid4(), enterprise_entity_id=entity_id
    )
    assert base != derive_structural_finding_id(
        tenant_id=TENANT, relationship_requirement_id=requirement_id, enterprise_entity_id=uuid4()
    )


def test_derive_structural_evaluation_id_changes_with_qualifying_targets_and_horizon() -> None:
    requirement_id, entity_id, cardinality_id = uuid4(), uuid4(), uuid4()
    target_a, target_b = uuid4(), uuid4()

    def _id(horizon: datetime, targets: tuple[UUID, ...]) -> UUID:
        return derive_structural_evaluation_id(
            tenant_id=TENANT,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=entity_id,
            integrity_relationship_cardinality_id=cardinality_id,
            evaluation_horizon=horizon,
            qualifying_target_ids=targets,
        )

    base = _id(NOW, (target_a,))
    assert base == _id(NOW, (target_a,))
    assert base != _id(NOW, (target_a, target_b))
    assert base != _id(NOW + timedelta(hours=1), (target_a,))


def test_derive_structural_evaluation_id_rejects_naive_horizon() -> None:
    with pytest.raises(ValidationException):
        derive_structural_evaluation_id(
            tenant_id=TENANT,
            relationship_requirement_id=uuid4(),
            enterprise_entity_id=uuid4(),
            integrity_relationship_cardinality_id=uuid4(),
            evaluation_horizon=datetime(2026, 1, 1),  # noqa: DTZ001 -- deliberately naive
            qualifying_target_ids=(),
        )


# --- StructuralIntegrityEvaluation / StructuralIntegrityFinding shape ---


def _evaluation(
    *,
    outcome: EvaluationOutcome = EvaluationOutcome.SATISFIED,
    qualifying_target_ids: tuple[UUID, ...] = (),
) -> StructuralIntegrityEvaluation:
    tenant_id, requirement_id, entity_id, cardinality_id = TENANT, uuid4(), uuid4(), uuid4()
    evaluation_id = derive_structural_evaluation_id(
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
        integrity_relationship_cardinality_id=cardinality_id,
        evaluation_horizon=NOW,
        qualifying_target_ids=qualifying_target_ids,
    )
    return StructuralIntegrityEvaluation(
        evaluation_id=evaluation_id,
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        integrity_relationship_cardinality_id=cardinality_id,
        enterprise_entity_id=entity_id,
        qualifying_target_ids=qualifying_target_ids,
        outcome=outcome,
        evaluation_horizon=NOW,
        evaluated_on=NOW,
    )


def test_structural_evaluation_accepts_consistent_identity() -> None:
    evaluation = _evaluation()
    assert evaluation.outcome is EvaluationOutcome.SATISFIED


def test_structural_evaluation_rejects_tampered_evaluation_id() -> None:
    evaluation = _evaluation()
    with pytest.raises(ValidationException):
        StructuralIntegrityEvaluation(
            evaluation_id=uuid4(),
            tenant_id=evaluation.tenant_id,
            relationship_requirement_id=evaluation.relationship_requirement_id,
            integrity_relationship_cardinality_id=evaluation.integrity_relationship_cardinality_id,
            enterprise_entity_id=evaluation.enterprise_entity_id,
            qualifying_target_ids=evaluation.qualifying_target_ids,
            outcome=evaluation.outcome,
            evaluation_horizon=evaluation.evaluation_horizon,
            evaluated_on=evaluation.evaluated_on,
        )


def test_structural_evaluation_rejects_duplicate_qualifying_targets() -> None:
    duplicate = uuid4()
    with pytest.raises(ValidationException):
        _evaluation(qualifying_target_ids=(duplicate, duplicate))


def _finding(
    *,
    finding_type: IntegrityFindingType = IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
    status: IntegrityFindingStatus = IntegrityFindingStatus.OPEN,
    state_revision: int = 1,
    occurrence_count: int = 1,
    reopen_count: int = 0,
    tenant_id: str = TENANT,
    requirement_id: UUID | None = None,
    entity_id: UUID | None = None,
) -> StructuralIntegrityFinding:
    requirement_id = requirement_id or uuid4()
    entity_id = entity_id or uuid4()
    return StructuralIntegrityFinding(
        finding_id=derive_structural_finding_id(
            tenant_id=tenant_id,
            relationship_requirement_id=requirement_id,
            enterprise_entity_id=entity_id,
        ),
        tenant_id=tenant_id,
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
        finding_type=finding_type,
        status=status,
        state_revision=state_revision,
        first_seen_at=NOW,
        last_seen_at=NOW,
        last_evaluated_horizon=NOW,
        occurrence_count=occurrence_count,
        reopen_count=reopen_count,
    )


def test_structural_finding_rejects_orphan_reference_type() -> None:
    with pytest.raises(ValidationException):
        _finding(finding_type=IntegrityFindingType.ORPHAN_REFERENCE)


def test_structural_finding_rejects_reopen_count_exceeding_occurrence_minus_one() -> None:
    with pytest.raises(ValidationException):
        _finding(occurrence_count=1, reopen_count=1)


def test_structural_finding_rejects_tampered_finding_id() -> None:
    finding = _finding()
    with pytest.raises(ValidationException):
        StructuralIntegrityFinding(
            finding_id=uuid4(),
            tenant_id=finding.tenant_id,
            relationship_requirement_id=finding.relationship_requirement_id,
            enterprise_entity_id=finding.enterprise_entity_id,
            finding_type=finding.finding_type,
            status=finding.status,
            state_revision=finding.state_revision,
            first_seen_at=finding.first_seen_at,
            last_seen_at=finding.last_seen_at,
            last_evaluated_horizon=finding.last_evaluated_horizon,
            occurrence_count=finding.occurrence_count,
            reopen_count=finding.reopen_count,
        )


# --- apply_structural_finding_transition (L-series: lifecycle) ---


def test_transition_no_existing_and_satisfied_produces_no_finding() -> None:
    result = apply_structural_finding_transition(
        existing=None,
        outcome=EvaluationOutcome.SATISFIED,
        finding_type=IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
        evaluation_horizon=NOW,
        tenant_id=TENANT,
        relationship_requirement_id=uuid4(),
        enterprise_entity_id=uuid4(),
    )
    assert result is None


def test_transition_no_existing_and_violated_opens_a_new_finding() -> None:
    requirement_id, entity_id = uuid4(), uuid4()
    result = apply_structural_finding_transition(
        existing=None,
        outcome=EvaluationOutcome.VIOLATED,
        finding_type=IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
        evaluation_horizon=NOW,
        tenant_id=TENANT,
        relationship_requirement_id=requirement_id,
        enterprise_entity_id=entity_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.OPEN
    assert result.state_revision == 1
    assert result.occurrence_count == 1
    assert result.reopen_count == 0
    assert result.finding_type is IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP


def test_transition_open_and_violated_refreshes_without_reopening() -> None:
    existing = _finding(finding_type=IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP)
    later = NOW + timedelta(hours=1)
    result = apply_structural_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.VIOLATED,
        finding_type=IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION,
        evaluation_horizon=later,
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        enterprise_entity_id=existing.enterprise_entity_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.OPEN
    assert result.state_revision == existing.state_revision + 1
    assert result.occurrence_count == existing.occurrence_count
    assert result.reopen_count == existing.reopen_count
    # Precedence can genuinely change type across re-evaluations (e.g. an
    # edge added then a second edge added crossing max) without a reopen.
    assert result.finding_type is IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION


def test_transition_open_and_satisfied_resolves() -> None:
    existing = _finding()
    result = apply_structural_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.SATISFIED,
        finding_type=existing.finding_type,
        evaluation_horizon=NOW + timedelta(hours=1),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        enterprise_entity_id=existing.enterprise_entity_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.RESOLVED
    assert result.state_revision == existing.state_revision + 1


def test_transition_resolved_and_satisfied_stays_resolved_idempotently() -> None:
    existing = _finding(status=IntegrityFindingStatus.RESOLVED, state_revision=2)
    result = apply_structural_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.SATISFIED,
        finding_type=existing.finding_type,
        evaluation_horizon=NOW + timedelta(hours=2),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        enterprise_entity_id=existing.enterprise_entity_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.RESOLVED
    assert result.state_revision == existing.state_revision + 1
    assert result.occurrence_count == existing.occurrence_count
    assert result.reopen_count == existing.reopen_count


def test_transition_resolved_and_violated_reopens_and_increments_reopen_count() -> None:
    existing = _finding(status=IntegrityFindingStatus.RESOLVED, state_revision=2)
    result = apply_structural_finding_transition(
        existing=existing,
        outcome=EvaluationOutcome.VIOLATED,
        finding_type=IntegrityFindingType.RELATIONSHIP_CARDINALITY_VIOLATION,
        evaluation_horizon=NOW + timedelta(hours=2),
        tenant_id=existing.tenant_id,
        relationship_requirement_id=existing.relationship_requirement_id,
        enterprise_entity_id=existing.enterprise_entity_id,
    )
    assert result is not None
    assert result.status is IntegrityFindingStatus.OPEN
    assert result.occurrence_count == existing.occurrence_count + 1
    assert result.reopen_count == existing.reopen_count + 1


def test_transition_rejects_mismatched_existing_identity() -> None:
    existing = _finding()
    with pytest.raises(ValidationException):
        apply_structural_finding_transition(
            existing=existing,
            outcome=EvaluationOutcome.VIOLATED,
            finding_type=IntegrityFindingType.MISSING_REQUIRED_RELATIONSHIP,
            evaluation_horizon=NOW,
            tenant_id=existing.tenant_id,
            relationship_requirement_id=uuid4(),
            enterprise_entity_id=existing.enterprise_entity_id,
        )
