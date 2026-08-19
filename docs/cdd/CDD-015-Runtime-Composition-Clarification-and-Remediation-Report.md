# CDD-015 — Runtime Composition Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Authority base: `275f5da4d1b9e398aa6c8d5c16ba9506893091e5`

## Decision

This report resolves the Gate F F-I3/F-I3.0 governance discovery finding: CDD-015 §32
("Authorized External Contracts") authorizes creation of the Gate F API package
(`backend/app/api/supply_chain_impact/{__init__,router,schemas,dependencies}.py`) but contains no
"Authorized Implementation Artifacts" category — unlike its own cited pattern precedent, CDD-013
§9 — covering the two runtime-composition files objectively required to make that package
reachable by any HTTP client: `backend/app/main.py` and `backend/app/core/dependency_container.py`.
It closes exactly that one narrow authorization gap. It introduces no new canonical vocabulary
(RFC-017 unchanged), no new access scope (PAD-003 unchanged), no new persistence schema, no new
endpoint behavior, and no business-policy change. It follows the CDD-015 Governed Impact Decision
Policy Clarification and Remediation Report precedent (itself following the CDD-013 Business-Facing
API Contract Clarification and Remediation Report precedent, and the CDD-010/CDD-012 Replay
Execution Contract Clarification and Remediation Report precedent for a *second*, later,
independent companion document against an already-clarified CDD — see `CDD-012-CDD-014-REPLAY-
FRONTEND-DEFECT-AUTHORIZATION.md` for the exact same "second remediation document against the same
CDD, added later, addressing a distinct gap" pattern): a standalone companion document to an
already-FROZEN CDD, not an edit to CDD-015 itself, not an edit to the already-merged
`CDD-015-Governed-Impact-Decision-Policy-Clarification-and-Remediation-Report.md`, and not a new
architecture baseline.

## Gap verification (repeated directly against repository state)

- `backend/app/main.py` currently registers exactly seven routers (`health`, `config`, `version`,
  `supplier_risk`, `ontology`, `entity_resolution`, `ontology_copilot`); it contains zero references
  to Gate F or `supply_chain_impact`.
- `backend/app/core/dependency_container.py`'s `Container` dataclass and `build_container()`
  currently construct `supplier_risk_api`, `entity_resolution_steward_api`, and
  `ontology_copilot_api`; it contains zero references to Gate F, `SupplyChainImpactApiService`, or
  `gate_f_pipeline`.
- Every existing API package in this repository (`supplier_risk`, `entity_resolution`,
  `ontology_copilot`, `ontology`) required both a `main.py` router registration and, where the
  package calls an application service, a `dependency_container.py` construction/wiring entry —
  with no exception found. This is a uniform, unbroken mechanical requirement of this repository's
  FastAPI composition-root pattern, not a discretionary implementation choice.
- CDD-015 §34's closing paragraph states explicitly: "Runtime/application startup composition,
  deployment configuration, and environment provisioning beyond the two entries above are
  explicitly out of scope" — confirming the omission is deliberate, not an oversight this report may
  silently treat as already implied.
- `backend/app/tests/test_supplier_risk_api_security.py` (the CDD-015 §35-mandated pattern for the
  as-yet-unwritten `test_gate_f_api_security.py`) constructs its test client via
  `TestClient(create_app())` — i.e., its own required test pattern is unusable unless the router is
  actually registered in `main.py`'s real application factory.

## Resolved items

**A — `backend/app/main.py` (MODIFY, narrowly authorized).** Add exactly one import line
(`from app.api.supply_chain_impact.router import router as supply_chain_impact_router`, following
the existing import-block ordering convention) and exactly one registration line
(`app.include_router(supply_chain_impact_router)`, following the existing
`app.include_router(entity_resolution_router)` line's exact call shape — no prefix argument, no
custom tags, no middleware). No other line of `main.py` may be added, removed, or reordered. No
change to any existing router's registration, to `create_app()`'s control flow, to CORS/middleware
configuration, or to any other application-startup behavior.

**B — `backend/app/core/dependency_container.py` (MODIFY, narrowly authorized).** Add exactly one
new optional field to the `Container` dataclass (`supply_chain_impact_api:
SupplyChainImpactApiService | None = None`, following the exact existing
`entity_resolution_steward_api`/`ontology_copilot_api` field pattern) and construct it inside
`build_container()`'s existing `if settings.database_url:` block, following the exact existing
`EntityResolutionStewardApiService(sessions)` / `OntologyCopilotApiService(sessions)` construction
pattern, using only the already-authorized, already-implemented `SupplyChainImpactApiService`
(`backend/app/application/supply_chain_impact_api.py`, CDD-015 §33) and `gate_f_pipeline.py`
(`backend/app/integration/gate_f_pipeline.py`, CDD-015 §33) exactly as those files already exist —
introducing no new constructor arguments to either, no new settings field, and no change to the
construction of `supplier_risk_api`, `entity_resolution_steward_api`, `ontology_copilot_api`, or any
other existing `Container` field or `build_container()` branch.

**C — Nothing else is authorized by this report.** In particular, this report does NOT authorize:
frontend implementation or modification of any kind; an approval, rejection, or execution endpoint
of any kind; any change to the four-condition DRM policy, the $10,000,000 materiality threshold, the
strict `>` operator, UNKNOWN/candidate-fact-authority semantics, or any other Gate F business-policy
behavior established by F-I2/F-I2.3; any new persistence model, table, column, or migration beyond
what CDD-015 §33 already authorizes; any new ontology/RFC-017 vocabulary; any new cognitive-engine
port or admission entrypoint; any Keycloak configuration change (already separately, sufficiently
authorized by CDD-015 §34, unaffected by this report); any general refactoring of `main.py` or
`dependency_container.py` beyond the two additions in Resolved Items A and B; and no change to the
actual Gate F API endpoint contract, request/response schema, or authentication/scope-enforcement
mechanism itself — those remain governed exclusively by CDD-015 §16-21/§28/§32 and PAD-003 §2a-§4a,
unchanged by this report.

## Compatibility and boundaries

- No modification to RFC-017: no new relationship type, concept, or canonical attribute.
- No modification to PAD-003: no new access scope, no new endpoint boundary, no change to identity
  or runtime trust boundaries. `supply-chain-impact:read` and `supply-chain-impact:evaluate` remain
  exactly as PAD-003 §2a-§4a defines them; this report does not touch scope enforcement logic.
- No modification to `docs/cdd/CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision.md`
  itself, and no modification to the already-merged
  `CDD-015-Governed-Impact-Decision-Policy-Clarification-and-Remediation-Report.md` — this report is
  a second, independent, additive companion document, following the CDD-012 precedent of multiple
  sequential remediation documents against one CDD.
- No modification to `architecture/released/*` and no new architecture baseline. Following the
  identical precedent already established for the first CDD-015 clarification report: this
  remediation is scoped entirely within CDD-015's own, non-baseline-tracked "Governed implementation
  work orders" entry in `architecture/INDEX.md` (a second link would be added to that same row
  alongside the existing "Resolved clarification" link), confirmed structurally exempt from
  `scripts/verify_architecture_release.py`'s governance-combination and per-baseline manifest checks.
- Gate E's authentication runtime, `TrustedPrincipal`, JWT validation, and the existing
  `_authorize()` scope-enforcement mechanism remain entirely unmodified; this report authorizes no
  new authentication or authorization framework of any kind.
- Every existing capability's registration in `main.py` and construction in
  `dependency_container.py` (`supplier_risk_api`, `entity_resolution_steward_api`,
  `ontology_copilot_api`, and their respective routers) remains byte-for-byte unmodified.

## Validation and rollback

Implementation under this report must pass: the full existing backend test suite unchanged (zero
new failures beyond the already-documented 7 pre-existing `test_ontology_api.py` failures), the
architecture-drift/allowlist tests extended to include exactly these two files and the new
`test_gate_f_api_security.py` module, and a targeted test confirming `create_app()` now exposes the
Gate F router while every other router's route table is unchanged. Rollback reverts only the two
additive lines/entries described in Resolved Items A and B; no existing capability's registration,
construction, or behavior is affected by rollback.
