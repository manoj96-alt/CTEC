# CDD-092 — Noetva OQI Governed Propagated Ontology Exposure (Activate · Harden · Expose CDD-042)

**Status:** FROZEN
**Version:** 1.0
**Date:** 2026-10-11
**Originating phases:** NOETVA-OQI-PROPAGATED-IMPACT-DR → NOETVA-OQI-PROPAGATED-IMPACT-G
**Architectural authority:** **CDD-042** (OQI4 Ontology Impact Intelligence) and its *Ordered Relationship-Instance Path Amendment*. This document is explicitly **subordinate** to CDD-042: it activates, hardens, and exposes the propagation capability CDD-042 already froze and implemented. It authorizes **no replacement traversal engine**, no new persistence architecture, and no schema migration. Where this document narrows a CDD-042 rule (edge/node eligibility, §5–§6) or corrects implementation conformance to it (digest, §12), it says so explicitly; every other CDD-042 decision stands unchanged.
**Precedent for form:** CDD-042 is evolved only by new companion documents, never by in-place edits of frozen text (CDD-042 Ordered Relationship-Instance Path Amendment). CDD-092 follows that precedent.

---

## 1. Governing baseline (independently re-derived at G)

```
Implementation baseline     e8c61ae840f9cef362788dad1ea91f64bd88d276  (tree b6cf3ce2…)
                            = CDD-091 OQI Demo UX Hardening, PASS + CLOSED (VM)
origin/main                 171a398af6d4af6bd2149ff69879f4cdc178ed3e
Migration head (baseline)   0049_oqi_remediation_actor_name
Migration head (origin/main) 0048_oqi_remediation_mutex
PR #253 / PR #254           OPEN, unmerged
Number uniqueness           CDD-092 unclaimed in every local and remote ref at freeze
```

CDD-091 is closed and **must not regress** (§24).

## 2. Discovery facts this document rests on (verified, not assumed)

1. CDD-042 already provides deny-by-default, tenant-scoped, relationship-type-scoped, directional `ImpactPropagationPolicy`; per-policy `max_depth` plus `GLOBAL_MAX_DEPTH_CEILING = 10`; one recursive-CTE snapshot with tenant re-applied at every step; path-local cycle safety; one current row per element; the 3 shortest distinct ordered relationship-instance paths retained; deterministic evaluation identity bound to `finding_state_revision + traversed_state_digest`; an immutable ledger plus current projection.
2. **`propagated_path = None` in Golden is not a defect of traversal, transport, or the frontend.** No production path enrolls any `ImpactPropagationPolicy` (only tests do) — CDD-042 defect **OQI-P3-007**. A disposable experiment proved that enrolling exactly three FORWARD policies makes the *unmodified* engine produce Meridian Cell Components → Aurora X1 Battery Cell (depth 1) → Aurora X1 Bill of Materials (depth 2) → Aurora X1 (depth 3).
3. **Latent correctness defect:** the traversal ignores edge and node governance state. Disposable proof: Draft/Proposed (unapproved), Suspended, and expired edges all carried impact once a policy existed.
4. **Read-model defect:** `get_ontology_impact` exposes only `propagated_rows[0]` and only bare relationship UUIDs, so Aurora X1 never surfaces and the panel cannot name anything.
5. **Digest conformance defect:** the evaluator records `(relationship_id, 1)` instead of the relationship's real `version_number`, contrary to CDD-042 §11.4.
6. **Unbounded path enumeration:** the CTE materializes every simple path before the 3-path retention. A disposable adversarial graph (width 200, 3 layers → 8,000,000 paths) held one statement for more than 9 minutes before cancellation. An outer `LIMIT` was measured to stop PostgreSQL's recursion early (50,001 rows in 0.49 s on that same graph); a realistic large supplier (1,000 materials × 10 BOMs × 1 product) enumerates 21,000 rows in 0.45 s.
7. Schema facts: `institutional_relationships` and `enterprise_entities` carry `lifecycle_state` (`lifecyclestate_t`: Draft, Active, Suspended, Archived), `governance_status` (`governancestatus_t`: Proposed, Approved, Retired, Archived), `effective_from` (NOT NULL), `effective_to` (nullable); edges additionally carry `superseded_by_id` and `version_number`; nodes carry no `superseded_by_id`. Tenant-qualified composite FKs make a cross-tenant edge structurally impossible. Relationship types are a global registry; candidacy is modelled as a relationship **type** (`candidateFor`).
8. Effective-time convention in this repository is half-open `[effective_from, effective_to)` — the exact predicate already used for "currently valid `supplies` relationships" on this same table (`integration/adapters/gate_f/krm.py`).

## 3. Product claim (frozen)

> A quality finding on an entity can **expose** downstream ontology elements when an enrolled propagation policy permits traversal across an eligible governed relationship between eligible governed entities.

Propagation is **exposure through governed dependencies** — not causation, not criticality, not severity, not a truth claim about any source value. **PATH ≠ CAUSATION. REACHABILITY ≠ CRITICALITY.**

## 4. Core propagation equation (frozen)

**ENROLLED ACTIVE POLICY** (tenant, relationship type, direction) **+ ELIGIBLE RELATIONSHIP INSTANCE + ELIGIBLE TARGET NODE + ALLOWED DIRECTION + DEPTH WITHIN POLICY AND GLOBAL BOUNDS = PROPAGATABLE HOP.** No single condition suffices. The anchor (the directly-impacted entity) must itself be eligible (§6) for any propagation to occur from it; DIRECT impact itself is unchanged by this rule.

## 5. Edge eligibility (frozen — narrows CDD-042 §7)

An `institutional_relationships` row may carry propagated exposure at evaluation time `t` only if **all** hold:

```
tenant_id          = evaluation tenant
lifecycle_state    = 'Active'
governance_status  = 'Approved'
effective_from    <= t
effective_to IS NULL OR effective_to > t          (half-open; effective_to = t is NOT effective)
superseded_by_id IS NULL
```

Deterministic exclusion of: lifecycle Draft, Suspended, Archived; governance Proposed, Retired, Archived; future `effective_from`; expired (`effective_to <= t`); any superseded row. `t` is the single evaluation moment (`evaluated_at`) supplied to the traversal as an explicit `as_of` parameter — never an implicit database clock, never defaulted.

## 6. Node eligibility (frozen)

An `enterprise_entities` row may participate (as the anchor, an intermediate, or a target) only if **all** hold: tenant = evaluation tenant; `lifecycle_state = 'Active'`; `governance_status = 'Approved'`; `effective_from <= t`; `effective_to IS NULL OR effective_to > t`. A valid edge never tunnels through an ineligible node. An ineligible anchor yields DIRECT impact only (unchanged) and zero propagation. Nodes carry no supersession column; no supersession predicate is invented for them.

Both predicates are applied **inside the single recursive CTE statement** (CDD-042 §9 snapshot invariant preserved).

## 7. Direct-impact precondition (unchanged CDD-042)

Propagation occurs only when direct outcome = `IMPACTED`. `IMPACT_UNKNOWN` and `NO_IMPACT` never manufacture downstream exposure. **UNKNOWN ≠ LOW. ABSENT ≠ NOT IMPACTED.**

## 8. Candidate, authority, and direction semantics (frozen)

- `candidateFor` is **not enrolled** in v1; deny-by-default excludes it — the traversal never hard-codes any type name. Proposed relationship rows are ineligible (§5). **CANDIDATE ≠ TRUTH.**
- Separate eligible Approved relationships each participate independently: no majority vote, no collapse, no authority-based selection; distinct relationship instances remain distinct path proofs. **AUTHORITY ≠ TRUTH. MAJORITY ≠ TRUTH.** Relationship-level evidence disagreement is out of scope.
- Direction remains policy-controlled. No global direction is encoded in the traversal.

## 9. Golden policy enrollment (frozen)

`demo_oqi_seeder.py` enrolls, idempotently (skip if the deterministic ID exists), inside `_seed_aurora_ontology_chain` **after** the chain edges are flushed and therefore **before** `_evaluate`:

| policy_id | relationship type | direction | max_depth | status | version |
|---|---|---|---|---|---|
| `680b9f10-82c4-57e6-8655-16bc54bb2d78` = `_uid("impact-propagation-policy:supplies:FORWARD")` | `supplies` | FORWARD | 5 | Active | 1 |
| `42554a60-e7c6-5d03-be94-5258bca06641` = `_uid("impact-propagation-policy:usedIn:FORWARD")` | `usedIn` | FORWARD | 5 | Active | 1 |
| `5c9ca4d7-b3a7-5276-941f-573b22b03712` = `_uid("impact-propagation-policy:defines:FORWARD")` | `defines` | FORWARD | 5 | Active | 1 |

Tenant `ctec-demo-tenant`; `_uid(label) = uuid5(BOOTSTRAP_SEED_NAMESPACE, "oqi-demo:" + label)`. Policies govern relationship **types**; traversal operates on eligible relationship **instances**. No Meridian/Aurora logic, no entity-ID or name matching, no hard-coded hop count. REVERSE/BOTH are **not** authorized for these policies. Re-seeding and Golden restore leave exactly three policy rows (proven in the packaged runtime).

## 10. Depth (frozen)

Golden supply-dependency policies use `max_depth = 5`, chosen for the general shape supplier → component → sub-assembly → BOM → product, not for Golden's three hops. `GLOBAL_MAX_DEPTH_CEILING = 10` is unchanged.

## 11. Cycles, multiple paths, divergence/convergence (unchanged CDD-042)

Path-local visited set: no entity repeats within a path; a cycle terminates only that branch, never produces UNKNOWN, never fails the evaluation, never yields duplicate cyclic paths. One current propagated row per element; at most `MAX_RETAINED_PATHS_PER_ELEMENT = 3` distinct ordered relationship-instance paths retained, ordered by (depth, ordered relationship-instance-ID sequence) — never by row order. One finding may expose many elements; one element may be reached by several retained paths; the element is never duplicated.

**Total path count is NOT exposed in v1.** Persisting it requires a schema change (e.g. an observation column), which CDD-092 does not authorize (§16). The UI states "Showing the 3 shortest governed paths" when three are retained. Total-count exposure is deferred.

## 12. Digest correction and temporal binding (frozen — CDD-042 §11.4 conformance)

The traversal returns each hop's real `institutional_relationships.version_number`; the evaluator records `(relationship_id, actual version_number)` in `traversed_relationships`. Evaluation identity remains `tenant + finding_family + finding_id + finding_state_revision + traversed_state_digest` (deterministic UUIDv5). No global ontology version. `evaluated_at` for a current-state evaluation is the same single moment passed as `as_of`. `PropagatedPathCandidate.relationship_versions` and the traversal `as_of` parameter are **required** — never defaulted (a default would silently reintroduce version 1 or hide the eligibility moment).

## 13. Path-enumeration bound (frozen — new safety rule)

`MAX_PROPAGATION_PATH_ROWS = 50_000` (constant in `oqi_ontology_impact_evaluation_repository.py`, alongside `MAX_RETAINED_PATHS_PER_ELEMENT`; revisable only by governance amendment). The CTE's final `SELECT` is fetched with `LIMIT MAX_PROPAGATION_PATH_ROWS + 1`, which stops recursion early. If more than the ceiling are returned, traversal raises `PropagationBoundExceededError` and the evaluation **fails closed**: nothing is persisted, the prior current projection stays untouched, callers report the ontology-impact step as FAILED (CDD-042 §13: an operational failure, never `IMPACT_UNKNOWN`, never a truncated result). Within the ceiling, results are complete and deterministic.

## 14. Re-evaluation, Business Impact, Reliance, criticality, attributes, agents, Ask Noetva (frozen boundaries)

- Recomputation keeps existing triggers (evaluation orchestration, remediation preparation, seeding, Golden restore). Existing projection semantics already retire elements no longer reached (ACTIVE → RESOLVED); `IMPACT_UNKNOWN` never retracts. Event-driven ontology-change re-evaluation: **DEFERRED**.
- OQI6 Business Impact derivation: **unchanged.** Golden HIGH remains anchored on the supplier's direct dependency; no downstream Business Impact is created for propagated elements. **PROPAGATED EXPOSURE ≠ BUSINESS CRITICALITY.**
- Reliance computation and orchestration: **unchanged.** No automatic Reliance evaluation for propagated elements (downstream Reliance orchestration DEFERRED).
- No severity, distance, confidence, or criticality score. **REACHABILITY ≠ CRITICALITY.**
- No attribute-level propagation (CDD-042 §4.7 stands). Allowed: "Aurora X1 is exposed to unresolved supplier evidence." Not allowed: "the country-of-origin error breaks Aurora X1", "Aurora X1 cannot launch".
- No agent participates in the computation. **AGENT ≠ FACT.**
- Ask Noetva's in-memory reachability is not reused, not modified, and not hardened here.

## 15. Read model, API, enrichment, ordering, explanation (frozen)

- **Read model:** `OntologyImpactRow.propagated_impacts: tuple[PropagatedImpactRow, ...]` — every ACTIVE propagated element, never only the first. `PropagatedImpactRow(entity_id, entity_type_name, entity_name, depth, paths)`; each path a tuple of `PropagatedImpactHopRow(relationship_instance_id, relationship_type_name, direction, from_entity_id, from_entity_name, to_entity_id, to_entity_name)` in traversal order (for REVERSE hops `from`/`to` follow traversal, not stored, orientation).
- **Enrichment:** names/types are read-time presentation from two batched reads (relationships ⋈ relationship types; entities ⋈ entity types), both filtered by the requesting tenant. No N+1. IDs from the immutable ledger remain authoritative; names never replace them. **DISPLAY NAME ≠ AUTHORITATIVE IDENTITY.**
- **Ordering:** elements by (depth ascending, `entity_name.casefold()` ascending, `str(entity_id)` ascending); paths in retained order (shortest first, then ordered relationship-ID sequence); hops in traversal order.
- **API:** additive `OntologyImpactResponse.propagated_impacts: tuple[PropagatedImpact, ...]` with `PropagatedImpact` / `PropagatedImpactHop` mirroring the read model. Policy ID/version stay in the ledger and are not added to the primary UX contract.
- **Legacy `propagated_path`:** retained, non-authoritative: the flattened retained hops of the first element in `propagated_impacts` order (`path_ordinal = path_index × 100 + hop_index`). Documented as legacy; not removed in this phase.
- **Wording constraint:** the word "canonical" must not appear in `backend/app/api/oqi/router.py` or `backend/app/api/oqi/schemas.py` (an existing H3 guard test asserts its absence).
- **Explanation:** deterministic, structured, never LLM-generated, never persisted as prose; the UI composes "{from} {relationship label} {to}" from hops (camelCase relationship names humanized, e.g. `usedIn` → "used in").

## 16. Storage and migration (frozen)

No new persistence architecture. **No schema migration.** The isolated prototype proved the complete capability with zero DDL. If implementation finds a migration necessary: **STOP**.

## 17. Frontend experience (frozen)

`OntologyImpactPanel` (IMPACTED branch) replaces the placeholder canvas ("Propagated (FORWARD)" nodes, UUID lists) with comprehension-first UX: (1) summary — "This unresolved finding exposes N downstream entities through governed ontology dependencies."; (2) primary chain to the deepest exposed element — supplier ↓ supplies Battery Cell ↓ used in BOM ↓ defines Aurora X1 — with a line that exposure is not a truth claim or a criticality measure; (3) every exposed entity, each expandable to its retained paths, with "Showing the 3 shortest governed paths" when three are retained; (4) the accessible path-detail section retained, now named. IMPACT_UNKNOWN and NO_IMPACT branches unchanged. **Absence language:** when no propagated exposure exists: "No governed propagated exposure is recorded for this Finding." — never "not impacted". No new generic graph explorer. Quality bar: an executive understands issue → governed chain → exposed product in seconds, without UUIDs.

**CEO/VC claim allowed:** "SAP says US and PLM says MX for Meridian Cell Components. Through governed, approved dependencies, Meridian supplies the Aurora X1 Battery Cell, which is used in the Aurora X1 BOM that defines Aurora X1. Aurora X1 is therefore exposed to this unresolved supplier evidence, and Noetva shows the exact governed path." **Not allowed:** US/MX is true; the launch fails; the disagreement causes product failure; Aurora X1 is necessarily blocked; reachability establishes criticality.

## 18. Golden demo-verify (frozen)

`demo-verify` gains check `ontology_propagated_chain`, read through the same governed read model the API uses: direct = Golden supplier; exposed elements exactly `[(Battery Cell, 1), (BOM, 2), (Aurora X1, 3)]` in order (no extra element); Aurora X1's retained paths exactly `[("supplies", "usedIn", "defines")]`. The pre-existing formatting of unrelated `database_cli.py` code (e.g. the `golden_demo_restore` assertion) must **not** be reformatted.

## 19. Isolated prototype evidence (G)

Disposable detached worktree at `e8c61ae`, scratch-committed only inside it, never pushed, discarded after use; disposable PostgreSQL databases and Docker stack only.

```
Prototype diff        16 files, +1113 / −156, sha256 6e48e2ae412107a6b21aa5939ab9ac045e8bc4c93a8e939fd70b8b33fd0aca32
Backend full suite    2408 passed, 0 failed  (2380 baseline + 28 net new; dirty-tree guard passes)
Ontology-impact PG + service suites  77 passed (all 37 pre-existing PG tests unchanged in behavior)
Golden story          19 passed (incl. D16 propagated chain)
mypy / ruff           clean (663 files)
Frontend              tsc 0 errors; Vitest 463/463 (one pre-existing intermittent ontology-studio test
                      flaked once, 30/30 ×3 in isolation and 463/463 on rerun; untouched by CDD-092);
                      Gate X 5/5; ESLint clean; Prettier clean; next build passes; tree clean after build
Docker (packaged)     images built from prototype commit; migration head 0049; Golden seed → golden-demo-restore
                      → demo-verify: [PASS] ontology_propagated_chain -- exposed=3
                      aurora_paths=[('supplies','usedIn','defines')]; ALL CHECKS PASSED; re-seed keeps 3 policies
Path explosion        unbounded: 8,000,000-path graph >9 min (cancelled); bounded: LIMIT 50,001 in 0.49 s;
                      realistic 21,000 rows in 0.45 s
Hidden-caller search  every constructor/fixture of changed types inside the ceiling; out-of-ceiling hits are
                      read-only consumers (test_generic_finding_detail_parity.py,
                      test_oqi_product_experience_service.py, conflict-lens.tsx, page.tsx, api-client.ts) proven
                      green without change
```

## 20. Exact implementation path ceiling (frozen)

| # | Path | Action | Authorized change |
|---|---|---|---|
| 1 | `backend/app/infrastructure/persistence/oqi_ontology_impact_evaluation_repository.py` | MODIFY | §5–§6 eligibility CTEs; anchor eligibility; `rel_version` in traversal; required `as_of`; `relationship_versions` on `PropagatedPathCandidate`; §13 ceiling constant, `LIMIT`, `PropagationBoundExceededError` |
| 2 | `backend/app/application/oqi_ontology_impact_evaluation_service.py` | MODIFY | single moment as `as_of`/`evaluated_at`; real relationship versions in the digest |
| 3 | `backend/app/application/oqi_product_experience_service.py` | MODIFY | §15 read model, batched tenant-filtered enrichment, ordering, legacy field |
| 4 | `backend/app/api/oqi/schemas.py` | MODIFY | additive `PropagatedImpact`, `PropagatedImpactHop`, `propagated_impacts` |
| 5 | `backend/app/api/oqi/router.py` | MODIFY | map `propagated_impacts` |
| 6 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | MODIFY | §9 Golden policy enrollment |
| 7 | `backend/app/infrastructure/persistence/database_cli.py` | MODIFY | §18 demo-verify check only |
| 8 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | MODIFY | `as_of` on existing traversal calls; §21 crowns |
| 9 | `backend/app/tests/test_oqi_ontology_impact_service.py` | MODIFY | fake repository `as_of`; `relationship_versions` on fixtures; digest-version and shuffled-order crowns |
| 10 | `backend/app/tests/test_oqi_api_router.py` | MODIFY | `propagated_impacts=()` on the fake ontology-impact row |
| 11 | `backend/app/tests/test_noetva_demo_readiness_golden_story.py` | MODIFY | D16 Golden propagated-chain crown |
| 12 | `frontend/lib/oqi/contracts.ts` | MODIFY | required `propagated_impacts`, `PropagatedImpact`, `PropagatedImpactHop` |
| 13 | `frontend/app/quality/findings/[findingId]/_components/ontology-impact-panel.tsx` | MODIFY | §17 UX |
| 14 | `frontend/tests/oqi-finding-detail.test.tsx` | MODIFY | fixtures; replace opaque-UX assertions with chain/absence crowns |
| 15 | `frontend/tests/oqi-conflict-lens.test.tsx` | MODIFY | `propagated_impacts: []` on two typed fixtures |
| 16 | `frontend/tests/oqi-product-truth.test.tsx` | MODIFY | `propagated_impacts: []` on one typed fixture |

**Counts: MODIFY = 16, CREATE = 0, DELETE = 0, TOTAL = 16.** This governance artifact is not part of the implementation ceiling. No other path. No wildcard. No generated-file, formatting, migration, or "small test fix" exception. Reformatting pre-existing code outside the authorized hunks is not authorized.

## 21. Test crowns (frozen minimum)

Real PostgreSQL wherever traversal behavior is asserted.

- **Edge eligibility:** Active+Approved+currently effective eligible; Draft, Suspended, Archived lifecycle; Proposed, Retired, Archived governance; future-effective; expired; `effective_to = as_of`; superseded → excluded.
- **Node eligibility:** Draft, Suspended, Archived; Proposed, Retired, Archived; future-effective; expired → no tunnelling; ineligible anchor → no propagation.
- **Broken path:** A→B→C→D with B→C ineligible plus A→E valid → exactly {B, E}.
- **Tenant:** composite-FK cross-tenant edge rejected (existing); foreign-tenant policy never enables edges; per-step tenant re-application (existing); enrichment tenant-filtered; a foreign tenant reading the finding gets nothing.
- **Cycle:** existing self-loop and 3-cycle remain green under the eligibility CTEs.
- **Multi-path:** existing diamond/cap/ordering tests; read-model diamond target carries its retained paths.
- **Path explosion:** ceiling met exactly → full result; ceiling exceeded → `PropagationBoundExceededError`.
- **Digest version:** traversal carries the real `version_number`; a changed version changes digest and evaluation identity.
- **Determinism:** shuffled candidate order → identical evaluation identity, observations, paths.
- **Read model / API:** all elements in (depth, name, id) order, enriched names/types, legacy field retained, zero/one/many elements, no false NO_IMPACT.
- **Frontend:** summary count; Golden chain with relationship labels and names; multiple exposed elements; no "Propagated (FORWARD)" placeholder or UUID-only primary UX; absence honesty; IMPACT_UNKNOWN/NO_IMPACT unchanged.
- **Golden story:** D16 exact chain and relationship-instance IDs; D7 Business Impact HIGH and D8 Reliance AT_RISK unchanged; agents not invoked; uniqueness unchanged.

## 22. Docker and Azure authorization (frozen)

- **Docker is mandatory** before any cloud step: backend and frontend images built for `linux/amd64` from the exact implementation commit; database at the correct migration head (`0049_oqi_remediation_actor_name` on the CDD-091 baseline; no new migration); Golden restore; `demo-verify: ALL CHECKS PASSED` including `ontology_propagated_chain`; the propagated chain visible in the packaged API/UI.
- **Azure:** deployment only to the dedicated demo environment (`rg-noetva-demo`) after all local and Docker gates pass, following the established CDD-090 manual procedure (build, push, bind by digest; migrate job; backend and frontend apps; golden-restore job bound to the same backend digest). No dev deployment, no production deployment, no CIAM mutation, no migration expected. Golden restore only via the governed job.
- **Live Golden crown:** from the Golden finding UI/API — direct Meridian Cell Components; exposed Aurora X1 Battery Cell, Aurora X1 Bill of Materials, Aurora X1; path supplies → usedIn → defines; tenant correct; relationship instances and enrolled policies (IDs and versions) real; paths deterministic; no candidate or ineligible edge; no UUID-only explanation; Business Impact HIGH, Reliance AT_RISK, agent honesty, and CDD-091 authority UX unchanged.

## 23. Implementation structure and order (frozen)

**Single I phase** (DR → G → I → VM): no migration, one coherent capability, backend/API/UI must agree, and no independent correctness boundary was found. Order: (1) eligibility CTEs + `as_of`; (2) relationship-version digest; (3) path ceiling; (4) traversal crowns; (5) Golden policy enrollment; (6) read model + batched enrichment; (7) API contract; (8) frontend contract; (9) panel UX; (10) demo-verify; (11) full regression and full-gate proof against the exact 16-path diff; (12) Docker; (13) Azure demo Golden crown.

## 24. CDD-091 regression requirements

Self-approval guard unchanged (`decided_by == authorization.requested_by`, machine IDs only); display identity presentation-only; requester/decider snapshots unchanged; OpenAPI actor-spoofing protections unchanged; authorization-dialog and session-control tests green; `test_oqi_remediation_identity_binding_postgres.py` 36/36.

## 25. Frozen invariants

CONNECTED ≠ IMPACTED · PATH ≠ CAUSATION · REACHABILITY ≠ CRITICALITY · CANDIDATE ≠ TRUTH · UNKNOWN ≠ LOW · ABSENT ≠ NOT IMPACTED · AUTHORITY ≠ TRUTH · MAJORITY ≠ TRUTH · AGENT ≠ FACT · PROPAGATED EXPOSURE ≠ BUSINESS CRITICALITY · DISPLAY NAME ≠ AUTHORITATIVE IDENTITY · PROPAGATED IMPACT REQUIRES AN ENROLLED POLICY · REQUIRES AN ELIGIBLE GOVERNED EDGE · REQUIRES ELIGIBLE GOVERNED NODES · EVERY PROPAGATED ELEMENT HAS A RETAINED GOVERNED PATH PROOF · PROPAGATION IS BOUNDED AND FAILS CLOSED.

## 26. Implementation STOP conditions

STOP — GOVERNANCE BOUNDARY if: a path outside §20 is required; a migration becomes necessary; traversal needs new infrastructure; policy semantics need expansion (including REVERSE/BOTH enrollment); Business Impact or Reliance must change; candidate semantics must change; Ask Noetva must be modified; tenant isolation cannot be preserved; the path ceiling cannot be enforced or must change; deterministic ordering cannot be guaranteed; Docker behavior differs materially from source; Golden data is insufficient; Azure requires unrelated mutation; CDD-091 regresses.

## 27. Deferred (explicitly outside CDD-092)

Total path-count exposure (needs schema); downstream Business Impact derivation; downstream Reliance orchestration; event-driven re-evaluation on ontology/policy change; relationship-level evidence disagreement; attribute-level causal lineage; policy-authoring UI/API for enterprise tenants (the adoption half of OQI-P3-007); Ask Noetva lifecycle hardening; Golden supplier entity-type fidelity ("System Actor" rather than "Supplier"); Gate S sibling authority-binding; frontend container healthcheck; deployment-pipeline Golden-restore rebinding; demo API resource URI variable; dialog centering; `CTEC_ENVIRONMENT` cleanup; optionalClaims cleanup; generalized instruction actor display; unrelated CDD numbering cleanup.

---

*CDD-092 authorizes governance only. It does not implement, deploy, or verify anything itself. It is subordinate to CDD-042, which remains the architectural authority for OQI4 ontology impact.*

---

# CDD-092 R1 — Governance Correction: Upgrade-Safe Golden Policy Enrollment

**Status:** FROZEN (R1)
**Version:** 1.1 (R1 amendment; v1.0 text above is unchanged and remains frozen)
**Date:** 2026-10-11
**Originating phases:** NOETVA-OQI-PROPAGATED-IMPACT-I (STOPPED — MATERIAL DEFECT / GOVERNANCE BOUNDARY) → NOETVA-OQI-PROPAGATED-IMPACT-G-R1
**v1.0 SHA-256 (sections 1–27 exactly as frozen at `995abac`):** `0382f8769dd5da334603cb778ca4135639f79090b904e946386e8a79e60a1b1e`
**Form:** append-only. Sections 1–27 are not rewritten; where R1 supersedes a v1.0 rule it says so explicitly (R1.4 supersedes the *placement* and *idempotency* sentences of §9 only; the §9 policy table is unchanged).

R1 changes exactly three things: (1) the lifecycle placement of Golden propagation-policy enrollment; (2) semantic validation of a pre-existing deterministic policy before it is accepted; (3) the pre-cloud upgrade-path proof standard. Every other CDD-092 v1.0 decision stands unchanged (R1.15).

## R1.1 Original freeze (v1.0 §9)

v1.0 §9 froze enrollment "inside `_seed_aurora_ontology_chain` after the chain edges are flushed and therefore before `_evaluate`", idempotent by "skip if the deterministic ID exists", and asserted that "Re-seeding and Golden restore leave exactly three policy rows (proven in the packaged runtime)". The packaged proof behind that sentence (§19) ran on a **fresh** database only.

## R1.2 Defect

`DemoOqiSeeder._seed_context` returns early for an already-seeded tenant, before `_seed_aurora_ontology_chain` is reached. A Golden tenant created by any image that predates enrollment therefore never receives the policies; `_evaluate` then runs OQI4 under deny-by-default with zero policies and records no propagation. Traversal, API, frontend, policy IDs and Docker packaging behaved correctly; the defect is solely the frozen enrollment *placement*.

## R1.3 Azure incident evidence (read-only, re-verified at G-R1)

- Candidate `80ac89a56085fcf6459273fef4356a55da1b11a4` deployed to demo: backend `sha256:470bfd0b569351f12eac50256a4f68584dd880b01249c2e7037e7a2eb372a19e` (`noetva-demo-eus2-backend--0000003`), frontend `sha256:1919d905d231ddc80bcf1a96dcd51cba0e94b336185e15f283aac2bc71f39e0e` (`--0000005`), Golden Restore job rebound to the backend digest (configuration diff: image only); migrate job untouched on `sha256:c34e8ed5…`.
- Golden Restore execution `noetva-demo-eus2-golden-restore-c1qqsrc` (started 2026-10-11T19:27:35Z): status **Failed**. Log Analytics (`ContainerAppConsoleLogs_CL`): 15 checks, 14 PASS, sole failure `[FAIL] ontology_propagated_chain -- exposed=0 aurora_paths=[]`, then `demo-verify: CHECKS FAILED`. SAP=US, PLM=MX, HIGH Business Impact, RELIANCE_AT_RISK, Ask Noetva, H6 candidate all PASS.
- Reproduced byte-for-byte locally at G-R1 with the same digest `470bfd0b…` against a database created by the previously certified runtime (R1.10): identical single failure, policies = 0.

## R1.4 Corrected architecture (supersedes the placement and idempotency sentences of §9)

**Invariant — GOLDEN PROPAGATION POLICY ENROLLMENT IS UPGRADE-SAFE:** every Golden seed/restore execution idempotently ensures, and semantically validates, the frozen propagation-policy set **after context ensure and before ontology-impact evaluation**, regardless of whether the base Golden tenant data was created in the current execution or by a previous application version.

Frozen placement — **Option A, seed-lifecycle orchestration**, the single authoritative enrollment location:

```
DemoOqiSeeder.seed(tenant_id)
  1. tenant validation            (DemoTenantRequiredError if not an allowed seed tenant)
  2. self._seed_context(tenant_id)          -> fresh bootstrap OR existing-tenant early return
  3. self._enroll_golden_propagation_policies(tenant_id)   [R1]
  4. self._evaluate(tenant_id, dependency_id)
  (5. commit is owned by the caller)
```

Enrollment is **removed** from `_seed_aurora_ontology_chain` (no duplicate defensive location). The §9 policy table, tenant, deterministic IDs, FORWARD-only, `max_depth = 5`, Active, version 1, `previous_version_id = NULL`, and deny-by-default are unchanged.

**Option B (enroll at the top of `_evaluate`) — rejected.** It is equally reachable today, but it makes an evaluation step perform bootstrap mutation; evaluation must consume governed policy state, not create it. Option A keeps `_evaluate` evaluation-only and places reference-data lifecycle in the orchestration method every entry point already converges on.

## R1.5 Call-graph and control-flow reachability proof (at `80ac89a`, repository-wide search)

Production entry points into `DemoOqiSeeder` (search: `DemoOqiSeeder(`, `.seed(`, `_seed_context(`, `_seed_aurora_ontology_chain(`, `_evaluate(`; non-app files: workflows, Bicep, Dockerfile/entrypoint, docs):

| # | Entry point | Route | Commit boundary |
|---|---|---|---|
| A | `database_cli golden-demo-restore` (`database_cli.py:457`) | safety predicate → scoped 4-table DELETE → `DemoOqiSeeder(session).seed(tenant_id=BOOTSTRAP_DEMO_TENANT_ID)` (`:519`) | single `session.commit()` after `seed()` returns |
| B | `database_cli demo-reset` (`database_cli.py:80`; `seed()` at `:105`) | `reset_database()` → OntologySeeder commit → BlueprintSeeder commit → `DemoOqiSeeder(session).seed()` | `session.commit()` after `seed()` returns |
| C | `python -m app.infrastructure.persistence.demo_oqi_seeder` (`__main__`, `:2146`) | `DemoOqiSeeder(session).seed()` | `session.commit()` after `seed()` returns |

Classification of every other hit: the Azure Golden Restore job (Bicep `container-apps-job-golden-restore.bicep:65`; workflow `azure-golden-demo-restore.yml` only starts that job) runs **A** then `demo-verify`; CI (`ci.yml:275`) and `DOCKER_SMOKE_TEST.md` run **C**; the backend `docker-entrypoint.sh` runs migrations + OntologySeeder + BlueprintSeeder only (never `DemoOqiSeeder`); `database_cli seed` is the unrelated EDT-001 `SeedLoader` (correction to the I-phase stop report, which mislabeled `:105` as the seed CLI — it is `demo-reset`). Test callers (golden story ×2, H4 integrity crown, generic finding-detail parity) call `seed()` and are not production paths. Other `*Seeder.seed()` hits are unrelated classes. **No fourth production path exists.**

Inside `DemoOqiSeeder` at `80ac89a`: `_seed_context` is called only by `seed()` (`:436`); `_evaluate` only by `seed()` (`:437`); `_seed_aurora_ontology_chain` only by `_seed_context` (`:688`). Branches of `seed()`:

- `tenant_id not in _ALLOWED_SEED_TENANTS` → raise before any mutation or evaluation (nothing to enroll; correct).
- `_seed_context` has exactly two returns: the existing-tenant early return (`:451–452`, taken when an active QualityRule `_QUALITY_CONDITION_ID` **and** an active supplier dependency exist) and the fresh-bootstrap return (`:689`, after `_seed_aurora_ontology_chain`). **Both** return control to `seed()`, which then unconditionally executes step 3 before step 4. Any exception inside `_seed_context` propagates out of `seed()` before evaluation.
- There is no return, branch, or exception handler in `seed()` between steps 2, 3 and 4. Therefore every production Golden evaluation reached through A, B or C executes enrollment first. Proven dynamically (R1.9 crown 2): with a pre-upgrade tenant, `_seed_aurora_ontology_chain` is not called and `_evaluate` observes 3 policies on entry.

## R1.6 Transaction atomicity

`_enroll_golden_propagation_policies` uses the caller's session and only `flush()`es; it never commits. A, B and C each commit once, after `seed()` returns. Any failure in policy validation, policy creation (including a database constraint violation), traversal or evaluation raises out of `seed()`; the caller's session is closed without commit, so nothing — including A's preceding scoped DELETE — is committed. No intermediate commit is introduced. Proven: conflict crowns leave planted rows and evaluation counts unchanged (R1.9). Partial committed upgrade is therefore impossible through A, B or C.

## R1.7 Existing-policy validation (frozen)

For each `(policy_id, relationship_type_name)` in `_GOLDEN_PROPAGATION_POLICIES`:

1. Resolve `relationship_type_id` by `relationship_types.relationship_type_name` (`supplies` / `usedIn` / `defines`). Absent → `GoldenPropagationPolicyConflictError` (fail closed).
2. Look up `impact_propagation_policies` by primary key `policy_id` (tenant-independent lookup, so a frozen ID present under another tenant is detected, not silently re-inserted).
3. **Not present** → create exactly the frozen policy via `OqiOntologyImpactPolicyRepositoryImpl.create(ImpactPropagationPolicy(...))` (the single authorized ORM construction site).
4. **Present and semantically identical** → accept without any write (no update, no new version, row byte-identical).
5. **Present under the deterministic ID with any differing governed field** → `GoldenPropagationPolicyConflictError`; never accept, update, overwrite, retire, re-version, or proceed to evaluation.
6. **Slot occupied by a different-ID Active policy** for the same `(tenant_id, relationship_type_id, direction)` → the insert in step 3 is rejected by the database (R1.8); not bypassed, not pre-empted by application logic.

Partial sets are handled by the same per-policy rule: only missing frozen policies are created. **Governed runtime** produces only 0 or 3 correct policies (all three are written in one session and committed together; there is no production policy-authoring API; the seeder is the only production writer). Partial sets are an **adversarial / out-of-band** recovery state and are tested as such.

**Comparison fields (exact model names; the table has no other columns besides the key `policy_id`, so no persistence metadata is excluded or compared):**

| field | frozen value |
|---|---|
| `tenant_id` | the seeded tenant (`ctec-demo-tenant` for the Golden demo) |
| `relationship_type_id` | id of `supplies` / `usedIn` / `defines` respectively |
| `direction` | `FORWARD` |
| `max_depth` | `5` |
| `governance_status` | `Active` |
| `version_number` | `1` |
| `previous_version_id` | `NULL` |

Note (consistent with the existing seeder design): Golden deterministic IDs, policy IDs included, are tenant-independent `uuid5` labels, so one database hosts one Golden seed tenant; a frozen policy ID owned by a different tenant is a semantic conflict (`tenant_id`) and fails closed.

**Error contract:** one new exception, `GoldenPropagationPolicyConflictError(Exception)`, declared in `demo_oqi_seeder.py` beside the existing `DemoTenantRequiredError` (seeder-local fail-closed convention). No existing exception fits: `DemoTenantRequiredError` is tenant-scope only and `ValidationException` is domain-input validation. Message names the policy ID, the relationship-type name, and the **names** of mismatched governed fields only — no values, no secrets.

## R1.8 Database-constraint interaction

- `uq_impact_propagation_policies_one_active`: partial unique index on `(tenant_id, relationship_type_id, direction) WHERE governance_status = 'Active'` (CDD-042 §8).
- `uq_impact_propagation_policies_tenant_pk`: unique `(tenant_id, policy_id)`; `policy_id` is the primary key.

Application validation protects **same ID / wrong semantics**; the database protects **different ID / conflicting Active slot**. R1 adds no application logic duplicating or weakening the index. A committed different-ID Active policy can exist only while the frozen policy is absent; enrolling the frozen policy then raises `IntegrityError` naming `uq_impact_propagation_policies_one_active` and the seed transaction fails closed (proven).

## R1.9 Prototype evidence (isolated worktree, scratch commits never pushed, destroyed after capture)

Prototype base `80ac89a`; R1 delta (2 paths) sha256 `3ea258993cb338daa2210b574f143320764f0d3f92a5fb7567a71f0939e96b4d` (reference only; I-R1 re-implements it). Real PostgreSQL; each crown runs the production `DemoOqiSeeder.seed()` inside one outer transaction that is rolled back. Pre-upgrade state is produced by running the real seeder with the policy set empty (the pre-enrollment seeder's observable behavior); the packaged crown (R1.10) is the authoritative upgrade proof.

| # | Crown (`test_oqi_ontology_impact_postgres.py`) | vs `80ac89a` seeder | vs R1 seeder |
|---|---|---|---|
| 1 | `test_cdd092r1_fresh_golden_seed_enrolls_frozen_policies_then_propagates` | pass | pass |
| 2 | `test_cdd092r1_preseeded_zero_policy_tenant_is_upgraded_before_evaluation` | **FAIL** (`['_evaluate:policies=0']`) | pass (`['_evaluate:policies=3']`; chain helper not called) |
| 3 | `test_cdd092r1_repeated_seed_is_row_identical` | pass | pass |
| 4 | `test_cdd092r1_partial_policy_set_is_completed_without_touching_the_existing_one` | **FAIL** | pass |
| 5–10 | `test_cdd092r1_deterministic_id_with_wrong_semantics_fails_closed` [direction, max_depth, governance_status, version_number (governed v2 with Retired v1 predecessor), relationship_type, tenant] | **FAIL** ×6 (no validation exists) | pass ×6 (raises; row untouched; evaluation count unchanged) |
| 11 | `test_cdd092r1_different_id_active_conflict_is_rejected_by_the_database` | **FAIL** (enrollment never reached) | pass (`IntegrityError` on `uq_impact_propagation_policies_one_active`; nothing written) |

Expected chain in crowns 1–4: Aurora X1 Battery Cell depth 1 → Aurora X1 Bill of Materials depth 2 → Aurora X1 depth 3. Adversarial pre-state is written through the governed repository (the CDD-042 single-construction-site guard `test_oqi4_ontology_impact_orms_have_single_construction_site` stays green).

Full prototype gates: backend **2424 passed / 0 failed** (2413 + 11); ruff clean; mypy clean (663 files); frontend tsc 0, Vitest **464/464**, Gate X **5/5**, `next build` exit 0; CDD-091 identity crown **36/36**, authorization UI **48/48**; prototype final feature diff vs `e8c61ae` = exactly the §20 16 paths (16 M / 0 A / 0 D); no migration (head `0049_oqi_remediation_actor_name`).

## R1.10 Packaged upgrade crowns (prototype, linux/amd64, real PostgreSQL 17)

The exact Azure job command (`golden-demo-restore` then `demo-verify`) was used for every restore.

1. **Old certified runtime establishes the pre-upgrade database.** Old image `noetvademoeus2acr.azurecr.io/noetva/backend@sha256:c34e8ed5f06ddad441aa354641b5a752d787cc30b8a11f5c727d53133188967a` (= ACR tag `e8c61ae840f9cef362788dad1ea91f64bd88d276` = Azure revision `--0000002`) against a fresh persistent volume: its own entrypoint (migrate + ontology + Blueprint seed), its seeder `__main__`, its Golden Restore job → `demo-verify: ALL CHECKS PASSED` (14 checks). Result: head `0049`, Golden supplier and chain edges present, **propagation policies = 0**, 0 active propagated impacts.
2. **Azure failure reproduction** (copy of that database): candidate `80ac89a` image `470bfd0b…` Golden Restore → `[FAIL] ontology_propagated_chain -- exposed=0 aurora_paths=[]`, `demo-verify: CHECKS FAILED`, 14 PASS, policies 0.
3. **Upgrade:** same volume and database (not recreated), R1 prototype image → `[PASS] ontology_propagated_chain -- exposed=3 aurora_paths=[('supplies', 'usedIn', 'defines')]`, literal `demo-verify: ALL CHECKS PASSED` (15 checks); exactly the three frozen policy rows (IDs/semantics per §9); depths 1/2/3 Battery Cell → BOM → Aurora X1; head `0049`.
4. **Repeated new-image restore** on the same database: PASS / ALL CHECKS PASSED; policy rows byte-identical (3); propagated chain identical.
5. **Azure-history replay** (old → `80ac89a` failed → R1 on the reproduction copy): PASS / ALL CHECKS PASSED; policies 3.
6. **Fresh new-image database** (separate PostgreSQL; R1 image entrypoint, seeder `__main__`, Golden Restore job): PASS / ALL CHECKS PASSED (15); policy rows identical to the upgraded database.

## R1.11 Path ceilings (frozen)

**Final feature ceiling** (final candidate vs certified feature baseline `e8c61ae`): unchanged — exactly the 16 §20 paths, **16 MODIFY / 0 CREATE / 0 DELETE**, no migration.

**R1 correction ceiling** (I-R1 commit(s) vs `80ac89a`): exactly **2 MODIFY / 0 CREATE / 0 DELETE**:

1. `backend/app/infrastructure/persistence/demo_oqi_seeder.py` — add `GoldenPropagationPolicyConflictError`; add `_enroll_golden_propagation_policies`; call it in `seed()` between `_seed_context` and `_evaluate`; remove enrollment from `_seed_aurora_ontology_chain`. Nothing else.
2. `backend/app/tests/test_oqi_ontology_impact_postgres.py` — the eleven R1.9 crowns and their fixtures/helpers (outer-transaction rollback; adversarial pre-state only through the governed repository; Golden-scoped policy queries).

Any other path relative to `80ac89a` → STOP. The other 14 CDD-092 paths are **not** reopened by R1.

## R1.12 Implementation authorization (NOETVA-OQI-PROPAGATED-IMPACT-I-R1)

Base: `80ac89a…` on `product/oqi-propagated-impact-i` (do not redo the feature from `e8c61ae`). Implement only R1.4–R1.8 within R1.11. Helper responsibility is frozen narrowly: *ensure that the exact CDD-092 Golden propagation-policy definitions exist and semantically match their deterministic identities* — it must not evaluate, modify edges/findings/Business Impact/Reliance, author arbitrary policies, expose any API, commit, or reconcile semantic conflicts.

Required before any Azure mutation (all must pass): R1.11 ceilings (both ledgers); the eleven R1.9 crowns; full backend; ruff; mypy; frontend tsc, Vitest, Gate X, `next build`; CDD-091 identity and authorization crowns; CDD-092 propagation crowns including the 50,000-row fail-closed crown; Docker fresh Golden Restore; **packaged old-image (`sha256:c34e8ed5…`) → new-image persisted-database upgrade** with `[PASS] ontology_propagated_chain` and literal `demo-verify: ALL CHECKS PASSED`; repeated new-image restore with byte-identical policy rows. Fresh-Docker success alone never authorizes cloud deployment.

## R1.13 Azure boundary

- **State at G-R1 freeze (read-only):** the separately authorized rollback has **not** occurred. Live: backend `--0000003` (`470bfd0b…`, 100%), frontend `--0000005` (`1919d905…`, 100%), Golden Restore job `470bfd0b…`, migrate job `c34e8ed5…` (untouched). Certified revisions `--0000002` (`c34e8ed5…`) and `--0000004` (`caf36622…`) exist inactive (Single revision mode). Last Golden Restore execution: `…-c1qqsrc` Failed (R1.3).
- **I-R1 Azure crown** (only after R1.12 passes): deploy the exact corrected backend/frontend digests to demo under the CDD-090 manual procedure (linux/amd64, ACR push, bind by digest); bind the Golden Restore job to the exact corrected backend digest; do **not** touch the migrate job; run Golden Restore against the real long-lived demo database; require `[PASS] ontology_propagated_chain` and `demo-verify: ALL CHECKS PASSED`; only then live API/UI crown and the CEO/VC screenshot.
- **Failure on R1:** if Golden Restore again reports `exposed=0` or any failure → STOP; no manual policy insertion, no database patching, no demo-verify bypass, no screenshot.
- **No manual policy repair:** no recovery procedure may insert the three policies into Azure PostgreSQL by hand; the application lifecycle must upgrade its own governed bootstrap data.
- No Golden Restore job logic/configuration change; no migrate rebinding; no CIAM, dev or production change. G-R1 performed no Azure mutation.

## R1.14 Invariants (frozen)

- **FRESH-BOOT SUCCESS ≠ UPGRADE SAFETY.**
- **DETERMINISTIC IDENTITY ≠ SEMANTIC EQUIVALENCE.**
- **GOLDEN RESTORE MUST ENSURE REQUIRED GOVERNED BOOTSTRAP DATA BEFORE EVALUATION.**
- **BOOTSTRAP RECONCILIATION MUST FAIL CLOSED ON SEMANTIC CONFLICT.**
- **PREVIOUS-RUNTIME → CANDIDATE-RUNTIME UPGRADE PROOF IS REQUIRED FOR NEW SEEDED STATE.**
- **POLICY ENSURE OCCURS AFTER CONTEXT ENSURE AND BEFORE EVALUATION, ON EVERY BRANCH.**

## R1.15 Unchanged by R1

Propagation meaning; policy IDs and semantics; edge/node eligibility; explicit `as_of`; direct-impact precondition; direction; depth; cycles; the 50,000-row fail-closed ceiling; path retention; digest correction; persistence; read model; API; UX; tenant isolation; Business Impact, Reliance, Agent and Ask Noetva boundaries; the CEO/VC claim; CDD-091.

## R1.16 STOP conditions (I-R1)

STOP if: any production entry point bypasses `seed()` steps 3→4; a path outside R1.11 is required; a migration is required; a deterministic-ID conflict does not fail closed; a different-ID Active conflict can coexist with the frozen policy; any failure leaves committed partial state; the packaged old runtime cannot establish a representative pre-upgrade database; the new runtime cannot upgrade it without manual repair; fresh bootstrap regresses; repeated restore duplicates or re-versions policies; propagation semantics, Business Impact or Reliance must change; Azure Golden Restore fails for any reason; CDD-091 regresses.

## R1.17 Program-level recommendation (recorded, not enacted here)

**FRESH-BOOT PASS IS NOT DEPLOYMENT PROOF.** Any feature that introduces or changes required seeded / reference / bootstrap state for an existing environment should prove: (1) fresh bootstrap; (2) already-seeded upgrade; (3) previous packaged runtime → candidate packaged runtime upgrade on a persisted database; (4) repeated candidate idempotency. **BOOTSTRAP + UPGRADE + IDEMPOTENCY + CONFLICT SAFETY = DEPLOYMENT CORRECTNESS.** No other governance artifact is modified by R1.

## R1.18 Deferred

Everything in §27, plus: a generic bootstrap-reconciliation framework for other seeded reference data; tenant-scoped deterministic Golden IDs; any policy-authoring surface; adoption of R1.17 into program-wide delivery doctrine.

---

*CDD-092 R1 authorizes governance only. It does not implement, deploy, or verify anything itself. CDD-092 remains subordinate to CDD-042.*
