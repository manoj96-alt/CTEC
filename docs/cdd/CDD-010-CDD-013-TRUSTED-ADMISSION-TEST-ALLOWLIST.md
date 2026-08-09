# CDD-010 / CDD-013 — Trusted Admission Test Allowlist

Version: 1.0
Status: APPROVED FOR REMEDIATION

Authorized test paths are exactly those enumerated by the submission-contract, integration, and persistence/recovery allowlists. They may cover canonical serialization, direct/nested/aliased injection, clock ownership and failure, concurrency, rollback, restart, retry, replay, tenant/version isolation, redaction, OpenAPI, and CDD-010–CDD-013 regression. No production test doubles or unrelated fixtures are authorized.
