"""CDD-047 Artifact Authorization row 7: `compute_generalized_coverage`
proved in isolation from real persistence, by substituting (never a real
session query) `get_active_policy` / `has_qualifying_coverage_for_dimension`
-- the "fake-repo" pattern this repository's own test suite uses elsewhere
for algorithm-level proofs distinct from real-Postgres integration proofs
(see test_oqi_quality_coverage_policy_postgres.py for the latter)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import (
    CoverageDimension,
    QualityCoveragePolicy,
    create_quality_coverage_policy,
)
from app.infrastructure.persistence.oqi_quality_coverage_policy_repository import (
    OqiQualityCoveragePolicyRepositoryImpl,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)
TENANT = "tenant-a"


def _repo() -> OqiQualityCoveragePolicyRepositoryImpl:
    # `session` is never touched by `compute_generalized_coverage` itself --
    # only by the patched methods below -- so `None` is a valid stand-in.
    return OqiQualityCoveragePolicyRepositoryImpl(session=None)  # type: ignore[arg-type]


def _policy(required: frozenset[CoverageDimension]) -> QualityCoveragePolicy:
    return create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id=TENANT,
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        required_dimensions=required,
        created_by="steward",
        created_on=NOW,
    )


# ---------------------------------------------------------------------
# CDD-047 §18 truth table -- no-policy branch is a literal pass-through.
# ---------------------------------------------------------------------


@pytest.mark.parametrize("legacy_value", [True, False])
def test_no_active_policy_returns_legacy_value_verbatim(legacy_value: bool) -> None:
    repo = _repo()
    with patch.object(repo, "get_active_policy", return_value=None) as mocked_lookup:
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=legacy_value,
        )
    assert result is legacy_value
    mocked_lookup.assert_called_once()


# ---------------------------------------------------------------------
# CDD-047 §12 -- policy aggregation, "every required dimension" semantics.
# ---------------------------------------------------------------------


def test_one_required_dimension_covered_yields_true() -> None:
    repo = _repo()
    policy = _policy(frozenset({CoverageDimension.COMPLETENESS}))
    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension", return_value=True),
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )
    assert result is True


def test_one_required_dimension_uncovered_yields_false() -> None:
    repo = _repo()
    policy = _policy(frozenset({CoverageDimension.COMPLETENESS}))
    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension", return_value=False),
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=True,  # legacy value must NOT leak through
        )
    assert result is False


def test_three_required_all_covered_yields_true() -> None:
    repo = _repo()
    policy = _policy(
        frozenset(
            {
                CoverageDimension.COMPLETENESS,
                CoverageDimension.VALIDITY,
                CoverageDimension.CONSISTENCY,
            }
        )
    )
    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension", return_value=True) as mocked,
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )
    assert result is True
    assert mocked.call_count == 3


def test_three_required_one_missing_yields_false() -> None:
    repo = _repo()
    policy = _policy(
        frozenset(
            {
                CoverageDimension.COMPLETENESS,
                CoverageDimension.VALIDITY,
                CoverageDimension.CONSISTENCY,
            }
        )
    )

    def _side_effect(
        *, tenant_id: str, source_object_ids: tuple[UUID, ...], dimension: CoverageDimension
    ) -> bool:
        return dimension != CoverageDimension.CONSISTENCY

    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension", side_effect=_side_effect),
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )
    assert result is False


def test_nine_required_only_three_covered_yields_false() -> None:
    repo = _repo()
    policy = _policy(frozenset(CoverageDimension))
    covered = {
        CoverageDimension.COMPLETENESS,
        CoverageDimension.VALIDITY,
        CoverageDimension.CONSISTENCY,
    }

    def _side_effect(
        *, tenant_id: str, source_object_ids: tuple[UUID, ...], dimension: CoverageDimension
    ) -> bool:
        return dimension in covered

    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension", side_effect=_side_effect),
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )
    assert result is False


# ---------------------------------------------------------------------
# CDD-047 §15 -- relationship / no-source-object-resolution boundary.
# ---------------------------------------------------------------------


def test_empty_source_object_ids_short_circuits_to_false_without_querying() -> None:
    """Covers both the RELATIONSHIP-anchor case and any ENTITY subject
    with zero resolvable source objects -- the caller already passes an
    empty tuple for both (CDD-047 §15)."""
    repo = _repo()
    policy = _policy(frozenset({CoverageDimension.COMPLETENESS}))
    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(repo, "has_qualifying_coverage_for_dimension") as mocked,
    ):
        result = repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.RELATIONSHIP,
            ontology_element_id=uuid4(),
            source_object_ids=(),
            legacy_any_evaluation_ever_run=False,
        )
    assert result is False
    mocked.assert_not_called()


# ---------------------------------------------------------------------
# Unsupported (future) dimension dispatch (CDD-047 §14). CDD-048 §23
# (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I final report):
# ACCURACY, REASONABLENESS, and INTEGRITY (CDD-050 §24) are removed from
# this parametrize list -- they now have live evaluators/dispatch and are
# proven to dispatch correctly (not unconditionally False) by the tests
# immediately below this class. UNIQUENESS/TIMELINESS remain genuinely
# unsupported.
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "dimension",
    [
        CoverageDimension.UNIQUENESS,
        CoverageDimension.TIMELINESS,
    ],
)
def test_unsupported_dimension_dispatch_returns_false_without_querying(
    dimension: CoverageDimension,
) -> None:
    repo = _repo()
    with (
        patch(
            "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
            "OqiQualityEvaluationRepositoryImpl"
        ) as oqi1_cls,
        patch(
            "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
            "OqiCrossSourceEvaluationRepositoryImpl"
        ) as oqi2_cls,
    ):
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=dimension
        )
    assert result is False
    oqi1_cls.assert_not_called()
    oqi2_cls.assert_not_called()


def test_completeness_and_validity_dispatch_to_oqi1() -> None:
    repo = _repo()
    for dimension in (CoverageDimension.COMPLETENESS, CoverageDimension.VALIDITY):
        with patch(
            "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
            "OqiQualityEvaluationRepositoryImpl"
        ) as oqi1_cls:
            oqi1_cls.return_value.has_qualifying_coverage_for_dimension.return_value = True
            result = repo.has_qualifying_coverage_for_dimension(
                tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=dimension
            )
        assert result is True
        oqi1_cls.return_value.has_qualifying_coverage_for_dimension.assert_called_once()


def test_consistency_dispatches_to_oqi2() -> None:
    repo = _repo()
    with patch(
        "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
        "OqiCrossSourceEvaluationRepositoryImpl"
    ) as oqi2_cls:
        oqi2_cls.return_value.has_qualifying_coverage_for_dimension.return_value = True
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=CoverageDimension.CONSISTENCY
        )
    assert result is True
    oqi2_cls.return_value.has_qualifying_coverage_for_dimension.assert_called_once()


def test_accuracy_dispatches_to_accuracy_repository() -> None:
    """CDD-048 §23 (OQI-H2-I-R1 narrow correction, disclosed in the
    OQI-H2-I final report): ACCURACY is OQI1-storage-shaped -- dispatches
    to `OqiAccuracyEvaluationRepositoryImpl`, never unconditionally False."""
    repo = _repo()
    with patch(
        "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
        "OqiAccuracyEvaluationRepositoryImpl"
    ) as accuracy_cls:
        accuracy_cls.return_value.has_qualifying_coverage_for_dimension.return_value = True
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=CoverageDimension.ACCURACY
        )
    assert result is True
    accuracy_cls.return_value.has_qualifying_coverage_for_dimension.assert_called_once()


def test_conformity_dispatches_to_conformity_evaluation_repository() -> None:
    """CDD-049 §21 (OQI-H3-I-R1 narrow correction, disclosed in the H3-I-R1
    amendment): CONFORMITY is OQI1-storage-shaped -- dispatches to
    `OqiConformityEvaluationRepositoryImpl`, never unconditionally False."""
    repo = _repo()
    with patch(
        "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
        "OqiConformityEvaluationRepositoryImpl"
    ) as conformity_cls:
        conformity_cls.return_value.has_qualifying_coverage_for_dimension.return_value = True
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=CoverageDimension.CONFORMITY
        )
    assert result is True
    conformity_cls.return_value.has_qualifying_coverage_for_dimension.assert_called_once()


def test_reasonableness_dispatches_to_business_rule_evaluation_repository() -> None:
    """CDD-048 §23 (OQI-H2-I-R1 narrow correction, disclosed in the
    OQI-H2-I final report): REASONABLENESS is OQI3-storage-shaped --
    dispatches to `OqiBusinessRuleEvaluationRepositoryImpl`, never
    unconditionally False."""
    repo = _repo()
    with patch(
        "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
        "OqiBusinessRuleEvaluationRepositoryImpl"
    ) as business_rule_cls:
        business_rule_cls.return_value.has_qualifying_coverage_for_dimension.return_value = True
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT,
            source_object_ids=(uuid4(),),
            dimension=CoverageDimension.REASONABLENESS,
        )
    assert result is True
    business_rule_cls.return_value.has_qualifying_coverage_for_dimension.assert_called_once()


def test_integrity_dispatches_to_integrity_evaluation_repositories() -> None:
    """CDD-050 §24: INTEGRITY is existence-only, subject-scoped, across
    BOTH new evaluation tables -- Reference is consulted first (an exact
    `source_object_id` match), short-circuiting before any ER-resolution
    attempt for Structural coverage."""
    repo = _repo()
    with patch(
        "app.infrastructure.persistence.oqi_quality_coverage_policy_repository."
        "OqiIntegrityReferenceEvaluationRepositoryImpl"
    ) as reference_cls:
        reference_cls.return_value.has_qualifying_coverage.return_value = True
        result = repo.has_qualifying_coverage_for_dimension(
            tenant_id=TENANT, source_object_ids=(uuid4(),), dimension=CoverageDimension.INTEGRITY
        )
    assert result is True
    reference_cls.return_value.has_qualifying_coverage.assert_called_once()


# ---------------------------------------------------------------------
# Exception propagation must never default to True.
# ---------------------------------------------------------------------


def test_exception_in_active_policy_lookup_propagates_never_defaults_true() -> None:
    repo = _repo()
    with (
        patch.object(repo, "get_active_policy", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )


def test_exception_in_dimension_coverage_check_propagates_never_defaults_true() -> None:
    repo = _repo()
    policy = _policy(frozenset({CoverageDimension.COMPLETENESS}))
    with (
        patch.object(repo, "get_active_policy", return_value=policy),
        patch.object(
            repo, "has_qualifying_coverage_for_dimension", side_effect=RuntimeError("boom")
        ),
        pytest.raises(RuntimeError, match="boom"),
    ):
        repo.compute_generalized_coverage(
            tenant_id=TENANT,
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            source_object_ids=(uuid4(),),
            legacy_any_evaluation_ever_run=False,
        )
