# CDD-013 — API Contract Implementation and Test Allowlist

Version: 1.0
Status: AUTHORIZED AFTER PAS-001 v1.1 PUBLICATION

## Production MODIFY

- `backend/app/api/supplier_risk/router.py`
- `backend/app/api/supplier_risk/schemas.py`
- `backend/app/application/supplier_risk_api.py`
- `backend/app/runtime/persistence/contracts.py`
- `backend/app/runtime/persistence/repository.py`

## Tests MODIFY

- `backend/app/tests/test_supplier_risk_api_contracts.py`
- `backend/app/tests/test_supplier_risk_api_commands.py`
- `backend/app/tests/test_supplier_risk_api_queries.py`
- `backend/app/tests/test_supplier_risk_api_failures.py`
- `backend/app/tests/test_supplier_risk_api_security.py`
- `backend/app/tests/test_runtime_architecture.py`

## Tests CREATE

- `backend/app/tests/test_supplier_risk_api_work_queue.py`
- `backend/app/tests/test_supplier_risk_api_submission_schema.py`
- `backend/app/tests/test_supplier_risk_api_recovery_options.py`

No migration, new table, business-capability implementation, runtime orchestration, authentication
verifier, configuration, dependency, startup, UI, or deployment change is authorized. Existing
runtime tables and repository sessions must supply all projections. All unlisted paths are
READ-ONLY.
