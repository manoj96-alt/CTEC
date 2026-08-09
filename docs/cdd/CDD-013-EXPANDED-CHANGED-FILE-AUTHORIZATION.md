# CDD-013 — Expanded Changed-File Authorization

Version: 1.0
Status: APPROVED FOR IMPLEMENTATION
Base: `96e5ec10a34b7fbed5b2868330f6e2bb2bc875a4`

Only the paths below may change during the CDD-013 work cycle. The five existing review documents
are preserved and updated in place. All unlisted paths are READ-ONLY.

## Governance publication allowlist

- `architecture/INDEX.md` — MODIFY
- `architecture/released/v1.4/README.md` — CREATE
- `architecture/released/v1.4/PAS-001_Supplier_Risk_Product_API_and_Security_Contract_v1.0_FROZEN.md` — CREATE
- `architecture/released/v1.4/IDP-001_Provider_Neutral_OIDC_Identity_Validation_Contract_v1.0_FROZEN.md` — CREATE
- `architecture/released/v1.4/RFC-014_Cognitive_Capability_Integration_Handoff_and_Transaction_Policy_v1.3_FROZEN.md` — CREATE
- `architecture/released/v1.4/PMM-001_Runtime_Persistence_Role_Mapping_v1.2_FROZEN.md` — CREATE
- `architecture/released/v1.4/ECOM_Physical_Data_Model_v1_5.sql` — CREATE
- `architecture/released/v1.4/DEPENDENCY-MATRIX-v1.4.csv` — CREATE
- `architecture/released/v1.4/BASELINE-RECORD-v1.6_FROZEN.md` — CREATE
- `architecture/released/v1.4/ARCHITECTURE-CONSISTENCY-REPORT-v1.5_FROZEN.md` — CREATE
- `architecture/released/v1.4/ARCHITECTURE-DRIFT-REPORT-v1.5_FROZEN.md` — CREATE
- `architecture/released/v1.4/RELEASE-READINESS-REPORT-v1.5_FROZEN.md` — CREATE
- `architecture/released/v1.4/RELEASE-MANIFEST-v1.4.xlsx` — CREATE
- `scripts/verify_architecture_release.py` — MODIFY; recognize and validate Baseline v1.4.
- `docs/cdd/CDD-013-EXPANDED-CHANGED-FILE-AUTHORIZATION.md` — CREATE/MODIFY
- `docs/cdd/CDD-013-Supplier-Risk-Application-API-and-Security-Boundary-DRAFT.md` — MODIFY
- `docs/cdd/CDD-013-ARCHITECTURE-AND-CONTRACT-IMPACT-ASSESSMENT.md` — MODIFY
- `docs/cdd/CDD-013-ENDPOINT-AND-SCHEMA-SPECIFICATION.md` — MODIFY
- `docs/cdd/CDD-013-SECURITY-AND-AUTHORIZATION-ASSESSMENT.md` — MODIFY
- `docs/cdd/CDD-013-PREIMPLEMENTATION-GATE-REPORT.md` — MODIFY

## Original implementation boundary (25 paths)

The original sixteen production/configuration/documentation paths and nine test paths in the CDD
draft remain authorized, subject to PAS-001.

## Newly authorized implementation paths

- `backend/pyproject.toml` — MODIFY; add the reviewed JWT/JWKS dependency.
- `backend/requirements.txt` — MODIFY; preserve editable installation convention.
- `backend/app/api/supplier_risk/authentication.py` — CREATE; real provider-neutral OIDC/JWKS verifier.
- `backend/app/infrastructure/persistence/models/api_security_audit.py` — CREATE; seventh ORM record.
- `backend/app/infrastructure/persistence/models/__init__.py` — MODIFY; register the audit mapping.
- `backend/app/infrastructure/persistence/api_security_audit_repository.py` — CREATE; append/query/disposition contract.
- `backend/app/infrastructure/persistence/migrations/versions/0009_api_security_audit.py` — CREATE; table, indexes, immutability trigger, rollback.
- `backend/app/tests/test_oidc_authentication.py` — CREATE; cryptographic validation and JWKS behavior.
- `backend/app/tests/test_api_security_audit.py` — CREATE; append-only, retention, hold, fail-closed behavior.
- `backend/app/tests/test_api_security_audit_migration.py` — CREATE; upgrade/downgrade and integrity constraints.
- `backend/app/tests/test_decision_engine.py` — MODIFY; migration-head regression only.
- `backend/app/tests/test_governance_engine.py` — MODIFY; migration-head regression only.
- `backend/app/tests/test_knowledge_engine.py` — MODIFY; migration-head regression only.
- `backend/app/tests/test_persistence_integration.py` — MODIFY; migration-head regression only.

## Closure-only governance paths

- `docs/cdd/Closure-Gate-4-CDD-013-Application-API-and-Security-Boundary-Implementation-Report.md` — CREATE
- `docs/cdd/CDD-013-IMPLEMENTATION-EVIDENCE.md` — CREATE

No business entity, canonical attribute, canonical relationship, second orchestration path,
product UI, deployment layer, analytics store, or unrelated API is authorized.
