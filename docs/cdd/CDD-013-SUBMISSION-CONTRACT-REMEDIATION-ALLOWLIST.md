# CDD-013 — Submission Contract Remediation Allowlist

Version: 1.0
Status: APPROVED FOR REMEDIATION

- `backend/app/api/supplier_risk/schemas.py` — MODIFY; remove caller-owned `received_at` and preserve closed validation.
- `backend/app/application/supplier_risk_api.py` — MODIFY; provide the trusted admission-payload builder after authentication and authorization.
- `backend/app/tests/test_supplier_risk_api_submission_schema.py` — MODIFY.
- `backend/app/tests/test_supplier_risk_api_commands.py` — MODIFY.
- `backend/app/tests/test_supplier_risk_api_contracts.py` — MODIFY if OpenAPI assertions require it.
- `backend/app/tests/test_supplier_risk_api_security.py` — MODIFY for injection/redaction coverage.
- `backend/app/tests/test_supplier_risk_api_restart.py` — MODIFY for committed timestamp reuse.

No other API, controller, business-rule, authentication, or product contract path is authorized.
