# CDD-012 — Trusted Admission Persistence and Recovery Allowlist

Version: 1.0
Status: APPROVED FOR REMEDIATION

- `backend/app/runtime/persistence/repository.py` — MODIFY; atomically persist and recover the admitted payload and original timestamp using existing execution and initial-handoff records.
- `backend/app/tests/test_runtime_persistence.py` — MODIFY.
- `backend/app/tests/test_runtime_recovery.py` — MODIFY if replay timestamp invariants require it.
- `backend/app/tests/test_supplier_risk_api_restart.py` — MODIFY.

Repository inspection established that no migration is required: `runtime_executions.payload_fingerprint` stores the canonical client fingerprint; `runtime_executions.admitted_at` stores the original trusted timestamp; and the protected initial `runtime_handoffs` record stores the admitted payload with its existing content hash and contract binding. No new table, field, index, or projection is authorized.
