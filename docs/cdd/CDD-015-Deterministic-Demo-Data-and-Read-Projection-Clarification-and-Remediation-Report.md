# CDD-015 — Deterministic Demo Data and Read-Projection Clarification and Remediation Report

Version: 1.0
Status: APPROVED CLARIFICATION
Authority base: `9168c67b69d25e075b874f82aa43a89e12920329`

## Decision

This report authorizes exactly the narrow F-I4 scope the Product Owner defined: deterministic
governed Gate F demo instance data, realistic evidence/provenance for that data, and two small
additive read-only projections on the already-implemented F-I3 API responses — nothing else. It
introduces no new business capability, no new business-policy behavior, no new access scope, and no
new canonical vocabulary. It follows the same standalone-companion-document precedent already used
twice for CDD-015 (the merged Governed Impact Decision Policy Clarification and Remediation Report,
PR #69, and the merged Runtime Composition Clarification and Remediation Report, PR #71): a
standalone companion document to an already-FROZEN CDD, not an edit to CDD-015 itself, not an edit
to either already-merged clarification report, and not a new architecture baseline. F-I5 (frontend)
is explicitly and entirely out of scope for this report — it requires its own, separate, future CDD
per CDD-015 §22's own text, not covered or implied here.

## Resolved items

**A — Demo instance data authority.** A new, standalone, demo-only seeder class
(`backend/app/infrastructure/persistence/demo_gate_f_seeder.py`) is authorized to CREATE exactly
three deterministic scenarios (RECOMMENDED, UNKNOWN, REJECTED — see Items D-F), instantiating
*only* the ten pre-existing RFC-017 §1 concepts and the seven pre-existing plus three
RFC-017-§3-authorized relationship types, through the existing `institutional_relationships` and
`assertions`/`institutional_relationship_assertions` persistence mechanisms CDD-015 §9/§16-17
already governs. This is demo *instance* data, never ontology vocabulary: it adds rows, never a new
`entity_types`/`relationship_types` value. Follows `DemoOntologyCopilotSeeder`'s exact, already-shipped
precedent (`backend/app/infrastructure/persistence/demo_ontology_copilot_seeder.py`): deterministic
`uuid5` IDs under the existing `BOOTSTRAP_SEED_NAMESPACE`, idempotent existence-checked writes,
refuses any tenant other than `BOOTSTRAP_DEMO_TENANT_ID` (raises), and is invoked exclusively through
its own `__main__` CLI entrypoint — **never** wired into `app.main.lifespan`, `build_container()`, or
any other production/runtime-composition code path. Zero runtime-composition file (`main.py`,
`dependency_container.py`) modification is authorized or required by this item — this seeder follows
its precedent's proven zero-wiring pattern exactly, avoiding any repeat of the gap the F-I3.0/F-I3.1
reports found and closed for the API router.

**B — Read-projection #1: evaluate-response explanation richness.** `backend/app/api/supply_chain_impact/router.py`
and `schemas.py` (both already CDD-015 §32-authorized) are authorized for the narrow MODIFY of adding
`structured_reasons: list[str]`, `narrative: str`, and `confidence: str` fields to the evaluate
response's per-candidate representation, populated by having the router re-read the
`decision_evaluation_records` rows the evaluate call itself just created — through the existing
public `DecisionEvaluationRepositoryImpl.records_for_group()` read contract, the same one the read
endpoint already uses — immediately after `SupplyChainImpactApiService.evaluate()` returns. This is a
pure projection of already-persisted state onto the response the same call already produces; it
performs no new computation, introduces no new business rule, and does not call `evaluate()` a second
time or create a second `decision_evaluations` group.

**C — Read-projection #2: per-condition evidence detail.** `router.py`/`schemas.py` are further
authorized for the narrow MODIFY of adding an evidence-detail projection (source system name,
assertion predicate, literal value, `asserted_on` timestamp) to both the evaluate and read responses,
by dereferencing the already-persisted `knowledge_references`/`GovernedFact.assertion_id` UUIDs
against the existing, public `Assertion`/`SourceSystem` models (`infrastructure/persistence/models/{assertion,source_system}.py`)
— a read-only lookup by primary key, not a new derivation. This includes exposing the already-derived
raw `qualification`/`capacity`/`leadTimeDays`/`costUsd` literal values for the shown alternate, again
purely as a projection of assertions KRM already created — not a new KRM/DRM computation, and no
modification to `gate_f/{krm,drm,grm}.py` or `domain/decision_engine/configuration.py` of any kind.

**D — Primary scenario (RECOMMENDED + HUMAN_APPROVAL_REQUIRED).** One deterministic chain: Risk
Event (`severity`="Severe") in a Region; Supplier (`locatedIn` that Region, `exposedTo` the Risk
Event); Material (`supplies` from Supplier, single valid edge); BOM (`usedIn`); Product (`defines`);
Facility (`assembledAt`); Revenue Exposure (`generatesRevenue`, `annualRevenueUsd`="12000000" — the
same demonstrative value already used throughout the F-I2/F-I3 automated test suite); one Alternate
Supplier (auto-discovered via `candidateFor`, `qualification`="true", `capacity`="true"). Under the
frozen, unmodified DRM policy this satisfies all four conditions positively (high-severity=True,
single-source=True, revenue $12,000,000 > $10,000,000 strictly=True, qualified+capacity=True) →
RECOMMENDED at DRM, `HUMAN_APPROVAL_REQUIRED` at GRM — the exact code path
`test_evaluate_and_read_round_trip_recommended` already proves. No policy threshold is invented or
adjusted to make this scenario succeed.

**E — UNKNOWN scenario.** A second deterministic Supplier chain, identical in shape, but with **no**
`severity` assertion seeded on its Risk Event (evidence genuinely absent, not asserted as false).
Under the frozen policy this yields `high_severity_disruption=null` and a candidate outcome of
`null`/`null`/`null` (no `decision_evaluation_records` row produced for that unit) — the exact code
path `test_evaluate_missing_severity_evidence_stays_unknown_not_rejected` already proves. Demonstrates
CDD-015's UNKNOWN≠FALSE invariant using real seeded (or rather, deliberately un-seeded) data, not a
fabricated negative.

**F — REJECTED scenario (included, narrowly justified).** A third deterministic Supplier chain with
zero Alternate Supplier entities discoverable in that scenario's tenant-graph neighborhood → DRM's
existing zero-alternate = known-False path (`REJECTED_NO_VIABLE_ALTERNATE`) — the exact code path
`test_evaluate_zero_alternates_is_known_rejected` already proves. Justification for inclusion (not
mere completeness, per the Product Owner's own instruction to justify rather than default): Item E
alone proves CTEC does not fabricate a negative when evidence is missing; it does **not**, by itself,
prove CTEC can and does produce a genuine negative when a condition is positively known false. Without
Item F, a skeptical demo observer cannot distinguish "the system never says no" from "the system
correctly withholds judgment when unsure" — the two states look identical (both a null/absent
recommendation) unless a real REJECTED case is also shown side by side. This is the smallest addition
that closes that specific demonstrability gap: it reuses entities/relationships already needed for
Items D-E, adds no new relationship type, and needs no new backend code path (already fully exercised
by existing tests).

**G — Provenance.** Every literal assertion seeded by Items D-F carries a real `source_system_id`
(via the existing `SourceSystem` model) with a demonstrative-but-labeled source name (e.g. "Gate F
Demo Risk Platform," "Gate F Demo Finance/BI," "Gate F Demo Supplier Portal" — deterministic simulated
source systems, per the Product Owner's own "may use deterministic simulated source systems" allowance,
never an unlabeled or placeholder-only authority string), and a real `asserted_on` timestamp — using
the exact same `_seed_source_system`/`_assert_literal` mechanism every existing Gate F test file
already uses. No new evidence/provenance mechanism is introduced.

**H — Nothing else is authorized by this report.** In particular: no frontend implementation, file,
or route of any kind (Items A-C authorize backend/API changes only); no approval, rejection, or
execution endpoint; no change to the four-condition DRM policy, the $10,000,000 materiality threshold,
the strict `>` operator, UNKNOWN semantics, RECOMMENDED/REJECTED semantics, or REQUIRES_REVIEW/
HUMAN_APPROVAL_REQUIRED mapping; no new persistence table, column, or migration; no new ontology
concept or relationship type beyond RFC-017 §1/§3's already-ratified set; no new Keycloak scope or
persona; no `main.py`/`dependency_container.py` modification.

## Proposed authorized artifact table

| Artifact and path | Action | Purpose | Boundary |
|---|---|---|---|
| `backend/app/infrastructure/persistence/demo_gate_f_seeder.py` | CREATE | Deterministic 3-scenario demo instance data (Items A, D-G), following `demo_ontology_copilot_seeder.py`'s exact pattern. | Demo-tenant-only refusal; own `__main__` CLI only; zero production wiring. |
| `backend/app/api/supply_chain_impact/router.py` | MODIFY | Add the two read-only projections (Items B-C). | No new endpoint; no change to `_authorize()`/scope enforcement; no second `evaluate()` call. |
| `backend/app/api/supply_chain_impact/schemas.py` | MODIFY | Add the new response fields the projections require. | Additive fields only; no removal or renaming of any existing field; `extra="forbid"` request model unchanged. |
| `backend/app/tests/test_demo_gate_f_seeder.py` | CREATE | Unit tests: ID determinism, tenant-refusal, structural correctness. | No frontend test content. |
| `backend/app/tests/test_demo_gate_f_seeder_postgres.py` | CREATE | Integration tests: idempotency, all three scenarios reproduced end-to-end through the real, unmodified `SupplyChainImpactApiService.evaluate()`, provenance preserved, tenant isolation. | Postgres-backed; asserts zero DRM/KRM/GRM behavior change. |
| `backend/app/tests/test_gate_f_api_security.py` | MODIFY | Extend with tests proving the two projections are read-only (same scope enforcement, same tenant boundary, no new computation, no new authority-bearing request field introduced). | Additive test functions only. |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | Extend `AUTHORIZED_CHANGED_PATHS` with the files above (architecture-drift allowlist, same mechanism every prior increment used). | Allowlist addition only. |

No other file is authorized. No directory wildcard, no "related files" clause.

## Non-goals (binding, restated)

Frontend implementation of any kind; frontend API client; any change to `/demo/supplier-risk` or
`/supplier-risk`; visual design; approval workflow; Approve/Reject controls; override; execution/
write-back; ERP mutation; supplier-switch execution; new Keycloak scope; new persona; any Gate F
business-policy change; new ontology concept or relationship type; Supply Chain Blueprint;
Source-to-Blueprint Semantic Mapping; Profiling/Gap Engine; Gap Impact/Remediation Engine;
generalized Decision Readiness; AI ontology discovery; any Azure/production-SaaS work.

## F-I5 explicitly deferred

Nothing in this report authorizes, implies, or pre-approves any part of a Gate F frontend. F-I5
requires its own, separate architecture-authoring phase and its own new CDD, per CDD-015 §22's own
text ("A future implementation CDD/PR would build a new, authenticated production frontend surface")
— unchanged, unaffected, and untouched by this report.

## Compatibility and boundaries

- No modification to RFC-017, PAD-003, or CDD-015 itself — this report is a third, independent,
  additive companion document, following the CDD-012 precedent of multiple sequential remediation
  documents against one CDD (already used twice for CDD-015).
- No modification to `architecture/released/*` and no new architecture baseline — scoped entirely
  within CDD-015's own non-baseline-tracked governed-implementation-work-order entry, following the
  identical precedent already established and verified structurally exempt from
  `scripts/verify_architecture_release.py`'s checks for both prior CDD-015 clarifications.
- Gate E's authentication runtime, `TrustedPrincipal`, JWT validation, and the existing `_authorize()`
  scope-enforcement mechanism remain entirely unmodified; the two projections remain protected by the
  exact same `supply-chain-impact:read`/`supply-chain-impact:evaluate` boundary the response they
  extend already requires — no new scope check, no scope-boundary change.
- `gate_f/{krm,drm,grm}.py`, `domain/decision_engine/configuration.py`, and
  `application/supply_chain_impact_api.py` remain byte-for-byte unmodified — every item in this report
  is either new demo *instance* data (Item A) using already-authorized persistence mechanisms, or a
  read-only re-projection of already-persisted/already-derived state (Items B-C) at the API-response
  layer only.

## Validation and rollback

Implementation under this report must pass: seeder idempotency and tenant-refusal tests; all three
scenarios reproduced deterministically through the real, unmodified evaluation path; provenance
fields present and correctly attributed; the existing full F-I2/F-I3 regression suites unchanged
(zero new failures beyond the already-documented pre-existing `test_ontology_api.py` failures); the
architecture-drift allowlist test extended and passing; `scripts/verify_architecture_release.py`
passing with zero drift. Rollback reverts only the additive seeder file, the additive response
fields, and the additive tests described here; no existing capability's behavior, persistence, or
authorization is affected by rollback.
