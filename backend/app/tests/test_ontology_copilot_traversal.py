from uuid import uuid4

from app.domain.ontology_copilot.traversal import GraphEdge, GraphEntity, find_paths_to_target_type


def _entity(name: str, entity_type: str) -> GraphEntity:
    return GraphEntity(entity_id=uuid4(), entity_name=name, entity_type_name=entity_type)


def test_finds_expected_two_hop_paths_to_target_type() -> None:
    supplier = _entity("TSMC", "Supplier")
    material_a = _entity("Material A", "Material")
    material_b = _entity("Material B", "Material")
    bom_a = _entity("BOM A", "BOM")
    bom_b = _entity("BOM B", "BOM")
    product_a = _entity("Product A", "Product")
    product_b = _entity("Product B", "Product")

    entities_by_id = {
        e.entity_id: e
        for e in (supplier, material_a, material_b, bom_a, bom_b, product_a, product_b)
    }
    edges = (
        GraphEdge("supplies", supplier.entity_id, material_a.entity_id),
        GraphEdge("supplies", supplier.entity_id, material_b.entity_id),
        GraphEdge("usedIn", material_a.entity_id, bom_a.entity_id),
        GraphEdge("usedIn", material_b.entity_id, bom_b.entity_id),
        GraphEdge("defines", bom_a.entity_id, product_a.entity_id),
        GraphEdge("defines", bom_b.entity_id, product_b.entity_id),
    )

    paths = find_paths_to_target_type(
        start_entity=supplier,
        entities_by_id=entities_by_id,
        edges=edges,
        target_entity_type_name="Product",
    )

    assert [p.target_entity_name for p in paths] == ["Product A", "Product B"]
    first = paths[0]
    assert [(s.entity_name, s.relationship_name) for s in first.steps] == [
        ("TSMC", "supplies"),
        ("Material A", "usedIn"),
        ("BOM A", "defines"),
        ("Product A", None),
    ]


def test_no_path_found_returns_empty_tuple() -> None:
    supplier = _entity("Isolated Supplier", "Supplier")
    entities_by_id = {supplier.entity_id: supplier}

    paths = find_paths_to_target_type(
        start_entity=supplier,
        entities_by_id=entities_by_id,
        edges=(),
        target_entity_type_name="Product",
    )
    assert paths == ()


def test_start_entity_matching_target_type_is_not_trivially_returned() -> None:
    # A "Product" asking about itself should not produce a zero-hop path;
    # only genuine outward traversal counts.
    product = _entity("Product A", "Product")
    entities_by_id = {product.entity_id: product}

    paths = find_paths_to_target_type(
        start_entity=product,
        entities_by_id=entities_by_id,
        edges=(),
        target_entity_type_name="Product",
    )
    assert paths == ()


def test_traversal_does_not_loop_forever_on_a_cycle() -> None:
    a = _entity("A", "Supplier")
    b = _entity("B", "Material")
    entities_by_id = {a.entity_id: a, b.entity_id: b}
    edges = (
        GraphEdge("supplies", a.entity_id, b.entity_id),
        GraphEdge("suppliedBy", b.entity_id, a.entity_id),
    )

    paths = find_paths_to_target_type(
        start_entity=a,
        entities_by_id=entities_by_id,
        edges=edges,
        target_entity_type_name="Product",
    )
    assert paths == ()


def test_traversal_never_invents_a_path_beyond_max_depth() -> None:
    entities = [_entity(f"E{i}", "Material") for i in range(10)]
    entities[-1] = _entity("Final Product", "Product")
    entities_by_id = {e.entity_id: e for e in entities}
    edges = tuple(
        GraphEdge("usedIn", entities[i].entity_id, entities[i + 1].entity_id)
        for i in range(len(entities) - 1)
    )

    paths = find_paths_to_target_type(
        start_entity=entities[0],
        entities_by_id=entities_by_id,
        edges=edges,
        target_entity_type_name="Product",
        max_depth=3,
    )
    assert paths == ()


def test_deterministic_ordering_is_stable_across_repeated_calls() -> None:
    supplier = _entity("TSMC", "Supplier")
    material_a = _entity("Material A", "Material")
    material_b = _entity("Material B", "Material")
    bom_a = _entity("BOM A", "BOM")
    bom_b = _entity("BOM B", "BOM")
    product_a = _entity("Product A", "Product")
    product_b = _entity("Product B", "Product")
    entities_by_id = {
        e.entity_id: e
        for e in (supplier, material_a, material_b, bom_a, bom_b, product_a, product_b)
    }
    # Edges listed out of "natural" order to prove sorting, not insertion
    # order, determines the result.
    edges = (
        GraphEdge("usedIn", material_b.entity_id, bom_b.entity_id),
        GraphEdge("defines", bom_b.entity_id, product_b.entity_id),
        GraphEdge("supplies", supplier.entity_id, material_b.entity_id),
        GraphEdge("supplies", supplier.entity_id, material_a.entity_id),
        GraphEdge("usedIn", material_a.entity_id, bom_a.entity_id),
        GraphEdge("defines", bom_a.entity_id, product_a.entity_id),
    )

    first = find_paths_to_target_type(
        start_entity=supplier,
        entities_by_id=entities_by_id,
        edges=edges,
        target_entity_type_name="Product",
    )
    second = find_paths_to_target_type(
        start_entity=supplier,
        entities_by_id=entities_by_id,
        edges=edges,
        target_entity_type_name="Product",
    )
    assert first == second
    assert [p.target_entity_name for p in first] == ["Product A", "Product B"]
