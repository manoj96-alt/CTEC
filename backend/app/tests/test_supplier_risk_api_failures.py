from fastapi.testclient import TestClient

from app.api.supplier_risk.schemas import ErrorResponse
from app.main import create_app


def test_safe_error_contract_excludes_security_internals() -> None:
    assert set(ErrorResponse.model_fields) == {"code", "message", "correlation_id", "retryable"}
    assert "token" not in ErrorResponse.model_fields
    assert "claims" not in ErrorResponse.model_fields
    assert "stack_trace" not in ErrorResponse.model_fields


def test_validation_error_uses_safe_stable_problem_shape() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/api/v1/supplier-risk/assessments", json={})
    assert response.status_code in {401, 422}
    assert set(response.json()) == {"code", "message", "correlation_id", "retryable"}
    assert not any(value in response.text.lower() for value in ("bearer ", "claims", "traceback"))
