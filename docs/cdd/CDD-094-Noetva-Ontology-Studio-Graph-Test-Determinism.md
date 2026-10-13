# CDD-094 — Ontology Studio Graph Test Determinism (CI Reliability)

**Status:** FROZEN
**Version:** 1.0
**Date:** 2026-10-13
**Originating phase:** NOETVA-ONTOLOGY-STUDIO-CI-RELIABILITY-DRG (Discover + Resolve + Govern only — implements, pushes, merges, and deploys nothing)
**Authorizes:** NOETVA-ONTOLOGY-STUDIO-CI-RELIABILITY-I (implementation of §8 exactly); integration into PR #255 is authorized separately and exclusively by CDD-093 R2.
**Scope:** One test file. No application, library, configuration, workflow, or dependency change. Not related to propagated-impact semantics.

---

## 1. Numbering

`docs/cdd/CDD-094*` is unclaimed on every local and `origin` ref, in every commit message, and in every open PR (verified at DRG). Highest prior number: CDD-093.

## 2. Incident

PR #255 (head `a686b1b42b7e9bbb2d877f18997812fa24c53ea5`, tree `6b4ec5b495ce08d90fe0ff445f362e7ea10b2632`) has required `backend` and `containers` green but `frontend` failing in three executions on that exact head (runs 38260204447, 38260210921 attempts 1–2), each 463/464, each in `frontend/tests/ontology-studio.test.tsx`, each a different test:

| Execution | Failing test | Failing statement | Missing text |
|---|---|---|---|
| job 114848474681 | "WOW-I3-B-R2: selecting Material distinguishes …" | L874 `fireEvent.click(screen.getAllByText("Material")[0])` | `Material` |
| job 114848451985 | "WOW-I3-B-R2: selecting Contract directly …" | L841 `fireEvent.click(screen.getAllByText("Contract")[0])` | `Contract` |
| job 115087108762 | "WOW-I3-B-R3: Supplier focus mode renders exactly …" | L760 `within(canvas).getAllByText("BOM")` | `BOM` |

All three fail at the same structural point: the first synchronous concept-label query immediately after `await waitFor(() => expect(screen.getByLabelText(/Ontology concept and relationship graph/)).toBeInTheDocument())`. The file is byte-identical on `origin/main`, `2f2cb3c`, and `a686b1b` (blob `d7689631c712a1489f5ceb2636a468320f116247`) and absent from the PR #255 integration diff; the frontend tree is identical on `2f2cb3c` and `a686b1b` (`17201b50230df331e0c4dfed3cb74829ac5b1d21`). CI environment identical across passing and failing runs (Node 22.23.3, runner image ubuntu-24 `20261002.596`, Vitest 3.2.7, npm cache hit, unchanged `vitest.config.ts`); only timing varies (file 1720–3200 ms). CI history (last 60 runs): every frontend failure is in this file and in one of the §4 tests, including two unrelated earlier occurrences (runs 36098552471 and 35568107793: "selecting a concept node shows its detail").

## 3. Root cause (proven)

`StudioClient` renders `ontology-graph.tsx`, whose `<div class="obs-ontology-canvas" role="img" aria-label="Ontology concept and relationship graph">` wraps a `reactflow` 11.11.4 `<ReactFlow nodes={nodes} …>`. ReactFlow v11 copies the `nodes` prop into its internal zustand store inside a **passive effect** (`@reactflow/core` `useStoreUpdater`: `useEffect(() => setStoreState(value), [value])`). Therefore the container commits one render **before** any concept node exists. The initial data arrives via resolved `fetch` promises **outside** `act()`, so React schedules that passive effect asynchronously; Testing Library's `waitFor` can resolve on the container-only commit, and the following synchronous concept query then finds nothing. This is a race between `waitFor` resolution and React's passive-effect flush.

Proof:
1. **Window exists, deterministically** — a MutationObserver probe recorded the DOM at the first moment the container appears: 20/20 runs `{nodes: 0, labels: 0}`; the 6 nodes arrive in a later commit.
2. **Causal amplification** — delaying `useStoreUpdater` by 50 ms (disposable, in a throwaway `node_modules`) makes **exactly the 14 tests of §4 fail and the other 16 pass** in the original file; with the §8 fix, none of the 14 initial-render failures occur.
3. **Natural failure rates (unamplified)** — original file: macOS 5/110 runs; Linux x86_64 Node 22.23.3 container with clean `npm ci` (CI-equivalent) 3/25; every failure one of the §4 tests. With the §8 fix: macOS 0/50, Linux 0/25.
4. **Not order-dependent** — a racy test run entirely alone fails (2/40); `tests/setup.ts` holds no state (inert `ResizeObserver`/`BroadcastChannel` stubs), studio components have no module-level mutable state, `afterEach` unstubs globals, RTL auto-cleanup applies.
5. **Concurrency only modulates probability** — single fork/no file parallelism 0/40; serialization would mask, not remove, the race (rejected, §7).
6. **No post-click race** — selection remounts ReactFlow (`key={selectedName ?? "__overview__"}`), but `fireEvent` is `act()`-wrapped and flushes the remount's passive effects synchronously: 30/30 real runs show the complete focus node set synchronously after the click. (Four further failures seen only under the timer-based amplification are artifacts: `act()` does not flush `setTimeout`.)

**Classification: TEST DEFECT.** The application is deterministic in outcome; the tests await the container instead of the semantic condition their next query depends on. **User/product risk:** at most a single-frame empty canvas before nodes appear on load and on selection (documented, intentional remount design); no functional defect. No application change is warranted or authorized.

## 4. The 14 affected tests (exact; all others unchanged)

Each row: the test whose initial container wait is replaced, and the concept label its next synchronous query depends on.

| # | Test (exact title prefix) | Concept awaited |
|---|---|---|
| 1 | selecting a concept node shows its detail | `Supplier` |
| 2 | CDD-062: concept lifecycle_state and governance_status render as a visual tag, text unchanged | `Supplier` |
| 3 | WOW-I3-B: a curated concept's real discovery_label renders as a truthful provenance badge | `Supplier` |
| 4 | WOW-I3-B: an auto-discovered concept's real discovery_label renders truthfully, never upgraded to Curated | `Supplier` |
| 5 | WOW-I3-B: node selection uses the real --obs-intelligence token, and the legend matches it, never a fabricated OQI/trust/quality annotation on any node | `Supplier` |
| 6 | WOW-I3-B-R3: selecting a concept renders only it and its directly connected concepts inside the focused canvas -- an unrelated concept is absent from the canvas, not merely muted, but remains real (present in Overview mode and Relationship Details) | `Region` |
| 7 | WOW-I3-B-R3: Supplier focus mode renders exactly Supplier/Material/Region/Contract and exactly the supplies/locatedIn/boundBy edges inside the canvas -- no unrelated concept or relationship (usedIn, candidateFor) is rendered | `BOM` |
| 8 | WOW-I3-B-R2: selecting Supplier makes 'Supplier — boundBy → Contract' directly, unambiguously readable in the inspector, with no reversed direction and every other real direct relationship present | `Supplier` |
| 9 | WOW-I3-B-R2: selecting Contract directly, unambiguously exposes both of its real incoming relationships (Supplier via boundBy, Material via coveredBy), with a truthfully empty outgoing set | `Contract` |
| 10 | WOW-I3-B-R2: selecting Material distinguishes its real incoming relationships from its real outgoing relationships, and the full accessible relationship inventory remains available | `Material` |
| 11 | WOW-I3-B-R3: Contract focus mode renders only its two real incoming neighbors (Supplier, Material) in the canvas -- Region, BOM, and Alternate Supplier are absent | `Contract` |
| 12 | WOW-I3-B-R3: Material focus mode renders exactly its 4 real direct neighbors (Supplier, Alternate Supplier, BOM, Contract) in the canvas -- Region is absent | `Material` |
| 13 | WOW-I3-B-R3: an obvious 'View full ontology' control returns from Concept Focus mode to Ontology Overview, restoring the complete real graph in the canvas | `Supplier` |
| 14 | WOW-I3-B-R3: selected/connected concept tiers are distinguished by border width and font weight, not color alone, and a concept with no direct relationship to the selection (Alternate Supplier, when Supplier is selected) is absent from the focused canvas entirely | `Supplier` |

The one other container wait in the file ("CDD-062: static graph legend explains selection border and edge style, adds no new interaction") performs no concept query and is **unchanged**.

## 5. Alternatives

| Option | Decision |
|---|---|
| **Await the rendered concept (semantic condition) via one helper** | **Selected** |
| Increase `waitFor`/`findBy` timeouts | Rejected — does not change what is awaited |
| Sleeps / fake-timer advancement | Rejected — arbitrary, masks the race |
| Retries (`retry`, CI re-runs) | Rejected — certification by repetition |
| Serialize tests / single worker | Rejected — masks, does not remove |
| Skip / `.todo` / weaken assertions / exclude from coverage / make frontend non-required | Prohibited |
| Change `ontology-graph.tsx` (e.g. remove the remount `key`, pre-seed the store) | Rejected — product code is correct; would alter intended behavior |
| Upgrade/replace reactflow | Rejected — out of scope, broad blast radius |

## 6. Invariant

**A test must await the semantic condition its next query depends on — for effect- or store-populated UI, the rendered content itself — never merely the presence of a container.**

## 7. Prohibited

Any change outside `frontend/tests/ontology-studio.test.tsx`; any change in that file other than §8; timeouts, sleeps, fake timers, retries, `.skip`/`.only`/`.todo`; changing any assertion, matcher, selector, fixture, or test title; `vitest.config.ts`, `tests/setup.ts`, workflow, package or lockfile changes; application code changes.

## 8. Authorized change (exact)

Path (only): `frontend/tests/ontology-studio.test.tsx` — MODIFY 1, CREATE 0, DELETE 0.

(a) Insert, immediately after the existing `afterEach(() => { vi.unstubAllGlobals(); });` block, this helper, byte-exact:

```ts
// ReactFlow v11 copies its `nodes` prop into an internal store inside a
// passive effect (`useStoreUpdater`), so the graph container is committed
// one render before any concept node exists. Querying a concept label right
// after merely finding the container therefore races React's passive-effect
// flush. Wait for the rendered concept itself -- the semantic condition the
// following query depends on -- never for the container alone.
async function waitForRenderedConcept(name: string): Promise<HTMLElement> {
  const graph = await screen.findByLabelText(
    /Ontology concept and relationship graph/,
  );
  await within(graph).findAllByText(name);
  return graph;
}
```

(b) In each of the 14 tests of §4, replace the block

```ts
  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
```

with `  await waitForRenderedConcept("<concept from §4>");`. Nothing else changes. The file must be prettier-clean as-is.

Exact result (from origin blob `d7689631c712a1489f5ceb2636a468320f116247`): new blob **`4c6e10fe7029589fb1c387f1d752d5ab92d86649`**; `git diff` (default context) SHA-256 **`0627e47b792a200a22868b63d25baeb6a7be70a93d7afd2c35e03ade9fd0d266`**; numstat +28 −70. Semantic ceiling verified at DRG: 30 tests, 37 `getAllByText`, 16 `fireEvent`, 0 skip/only/todo/sleep/timeout/fake-timer before and after; the 14 removed `expect(container).toBeInTheDocument()` checks are subsumed (not dropped) by `findByLabelText(graph)` (rejects if absent) plus the stronger `findAllByText(concept)`.

## 9. Implementation (NOETVA-ONTOLOGY-STUDIO-CI-RELIABILITY-I)

Branch `product/ontology-studio-ci-reliability-i` from `origin/main` `171a398af6d4af6bd2149ff69879f4cdc178ed3e` (the file is identical on `main` and PR #255); exactly one commit producing blob `4c6e10fe…` with diff fingerprint `0627e47b…`; any difference = STOP. Not merged to `main` independently; it reaches `main` only via PR #255 per CDD-093 R2.

## 10. Required proof (implementation and every later certification)

- Stress: `tests/ontology-studio.test.tsx` ≥ 100 consecutive runs with 0 failures locally, and ≥ 50 consecutive runs with 0 failures in a Linux x86_64 `node:22.23.3` container after a clean `npm ci` (CI-equivalent); plus the causal amplification run showing none of the 14 initial-render failures.
- Full frontend CI contract (Node 22 on GitHub): `npm ci`, `format:check`, `lint`, `typecheck`, `npm test -- --run --coverage` (thresholds met), `build`; Gate X; CDD-091 authorization UI (48/48).
- GitHub: required `frontend` green on the exact integration head per CDD-093 R2 (a re-run is not certification).

## 11. Boundaries

No Azure, CIAM, database, dev, or production action. No change to propagated-impact (CDD-092), authority binding (CDD-090/091), or Golden Demo (CDD-087) semantics.

## 12. STOP conditions

Any further failure in the stress or CI-equivalent runs; any failing test outside §4; any diff beyond §8; the fingerprint/blob mismatching; any required CI failure; any need for a timeout, retry, serialization, or application change.

---

*CDD-094 authorizes governance only. It implements, pushes, merges, and deploys nothing itself.*
