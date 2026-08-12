"""Deterministic MVP ontology quality score. Explainable, not AI-generated:
every dimension is a simple, auditable check over persisted ontology data
plus the curated seed metadata. No learned or opaque scoring is involved.
"""

from dataclasses import dataclass, field

from app.infrastructure.persistence.ontology_seed import (
    CONCEPT_DEFINITIONS,
    REQUIRED_CONCEPTS,
    REQUIRED_RELATIONSHIPS,
)


@dataclass(frozen=True, slots=True)
class DimensionScore:
    dimension: str
    score: float
    passed: bool
    explanation: str


@dataclass(frozen=True, slots=True)
class QualityScoreResult:
    overall_score: float
    dimensions: tuple[DimensionScore, ...]
    passed_checks: tuple[str, ...] = field(default_factory=tuple)
    failed_checks: tuple[str, ...] = field(default_factory=tuple)
    method: str = (
        "Deterministic MVP calculation: the mean of seven explainable, rule-based "
        "coverage and completeness checks over persisted ontology data. Not an "
        "AI-generated or learned score."
    )


def calculate_quality_score(
    *,
    concept_names: set[str],
    relationship_triples: set[tuple[str, str, str]],
    concept_governance_statuses: dict[str, str],
    relationship_governance_statuses: dict[str, str],
) -> QualityScoreResult:
    dimensions: list[DimensionScore] = []

    # 1. Required concept coverage
    present_concepts = set(REQUIRED_CONCEPTS) & concept_names
    concept_coverage = len(present_concepts) / len(REQUIRED_CONCEPTS)
    dimensions.append(
        DimensionScore(
            dimension="concept_coverage",
            score=concept_coverage,
            passed=concept_coverage == 1.0,
            explanation=(
                f"{len(present_concepts)}/{len(REQUIRED_CONCEPTS)} required concepts "
                f"are persisted as governed entity types."
            ),
        )
    )

    # 2. Required relationship coverage
    present_relationships = set(REQUIRED_RELATIONSHIPS) & relationship_triples
    relationship_coverage = len(present_relationships) / len(REQUIRED_RELATIONSHIPS)
    dimensions.append(
        DimensionScore(
            dimension="relationship_coverage",
            score=relationship_coverage,
            passed=relationship_coverage == 1.0,
            explanation=(
                f"{len(present_relationships)}/{len(REQUIRED_RELATIONSHIPS)} required "
                f"relationships are persisted with a domain/range binding."
            ),
        )
    )

    # 3. Definition completeness (curated MVP metadata, see ontology_seed.py docstring)
    defined = {name for name in present_concepts if CONCEPT_DEFINITIONS.get(name, "").strip()}
    definition_completeness = len(defined) / len(REQUIRED_CONCEPTS) if REQUIRED_CONCEPTS else 0.0
    dimensions.append(
        DimensionScore(
            dimension="definition_completeness",
            score=definition_completeness,
            passed=definition_completeness == 1.0,
            explanation=(
                f"{len(defined)}/{len(REQUIRED_CONCEPTS)} required concepts have a "
                f"curated MVP definition (not yet a database-governed field)."
            ),
        )
    )

    # 4. Mapping completeness — every required relationship's domain and range
    #    concept must itself be present in the persisted concept set.
    mapped = {
        (name, source, target)
        for name, source, target in present_relationships
        if source in concept_names and target in concept_names
    }
    mapping_completeness = (
        len(mapped) / len(REQUIRED_RELATIONSHIPS) if REQUIRED_RELATIONSHIPS else 0.0
    )
    dimensions.append(
        DimensionScore(
            dimension="mapping_completeness",
            score=mapping_completeness,
            passed=mapping_completeness == 1.0,
            explanation=(
                f"{len(mapped)}/{len(REQUIRED_RELATIONSHIPS)} relationships have both "
                f"their source and target concept persisted."
            ),
        )
    )

    # 5. Provenance completeness — every required concept and relationship
    #    must have a recorded governance status (a proxy for provenance in
    #    this MVP, since both share the same governed created_by/on fields).
    concept_provenance = sum(
        1 for name in present_concepts if concept_governance_statuses.get(name)
    )
    relationship_provenance = sum(
        1 for name, _, _ in present_relationships if relationship_governance_statuses.get(name)
    )
    total_items = len(REQUIRED_CONCEPTS) + len(REQUIRED_RELATIONSHIPS)
    provenance_completeness = (
        (concept_provenance + relationship_provenance) / total_items if total_items else 0.0
    )
    dimensions.append(
        DimensionScore(
            dimension="provenance_completeness",
            score=provenance_completeness,
            passed=provenance_completeness == 1.0,
            explanation=(
                f"{concept_provenance + relationship_provenance}/{total_items} concepts "
                f"and relationships carry a recorded governance status."
            ),
        )
    )

    # 6. Valid relationship endpoints — every required relationship's source
    #    and target must be one of the required concepts (no dangling edge).
    valid_endpoints = sum(
        1
        for name, source, target in present_relationships
        if source in REQUIRED_CONCEPTS and target in REQUIRED_CONCEPTS
    )
    endpoint_validity = (
        valid_endpoints / len(REQUIRED_RELATIONSHIPS) if REQUIRED_RELATIONSHIPS else 0.0
    )
    dimensions.append(
        DimensionScore(
            dimension="valid_relationship_endpoints",
            score=endpoint_validity,
            passed=endpoint_validity == 1.0,
            explanation=(
                f"{valid_endpoints}/{len(REQUIRED_RELATIONSHIPS)} relationships bind "
                f"only concepts within the required ontology scope."
            ),
        )
    )

    # 7. Governance-status completeness — every persisted concept and
    #    relationship must be explicitly Approved (not left Proposed).
    approved_concepts = sum(
        1 for name in present_concepts if concept_governance_statuses.get(name) == "Approved"
    )
    approved_relationships = sum(
        1
        for name, _, _ in present_relationships
        if relationship_governance_statuses.get(name) == "Approved"
    )
    governance_completeness = (
        (approved_concepts + approved_relationships) / total_items if total_items else 0.0
    )
    dimensions.append(
        DimensionScore(
            dimension="governance_status_completeness",
            score=governance_completeness,
            passed=governance_completeness == 1.0,
            explanation=(
                f"{approved_concepts + approved_relationships}/{total_items} concepts "
                f"and relationships are explicitly Approved."
            ),
        )
    )

    overall = sum(dimension.score for dimension in dimensions) / len(dimensions)
    passed_checks = tuple(dimension.dimension for dimension in dimensions if dimension.passed)
    failed_checks = tuple(dimension.dimension for dimension in dimensions if not dimension.passed)

    return QualityScoreResult(
        overall_score=round(overall, 4),
        dimensions=tuple(dimensions),
        passed_checks=passed_checks,
        failed_checks=failed_checks,
    )
