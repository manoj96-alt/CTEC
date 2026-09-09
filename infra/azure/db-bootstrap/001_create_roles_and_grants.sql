-- Noetva Azure PostgreSQL role bootstrap (Noetva D0 Section BG / I0-R1
-- Section 20/21). Run ONCE per environment by an operator connected as the
-- Flexible Server administrator login (the ADMIN/EMERGENCY authority --
-- break-glass only, never the application or migration credential).
--
-- Creates exactly three authorities, least privilege, structurally
-- incapable of being confused with one another:
--
--   noetva_app      -- APPLICATION: DML only. No CREATE/ALTER/DROP of any
--                      kind. This is the role the backend Container App
--                      and the migration Container Apps Job's own runtime
--                      queries never use for schema changes.
--   noetva_migrate   -- MIGRATION: DDL + DML. The ONLY role Alembic ever
--                      connects as. Owns every object it creates.
--   (server admin)   -- ADMIN/EMERGENCY: the Flexible Server administrator
--                      login itself, used only via the audited break-glass
--                      path (Noetva D0 Section BE/BF) -- never referenced
--                      by application configuration.
--
-- Idempotent: safe to re-run against an already-bootstrapped database.
-- Never prints a password: values are supplied via psql variables
-- (`-v app_password=... -v migrate_password=...`), substituted with `:'var'`
-- (quoted-literal substitution), and this script contains no `\echo` of
-- either variable. The wrapper (scripts/run_db_bootstrap.sh) that invokes
-- this file is equally responsible for never logging the variable values it
-- reads from Key Vault.

\set ON_ERROR_STOP on

-- ---- 0. Required extension (ADMIN-only step, empirically required) ---
-- Migration 0001 (canonical_v1_3.sql) defaults every UUID primary key via
-- `gen_random_uuid()`, which pgcrypto provides. `CREATE EXTENSION` requires
-- privilege neither noetva_app nor noetva_migrate has -- confirmed directly
-- by running the real 46-migration chain against a live PostgreSQL 17
-- container as a plain non-superuser role, which failed with exactly
-- `permission denied to create extension "pgcrypto"` until this step was
-- added and run as the elevated ADMIN authority. On Azure Database for
-- PostgreSQL Flexible Server this additionally requires the extension to
-- already be present in the server's `azure.extensions` allow-list
-- parameter (set declaratively in modules/postgresql.bicep) -- CREATE
-- EXTENSION fails even for the administrator login until that allow-list
-- change has been applied. This is the ONE place ADMIN authority is used
-- for anything beyond break-glass (Noetva D0 Section BG) -- a narrow,
-- idempotent, non-destructive, one-time-per-environment exception required
-- by Postgres/Azure's own extension-privilege model, not a relaxation of
-- the APPLICATION/MIGRATION/ADMIN separation for schema work itself.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---- 1. Roles (idempotent creation) ----------------------------------
-- psql variable substitution (`:'var'`) is a client-side TEXT preprocessing
-- step and does NOT reach inside a dollar-quoted ($do$...$do$) PL/pgSQL
-- body -- verified directly against a real PostgreSQL 17 container while
-- writing this script (an earlier draft that referenced `:'app_password'`
-- inside the DO block below failed with a literal
-- `syntax error at or near ":"`). The role is therefore created here with
-- no meaningful password (immediately overwritten below, outside any
-- dollar-quoted block, where substitution does apply), and the real
-- password is set by a plain top-level ALTER ROLE statement -- which also
-- makes password-setting naturally idempotent regardless of whether the
-- role was just created or already existed.
DO $do$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'noetva_app') THEN
        CREATE ROLE noetva_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'noetva_migrate') THEN
        CREATE ROLE noetva_migrate LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
    END IF;
END
$do$;

ALTER ROLE noetva_app WITH PASSWORD :'app_password';
ALTER ROLE noetva_migrate WITH PASSWORD :'migrate_password';

-- ---- 2. Database-level connect grants only to the two named roles ----
GRANT CONNECT ON DATABASE ctec TO noetva_app;
GRANT CONNECT ON DATABASE ctec TO noetva_migrate;
REVOKE ALL ON DATABASE ctec FROM PUBLIC;

-- ---- 3. Schema ownership/usage ----------------------------------------
-- noetva_migrate owns the schema's objects (it is the role Alembic runs
-- migrations as, and therefore the role that CREATEs every table). Schema
-- usage is granted to both; CREATE on the schema is granted ONLY to
-- noetva_migrate -- this is the single structural fact that makes
-- "APPLICATION cannot CREATE/ALTER/DROP" true, not merely documented.
GRANT USAGE ON SCHEMA public TO noetva_app;
GRANT USAGE, CREATE ON SCHEMA public TO noetva_migrate;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- ---- 4. DML on every existing table/sequence, for both current data ---
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO noetva_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO noetva_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO noetva_migrate;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO noetva_migrate;

-- ---- 5. Default privileges for FUTURE objects migrations create -------
-- Every table/sequence a future `alembic upgrade head` creates (run as
-- noetva_migrate) automatically grants noetva_app the same DML-only
-- privilege, with zero manual re-grant step required after any future
-- migration (Noetva I0-R1 Section 21: "idempotent where practical").
ALTER DEFAULT PRIVILEGES FOR ROLE noetva_migrate IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO noetva_app;
ALTER DEFAULT PRIVILEGES FOR ROLE noetva_migrate IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO noetva_app;

-- ---- 6. Explicit confirmation this script never printed a secret -----
-- (No \echo of :app_password or :migrate_password anywhere above.)
SELECT 'bootstrap complete: noetva_app (DML-only) and noetva_migrate (DDL+DML) exist and are granted correctly' AS result;
