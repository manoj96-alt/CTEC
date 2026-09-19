# CDD-088 — Noetva Alternative Sourcing Semantics: Active Source vs Sourcing Capability Governance Correction

**Status:** Governance correction. Supersedes ONLY the discovery-relationship portions of CDD-086/CDD-087 (§14 below is the exact, exhaustive list). CDD-085 (SHA-256 `4780bb04a030fc766f73f3eb5a78168933ca1a1412b1027a321daccc7b9bb389`), CDD-086 (SHA-256 `7ff109ab11c4760c28b02a05ed652779ec331e697a1e381ac7613ee5a09011f5`), and CDD-087 (SHA-256 `9124ca90c1dfcf3e73221c05f3a522d5304bc9df86cf92d10606394ff715eb1b`) remain frozen, historical, byte-identical governance artifacts — none are rewritten. This artifact authorizes I1 implementation only where it amends them; every CDD-086/087 decision not listed in §14 remains binding as originally frozen.

**Trigger:** R4-I1 implementation, executed exactly per CDD-087, was correctly STOPPED by real PostgreSQL test execution: giving a candidate a real `supplies` edge into the disrupted supplier's own material necessarily makes `krm.py::derive_single_source_exposure` (condition 2, unmodified, unmodifiable) count 2+ currently-valid `supplies` edges, flipping `single_source_exposure` from `True` to `False` and forcing `REJECTED_NOT_SINGLE_SOURCED` regardless of every other condition. CDD-086/CDD-087's own architecture was internally contradictory whenever more than one candidate exists.

---

## 1. Why `supplies` is semantically wrong for alternative discovery

`supplies` (`Supplier`→`Material`, `ontology_seed.py`) is not a neutral "connects a supplier to a material" edge — it is the specific signal `krm.py::derive_single_source_exposure` reads to answer "how many suppliers are **currently, actively** sourcing this material" (its own docstring: "counts currently valid `supplies` relationships targeting the Material"). Reusing it for "which suppliers **could** source this material if the current one is disrupted" conflates two genuinely different enterprise facts — ACTIVE SOURCING (a live procurement relationship) and SOURCING CAPABILITY (a durable qualification/approval fact, true whether or not the material is currently ordered from that supplier). A material cannot be truthfully both "single-sourced" (exactly one active supplier) and "has 2+ real `supplies` edges" (CDD-087 §5's own discovery precondition) — these are mutually exclusive by construction once discovery finds more than zero real candidates.

## 2. `candidateFor` semantic analysis — reused only where already proven safe, rejected as the discovery signal

Traced to the original source of truth, `docs/cdd/CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision.md` (the artifact that introduced `candidateFor`, RFC-017 §3c), not merely current code:

- §9 (quoted directly in `krm.py::derive_candidate_evidence`'s own docstring): **"Gate F MUST create one `institutional_relationships` row per (Alternate Supplier, Material) pair under evaluation"** — `candidateFor` is explicitly specified as a row Gate F **creates during evaluation**, not a pre-existing enterprise fact.
- §16 item B / §CDD-015 line ~469-471: `candidateFor` instances are classified as **"mutating with respect to runtime decision persistence"** — explicitly **not** canonical enterprise master data.
- Current `krm.py::derive_candidate_evidence` implements this exactly: a fresh, non-deterministic (`uuid4()`) `candidateFor` row is created on every evaluate() call, for every candidate id it is handed.

**Conclusion: `candidateFor` is a post-discovery evaluation artifact, not a pre-existing governed fact.** Using it as the discovery signal would be circular ("candidate discovered because `candidateFor` exists" vs. "`candidateFor` exists because a candidate was evaluated") — Option B (governing prompt §5) is **rejected**, confirmed from CDD-015's own original authorization text, not merely by re-reading current code.

## 3. Existing ontology relationship inventory (exhaustive)

Every relationship type ever defined anywhere in the backend, confirmed by direct grep of `ontology_seed.py`/`blueprint_seed.py` (the only two files that declare relationship-type triples):

| Name | Domain → Range | Semantic |
|---|---|---|
| `supplies` | Supplier → Material | Active, current sourcing (feeds single-source-exposure count) |
| `usedIn` | Material → BOM | Bill-of-materials composition |
| `defines` | BOM → Product | Bill-of-materials composition |
| `assembledAt` | Product → Facility | Production site |
| `generatesRevenue` | Product → Revenue Exposure | Business exposure |
| `locatedIn` | Supplier → Region | Geography |
| `exposedTo` | Region → Risk Event | Risk propagation |
| `boundBy` | Supplier → Contract | Contractual relationship |
| `coveredBy` | Material → Contract | Contractual relationship |
| `candidateFor` | Alternate Supplier → Material | Evaluation artifact (§2) |

No relationship type anywhere in this inventory represents "governed capability/approval to source a material, independent of current active sourcing." Option A (reuse an existing relationship) is therefore **unavailable** — confirmed exhaustively, not assumed.

## 4. Selected resolution: Option C — a new, narrowly-scoped governed relationship type

**`approvedSourceFor`** (`Supplier` → `Material`), added additively to `ontology_seed.py`'s `REQUIRED_RELATIONSHIPS` (matching CDD-015's own precedent for adding `assembledAt`/`coveredBy`/`candidateFor` the same way — one new tuple, `ONTOLOGY_SEED_VERSION` not bumped, per that precedent's own explicit idempotency rule). Deliberately avoids the word "qualified" (already a distinct evidence-assertion predicate on the candidate itself, §8) and "eligible" (the DRM-derived tri-state condition, §3 layer D) — using either would risk exactly the semantic collapse this correction exists to prevent.

**Enterprise semantics:** "Supplier S is a governed, durable, approved potential source for Material M" — an enterprise fact independent of whether S is *currently* supplying M (`supplies`), independent of whether S has been *evaluated* as a candidate for a specific disruption (`candidateFor`), and independent of whether S's *current qualification/capacity evidence* (assertions on S) happens to satisfy Gate F's conditions. It represents the outcome of a supplier-approval/qualification program — precisely the kind of durable master-data fact that belongs in the ontology, not the result of any decision this route computes.

## 5. Active-source semantics (unchanged, reaffirmed)

`supplies` keeps its existing, sole, correct meaning: which supplier(s) are the material's **currently active** source(s). `krm.py::derive_single_source_exposure` is **not modified** and needs no modification — it already correctly counts exactly this. This correction adds a relationship it will never see, by construction (`approvedSourceFor` is a distinct relationship type name; `derive_single_source_exposure`'s query filters on `relationship_type_id == supplies` only).

## 6. Corrected discovery algorithm

Unchanged in shape from CDD-087 §5 — only the relationship-name input changes:

```
candidate_ids = {
    edge.from_entity_id
    for edge in edges
    if edge.relationship_name == "approvedSourceFor"
    and edge.to_entity_id == affected_material.entity_id
    and edge.from_entity_id != disrupted_supplier.entity_id
    and entities_by_id[edge.from_entity_id].entity_type_name == "Supplier"
}
```
`traversal.py::discover_candidates_supplying` (CDD-087 §5) is reused exactly as designed — it already takes `relationship_name` as a parameter, defaulted to `"supplies"`; the correction is simply passing `"approvedSourceFor"` at the one call site in `supply_chain_impact_api.py`. **No change to the function's signature, purity, or module placement.**

## 7. Corrected demo topology

Per scenario (`recommended`/`unknown`/`rejected`, same `gate-f-demo:{label}:{suffix}` naming convention as CDD-087 §7):

- Disrupted Supplier **A** `--supplies-->` Material **M** (unchanged from today — the one, sole, active source).
- Candidate Supplier **B** `--approvedSourceFor-->` Material **M** (no `supplies` edge). Evidence: `qualification=true, capacity=true, leadTimeDays=21, costUsd=185000`.
- (Recommended scenario only) Candidate Supplier **C** `--approvedSourceFor-->` Material **M** (no `supplies` edge). Evidence: `qualification=true`, **`capacity` genuinely unasserted**, `leadTimeDays=35, costUsd=170000`.
- (Recommended scenario only) Unrelated Supplier **D** `--approvedSourceFor-->` Unrelated Material **X** (never M). Proves exclusion.

Because B/C/D connect to Material via `approvedSourceFor`, never `supplies`, the disrupted supplier's own `supplies` edge remains the material's **only** currently-valid `supplies` relationship in every scenario — `single_source_exposure` is `True` throughout, exactly as CDD-086's original RECOMMENDED scenario required.

## 8. Candidate C — relevant while capacity is genuinely UNKNOWN (unchanged design, corrected relationship)

C's `approvedSourceFor` edge makes it discoverable (RELEVANCE, layer B/C) regardless of its evidence completeness. Its `capacity` assertion is genuinely never written (never asserted false) — Gate F's existing, unmodified tri-state `GovernedFact` machinery correctly surfaces this as Unknown at evaluation time (ELIGIBILITY, layer D). The `qualification` **assertion** predicate (on Supplier C itself, material-agnostic) remains entirely distinct from the `approvedSourceFor` **relationship** (Supplier C → Material M specifically) — confirmed distinct by source inspection (§9 of the governing prompt's own instruction): one is a fact about the supplier, the other a fact about the supplier-material pairing. Neither duplicates nor substitutes for the other.

## 9. Relationship-mutation proof (corrected)

Identical shape to CDD-087 §13/R4-I1 §19, operating on `approvedSourceFor` instead of `supplies`: seed `{A--supplies-->M, B--approvedSourceFor-->M, C--approvedSourceFor-->M, D--approvedSourceFor-->X}` → discover `{B,C}` → mutate only `approvedSourceFor` edges (remove C→M, add D→M), zero application-code change → discover `{B,D}`. **`single_source_exposure` is asserted `True` before AND after the mutation** — provable by construction, since no `supplies` edge is ever touched by this mutation. This is the exact proof the governing prompt's §10/§23 require and CDD-087's original design could not deliver.

## 10. Gate F KRM/DRM disposition — unchanged, reaffirmed stronger

`krm.py` and `drm.py` remain **entirely unmodified** — more strongly reaffirmed than CDD-087's own claim, because this correction resolves the defect that CDD-087's design would otherwise have required a KRM change (or a dishonest effective-date hack) to paper over. `derive_single_source_exposure`'s existing behavior is **correct and is not touched, weakened, or special-cased** — it caught a real modeling mistake and continues to do exactly its job.

## 11. `relevance_relationship` correction

The additive `CandidateOutcomeResponse`/`CandidateOutcome.relevance_relationship` field (CDD-087 §9) is unchanged in shape (`str | None`) but now truthfully carries `"approvedSourceFor"`, not `"supplies"`, whenever a candidate is discovered via this relationship. This is **more precise than CDD-087's original value**, not merely a rename: it now correctly distinguishes "why this candidate was considered" (a durable sourcing-capability fact) from the disrupted supplier's own, structurally different `supplies` relationship — directly enabling I2's eventual "Currently sourced from" vs. "Qualified/capable alternative source" distinction (governing prompt §18).

## 12. Tenant-isolation architecture (unchanged)

No change from CDD-087 §12/§14: `discover_candidates_supplying` still operates exclusively on the tenant-scoped `(entities_by_id, edges)` from `InstitutionalRelationshipStore.load_tenant_graph`, with zero new query. Isolation is unaffected by which relationship-type string is passed in.

## 13. Test-file impact re-verified (no additional forbidden-file risk)

Directly re-inspected every test that reads `REQUIRED_RELATIONSHIPS`/`REQUIRED_CONCEPTS` for a hardcoded-count or hardcoded-fraction dependency that an **additive** relationship-type tuple could break:
- `test_gate_f_semantic_foundation.py` (FORBIDDEN, CDD-087): asserts `in REQUIRED_RELATIONSHIPS` only (3 `in` checks) — unaffected by an additional tuple. Confirmed by full re-read; remains untouched.
- `test_ontology_seed.py`, `test_ontology_api.py`, `test_ontology_quality_score.py` (never in CDD-087's scope, out of Gate F): every relevant assertion derives its denominator from `len(REQUIRED_RELATIONSHIPS)`/`set(REQUIRED_RELATIONSHIPS)` dynamically — no hardcoded count or fraction found (confirmed by direct grep for `== 0.` / `pytest.approx` / literal fraction patterns: none). Remain untouched, no new conditional-file risk introduced.
- `frontend/tests/ontology-studio.test.tsx`'s `["Alternate Supplier", "Supplier"]` ego-layout assertion for Material's incoming concepts: `approvedSourceFor`'s source concept is also `Supplier` (not a new concept) — the asserted concept-name set is unaffected. Remains untouched.

## 14. Exact CDD supersession matrix

| CDD-086/087 decision | Status | Corrected decision | Rationale |
|---|---|---|---|
| Discovery relationship = `supplies` | **SUPERSEDED** | Discovery relationship = `approvedSourceFor` (new) | §1, §4 |
| Demo topology: B/C/D connect via `supplies` | **SUPERSEDED** | B/C/D connect via `approvedSourceFor`; only A retains `supplies` | §7 |
| Discovery pseudocode / `discover_candidates_supplying` default | **SUPERSEDED (parameter value only)** | Same function, `relationship_name="approvedSourceFor"` at the call site | §6 |
| `relevance_relationship` value | **SUPERSEDED (value only)** | `"approvedSourceFor"`, not `"supplies"` | §11 |
| `ontology_seed.py` — no I1 change | **SUPERSEDED** | Additive: one new `REQUIRED_RELATIONSHIP` tuple `("approvedSourceFor","Supplier","Material")` | §4 |
| Gate F KRM/DRM boundary (unchanged) | **REAFFIRMED, unchanged** | Still unchanged — more strongly proven necessary | §10 |
| Ordinary-Supplier-entity decision (retire "Alternate Supplier" typing) | **REAFFIRMED, unchanged** | Unchanged — orthogonal to which relationship establishes relevance | CDD-086 §3 |
| Per-material discovery (inside the materials loop) | **REAFFIRMED, unchanged** | Unchanged | CDD-087 §5 |
| Candidate B/C evidence design (full vs. missing capacity) | **REAFFIRMED, unchanged** | Unchanged | §8 |
| Tenant isolation (in-memory graph only, zero new query) | **REAFFIRMED, unchanged** | Unchanged | §12 |
| API additive contract (`relevance_relationship: str \| None`) | **REAFFIRMED, shape unchanged** | Field shape/nullability identical; value corrected (§11) | §11 |
| Frontend boundary (contracts.ts mirror + mechanical fixture fields only) | **REAFFIRMED, unchanged** | Unchanged | CDD-087 §17 |
| `candidateFor` binding change | **REAFFIRMED, still not required** | Still not touched | CDD-087 §10, reaffirmed by §2 above |
| Test matrix (A–T) | **REAFFIRMED, relationship name corrected** | Same 20-item shape; every fixture uses `approvedSourceFor` where CDD-087 said `supplies`, plus new single-source-exposure invariant assertions (§16 below) | §9, §16 |

## 15. Path authorization (corrected, replacing CDD-087 §19)

**CREATE (0).** No new file — `approvedSourceFor` is one additive tuple in an already-modify-authorized file; `discover_candidates_supplying` already exists in `traversal.py` from the (uncommitted, stashed) CDD-087 implementation attempt and needs no new file either.

**MODIFY (unconditional, 7 — CDD-087's original 6 plus one):**
1. `backend/app/domain/ontology_copilot/traversal.py` — unchanged from CDD-087 §5 (function already correctly parameterized; no edit needed beyond what CDD-087 already authorized).
2. `backend/app/application/supply_chain_impact_api.py` — call-site `relationship_name` argument becomes `"approvedSourceFor"` (was to be `"supplies"`); everything else per CDD-087 §5 unchanged.
3. `backend/app/api/supply_chain_impact/schemas.py` — unchanged from CDD-087 §9 (field shape identical).
4. `backend/app/api/supply_chain_impact/router.py` — unchanged from CDD-087 §9.
5. `backend/app/infrastructure/persistence/demo_gate_f_seeder.py` — topology per §7 above (B/C/D linked via `approvedSourceFor`, not `supplies`).
6. `frontend/lib/supply-chain-impact/contracts.ts` — unchanged from CDD-087 §9.
7. **NEW:** `backend/app/infrastructure/persistence/ontology_seed.py` — additive only: one new tuple `("approvedSourceFor", "Supplier", "Material")` appended to `REQUIRED_RELATIONSHIPS`. `ONTOLOGY_SEED_VERSION` NOT bumped (CDD-015's own binding precedent, §4). No existing tuple, concept, or definition touched.

**MODIFY (conditional, exact enumerated set, verify need before touching, 6 — identical to CDD-087 §19, relationship-name corrected in the fixtures):**
8. `backend/app/tests/test_gate_f_traversal_orchestration.py` — fixtures use `approvedSourceFor` for candidates, `supplies` only for the disrupted supplier; add the §16 single-source-exposure invariant assertions.
9. `backend/app/tests/test_gate_f_cardinality.py`
10. `backend/app/tests/test_gate_f_tenant_isolation.py`
11. `backend/app/tests/test_demo_gate_f_seeder_postgres.py`
12. `backend/app/tests/test_gate_f_api_security.py` — verify need; unaffected by relationship-name choice per CDD-087's own finding (it tests auth, not discovery).
13. `frontend/tests/supply-chain-impact-workspace.test.tsx` and `frontend/tests/supply-chain-impact-accessibility.test.tsx` — mechanical `relevance_relationship: "approvedSourceFor"` (was to be `"supplies"`) in existing fixtures only.

**DELETE (0).**

**FORBIDDEN (unchanged from CDD-087 §19, reaffirmed):** `drm.py`; `krm.py`; `test_gate_f_semantic_foundation.py`; `test_decision_engine.py`; `test_demo_gate_f_seeder.py`; any OQI file; any Ontology Explorer/Modeling *component* file (the ontology **data** layer's additive tuple is authorized above; no Explorer *code* file changes); `site-shell.tsx`; `frontend/app/supply-chain-impact/**`; any new endpoint/route; any action control; any agent/LLM integration; `infra/**`; any deploy action; any *existing* `ontology_seed.py` tuple, concept definition, or the `candidateFor` binding.

```
Corrected I1: CREATE = 0, MODIFY ≤ 7 (unconditional) + ≤ 6 (conditional), DELETE = 0, TOTAL ≤ 13
```

## 16. Corrected adversarial test matrix

CDD-087 §13's 20-item matrix (A–T) is reused verbatim in structure, with every candidate-linking edge now `approvedSourceFor` instead of `supplies`, plus these additional, newly-mandatory invariant assertions this correction specifically exists to guarantee:

| Item | Assertion |
|---|---|
| New | `single_source_exposure is True` in the multi-candidate discovery test (B, C both discovered) — the exact case CDD-087's design could not satisfy |
| New | `single_source_exposure is True` **before and after** the relationship-mutation test (remove C's edge, add D's edge) |
| New | The disrupted supplier's `supplies` edge count into the material is exactly 1 throughout every test in this file |
| Reaffirmed (A–T) | Unchanged in intent from CDD-087 §13/governing-prompt §17; every fixture-building call now passes `type_name="approvedSourceFor"`-equivalent relationship construction instead of `supplies` for candidate edges |

## 17. Docker/PostgreSQL verification requirements (unchanged)

CDD-087 §20/§22 stand: full backend suite including the real-Postgres integration tier must be green, including the new single-source-exposure invariant assertions (§16), before any Docker image build; a fresh Docker image run locally exercising all three demo scenarios end-to-end remains the required gate before any I2/Azure work.

## 18. I2 semantic handoff

I2's eventual UI (not authorized here) can now truthfully distinguish, using real API data: **"Currently sourced from"** (the `supplies`-derived active source, unchanged from R1-R3's existing chain visualization) versus **"Qualified/capable alternative source"** (each `approvedSourceFor`-derived candidate, using the corrected `relevance_relationship` value) — a materially more meaningful distinction than R3's flat "Alternative under evaluation" label, without freezing any specific wording here (governing prompt §18's own instruction).

## 19. Truth-contract audit

All terms carried forward from CDD-086/087, plus the governing prompt's new explicit additions, all satisfied by construction: active source ≠ sourcing capability (§1/§5, now two distinct relationship types); sourcing capability ≠ current supply (§5); sourcing capability ≠ eligibility (§8, relationship vs. assertion, confirmed distinct by source inspection); relevant candidate ≠ eligible candidate (§8); eligible candidate ≠ recommended candidate (unchanged DRM); recommended candidate ≠ authorized action (unchanged GRM/human-authority); seeded enterprise capability fact ≠ seeded candidate answer (§7 — `approvedSourceFor` edges are real relationships the discovery function derives from, never a `candidateSupplierIds`-shaped answer); relationship-driven discovery ≠ ranking (unchanged, no ranking anywhere); missing ≠ false, Unknown ≠ failed (§8, unchanged `GovernedFact`); policy confidence ≠ AI confidence, deterministic policy ≠ agent reasoning (§10, Gate F fully unchanged). Live agent reasoning: `NOT_INVOKED`.

## 20. Exact corrected-I1 handoff instruction

An implementing agent may resume directly from the stashed CDD-087 diagnostic diff (`git stash list` on `product/wow-i4-b1`, entry preserved per R4-G-R1 §12's preservation procedure) with exactly these corrections applied before re-attempting: (1) change the one `discover_candidates_supplying(...)` call site's `relationship_name` argument from `"supplies"` to `"approvedSourceFor"`; (2) change `relevance_relationship = SUPPLIES_RELATIONSHIP_NAME if ... else None` to reference a new `APPROVED_SOURCE_FOR_RELATIONSHIP_NAME = "approvedSourceFor"` constant instead; (3) add the one new tuple to `ontology_seed.py`'s `REQUIRED_RELATIONSHIPS`, and add `"approvedSourceFor"` to `demo_gate_f_seeder.py`'s `_REQUIRED_RELATIONSHIP_TYPES`; (4) in `demo_gate_f_seeder.py`, link every candidate (B, C, unrelated-supplier, and the `unknown`/`rejected` scenarios' single candidates) via `approvedSourceFor` to their material instead of `supplies` — the disrupted supplier's own `supplies` edge is the only one left unchanged; (5) apply the identical fixture-relationship-name correction to the two frontend test fixtures and the four conditional backend test files (§15 items 8-13), adding the §16 single-source-exposure invariant assertions; (6) re-run the full real-PostgreSQL suite and confirm every previously-failing RECOMMENDED-path assertion now passes with `single_source_exposure is True` throughout. No other file, function signature, or architectural decision changes.

## 21. Final disposition

Governance correction complete. Root cause identified and resolved at the relationship-semantics layer, with zero Gate F (`krm.py`/`drm.py`) weakening — the failing tests correctly caught a real modeling defect and remain fully authoritative. `product/wow-i4-b1`'s broken diagnostic diff is preserved (`git stash`, `stash@{0}`) and exported to a durable patch file outside the repository for reference; nothing was committed or discarded. No implementation performed by this artifact itself.

Safe to proceed to a corrected I1 implementation attempt when the operator directs it, following §20 exactly. Not safe to resume from the stashed diff without applying §20's corrections first.
