# CDD-045 Artifact Authorization — Flagship Explainable Product Experience (OQI7)

Version: 1.0 FROZEN
Status: FROZEN
Governs: CDD-045 (FROZEN)

## 1. Authorization structure

Two independently-gated, exactly-accounted path sets — mirroring CDD-043's own I1/I2 precedent — each named
now for planning completeness but gated behind its own separate, future, explicit Product Owner
implementation-start authorization:

```
OQI7-I1 -- Backend / Product-Serving API   (gated: authorized now to plan, requires separate
                                             implementation-start authorization)
OQI7-I2 -- Flagship /quality Frontend/UX   (gated behind OQI7-I1's own formal closure)
```

Companion governance also includes the narrow CDD-033 amendment (`CDD-033-OQI7-Placeholder-Supersession-Amendment.md`)
— already published as part of this same governance freeze, not a future implementation path.

## 2. OQI7-I1 — Backend / Product-Serving API

```
CREATE = 8
MODIFY = 1  (semantic)
DELETE = 0
TOTAL  = 9
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | CREATE | `backend/app/api/oqi/__init__.py` | package marker |
| 2 | CREATE | `backend/app/api/oqi/router.py` | `APIRouter(prefix="/api/v1/oqi", tags=["oqi"])`; all product-serving read routes + the two remediation-action HTTP wrappers (CDD-045 §22-23) |
| 3 | CREATE | `backend/app/api/oqi/schemas.py` | Pydantic response models for every contract in CDD-045 §23 (Command Center, Finding list/detail, Evidence, Ontology Impact, Business Impact, Reliance, Agent Investigation, Remediation) |
| 4 | CREATE | `backend/app/api/oqi/dependencies.py` | scope-authorization dependency (`oqi:read`, `oqi-remediation:authorize`, `oqi-remediation:report-execution`), reusing `app.api.supplier_risk.authentication.TrustedPrincipal`/`app.api.supplier_risk.dependencies.principal` exactly — no new auth mechanism |
| 5 | CREATE | `backend/app/application/oqi_product_experience_service.py` | backend-owned semantic aggregation: composes OQI1-6 domain read models into each CDD-045 §23 contract; the sole place OQI7 "decides meaning" (CDD-045 §27) |
| 6 | CREATE | `backend/app/tests/test_oqi_api_router.py` | route-level tests: RBAC, tenant scoping, IDOR, pagination, response-schema shape, error semantics |
| 7 | CREATE | `backend/app/tests/test_oqi_product_experience_service.py` | domain-level aggregation tests: N-source preservation, `IMPACT_UNKNOWN`/`NO_KNOWN_BUSINESS_IMPACT`/`RELIANCE_UNKNOWN` non-downgrade, candidate-not-truth labeling, synthesizer-only-basis detection, staleness exposure |
| 8 | CREATE | `backend/app/tests/test_oqi_api_postgres.py` | real-Postgres integration: full contract composition against real OQI1-6 persisted state, tenant-isolation adversarial tests, concurrent-read stability |
| — | MODIFY | `backend/app/main.py` | narrow, additive-only: `app.include_router(oqi_router)` alongside the existing 12 router registrations; no existing registration line changed |

## 3. OQI7-I2 — Flagship `/quality` Frontend/UX (gated behind OQI7-I1 closure)

```
CREATE = 16
MODIFY = 2  (semantic)
DELETE = 0
TOTAL  = 18
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | CREATE | `frontend/app/quality/_components/command-center.tsx` | Reliance-count hero + supporting cards (CDD-045 §7) |
| 2 | CREATE | `frontend/app/quality/_components/reliance-hero.tsx` | the three-count Reliance distribution component, reused wherever Reliance is summarized |
| 3 | CREATE | `frontend/app/quality/findings/page.tsx` | Finding list: multi-dimension filter/sort, no composite score (CDD-045 §10) |
| 4 | CREATE | `frontend/app/quality/findings/[findingId]/page.tsx` | Finding detail shell: tab container (Evidence / Ontology Impact / Business Impact / Reliance / Agent Investigation / Remediation) |
| 5 | CREATE | `frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx` | N-source/single-source evidence comparison (CDD-045 §11) |
| 6 | CREATE | `frontend/app/quality/findings/[findingId]/_components/ontology-impact-panel.tsx` | ReactFlow-based entity-level impact graph (CDD-045 §12, §15) |
| 7 | CREATE | `frontend/app/quality/findings/[findingId]/_components/business-impact-panel.tsx` | per-dependency cards, never collapsed (CDD-045 §13) |
| 8 | CREATE | `frontend/app/quality/findings/[findingId]/_components/reliance-panel.tsx` | Reliance state + reason codes + history timeline (CDD-045 §16) |
| 9 | CREATE | `frontend/app/quality/findings/[findingId]/_components/agent-investigation-panel.tsx` | specialist assessments side-by-side + recommendation + basis label (CDD-045 §18) |
| 10 | CREATE | `frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx` | authorization/execution stepper (CDD-045 §20) |
| 11 | CREATE | `frontend/lib/oqi/api-client.ts` | typed client, `OqiApiError extends Error`, mirrors `lib/evidence-fitness/api-client.ts`'s exact pattern |
| 12 | CREATE | `frontend/lib/oqi/contracts.ts` | TypeScript types mirroring the CDD-045 §23 response schemas exactly |
| 13 | CREATE | `frontend/tests/oqi-command-center.test.tsx` | Command Center rendering, zero-score assertion, UNKNOWN equal-visual-weight assertion |
| 14 | CREATE | `frontend/tests/oqi-findings-workspace.test.tsx` | Finding list filter/sort/pagination, no-priority-score assertion |
| 15 | CREATE | `frontend/tests/oqi-finding-detail.test.tsx` | all six panels, N-source missingness/dissent visibility, candidate-not-truth labeling, graph attribute-level-edge prohibition, specialist-disagreement visibility, remediation-stepper execution!=resolution assertion |
| 16 | CREATE | `frontend/tests/oqi-product-truth.test.tsx` | mechanical enforcement of CDD-045 §29's UI Truth Table — the exact "must not say" strings must never appear in rendered OQI output, mirroring `gate-x-honesty.test.tsx`'s own enforcement pattern |
| — | MODIFY | `frontend/app/quality/page.tsx` | replace the four `PLANNED_CONCEPTS` cards ("Rules"/"Findings"/"DQ Impact"/"Remediation") with the real Command Center component; Evidence Fitness section unchanged |
| — | MODIFY | `frontend/tests/gate-x-navigation.test.tsx` | update expected `/quality` domain content assertions to reflect the live OQI Command Center replacing the PLANNED placeholder cards; no other navigation-array assertion changed |

No `frontend/package.json` or lockfile change is authorized — `reactflow` is already installed and already the
live pattern (verified `frontend/package.json:22`); Cytoscape is left untouched (CDD-045 §15).

## 4. Independent double-count reconciliation (binding, per CDD-043's own established discipline)

**I1 — Count derivation A** (summary arithmetic): `8 CREATE + 1 semantic MODIFY + 0 DELETE = 9`.
**I1 — Count derivation B** (literal row enumeration): §2 lists 8 numbered CREATE rows + 1 unnumbered MODIFY
row. `8 + 1 = 9`. Agree at **9**.

**I2 — Count derivation A** (summary arithmetic): `16 CREATE + 2 semantic MODIFY + 0 DELETE = 18`.
**I2 — Count derivation B** (literal row enumeration): §3 lists 16 numbered CREATE rows + 2 unnumbered MODIFY
rows. `16 + 2 = 18`. Agree at **18**.

**Combined total**: `9 (I1) + 18 (I2) = 27` unique authorized paths across both phases, zero path overlap
(I1 is exclusively `backend/`, I2 is exclusively `frontend/`).

No discrepancy exists between either phase's two independent derivations — both phases are safe to publish
under this document's own double-count requirement.

## 5. Explicit prohibitions

No path outside §2's exact 9-path I1 set or §3's exact 18-path I2 set may be created or modified for OQI7
purposes. No file under `backend/app/domain/oqi*`, `backend/app/infrastructure/persistence/`,
`backend/app/domain/gate_s/`, `backend/app/domain/gate_v/`, `backend/app/integration/adapters/gate_f/`, or any
existing frontend workspace outside the exact `frontend/app/quality/*` and `frontend/lib/oqi/*` paths named
above may be created, modified, or deleted. No database migration file. No `CDD-033` (amended only via its
already-published narrow companion), `CDD-039`–`CDD-044`, or any of their Artifact Authorizations.

## 6. Table count expectations

```
Pre-OQI7:  100  (verified against real migrated PostgreSQL schema, this document's own preflight)
Post-OQI7: 100  (unchanged -- OQI7 is a read/composition layer, zero new tables, zero new migration)
```

## 7. Migration

**None.** CDD-045 §24 freezes zero new tables and zero new migration for OQI7-I1. Current migration head
`0026_oqi6_reliance` remains authoritative and unchanged through both OQI7-I1 and OQI7-I2.

## 8. Governance publication paths (this freeze itself, already committed — not a future authorization)

```
docs/cdd/CDD-033-OQI7-Placeholder-Supersession-Amendment.md                                        (CREATE)
docs/cdd/CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience.md            (CREATE)
docs/cdd/CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience-Artifact-Authorization.md  (CREATE, this file)
```

## 9. Acceptance criteria (for the future OQI7-I1 and OQI7-I2 implementation phases)

**I1**: all 9 paths present exactly as named (no 10th path); zero new table; zero new migration; the two
action endpoints call OQI5-I1's existing service methods without modifying them; `/api/v1/oqi` mounted
alongside, not replacing, any existing router; full test matrix from CDD-045 §28 passing on real PostgreSQL;
zero regression in OQI1-6/Gate S/Gate V/Gate F/Gate W suites; static/security quality clean; exact-head CI
green.

**I2**: all 18 paths present exactly as named (no 19th path); zero package-manifest change; the UI Truth Table
(CDD-045 §29) enforced mechanically by `oqi-product-truth.test.tsx`; all 12 OQI7-VM crown-test scenarios
(CDD-045 §28) passing against real I1 API responses (not mocked data) at OQI7-VM time; accessibility checks
passing; zero regression in existing `gate-x-*` navigation/honesty tests beyond the one authorized content
update.

## 10. STOP conditions (fail-closed, unchanged discipline)

STOP and report — do not improvise — if: an implementation need requires touching any path outside §2/§3's
exact sets; any previously-frozen governance file (including the two just-published in this freeze) requires
editing in place; the double-counts in §4 ever disagree at implementation time; the verified table count ever
differs from 100; any firewall in CDD-045 §26 would be crossed; OQI7-I1's read-model design turns out to
genuinely require new persistence; OQI7-I2 turns out to genuinely require a new dependency (chart library,
client-cache library, or graph library beyond ReactFlow).
