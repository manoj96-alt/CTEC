from dataclasses import asdict

import pytest
from pydantic import ValidationError

from app.api.supplier_risk.schemas import SupplierRiskAssessmentRequest
from app.tests.test_supplier_risk_pipeline import build_request


def external_request() -> dict[str, object]:
    value = asdict(build_request())
    for observation in value["observations"]:
        observation.pop("received_at")
    return value


def test_submission_schema_is_closed_and_maps_governed_request() -> None:
    value = external_request()
    parsed = SupplierRiskAssessmentRequest.model_validate(value)
    assert parsed.context_id == value["context_id"]
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "tenant_id": "forbidden"})
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "recommendation": "APPROVED"})


def test_submission_schema_enforces_scores_and_collection_bounds() -> None:
    value = external_request()
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "identity_score": 2})
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "supplier_names": []})


@pytest.mark.parametrize("name", ["received_at", "receivedAt", "trusted_received_at"])
def test_submission_schema_rejects_trusted_timestamp_injection(name: str) -> None:
    value = external_request()
    observations = value["observations"]
    assert isinstance(observations, (list, tuple))
    assert isinstance(observations[0], dict)
    observations[0][name] = "2026-01-01T00:00:00Z"
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate(value)
