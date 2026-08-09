from dataclasses import asdict

import pytest
from pydantic import ValidationError

from app.api.supplier_risk.schemas import SupplierRiskAssessmentRequest
from app.tests.test_supplier_risk_pipeline import build_request


def test_submission_schema_is_closed_and_maps_governed_request() -> None:
    value = asdict(build_request())
    parsed = SupplierRiskAssessmentRequest.model_validate(value)
    assert parsed.context_id == value["context_id"]
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "tenant_id": "forbidden"})
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "recommendation": "APPROVED"})


def test_submission_schema_enforces_scores_and_collection_bounds() -> None:
    value = asdict(build_request())
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "identity_score": 2})
    with pytest.raises(ValidationError):
        SupplierRiskAssessmentRequest.model_validate({**value, "supplier_names": []})
