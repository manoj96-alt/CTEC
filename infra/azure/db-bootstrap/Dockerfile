# CDD-068: minimal, Noetva-controlled image for the one-time (or
# credential-rotation-time) ADMIN-authority database bootstrap Job only.
# Adds exactly one runtime capability the backend/migration image lacks:
# `psql`. Runs the already-committed, unmodified run_db_bootstrap.sh
# against the already-committed, unmodified 001_create_roles_and_grants.sql
# -- no SQL/bootstrap logic is duplicated or reimplemented here. Never used
# for application runtime, never given application authority.
#
# Build context MUST be infra/azure/ (not infra/azure/db-bootstrap/), e.g.:
#   docker build -f infra/azure/db-bootstrap/Dockerfile infra/azure
# so that the sibling infra/azure/scripts/ directory is reachable, matching
# run_db_bootstrap.sh's own relative-path expectation of its sibling
# db-bootstrap/ directory (SCRIPT_DIR/../db-bootstrap/...).
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install --no-install-recommends -y postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY scripts/run_db_bootstrap.sh ./scripts/run_db_bootstrap.sh
COPY db-bootstrap/001_create_roles_and_grants.sql ./db-bootstrap/001_create_roles_and_grants.sql
RUN chmod +x ./scripts/run_db_bootstrap.sh

RUN addgroup --system dbbootstrap && adduser --system --ingroup dbbootstrap dbbootstrap
USER dbbootstrap

ENTRYPOINT ["./scripts/run_db_bootstrap.sh"]
