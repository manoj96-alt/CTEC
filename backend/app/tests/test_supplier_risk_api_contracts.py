from app.main import create_app


def test_openapi_has_bounded_supplier_risk_contracts() -> None:
    schema = create_app().openapi()
    assert {
        "/api/v1/supplier-risk/assessments",
        "/api/v1/supplier-risk/executions/{execution_id}",
        "/api/v1/supplier-risk/executions/{logical_execution_id}/attempts",
        "/api/v1/supplier-risk/executions/{logical_execution_id}/attempts/{execution_id}/stages",
        "/api/v1/supplier-risk/executions/{logical_execution_id}/result",
        "/api/v1/supplier-risk/executions/{logical_execution_id}/retry",
        "/api/v1/supplier-risk/executions/{logical_execution_id}/replay",
    } <= set(schema["paths"])
    assert "securitySchemes" in schema["components"]
