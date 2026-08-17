#!/bin/sh
# Local/demo-only runtime credential bootstrap for the CTEC realm's
# ctec-demo-user (PAD-002 SS13, fallback mechanism 2: Keycloak Admin CLI).
#
# Keycloak 26.0.8 does not substitute ${env.VAR} placeholders inside
# realm-import user credentials (empirically confirmed during Gate E Phase
# 1) -- the committed realm JSON therefore defines ctec-demo-user with no
# password at all. This script is the only place the demo password is ever
# set, and it is set only from the caller's own environment, never printed,
# never persisted to a file, and never defaulted.
#
# Safe to run any number of times: kcadm.sh set-password overwrites the
# existing credential rather than appending one, so repeated runs converge
# on the same state without creating duplicate users, clients, or scopes.
set -eu

: "${CTEC_DEMO_USER_PASSWORD:?CTEC_DEMO_USER_PASSWORD must be set to bootstrap the local Keycloak demo user}"
: "${KC_BOOTSTRAP_ADMIN_USERNAME:?KC_BOOTSTRAP_ADMIN_USERNAME must be set}"
: "${KC_BOOTSTRAP_ADMIN_PASSWORD:?KC_BOOTSTRAP_ADMIN_PASSWORD must be set}"

KCADM=/opt/keycloak/bin/kcadm.sh
KEYCLOAK_URL="${KEYCLOAK_INTERNAL_URL:-http://keycloak:8080}"

echo "[bootstrap] authenticating to Keycloak admin API at ${KEYCLOAK_URL}..."
"$KCADM" config credentials \
  --server "$KEYCLOAK_URL" \
  --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
  --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null

echo "[bootstrap] setting ctec-demo-user password in realm CTEC (idempotent)..."
"$KCADM" set-password \
  -r CTEC \
  --username ctec-demo-user \
  --new-password "$CTEC_DEMO_USER_PASSWORD" >/dev/null

echo "[bootstrap] done."
