# CDD-010/CDD-012 Replay Remediation Authorization

Version: 1.0
Status: APPROVED FOR IMPLEMENTATION
Base: `ba59931de602e4cd66bb8edf8b2266b718b17073`

## Authority and governance amendment allowlist

- `architecture/INDEX.md`
- `architecture/released/v1.5/**`
- `scripts/verify_architecture_release.py`
- `docs/cdd/CDD-010-CDD-012-REPLAY-REMEDIATION-AUTHORIZATION.md`
- `docs/cdd/CDD-010-CDD-012-Replay-Execution-Contract-Clarification-and-Remediation-Report.md`

## Runtime recovery implementation and test allowlist

- `backend/pyproject.toml`
- `backend/app/runtime/engine.py`
- `backend/app/runtime/orchestration.py`
- `backend/app/runtime/persistence/contracts.py`
- `backend/app/runtime/persistence/crypto.py`
- `backend/app/runtime/persistence/repository.py`
- `backend/app/runtime/recovery.py`
- `backend/app/tests/test_authenticated_handoff_recovery.py`
- `backend/app/tests/test_resume_from_stage.py`
- `backend/app/tests/test_atomic_replay_creation.py`
- `backend/app/tests/test_execution_recovery.py`
- `backend/app/tests/test_execution_replay.py`
- `backend/app/tests/test_runtime_architecture.py`

No schema migration is authorized. Existing runtime tables and recovery linkage fields are
sufficient when replay admission uses a transaction-scoped advisory lock and one transaction.

## Preserved CDD-013 allowlist

The exact CDD-013 boundary published at
`docs/cdd/CDD-013-EXPANDED-CHANGED-FILE-AUTHORIZATION.md` remains controlling. Its partial work is
preserved in stash `CDD-013 partial implementation preserved before replay remediation` and must
not be reapplied until this remediation is merged to remote main.

All unlisted files are READ-ONLY. Capability business rules, canonical ontology, UI, deployment,
unrelated APIs, and additional persistence records are prohibited.

