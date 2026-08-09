# CDD-013 — Architecture and Contract-Impact Assessment

Version: 1.0

Status: APPROVED — P0 RESOLVED

PAS-001 v1.0, IDP-001 v1.0, RFC-014 v1.3, PMM-001 v1.2, and Physical Model v1.5 resolve the
identified authority gaps without changing canonical or capability semantics.

Baseline: `96e5ec10a34b7fbed5b2868330f6e2bb2bc875a4`

## Executive finding

CDD-013 is architecturally bounded but not implementation-authorized. The runtime, business flow,
durable records, replay role/scope, and product-access boundary exist. The missing authority is one
cohesive product API/security profile; ordinary HTTP schema design is otherwise fully specifiable.

## P0 — consolidated authority gap

PAD-001 v1.5 defines PAC-001 through PAC-006 but does not assign supplier-risk assessment to one
protocol or define a supplier-risk product profile. PAD/EIC expressly leave authentication and
authorization implementation outside their scope. RSP-001 defines privileged replay authority but
not ordinary submit/read roles, tenant concealment, result disclosure, authentication trust source,
rate limiting, payload limits, or HTTP retry/replay contracts.

Publishing endpoints without that authority would make engineering decide externally visible
security and protocol semantics. The minimum remedy is one PAS-001 or PAD clarification covering:

- supplier-risk submission/result/history/execution protocol mapping;
- trusted identity verifier ownership and claims-to-AuthorityContext derivation;
- exact command/read/retry/replay permissions and tenant binding;
- permitted evidence/provenance/policy reference disclosure and redaction;
- API/idempotency/version/error/HTTP compatibility;
- rate, request-size, audit, and abuse-control minimums.

## P1 — implementation impacts, not separate governance blockers

1. CDD-012 exposes admission, snapshot, checkpoint, result, retention, and replay-authorization
   primitives but lacks tenant-scoped logical-execution/history/stage/reference query ports. CDD-013
   explicitly authorizes additive repository projections; no schema change is required.
2. Retry/replay need an application service to validate PAS-001 permissions, select a CDD-012
   checkpoint, create the new request/attempt, and call the existing runtime. This is orchestration
   of existing runtime services, not a second cognitive orchestration path.
3. Existing `main.py` has system routes and request correlation only. CDD-013 must register one
   router and trusted security dependencies without changing capability composition.
4. Existing settings have no approved authentication/rate/payload controls. Only non-secret,
   fail-closed settings may be added after PAS-001.

## Contract impact

| Existing authority/component | Impact |
|---|---|
| PAD-001 v1.5 | Needs a narrow supplier-risk API/security profile; no business semantics. |
| EIC-001 v1.3 | Unchanged; API maps to the single runtime invocation boundary. |
| EOM/ESM | Unchanged; API transports state and outcomes. |
| RFC-014/RSP-001 | Unchanged; retry/replay and replay authority are enforced, not redefined. |
| CIM-001/BCSs | Unchanged; request translation is field mapping only. |
| Physical Model/PMM | Unchanged if audit uses approved safe logging and existing runtime records. |
| CDD-010/011/012 | Additive consumer only; existing regression suites remain binding. |

## Technology impact

FastAPI, Pydantic, SQLAlchemy, PostgreSQL, and the repository configuration pattern already exist.
CDD-013 needs no new dependency if authentication, rate limiting, and audit are injected ports.
PAS-001 must identify the trusted verifier boundary; selecting a new identity SDK or gateway is
outside this CDD and would require separate technology authorization.

## Architecture drift result

No entity, relationship, canonical attribute, BCS meaning, capability order, persistence schema,
or runtime state change is proposed. The draft introduces external contracts only after explicit
authority. Current result: zero silent drift; one P0 authority dependency.
