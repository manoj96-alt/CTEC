import ast
from pathlib import Path


def test_integration_package_has_no_api_startup_or_configuration_imports() -> None:
    root = Path(__file__).parents[1] / "integration"
    prohibited = {"app.api", "app.main", "app.core.config"}
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        imports = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(any(value.startswith(item) for item in prohibited) for value in imports)


def test_integration_package_contains_only_authorized_modules() -> None:
    root = Path(__file__).parents[1] / "integration"
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*.py")}
    assert actual == {
        "__init__.py",
        "contracts.py",
        "supplier_risk_policy.py",
        "dependencies.py",
        "pipeline.py",
        "adapters/__init__.py",
        "adapters/erm.py",
        "adapters/srm.py",
        "adapters/asm.py",
        "adapters/krm.py",
        "adapters/drm.py",
        "adapters/grm.py",
    }
