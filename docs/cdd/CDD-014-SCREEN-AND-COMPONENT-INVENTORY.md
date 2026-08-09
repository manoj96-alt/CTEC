# CDD-014 — Screen and Component Inventory

Version: 1.0

| Screen | Minimum components | Key accessible behavior |
|---|---|---|
| Work queue | `AssessmentTable`, pagination, empty/error state | Caption, sortable-state text if authorized, row links, responsive cards below table breakpoint |
| New assessment | `AssessmentForm`, error summary, confirmation | Native labels/descriptions, field errors, no business defaults |
| Execution overview | `ExecutionSummary`, `AttemptHistory`, tab navigation | Heading focus, current attempt stated in text |
| Stage progress | `StageTimeline`, `StageStatus` | Ordered list, status text/icons, polite live updates, reduced motion |
| Recommendation | `RecommendationPanel`, `OutcomeBadge`, `ActionabilityPanel`, `ConditionList` | Outcome and actionability separated; conditions never hidden |
| Evidence/provenance | `ReferenceList`, disclosure state | Reference-only rendering, no unsafe HTML, scope-safe denial |
| Retry workflow | `RetryDialog`, reason field, confirmation summary | Focus trap/restore, destructive-style deliberate action |
| Replay workflow | `ReplayDialog`, server option list, reason, original/new attempt summary | Privileged warning, no client checkpoint entry |
| Route states | `AccessDenied`, `TenantSafeNotFound`, `RateLimited`, `Unavailable`, `SessionExpired` | Correct heading, recovery action, no diagnostic leakage |

Shared components: `SupplierRiskShell`, `Breadcrumbs`, `StatusSummary`, `SafeProblem`, `LoadingState`,
`EmptyState`, `Pagination`, and `LiveRegion`. Components receive presentation view models only and
contain no API calls or recommendation rules.
