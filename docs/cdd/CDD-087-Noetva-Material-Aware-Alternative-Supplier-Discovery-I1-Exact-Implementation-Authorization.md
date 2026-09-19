# CDD-087 — Noetva Material-Aware Alternative Supplier Discovery: I1 Exact Implementation Authorization

**Status:** Path-authorization artifact. Authorizes I1 (backend/domain) implementation only. Does not modify CDD-085 (SHA-256 `4780bb04a030fc766f73f3eb5a78168933ca1a1412b1027a321daccc7b9bb389`, re-verified) or CDD-086 (SHA-256 `7ff109ab11c4760c28b02a05ed652779ec331e697a1e381ac7613ee5a09011f5`, re-verified). CDD-086 is the authoritative architecture; this artifact only narrows it to an exact, implementable file set.

## 1. Authoritative baseline

`main` = `0e2223d26697b53d84478780b814102c2bb571cb`. `product/wow-i4` @ `9dbac52` (PR #244, open, unaffected). `product/wow-i4-b1` @ `60ca26b` (R1/R2/R3 + CDD-086), PR #245 open/mergeable. Working tree clean at authoring time.

## 2. Architecture dependency

This artifact implements exactly CDD-086 §5 (discovery algorithm), §9 (Gate F ownership), §3/§4 (Supplier migration decision), §18 (seed migration), §19 (adversarial matrix), §10 (API contract) — narrowed to I1's exact surface. No architecture decision is re-opened here.

## 3. Reconfirmed `supplies` relationship semantics (re-verified from source)

- Name: literal `"supplies"`, already a named constant `SUPPLIES_RELATIONSHIP_TYPE_NAME = "supplies"` in `backend/app/integration/adapters/gate_f/krm.py:45` — reusable, not re-invented.
- Binding: `("supplies", "Supplier", "Material")` in `ontology_seed.py`'s `REQUIRED_RELATIONSHIPS` (curated presentation metadata only — `OntologyRelationshipBinding` is read-only by `domain/ontology/resolver.py::resolve_supplier_risk_ontology` for the Ontology Service API/Explorer; confirmed **not** enforced at write time anywhere in the write path (`demo_gate_f_seeder.py::_relate` inserts `InstitutionalRelationship` rows directly, with no binding check)).
- Direction: `from_entity_id` = Supplier, `to_entity_id` = Material (confirmed in `demo_gate_f_seeder.py`: `("supplies", "supplies", supplier.entity_id, material.entity_id)`).
- Persistence: `institutional_relationships` rows, tenant-scoped (`tenant_id` column, RFC-016 composite FK).
- Loading: `InstitutionalRelationshipStore.load_tenant_graph(tenant_id)` already loads **every** entity and edge for the tenant into `(entities_by_id: dict[UUID, GraphEntity], edges: tuple[GraphEdge, ...])`, where `GraphEdge.relationship_name` is the literal relationship-type name string (e.g. `"supplies"`). `supply_chain_impact_api.py::_evaluate` already calls this once and holds both in scope for the remainder of the request.
- Comparable existing traversal: `krm.py::derive_single_source_exposure` already queries `InstitutionalRelationship` filtered by `relationship_type_id == supplies` AND `to_entity_id == material_entity_id` — the exact reverse-lookup shape needed, today used only to `len(...)` count, never to return the set.

## 4. Exact current runtime path (re-derived, classified)

```
router.py::evaluate (POST /api/v1/supply-chain-impact/evaluations)
  -> SupplyChainImpactApiService.evaluate (supply_chain_impact_api.py)
    -> InstitutionalRelationshipStore.load_tenant_graph            [NO CHANGE]
    -> SupplyChainImpactApiService._traverse_impact                [NO CHANGE]
    -> SupplyChainImpactApiService._find_risk_event                [NO CHANGE]
    -> alternate_supplier_ids = <tenant-wide type scan>             [MODIFY REQUIRED -- §5]
    -> per material: krm.derive_single_source_exposure              [NO CHANGE]
                     krm.derive_revenue_materiality                 [NO CHANGE]
                     per candidate: krm.derive_candidate_evidence    [NO CHANGE]
                                    drm.evaluate / _classify         [NO CHANGE]
    -> grm.evaluate                                                 [NO CHANGE]
  -> router.py response assembly (_candidate_response, _evidence_items) [MODIFY REQUIRED -- §9, additive field]
  -> schemas.py CandidateOutcomeResponse                            [MODIFY REQUIRED -- §9, additive field]
  -> frontend/lib/supply-chain-impact/contracts.ts CandidateOutcome [MODIFY REQUIRED -- additive mirror only]
```

## 5. Target discovery ownership and exact fix location

**Ownership (reconfirmed, CDD-086 §9): ontology/orchestration layer owns discovery; Gate F KRM/DRM unchanged.**

**New finding, load-bearing for the exact fix:** the current type-scan runs **once, before** the `for material in impact.materials:` loop — tenant-wide and material-agnostic. Under material-aware discovery, the candidate set differs **per material** (a Supplier of Material M is not necessarily a Supplier of Material N), so the discovery call must move **inside** the per-material loop, invoked once per `material.material_entity_id`, replacing the single pre-loop `alternate_supplier_ids` computation.

Exact replacement, in `backend/app/application/supply_chain_impact_api.py`:
```python
# REMOVED (pre-loop, material-agnostic, type-based):
alternate_supplier_ids = tuple(sorted(
    (entity.entity_id for entity in entities_by_id.values()
     if entity.entity_type_name == ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME),
    key=str,
))

# ADDED (inside the `for material in impact.materials:` loop, material-aware,
# relationship-based, self-excluding):
candidate_supplier_ids = discover_candidates_supplying(
    entities_by_id=entities_by_id,
    edges=edges,
    material_entity_id=material.material_entity_id,
    exclude_entity_id=supplier.entity_id,
)
targets = candidate_supplier_ids or (None,)
```
`discover_candidates_supplying` is a new **pure domain function** in `backend/app/domain/ontology_copilot/traversal.py` (same module as `find_paths_to_target_type`, same purity/no-DB-access contract stated in that module's own docstring):
```python
def discover_candidates_supplying(
    *,
    entities_by_id: dict[UUID, GraphEntity],
    edges: tuple[GraphEdge, ...],
    material_entity_id: UUID,
    exclude_entity_id: UUID,
    relationship_name: str = "supplies",
) -> tuple[UUID, ...]:
    """Every entity with a `relationship_name` edge directly into
    `material_entity_id`, excluding `exclude_entity_id`, sorted for stable
    ordering. Pure: operates only on the supplied, already tenant-scoped
    graph -- no query, no traversal beyond one incoming-edge filter."""
```
(Function name is a suggestion, not frozen — the implementer may rename to match reviewer preference; its signature, purity, module placement, and single responsibility are frozen.) `ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME` becomes dead in this file once the scan is removed — delete the now-unused constant in the same diff (the entity TYPE `"Alternate Supplier"` itself is **not** deleted from the ontology; only this file's now-unused reference to its name).

## 6. Supplier / Alternate-Supplier migration decision

**Decision (CDD-086 §3, reconfirmed): retire the demo's reliance on the `"Alternate Supplier"` entity type as the discovery signal. Do not delete the entity type from the ontology** (`ontology_seed.py`'s `REQUIRED_CONCEPTS`/`CONCEPT_DEFINITIONS` entry for `"Alternate Supplier"` is out of I1 scope — deleting a concept type is a larger, separately-justified ontology change with its own blast radius on Ontology Explorer/Modeling, not required for discovery to work correctly). I1 only stops **using** the type as a filter; the type may remain defined, simply unused by this code path going forward.

`candidateFor`'s binding (`Alternate Supplier → Material`) is **NOT changed in I1** — confirmed not functionally required (§3: bindings are display-only, unenforced at write time), and changing it would force an unnecessary, unjustified edit to `test_gate_f_semantic_foundation.py:26`'s `assert ("candidateFor", "Alternate Supplier", "Material") in REQUIRED_RELATIONSHIPS`. Deferred to a future, separately-scoped ontology-cleanup CDD if ever pursued.

Approach: **CREATE new ordinary-`Supplier`-typed demo candidates; do not repurpose the existing single Alternate Supplier entity.** Repurposing it (retyping in place) would be a one-off migration hack; creating clean, purpose-named `Supplier`-typed fixtures that genuinely supply the affected material proves the architecture, matching CDD-086 §18's explicit preference for "the demo to prove real discovery rather than preserve answer-shaped compatibility."

## 7. Exact demo topology (`demo_gate_f_seeder.py`)

Existing naming convention (re-verified): `label_id(suffix) = f"gate-f-demo:{label}:{suffix}"`, scenario labels `"recommended"`/`"unknown"`/`"rejected"`, deterministic ids via `uuid5(BOOTSTRAP_SEED_NAMESPACE, f"gate-f-demo:{label}")`. The new topology follows this convention exactly, scoped **per scenario** (each of the three scenarios keeps its own independent Material, so candidate suppliers must be seeded per scenario too — a candidate seeded only for `"recommended"` must not leak into `"unknown"`/`"rejected"`'s candidate set, since discovery is material-scoped and each scenario's Material id is already distinct):

For the `"recommended"` scenario (the only one exercising the full multi-candidate/eligibility-contrast story, per §8):
- `gate-f-demo:recommended:candidate-b` — `Supplier`-typed, name `"Demo Candidate Supplier B (recommended)"`, `supplies` → the scenario's existing Material.
- `gate-f-demo:recommended:candidate-c` — `Supplier`-typed, name `"Demo Candidate Supplier C (recommended)"`, `supplies` → the same Material.
- `gate-f-demo:recommended:unrelated-supplier` — `Supplier`-typed, name `"Demo Unrelated Supplier (recommended)"`, `supplies` → a **new**, otherwise-unused demo Material (`gate-f-demo:recommended:unrelated-material`) it alone supplies — proves adversarial test C/I (a real Supplier, unrelated to the affected Material, is never discovered).

The `"unknown"` and `"rejected"` scenarios retain the single-candidate shape they have today (their own purpose is to prove the UNKNOWN/REJECTED *outcome* paths, not multi-candidate cardinality, which `"recommended"` already covers) — but that one candidate migrates from `Alternate Supplier`-typed to `Supplier`-typed-with-a-real-`supplies`-edge, for architectural consistency (no scenario may keep the old type-scan shape, or the migration is incomplete and untested).

**Absolutely forbidden**, reconfirmed: no field or relationship named/shaped like `alternateSupplierFor`, `candidateSupplierIds`, `bestSupplier`, `recommendedSupplier`, `selectedAlternative`, or any semantic equivalent. The candidate set must be computable by §5's function from `supplies` edges alone.

## 8. Exact demo evidence design

- Candidate B (`recommended` scenario): `qualification=true`, `capacity=true`, `leadTimeDays` and `costUsd` both asserted (mirrors today's single alternate's real values, e.g. `21`/`185000`, reused) — fully eligible, demonstrating RELEVANT ∧ ELIGIBLE.
- Candidate C (`recommended` scenario): `qualification=true`, **no `capacity` assertion at all** (genuinely absent, never asserted false) — demonstrates RELEVANT ∧ eligibility-Unknown-on-one-condition, the concrete proof that "relevant ≠ automatically eligible" (governing prompt §8). No new policy condition is introduced — this reuses DRM's existing `capacity_sufficient` tri-state exactly as `GovernedFact(value=None)` already models "insufficient governed evidence" today.
- No ranking, score, or ordering-as-preference between B and C is introduced anywhere — their `CandidateOutcome` order is the deterministic sort from §5's function (by entity id, matching today's `key=str` convention), stated explicitly as non-ranking in both the domain function's docstring and (I2's concern, not I1's) any future UI copy.

## 9. Candidate relevance API contract (exact, minimal, additive)

`CandidateOutcomeResponse` (`backend/app/api/supply_chain_impact/schemas.py`) gains exactly one new field:
```python
relevance_relationship: str | None
```
— the real relationship-type name (`"supplies"`) that connected this candidate to the affected material; `None` only in the pre-existing "no candidate at all" shape (`alternate_supplier_entity_id is None`). **No** richer structure (relationship id, from/to entity ids) is added: `alternate_supplier_entity_id` (already present) is the "from," and the enclosing `MaterialEvaluationResult.material_entity_id` (already present) is the "to" — duplicating either would expose persistence internals not needed by any consumer (governing prompt §9's explicit caution). `router.py::_candidate_response` is extended to populate it from the same `CandidateEvidence`/discovery result already in scope — no new query. `application/supply_chain_impact_api.py`'s internal `CandidateOutcome` dataclass gains the same field, sourced directly from §5's discovery call (the relationship name used to find that candidate), not recomputed later.

`frontend/lib/supply-chain-impact/contracts.ts`'s `CandidateOutcome` interface mirrors it as `relevance_relationship: string | null` — a type-only, backward-compatible addition (existing fixtures in `supply-chain-impact-workspace.test.tsx`/`supply-chain-impact-accessibility.test.tsx` remain valid without modification, since TypeScript structural typing does not require every literal object to redeclare every interface field when the field is present-but-unused at a given call site only if optional — **to guarantee zero required frontend test-fixture changes, this field is typed non-optional but every existing fixture already includes every other required field, so it must be added to each of the ~4 response fixtures in those two test files with a real value** (`"supplies"` for populated candidates, `null` for the one already-existing empty-candidate shape) to keep them compiling; this is the one small, mechanical, unconditional frontend test-fixture touch required by an additive-but-non-optional contract field). No frontend *component* or *page* file changes — I1 renders nothing new.

## 10. `candidateFor` decision

Not touched in I1 (§6). The relationship type itself continues to exist and continues to be created per-candidate by `krm.py::derive_candidate_evidence`, entirely unchanged — it already correctly records "this pairing was formally evaluated," and remains correct regardless of which entity type the candidate happens to carry (the relationship instance itself has no type-binding enforcement, §3).

## 11. Gate F KRM/DRM change/no-change proof (adversarial)

- `drm.py`: **NO CHANGE.** `_classify` operates only on `DrmUnit` (material id, three tri-state facts, one `CandidateEvidence | None`) — it has no reference to how the candidate was discovered or what entity type it carries. Verified by direct re-read: zero occurrence of `entity_type_name` or any discovery concept anywhere in `drm.py`.
- `krm.py`: **NO CHANGE.** `derive_candidate_evidence(alternate_supplier_entity_id: UUID, material_entity_id: UUID, ...)` takes the candidate id as an opaque parameter and reads assertions directly by id — it does not discover, filter, or validate the candidate's type or relationship to the material. `SUPPLIES_RELATIONSHIP_TYPE_NAME`/`derive_single_source_exposure` are reused **as-is** (read, not modified) by the new §5 domain function only insofar as they establish the existing precedent for the relationship name constant; no line in `krm.py` itself is edited.
- Both files' existing unit tests (`test_gate_f_adapters.py`) pass an explicit candidate id directly and therefore require **NO CHANGE** — they test the adapters, not discovery.

## 12. Tenant-isolation architecture (proof, not new code)

`discover_candidates_supplying` (§5) operates **exclusively** on `(entities_by_id, edges)` already produced by `InstitutionalRelationshipStore.load_tenant_graph(tenant_id)`, which is tenant-scoped by its own `WHERE tenant_id == ...` query and structurally protected by RFC-016's tenant-qualified composite foreign keys. The new function introduces **zero new database query** and **zero new repository method** — it is pure in-memory filtering over data whose tenant scope was already established before it runs. Isolation is proven by construction, not by an additional runtime check; adversarial test P (§13) makes this observable rather than merely architectural.

## 13. Adversarial test matrix — exact test assignment

| Governing-prompt item | Test file | Disposition |
|---|---|---|
| A, B, C, D, I, J (relationship-driven discovery, unrelated-material exclusion, old-type-alone insufficiency) | `test_gate_f_traversal_orchestration.py` | MODIFY: replace the `"Alternate Supplier"`-typed, edge-less fixture helper with `Supplier`-typed fixtures carrying real `supplies` edges per §7; add the unrelated-material-supplier case |
| D (self-exclusion) | `test_gate_f_traversal_orchestration.py` | MODIFY: new case — the disrupted Supplier's own `supplies` edge to its own Material must not make it its own candidate |
| E, F (edge removal/addition without code change) | `test_gate_f_traversal_orchestration.py` (new) | CREATE-within-file: two tests seeding/omitting a `supplies` row directly, proving pure data-drivenness |
| G, H (multiple candidates, no ranking) | `test_gate_f_cardinality.py` | MODIFY: replace `"Alternate Supplier"`-typed multi-entity fixture with `Supplier`-typed + `supplies` edges (§7/§8's B/C shape); existing cardinality assertions (list length, no order-as-rank language) are reused |
| K, L (missing qualification/capacity → Unknown) | `test_gate_f_cardinality.py` or `test_gate_f_adapters.py` | MODIFY (whichever already covers this today; verify before touching — do not duplicate) |
| M (truthful failure reason) | `test_gate_f_adapters.py` | NO CHANGE (already covers `GateFOutcomeReason` directly against an explicit candidate id, §11) |
| N (relevance relationship returned) | `test_gate_f_traversal_orchestration.py` (new) | CREATE-within-file: asserts `relevance_relationship == "supplies"` on a real discovered candidate |
| O (provenance intact) | `test_gate_f_adapters.py` | NO CHANGE (already asserts `knowledge_references`/`evidence` shape) |
| P (tenant isolation) | `test_gate_f_tenant_isolation.py` | MODIFY: `test_cross_tenant_alternate_supplier_is_excluded_from_candidate_discovery` → rename/rebuild around a cross-tenant `Supplier` with a same-shaped `supplies` edge to a same-named Material in a different tenant |
| Q, R (frontend zero discovery/policy logic) | `frontend/tests/supply-chain-impact-workspace.test.tsx` | NO CHANGE (already asserted by the existing "no business conclusion is computed client-side" test; still true, nothing to add for a backend-only field) |
| S (recommendation backend-authoritative) | existing suite | NO CHANGE |
| T (human authority unchanged) | existing suite | NO CHANGE |
| Seeder idempotency/topology | `test_demo_gate_f_seeder_postgres.py` | MODIFY: fixture/assertions updated for the §7 topology; idempotency assertions (`first == second`) pattern reused unchanged |
| Ontology binding assertion | `test_gate_f_semantic_foundation.py` | NO CHANGE (§6/§10 — binding not touched) |

## 14. $12M exposure — no-change proof

Re-confirmed by direct re-read: `_traverse_impact`, `krm.py::derive_revenue_materiality`, and the `Product --generatesRevenue--> RevenueExposure`/`annualRevenueUsd` chain contain no reference to `alternate_supplier`/`Alternate Supplier` anywhere. **Classification: NO CHANGE** for every file in this chain (`supply_chain_impact_api.py::_traverse_impact`, `krm.py::derive_revenue_materiality`, `demo_gate_f_seeder.py`'s revenue-exposure seeding block, `schemas.py::ImpactSummaryResponse`).

## 15. Deferred conflict-resolution gap

Reconfirmed: `_latest_assertion`'s recency-wins conflict resolution is **DEFERRED — separately governed capability gap**, per CDD-086 §12. I1 does not touch `_latest_assertion` — the new discovery function calls it zero times (it only reads real *relationship* edges, not assertions; assertion reads remain entirely inside the unchanged `krm.py`).

## 16. Live agents

Unchanged: `NOT_INVOKED`. No agent/LLM/ranking capability is introduced anywhere in I1.

## 17. I2 boundary (minimum surface only, not authorized here)

I1 authorizes exactly the type-contract mirror in `frontend/lib/supply-chain-impact/contracts.ts` (§9) and nothing else in `frontend/`. No component, page, or test *beyond* the mechanical fixture-value additions already required by §9's non-optional field is touched. I2's own page/component authorization is explicitly deferred to its own future path-authorization artifact, once I1's real `relevance_relationship` values exist to design against.

## 18. Legacy secondary navigation

**Explicitly out of I1 scope**, reconfirmed per the governing prompt §19: `frontend/components/site-shell.tsx` is **FORBIDDEN** in this authorization (§21 below). CDD-086 §17's resolution direction stands as future guidance only, not actioned by I1.

## 19. Exact path authorization

**CREATE (1, conditional):**
1. None required as a new *file*. The one new function (`discover_candidates_supplying`, §5) lives inside the already-authorized-to-modify `traversal.py` (MODIFY, not CREATE) — no new file is justified for a single ~15-line pure function alongside its existing, single-responsibility sibling in the same module.

**MODIFY (unconditional, 6):**
1. `backend/app/domain/ontology_copilot/traversal.py` — add `discover_candidates_supplying` (§5). Additive; `find_paths_to_target_type` untouched.
2. `backend/app/application/supply_chain_impact_api.py` — replace the pre-loop type-scan with the per-material discovery call (§5); remove the now-unused `ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME` constant and its import if it becomes fully unused; add `relevance_relationship` to the internal `CandidateOutcome` dataclass and populate it (§9).
3. `backend/app/api/supply_chain_impact/schemas.py` — add `relevance_relationship: str | None` to `CandidateOutcomeResponse` (§9).
4. `backend/app/api/supply_chain_impact/router.py` — thread the new field through `_candidate_response` (§9). No route, status code, or auth/scope change.
5. `backend/app/infrastructure/persistence/demo_gate_f_seeder.py` — migrate to the §7 topology (new `Supplier`-typed candidates + `supplies` edges per scenario, replacing the single tenant-wide `Alternate Supplier` entity and its assertions).
6. `frontend/lib/supply-chain-impact/contracts.ts` — add `relevance_relationship: string | null` to `CandidateOutcome` (§9). No other frontend file.

**MODIFY (conditional, exact enumerated set, verify need before touching — do not expand without a new discovery pass, 6):**
7. `backend/app/tests/test_gate_f_traversal_orchestration.py` — §13.
8. `backend/app/tests/test_gate_f_cardinality.py` — §13.
9. `backend/app/tests/test_gate_f_tenant_isolation.py` — §13.
10. `backend/app/tests/test_demo_gate_f_seeder_postgres.py` — §13.
11. `backend/app/tests/test_gate_f_api_security.py` — touch **only** if its own `Alternate Supplier` fixture (line ~471) breaks under the new discovery call; it tests auth/scope boundaries, not discovery, so likely needs no change — verify, do not assume.
12. `frontend/tests/supply-chain-impact-workspace.test.tsx` and `frontend/tests/supply-chain-impact-accessibility.test.tsx` — mechanical addition of `relevance_relationship` to each existing response/candidate fixture object only (§9); zero new test, zero new assertion, zero behavior change to any existing assertion.

**DELETE (0).** No file is deleted. No entity type is removed from the ontology (§6).

**FORBIDDEN (explicit, reconfirmed):** `backend/app/integration/adapters/gate_f/drm.py`; `backend/app/integration/adapters/gate_f/krm.py`; `backend/app/infrastructure/persistence/ontology_seed.py` (the `candidateFor` binding, §6/§10); `backend/app/tests/test_gate_f_semantic_foundation.py`; `backend/app/tests/test_decision_engine.py`; `backend/app/tests/test_demo_gate_f_seeder.py` (tests only the tenant guard, unrelated to topology); any OQI file; any Ontology Explorer/Modeling file; `frontend/components/site-shell.tsx` (§18); `frontend/app/supply-chain-impact/**` (page/components — I2's scope, not I1's); any new API endpoint or route; any approve/reject/execute control; any agent/LLM integration; `infra/**`; any Azure/Docker deploy action.

```
I1: CREATE = 0, MODIFY ≤ 6 (unconditional) + ≤ 6 (conditional), DELETE = 0, TOTAL ≤ 12
```

## 20. Docker verification requirements

Before any Azure consideration: full backend unit/integration suite (including the real-PostgreSQL `*_postgres.py` tier) green; a fresh backend Docker image built and its container run locally against the same PostgreSQL fixture used by the integration tests, exercising `POST /evaluations` for all three demo scenarios end-to-end inside the container (not just `pytest` on the host) to prove the discovery function behaves identically under the actual deployed runtime. No Azure deployment is required to prove I1 — Docker-local proof is sufficient and is the required gate before any I2/Azure work begins.

## 21. Azure proof strategy (design only — unchanged from CDD-086 §20, not executed here)

Unchanged: seed `{A→M, B→M, C→M, D→X}` (§7's topology, generalized) → evaluate → capture `{B, C}`; governed demo-only relationship mutation (remove `C→M`, add `D→M`) via the same idempotent seeder mechanism, zero application-code change between steps → re-evaluate → capture `{B, D}`. This remains an I2/VM-stage demonstration, not an I1 deliverable; I1's own Docker-local proof (§20) is the load-bearing gate for I1 itself.

## 22. Rollback / backward compatibility

API field is additive-only (§9); no existing field renamed, removed, or reinterpreted. Seed migration is scoped to the labeled demo tenant only (`demo_gate_f_seeder.py`'s existing `_ALLOWED_SEED_TENANTS` guard, unchanged) and remains idempotent. The `Alternate Supplier` entity type remains defined in the ontology (§6) — nothing about I1 is destructive to existing persisted demo data beyond the seeder's own idempotent re-seed semantics. All prior branches/PRs/Azure revisions (§24 of the governing prompt) remain untouched — this artifact makes no code change at all.

## 23. Truth-contract audit

Every term from the governing prompt §25 is preserved by construction: seeded facts ≠ seeded answer (§7's explicit forbidden-shapes list); type match ≠ material-aware discovery (§5's fix); supplier ≠ alternative intrinsically (§6's decision); relevant ≠ eligible ≠ recommended ≠ authorized ≠ executed (§8's B/C evidence design makes this observable, not merely asserted); relationship ≠ causation, hop grouping ≠ traced path (unaffected, R2/R3's existing boundary untouched); missing ≠ false, Unknown ≠ failed (§8, unchanged `GovernedFact`); policy confidence ≠ AI confidence, deterministic policy ≠ agent reasoning (§11, Gate F unchanged); demo data ≠ customer data (§7's tenant-scoped seeder guard, unchanged); remediation ≠ resolution (no remediation capability touched). Live agent reasoning: `NOT_INVOKED` (§16).

## 24. STOP conditions (must hold before I1 implementation begins)

STOP and return to governance rather than proceed if, once implementation starts: (a) any test in §13's conditional list requires a change to `drm.py`/`krm.py`/`ontology_seed.py`'s binding to pass (would contradict §11/§6's no-change proof); (b) the additive `relevance_relationship` field cannot remain nullable-only-for-the-empty-candidate-case without breaking an existing assertion; (c) the demo topology (§7) cannot be seeded without introducing any answer-shaped field; (d) discovery cannot be proven tenant-isolated without a new database query. None of these were encountered during this artifact's own source verification — all four boundaries hold as designed.

## 25. Exact I1 handoff instruction

An implementing agent may proceed directly from §19's path table without further architectural decision-making: the discovery algorithm (§5), its exact code location and replacement point (§5), the demo topology and evidence design (§7/§8), the API contract's exact shape (§9), the Gate F no-change boundary (§11, adversarially verified), the tenant-isolation proof (§12), and the full test-file assignment (§13) are all frozen. Implement, run the full suite (unconditional + conditional test files per §19), verify §20's Docker-local proof, then STOP for operator review before any I2/frontend work or Azure action.

## 26. Final disposition

Exact I1 path authorization frozen. No implementation performed by this artifact itself. `product/wow-i4-b1` unchanged in code (governance commit only). Ready for a future, explicitly-authorized I1 implementation phase.
