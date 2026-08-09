# CDD-014 — Frontend Implementation and Test Allowlist

Version: 1.0
Status: AUTHORIZED AFTER CDD-013 REMEDIATION VALIDATION

## Production CREATE

- `frontend/app/auth/callback/page.tsx`
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
- `frontend/lib/auth/browser-session.ts`
- `frontend/lib/auth/config.ts`
- `frontend/lib/supplier-risk/api-client.ts`
- `frontend/lib/supplier-risk/contracts.ts`
- `frontend/lib/supplier-risk/mappers.ts`
- `frontend/lib/supplier-risk/polling.ts`
- `frontend/lib/supplier-risk/validation.ts`

## Production MODIFY

- `frontend/app/layout.tsx`
- `frontend/app/globals.css`
- `frontend/components/site-shell.tsx`
- `frontend/next.config.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.json`
- `frontend/vitest.config.ts`
- `frontend/tests/setup.ts`
- `README.md`

## Tests CREATE

- `frontend/tests/browser-session.test.ts`
- `frontend/tests/supplier-risk-api-client.test.ts`
- `frontend/tests/supplier-risk-contract.test.ts`
- `frontend/tests/supplier-risk-form.test.tsx`
- `frontend/tests/supplier-risk-execution.test.tsx`
- `frontend/tests/supplier-risk-recommendation.test.tsx`
- `frontend/tests/supplier-risk-recovery.test.tsx`
- `frontend/tests/supplier-risk-security.test.tsx`
- `frontend/tests/supplier-risk-accessibility.test.tsx`

## Governance and closure MODIFY/CREATE

- the fourteen CDD-014 preimplementation documents;
- `docs/cdd/Closure-Gate-5-CDD-014-Supplier-Risk-Business-Workflow-and-User-Experience-Implementation-Report.md`.

Only `oidc-client-ts` and `axe-core`/`vitest-axe` may be added, solely for BSP-001 session behavior
and automated accessibility validation. No BFF, alternate API, persistence, analytics, deployment,
or business-rule artifact is authorized. All unlisted paths are READ-ONLY.
