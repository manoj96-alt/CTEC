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

`make migrate` and `make seed` are reserved command contracts. They intentionally stop with an explanatory message until a later CDD authorizes persistence and dataset-loading behavior.
