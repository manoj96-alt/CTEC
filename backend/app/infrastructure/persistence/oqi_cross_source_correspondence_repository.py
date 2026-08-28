"""Repository for OQI2 governed `ComparisonSubjectCorrespondence`
persistence (CDD-040 §12, §52). `activate_new_version` mirrors
`OqiQualityRuleRepositoryImpl.activate_new_version`'s exact retire-then-
flush-then-activate transaction ordering, so the partial unique index
(`uq_comparison_subject_correspondences_one_active`) is never transiently
violated within the same transaction."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.oqi_cross_source.correspondence import (
    ComparisonSubjectCorrespondence,
    ComparisonSubjectCorrespondenceMember,
    ComparisonSubjectCorrespondenceStatus,
)
from app.infrastructure.persistence.models.oqi_cross_source_correspondence import (
    ComparisonSubjectCorrespondenceMemberORM,
    ComparisonSubjectCorrespondenceORM,
)


class OqiCrossSourceCorrespondenceRepository(Protocol):
    def create(self, correspondence: ComparisonSubjectCorrespondence) -> None: ...

    def get_by_id(self, correspondence_id: UUID) -> ComparisonSubjectCorrespondence | None: ...

    def get_active(
        self, *, tenant_id: str, comparison_subject_id: UUID
    ) -> ComparisonSubjectCorrespondence | None: ...

    def activate_new_version(
        self, new_correspondence: ComparisonSubjectCorrespondence, *, retired_on: datetime
    ) -> None: ...


class OqiCrossSourceCorrespondenceRepositoryImpl:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, correspondence: ComparisonSubjectCorrespondence) -> None:
        self.session.add(_to_orm(correspondence))
        self.session.flush()
        for member in correspondence.members:
            self.session.add(
                ComparisonSubjectCorrespondenceMemberORM(
                    correspondence_id=correspondence.correspondence_id,
                    participant_role=member.participant_role,
                    source_object_id=member.source_object_id,
                    source_record_reference=member.source_record_reference,
                )
            )

    def get_by_id(self, correspondence_id: UUID) -> ComparisonSubjectCorrespondence | None:
        model = self.session.get(ComparisonSubjectCorrespondenceORM, correspondence_id)
        if model is None:
            return None
        return _to_domain(model, self._members_of(correspondence_id))

    def get_active(
        self, *, tenant_id: str, comparison_subject_id: UUID
    ) -> ComparisonSubjectCorrespondence | None:
        model = self.session.execute(
            select(ComparisonSubjectCorrespondenceORM).where(
                ComparisonSubjectCorrespondenceORM.tenant_id == tenant_id,
                ComparisonSubjectCorrespondenceORM.comparison_subject_id == comparison_subject_id,
                ComparisonSubjectCorrespondenceORM.status
                == ComparisonSubjectCorrespondenceStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        return _to_domain(model, self._members_of(model.correspondence_id))

    def activate_new_version(
        self, new_correspondence: ComparisonSubjectCorrespondence, *, retired_on: datetime
    ) -> None:
        if new_correspondence.status is not ComparisonSubjectCorrespondenceStatus.ACTIVE:
            raise ValueError("activate_new_version requires an ACTIVE new_correspondence")

        current = self.session.execute(
            select(ComparisonSubjectCorrespondenceORM).where(
                ComparisonSubjectCorrespondenceORM.tenant_id == new_correspondence.tenant_id,
                ComparisonSubjectCorrespondenceORM.comparison_subject_id
                == new_correspondence.comparison_subject_id,
                ComparisonSubjectCorrespondenceORM.status
                == ComparisonSubjectCorrespondenceStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()
        if current is not None:
            current.status = ComparisonSubjectCorrespondenceStatus.RETIRED.value
            current.retired_on = retired_on
            self.session.flush()

        self.create(new_correspondence)
        self.session.flush()

    def _members_of(
        self, correspondence_id: UUID
    ) -> tuple[ComparisonSubjectCorrespondenceMemberORM, ...]:
        rows = (
            self.session.execute(
                select(ComparisonSubjectCorrespondenceMemberORM).where(
                    ComparisonSubjectCorrespondenceMemberORM.correspondence_id == correspondence_id
                )
            )
            .scalars()
            .all()
        )
        return tuple(rows)


def _to_orm(correspondence: ComparisonSubjectCorrespondence) -> ComparisonSubjectCorrespondenceORM:
    return ComparisonSubjectCorrespondenceORM(
        correspondence_id=correspondence.correspondence_id,
        comparison_subject_id=correspondence.comparison_subject_id,
        tenant_id=correspondence.tenant_id,
        version=correspondence.version,
        status=correspondence.status.value,
        created_by=correspondence.created_by,
        created_on=correspondence.created_on,
        retired_on=correspondence.retired_on,
    )


def _to_domain(
    model: ComparisonSubjectCorrespondenceORM,
    member_models: tuple[ComparisonSubjectCorrespondenceMemberORM, ...],
) -> ComparisonSubjectCorrespondence:
    members = tuple(
        ComparisonSubjectCorrespondenceMember(
            participant_role=member_model.participant_role,
            source_object_id=member_model.source_object_id,
            source_record_reference=member_model.source_record_reference,
        )
        for member_model in member_models
    )
    return ComparisonSubjectCorrespondence(
        correspondence_id=model.correspondence_id,
        comparison_subject_id=model.comparison_subject_id,
        tenant_id=model.tenant_id,
        version=model.version,
        status=ComparisonSubjectCorrespondenceStatus(model.status),
        members=members,
        created_by=model.created_by,
        created_on=model.created_on,
        retired_on=model.retired_on,
    )
