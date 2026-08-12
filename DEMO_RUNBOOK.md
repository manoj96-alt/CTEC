# CTEC Local Demo Runbook

## Prerequisites

Copy `.env.example` to `.env` and set at minimum:

- `CTEC_RUNTIME_HANDOFF_KEY` — generate with:
  ```bash
  python3 -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
  ```
  Required. The stack refuses to start without it (`docker compose` will report a clear
  "Set CTEC_RUNTIME_HANDOFF_KEY" error rather than starting in a broken state).

The **Ontology Studio** works with no further configuration — its API has no auth
dependency. **Supplier Risk submission** additionally requires a real OIDC issuer:
`CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`, `CTEC_OIDC_JWKS_URL` (backend) and
`NEXT_PUBLIC_OIDC_AUTHORITY`, `NEXT_PUBLIC_OIDC_CLIENT_ID`, `NEXT_PUBLIC_OIDC_REDIRECT_URI`,
`NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI` (frontend, baked in at build time). There is
intentionally no baked-in default for any of these.

## Start

```bash
docker compose up --build
```

Expected startup order (health-gated, not time-guessed): `postgres` becomes healthy first,
then `backend` starts — running `alembic upgrade head` and the idempotent ontology seed
before the server itself starts — then `frontend` starts once `backend` reports healthy.
Expect roughly 30–60 seconds on a clean start (dominated by image builds the first time;
well under 20 seconds on subsequent starts with cached layers).

## Observe

```bash
docker compose ps
docker compose logs --tail=100
docker compose logs backend --tail=100   # migration/seed output appears here first
```

## Stop, preserving data

```bash
docker compose down
```

## Optional clean reset — DESTRUCTIVE, deletes all persisted data

```bash
docker compose down -v
```

## URLs

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Ontology Studio | http://localhost:3000/ontology-studio |
| Supplier Risk | http://localhost:3000/supplier-risk |
| Backend API | http://localhost:8000 |
| API docs (FastAPI) | http://localhost:8000/docs |
| Health endpoint | http://localhost:8000/health |
| Ontology API | http://localhost:8000/api/v1/ontologies |

## Environment variable names (see `.env.example` for the full list, no values here)

`CTEC_DATABASE_URL`, `CTEC_RUNTIME_HANDOFF_KEY`, `CTEC_OIDC_ISSUER`, `CTEC_OIDC_AUDIENCE`,
`CTEC_OIDC_JWKS_URL`, `NEXT_PUBLIC_CTEC_API_ORIGIN`, `NEXT_PUBLIC_OIDC_AUTHORITY`,
`NEXT_PUBLIC_OIDC_CLIENT_ID`, `NEXT_PUBLIC_OIDC_REDIRECT_URI`,
`NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI`, `POSTGRES_DB`, `POSTGRES_USER`,
`POSTGRES_PASSWORD`.

## Sunday demo sequence

1. Open http://localhost:3000/ontology-studio — walk through overview, connector catalog,
   graph (click a concept), quality panel, API/export preview.
2. Click **Open Supplier Risk Application**.
3. Submit or open an existing assessment; show the result panel's ontology attribution line
   ("Powered by supplier-risk v1.0 · Published · Quality NN%") and the semantic path.
4. Navigate back to Ontology Studio via the persistent nav bar to close the loop.

## Traceable image tags

```bash
SHORT_SHA=$(git rev-parse --short HEAD)
docker build -t ctec-backend:$SHORT_SHA -t ctec-backend:demo ./backend
docker build -t ctec-frontend:$SHORT_SHA -t ctec-frontend:demo ./frontend
```

## Known limitation of this specific sandbox (not of these Docker files)

The sandbox this runbook was authored in has no network access to any container registry
(Docker Hub and GHCR both return `403 Forbidden` — confirmed by direct test). The Docker
daemon itself works, and both Dockerfiles were confirmed to parse and begin building
correctly (build context sent, first `FROM` layer reached) before failing at the base-image
pull step for that reason alone. `docker compose up --build` has not been executed
end-to-end from this sandbox. Run it from a networked machine to complete the smoke test in
`DOCKER_SMOKE_TEST.md`.
