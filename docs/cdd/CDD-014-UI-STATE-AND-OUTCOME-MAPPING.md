# CDD-014 — UI State and Outcome Mapping

Version: 1.0

## Separation model

| Dimension | Source | Presentation rule |
|---|---|---|
| Execution status | CDD-013/ESM | Accepted, Executing, Completed, Failed; never derived from recommendation |
| Business outcome | CDD-013 terminal classification/result | Approved, conditionally approved, rejected, indeterminate, gated as explicitly returned |
| Stage status | CDD-013 stage response | Per-stage status and safe code; not a business outcome |
| Technical failure | CDD-013 safe terminal classification/diagnostic | Separate failure panel; no rejection language |
| Recommendation | GRM value transported by CDD-013 | Render exact value and explanation/reference fields; no simplification |
| Permitted next action | CDD-013 actionability, standing, conditions, and recovery eligibility | Never inferred from HTTP or client role alone |

## Minimum state model

- **Server-authoritative:** execution, attempts, stages, result, eligibility, permitted references.
- **URL/navigation:** logical and attempt identifiers, selected view, opaque pagination cursor.
- **Temporary form:** unsent fields, validation display, confirmation state, mutation request ID.
- **Authentication/session:** provider session handle and minimum presentation claims supplied by a
  governed browser session integration; never AuthorityContext.
- **Presentation-only:** dialog state, expanded rows, live-announcement text, non-sensitive display
  preference.

The current API cannot provide all required business-outcome and next-action dimensions. Until the
P0 response fields are frozen, the frontend must not synthesize the missing mapping.
