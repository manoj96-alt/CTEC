# CDD-086 — Noetva Material-Aware Alternative Supplier Discovery and Explainable Supply Chain Decision Intelligence (Discovery + Resolution + Governance)

**Status:** Discovery/Resolution/Governance only. No implementation authorized by this artifact. Supersedes no prior CDD; CDD-085 remains frozen and unmodified (re-verified byte-identical throughout this artifact's authoring: SHA-256 `4780bb04a030fc766f73f3eb5a78168933ca1a1412b1027a321daccc7b9bb389`).

**Trigger:** Operator visual rejection of WOW-I4-B1-R3 (`product/wow-i4-b1` @ `ec0d6abaf0d8863e882a138ada57a1f86e7ad22f`). R3 improved presentation but explained the wrong product story: a tenant-wide entity-type scan presented as "alternative discovery," with no material-aware relevance model. This artifact re-derives the actual architecture independently from source (not from the R3 report) and freezes the target model.

---

## 1. Independently re-derived current-state provenance

Re-traced directly from source, not assumed from any prior report:

- `backend/app/infrastructure/persistence/demo_gate_f_seeder.py`: seeds exactly **one** `Alternate Supplier`-typed entity (`gate-f-demo:alternate-supplier`, "Demo Alternate Supplier (Gate F)"), tenant-wide, shared across all three demo scenarios. It carries four literal assertions (`qualification=true`, `capacity=true`, `leadTimeDays=21`, `costUsd=185000`) from a "Gate F Demo Supplier Portal" source system. **It has no `supplies` (or any other) relationship to any Material in seed data today** — confirmed by reading the seeder's full relationship list (`locatedIn`, `exposedTo`, `supplies`, `usedIn`, `defines`, `assembledAt`, `generatesRevenue` — none touch the Alternate Supplier entity).
- `backend/app/application/supply_chain_impact_api.py::_evaluate`: discovery is
  ```python
  alternate_supplier_ids = tuple(sorted(
      (entity.entity_id for entity in entities_by_id.values()
       if entity.entity_type_name == ALTERNATE_SUPPLIER_ENTITY_TYPE_NAME),
      key=str,
  ))
  ```
  — a **tenant-wide entity-TYPE scan**, independent of the Material under evaluation. It is genuinely dynamic (not a hardcoded id) and would return every such entity if more than one existed, but it is **not material-aware**: it has no relationship to the disrupted Material, the disrupted Supplier, or any governed sourcing fact.
- `backend/app/integration/adapters/gate_f/krm.py::derive_candidate_evidence`: for each discovered id, creates a fresh `candidateFor` relationship instance and reads whatever `qualification`/`capacity`/`leadTimeDays`/`costUsd` assertions already exist on that entity. Real, non-fabricated evidence — but evaluated against a candidate SET that was never material-aware in the first place.
- `backend/app/integration/adapters/gate_f/drm.py::_classify`: the real, unmodified four-condition binary policy (CDD-015 §11): high-severity disruption, single-source exposure, revenue materiality (`>$10,000,000`), qualified+capacity-sufficient alternate. AND-logic short-circuit; any positively-False condition → REJECTED with a specific, distinguishable reason (`GateFOutcomeReason`); all positively-True → RECOMMENDED; otherwise (Unknown, none False) → no record (UNKNOWN, never fabricated).

## 2. Exact limitation of current tenant-wide type discovery

Today's discovery answers "which entities are *typed* Alternate Supplier," never "which entities *supply the affected Material*." The conceptual failure case from the governing prompt is real and reproducible against current code: a `Supplier`-typed entity D that supplies only Material X (never M) would **not** be excluded by today's logic if it were mistakenly typed `Alternate Supplier` — and, conversely, a genuine alternate source of Material M that happens to be typed plain `Supplier` (as every other real supplier in this ontology is) is **structurally invisible** to today's discovery, because discovery filters on `entity_type_name == "Alternate Supplier"`, not on any `supplies` relationship to M. The current single seeded Alternate Supplier's lack of any `supplies` edge (§1) is not an oversight in isolation — it is the direct, necessary consequence of a type-scan that never asked "supplies what?"

## 3. Decision on the "Alternate Supplier" entity type

**Decision: (B) — migrate toward ordinary `Supplier` entities plus a governed `supplies` relationship; do not treat "alternate" as an intrinsic entity type.**

Reasoning, verified against the ontology's own schema (`backend/app/infrastructure/persistence/ontology_seed.py`):
- `REQUIRED_RELATIONSHIPS` already declares `("supplies", "Supplier", "Material")` as a first-class, governed relationship binding. This is exactly the fact a material-aware candidate needs to carry — a real `Supplier` supplying the affected `Material` — and it already exists, unmodified, in the frozen SS3 vocabulary.
- "Alternativeness" is not a property of a supplier; it is a property of a *decision context* (this supplier is an alternative *to Supplier A*, *for Material M*, *right now*). Modeling it as a standalone entity type conflates identity with role, and is why today's implementation could only ever answer "who is typed Alternate Supplier," never "who else can supply this."
- No real enterprise system (ERP/SRM/PLM) carries an "Alternate Supplier" master-data type distinct from Supplier. Every supplier in Noetva's own governed ontology should be an ordinary `Supplier`; "alternative" is the *result* of a query (§5), not a label on a row.
- `candidateFor` (`Alternate Supplier` → `Material`) is retained as a concept — it already correctly captures "this pairing was formally evaluated as a candidate" — but its domain binding must migrate from `Alternate Supplier` to `Supplier` (§4). This is a metadata-level `OntologyRelationshipBinding` change (curated governance metadata, not a runtime-enforced constraint — confirmed no code path validates writes against it), not a breaking schema change.
- Rejected alternative (A, retain Alternate Supplier): would require every real alternative source to be re-typed away from `Supplier` before it could ever be discovered, permanently coupling "is a candidate" to a manual re-typing step — precisely the "answer-bearing seed" anti-pattern the governing prompt forbids (§8 of the governing prompt).
- Rejected alternative (C): no other existing entity type or relationship pattern in the current ontology better fits; (B) reuses 100% existing, already-governed vocabulary.

**Migration is NOT authorized or performed in this artifact.** It is frozen as the target for a future implementation phase (§25).

## 4. Target ontology relationship model

Reuse the existing, unmodified `supplies` relationship type (`Supplier → Material`) as the sole discovery signal. No new relationship type is invented — this directly satisfies the governing prompt's §7 instruction to prefer an existing governed relationship over a new one. `SOURCED_FROM`/`SUPPLIER_OF`/`PROVIDES`/`QUALIFIED_FOR` were considered and rejected: none exist in the current 10-relationship SS3 vocabulary, and `supplies` already carries the exact semantic needed (an organization providing a material to the enterprise).

`candidateFor` (`Supplier` → `Material`, binding updated per §3) is retained as the **relevance/provenance** relationship: KRM continues to create one fresh instance per (candidate, material) pair actually evaluated, but that pairing is now genuinely meaningful — "this candidate was evaluated because it has a governed `supplies` relationship to the affected Material" — rather than "we tried this entity because of its type."

## 5. Material-aware candidate-discovery algorithm

Verified directly against `backend/app/domain/ontology_copilot/traversal.py` and `backend/app/infrastructure/persistence/institutional_relationship_store.py`:

- `find_paths_to_target_type` is a **forward-only** BFS (adjacency built from `edge.from_entity_id`); it cannot answer "who points at this Material," only "where can I reach from this Supplier." It is not directly reusable for reverse (incoming-edge) discovery without a new function.
- `InstitutionalRelationshipStore.load_tenant_graph(tenant_id)` already loads the **entire** tenant's entities and edges into memory as `(entities_by_id, edges)` — and `supply_chain_impact_api.py::_evaluate` already holds exactly this data in scope, at the exact point where the current type-scan runs. **No new database query is required.**

**Target algorithm** (pure, deterministic, domain-layer — new function in `traversal.py`, e.g. `find_entities_with_relationship_to`):
```
candidates = { e.from_entity_id for e in edges
               if e.relationship_name == "supplies"
               and e.to_entity_id == affected_material.entity_id
               and e.from_entity_id != disrupted_supplier.entity_id }
```
i.e., every entity with a real `supplies` edge into the affected Material, excluding the disrupted supplier itself (governing prompt §3, example E). This is symmetric to, and can share logic with, the already-existing reverse-style query in `krm.py::derive_single_source_exposure` (which already filters `InstitutionalRelationship` by `relationship_type_id == supplies AND to_entity_id == material_entity_id` — today only to *count* them, not to return them). The target function generalizes that exact, already-proven pattern from "count" to "return the set," operating on the in-memory graph already loaded rather than a second database round-trip.

Excluded from the candidate set: entities reachable only via other relationship types (`usedIn`, `defines`, `locatedIn`, etc.) even if incidentally typed `Supplier`; the disrupted supplier itself; any entity outside the tenant (structurally impossible — `load_tenant_graph` is tenant-scoped by construction, RFC-016).

## 6. Candidate relevance / explainability model

Five distinct concepts (governing prompt §6), each independently representable in already-existing or minimally-extended data:

1. **Relevance** — "why was this candidate considered?" → the real `supplies` edge discovered in §5; exposed on `CandidateOutcome` as a new field naming the governing relationship (e.g. `relevance_relationship: "supplies"`) plus the real material name/id it was matched against. Backed by the real, freshly-created `candidateFor` relationship instance (unchanged mechanism, corrected input).
2. **Evidence** — the existing `qualification`/`capacity`/`leadTimeDays`/`costUsd` assertions, unchanged (`CandidateOutcome.evidence`).
3. **Eligibility** — the existing per-condition tri-state facts (`GovernedFact`), already correctly modeled as True/False/Unknown with assertion provenance; R3's frontend "Governed conditions" checklist already renders this using real fields.
4. **Recommendation** — the existing, unmodified DRM `outcome`/`reason`/`narrative`/`structured_reasons`/`confidence` — deterministic policy output, never recomputed client-side.
5. **Authorization** — the existing, unmodified GRM `governance_standing` (`HUMAN_APPROVAL_REQUIRED`) and the frozen human-authority sentence. No action control exists or is proposed.

These five must never collapse into one another (governing prompt §6): a candidate can be *relevant* (supplies the material) without being *eligible* (may fail qualification/capacity); *eligible* without being *recommended* (DRM's four-condition AND-logic is stricter than eligibility alone — e.g. the supplier-level conditions 1-3 must also hold); *recommended* without being *authorized* (a human must still approve); never *executed* (no such capability exists anywhere in this route).

## 7. Evidence / provenance architecture

Unchanged from today's real, already-governed mechanism: every evidence fact is a persisted `Assertion` row (predicate/value/source_system/asserted_on), attached to the `candidateFor` relationship instance via `InstitutionalRelationshipAssertions`, and surfaced as `SupportingKnowledgeReference`s in the decision record's `knowledge_references`. No new provenance mechanism is needed — only the *input* to discovery changes (§5), not how evidence is subsequently derived or recorded.

## 8. Eligibility architecture

Unchanged: `GovernedFact(value: bool | None, assertion_id: UUID | None)` already correctly encodes "Unknown ≠ False" at exactly the needed granularity, with a pointer to the backing assertion when known. No new eligibility model is required.

## 9. Gate F ownership / refactor decision

**Decision: discovery moves to the ontology/orchestration layer; Gate F's KRM/DRM adapters are unchanged in responsibility.**

`supply_chain_impact_api.py` already explicitly owns "traversal orchestration" (its own module docstring) — it already calls `find_paths_to_target_type` for impact propagation and risk-event lookup, and already loads the full tenant graph before any Gate F adapter runs. Replacing its current `alternate_supplier_ids` type-scan (8 lines) with a call to the new §5 discovery function is a **same-layer, same-file, minimal, boundary-respecting change**. `gate_f/krm.py::derive_candidate_evidence` and `gate_f/drm.py::_classify` require **zero logic change** — they already operate per-candidate-id, agnostic to how that id was discovered. Gate F does not gain, and should not gain, generic ontology-discovery semantics — it continues to answer only "what do we know about this candidate" and "what does policy conclude," never "who is a candidate."

## 10. API contract decision

**Additive only, backward-compatible.** `CandidateOutcomeResponse` (`backend/app/api/supply_chain_impact/schemas.py`) gains one new, optional-on-read field surfacing §6 item 1 (relevance): the governing relationship name and the affected-material reference already known to the caller via `impact.materials`. No existing field is removed, renamed, or reinterpreted. `frontend/lib/supply-chain-impact/contracts.ts` mirrors the addition exactly, as every prior round in this phase has done. This is a UI-adjacent field ("why was this shown"), not a UI-shaped one — it states a real governed fact (which relationship connected this candidate), not a presentation concern.

## 11. Multiple-candidate behavior

Already structurally supported end to end today (`materials[].candidates[]` is already a list; `AlternativesPanel` already renders the full array, not index 0). The only change is that the *set* discovery produces will, with corrected seed data (§19), genuinely contain more than one entry. No ranking is introduced — Gate F has no ranking policy; DRM classifies each candidate independently. `#1`/`Top`/`Best`/`Preferred`/`Optimal`/`Winner` remain forbidden (unchanged truth-contract term from R2/R3, reaffirmed).

## 12. UNKNOWN / conflicting evidence behavior

"Missing evidence → Unknown, never False" is already correctly implemented (`GovernedFact`, `_latest_assertion` returning `None` when nothing is asserted). **Gap, disclosed rather than hidden (governing prompt §13):** `_latest_assertion` silently resolves multiple assertions on the same predicate by recency (`ORDER BY effective_from DESC, asserted_on DESC LIMIT 1`) — genuinely *conflicting* evidence (two assertions disagreeing at the same effective time) is not detected or surfaced today; it is masked as "latest wins." This is a **pre-existing limitation, out of scope for this DRG phase** — flagged for a future, separately-governed assertion-conflict CDD if ever required. Candidate relevance itself must never depend on eligibility evidence being complete (§5's discovery test is purely relationship-based, independent of whether qualification/capacity are known) — an incomplete-evidence candidate still appears, correctly, as a relevant-but-Unknown-eligibility candidate, never silently dropped.

## 13. OQI integration decision

**Decision: do not couple.** OQI's Reliance/evidence-fitness capability answers a different question (is a *governed finding* fit for use, across a data-quality corpus) than Gate F's per-candidate tri-state evidence (does *this specific assertion* exist for *this specific candidate*). Coupling them would conflate two genuinely distinct, already-separately-governed semantics — exactly the risk the truth contract exists to prevent (relationship ≠ causation; the same discipline applies to capability boundaries). Gate F's own `GovernedFact` pattern already fully satisfies the "Unknown ≠ False" requirement without any OQI dependency.

## 14. Tenant-isolation proof architecture

Structural, not procedural: `InstitutionalRelationshipStore.load_tenant_graph` is tenant-scoped by its own `WHERE tenant_id == ...` query, and RFC-016's tenant-qualified composite foreign keys make it structurally impossible for one tenant's `institutional_relationships` rows to reference another tenant's `enterprise_entities`. Because the new discovery function (§5) operates purely on the `(entities_by_id, edges)` already produced by this tenant-scoped load, it inherits tenant isolation **by construction** — no new isolation logic is needed or should be written. Adversarial test M (§21) proves this observationally (a cross-tenant Supplier with a real `supplies` edge to a same-named Material in a different tenant must never appear).

## 15. $12M business-exposure provenance

Traced exactly, unchanged from R2/R3's own verified chain: `Product --generatesRevenue--> RevenueExposure` (real relationship, `_traverse_impact`), `RevenueExposure` entity carries a real `annualRevenueUsd` assertion (`"12000000"`, source "Gate F Demo Finance/BI"), read by `krm.py::derive_revenue_materiality` and compared (backend-only, never client-side) against the governed `$10,000,000` materiality threshold (`GateFPolicyConfiguration.materiality_threshold_usd`). The UI's `$12,000,000` is this exact asserted value, currency-formatted — not a decorative or computed number. No causal claim beyond "this product's associated revenue-exposure entity carries this asserted figure" is made or proposed; hop-grouping truth boundary (relationship ≠ traced item-to-item causation) is unaffected by this phase.

## 16. Frontend information architecture (target, conceptual — not frozen pixel-for-pixel)

Preserves the explanatory sequence from the governing prompt §12: disruption → what's affected (ontology impact, unchanged from R3) → what alternatives Noetva found (relevance-first: "supplies the same Material" stated explicitly per candidate, not just a name) → evidence per candidate → eligibility/policy assessment per candidate → recommendation → human authority. Exact labels/layout are explicitly **not** frozen here (governing prompt §12) — they are implementation-phase (I3) design work, informed by real API data once §10's field exists.

## 17. Legacy secondary-navigation resolution

Investigated further per governing prompt §18/R3's own governance-gap flag. `secondaryNavItems` (`Home`/`Architecture`/`Dataset`/`Prototype`/`About`) remains frozen "preserved exactly" across CDD-033 §5 item 1 (origin), CDD-062 §3, CDD-079's I1 authorization table, and CDD-084 §23/FORBIDDEN — four independent governing artifacts, none superseded here. **Resolution direction frozen:** deprecate the standalone secondary-nav row in favor of folding genuinely-still-needed reachability (`/about`, `/architecture`) into a single utility affordance (e.g. a footer or account-menu entry), while `/` (Home) and `/dataset`/`/prototype` are evaluated for retirement given CDD-084's own finding that `/` is "a 6-section, pre-Observatory, zero-`--obs-*`-token marketing landing page" no longer representative of the authenticated product. **Not implemented here** — this is architecturally appropriate to fold into I1/I3 of this phase's own implementation (§25) *only if* it can be done as a narrow, separately-tested slice; otherwise it remains its own future CDD. Route reachability must be preserved for any route with a real inbound link elsewhere (CDD-084 §9's home-page reachability finding) until that reachability is deliberately migrated, not silently dropped.

## 18. Demo seed-data migration strategy

**Required, not optional**, given §1's finding that today's single Alternate Supplier has zero `supplies` edges. New seed data must express the governing prompt's own conceptual example directly:
```
Supplier A (disrupted) --supplies--> Material M
Supplier B             --supplies--> Material M
Supplier C             --supplies--> Material M
Supplier D             --supplies--> Material X   (never M)
```
with B/C carrying real qualification/capacity/leadTimeDays/costUsd assertions (varied, so RECOMMENDED/UNKNOWN/eligibility-failure scenarios remain genuinely distinguishable — e.g. B fully qualified, C missing capacity evidence). **Must NOT seed** any `alternateSupplierForA`/`bestAlternative`/`recommendedSupplier`/`candidateSupplierIds`-shaped field or relationship — the candidate set must be a pure *consequence* of the `supplies` edges, provable by adding/removing exactly those edges without any code change (adversarial tests F/G, §21). This directly supersedes `demo_gate_f_seeder.py`'s current single-alternate design; the three existing scenarios (RECOMMENDED/UNKNOWN/REJECTED) must be re-verified to still produce their intended outcome under the new, relationship-derived candidate set.

## 19. Adversarial test matrix

All twenty items from the governing prompt §19 are adopted verbatim as the mandatory acceptance bar for the future implementation phase, mapped to concrete assertions:

| # | Test | Proves |
|---|---|---|
| A-D | A supplies M; B supplies M → discovered; C supplies M → discovered; D supplies X only → NOT discovered | Relationship-driven, type-independent discovery |
| E | A never returned as its own alternative | Self-exclusion |
| F | Remove B→M edge (fixture/seed change only) → B disappears | No code-level hardcoding |
| G | Add D→M edge (fixture/seed change only) → D appears | No code-level hardcoding |
| H | Multiple candidates returned in one evaluation | List, not singleton, semantics |
| I | No ranking language/order-as-rank claim absent a governed ranking policy | Truth contract |
| J/K | Missing qualification/capacity → Unknown, not False | Tri-state fidelity |
| L | A candidate that fails qualification/capacity shows the real, specific rejection reason | `GateFOutcomeReason` fidelity |
| M | Cross-tenant Supplier with a same-shaped `supplies` edge never appears | Tenant isolation (§14) |
| N | Provenance (source system, assertion id, relationship id) preserved end to end | Evidence architecture (§7) |
| O | Each candidate's relevance explanation names the real governing relationship | §6 item 1 / §10 field |
| P/Q | Zero candidate-discovery or policy-calculation logic exists in `frontend/` | Frontend boundary (§16 of governing prompt) |
| R | `outcome`/`reason`/`narrative`/`confidence` remain byte-identical to backend response | No recomputation |
| S/T | Exact human-authority sentence present; zero action controls; no autonomous-execution implication | Truth contract |

## 20. Docker / Azure proof strategy (design only — not executed in this phase)

A future implementation phase should prove discovery is real, not re-seeded-as-an-answer, via a two-step Azure demonstration against the DEV/DEMO tenant: (1) evaluate with seed state `{A→M, B→M, C→M, D→X}`, capturing the candidate set `{B, C}`; (2) apply a **governed relationship-only** demo-data mutation — remove `C→M`, add `D→M` — through the existing seeder mechanism (never a manual DB edit), redeploy nothing (no application code changes between steps), re-evaluate, and capture the candidate set `{B, D}`. Because no code changes between steps, this is a direct, reproducible proof that candidates are derived, not seeded as an answer. The safest governed method is a dedicated, clearly-labeled demo re-seed script variant (mirroring `demo_gate_f_seeder.py`'s own idempotent, tenant-restricted, CLI-only precedent), run against DEV only, never DEMO/production, with an explicit before/after API response capture as the artifact of proof.

## 21. Backward compatibility / rollback

Additive API field (§10): existing consumers unaffected. Ontology binding change (§3/§4, `candidateFor` domain from `Alternate Supplier` to `Supplier`) is metadata-level, not runtime-enforced (§3) — reversible without data loss. Seed-data migration (§18) is scoped to the labeled demo tenant only (`demo_gate_f_seeder.py`'s existing `_ALLOWED_SEED_TENANTS` guard, unchanged), never touches `main`/production data. R1/R2/R3's visual work on `product/wow-i4-b1` is explicitly preserved (governing prompt §23) — selectively reusable in the eventual I3 (frontend) slice, not discarded. Azure rollback revisions (`--wowi4b1r1/r2/r3`, backend `--0000007`) remain untouched.

## 22. Exact implementation phases

Per governing prompt §22 ("prefer fewer phases if quality/correctness allow"): **two phases**, not three, because I1 (ontology/domain discovery) and I2 (Gate F/API integration) touch the same file (`supply_chain_impact_api.py`) for the same reason (replacing one discovery call) and are not independently testable or deployable — splitting them would create an intermediate, non-functional state. I3 (frontend) is correctly separate: it depends on the new API field (§10) actually existing, is a materially larger, independently-reviewable diff, and is where the real Azure visual-acceptance checkpoint belongs (governing prompt §22's own requirement).

- **DRG (this artifact):** discovery, resolution, governance. No code change. — COMPLETE.
- **I1 — Ontology + Discovery + Gate F integration:** new `traversal.py` reverse-lookup function; `supply_chain_impact_api.py` discovery-call replacement; `ontology_seed.py` `candidateFor` binding update; `demo_gate_f_seeder.py` migration to the B/C/D-style relationship-driven fixture; `CandidateOutcomeResponse`/`contracts.ts` additive field; full adversarial test matrix (§19) as real, passing tests (backend + a thin frontend contract test). Backend-only visible surface plus the one additive frontend contract file — no visual UI change in this slice.
- **I2 — Supply Chain decision-intelligence UX:** the frontend information architecture (§16), built on I1's real `relevance_relationship` field — reusing R1/R2/R3's Observatory visual language and, selectively, its already-accepted composition patterns (evidence ledger, governed-conditions checklist) — culminating in real Azure visual operator acceptance before any merge, per the identical "Claude changes the product, Azure proves the product, operator acceptance closes the visual decision" discipline used throughout this phase family.
- **VM:** cross-phase verification, full regression, final merge decision — only after I2's own operator acceptance.

WOW-I4-B2 (Ontology Modeling) remains fully governed by CDD-085 and untouched, sequenced strictly after this phase's own VM, unchanged.

## 23. Exact CREATE/MODIFY/DELETE path authorization

**None authorized by this artifact.** This is a discovery/governance artifact only. Path authorization for I1/I2 is deferred to a follow-on authorization artifact (either an amendment to this CDD or a new CDD), to be written and frozen immediately before I1 implementation begins — following the exact CDD-085 precedent of separating architecture-freeze from implementation-authorization. Anticipated (not authorized) I1 surface, for planning only: `backend/app/domain/ontology_copilot/traversal.py`, `backend/app/application/supply_chain_impact_api.py`, `backend/app/infrastructure/persistence/ontology_seed.py`, `backend/app/infrastructure/persistence/demo_gate_f_seeder.py`, `backend/app/api/supply_chain_impact/schemas.py`, `frontend/lib/supply-chain-impact/contracts.ts`, plus their existing test files.

## 24. Truth-contract audit

Every non-negotiable term from the governing prompt §24 is preserved by this artifact's own decisions: seeded enterprise facts ≠ seeded answer (§18's explicit prohibition, mechanically provable by tests F/G); ontology type match ≠ material-aware discovery (§2's diagnosis, §5's fix); candidate ≠ eligible ≠ recommended ≠ authorized ≠ executed (§6, never collapsed); relationship ≠ causation and hop grouping ≠ traced path (§15, unchanged from R2/R3); missing ≠ false, unknown ≠ failed (§8/§12, unchanged `GovernedFact` semantics); policy confidence ≠ AI confidence, deterministic reasoning ≠ agent reasoning (§9, unchanged Gate F); demo data ≠ customer data (§18's tenant guard, unchanged); remediation ≠ resolution (no remediation capability proposed anywhere in this artifact). Live agent reasoning remains `NOT_INVOKED` — nothing in this artifact invokes, references, or implies any agentic capability.

## 25. Final disposition

Architecture discovered, resolved, and governed. No implementation performed. `product/wow-i4-b1` unchanged at `ec0d6ab` (R3, visually rejected but preserved for selective reuse per §21). CDD-085 unchanged. This artifact (CDD-086) freezes the target model; a follow-on path-authorization artifact is required before I1 implementation may begin.

Safe to proceed to a future I1 path-authorization artifact when the operator directs it. Not safe to begin implementation from this artifact alone (no path authorization exists yet, per §23).
