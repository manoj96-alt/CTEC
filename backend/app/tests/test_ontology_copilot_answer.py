from uuid import uuid4

from app.domain.ontology_copilot.answer import compose_products_depending_on_supplier_answer
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
