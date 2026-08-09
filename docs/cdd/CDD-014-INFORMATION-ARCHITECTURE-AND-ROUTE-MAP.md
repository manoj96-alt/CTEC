# CDD-014 — Information Architecture and Route Map

Version: 1.0

## Hierarchy

```text
Supplier Risk
├── Work Queue                     /supplier-risk
├── New Assessment                 /supplier-risk/new
└── Execution Overview             /supplier-risk/executions/{logicalExecutionId}
    ├── Progress                   ?view=progress
    ├── Recommendation             ?view=recommendation
    ├── Evidence & Provenance      ?view=evidence
    └── Attempt detail             /attempts/{executionId}
```

Retry and replay are modal/step workflows launched from the execution overview; they do not create
bookmarkable URLs containing reasons, tokens, checkpoint data, or authority information.

## Navigation rules

- Primary navigation adds one “Supplier Risk” entry for authenticated users with at least one PAS
  capability; server denial remains authoritative.
- Breadcrumbs: Supplier Risk → logical execution short identifier → current view/attempt.
- Titles: `Supplier Risk`, `New supplier-risk assessment`, and
  `Supplier-risk execution {safe-short-id} · CTEC`.
- Deep links contain only stable logical/attempt identifiers. After authentication renewal, return
  only to a validated same-origin path and refetch.
- Access denied, tenant-safe not found, rate limited, and unavailable render as route-level states;
  no cross-tenant detail is disclosed.
- Technical attempt detail is subordinate to the logical execution. Business users see the current
  attempt first and may inspect history without seeing opaque handoffs.

The work-queue route remains blocked until a frozen list endpoint exists.
