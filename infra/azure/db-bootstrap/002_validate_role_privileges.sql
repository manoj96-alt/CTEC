-- Validates that 001_create_roles_and_grants.sql produced exactly the
-- separation Noetva D0 Section BG requires (Noetva I0-R1 Section 21).
-- Run this connected AS noetva_app first, then AS noetva_migrate (the
-- wrapper script runs it twice, once per role, and expects the specific
-- pass/fail pattern documented in each block's comment).
--
-- This script creates and drops its own throwaway probe table/row; it
-- never touches product data.

\set ON_ERROR_STOP off

-- ==== Run as noetva_app: every one of these DDL attempts MUST fail =====
-- (ON_ERROR_STOP is off for this file specifically so we can observe and
-- report each expected failure rather than aborting after the first one;
-- the wrapper script greps for "permission denied" in the output of each.)

\echo '--- probe 1: noetva_app attempting CREATE TABLE (expect: permission denied) ---'
CREATE TABLE __privilege_probe (id int);

\echo '--- probe 2: noetva_app attempting ALTER on an existing governed table (expect: permission denied) ---'
ALTER TABLE source_objects ADD COLUMN __privilege_probe_col int;

\echo '--- probe 3: noetva_app attempting DROP on an existing governed table (expect: permission denied) ---'
DROP TABLE source_objects;

\echo '--- probe 4: noetva_app performing required DML (expect: success, 0 rows is fine) ---'
SELECT count(*) FROM source_objects;

\echo '--- probe 5: tenant-isolation composite FKs still exist and cover (tenant_id, entity_id) (expect: 4 rows, one per constraint below) ---'
-- Deliberately a catalog check, not a live INSERT: this table has several
-- OTHER, unrelated, non-tenant FKs (e.g. created_by -> enterprise_entities)
-- that a from-scratch, unseeded database cannot satisfy, which would make
-- a live-INSERT probe fail for the wrong reason and falsely look like a
-- tenant-isolation failure. Querying pg_constraint instead directly proves
-- the composite tenant-qualified FKs from Noetva D0 Section I (migrations
-- 0038/0041/0042/0043/0044/0046) exist with both columns present,
-- independent of seed data and independent of which role queries it
-- (reading pg_catalog requires no special privilege).
SELECT
    conname,
    conrelid::regclass AS child_table,
    confrelid::regclass AS parent_table,
    (SELECT array_agg(attname ORDER BY ord)
     FROM unnest(conkey) WITH ORDINALITY AS k(attnum, ord)
     JOIN pg_attribute ON pg_attribute.attrelid = conrelid AND pg_attribute.attnum = k.attnum
    ) AS child_columns
FROM pg_constraint
WHERE contype = 'f'
  AND conname IN (
    'fk_oqi_integrity_ref_eval_tenant_source_object',
    'fk_source_objects_tenant_source_system',
    'fk_oqi_integrity_ref_eval_tenant_resolution_record',
    'fk_oqi_remediation_instructions_tenant_case'
  )
ORDER BY conname;
