"""Deterministic answer composition for Ask CTEC (Gate D). No LLM: every
sentence is built from a fixed template filled with real traversal results.
The structured evidence (app.domain.ontology_copilot.traversal.TraversalPath)
remains the source of truth; this module only renders it as a short
human-readable sentence.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.ontology_copilot.traversal import TraversalPath


@dataclass(frozen=True, slots=True)
class AnsweredResult:
    answer: str
    product_names: tuple[str, ...]


def compose_products_depending_on_supplier_answer(
    *, supplier_name: str, paths: tuple[TraversalPath, ...]
) -> AnsweredResult:
    # De-duplicate by target entity id: more than one governed path may
    # reach the same product (e.g. two distinct materials feeding the same
    # BOM); the product is still counted once.
    seen: dict[str, str] = {}
    for path in paths:
        seen.setdefault(str(path.target_entity_id), path.target_entity_name)
    product_names = tuple(sorted(seen.values()))

    count = len(product_names)
    if count == 0:
        answer = (
            f"CTEC found 0 products connected to {supplier_name} "
            "through governed ontology relationships."
        )
    elif count == 1:
        answer = f"1 product depends on {supplier_name}:\n- {product_names[0]}"
    else:
        listed = "\n".join(f"- {name}" for name in product_names)
        answer = f"{count} products depend on {supplier_name}:\n{listed}"
    return AnsweredResult(answer=answer, product_names=product_names)


def compose_information_element_context_explanation_answer(
    *,
    blueprint_name: str,
    information_element_name: str,
    coverage_status: str,
    evidence_availability_status: str | None,
) -> str:
    """Gate P (CDD-025 §12): template-only rendering of an already-composed
    Gate N (coverage_status, evidence_availability_status) pair. Every
    sentence below is the exact, frozen vocabulary CDD-025 §12 binds -- no
    word here may be swapped for a trust/confidence/freshness/correctness/
    quality/readiness/satisfaction claim.
    """
    if coverage_status == "MAPPED":
        coverage_sentence = "CTEC has an Approved semantic mapping for this requirement."
    else:
        coverage_sentence = (
            "CTEC does not currently have an Approved semantic mapping for this requirement."
        )

    if evidence_availability_status is None:
        evidence_sentence = (
            "Evidence availability is not applicable, since no mapping exists to resolve a "
            "SourceField from."
        )
    elif evidence_availability_status == "EVIDENCE_PRESENT":
        evidence_sentence = (
            "Governed non-empty evidence has been observed for the resolved SourceField."
        )
    elif evidence_availability_status == "EVIDENCE_EMPTY":
        evidence_sentence = (
            "Governed evidence has been observed for the resolved SourceField, but it is empty."
        )
    else:
        evidence_sentence = "No governed evidence has been observed for the resolved SourceField."

    return (
        f"{information_element_name!r} in the {blueprint_name} Blueprint: "
        f"{coverage_sentence} {evidence_sentence}"
    )
