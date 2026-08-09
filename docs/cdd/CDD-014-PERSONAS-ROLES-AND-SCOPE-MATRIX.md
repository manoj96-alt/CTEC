# CDD-014 — Personas, Roles, and Scope Matrix

Version: 1.0

## Personas

| Persona | Business need | Authority source |
|---|---|---|
| Supply-chain analyst | Submit and monitor supplier-risk assessments | Validated OIDC identity plus PAS scopes |
| Supply-chain decision user | Read governed recommendations and permitted references | Validated identity plus read/evidence permission |
| Recovery operator | Request privileged replay after reviewing server-authorized options | `execution:replay` plus `EXECUTION_RECOVERY_OPERATOR` |
| Read-only reviewer | Review status and results without mutation | `supplier-risk:read` |

Personas are presentation aids, not new roles or authorization authorities.

## Canonical scope matrix

| UI capability | PAS-001 authority | Visible behavior | Server remains authoritative |
|---|---|---|---|
| Submit assessment | `supplier-risk:submit` | Show enabled form when present; otherwise explain unavailable action | Yes |
| Read execution, attempts, stages, result | `supplier-risk:read` | Show links and views when present | Yes |
| Read evidence/provenance | `supplier-risk:evidence:read` for protected content; ordinary read returns safe references only | Show only server-permitted references/content | Yes |
| Retry | `supplier-risk:retry` plus server eligibility | Show only when server reports eligible; confirm before send | Yes |
| Replay | `execution:replay` plus `EXECUTION_RECOVERY_OPERATOR` and server options | Privileged workflow with reason and confirmation | Yes |

The initiating request's uppercase labels do not exist as frozen scope strings. Controls may be
hidden or disabled for usability, but this never constitutes authorization. A `403` always wins over
client state; `404` never confirms cross-tenant existence.
