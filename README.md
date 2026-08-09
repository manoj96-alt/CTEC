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
