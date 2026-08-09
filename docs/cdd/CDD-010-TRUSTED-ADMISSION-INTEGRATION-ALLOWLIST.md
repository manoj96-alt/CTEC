# CDD-010 — Trusted Admission and Integration Allowlist

Version: 1.0
Status: APPROVED FOR REMEDIATION

- `backend/app/runtime/contracts.py` — MODIFY; add a neutral trusted admission-payload builder contract.
- `backend/app/runtime/execution_store.py` — MODIFY; return the committed admitted payload and timestamp.
- `backend/app/runtime/invocation.py` — MODIFY; compare the canonical client-payload fingerprint.
- `backend/app/runtime/engine.py` — MODIFY; execute only the payload returned by atomic admission.
- `backend/app/tests/test_runtime_invocation.py` — MODIFY.
- `backend/app/tests/test_runtime_engine.py` — MODIFY.
- `backend/app/tests/test_runtime_concurrency.py` — MODIFY.

The runtime remains opaque to supplier-risk meaning. It may invoke a trusted builder with the server admission timestamp but may not inspect or transform the payload.
