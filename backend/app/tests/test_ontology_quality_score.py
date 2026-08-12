from app.domain.ontology.quality_score import calculate_quality_score
from app.infrastructure.persistence.ontology_seed import REQUIRED_CONCEPTS, REQUIRED_RELATIONSHIPS


def test_complete_ontology_scores_perfectly_on_every_dimension() -> None:
    concept_names = set(REQUIRED_CONCEPTS)
    relationship_triples = set(REQUIRED_RELATIONSHIPS)
    concept_statuses = {name: "Approved" for name in REQUIRED_CONCEPTS}
    relationship_statuses = {name: "Approved" for name, _, _ in REQUIRED_RELATIONSHIPS}

    result = calculate_quality_score(
        concept_names=concept_names,
        relationship_triples=relationship_triples,
        concept_governance_statuses=concept_statuses,
        relationship_governance_statuses=relationship_statuses,
    )

    assert result.overall_score == 1.0
    assert len(result.failed_checks) == 0
    assert len(result.passed_checks) == 7
    assert all(dimension.passed for dimension in result.dimensions)


def test_missing_concept_reduces_coverage_and_dependent_dimensions_explainably() -> None:
    concept_names = set(REQUIRED_CONCEPTS) - {"Contract"}
    relationship_triples = set(REQUIRED_RELATIONSHIPS)
    concept_statuses = {name: "Approved" for name in concept_names}
    relationship_statuses = {name: "Approved" for name, _, _ in REQUIRED_RELATIONSHIPS}

    result = calculate_quality_score(
        concept_names=concept_names,
        relationship_triples=relationship_triples,
        concept_governance_statuses=concept_statuses,
        relationship_governance_statuses=relationship_statuses,
    )

    assert result.overall_score < 1.0
    coverage = next(d for d in result.dimensions if d.dimension == "concept_coverage")
    assert coverage.passed is False
    assert "9/10" in coverage.explanation
    # the boundBy relationship (Supplier -> Contract) loses a valid endpoint
    # once Contract is missing from the persisted concept set
    mapping = next(d for d in result.dimensions if d.dimension == "mapping_completeness")
    assert mapping.score < 1.0


def test_proposed_governance_status_fails_governance_completeness_only() -> None:
    concept_names = set(REQUIRED_CONCEPTS)
    relationship_triples = set(REQUIRED_RELATIONSHIPS)
    concept_statuses = {name: "Approved" for name in REQUIRED_CONCEPTS}
    concept_statuses["Supplier"] = "Proposed"
    relationship_statuses = {name: "Approved" for name, _, _ in REQUIRED_RELATIONSHIPS}

    result = calculate_quality_score(
        concept_names=concept_names,
        relationship_triples=relationship_triples,
        concept_governance_statuses=concept_statuses,
        relationship_governance_statuses=relationship_statuses,
    )

    governance = next(
        d for d in result.dimensions if d.dimension == "governance_status_completeness"
    )
    assert governance.passed is False
    provenance = next(d for d in result.dimensions if d.dimension == "provenance_completeness")
    assert provenance.passed is True  # Proposed is still a recorded status
    coverage = next(d for d in result.dimensions if d.dimension == "concept_coverage")
    assert coverage.passed is True  # governance status doesn't affect coverage
