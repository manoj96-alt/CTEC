# CDD-014 — Business Journey Specification

Version: 1.0

All journeys use keyboard-operable controls, visible focus, programmatic labels, focus placement on
the page heading or first invalid field, and polite live announcements for asynchronous state.

| Journey | Role/scope and entry | Screens and CDD-013 calls | States and actions | Recovery and audit sensitivity |
|---|---|---|---|---|
| Start assessment | Analyst; `supplier-risk:submit`; New assessment | Form → `POST /assessments` | Validate only frozen schema; confirm summary; submit once | Preserve non-sensitive form state in memory; submission is audit-sensitive |
| Correct validation | Submitter; invalid form/API `400/422` | Form; no call until client-valid | Inline summary and field errors; never invent defaults | Focus error summary, then field; retain entered non-sensitive values |
| Prevent duplicate | Submitter | Form; one generated request ID used as Idempotency-Key | Disable while pending; repeat uses same key/body | Conflict shows safe guidance; never silently generate a second request |
| View after submission | Submitter/read user | Redirect to execution overview; `GET /executions/{id}` | Loading, accepted, executing, terminal, safe error | URL stores logical ID only; refresh refetches server state |
| Track stages | Read user | Overview/stages; `GET attempts`, then `GET stages` | Ordered ERM→GRM timeline; no handoff content | Poll with backoff while active; stop when terminal/hidden tab |
| Completed recommendation | Read user | Result; `GET /result` | Exact recommendation, standing, actionability, next action | `202` remains pending; do not infer from HTTP alone |
| Conditional approval | Read user | Recommendation | Show all returned conditions and verified status; no action if unverified | Blocked until CDD-013 exposes conditions |
| Rejected/gated | Read user | Overview/result | Keep business outcome separate from successful technical execution | No retry unless server declares eligible |
| Indeterminate | Read user | Overview/result | Label insufficient/conflicting evidence; never call it rejected | Present permitted next action only from server contract |
| Technical failure | Read user; retry scope for mutation | Overview | Safe diagnostic only; visually distinct from business result | Offer retry only from server eligibility |
| Evidence/provenance | Authorized reader | Evidence view; result/reference endpoint | Show permitted references, not protected payloads | Access and disclosure are audit-sensitive; blocked pending contract |
| Retry | Retry user; `supplier-risk:retry` | Confirmation → `POST /retry` | Explain retained logical execution; reason; single submit | Stale `409/403` wins; show original and returned attempt IDs |
| Privileged replay | Recovery operator | Replay dialog → `POST /replay` | Server options only, required reason, deliberate confirmation | Never construct checkpoint metadata; audit-sensitive |
| Expired authentication | Any | Current page → governed reauthentication | Clear sensitive memory, preserve return URL without secrets | Refetch all state after renewed session |
| Rate/conflict/unavailable | Any | Current operation | Safe message for `409`, `429`, `503`; bounded retry when allowed | Respect Retry-After if governed; no tight loop |
| Return after refresh | Read user | Deep link → execution/status calls | Reconstruct only from URL and server | Not-found is tenant-safe; do not use cached complete responses |

PAS-001 v1.1 supplies the tenant-safe paginated work queue. Empty, loading, error, pagination, and
refresh behavior use the same protected-read rules.
