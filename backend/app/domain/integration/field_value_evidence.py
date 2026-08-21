"""Domain model for governed Source Field-Value Evidence (CDD-022 §6-§12,
§25; Field-Value Evidence Artifact Authorization). An immutable, append-only
fact recording a raw observed representation for an already-governed
`SourceField` (CDD-019, unmodified). Deterministic identity is
domain-owned: every `FieldValueEvidence` -- newly constructed via `new()` or
rehydrated from persistence via the constructor directly -- has its
`field_value_evidence_id` verified against the same governed derivation
from its own four semantic identity inputs (`source_field_id`,
`source_record_reference`, `observed_representation`, `observed_at`); a
mismatch fails explicitly rather than silently constructing an inconsistent
fact. `received_at` and `evidence_reference` never participate in identity.
Canonicalization is a length-prefixed, self-delimiting encoding (UTF-8 byte
length, never Python character count) under a fixed algorithm-version
marker -- collision-safe for arbitrary raw source representations, unlike
the naive delimiter-joined convention used by other seeders in this
repository (Artifact Authorization §7)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid5

from app.core.bootstrap import BOOTSTRAP_SEED_NAMESPACE
from app.domain.shared.exceptions import ValidationException
from app.domain.shared.value_objects import Identifier

_IDENTITY_ALGORITHM_VERSION = "FIELD_VALUE_EVIDENCE_IDENTITY_V1"


def _length_prefixed(value: str) -> str:
    if not isinstance(value, str):
        raise ValidationException("Field Value Evidence identity component must be text")
    return f"{len(value.encode('utf-8'))}:{value}"


def derive_field_value_evidence_id(
    *,
    source_field_id: UUID,
    source_record_reference: str,
    observed_representation: str,
    observed_at: datetime,
) -> UUID:
    """CDD-022 §6, Artifact Authorization §7: the sole authorized
    deterministic-identity derivation for `FieldValueEvidence`. Exactly
    these four semantic identity inputs -- `received_at` and
    `evidence_reference` never participate. Each component is canonicalized
    to a length-prefixed, self-delimiting segment (UTF-8 byte length, never
    Python character count) before concatenation, making the encoding
    uniquely decodable regardless of delimiter characters occurring inside
    any raw component."""
    canonical_material = (
        _length_prefixed(_IDENTITY_ALGORITHM_VERSION)
        + _length_prefixed(str(source_field_id))
        + _length_prefixed(source_record_reference)
        + _length_prefixed(observed_representation)
        + _length_prefixed(observed_at.astimezone(UTC).isoformat())
    )
    return uuid5(BOOTSTRAP_SEED_NAMESPACE, canonical_material)


@dataclass(frozen=True, slots=True)
class FieldValueEvidence:
    field_value_evidence_id: Identifier
    source_field_id: Identifier
    source_record_reference: str
    observed_representation: str
    observed_at: datetime
    received_at: datetime
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        for field_name, identifier_value in (
            ("Field Value Evidence ID", self.field_value_evidence_id),
            ("Source Field", self.source_field_id),
        ):
            if not isinstance(identifier_value, Identifier):
                raise ValidationException(f"{field_name} must be an Identifier")
        if (
            not isinstance(self.source_record_reference, str)
            or not self.source_record_reference.strip()
        ):
            raise ValidationException("Source Record Reference must be non-empty text")
        if not isinstance(self.observed_representation, str):
            raise ValidationException("Observed Representation must be text")
        if self.evidence_reference is not None and not isinstance(self.evidence_reference, str):
            raise ValidationException("Evidence Reference must be text or None")
        for field_name, date_value in (
            ("Observed At", self.observed_at),
            ("Received At", self.received_at),
        ):
            if not isinstance(date_value, datetime) or date_value.tzinfo is None:
                raise ValidationException(f"{field_name} must be a timezone-aware datetime")

        expected_id = derive_field_value_evidence_id(
            source_field_id=self.source_field_id.value,
            source_record_reference=self.source_record_reference,
            observed_representation=self.observed_representation,
            observed_at=self.observed_at,
        )
        if self.field_value_evidence_id.value != expected_id:
            raise ValidationException(
                "Field Value Evidence ID is inconsistent with its own governed semantic "
                "identity inputs"
            )

    @classmethod
    def new(
        cls,
        *,
        source_field_id: Identifier,
        source_record_reference: str,
        observed_representation: str,
        observed_at: datetime,
        received_at: datetime,
        evidence_reference: str | None = None,
    ) -> FieldValueEvidence:
        """Domain-owned construction for a fresh fact: derives
        `field_value_evidence_id` internally so callers never compute their
        own identity (CDD-022 §25, Artifact Authorization §7-§8)."""
        derived_id = derive_field_value_evidence_id(
            source_field_id=source_field_id.value,
            source_record_reference=source_record_reference,
            observed_representation=observed_representation,
            observed_at=observed_at,
        )
        return cls(
            field_value_evidence_id=Identifier(derived_id),
            source_field_id=source_field_id,
            source_record_reference=source_record_reference,
            observed_representation=observed_representation,
            observed_at=observed_at,
            received_at=received_at,
            evidence_reference=evidence_reference,
        )
