"""OQI2 `ComparisonSubjectCorrespondence` (CDD-040 §9-§13). Explicitly and
non-inferentially establishes which governed source-record lineages belong
to the same stable OQI2 comparison subject. Never fuzzy, scored, or
AI-inferred -- a bare, explicitly-governed crosswalk, structurally analogous
to a human-attested fact. Not a general Entity Resolution capability
(CDD-040 §9's firewall).

`comparison_subject_id` is a stable governed identity with no derivation
formula (CDD-040 §10) -- assigned once, by governed action, and never
re-derived. `correspondence_id` identifies exactly one immutable version of
the correspondence assertion, deterministically derived (§11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.oqi.evaluation import _length_prefixed, canonical_form
from app.domain.shared.exceptions import DomainException, ValidationException

# CDD-040 §11: fixed, frozen forever once implemented. Deliberately distinct
# from OQI1's own OQI_NAMESPACE ("urn:ctec:oqi:v1") and CDD-022's
# BOOTSTRAP_SEED_NAMESPACE, so no OQI2 identity can ever collide with an
# OQI1 or evidence identity under any adversarially-chosen input.
OQI_CROSS_SOURCE_NAMESPACE: UUID = uuid5(NAMESPACE_URL, "urn:ctec:oqi:cross-source:v1")

_MAX_TENANT_ID_LENGTH = 200
_MAX_ROLE_LENGTH = 64
_MIN_MEMBERS = 2


class OqiMalformedCorrespondenceError(DomainException):
    """CDD-040 §56: raised whenever a governed correspondence's shape is
    invalid -- at construction or at persistence/activation. Never caught to
    silently fabricate a comparison subject."""


class ComparisonSubjectCorrespondenceStatus(StrEnum):
    """CDD-040 §12: exactly these two, closed. No DRAFT."""

    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


def derive_correspondence_id(*, tenant_id: str, comparison_subject_id: UUID, version: int) -> UUID:
    """CDD-040 §11's exact deterministic correspondence identity formula."""
    material = (
        _length_prefixed("comparison_subject_correspondence")
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(canonical_form(comparison_subject_id))
        + _length_prefixed(str(version))
    )
    return uuid5(OQI_CROSS_SOURCE_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class ComparisonSubjectCorrespondenceMember:
    """CDD-040 §13: binds one stable `participant_role` to exactly one
    lineage component pair within one correspondence version. `tenant_id` is
    inherited from the correspondence header, never duplicated per member."""

    participant_role: str
    source_object_id: UUID
    source_record_reference: str

    def __post_init__(self) -> None:
        if not isinstance(self.participant_role, str) or not (
            1 <= len(self.participant_role) <= _MAX_ROLE_LENGTH
        ):
            raise ValidationException(
                f"participant_role must be non-empty text of length <= {_MAX_ROLE_LENGTH}"
            )
        if not isinstance(self.source_object_id, UUID):
            raise ValidationException("source_object_id must be a UUID")
        if (
            not isinstance(self.source_record_reference, str)
            or not self.source_record_reference.strip()
        ):
            raise ValidationException("source_record_reference must be non-empty text")


@dataclass(frozen=True, slots=True)
class ComparisonSubjectCorrespondence:
    correspondence_id: UUID
    comparison_subject_id: UUID
    tenant_id: str
    version: int
    status: ComparisonSubjectCorrespondenceStatus
    members: tuple[ComparisonSubjectCorrespondenceMember, ...]
    created_by: str
    created_on: datetime
    retired_on: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.correspondence_id, UUID):
            raise ValidationException("correspondence_id must be a UUID")
        if not isinstance(self.comparison_subject_id, UUID):
            raise ValidationException("comparison_subject_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException(
                f"tenant_id must be non-empty text of length <= {_MAX_TENANT_ID_LENGTH}"
            )
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValidationException("version must be a positive integer")
        if not isinstance(self.status, ComparisonSubjectCorrespondenceStatus):
            raise ValidationException("status must be a ComparisonSubjectCorrespondenceStatus")
        if not isinstance(self.created_by, str) or not self.created_by.strip():
            raise ValidationException("created_by must be non-blank text")
        if self.created_on is None or self.created_on.tzinfo is None:
            raise ValidationException("created_on must include a timezone")
        if (
            self.status is ComparisonSubjectCorrespondenceStatus.ACTIVE
            and self.retired_on is not None
        ):
            raise ValidationException("ACTIVE correspondences must not carry retired_on")
        if self.status is ComparisonSubjectCorrespondenceStatus.RETIRED and self.retired_on is None:
            raise ValidationException("RETIRED correspondences must carry retired_on")
        if self.retired_on is not None and self.retired_on.tzinfo is None:
            raise ValidationException("retired_on must include a timezone")

        # CDD-040 §56: >= 2 members, unique roles, unique lineage.
        if not isinstance(self.members, tuple) or len(self.members) < _MIN_MEMBERS:
            raise OqiMalformedCorrespondenceError(
                f"correspondence must have at least {_MIN_MEMBERS} members"
            )
        if not all(
            isinstance(member, ComparisonSubjectCorrespondenceMember) for member in self.members
        ):
            raise OqiMalformedCorrespondenceError(
                "members must be ComparisonSubjectCorrespondenceMember instances"
            )
        roles = [member.participant_role for member in self.members]
        if len(set(roles)) != len(roles):
            raise OqiMalformedCorrespondenceError(
                "participant_role must be unique within a version"
            )
        lineages = [
            (member.source_object_id, member.source_record_reference) for member in self.members
        ]
        if len(set(lineages)) != len(lineages):
            raise OqiMalformedCorrespondenceError(
                "the same lineage must not be bound to two conflicting roles"
            )

        expected_id = derive_correspondence_id(
            tenant_id=self.tenant_id,
            comparison_subject_id=self.comparison_subject_id,
            version=self.version,
        )
        if self.correspondence_id != expected_id:
            raise ValidationException(
                "correspondence_id is inconsistent with its own governed semantic identity inputs"
            )

    @classmethod
    def new(
        cls,
        *,
        comparison_subject_id: UUID,
        tenant_id: str,
        version: int,
        status: ComparisonSubjectCorrespondenceStatus,
        members: tuple[ComparisonSubjectCorrespondenceMember, ...],
        created_by: str,
        created_on: datetime,
        retired_on: datetime | None = None,
    ) -> ComparisonSubjectCorrespondence:
        correspondence_id = derive_correspondence_id(
            tenant_id=tenant_id, comparison_subject_id=comparison_subject_id, version=version
        )
        return cls(
            correspondence_id=correspondence_id,
            comparison_subject_id=comparison_subject_id,
            tenant_id=tenant_id,
            version=version,
            status=status,
            members=members,
            created_by=created_by,
            created_on=created_on,
            retired_on=retired_on,
        )
