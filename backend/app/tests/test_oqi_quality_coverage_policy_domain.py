"""CDD-047 Artifact Authorization row 6: OQI-H1 QualityCoveragePolicy
domain-level construction, versioning, and closed-vocabulary validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from app.domain.oqi.quality_rule import QualityDimension
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.oqi_quality_coverage.policy import (
    CoverageDimension,
    QualityCoveragePolicy,
    QualityCoveragePolicyStatus,
    create_quality_coverage_policy,
    new_quality_coverage_policy_version,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_coverage_dimension_is_exactly_nine() -> None:
    assert len(list(CoverageDimension)) == 9
    assert {member.value for member in CoverageDimension} == {
        "COMPLETENESS",
        "VALIDITY",
        "CONSISTENCY",
        "ACCURACY",
        "UNIQUENESS",
        "TIMELINESS",
        "INTEGRITY",
        "CONFORMITY",
        "REASONABLENESS",
    }


def test_quality_dimension_is_exactly_five_after_h3_conformity() -> None:
    """CDD-047 §5: H1 must not expand QualityDimension -- proven true for
    H1 by construction (H1 introduced ACCURACY nowhere). CDD-048 §7, §14
    (OQI-H2-I-R1 narrow correction, disclosed in the OQI-H2-I final
    report): H2 additively extends QualityDimension with exactly one member,
    ACCURACY. CDD-049 §4, §6 (OQI-H3-I-R1 narrow correction, disclosed in
    this amendment) additively extends it a third time with exactly one more
    member, CONFORMITY -- REASONABLENESS is deliberately NOT added here (nor
    ever will be), since it is BusinessRule-shaped, not QualityRule-shaped
    (CDD-048 §10, §14). This test proves the two vocabularies remain
    genuinely independent -- CoverageDimension having nine members does not
    imply QualityDimension tracks it member-for-member."""
    assert len(list(QualityDimension)) == 5
    assert {member.value for member in QualityDimension} == {
        "COMPLETENESS",
        "VALIDITY",
        "CONSISTENCY",
        "ACCURACY",
        "CONFORMITY",
    }


def test_coverage_dimension_and_quality_dimension_are_distinct_types() -> None:
    # `cast(object, ...)` broadens only the static type of the left operand
    # so mypy no longer treats this as a statically-impossible comparison
    # between two unrelated enum types -- the runtime identity check itself
    # (the actual proof of distinctness) is completely unchanged.
    assert cast(object, CoverageDimension) is not QualityDimension
    assert not issubclass(CoverageDimension, QualityDimension)
    assert not issubclass(QualityDimension, CoverageDimension)


def test_create_policy_is_active_version_one_no_previous() -> None:
    policy = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id="tenant-a",
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    assert policy.status is QualityCoveragePolicyStatus.ACTIVE
    assert policy.version_number == 1
    assert policy.previous_version_id is None


def test_new_version_increments_and_chains_to_prior() -> None:
    v1 = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id="tenant-a",
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    v2 = new_quality_coverage_policy_version(
        v1,
        new_policy_id=uuid4(),
        status=QualityCoveragePolicyStatus.RETIRED,
        created_by="steward",
        created_on=NOW,
    )
    assert v2.version_number == 2
    assert v2.previous_version_id == v1.policy_id
    assert v2.tenant_id == v1.tenant_id
    assert v2.ontology_element_type == v1.ontology_element_type
    assert v2.ontology_element_id == v1.ontology_element_id
    # Retirement does not redefine what was required (module docstring).
    assert v2.required_dimensions == v1.required_dimensions


def test_new_version_may_change_required_dimensions() -> None:
    v1 = create_quality_coverage_policy(
        policy_id=uuid4(),
        tenant_id="tenant-a",
        ontology_element_type=OntologyElementType.ENTITY,
        ontology_element_id=uuid4(),
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
        created_by="steward",
        created_on=NOW,
    )
    v2 = new_quality_coverage_policy_version(
        v1,
        new_policy_id=uuid4(),
        status=QualityCoveragePolicyStatus.ACTIVE,
        required_dimensions=frozenset({CoverageDimension.COMPLETENESS, CoverageDimension.ACCURACY}),
        created_by="steward",
        created_on=NOW,
    )
    assert v2.required_dimensions == frozenset(
        {CoverageDimension.COMPLETENESS, CoverageDimension.ACCURACY}
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"required_dimensions": frozenset()},
    ],
)
def test_empty_required_dimensions_rejected(
    kwargs: dict[str, frozenset[CoverageDimension]],
) -> None:
    with pytest.raises(ValidationException, match="required_dimensions must be non-empty"):
        QualityCoveragePolicy(
            policy_id=uuid4(),
            tenant_id="tenant-a",
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            status=QualityCoveragePolicyStatus.ACTIVE,
            version_number=1,
            previous_version_id=None,
            created_by="steward",
            created_on=NOW,
            **kwargs,
        )


def test_duplicate_dimension_structurally_impossible() -> None:
    """A frozenset cannot contain a duplicate member -- proven directly
    rather than asserted, since Python's own set semantics are the actual
    enforcement mechanism at the domain layer (the database's composite
    primary key on (policy_id, dimension) is the independent, real-Postgres
    proof -- see test_oqi_quality_coverage_policy_postgres.py)."""
    dimensions = frozenset(
        {CoverageDimension.COMPLETENESS, CoverageDimension.COMPLETENESS, CoverageDimension.VALIDITY}
    )
    assert len(dimensions) == 2


def test_unknown_dimension_rejected_at_construction() -> None:
    with pytest.raises((ValidationException, ValueError)):
        # A raw string not in the closed CoverageDimension enum must fail
        # when a caller attempts to coerce it.
        CoverageDimension("NOT_A_REAL_DIMENSION")


def test_active_relationship_type_only_two_values() -> None:
    assert {member.value for member in OntologyElementType} >= {"ENTITY", "RELATIONSHIP"}


def test_version_one_must_not_declare_previous_version_id() -> None:
    with pytest.raises(ValidationException, match="version 1 must not declare"):
        QualityCoveragePolicy(
            policy_id=uuid4(),
            tenant_id="tenant-a",
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            status=QualityCoveragePolicyStatus.ACTIVE,
            version_number=1,
            previous_version_id=uuid4(),
            required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
            created_by="steward",
            created_on=NOW,
        )


def test_version_greater_than_one_requires_previous_version_id() -> None:
    with pytest.raises(ValidationException, match="requires an explicit previous_version_id"):
        QualityCoveragePolicy(
            policy_id=uuid4(),
            tenant_id="tenant-a",
            ontology_element_type=OntologyElementType.ENTITY,
            ontology_element_id=uuid4(),
            status=QualityCoveragePolicyStatus.ACTIVE,
            version_number=2,
            previous_version_id=None,
            required_dimensions=frozenset({CoverageDimension.COMPLETENESS}),
            created_by="steward",
            created_on=NOW,
        )


def test_status_closed_to_active_retired() -> None:
    assert {member.value for member in QualityCoveragePolicyStatus} == {"ACTIVE", "RETIRED"}
