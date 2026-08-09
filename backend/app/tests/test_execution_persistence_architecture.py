from pathlib import Path


def test_runtime_persistence_remains_application_boundary_neutral() -> None:
    root = Path(__file__).parents[1] / "runtime" / "persistence"
    text = "\n".join(path.read_text() for path in root.glob("*.py"))
    assert "fastapi" not in text.lower()
    assert "app.api" not in text
    assert "supplier_risk_policy" not in text
