from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.shared.exceptions import ValidationException


class ResolutionOutcome(StrEnum):
    RESOLVED = "Resolved"
    POSSIBLE = "Possible Resolution"
    UNRESOLVED = "Unresolved"
    # Two or more corroborating representations disagree on a strong,
    # governed identifier (or a known parent/subsidiary distinction), so
    # automatic and steward resolution are both withheld until the conflict
    # is investigated. Added in ERM 3A; the value is a new string, so it is
    # additive to the existing `outcome` column (String(32), no CHECK
    # constraint) and does not alter the meaning of RESOLVED/POSSIBLE/
    # UNRESOLVED for any existing record.
    BLOCKED_CONFLICT = "Blocked Conflict"


class BusinessConfidence(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class StewardDecisionAction(StrEnum):
    """The fixed, exhaustive set of human steward actions on a resolution
    case (Increment 3A Gate C). Not a general workflow/state-machine
    vocabulary -- exactly the four actions the product supports, each with
    fixed outcome semantics enforced by
    EvidenceResolutionEngine.decide_steward_action()."""

    CONFIRM_MATCH = "confirm_match"
    REJECT_MATCH = "reject_match"
    MARK_UNRESOLVED = "mark_unresolved"
    BLOCK_CONFLICT = "block_conflict"


@dataclass(frozen=True, slots=True)
class ResolutionCandidate:
    enterprise_entity_id: UUID
    internal_score: float
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.internal_score <= 1:
            raise ValidationException("Internal candidate score must be between 0 and 1")
        if not self.reasons:
            raise ValidationException("Candidate evaluation requires at least one reason")


class EvidenceType(StrEnum):
    """Multi-attribute evidence categories evaluated for a resolution case.

    Categories intentionally omitted from this MVP subset (shared contracts,
    supplied materials, shared facilities) have no governed persisted source
    in the current schema; SOURCE_SYSTEM_PROVENANCE is the supporting-
    evidence signal that is actually computable today.
    """

    STRONG_IDENTIFIER_LEI = "Strong Identifier: LEI"
    STRONG_IDENTIFIER_EXTERNAL_ID = "Strong Identifier: External ID (DUNS or equivalent)"
    STRONG_IDENTIFIER_TAX_REGISTRATION = "Strong Identifier: Tax/Business Registration"
    SOURCE_SYSTEM_CROSSWALK = "Trusted Source-System Crosswalk"
    DOMAIN_VERIFIED = "Verified Website Domain"
    EMAIL_DOMAIN_VERIFIED = "Verified Business Email Domain"
    COUNTRY_MATCH = "Country"
    REGISTERED_ADDRESS_MATCH = "Normalized Registered Address"
    POSTAL_CODE_MATCH = "Postal Code"
    LEGAL_NAME_MATCH = "Legal Name"
    TRADING_NAME_MATCH = "Trading Name"
    ALIAS_MATCH = "Approved Alias"
    ACRONYM_MATCH = "Acronym Alignment"
    LEGAL_SUFFIX_NORMALIZED = "Legal Suffix Normalized"
    PARENT_SUBSIDIARY_DISTINCTION = "Parent/Subsidiary/Branch Distinction"
    SOURCE_SYSTEM_PROVENANCE = "Source-System Provenance"


class EvidenceClassification(StrEnum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    MISSING = "Missing"
    VETO = "Veto"


# Evidence types that, alone, must never be sufficient to auto-resolve
# (Required safety rules 1 and 2). This is a hard invariant of the engine,
# not something a customer policy can relax.
NAME_ONLY_EVIDENCE_TYPES = frozenset(
    {
        EvidenceType.LEGAL_NAME_MATCH,
        EvidenceType.TRADING_NAME_MATCH,
        EvidenceType.ALIAS_MATCH,
        EvidenceType.LEGAL_SUFFIX_NORMALIZED,
    }
)
ACRONYM_ONLY_EVIDENCE_TYPES = frozenset({EvidenceType.ACRONYM_MATCH})
STRONG_IDENTIFIER_EVIDENCE_TYPES = frozenset(
    {
        EvidenceType.STRONG_IDENTIFIER_LEI,
        EvidenceType.STRONG_IDENTIFIER_EXTERNAL_ID,
        EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION,
        EvidenceType.SOURCE_SYSTEM_CROSSWALK,
    }
)
# Evidence types masked/fingerprinted before display or persistence rather
# than shown as a raw value (never sensitive banking material in this MVP
# subset, but tax/business-registration identifiers are treated as
# controlled values per the increment's sensitive-data rule).
SENSITIVE_EVIDENCE_TYPES = frozenset({EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION})


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    evidence_type: EvidenceType
    compared_attributes: tuple[str, ...]
    normalized_values: tuple[str, ...]
    classification: EvidenceClassification
    contribution: float
    explanation: str
    provenance: str

    def __post_init__(self) -> None:
        if not self.compared_attributes:
            raise ValidationException("Evidence item requires at least one compared attribute")
        if not -1.0 <= self.contribution <= 1.0:
            raise ValidationException("Evidence contribution must be between -1 and 1")
        if self.classification is EvidenceClassification.MISSING and self.contribution != 0.0:
            raise ValidationException("Missing evidence must not contribute a nonzero score")
        if not self.explanation.strip():
            raise ValidationException("Evidence item requires an explanation")
        if not self.provenance.strip():
            raise ValidationException("Evidence item requires provenance")


@dataclass(frozen=True, slots=True)
class EvidenceProfile:
    """The full, honest evidence breakdown for one resolution case: what was
    compared, what matched, what conflicted, and what was never populated."""

    items: tuple[EvidenceItem, ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise ValidationException("Evidence profile requires at least one evidence item")

    @property
    def positive_items(self) -> tuple[EvidenceItem, ...]:
        return tuple(i for i in self.items if i.classification is EvidenceClassification.POSITIVE)

    @property
    def negative_items(self) -> tuple[EvidenceItem, ...]:
        return tuple(i for i in self.items if i.classification is EvidenceClassification.NEGATIVE)

    @property
    def missing_items(self) -> tuple[EvidenceItem, ...]:
        return tuple(i for i in self.items if i.classification is EvidenceClassification.MISSING)

    @property
    def veto_items(self) -> tuple[EvidenceItem, ...]:
        return tuple(i for i in self.items if i.classification is EvidenceClassification.VETO)

    def as_record(self) -> dict[str, object]:
        return {
            "items": [
                {
                    "evidence_type": item.evidence_type.value,
                    "compared_attributes": list(item.compared_attributes),
                    "normalized_values": list(item.normalized_values),
                    "classification": item.classification.value,
                    "contribution": item.contribution,
                    "explanation": item.explanation,
                    "provenance": item.provenance,
                }
                for item in self.items
            ]
        }

    @staticmethod
    def from_record(data: dict[str, object]) -> "EvidenceProfile":
        """Inverse of as_record(): reconstructs the domain object from the
        exact JSON shape persisted on
        EnterpriseEntityResolutionRecordModel.evidence_profile. Used by
        Gate C to re-decide against an already-computed profile without
        ever re-deriving it from raw source representations (which are
        never persisted)."""
        raw_items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(raw_items, list):
            raise ValidationException("Evidence profile record must be a dict with an items list")
        try:
            items = tuple(
                EvidenceItem(
                    evidence_type=EvidenceType(raw["evidence_type"]),
                    compared_attributes=tuple(raw["compared_attributes"]),
                    normalized_values=tuple(raw["normalized_values"]),
                    classification=EvidenceClassification(raw["classification"]),
                    contribution=float(raw["contribution"]),
                    explanation=raw["explanation"],
                    provenance=raw["provenance"],
                )
                for raw in raw_items
            )
        except (KeyError, ValueError, TypeError) as error:
            raise ValidationException(f"Malformed evidence profile record: {error}") from error
        return EvidenceProfile(items=items)


@dataclass(frozen=True, slots=True)
class EnterpriseEntityResolutionRecord:
    record_id: UUID
    tenant_id: str
    enterprise_entity_id: UUID | None
    supporting_source_object_ids: tuple[UUID, ...]
    outcome: ResolutionOutcome
    business_confidence: BusinessConfidence
    structured_reasons: tuple[str, ...]
    narrative_explanation: str
    produced_at: datetime
    policy_version: str
    evidence_profile: EvidenceProfile | None = None
    policy_id: UUID | None = None
    actor_id: str | None = None
    decision_rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.tenant_id.strip():
            raise ValidationException("Tenant ID is required")
        if not self.supporting_source_object_ids:
            raise ValidationException("At least one supporting Source Object is required")
        if len(set(self.supporting_source_object_ids)) != len(self.supporting_source_object_ids):
            raise ValidationException("Supporting Source Objects must be unique")
        entity_free_outcomes = (ResolutionOutcome.UNRESOLVED, ResolutionOutcome.BLOCKED_CONFLICT)
        if self.outcome in entity_free_outcomes and self.enterprise_entity_id is not None:
            raise ValidationException(
                "Unresolved and Blocked Conflict records cannot reference an Enterprise Entity"
            )
        # Only RESOLVED strictly requires an Enterprise Entity reference.
        # POSSIBLE may carry one (the automatic engine always ties a
        # POSSIBLE candidate to a specific entity -- see
        # EvidenceResolutionEngine.resolve()'s own, stricter requirement for
        # that path) or may not (a steward's reject_match decision -- Gate
        # C -- clears the candidate while the case remains POSSIBLE: there
        # is no ranked "next candidate" in the multi-attribute evidence
        # model to fall back to).
        if self.outcome is ResolutionOutcome.RESOLVED and self.enterprise_entity_id is None:
            raise ValidationException("Resolved outcomes require an Enterprise Entity reference")
        if not self.structured_reasons or not self.narrative_explanation.strip():
            raise ValidationException("Structured reasons and narrative explanation are required")
        if self.produced_at.tzinfo is None:
            raise ValidationException("Produced timestamp must include a timezone")
        if not self.policy_version.strip():
            raise ValidationException("Resolution Policy Version is required")
        if self.actor_id is not None and not self.actor_id.strip():
            raise ValidationException("Actor ID must not be blank when provided")
        if self.decision_rationale is not None and not self.decision_rationale.strip():
            raise ValidationException("Decision rationale must not be blank when provided")
