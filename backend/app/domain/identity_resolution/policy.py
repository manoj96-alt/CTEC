"""Tenant-configurable Entity Resolution policy: a strictly validated,
versioned configuration for the evidence-based resolution engine
(app.domain.identity_resolution.evidence). Not a general-purpose rules
engine -- a small, fixed, concrete set of governed knobs.

Safety invariants that are NOT policy-configurable, on purpose, so ordinary
customer weighting can never disable them:
  - name-only, acronym-only, and name+acronym-only evidence never qualify a
    case for automatic resolution (enforced in evidence.py using the fixed
    NAME_ONLY_EVIDENCE_TYPES / ACRONYM_ONLY_EVIDENCE_TYPES sets);
  - a conflict between two different values of the same strong-identifier
    type is always a veto (evidence.py);
  - sensitive identifiers (SENSITIVE_EVIDENCE_TYPES) are always
    fingerprinted before they exist anywhere outside evidence.py's
    comparison step -- sensitive_value_masking exists on the policy schema
    only because the brief lists it as a policy concern to acknowledge, but
    it must always validate to True.

What IS policy-governed: thresholds, which evidence types participate at
all, per-type contribution weights, how many non-name corroborating
attributes are required, which strong-identifier types (if any) are
mandatory for auto-resolution, source-system trust weighting, and whether a
country or parent/subsidiary conflict is a hard veto or a review-forcing
signal (both always block automatic resolution; policy only chooses which
severity label applies).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.identity_resolution.model import (
    STRONG_IDENTIFIER_EVIDENCE_TYPES,
    EvidenceType,
)
from app.domain.shared.exceptions import ValidationException

ConflictSeverity = Literal["veto", "review"]

_REQUIRED_KEYS = frozenset(
    {
        "policy_name",
        "policy_version",
        "resolved_threshold",
        "possible_threshold",
        "high_confidence_threshold",
        "medium_confidence_threshold",
        "min_corroborating_attributes",
        "participating_evidence_types",
        "mandatory_auto_resolution_evidence",
        "evidence_weights",
        "source_system_trust_weights",
        "country_conflict_severity",
        "parent_subsidiary_conflict_severity",
        "sensitive_value_masking",
        "human_approval_required_for_override",
    }
)


@dataclass(frozen=True, slots=True)
class ResolutionPolicyDefinition:
    policy_name: str
    policy_version: str
    resolved_threshold: float
    possible_threshold: float
    high_confidence_threshold: float
    medium_confidence_threshold: float
    min_corroborating_attributes: int
    participating_evidence_types: tuple[EvidenceType, ...]
    mandatory_auto_resolution_evidence: tuple[EvidenceType, ...]
    evidence_weights: dict[EvidenceType, float]
    source_system_trust_weights: dict[str, float] = field(default_factory=dict)
    country_conflict_severity: ConflictSeverity = "veto"
    parent_subsidiary_conflict_severity: ConflictSeverity = "veto"
    sensitive_value_masking: bool = True
    human_approval_required_for_override: bool = True

    def __post_init__(self) -> None:
        if not self.policy_name.strip():
            raise ValidationException("Policy name is required")
        if not self.policy_version.strip():
            raise ValidationException("Policy version is required")
        for name, value in (
            ("resolved_threshold", self.resolved_threshold),
            ("possible_threshold", self.possible_threshold),
            ("high_confidence_threshold", self.high_confidence_threshold),
            ("medium_confidence_threshold", self.medium_confidence_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationException(f"{name} must be between 0 and 1")
        if not self.resolved_threshold > self.possible_threshold:
            raise ValidationException("resolved_threshold must exceed possible_threshold")
        if not self.high_confidence_threshold >= self.medium_confidence_threshold:
            raise ValidationException(
                "high_confidence_threshold must be at least medium_confidence_threshold"
            )
        if self.min_corroborating_attributes < 1:
            raise ValidationException("min_corroborating_attributes must be at least 1")
        if not self.participating_evidence_types:
            raise ValidationException("participating_evidence_types must not be empty")
        unknown_mandatory = (
            set(self.mandatory_auto_resolution_evidence) - STRONG_IDENTIFIER_EVIDENCE_TYPES
        )
        if unknown_mandatory:
            raise ValidationException(
                "mandatory_auto_resolution_evidence may only reference governed strong-identifier "
                f"types, not: {sorted(t.value for t in unknown_mandatory)}"
            )
        if not set(self.mandatory_auto_resolution_evidence) <= set(
            self.participating_evidence_types
        ):
            raise ValidationException(
                "mandatory_auto_resolution_evidence must be a subset of participating_evidence_types"
            )
        unknown_weighted = set(self.evidence_weights) - set(self.participating_evidence_types)
        if unknown_weighted:
            raise ValidationException(
                "evidence_weights references evidence types outside participating_evidence_types: "
                f"{sorted(t.value for t in unknown_weighted)}"
            )
        for evidence_type, weight in self.evidence_weights.items():
            if not 0.0 < weight <= 1.0:
                raise ValidationException(
                    f"evidence_weights[{evidence_type.value!r}] must be between 0 (exclusive) and 1"
                )
        for source_system, weight in self.source_system_trust_weights.items():
            if not source_system.strip():
                raise ValidationException("source_system_trust_weights keys must not be blank")
            if not 0.0 < weight <= 2.0:
                raise ValidationException(
                    f"source_system_trust_weights[{source_system!r}] must be between 0 (exclusive) and 2"
                )
        if self.country_conflict_severity not in ("veto", "review"):
            raise ValidationException("country_conflict_severity must be 'veto' or 'review'")
        if self.parent_subsidiary_conflict_severity not in ("veto", "review"):
            raise ValidationException(
                "parent_subsidiary_conflict_severity must be 'veto' or 'review'"
            )
        if self.sensitive_value_masking is not True:
            raise ValidationException(
                "sensitive_value_masking cannot be disabled by policy; this is a security invariant"
            )

    def to_definition_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "policy_version": self.policy_version,
            "resolved_threshold": self.resolved_threshold,
            "possible_threshold": self.possible_threshold,
            "high_confidence_threshold": self.high_confidence_threshold,
            "medium_confidence_threshold": self.medium_confidence_threshold,
            "min_corroborating_attributes": self.min_corroborating_attributes,
            "participating_evidence_types": [t.value for t in self.participating_evidence_types],
            "mandatory_auto_resolution_evidence": [
                t.value for t in self.mandatory_auto_resolution_evidence
            ],
            "evidence_weights": {t.value: w for t, w in self.evidence_weights.items()},
            "source_system_trust_weights": dict(self.source_system_trust_weights),
            "country_conflict_severity": self.country_conflict_severity,
            "parent_subsidiary_conflict_severity": self.parent_subsidiary_conflict_severity,
            "sensitive_value_masking": self.sensitive_value_masking,
            "human_approval_required_for_override": self.human_approval_required_for_override,
        }

    @staticmethod
    def from_definition_dict(raw: dict[str, Any]) -> "ResolutionPolicyDefinition":
        if not isinstance(raw, dict):
            raise ValidationException("Policy definition must be a JSON object")
        unknown_keys = set(raw) - _REQUIRED_KEYS
        if unknown_keys:
            raise ValidationException(f"Unknown policy configuration keys: {sorted(unknown_keys)}")
        missing_keys = _REQUIRED_KEYS - set(raw)
        if missing_keys:
            raise ValidationException(
                f"Missing required policy configuration keys: {sorted(missing_keys)}"
            )
        try:
            participating = tuple(EvidenceType(v) for v in raw["participating_evidence_types"])
            mandatory = tuple(EvidenceType(v) for v in raw["mandatory_auto_resolution_evidence"])
            weights = {EvidenceType(k): float(v) for k, v in raw["evidence_weights"].items()}
        except ValueError as error:
            raise ValidationException(
                f"Invalid evidence type in policy definition: {error}"
            ) from error
        return ResolutionPolicyDefinition(
            policy_name=raw["policy_name"],
            policy_version=raw["policy_version"],
            resolved_threshold=float(raw["resolved_threshold"]),
            possible_threshold=float(raw["possible_threshold"]),
            high_confidence_threshold=float(raw["high_confidence_threshold"]),
            medium_confidence_threshold=float(raw["medium_confidence_threshold"]),
            min_corroborating_attributes=int(raw["min_corroborating_attributes"]),
            participating_evidence_types=participating,
            mandatory_auto_resolution_evidence=mandatory,
            evidence_weights=weights,
            source_system_trust_weights=dict(raw["source_system_trust_weights"]),
            country_conflict_severity=raw["country_conflict_severity"],
            parent_subsidiary_conflict_severity=raw["parent_subsidiary_conflict_severity"],
            sensitive_value_masking=bool(raw["sensitive_value_masking"]),
            human_approval_required_for_override=bool(raw["human_approval_required_for_override"]),
        )


_ALL_EVIDENCE_TYPES: tuple[EvidenceType, ...] = tuple(EvidenceType)
_BASE_WEIGHTS: dict[EvidenceType, float] = {
    EvidenceType.STRONG_IDENTIFIER_LEI: 0.95,
    EvidenceType.STRONG_IDENTIFIER_EXTERNAL_ID: 0.9,
    EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION: 0.9,
    EvidenceType.SOURCE_SYSTEM_CROSSWALK: 0.85,
    EvidenceType.DOMAIN_VERIFIED: 0.35,
    EvidenceType.EMAIL_DOMAIN_VERIFIED: 0.25,
    EvidenceType.COUNTRY_MATCH: 0.15,
    EvidenceType.REGISTERED_ADDRESS_MATCH: 0.2,
    EvidenceType.POSTAL_CODE_MATCH: 0.1,
    EvidenceType.LEGAL_NAME_MATCH: 0.1,
    EvidenceType.TRADING_NAME_MATCH: 0.1,
    EvidenceType.ALIAS_MATCH: 0.1,
    EvidenceType.ACRONYM_MATCH: 0.05,
    # LEGAL_SUFFIX_NORMALIZED and PARENT_SUBSIDIARY_DISTINCTION are
    # deliberately absent: evidence.py hardcodes their contribution to 0.0
    # unconditionally (never routed through evidence_weights), and
    # evidence_weights values must be strictly positive, so they cannot be
    # listed here with a 0.0 weight.
    EvidenceType.SOURCE_SYSTEM_PROVENANCE: 0.05,
}


def conservative_preset() -> ResolutionPolicyDefinition:
    """Recommended default. Requires a governed strong identifier for any
    automatic resolution; name/acronym/domain/country evidence alone routes
    to steward review, never auto-resolves."""
    return ResolutionPolicyDefinition(
        policy_name="Conservative",
        policy_version="Supplier Resolution — Conservative v1.0",
        resolved_threshold=0.92,
        possible_threshold=0.55,
        high_confidence_threshold=0.92,
        medium_confidence_threshold=0.6,
        min_corroborating_attributes=3,
        participating_evidence_types=_ALL_EVIDENCE_TYPES,
        mandatory_auto_resolution_evidence=(
            EvidenceType.STRONG_IDENTIFIER_LEI,
            EvidenceType.STRONG_IDENTIFIER_EXTERNAL_ID,
            EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION,
            EvidenceType.SOURCE_SYSTEM_CROSSWALK,
        ),
        evidence_weights=dict(_BASE_WEIGHTS),
        country_conflict_severity="veto",
        parent_subsidiary_conflict_severity="veto",
    )


def balanced_preset() -> ResolutionPolicyDefinition:
    """No specific strong identifier is mandatory, but auto-resolution still
    requires either a strong identifier or several corroborating non-name
    attributes; country/parent-subsidiary conflicts still block, as a
    review signal rather than an outright veto."""
    return ResolutionPolicyDefinition(
        policy_name="Balanced",
        policy_version="Supplier Resolution — Balanced v1.0",
        resolved_threshold=0.85,
        possible_threshold=0.5,
        high_confidence_threshold=0.85,
        medium_confidence_threshold=0.55,
        min_corroborating_attributes=2,
        participating_evidence_types=_ALL_EVIDENCE_TYPES,
        mandatory_auto_resolution_evidence=(),
        evidence_weights=dict(_BASE_WEIGHTS),
        country_conflict_severity="review",
        parent_subsidiary_conflict_severity="veto",
    )


def exploratory_preset() -> ResolutionPolicyDefinition:
    """Lowest thresholds and corroboration bar for exploratory/analyst use;
    still bound by every hard safety invariant in evidence.py (name/acronym
    alone never resolve; strong-identifier conflicts always veto)."""
    return ResolutionPolicyDefinition(
        policy_name="Exploratory",
        policy_version="Supplier Resolution — Exploratory v1.0",
        resolved_threshold=0.75,
        possible_threshold=0.4,
        high_confidence_threshold=0.75,
        medium_confidence_threshold=0.45,
        min_corroborating_attributes=1,
        participating_evidence_types=_ALL_EVIDENCE_TYPES,
        mandatory_auto_resolution_evidence=(),
        evidence_weights=dict(_BASE_WEIGHTS),
        country_conflict_severity="review",
        parent_subsidiary_conflict_severity="review",
    )


PRESET_FACTORIES: dict[str, Any] = {
    "Conservative": conservative_preset,
    "Balanced": balanced_preset,
    "Exploratory": exploratory_preset,
}
