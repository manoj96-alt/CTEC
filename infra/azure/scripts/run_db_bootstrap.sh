#!/usr/bin/env bash
# Runs db-bootstrap/001_create_roles_and_grants.sql against a real Flexible
# Server, once per environment, connected as the ADMIN authority. Secrets
# are read from environment variables (populated by the deployment
# pipeline from Key Vault, never from a file in this repository) and are
# never echoed, logged, or passed as a bare CLI argument that would appear
# in shell history or process listings (Noetva D0/I0-R1 Section 50).
#
# Required environment variables (values never printed by this script):
#   NOETVA_PG_HOST            Flexible Server FQDN
#   NOETVA_PG_ADMIN_USER      administrator login (ADMIN/EMERGENCY authority)
#   NOETVA_PG_ADMIN_PASSWORD  administrator password
#   NOETVA_PG_APP_PASSWORD    password to (re)set for noetva_app
#   NOETVA_PG_MIGRATE_PASSWORD password to (re)set for noetva_migrate
set -euo pipefail

: "${NOETVA_PG_HOST:?NOETVA_PG_HOST must be set}"
: "${NOETVA_PG_ADMIN_USER:?NOETVA_PG_ADMIN_USER must be set}"
: "${NOETVA_PG_ADMIN_PASSWORD:?NOETVA_PG_ADMIN_PASSWORD must be set}"
: "${NOETVA_PG_APP_PASSWORD:?NOETVA_PG_APP_PASSWORD must be set}"
: "${NOETVA_PG_MIGRATE_PASSWORD:?NOETVA_PG_MIGRATE_PASSWORD must be set}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# set +x guard: even if this script were invoked under a shell with -x
# tracing enabled by the caller, PGPASSWORD and the -v values below would
# be visible in that trace. Explicitly disable it for the one command that
# touches secret values.
set +x
PGPASSWORD="$NOETVA_PG_ADMIN_PASSWORD" PGSSLMODE=require psql \
  -h "$NOETVA_PG_HOST" \
  -U "$NOETVA_PG_ADMIN_USER" \
  -d ctec \
  -v app_password="$NOETVA_PG_APP_PASSWORD" \
  -v migrate_password="$NOETVA_PG_MIGRATE_PASSWORD" \
  -f "$SCRIPT_DIR/../db-bootstrap/001_create_roles_and_grants.sql"

echo "[run_db_bootstrap] roles and grants applied (no secret values were printed above)"
