# CDD-014 — Exact Changed-File Authorization

Version: 1.0 PROPOSED

Status: INACTIVE WHILE PREIMPLEMENTATION GATE IS BLOCKED

All paths not listed are READ-ONLY. DELETE is not authorized. This list must be revised atomically
after the P0 contract/session remediation selects the client-generation, OIDC, accessibility, and
E2E strategy; no implementation may begin from this provisional list.

## Production — proposed CREATE

- `frontend/app/supplier-risk/page.tsx`
- `frontend/app/supplier-risk/new/page.tsx`
- `frontend/app/supplier-risk/executions/[logicalExecutionId]/page.tsx`
- `frontend/app/supplier-risk/executions/[logicalExecutionId]/attempts/[executionId]/page.tsx`
- `frontend/components/supplier-risk/assessment-form.tsx`
- `frontend/components/supplier-risk/assessment-table.tsx`
- `frontend/components/supplier-risk/attempt-history.tsx`
- `frontend/components/supplier-risk/stage-timeline.tsx`
- `frontend/components/supplier-risk/recommendation-panel.tsx`
- `frontend/components/supplier-risk/reference-list.tsx`
- `frontend/components/supplier-risk/retry-dialog.tsx`
- `frontend/components/supplier-risk/replay-dialog.tsx`
- `frontend/components/supplier-risk/route-state.tsx`
- `frontend/components/supplier-risk/status-summary.tsx`
- `frontend/lib/supplier-risk/api-client.ts`
- `frontend/lib/supplier-risk/contracts.ts`
- `frontend/lib/supplier-risk/mappers.ts`
- `frontend/lib/supplier-risk/polling.ts`
- `frontend/lib/supplier-risk/session.ts`
- `frontend/lib/supplier-risk/validation.ts`

## Production — proposed MODIFY

- `frontend/app/layout.tsx` — bounded metadata/session integration only.
- `frontend/app/globals.css` — accessible supplier-risk tokens/layout only.
- `frontend/components/site-shell.tsx` — role-aware navigation only.
- `frontend/next.config.ts` — security headers/public configuration only if selected authority requires.
- `frontend/package.json` and `frontend/package-lock.json` — only explicitly approved client/session/
  accessibility/E2E dependencies after governance.
- `frontend/tsconfig.json` and `frontend/vitest.config.ts` — test/path configuration only.

## Tests — proposed CREATE

- `frontend/tests/supplier-risk-api-client.test.ts`
- `frontend/tests/supplier-risk-contract.test.ts`
- `frontend/tests/supplier-risk-form.test.tsx`
- `frontend/tests/supplier-risk-execution.test.tsx`
- `frontend/tests/supplier-risk-recommendation.test.tsx`
- `frontend/tests/supplier-risk-recovery.test.tsx`
- `frontend/tests/supplier-risk-security.test.tsx`
- `frontend/tests/supplier-risk-accessibility.test.tsx`
- `frontend/e2e/supplier-risk.spec.ts`

## Governance/evidence — proposed CREATE or MODIFY

- All `docs/cdd/CDD-014-*.md` files in this reviewed package.
- `README.md` only for bounded developer/run documentation after implementation approval.
- `backend/app/tests/test_supplier_risk_api_contracts.py` only if the approved CDD-013 remediation
  explicitly authorizes its contract assertions; otherwise READ-ONLY.

## Prohibited

All backend production, migration, runtime, capability, persistence, deployment, ontology,
architecture-release, and unrelated frontend paths are prohibited unless a separately reviewed
contract-remediation work order expressly authorizes them.
