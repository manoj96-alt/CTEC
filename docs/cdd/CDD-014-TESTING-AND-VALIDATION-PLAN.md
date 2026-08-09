# CDD-014 — Testing and Validation Plan

Version: 1.0

## Test layers

- **Unit:** view-model mappings, safe errors, request IDs/idempotency, polling/backoff, scope-aware
  presentation, redaction, URL validation, and stale-response rejection.
- **Component:** forms, error summary, queue, attempts, timeline, recommendation, evidence,
  conditions, retry/replay dialogs, session states, and responsive rendering.
- **Contract:** corrected committed/runtime OpenAPI against the client, exact enums/required fields,
  API version, safe errors, pagination, and no trusted metadata in requests.
- **Integration/E2E:** successful submission; validation; duplicate/concurrent submission; execution,
  attempts, stages, and result; all standings/terminal classes; gated versus failed; evidence scope;
  retry/replay and stale eligibility; auth expiry; `401/403/404/409/413/429/503`; unsupported version;
  network interruption; refresh/deep link; pagination; tenant/authority injection attempts.
- **Security:** no token or sensitive response persistence/logging/URL exposure; XSS payloads render
  as text; redirect validation; tenant-safe not found; dependency, lockfile, secret, and CSP review.
- **Accessibility:** automated WCAG checks plus keyboard, focus, VoiceOver/NVDA, contrast, 200% zoom,
  320 px reflow, reduced motion, responsive table/timeline/dialog manual evidence.
- **Regression:** frontend lint, format, typecheck, unit coverage, build, backend OpenAPI/schema tests,
  CDD-010 through CDD-013 protected jobs, container checks, architecture release verifier, changed-file
  authorization, and `git diff --check`.

## Required evidence

Record exact commands, versions, browser/assistive-technology matrix, pass/fail counts, coverage,
OpenAPI checksum, dependency audit, screenshots only where they contain no sensitive data, changed
paths, and residual risks. No production test may use a mock in place of CDD-013 for contract or E2E
acceptance; unit/component tests may use typed fixtures.
