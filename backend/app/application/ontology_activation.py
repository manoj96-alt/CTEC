"""Supplier Risk's ontology activation contract. The backend — never the
browser — resolves which published ontology a result is attributed to.
Reuses the single shared resolver in app.domain.ontology.resolver; this
module adds no second ontology representation, only the supplier-risk
specific projection (applicable concept/relationship IDs, semantic path)
on top of it.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.domain.ontology.resolver import resolve_supplier_risk_ontology
from app.domain.ontology.semantic_path import (
    SemanticPathStep,
    build_semantic_path,
    render_semantic_path_text,
)

APPLICABLE_CONCEPT_NAMES: tuple[str, ...] = (
    "Supplier",
    "Material",
    "BOM",
    "Product",
    "Facility",
    "Region",
    "Revenue Exposure",
    "Alternate Supplier",
    "Contract",
    "Risk Event",
)
APPLICABLE_RELATIONSHIP_NAMES: tuple[str, ...] = (
    "supplies",
    "usedIn",
    "defines",
    "generatesRevenue",
    "locatedIn",
    "exposedTo",
    "boundBy",
)


@dataclass(frozen=True, slots=True)
class OntologyActivation:
    ontology_id: str
    ontology_version: str
    ontology_status: str
    applicable_concept_ids: list[str]
    applicable_relationship_ids: list[str]
    quality_overall_score: float
    semantic_path: list[SemanticPathStep]
    semantic_path_text: str


class OntologyActivationService:
    """Reads the persisted, published ontology and resolves the activation
    context for a Supplier Risk result. Never trusts a browser-supplied
    ontology version — resolution always happens here, server-side."""

    def __init__(self, session_factory: "sessionmaker[Session] | None") -> None:
        self._sessions = session_factory

    def resolve(self) -> OntologyActivation | None:
        if self._sessions is None:
            return None
        with self._sessions() as session:
            ontology = resolve_supplier_risk_ontology(session)

        applicable_concept_ids = [
            concept_id
            for name in APPLICABLE_CONCEPT_NAMES
            if (concept_id := ontology.concept_id_by_name(name)) is not None
        ]
        applicable_relationship_ids = [
            relationship_id
            for name in APPLICABLE_RELATIONSHIP_NAMES
            if (relationship_id := ontology.relationship_id_by_name(name)) is not None
        ]
        path = build_semantic_path(ontology)

        return OntologyActivation(
            ontology_id=ontology.ontology_id,
            ontology_version=ontology.version,
            ontology_status=ontology.status,
            applicable_concept_ids=applicable_concept_ids,
            applicable_relationship_ids=applicable_relationship_ids,
            quality_overall_score=ontology.quality()["overall_score"],
            semantic_path=path,
            semantic_path_text=render_semantic_path_text(path),
        )
