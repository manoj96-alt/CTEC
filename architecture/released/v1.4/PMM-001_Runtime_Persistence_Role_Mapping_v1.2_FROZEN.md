# PMM-001 — Runtime Persistence Role Mapping

Version: 1.2  
Status: FROZEN  
Supersedes: PMM-001 v1.1  
Approval: CDD-013 bounded governance decision

PMM-001 v1.1 remains controlling for all existing tables. Physical Model v1.5 adds exactly one
non-canonical application-security table:

| Table | Role | Authorized writer |
|---|---|---|
| `api_security_audit_events` | Immutable API admission, authorization, disclosure, and abuse-control evidence | CDD-013 API security audit repository |

The record is implementation metadata, not a CEO entity or canonical outcome. It is append-only;
ordinary application UPDATE/DELETE is prohibited. Tenant-scoped, auditable disposition after
retention expiry and legal-hold clearance is the sole deletion exception. The accountable data
owner is the ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`).
