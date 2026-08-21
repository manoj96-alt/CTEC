from uuid import uuid4

from app.domain.ontology_copilot.answer import (
    compose_information_element_context_explanation_answer,
    compose_products_depending_on_supplier_answer,
)
from app.domain.ontology_copilot.traversal import EvidenceStep, TraversalPath


def _path(product_name: str) -> TraversalPath:
    product_id = uuid4()
    return TraversalPath(
        target_entity_id=product_id,
        target_entity_name=product_name,
        steps=(
            EvidenceStep(1, uuid4(), "TSMC", "Supplier", "supplies"),
            EvidenceStep(2, product_id, product_name, "Product", None),
        ),
    )


def test_zero_products() -> None:
    result = compose_products_depending_on_supplier_answer(supplier_name="TSMC", paths=())
    assert result.product_names == ()
    assert "0 products" in result.answer
    assert "TSMC" in result.answer


def test_one_product() -> None:
    result = compose_products_depending_on_supplier_answer(
        supplier_name="TSMC", paths=(_path("Product A"),)
    )
    assert result.product_names == ("Product A",)
    assert "1 product depends on TSMC" in result.answer
    assert "Product A" in result.answer


def test_multiple_products_sorted_deterministically() -> None:
    result = compose_products_depending_on_supplier_answer(
        supplier_name="TSMC", paths=(_path("Product B"), _path("Product A"))
    )
    assert result.product_names == ("Product A", "Product B")
    assert "2 products depend on TSMC" in result.answer


def test_duplicate_paths_to_the_same_product_are_counted_once() -> None:
    single_path = _path("Product A")
    duplicate = TraversalPath(
        target_entity_id=single_path.target_entity_id,
        target_entity_name=single_path.target_entity_name,
        steps=single_path.steps,
    )
    result = compose_products_depending_on_supplier_answer(
        supplier_name="TSMC", paths=(single_path, duplicate)
    )
    assert result.product_names == ("Product A",)
    assert "1 product depends on TSMC" in result.answer


# ---------------------------------------------------------------------------
# Gate P (CDD-025 §12): Information-Element context explanation rendering
# ---------------------------------------------------------------------------

_FORBIDDEN_WORDS = (
    "trust",
    "confidence",
    "confident",
    "fresh",
    "stale",
    "correct",
    "valid",
    "complete",
    "quality",
    "risk",
    "severity",
    "priority",
    "ready",
    "satisfied",
    "satisfies",
    "blocker",
    "critical",
    "failed",
    "fail ",
)


def _assert_no_forbidden_claims(answer: str) -> None:
    lowered = answer.lower()
    for word in _FORBIDDEN_WORDS:
        assert word not in lowered, f"forbidden word {word!r} found in rendered answer: {answer!r}"


def test_mapped_evidence_present_answer() -> None:
    answer = compose_information_element_context_explanation_answer(
        blueprint_name="Semiconductor Supply Chain Blueprint",
        information_element_name="Supplier Legal Name",
        coverage_status="MAPPED",
        evidence_availability_status="EVIDENCE_PRESENT",
    )
    assert "Supplier Legal Name" in answer
    assert "Semiconductor Supply Chain Blueprint" in answer
    assert "CTEC has an Approved semantic mapping for this requirement." in answer
    assert "Governed non-empty evidence has been observed for the resolved SourceField." in answer
    _assert_no_forbidden_claims(answer)


def test_mapped_evidence_empty_answer() -> None:
    answer = compose_information_element_context_explanation_answer(
        blueprint_name="Blueprint A",
        information_element_name="Element A",
        coverage_status="MAPPED",
        evidence_availability_status="EVIDENCE_EMPTY",
    )
    assert (
        "Governed evidence has been observed for the resolved SourceField, but it is empty."
        in answer
    )
    _assert_no_forbidden_claims(answer)


def test_mapped_no_evidence_answer() -> None:
    answer = compose_information_element_context_explanation_answer(
        blueprint_name="Blueprint A",
        information_element_name="Element A",
        coverage_status="MAPPED",
        evidence_availability_status="NO_EVIDENCE",
    )
    assert "No governed evidence has been observed for the resolved SourceField." in answer
    _assert_no_forbidden_claims(answer)


def test_unmapped_answer_evidence_status_none() -> None:
    answer = compose_information_element_context_explanation_answer(
        blueprint_name="Blueprint A",
        information_element_name="Element A",
        coverage_status="UNMAPPED",
        evidence_availability_status=None,
    )
    assert (
        "CTEC does not currently have an Approved semantic mapping for this requirement." in answer
    )
    assert (
        "Evidence availability is not applicable, since no mapping exists to resolve a "
        "SourceField from." in answer
    )
    _assert_no_forbidden_claims(answer)


def test_answer_is_deterministic_for_identical_input() -> None:
    first = compose_information_element_context_explanation_answer(
        blueprint_name="Blueprint A",
        information_element_name="Element A",
        coverage_status="MAPPED",
        evidence_availability_status="EVIDENCE_PRESENT",
    )
    second = compose_information_element_context_explanation_answer(
        blueprint_name="Blueprint A",
        information_element_name="Element A",
        coverage_status="MAPPED",
        evidence_availability_status="EVIDENCE_PRESENT",
    )
    assert first == second
