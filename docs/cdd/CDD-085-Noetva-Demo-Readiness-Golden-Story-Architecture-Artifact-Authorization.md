# CDD-085 Noetva Demo Readiness Golden Story Architecture — Artifact Authorization

**Status:** FROZEN
**Version:** 1.0
**Governs:** implementation of `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md` only. No
wildcard, no directory-level grant, no "and related files" language. Any path not named below is
unauthorized; if implementation discovers a genuine need to touch an unnamed path, implementation must STOP
and return for a narrow amendment, exactly as the `OQI-H1` through `OQI-H6`/`H6-G-R1` precedent establishes.

## 1. Accounting

```
CREATE = 2
MODIFY = 5
DELETE = 0
TOTAL  = 7
```

## 2. CREATE (2)

| # | Path | Purpose |
|---|---|---|
| 1 | `backend/app/tests/test_noetva_demo_readiness_golden_story.py` | Crown suite proving CDD-085's own deterministic-state contract (§19 of the main document) — the D1-D25 matrix in §7 below. |
| 2 | `docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md` | The presenter-facing runbook: exact screen order, exact spoken lines, exact `make demo-reset`/`make demo-verify` instructions. Documentation only — no code, no test obligation. **Deliberately placed under a new `docs/demo/` directory, never under `docs/product/`** — `docs/product/` remains absolutely untouched (zero create/modify/delete), exactly as every prior governing prompt in this program has required without exception, regardless of any technical argument that a different worktree/branch would not disturb the user's own untracked local files there. The rule is treated as unconditional, not situational. |

## 3. MODIFY (5)

| # | Path | Permitted modification |
|---|---|---|
| 1 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | (a) Rename the display string at the Supplier `EnterpriseEntity` construction from `"Demo Supplier (OQI Showcase)"` to `"Meridian Cell Components"` — value only, `_SUPPLIER_ENTITY_ID` and every FK referencing it unchanged. (b) Rename the `BusinessProcess` display string from `"Supplier Qualification (Demo)"` to `"Aurora X1 Supplier Qualification"` — value only. (c) Add a new, additive seed block (mirroring the existing H4 block's own `_entity`/`_edge` helper pattern, CDD-085 §7): one `Material`-type `EnterpriseEntity` ("Aurora X1 Battery Cell"), one `BOM`-type `EnterpriseEntity` ("Aurora X1 Bill of Materials"), reusing the already-authorized `Product`-type "Aurora X1" entity (below), and three `InstitutionalRelationship` edges (`supplies`, `usedIn`, `defines`) connecting them in the exact chain CDD-085 §7 freezes. Must resolve each relationship's `relationship_type_id` from the already-governed ontology vocabulary (`ontology_seed.py`, unmodified) — no new relationship type. (d) Rename `_H6_PRODUCT_A_NAME`/`_H6_PRODUCT_B_NAME`/`_H6_PRODUCT_C_NAME` from `"H6 Demo Duplicate Widget"`/`"H6 DEMO DUPLICATE WIDGET"`/`"H6 Demo Distinct Gadget"` to `"Aurora X1"`/`"AURORA X1"`/`"Nimbus S2 Controller"` respectively, and make the H6 "Product A" entity ID the *same* entity ID as the newly-added Aurora X1 Product entity from (c) — one entity, not two — so the Uniqueness candidate's canonical member is the real, ontology-connected Aurora X1 Product. No `UniquenessPolicy` row added, removed, or re-anchored — the existing Product-type policy (`_H6_POLICY_ID`) is reused unchanged. (e) Add new, additive fields to `DemoOqiSeedSummary` reporting the new entities' outcomes/IDs, needed for row-1's own test file to assert against — no existing field removed or renamed. No other line in this file may change. No new table, no new migration. |
| 2 | `backend/app/infrastructure/persistence/database_cli.py` | Add exactly two new subcommands, `demo-reset` and `demo-verify`, plus their two implementing functions and one new environment-guard helper function, per CDD-085 §18/§20 exactly: `demo-reset` requires `CTEC_DEMO_RESET_ALLOWED=true` and a resolved database-host allowlist check before calling the *existing, unmodified* `reset_database()` followed by the *existing, unmodified* `OntologySeeder`/`BlueprintSeeder` calls and the row-1-modified `DemoOqiSeeder`; `demo-verify` reads back and asserts CDD-085 §19's exact contract, exiting non-zero with a specific failure message on any mismatch. No existing function (`migrate`, `reset_database`, `seed`) may change signature or behavior. |
| 3 | `Makefile` | Add exactly two new targets, `demo-reset` and `demo-verify`, each a single `cd backend && python -m app.infrastructure.persistence.database_cli <subcommand>` line mirroring the existing `reset-db`/`seed` targets' own shape exactly. No existing target's recipe may change. Add both new target names to the existing `.PHONY` line. |
| 4 | `frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx` | Add exactly one new, conditionally-rendered link (CDD-085 §14): when `findingFamily === "OQI2"`, render a link reading "View resolved entity" to `/data/entity-resolution`. No other markup, styling, prop, or existing conditional branch may change. |
| 5 | `frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx` | Change the single `EXAMPLE_QUESTION` constant from `"Which products depend on TSMC?"` to `"Which products depend on Meridian Cell Components?"` (CDD-085 §12). No other line in this file may change. |

## 4. Unauthorized paths (explicit, non-exhaustive callouts)

**ALL OTHERS.** Explicitly not authorized: `frontend/components/site-shell.tsx` or any primary-navigation
file (no navigation redesign, CDD-085 §14's own restriction); `backend/app/infrastructure/persistence/demo_gate_f_seeder.py`
or any Gate F/Supply-Chain-Impact frontend/backend file (CDD-085 §17, deferred); `backend/app/infrastructure/persistence/seed_loader.py`
or any EDT-001 dataset file (unrelated, untouched); any H1-H6 domain, application, persistence, migration, or
test file (CDD-085 §9/§23 — Demo Readiness consumes, never modifies, frozen OQI governance); any file under
`docs/cdd/` naming CDD-046 through CDD-084 or the H6 G-R1 amendment; any Keycloak realm file; any file
implementing agent execution (`oqi_remediation_agent_service.py`, `oqi_remediation_agent_repository.py`,
`models/oqi_remediation_agent.py`) — CDD-085 §15 authorizes zero change here; any new database migration
file; any file under `docs/product/` whatsoever — zero exception, this directory is entirely untouched by
this document.

## 5. Migration

**None authorized.** CDD-085 §24 requires a STOP if any migration is found necessary. Table count remains
131, migration head remains `0047_oqi_h6_uniqueness`, unchanged by this phase.

## 6. Deterministic seed-state test matrix — D1-D25 (binding)

Binding on `backend/app/tests/test_noetva_demo_readiness_golden_story.py` (§2 row 1):

```
D1   Golden Supplier seed is deterministic (uuid5-stable ID; re-running DemoOqiSeeder is idempotent, no
     duplicate row).
D2   SAP/PLM Country-of-Origin evidence values are exactly "US"/"MX", unchanged from the pre-rename seeder.
D3   The renamed Supplier entity ("Meridian Cell Components") resolves to the same governed entity_id the
     existing OQI2/Accuracy/Reasonableness/Conformity/Timeliness evaluations already reference.
D4   The three authorized ontology relationships (supplies/usedIn/defines) exist, each with the correct
     from/to entity and the correct, already-governed relationship_type_id.
D5   The existing five OQI evaluations (Accuracy SAP/PLM, Reasonableness, Conformity SAP/PLM) produce
     byte-identical outcomes to the pre-rename seeder (TestH1H2H3NonRegression's own existing assertions
     must remain green, unmodified).
D6   The primary OQI2 Consistency Finding is OPEN.
D7   The "Aurora X1 Supplier Qualification" business dependency has Criticality = HIGH.
D8   The Supplier's Reliance state is RELIANCE_AT_RISK.
D9   POST .../remediation/prepare against the OQI2 Finding produces a genuine, non-fabricated candidate
     (basis=ACCURACY_REFERENCE_EVIDENCE, proposed_value="US") -- re-proving DR's own live-verified result
     is unbroken by the rename.
D10  The remediation authorization-decide path requires and records a named human principal -- rejects an
     anonymous/missing decided_by.
D11  Reporting execution triggers re-evaluation (state_revision increments).
D12  If the underlying SAP/PLM evidence is unchanged, the Finding remains OPEN after execution is reported
     (REMEDIATION != RESOLUTION, re-proven against the renamed data).
D13  The H6 Uniqueness candidate pair exists for ("Aurora X1", "AURORA X1"), both resolving to the same
     canonical_name, both tenant-scoped correctly.
D14  The H6 candidate's Finding status is OPEN and no adjudication exists in the fresh-seed state (candidate,
     not fact).
D15  No merge/deactivate action exists for the pair at the API or DB layer (re-confirming CDD-084/H6-VM-R1's
     own already-proven closed adjudication-action set -- not re-testing H6 itself, only confirming the
     renamed entities inherit the same guarantee).
D16  Running `demo-reset` after a live remediation authorization/execution-report removes that
     authorization/execution state (no contamination survives a reset).
D17  Two consecutive `demo-reset` + re-seed cycles produce semantically identical Golden Demo state
     (same entity names, same Finding/Reliance/evaluation outcomes; entity IDs may legitimately be
     uuid5-stable and thus literally identical).
D18  The new Evidence-tab contextual link is present only for OQI2-family findings and points to
     /data/entity-resolution.
D19  None of the Golden Demo's frozen route sequence (CDD-085 §13) returns a 404 -- explicitly including a
     assertion that the primary Finding's detail route succeeds (contrasting with the known, separately-
     tracked Integrity 404, which this suite must NOT silently normalize by omission -- assert only on the
     Golden Demo's own OQI2/H6 routes).
D20  The corrected Ask CTEC placeholder question ("Which products depend on Meridian Cell Components?")
     is asserted against the live ontology-copilot endpoint and its actual result (answered/no_match) is
     recorded and asserted explicitly -- if it returns no_match, this test must FAIL, surfacing to
     Implementation/VM that Ask CTEC cannot yet be promoted out of EXTENDED-DEMO-ONLY status (CDD-085 §12's
     own disclosed uncertainty), rather than silently passing either way.
D21  Agent Investigation for the Golden Finding returns zero specialists/zero recommendation (no fabricated
     output), consistent with CDD-085 §15.
D22  Tenant isolation and authentication scope requirements are unchanged -- the renamed entities still
     require the correct tenant_id and the correct OAuth scopes on every touched route.
D23  The full existing backend regression suite (all H1-H6 tests) remains green, unmodified in count or
     outcome beyond this row's own new file and the existing TestH1H2H3NonRegression assertions already
     covered by D5.
D24  Fresh Docker (clean volumes, `demo-reset` + `demo-verify` run inside the container) reproduces every
     D1-D22 assertion identically to host.
D25  Where browser tooling is available at VM time, the Golden Demo's frozen route sequence (CDD-085 §13)
     completes with zero unplanned backtrack and zero console/network error.
```

## 7. Acceptance criteria (binding)

Implementation is acceptable only if: it touches no path outside §2-§3; D1-D24 pass against real PostgreSQL
(D25 pending real browser tooling, per CDD-085's own honest disclosure of this environment's current
limitation); every existing H1-H6 test remains green, unmodified; whole-package `mypy`/`black`/`isort`/`ruff`
are clean; `demo-reset` demonstrably refuses to run without both guard conditions; zero migration is
introduced; the Integrity 404 remains explicitly un-normalized (tracked, not silently hidden, not fixed
inside this phase).

## 8. Authorization

This document is approved and published as the exact, binding path/schema/test authorization for
Demo-Readiness implementation, companion to
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`. Implementation may proceed against exactly the
paths, schema, and test matrix authorized above; any deviation requires a narrow governance amendment, never
a unilateral implementation-time decision.
