"""Multi-attribute evidence comparison and policy-governed decisioning for
Entity Resolution. Builds an honest, explainable EvidenceProfile from raw
supplier representations and a proposed canonical candidate, then applies a
ResolutionPolicyDefinition to reach a deterministic outcome.

Real schema limitation, disclosed: the physical model has no persisted,
governed columns for multi-attribute supplier data (domain, country,
aliases, strong identifiers, ...) on source_objects/enterprise_entities --
only a name. This module therefore takes structured attributes as direct
engine input (SourceRepresentation), not as a query against a new governed
table; what gets persisted immutably is the *computed* EvidenceProfile
(app.domain.identity_resolution.model.EvidenceProfile), not the raw input
attributes. A future increment could extend the physical model with a real
source-attribute store.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.domain.identity_resolution import normalization as norm
from app.domain.identity_resolution.model import (
    ACRONYM_ONLY_EVIDENCE_TYPES,
    NAME_ONLY_EVIDENCE_TYPES,
    SENSITIVE_EVIDENCE_TYPES,
    STRONG_IDENTIFIER_EVIDENCE_TYPES,
    BusinessConfidence,
    EvidenceClassification,
    EvidenceItem,
    EvidenceProfile,
    EvidenceType,
    ResolutionOutcome,
)
from app.domain.identity_resolution.policy import ResolutionPolicyDefinition
from app.domain.shared.exceptions import ValidationException

# Country/parent-subsidiary conflicts classified NEGATIVE (policy severity
# "review") still always block automatic resolution, distinguishing them
# from an ordinary weak-negative signal like a postal-code mismatch.
_ALWAYS_REVIEW_FORCING_ON_NEGATIVE = frozenset(
    {EvidenceType.COUNTRY_MATCH, EvidenceType.PARENT_SUBSIDIARY_DISTINCTION}
)


@dataclass(frozen=True, slots=True)
class SourceRepresentation:
    """One raw supplier representation's declared attributes, as engine
    input. Not every field need be populated -- missing evidence is honest,
    not a stand-in for zero."""

    source_object_id: UUID
    source_system_name: str
    display_name: str
    trading_name: str | None = None
    aliases: tuple[str, ...] = ()
    acronym: str | None = None
    website_domain: str | None = None
    email_domain: str | None = None
    country: str | None = None
    registered_address: str | None = None
    postal_code: str | None = None
    # (identifier type, raw value) -- type must be one of
    # STRONG_IDENTIFIER_EVIDENCE_TYPES. Raw values for SENSITIVE_EVIDENCE_TYPES
    # never leave this dataclass unmasked; build_evidence_profile fingerprints
    # them before they appear in any EvidenceItem.
    strong_identifiers: tuple[tuple[EvidenceType, str], ...] = ()
    parent_entity_name: str | None = None

    def __post_init__(self) -> None:
        if not self.display_name.strip():
            raise ValidationException("SourceRepresentation requires a display_name")
        if not self.source_system_name.strip():
            raise ValidationException("SourceRepresentation requires a source_system_name")
        for identifier_type, _value in self.strong_identifiers:
            if identifier_type not in STRONG_IDENTIFIER_EVIDENCE_TYPES:
                raise ValidationException(
                    f"{identifier_type} is not a governed strong-identifier type"
                )


def _display_value(evidence_type: EvidenceType, raw: str) -> str:
    """The safe value shown in an EvidenceItem: fingerprinted for sensitive
    types, normalized otherwise. Never the raw sensitive value."""
    if evidence_type in SENSITIVE_EVIDENCE_TYPES:
        return norm.fingerprint(raw)
    return raw


def _comparison_key(evidence_type: EvidenceType, raw: str) -> str:
    """The value actually compared for agreement/conflict. For sensitive
    types this is the fingerprint too, so raw values are never held in
    memory past this function's input."""
    if evidence_type in SENSITIVE_EVIDENCE_TYPES:
        return norm.fingerprint(raw)
    return raw


def _name_like_item(
    evidence_type: EvidenceType,
    candidate_value: str,
    rep_values: tuple[tuple[str, str], ...],
    *,
    normalize: Callable[[str], str],
    label: str,
    weight: float,
) -> EvidenceItem:
    """Exact-match-only comparison for name/trading-name/alias: a match is
    POSITIVE (contributing its configured weight -- name evidence is a real,
    meaningful signal, just never alone sufficient for automatic resolution;
    that safety rule is enforced in decide() by excluding
    NAME_ONLY_EVIDENCE_TYPES from the corroboration count, not by zeroing
    its score contribution here), anything else is MISSING (natural name
    variation is not evidence of conflict, unlike a strong identifier or
    country)."""
    candidate_norm = normalize(candidate_value)
    matches = sorted(
        {source_system for source_system, value in rep_values if normalize(value) == candidate_norm}
    )
    if matches:
        return EvidenceItem(
            evidence_type=evidence_type,
            compared_attributes=(label,),
            normalized_values=(candidate_norm,),
            classification=EvidenceClassification.POSITIVE,
            contribution=weight,
            explanation=f"{label} matches the candidate exactly for: {', '.join(matches)}.",
            provenance=", ".join(matches),
        )
    return EvidenceItem(
        evidence_type=evidence_type,
        compared_attributes=(label,),
        normalized_values=(),
        classification=EvidenceClassification.MISSING,
        contribution=0.0,
        explanation=f"No representation's {label.lower()} matched the candidate's exactly.",
        provenance="none",
    )


def _agreement_item(
    evidence_type: EvidenceType,
    label: str,
    candidate_value: str | None,
    rep_values: tuple[tuple[str, str], ...],
    *,
    normalize: Callable[[str], str],
    conflict_classification: EvidenceClassification,
    weight: float,
) -> EvidenceItem:
    """Generic 'do all present values agree' comparison: POSITIVE if every
    present value (candidate + representations) normalizes identically,
    conflict_classification if two disagree, MISSING if nothing is present."""
    values: dict[str, list[str]] = {}
    if candidate_value:
        values.setdefault(normalize(candidate_value), []).append("candidate")
    for source_system, raw in rep_values:
        if raw:
            values.setdefault(normalize(raw), []).append(source_system)
    if not values:
        return EvidenceItem(
            evidence_type=evidence_type,
            compared_attributes=(label,),
            normalized_values=(),
            classification=EvidenceClassification.MISSING,
            contribution=0.0,
            explanation=f"{label} was not provided by the candidate or any representation.",
            provenance="none",
        )
    if len(values) == 1:
        ((normalized_value, sources),) = values.items()
        return EvidenceItem(
            evidence_type=evidence_type,
            compared_attributes=(label,),
            normalized_values=(normalized_value,),
            classification=EvidenceClassification.POSITIVE,
            contribution=weight,
            explanation=f"{label} agrees across: {', '.join(sorted(sources))}.",
            provenance=", ".join(sorted(sources)),
        )
    normalized_values = tuple(sorted(values))
    provenance = "; ".join(f"{v}: {', '.join(sorted(s))}" for v, s in sorted(values.items()))
    return EvidenceItem(
        evidence_type=evidence_type,
        compared_attributes=(label,),
        normalized_values=normalized_values,
        classification=conflict_classification,
        contribution=-weight if conflict_classification is EvidenceClassification.NEGATIVE else 0.0,
        explanation=f"{label} conflicts: {provenance}.",
        provenance=provenance,
    )


def build_evidence_profile(
    *,
    representations: tuple[SourceRepresentation, ...],
    candidate_name: str,
    candidate_country: str | None,
    candidate_parent_entity_name: str | None,
    policy: ResolutionPolicyDefinition,
) -> EvidenceProfile:
    if not representations:
        raise ValidationException("At least one source representation is required")

    participating = set(policy.participating_evidence_types)
    weight: Callable[[EvidenceType], float] = lambda t: policy.evidence_weights.get(  # noqa: E731
        t, 0.0
    )
    items: list[EvidenceItem] = []

    def include(evidence_type: EvidenceType, builder: Callable[[], EvidenceItem]) -> None:
        if evidence_type in participating:
            items.append(builder())

    include(
        EvidenceType.LEGAL_NAME_MATCH,
        lambda: _name_like_item(
            EvidenceType.LEGAL_NAME_MATCH,
            candidate_name,
            tuple((r.source_system_name, r.display_name) for r in representations),
            normalize=norm.canonical_name,
            label="Legal Name",
            weight=weight(EvidenceType.LEGAL_NAME_MATCH),
        ),
    )
    include(
        EvidenceType.TRADING_NAME_MATCH,
        lambda: _name_like_item(
            EvidenceType.TRADING_NAME_MATCH,
            candidate_name,
            tuple(
                (r.source_system_name, r.trading_name) for r in representations if r.trading_name
            ),
            normalize=norm.canonical_name,
            label="Trading Name",
            weight=weight(EvidenceType.TRADING_NAME_MATCH),
        ),
    )
    include(
        EvidenceType.ALIAS_MATCH,
        lambda: _name_like_item(
            EvidenceType.ALIAS_MATCH,
            candidate_name,
            tuple((r.source_system_name, alias) for r in representations for alias in r.aliases),
            normalize=norm.canonical_name,
            label="Approved Alias",
            weight=weight(EvidenceType.ALIAS_MATCH),
        ),
    )

    if EvidenceType.ACRONYM_MATCH in participating:
        candidate_acronym = norm.derive_acronym(candidate_name)
        rep_acronyms = tuple(
            (
                r.source_system_name,
                (
                    norm.normalize_acronym(r.acronym)
                    if r.acronym
                    else norm.derive_acronym(r.display_name)
                ),
            )
            for r in representations
        )
        matches = sorted({source for source, value in rep_acronyms if value == candidate_acronym})
        if matches:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.ACRONYM_MATCH,
                    compared_attributes=("Acronym",),
                    normalized_values=(candidate_acronym,),
                    classification=EvidenceClassification.POSITIVE,
                    contribution=weight(EvidenceType.ACRONYM_MATCH),
                    explanation=f"Derived acronym {candidate_acronym!r} matches: {', '.join(matches)}.",
                    provenance=", ".join(matches),
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.ACRONYM_MATCH,
                    compared_attributes=("Acronym",),
                    normalized_values=(),
                    classification=EvidenceClassification.MISSING,
                    contribution=0.0,
                    explanation="No representation's acronym matched the candidate's derived acronym.",
                    provenance="none",
                )
            )

    if EvidenceType.LEGAL_SUFFIX_NORMALIZED in participating:
        stripped = [
            r.source_system_name
            for r in representations
            if norm.strip_legal_suffix(norm.normalize_name(r.display_name))
            != norm.normalize_name(r.display_name)
        ]
        if norm.strip_legal_suffix(norm.normalize_name(candidate_name)) != norm.normalize_name(
            candidate_name
        ):
            stripped.append("candidate")
        if stripped:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.LEGAL_SUFFIX_NORMALIZED,
                    compared_attributes=("Legal Suffix",),
                    normalized_values=tuple(sorted(stripped)),
                    classification=EvidenceClassification.POSITIVE,
                    contribution=0.0,
                    explanation=f"A governed legal suffix was normalized for: {', '.join(sorted(stripped))}.",
                    provenance=", ".join(sorted(stripped)),
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.LEGAL_SUFFIX_NORMALIZED,
                    compared_attributes=("Legal Suffix",),
                    normalized_values=(),
                    classification=EvidenceClassification.MISSING,
                    contribution=0.0,
                    explanation="No recognized legal suffix was present to normalize.",
                    provenance="none",
                )
            )

    include(
        EvidenceType.DOMAIN_VERIFIED,
        lambda: _agreement_item(
            EvidenceType.DOMAIN_VERIFIED,
            "Website Domain",
            None,
            tuple((r.source_system_name, r.website_domain or "") for r in representations),
            normalize=norm.normalize_domain,
            conflict_classification=EvidenceClassification.NEGATIVE,
            weight=weight(EvidenceType.DOMAIN_VERIFIED),
        ),
    )
    include(
        EvidenceType.EMAIL_DOMAIN_VERIFIED,
        lambda: _agreement_item(
            EvidenceType.EMAIL_DOMAIN_VERIFIED,
            "Business Email Domain",
            None,
            tuple((r.source_system_name, r.email_domain or "") for r in representations),
            normalize=norm.normalize_domain,
            conflict_classification=EvidenceClassification.NEGATIVE,
            weight=weight(EvidenceType.EMAIL_DOMAIN_VERIFIED),
        ),
    )
    include(
        EvidenceType.COUNTRY_MATCH,
        lambda: _agreement_item(
            EvidenceType.COUNTRY_MATCH,
            "Country",
            candidate_country,
            tuple((r.source_system_name, r.country or "") for r in representations),
            normalize=norm.normalize_country,
            conflict_classification=(
                EvidenceClassification.VETO
                if policy.country_conflict_severity == "veto"
                else EvidenceClassification.NEGATIVE
            ),
            weight=weight(EvidenceType.COUNTRY_MATCH),
        ),
    )
    include(
        EvidenceType.REGISTERED_ADDRESS_MATCH,
        lambda: _agreement_item(
            EvidenceType.REGISTERED_ADDRESS_MATCH,
            "Registered Address",
            None,
            tuple((r.source_system_name, r.registered_address or "") for r in representations),
            normalize=norm.normalize_address,
            conflict_classification=EvidenceClassification.NEGATIVE,
            weight=weight(EvidenceType.REGISTERED_ADDRESS_MATCH),
        ),
    )
    include(
        EvidenceType.POSTAL_CODE_MATCH,
        lambda: _agreement_item(
            EvidenceType.POSTAL_CODE_MATCH,
            "Postal Code",
            None,
            tuple((r.source_system_name, r.postal_code or "") for r in representations),
            normalize=norm.normalize_postal_code,
            conflict_classification=EvidenceClassification.NEGATIVE,
            weight=weight(EvidenceType.POSTAL_CODE_MATCH),
        ),
    )

    for identifier_type in (
        EvidenceType.STRONG_IDENTIFIER_LEI,
        EvidenceType.STRONG_IDENTIFIER_EXTERNAL_ID,
        EvidenceType.STRONG_IDENTIFIER_TAX_REGISTRATION,
        EvidenceType.SOURCE_SYSTEM_CROSSWALK,
    ):
        if identifier_type not in participating:
            continue
        values: dict[str, list[str]] = {}
        for r in representations:
            for kind, raw in r.strong_identifiers:
                if kind is identifier_type and raw.strip():
                    values.setdefault(_comparison_key(identifier_type, raw), []).append(
                        r.source_system_name
                    )
        label = identifier_type.value
        if not values:
            items.append(
                EvidenceItem(
                    evidence_type=identifier_type,
                    compared_attributes=(label,),
                    normalized_values=(),
                    classification=EvidenceClassification.MISSING,
                    contribution=0.0,
                    explanation=f"{label} was not provided by any representation.",
                    provenance="none",
                )
            )
        elif len(values) == 1:
            ((key, sources),) = values.items()
            raw_for_display = next(
                raw
                for r in representations
                for kind, raw in r.strong_identifiers
                if kind is identifier_type and _comparison_key(identifier_type, raw) == key
            )
            items.append(
                EvidenceItem(
                    evidence_type=identifier_type,
                    compared_attributes=(label,),
                    normalized_values=(_display_value(identifier_type, raw_for_display),),
                    classification=EvidenceClassification.POSITIVE,
                    contribution=weight(identifier_type),
                    explanation=f"{label} agrees across: {', '.join(sorted(sources))}.",
                    provenance=", ".join(sorted(sources)),
                )
            )
        else:
            provenance = "; ".join(f"{', '.join(sorted(s))}" for s in values.values())
            items.append(
                EvidenceItem(
                    evidence_type=identifier_type,
                    compared_attributes=(label,),
                    normalized_values=tuple(f"fp:conflict:{i}" for i in range(len(values))),
                    classification=EvidenceClassification.VETO,
                    contribution=0.0,
                    explanation=f"{label} conflicts across representations ({len(values)} distinct values).",
                    provenance=provenance,
                )
            )

    if EvidenceType.PARENT_SUBSIDIARY_DISTINCTION in participating:
        declared_parents = sorted(
            {
                (r.source_system_name, norm.canonical_name(r.parent_entity_name))
                for r in representations
                if r.parent_entity_name
            }
        )
        candidate_canonical = (
            norm.canonical_name(candidate_parent_entity_name)
            if candidate_parent_entity_name
            else None
        )
        conflicting = [
            source
            for source, parent in declared_parents
            if candidate_canonical is not None and parent != candidate_canonical
        ]
        if not declared_parents:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.PARENT_SUBSIDIARY_DISTINCTION,
                    compared_attributes=("Parent Entity",),
                    normalized_values=(),
                    classification=EvidenceClassification.MISSING,
                    contribution=0.0,
                    explanation="No representation declared a parent/subsidiary relationship.",
                    provenance="none",
                )
            )
        elif conflicting:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.PARENT_SUBSIDIARY_DISTINCTION,
                    compared_attributes=("Parent Entity",),
                    normalized_values=tuple(sorted({p for _s, p in declared_parents})),
                    classification=(
                        EvidenceClassification.VETO
                        if policy.parent_subsidiary_conflict_severity == "veto"
                        else EvidenceClassification.NEGATIVE
                    ),
                    contribution=0.0,
                    explanation=(
                        "A declared parent/subsidiary relationship differs from the candidate for: "
                        f"{', '.join(sorted(conflicting))}."
                    ),
                    provenance=", ".join(sorted(conflicting)),
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.PARENT_SUBSIDIARY_DISTINCTION,
                    compared_attributes=("Parent Entity",),
                    normalized_values=tuple(sorted({p for _s, p in declared_parents})),
                    classification=EvidenceClassification.POSITIVE,
                    contribution=0.0,
                    explanation="Declared parent/subsidiary relationships are consistent with the candidate.",
                    provenance=", ".join(sorted(s for s, _p in declared_parents)),
                )
            )

    if EvidenceType.SOURCE_SYSTEM_PROVENANCE in participating:
        distinct_systems = sorted({r.source_system_name for r in representations})
        if len(distinct_systems) >= 2:
            base = weight(EvidenceType.SOURCE_SYSTEM_PROVENANCE)
            trust_adjusted = sum(
                policy.source_system_trust_weights.get(system, 1.0) for system in distinct_systems
            ) / len(distinct_systems)
            contribution = min(1.0, base * trust_adjusted * (len(distinct_systems) - 1))
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.SOURCE_SYSTEM_PROVENANCE,
                    compared_attributes=("Source System",),
                    normalized_values=tuple(distinct_systems),
                    classification=EvidenceClassification.POSITIVE,
                    contribution=contribution,
                    explanation=(
                        f"{len(distinct_systems)} independent source systems corroborate this case: "
                        f"{', '.join(distinct_systems)}."
                    ),
                    provenance=", ".join(distinct_systems),
                )
            )
        else:
            items.append(
                EvidenceItem(
                    evidence_type=EvidenceType.SOURCE_SYSTEM_PROVENANCE,
                    compared_attributes=("Source System",),
                    normalized_values=tuple(distinct_systems),
                    classification=EvidenceClassification.MISSING,
                    contribution=0.0,
                    explanation="Only one source system is represented; no independent corroboration.",
                    provenance=", ".join(distinct_systems),
                )
            )

    return EvidenceProfile(items=tuple(items))


@dataclass(frozen=True, slots=True)
class ResolutionDecision:
    """Transient (never persisted as-is) result of evaluating one candidate.
    The caller derives an EnterpriseEntityResolutionRecord from this."""

    outcome: ResolutionOutcome
    business_confidence: BusinessConfidence
    score: float
    evidence_profile: EvidenceProfile
    triggered_mandatory_rules: tuple[str, ...]
    triggered_veto_rules: tuple[str, ...]
    structured_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        reasons = list(self.triggered_veto_rules) + list(self.triggered_mandatory_rules)
        if not reasons:
            reasons = [
                f"{item.evidence_type.value}: {item.explanation}"
                for item in self.evidence_profile.positive_items
            ] or ["No positive, negative, or veto evidence was available."]
        object.__setattr__(self, "structured_reasons", tuple(reasons))


def decide(
    evidence_profile: EvidenceProfile, policy: ResolutionPolicyDefinition
) -> ResolutionDecision:
    """Deterministic policy-governed decisioning over an evidence profile.
    Encodes every required safety rule; see module docstring and
    policy.py's."""
    veto_items = evidence_profile.veto_items
    if veto_items:
        veto_rules = tuple(
            f"Veto: {item.evidence_type.value} conflicts ({item.provenance})" for item in veto_items
        )
        return ResolutionDecision(
            outcome=ResolutionOutcome.BLOCKED_CONFLICT,
            business_confidence=BusinessConfidence.LOW,
            score=0.0,
            evidence_profile=evidence_profile,
            triggered_mandatory_rules=(),
            triggered_veto_rules=veto_rules,
        )

    positive = evidence_profile.positive_items
    negative = evidence_profile.negative_items
    raw_score = sum(item.contribution for item in positive) - sum(
        abs(item.contribution) for item in negative
    )
    score = max(0.0, min(1.0, raw_score))

    review_forcing = any(
        item.evidence_type in _ALWAYS_REVIEW_FORCING_ON_NEGATIVE for item in negative
    )

    strong_positive_types = frozenset(
        item.evidence_type
        for item in positive
        if item.evidence_type in STRONG_IDENTIFIER_EVIDENCE_TYPES
    )
    mandatory = frozenset(policy.mandatory_auto_resolution_evidence)
    mandatory_satisfied = not mandatory or bool(strong_positive_types & mandatory)

    non_name_positive_types = frozenset(item.evidence_type for item in positive) - (
        NAME_ONLY_EVIDENCE_TYPES | ACRONYM_ONLY_EVIDENCE_TYPES
    )
    corroborated = len(non_name_positive_types) >= policy.min_corroborating_attributes

    eligible_for_auto = (
        not review_forcing and mandatory_satisfied and (bool(strong_positive_types) or corroborated)
    )

    mandatory_rules: list[str] = []
    if strong_positive_types:
        mandatory_rules.append(
            "Strong identifier match: " + ", ".join(sorted(t.value for t in strong_positive_types))
        )
    if corroborated:
        mandatory_rules.append(
            f"Corroborating non-name attributes: {len(non_name_positive_types)} "
            f"(policy requires {policy.min_corroborating_attributes})"
        )
    if mandatory and not (strong_positive_types & mandatory):
        mandatory_rules.append(
            "Policy requires one of: " + ", ".join(sorted(t.value for t in mandatory))
        )
    if review_forcing:
        mandatory_rules.append("Country or parent/subsidiary conflict forces steward review")

    if eligible_for_auto and score >= policy.resolved_threshold:
        outcome = ResolutionOutcome.RESOLVED
    elif score >= policy.possible_threshold:
        outcome = ResolutionOutcome.POSSIBLE
    else:
        outcome = ResolutionOutcome.UNRESOLVED

    confidence = (
        BusinessConfidence.HIGH
        if score >= policy.high_confidence_threshold
        else (
            BusinessConfidence.MEDIUM
            if score >= policy.medium_confidence_threshold
            else BusinessConfidence.LOW
        )
    )

    return ResolutionDecision(
        outcome=outcome,
        business_confidence=confidence,
        score=score,
        evidence_profile=evidence_profile,
        triggered_mandatory_rules=tuple(mandatory_rules),
        triggered_veto_rules=(),
    )
