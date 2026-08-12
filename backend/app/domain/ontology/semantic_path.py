"""Builds the Supplier -> Material -> BOM -> Product -> Revenue Exposure
semantic path shown in a supplier-risk result, using only relationships
that are genuinely present in the resolved, persisted ontology. If a step
is missing from the persisted ontology, that step is simply omitted from
the path rather than fabricated — the path is always a true subset of
what is actually persisted.
"""

from dataclasses import dataclass

from app.domain.ontology.resolver import ResolvedOntology

SUPPLIER_RISK_PATH_STEPS: tuple[str, ...] = ("supplies", "usedIn", "defines", "generatesRevenue")


@dataclass(frozen=True, slots=True)
class SemanticPathStep:
    relationship_id: str
    relationship_name: str
    source_concept: str
    source_concept_id: str
    target_concept: str
    target_concept_id: str


def build_semantic_path(ontology: ResolvedOntology) -> list[SemanticPathStep]:
    steps: list[SemanticPathStep] = []
    for relationship_name in SUPPLIER_RISK_PATH_STEPS:
        relationship = ontology.relationship_by_name(relationship_name)
        if relationship is None:
            continue
        source_id = ontology.concept_id_by_name(relationship["source_concept"])
        target_id = ontology.concept_id_by_name(relationship["target_concept"])
        if source_id is None or target_id is None:
            continue
        steps.append(
            SemanticPathStep(
                relationship_id=relationship["relationship_type_id"],
                relationship_name=relationship["name"],
                source_concept=relationship["source_concept"],
                source_concept_id=source_id,
                target_concept=relationship["target_concept"],
                target_concept_id=target_id,
            )
        )
    return steps


def render_semantic_path_text(steps: list[SemanticPathStep]) -> str:
    if not steps:
        return ""
    parts = [steps[0].source_concept]
    for step in steps:
        parts.append(f"→ {step.relationship_name} →")
        parts.append(step.target_concept)
    return " ".join(parts)
