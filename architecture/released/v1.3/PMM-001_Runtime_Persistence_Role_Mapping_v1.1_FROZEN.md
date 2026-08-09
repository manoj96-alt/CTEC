# PMM-001 — Runtime Persistence Role Mapping

Version: 1.1  
Status: FROZEN  
Supersedes: PMM-001 v1.0  
Approval: CDD-012 bounded governance decision

PMM-001 v1.0 remains controlling for all existing tables. Physical Model v1.4 adds exactly six non-canonical runtime tables:

| Table | Role | Authorized writer |
|---|---|---|
| `runtime_executions` | Immutable admission identity plus controlled technical current-state projection | CDD-012 runtime repository |
| `runtime_stages` | Immutable attempt/checkpoint history | CDD-012 runtime repository |
| `runtime_handoffs` | Immutable protected handoff record | CDD-012 runtime repository |
| `runtime_artifact_references` | Immutable evidence/provenance/capability/decision reference | CDD-012 runtime repository |
| `runtime_results` | Immutable terminal result | CDD-012 runtime repository |
| `runtime_recovery_attempts` | Immutable replay/retry authorization and lineage | CDD-012 recovery repository |

Runtime records are implementation metadata, not CEO entities or canonical outcomes. Business meaning remains in capability-owned records. UPDATE is permitted only for the controlled technical state/revision fields of `runtime_executions`; all other rows are append-only. Tenant-scoped retention/legal-hold deletion is the sole governed deletion exception.
