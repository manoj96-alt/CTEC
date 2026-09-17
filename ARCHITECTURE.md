# CTEC Architecture

## Purpose

CTEC (Cognitive Twin Enterprise Core) is a YC prototype demonstrating the Enterprise Cognitive Operating Model in the supply-chain domain. The ontology and reasoning capabilities are the product; the UI is a restrained delivery surface.

## Architectural style

CTEC is a Clean Architecture, Domain-Driven Design modular monolith. It is not a microservice system. Dependencies point inward: delivery and infrastructure depend on application and domain contracts, never the reverse.

```text
Frontend / API
      |
      v
Application
      |
      v
Domain
      ^
      |
Infrastructure adapters
```

The frontend and API must not access persistence directly. Business logic belongs only in authorized domain services.

## Repository boundaries

- `backend/app/api/` — HTTP delivery; currently health, public configuration, and version only.
- `backend/app/core/` — composition, configuration, logging, constants, and shared errors.
- `backend/app/domain/` — bounded domain modules implemented only by their assigned CDDs.
- `backend/app/application/` — use-case orchestration and ports.
- `backend/app/infrastructure/` — persistence and external adapters behind contracts.
- `frontend/` — Next.js presentation layer with no business or persistence logic.
- `datasets/` — immutable, versioned demo datasets.
- `tools/` — reusable engineering utilities authorized by later CDDs.
- `deployment/` and `docker-compose.yml` — prototype deployment assets.

## Technology constraints

TAS-001 selects Next.js, React, Tailwind CSS, Cytoscape.js, React Flow, FastAPI, SQLAlchemy, PostgreSQL, Docker Compose, and GitHub Actions. Deferred infrastructure must not be added without an approved TAS change.

## Architecture governance

Every CDD is implemented in exactly one pull request and must pass:

1. CR-001 Gate A — Repository and Architecture Review
2. CR-001 Gate B — Code Quality Review
3. CR-001 Gate C — Business Workflow Review

The pull request must also record the CDS-001 five-hat review and confirm that no entity, relationship, attribute, RFC, layer, or technology drift occurred.

Authoritative project references are maintained outside this Git repository in the local project reference library. Their approved versions govern implementation; this document summarizes but does not replace them.
