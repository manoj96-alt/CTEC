"""OQI5-I1 `RemediationCase` (CDD-043 Sec11): one stable, per-Finding
aggregate persisting the deterministic remediation lifecycle across
reopens -- mirroring how one stable `BusinessRuleFinding`/`QualityFinding`
persists across its own reopen cycle. `case_id` is deterministic from the
Finding's own stable identity (`tenant_id + finding_family + finding_id`),
never regenerated across reopens, so re-extracting candidates for a
reopened Finding reuses the same case row rather than creating a new one."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5

from app.domain.oqi.evaluation import _length_prefixed, canonical_form
from app.domain.oqi.quality_rule import OQI_NAMESPACE
from app.domain.shared.exceptions import ValidationException

_CASE_IDENTITY_ALGORITHM_VERSION = "OQI_REMEDIATION_CASE_IDENTITY_V1"
_MAX_FINDING_ID_TEXT_LENGTH = 200


class FindingFamily(StrEnum):
    """CDD-043 Sec11: closed, exactly these three. OQI5-I1 has no
    "unknown family" branch -- an unsupported family must fail closed at
    the caller, never silently be treated as a valid remediation source."""

    OQI1 = "OQI1"
    OQI2 = "OQI2"
    OQI3 = "OQI3"


class RemediationCaseStatus(StrEnum):
    """CDD-043 Sec11: closed, exactly these eight. Longest value
    `EXTERNAL_EXECUTION_REPORTED` = 25 chars, `String(32)` safe (Artifact
    Authorization Sec7)."""

    CANDIDATE_READY = "CANDIDATE_READY"
    AWAITING_AUTHORITY = "AWAITING_AUTHORITY"
    AUTHORIZED = "AUTHORIZED"
    EXTERNAL_EXECUTION_REPORTED = "EXTERNAL_EXECUTION_REPORTED"
    AWAITING_REEVALUATION = "AWAITING_REEVALUATION"
    RESOLVED = "RESOLVED"
    STEWARD_INVESTIGATION = "STEWARD_INVESTIGATION"
    NO_REMEDIATION = "NO_REMEDIATION"


def derive_remediation_case_id(
    *, tenant_id: str, finding_family: FindingFamily, finding_id: UUID
) -> UUID:
    """CDD-043 Sec11: deterministic from the Finding's own stable
    identity alone -- excludes state_revision, candidate set, and every
    other volatile fact, so the same Finding always resolves to the same
    case_id regardless of how many times it is reopened or re-evaluated."""
    material = (
        _length_prefixed(_CASE_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(finding_family.value)
        + _length_prefixed(str(finding_id))
    )
    return uuid5(OQI_NAMESPACE, material)


@dataclass(frozen=True, slots=True)
class RemediationCase:
    case_id: UUID
    tenant_id: str
    finding_family: FindingFamily
    finding_id: UUID
    status: RemediationCaseStatus
    external_execution_claimed: bool
    external_execution_claimed_on: datetime | None
    created_on: datetime
    updated_on: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, UUID):
            raise ValidationException("case_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValidationException("tenant_id must be non-blank text")
        if not isinstance(self.finding_family, FindingFamily):
            raise ValidationException("finding_family must be a FindingFamily")
        if not isinstance(self.finding_id, UUID):
            raise ValidationException("finding_id must be a UUID")
        if not isinstance(self.status, RemediationCaseStatus):
            raise ValidationException("status must be a RemediationCaseStatus")
        if not isinstance(self.external_execution_claimed, bool):
            raise ValidationException("external_execution_claimed must be an explicit bool")
        if self.external_execution_claimed and self.external_execution_claimed_on is None:
            raise ValidationException(
                "external_execution_claimed_on is required when claimed is True"
            )
        for label, value in (
            ("external_execution_claimed_on", self.external_execution_claimed_on),
            ("created_on", self.created_on),
            ("updated_on", self.updated_on),
        ):
            if value is not None and value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")
        if self.created_on is None:
            raise ValidationException("created_on is required")
        if self.updated_on is None:
            raise ValidationException("updated_on is required")

        expected_id = derive_remediation_case_id(
            tenant_id=self.tenant_id,
            finding_family=self.finding_family,
            finding_id=self.finding_id,
        )
        if self.case_id != expected_id:
            raise ValidationException(
                "case_id is inconsistent with its own governed semantic identity inputs"
            )


def open_or_reuse_case(
    *,
    existing: RemediationCase | None,
    tenant_id: str,
    finding_family: FindingFamily,
    finding_id: UUID,
    status: RemediationCaseStatus,
    now: datetime,
) -> RemediationCase:
    """CDD-043 Sec11: creates a new case only if none exists for this
    Finding's stable identity; otherwise reuses the existing case_id and
    updates only `status`/`updated_on` -- a reopened Finding never gets a
    new case. Does not touch `external_execution_claimed*` (a separate,
    narrower transition -- see `record_external_execution_claim`)."""
    case_id = derive_remediation_case_id(
        tenant_id=tenant_id, finding_family=finding_family, finding_id=finding_id
    )
    if existing is not None:
        if existing.case_id != case_id:
            raise ValidationException(
                "existing RemediationCase identity does not match the supplied identity arguments"
            )
        return replace(existing, status=status, updated_on=now)
    return RemediationCase(
        case_id=case_id,
        tenant_id=tenant_id,
        finding_family=finding_family,
        finding_id=finding_id,
        status=status,
        external_execution_claimed=False,
        external_execution_claimed_on=None,
        created_on=now,
        updated_on=now,
    )


def record_external_execution_claim(*, case: RemediationCase, now: datetime) -> RemediationCase:
    """CDD-043 Sec16: a human-reported claim only -- never itself a
    resolution. Sets `status=EXTERNAL_EXECUTION_REPORTED`, distinct from
    `RESOLVED`, which only a subsequent, independent case-status refresh
    against the Finding's own re-evaluated state may set (Sec17)."""
    return replace(
        case,
        status=RemediationCaseStatus.EXTERNAL_EXECUTION_REPORTED,
        external_execution_claimed=True,
        external_execution_claimed_on=now,
        updated_on=now,
    )


def refresh_case_status_from_finding(
    *, case: RemediationCase, finding_status_is_resolved: bool, now: datetime
) -> RemediationCase:
    """CDD-043 Sec17: `RemediationCase.status` transitions to `RESOLVED`
    only as a read-only reflection of the Finding's own resolved state,
    read fresh from the existing, unmodified OQI evaluator's own Finding
    row -- this function asserts nothing about resolution independently;
    it merely mirrors what the caller already determined by re-reading the
    Finding. If the Finding is not resolved, the case remains at whatever
    status it already carries (e.g. `AWAITING_REEVALUATION`)."""
    if finding_status_is_resolved and case.status is not RemediationCaseStatus.RESOLVED:
        return replace(case, status=RemediationCaseStatus.RESOLVED, updated_on=now)
    return case
