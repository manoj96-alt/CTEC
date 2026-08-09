# CTEC — Cognitive Twin Enterprise Core

Infrastructure-only project foundation for the Enterprise Cognitive Operating Model supply-chain prototype. This layer intentionally contains no business, persistence, ontology, graph, identity-resolution, reasoning, governance, assertion, knowledge, or decision-assembly logic.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

- UI: http://localhost:3000
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/health
- Root health: http://localhost:8000/health

See [Developer Setup](docs/developer-setup.md), [Local Development](docs/local-development.md), [Folder Structure](docs/folder-structure.md), [Coding Standards](docs/coding-standards.md), and [Architecture Overview](docs/architecture/overview.md).

## Quality commands

```bash
make run
make test
make lint
make format
make typecheck
```

CDD-002 activates `make migrate`, `make seed`, and `make reset-db`. See [PERSISTENCE-001](docs/persistence/PERSISTENCE-001.md) before using destructive reset behavior.

## Cognitive Engine runtime shell

CDD-010 provides an internal, in-process orchestration shell behind one invocation facade. A
caller constructs `CognitiveEngineRuntime` with exactly six opaque `CapabilityStepPort`
implementations assigned to ERM, SRM, ASM, KRM, DRM, and GRM order. The shell does not provide
production capability adapters, semantic handoff mappings, persistence, configuration, or a
product API.

Runtime validation commands:

```bash
cd backend
pytest app/tests/test_runtime_contracts.py \
  app/tests/test_runtime_invocation.py \
  app/tests/test_runtime_orchestration.py \
  app/tests/test_runtime_execution_state.py \
  app/tests/test_runtime_architecture.py
mypy app/runtime app/tests/test_runtime_contracts.py \
  app/tests/test_runtime_invocation.py \
  app/tests/test_runtime_orchestration.py \
  app/tests/test_runtime_execution_state.py \
  app/tests/test_runtime_architecture.py
```

## Supplier-risk capability integration

CDD-011 provides an internally constructible supplier-risk chain through
`app.integration.pipeline.supplier_risk_capability_ports`. Callers inject the governed ERM, SRM,
ASM, KRM, DRM, and GRM services, their existing persistence stores, policy classifiers, and a UTC
clock. The resulting six ports are supplied to the CDD-010 `CognitiveEngineRuntime`.

Protocol `1.0` remains the legacy opaque runtime contract. Protocol `2.0` requires trusted
`AuthorityContext` control metadata version `1.0`; missing, unsupported, malformed, expired, or
conflicting metadata is rejected before capability execution. The integration produces a governed
recommendation and record references only. It does not expose a REST API or execute sourcing,
supplier, contractual, financial, or operational actions.

## Durable execution and recovery

CDD-012 adds an application-neutral SQLAlchemy execution store for the CDD-010/011 runtime. It
persists atomic admissions, six ordered stage checkpoints, opaque protected handoffs, produced
record references, terminal results, and separately authorized recovery attempts. Construct
`CognitiveEngineRuntime` with an injected `SqlAlchemyExecutionStore`; the in-memory CDD-010 store
remains available for process-local use.

Recovery is integrity-first. It resumes only after the last verified committed checkpoint and is
blocked for uncertain side effects. Every replay is a new immutable attempt under the original
logical execution and requires tenant-matched `EXECUTION_RECOVERY_OPERATOR` authority with the
`execution:replay` scope, an authorization reference, reason, correlation identifier, and UTC
timestamp. Terminal records are retained for seven years; legal hold suspends deletion. This
layer provides no API, UI, deployment wiring, or business-rule interpretation.

## Supplier-risk application API

CDD-013 exposes the bounded `/api/v1/supplier-risk` boundary. It requires a cryptographically
verified OIDC/OAuth 2.0 bearer access token, tenant-scoped PAS-001 scopes, an `Idempotency-Key`,
PostgreSQL migrations through `0009_api_security_audit`, and a deployment-owned versioned AES-GCM
handoff key. `X-User` is never trusted. Tokens, complete claims, protected payloads, and sensitive evidence
are not logged or persisted. The API reuses the CDD-010 runtime, CDD-011 six-capability flow, and
CDD-012 durable store; it does not create another orchestration path or execute sourcing actions.

## Supplier-risk business workflow

CDD-014 exposes the governed workflow at `/supplier-risk`. It consumes only CDD-013 for the tenant
work queue, assessment submission, execution/attempt/stage observation, governed results, retry
eligibility, and privileged replay. Configure the public client with
`NEXT_PUBLIC_OIDC_AUTHORITY`, `NEXT_PUBLIC_OIDC_CLIENT_ID`, `NEXT_PUBLIC_OIDC_REDIRECT_URI`,
`NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI`, `NEXT_PUBLIC_OIDC_SCOPE`, and
`NEXT_PUBLIC_CTEC_API_ORIGIN`. BSP-001 requires Authorization Code + PKCE and memory-only tokens;
never place credentials or tokens in these public settings.
