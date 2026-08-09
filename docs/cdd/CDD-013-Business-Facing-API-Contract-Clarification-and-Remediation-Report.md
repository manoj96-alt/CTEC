# CDD-013 — Business-Facing API Contract Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Authority base: `9d2ab3042f22e69b9d41d01fd0905cbb7cd73ec7`

## Decision

PAS-001 v1.1 is a backward-compatible additive clarification of `/api/v1/supplier-risk`. It
preserves every v1 operation and frozen supplier-risk semantic while adding the minimum
business-facing read and recovery-discovery fields required by CDD-014. Existing requests and
responses retain their meaning; unknown request fields remain rejected. No second API version is
required because no existing required field, enum meaning, authorization rule, or idempotency rule
changes.

## Resolved P0s

1. tenant-scoped, cursor-paginated work queue over existing runtime records;
2. explicit closed submission schema mapped field-for-field to `SupplierRiskRequest`;
3. explicit execution/terminal classification, governed result conditions, safe explanations, and
   reference-only traceability;
4. CDD-012-owned retry eligibility with attempt revision;
5. server-issued replay option references bound to tenant, attempt, stage, revision, and integrity;
6. BSP-001 public-browser Authorization Code + PKCE and memory-only token profile.

## Compatibility and boundaries

- Canonical PAS scopes are `supplier-risk:submit`, `supplier-risk:read`,
  `supplier-risk:evidence:read`, `supplier-risk:retry`, and `supplier-risk:replay`.
- The implementation accepts the new canonical replay scope at the product boundary and maps it to
  the existing CDD-012 `execution:replay` recovery authority internally; the old runtime scope is
  not exposed as an alternate product authority.
- Evidence content is never returned by ordinary result reads. Result references remain safe; any
  future evidence-content endpoint requires `supplier-risk:evidence:read` and a separate contract.
- Replay option references are opaque authenticated server values; they are not persistence IDs or
  checkpoint payloads and are revalidated on submission.
- No schema migration, search store, analytics projection, orchestration, business rule, or tenant
  selection is introduced.

## Validation and rollback

The API release must pass the exact validations in the CDD-014 package, all CDD-010–013 regressions,
OpenAPI compatibility, tenant non-disclosure, authorization, concurrency, idempotency, audit, and
changed-file checks. Rollback reverts only the additive API/repository implementation; existing v1
clients and runtime data remain valid.
