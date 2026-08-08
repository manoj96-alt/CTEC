# CTEC Alpha

CTEC Alpha is a modular-monolith workspace for the Enterprise Cognitive Operating Model prototype. The existing CDD-004 through CDD-009 implementation lives unchanged architecturally under `cognitive-engine/`; the new experience and sample-data areas consume that engine without redefining its business semantics.

## Repository structure

```text
ctec-alpha/
├── cognitive-engine/      # Existing cognitive implementation and engineering tools
│   ├── backend/
│   ├── frontend/
│   ├── deployment/
│   ├── scripts/
│   └── tools/
├── experience-backend/    # Phase 1 consumer
├── experience-frontend/   # Phase 2 consumer
├── sample-data/           # Phase 3 governed demo inputs
├── docs/
│   └── demo/
├── docker-compose.yml
└── Makefile
```

The GitHub repository remains `CTEC`; `ctec-alpha` describes its new logical root layout. Git moves preserve the full history of the relocated implementation.

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
make migrate
make seed
```

The root commands delegate into `cognitive-engine/`. The Compose file mounts `sample-data/` read-only into the backend container.
