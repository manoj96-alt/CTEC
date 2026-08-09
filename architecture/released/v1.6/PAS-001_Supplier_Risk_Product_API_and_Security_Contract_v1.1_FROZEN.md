# PAS-001 — Supplier Risk Product API and Security Contract

Version: 1.1
Status: FROZEN
Supersedes: PAS-001 v1.0
Owner: ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`)

PAS-001 v1.1 preserves every v1.0 rule and adds only the following backward-compatible contracts.

## Canonical product scopes

`supplier-risk:submit`, `supplier-risk:read`, `supplier-risk:evidence:read`,
`supplier-risk:retry`, and `supplier-risk:replay` are the only product scope strings. Replay also
requires `EXECUTION_RECOVERY_OPERATOR`. The application boundary maps validated product replay
authority to CDD-012 recovery authority; callers never submit runtime AuthorityContext.

## Work queue

`GET /api/v1/supplier-risk/executions?cursor&limit&status` requires `supplier-risk:read`. Tenant is
derived only from the validated principal. Results are ordered by `admitted_at DESC,
logical_execution_id DESC`; cursor is an opaque/stable offset token for this bounded MVP. `limit` is
1–100, default 25. The optional `status` filter accepts only exact ESM states. Each item contains
logical/current attempt references, a safe subject summary, submission and last-updated timestamps,
execution status, current/terminal stage, terminal classification when present, and boolean
retry/replay indicators. Empty results are `200`; invalid filters `400`; auth and abuse behavior
inherits v1.0. No evidence content or sensitive diagnostics are returned.

## Closed submission

The request maps exactly to CIM-001 `SupplierRiskRequest`: names, source object IDs, enterprise and
semantic candidates, context/material/facility-or-region IDs, effective UTC time, governed source
observations, supplier eligibility, six confidence scores, policy identifiers/versions/rule,
optional Acceptance Evidence reference, conditions, verified conditions, and exceptional-policy
indicator. Unknown fields and caller-supplied tenant/principal/roles/scopes/AuthorityContext,
execution state, outcomes, recommendations, server timestamps, recovery metadata, persistence
records, or unrestricted evidence are rejected. Strings are trimmed and bounded to 1,000
characters; arrays to 100 entries; scores are finite `[0,1]`; identifiers are UUID; timestamps are
timezone-aware; observations and eligibility use the closed CIM enums and fields.

## Result and recovery discovery

Execution/result responses explicitly carry execution and attempt state, terminal flag,
classification (`IN_PROGRESS`, `APPROVED`, `CONDITIONALLY_APPROVED`, `REJECTED`, `INDETERMINATE`,
`BUSINESS_GATED`, `TECHNICAL_FAILURE`), safe diagnostic, recommendation, standing, actionability,
conditions and verification, safe explanation, produced-record, evidence/provenance/policy/decision
references, and contract version where available from the governed execution envelope. Missing
values remain absent; the API does not reconstruct them.

`GET /executions/{logical}/retry-eligibility` requires `supplier-risk:retry` and returns eligible,
governing attempt, stable reason, safe constraint, attempt revision, and retry action. CDD-012 owns
the determination; stale revision is rejected on mutation.

`GET /executions/{logical}/replay-options` requires `supplier-risk:replay` and recovery role. It
returns only authenticated opaque option reference, safe stage label, source attempt, checkpoint
time, eligibility/reason, and revision. `POST /replay` accepts that option plus bounded reason and
revalidates tenant, authority, integrity, stage, and revision. Fabricated/stale/cross-tenant values
return tenant-safe denial/conflict without protected detail.

Evidence content, tokens, checkpoint payloads, cryptographic material, SQL, handoffs, audit records,
and persistence internals remain prohibited.

## Compatibility

All changes are additive within API v1. Existing v1 requests and responses retain their original
meaning. New optional response fields may be ignored by old clients. Closed submission validation
formalizes the already-governed CIM payload and rejects data that was never authorized. Silent
coercion, downgrade, or semantic reinterpretation remains prohibited.
