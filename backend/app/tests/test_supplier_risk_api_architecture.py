import ast
from pathlib import Path


def test_router_does_not_import_orm_or_capability_services() -> None:
    path = Path(__file__).parents[1] / "api" / "supplier_risk" / "router.py"
    tree = ast.parse(path.read_text())
    imports = [
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    ]
    assert not any("persistence.models" in value or "domain." in value for value in imports)
