"""OQI-H2 `OqiReferenceEvidenceConflict` (CDD-048 §16): the governance
condition raised when two or more qualifying (ACTIVE) `ReferenceEvidence
Assertion` rows for the same governed subject disagree on the asserted
value. Explicitly NOT a Quality Finding -- it carries no `QualityFindingOrigin`,
no `FindingStorageFamily`, no `QualityDimension`, and must never be labeled
`REFERENCE_VALUE_UNSUPPORTED` (that would misrepresent "Noetva currently
lacks a defensible reference basis" as "this specific observed value is
wrong," a materially different and unsupported claim, CDD-048 §16).

Persisted, mutable current-state (`ACTIVE`/`RESOLVED`), mirroring
`CurrentOntologyImpact`'s lifecycle pattern -- a steward needs a stable,
followable governance item, not a value recomputed fresh on every query.
Resolution requires a genuine governed change: one of the conflicting
assertions superseded by a new version that removes the disagreement, or
explicit retirement of one of them by the authority that owns its form.
There is no "pick one" action."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.oqi.evaluation import _length_prefixed, canonical_form
from app.domain.oqi_ontology_impact.evaluation import OntologyElementType
from app.domain.shared.exceptions import ValidationException

_MAX_TENANT_ID_LENGTH = 200


class ReferenceEvidenceConflictStatus(StrEnum):
    """CDD-048 §16: closed, exactly these two."""

    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


def derive_reference_evidence_conflict_id(
    *,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    source_field_id: UUID,
    conflicting_assertion_ids: tuple[UUID, ...],
) -> UUID:
    """CDD-048 §16: deterministic uuid5 over tenant + subject + the sorted
    conflicting assertion ids -- row-return order never affects identity."""
    sorted_ids = tuple(sorted(conflicting_assertion_ids, key=canonical_form))
    material = (
        _length_prefixed("OQI_REFERENCE_EVIDENCE_CONFLICT_IDENTITY_V1")
        + _length_prefixed(canonical_form(tenant_id))
        + _length_prefixed(ontology_element_type.value)
        + _length_prefixed(canonical_form(ontology_element_id))
        + _length_prefixed(canonical_form(source_field_id))
        + _length_prefixed(str(len(sorted_ids)))
        + "".join(_length_prefixed(canonical_form(assertion_id)) for assertion_id in sorted_ids)
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    # Reuse the OQI reference-evidence namespace indirectly via uuid5 over
    # the digest -- avoids importing a namespace constant this module has no
    # other reason to depend on, while remaining fully deterministic.
    from uuid import NAMESPACE_URL, uuid5

    return uuid5(NAMESPACE_URL, f"urn:ctec:oqi:reference-evidence-conflict:v1:{digest}")


@dataclass(frozen=True, slots=True)
class OqiReferenceEvidenceConflict:
    conflict_id: UUID
    tenant_id: str
    ontology_element_type: OntologyElementType
    ontology_element_id: UUID
    source_field_id: UUID
    conflicting_assertion_ids: tuple[UUID, ...]
    status: ReferenceEvidenceConflictStatus
    first_detected_at: datetime
    last_observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.conflict_id, UUID):
            raise ValidationException("conflict_id must be a UUID")
        if not isinstance(self.tenant_id, str) or not (
            1 <= len(self.tenant_id) <= _MAX_TENANT_ID_LENGTH
        ):
            raise ValidationException("tenant_id must be non-empty bounded text")
        if not isinstance(self.ontology_element_type, OntologyElementType):
            raise ValidationException("ontology_element_type must be an OntologyElementType")
        if not isinstance(self.ontology_element_id, UUID):
            raise ValidationException("ontology_element_id must be a UUID")
        if not isinstance(self.source_field_id, UUID):
            raise ValidationException("source_field_id must be a UUID")
        if not isinstance(self.conflicting_assertion_ids, tuple) or not all(
            isinstance(assertion_id, UUID) for assertion_id in self.conflicting_assertion_ids
        ):
            raise ValidationException("conflicting_assertion_ids must be a tuple of UUIDs")
        if len(self.conflicting_assertion_ids) < 2:
            raise ValidationException(
                "a conflict requires at least two disagreeing qualifying assertions"
            )
        if len(set(self.conflicting_assertion_ids)) != len(self.conflicting_assertion_ids):
            raise ValidationException("conflicting_assertion_ids must not contain duplicates")
        if not isinstance(self.status, ReferenceEvidenceConflictStatus):
            raise ValidationException("status must be a ReferenceEvidenceConflictStatus")
        for label, value in (
            ("first_detected_at", self.first_detected_at),
            ("last_observed_at", self.last_observed_at),
        ):
            if value is None or value.tzinfo is None:
                raise ValidationException(f"{label} must include a timezone")

        expected_id = derive_reference_evidence_conflict_id(
            tenant_id=self.tenant_id,
            ontology_element_type=self.ontology_element_type,
            ontology_element_id=self.ontology_element_id,
            source_field_id=self.source_field_id,
            conflicting_assertion_ids=self.conflicting_assertion_ids,
        )
        if self.conflict_id != expected_id:
            raise ValidationException(
                "conflict_id is inconsistent with its own governed semantic identity inputs"
            )


def open_or_touch_conflict(
    *,
    existing: OqiReferenceEvidenceConflict | None,
    tenant_id: str,
    ontology_element_type: OntologyElementType,
    ontology_element_id: UUID,
    source_field_id: UUID,
    conflicting_assertion_ids: tuple[UUID, ...],
    now: datetime,
) -> OqiReferenceEvidenceConflict:
    """CDD-048 §16: creates a new conflict row only if none exists for this
    exact set of disagreeing assertions; otherwise reuses the existing
    `conflict_id` and updates only `last_observed_at` (and reopens to
    `ACTIVE` if it had been marked `RESOLVED` but the same disagreement is
    still detected -- a governed change must have failed to actually remove
    it). Never invents a precedence between the conflicting assertions."""
    conflict_id = derive_reference_evidence_conflict_id(
        tenant_id=tenant_id,
        ontology_element_type=ontology_element_type,
        ontology_element_id=ontology_element_id,
        source_field_id=source_field_id,
        conflicting_assertion_ids=conflicting_assertion_ids,
    )
    if existing is not None:
        if existing.conflict_id != conflict_id:
            raise ValidationException(
                "existing conflict identity does not match the supplied identity arguments"
            )
        return replace(
            existing, status=ReferenceEvidenceConflictStatus.ACTIVE, last_observed_at=now
        )
    return OqiReferenceEvidenceConflict(
        conflict_id=conflict_id,
        tenant_id=tenant_id,
        ontology_element_type=ontology_element_type,
        ontology_element_id=ontology_element_id,
        source_field_id=source_field_id,
        conflicting_assertion_ids=conflicting_assertion_ids,
        status=ReferenceEvidenceConflictStatus.ACTIVE,
        first_detected_at=now,
        last_observed_at=now,
    )


def resolve_conflict(
    *, existing: OqiReferenceEvidenceConflict, now: datetime
) -> OqiReferenceEvidenceConflict:
    """CDD-048 §16: marks a conflict `RESOLVED`. Callers MUST only invoke
    this after confirming, via a fresh re-derivation, that the disagreement
    genuinely no longer exists among the currently-ACTIVE qualifying
    assertions for this subject -- this function itself performs no such
    check; it is a pure state transition."""
    return replace(existing, status=ReferenceEvidenceConflictStatus.RESOLVED, last_observed_at=now)
