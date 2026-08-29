"""Pure domain unit tests for `app.domain.oqi_cross_source.correspondence`
(CDD-040 §9-§13, §56)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
    OqiMalformedCorrespondenceError,
    derive_correspondence_id,
)
from app.domain.shared.exceptions import ValidationException

NOW = datetime.now(UTC)


def _members(
    *, roles: tuple[str, ...] = ("SAP", "PLM")
) -> tuple[ComparisonSubjectCorrespondenceMember, ...]:
    return tuple(
        ComparisonSubjectCorrespondenceMember(
            participant_role=role,
            source_object_id=uuid4(),
            source_record_reference=f"REF-{role}",
        )
        for role in roles
    )


def _correspondence(
    *,
    comparison_subject_id: UUID | None = None,
    tenant_id: str = "tenant-a",
    version: int = 1,
    status: ComparisonSubjectCorrespondenceStatus = ComparisonSubjectCorrespondenceStatus.ACTIVE,
    members: tuple[ComparisonSubjectCorrespondenceMember, ...] | None = None,
    retired_on: datetime | None = None,
) -> ComparisonSubjectCorrespondence:
    return ComparisonSubjectCorrespondence.new(
        comparison_subject_id=comparison_subject_id or uuid4(),
        tenant_id=tenant_id,
        version=version,
        status=status,
        members=members if members is not None else _members(),
        created_by="steward",
        created_on=NOW,
        retired_on=retired_on,
    )


# --- identity determinism ---


def test_correspondence_id_is_deterministic() -> None:
    subject_id = uuid4()
    a = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=subject_id, version=1)
    b = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=subject_id, version=1)
    assert a == b


def test_correspondence_id_differs_by_version() -> None:
    subject_id = uuid4()
    a = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=subject_id, version=1)
    b = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=subject_id, version=2)
    assert a != b


def test_correspondence_id_differs_by_subject() -> None:
    a = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=uuid4(), version=1)
    b = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=uuid4(), version=1)
    assert a != b


def test_correspondence_id_differs_by_tenant() -> None:
    subject_id = uuid4()
    a = derive_correspondence_id(tenant_id="tenant-a", comparison_subject_id=subject_id, version=1)
    b = derive_correspondence_id(tenant_id="tenant-b", comparison_subject_id=subject_id, version=1)
    assert a != b


def test_new_correspondence_has_consistent_id() -> None:
    subject_id = uuid4()
    correspondence = _correspondence(comparison_subject_id=subject_id, version=1)
    assert correspondence.correspondence_id == derive_correspondence_id(
        tenant_id="tenant-a", comparison_subject_id=subject_id, version=1
    )


def test_rehydrated_correspondence_with_wrong_id_is_rejected() -> None:
    with pytest.raises(ValidationException):
        ComparisonSubjectCorrespondence(
            correspondence_id=derive_correspondence_id(
                tenant_id="tenant-a", comparison_subject_id=uuid4(), version=1
            ),
            comparison_subject_id=uuid4(),  # a different, unrelated subject
            tenant_id="tenant-a",
            version=1,
            status=ComparisonSubjectCorrespondenceStatus.ACTIVE,
            members=_members(),
            created_by="steward",
            created_on=NOW,
        )


# --- member shape validation (CDD-040 §56) ---


def test_requires_at_least_two_members() -> None:
    with pytest.raises(OqiMalformedCorrespondenceError):
        _correspondence(members=_members(roles=("SAP",)))


def test_rejects_duplicate_role() -> None:
    duplicate_role_members = (
        ComparisonSubjectCorrespondenceMember(
            participant_role="SAP", source_object_id=uuid4(), source_record_reference="R1"
        ),
        ComparisonSubjectCorrespondenceMember(
            participant_role="SAP", source_object_id=uuid4(), source_record_reference="R2"
        ),
    )
    with pytest.raises(OqiMalformedCorrespondenceError):
        _correspondence(members=duplicate_role_members)


def test_rejects_same_lineage_bound_to_two_roles() -> None:
    shared_object_id = uuid4()
    conflicting_members = (
        ComparisonSubjectCorrespondenceMember(
            participant_role="SAP",
            source_object_id=shared_object_id,
            source_record_reference="MAT-100",
        ),
        ComparisonSubjectCorrespondenceMember(
            participant_role="PLM",
            source_object_id=shared_object_id,
            source_record_reference="MAT-100",
        ),
    )
    with pytest.raises(OqiMalformedCorrespondenceError):
        _correspondence(members=conflicting_members)


# --- lifecycle ---


def test_active_correspondence_must_not_carry_retired_on() -> None:
    with pytest.raises(ValidationException):
        _correspondence(status=ComparisonSubjectCorrespondenceStatus.ACTIVE, retired_on=NOW)


def test_retired_correspondence_must_carry_retired_on() -> None:
    with pytest.raises(ValidationException):
        _correspondence(status=ComparisonSubjectCorrespondenceStatus.RETIRED, retired_on=None)


def test_retired_correspondence_with_retired_on_is_valid() -> None:
    correspondence = _correspondence(
        status=ComparisonSubjectCorrespondenceStatus.RETIRED, retired_on=NOW
    )
    assert correspondence.status is ComparisonSubjectCorrespondenceStatus.RETIRED
