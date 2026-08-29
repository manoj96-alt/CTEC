# CDD-041 OQI3 Atomic Multi-Field Evidence Frontier Amendment

**Status:** APPROVED ARCHITECTURE AMENDMENT
**Version:** 1.0
**Amends:** CDD-041 §21 (CURRENT_STATE algorithm) and its implicit dependence on `select_input_frontier` — narrowly, mechanically, without reopening BusinessRule/InputBinding/AST/Kleene semantics already frozen by CDD-041, the GA amendment, or the G2 amendment
**Precedent:** governance-resolution-then-freeze pattern already exercised twice this gate (OQI3-R2 → OQI3-G2); OQI2's own N-source concurrency discipline (evaluator authority vs. evidence-table coherence kept as two distinct concerns)
**Companion to:** OQI3-R3 (architecture resolution, read-only, this session)

## 1. Discovered defect (reaffirmed from OQI3-I3/OQI3-R3, re-verified fresh in this phase)

OQI3-I3 attempted to implement CURRENT_STATE Finding lifecycle on top of `select_input_frontier` and found — before writing any lifecycle code — that the function performs:

```
select_known_lineage(...)          -- one SELECT
for binding in rule.input_bindings:
    select_latest_field_value(...) -- one SELECT per bound role
```

confirmed by direct read of `oqi_business_rule_evaluation_service.py::select_input_frontier` (lines 217-252) in this phase: known-lineage and every bound role's evidence are **N+1 separate PostgreSQL statements**, not one. The committed adversarial test `test_concurrency_scope_frontier_can_observe_evidence_committed_mid_selection` (`test_oqi_business_rule_postgres.py:1398`) — re-confirmed present and asserting exactly this in this phase — empirically proves a concurrent writer's commit landing between two of those reads is visible to the later read under Postgres's default `READ COMMITTED` isolation (re-confirmed live in OQI3-R3, not merely by grep).

OQI3-R3 established, and this amendment freezes, that seed-3 advisory authority (once implemented by I3) serializes **evaluators against evaluators** — it does nothing for **evaluators against non-participating evidence writers**. No mechanism in this repository currently makes writers participate in Finding authority, no elevated transaction isolation is used anywhere (confirmed by grep across `backend/app` in R3 and re-confirmed absent in this phase), and no single set-based statement currently exists. This is release-blocking per CDD-041's own concurrency-correctness standard and was correctly not downgraded to a P3 by I3.

## 2. Root cause

Artifact-authorization-adjacent architecture gap: CDD-041 §21 assumed evidence selection was already snapshot-coherent when composed under seed-3 authority. It is not — the frontier's own internal structure (N sequential statements) can straddle a concurrent writer regardless of what lock the *evaluator* holds. This is a correctness property of the evidence-selection algorithm itself, independent of Finding-lifecycle locking, and was never previously specified because I2 never needed CURRENT_STATE correctness (I2 only implemented HISTORICAL execution and the deterministic ledger, per CDD-041's own I1→I2→I3 decomposition).

## 3. Frozen invariant (binding)

> All mutable database facts used to construct one BusinessRule Evaluation's evidence frontier — subject-known/known-lineage, qualifying-evidence existence, and the latest-qualifying-evidence-per-role selection — must be obtained from **one PostgreSQL statement**, and therefore one `READ COMMITTED` statement snapshot. No BusinessRule Evaluation may combine evidence-state facts drawn from two different statement snapshots.

"One statement" means one command sent to PostgreSQL whose complete execution uses one statement snapshot. CTEs, window functions, correlated scalar subqueries, and LATERAL constructs are permitted *inside* that one statement. Two sequential `SELECT`s — even inside the same transaction, even under a held lock — are **not** one statement for the purpose of this invariant, because a lock that only the evaluator holds does not prevent a non-participating writer's `COMMIT` from becoming visible to the second `SELECT`.

## 4. Frozen architecture

Replace the current sequential algorithm with one statement of this shape (SQLAlchemy Core, exact identifiers/parameterization left to implementation, semantics frozen here):

```sql
WITH bound_roles(input_role, source_field_id) AS (
    VALUES (:role_1, :field_id_1), (:role_2, :field_id_2), ...   -- from rule.input_bindings, safely parameterized
),
ranked AS (
    SELECT
        br.input_role,
        fve.field_value_evidence_id,
        ROW_NUMBER() OVER (
            PARTITION BY br.input_role
            ORDER BY fve.observed_at DESC, fve.received_at DESC   -- existing frozen OQI1-derived ordering, unchanged
        ) AS rn
    FROM bound_roles br
    LEFT JOIN field_value_evidence fve
        ON fve.source_field_id = br.source_field_id
       AND fve.source_record_reference = :source_record_reference
       AND fve.observed_representation != ''
       AND fve.received_at <= :evaluation_horizon
)
SELECT
    (SELECT EXISTS (
        SELECT 1 FROM field_value_evidence fve2
        JOIN source_field sf ON sf.source_field_id = fve2.source_field_id
        WHERE sf.source_object_id = :source_object_id
          AND fve2.source_record_reference = :source_record_reference
          AND fve2.observed_representation != ''
          AND fve2.received_at <= :evaluation_horizon
    )) AS subject_known,
    br.input_role,
    ranked.field_value_evidence_id
FROM bound_roles br
LEFT JOIN ranked ON ranked.input_role = br.input_role AND (ranked.rn = 1 OR ranked.rn IS NULL);
```

The `subject_known` scalar subquery and the per-role `ranked` CTE are evaluated as one query tree by PostgreSQL and therefore share one statement snapshot — this is what closes both the known-lineage race and the per-field race simultaneously, in one fix, rather than two.

### 4.1 What this changes and what it does not

This amendment authorizes a change to **snapshot acquisition mechanics only**. It does **not** authorize any change to:

- evidence-selection *meaning* (latest-qualifying-evidence ordering, `received_at <= horizon` boundary, non-empty-representation filter) — these are the exact OQI1-derived predicates already frozen, reproduced verbatim in the query above;
- `EMPTY` semantics — a bound role with known lineage and zero qualifying evidence still yields the frozen `EMPTY` sentinel (`ranked.field_value_evidence_id IS NULL` after the `LEFT JOIN`, structurally identical to today's `entries.append(...evidence_id=None...)`);
- `NOT_EVALUABLE`/unknown-subject semantics — if `subject_known` is false, the caller still returns `NOT_EVALUABLE` exactly as today; no `EMPTY` entries are manufactured for an unknown subject;
- the role-keyed evidence digest formula or the Evaluation-ID formula — both are pure functions of the resulting `(input_role, evidence_id-or-EMPTY)` set, role-sorted before hashing; for unchanged database state, the new query returns the identical result set as the old algorithm, so both formulas are mechanically unchanged (verified against their actual definitions in OQI3-R3, not merely hoped for);
- typed interpretation, applicability, Kleene evaluation, or observation derivation (`determine_outcome` is a pure function of the frontier's output tuple, with no repository access inside it — confirmed by direct read of its signature);
- OQI2's N-source comparison/correspondence architecture, or `QualityRule`/OQI1's own selector — neither is touched by this amendment. OQI1's closed capability layer is not reopened; its query remains the *semantic anchor being preserved*, not a target for refactor.
- the OQI3-I2-R parent-gated historical-replay idempotency mechanism (`INSERT ... ON CONFLICT (evaluation_id) DO NOTHING RETURNING`) — that operates entirely downstream of frontier selection, on the `business_rule_evaluations` insert, and is unaffected by how the frontier itself was computed.

### 4.2 Immutable-metadata boundary (reaffirmed)

`BusinessRule` domain structure (family, frozen AST, input bindings, `expected_type` per binding) may be loaded outside the atomic frontier statement, because it is immutable per rule version and already fully materialized before evidence selection in the existing code path. Only *mutable evidence-state facts* (subject-known, per-role evidence existence/identity) must share the one statement. This boundary is unchanged from OQI3-R3's finding and is not weakened here.

### 4.3 ORM lazy-load firewall (reaffirmed)

No ORM access after the atomic frontier statement returns may supply a mutable evidence-state fact that affects the Evaluation's outcome. Reading `observed_representation` for an already-identified `field_value_evidence_id` afterward is permitted, because `FieldValueEvidence` is insert-only (confirmed: zero update/delete/merge call sites across production code, per CDD-022's raw-evidence immutability) — the row's content cannot change between the coherent-snapshot statement and the later read.

## 5. Equal-temporal-key ambiguity — recorded, not fixed

**OQI-P3-006 — Equal-temporal-key latest-evidence tie ambiguity, inherited from OQI1.** If two qualifying evidence rows for the same subject/field have identical `observed_at` and identical `received_at`, neither the existing OQI1 selector nor this amendment's window-function replacement define a deterministic winner (`ROW_NUMBER()`'s output order is unspecified beyond the given `ORDER BY` columns when they tie). This is a pre-existing gap, confirmed identical in OQI1's own `select_latest_target_field_value` (no third tiebreaker there either) — not introduced by this amendment, not fixed by it, and not a license to invent a new arbitrary tiebreaker unilaterally. The future OQI3-I2-R3 implementation must acknowledge this inherited undefined-winner behavior in its equal-timestamp regression rather than assert a specific deterministic outcome it cannot actually guarantee. OQI1 is not reopened to address this.

## 6. Responsibility split (frozen, reaffirmed)

```
Atomic frontier (this amendment):
    evaluator-vs-evidence-writer statement-snapshot coherence

Seed-3 advisory authority (still required, unchanged, I3's to implement):
    evaluator-vs-evaluator serialization
    single stable Finding authority
    Finding counter/state_revision/occurrence/reopen safety
    first-violation / resolution / reopen race prevention
```

Both mechanisms are required for CURRENT_STATE correctness; neither replaces the other. This amendment does not remove, weaken, or substitute for seed-3.

## 7. Frozen future I3 ordering (reaffirmed, unchanged from CDD-041 §21's own step order)

```
load/validate immutable rule metadata
→ establish subject
→ compute stable Finding identity
→ acquire seed-3 advisory transaction lock
→ perform required post-lock validation
→ establish trusted CURRENT_STATE horizon           (AFTER seed-3 acquisition)
→ execute ONE atomic frontier statement              (this amendment's subject)
→ typed interpretation
→ applicability
→ Kleene/AST evaluation
→ derive deterministic observations
→ persist immutable Evaluation
→ mutate BusinessRuleFinding
→ commit
```

Horizon establishment after seed-3 acquisition (not before) avoids an arbitrarily long lock-wait producing a stale "now" relative to when the frontier is actually read — this is a direct reading of CDD-041 §21's existing step order (horizon determination after lock acquisition), not a new decision.

## 8. HISTORICAL/CURRENT_STATE shared selector

One atomic selector implementation is authorized for both `HISTORICAL` and `CURRENT_STATE` modes — the underlying evidence-selection semantics (latest qualifying evidence under a horizon) are identical between modes; only the horizon value and whether Finding authority is taken differ. This avoids maintaining two subtly-different evidence-selection algorithms. This does not touch or regress OQI3-I2-R's historical-replay idempotency mechanism (§4.1). If a future implementation phase discovers this genuinely cannot be shared without violating an existing frozen semantic, it must STOP and return for architecture review rather than force a shared implementation — but no such obstruction is known at authorization time.

## 9. Implementation authorization (exact, narrow)

Authorized changes are limited to exactly:

| # | Action | Path | Authorized change |
|---|---|---|---|
| 1 | MODIFY | `backend/app/infrastructure/persistence/oqi_business_rule_evaluation_repository.py` | replace `select_known_lineage`/`select_latest_field_value` with one atomic-frontier method implementing §4's query |
| 2 | MODIFY | `backend/app/application/oqi_business_rule_evaluation_service.py` | `select_input_frontier` calls the new atomic method instead of the sequential loop; no change to its return type/contract |
| 3 | MODIFY | `backend/app/tests/test_oqi_business_rule_postgres.py` | add the mandatory regression set (§10) |

All three paths are already present in the original CDD-041 Artifact Authorization (rows 9, 10, 15) — confirmed by direct read in this phase. **No new file. No new authorization surface required beyond this amendment's authorization of the algorithm content itself**, which no prior CDD-041 document (original, GA, or G2) described.

**Explicitly NOT authorized as part of this repair (OQI3-I2-R3):** any `BusinessRuleFinding` lifecycle code, the seed-3 advisory lock itself, Finding counters (`occurrence_count`/`reopen_count`/`state_revision`), `resolution_basis`, reopen logic, or any Finding mutation of any kind. That remains OQI3-I3-R's exclusive scope, to be attempted only after this repair closes the P1.

## 10. Mandatory regression list for OQI3-I2-R3 (exact, binding)

1. Unchanged-state equivalence: old sequential algorithm and new atomic algorithm return identical `(role, evidence_id)` sets for the same DB state.
2. Digest equivalence: identical `input_evidence_digest` output between old/new for unchanged state.
3. Evaluation-ID equivalence: identical `derive_business_rule_evaluation_id` output for unchanged state.
4. All-bound-roles-EMPTY: known subject, zero evidence for any bound field.
5. Unknown subject: zero evidence anywhere for the SourceObject/record → `NOT_EVALUABLE`, no partial `EMPTY` entries manufactured.
6. Mixed `EMPTY`/value roles in one Evaluation.
7. Equal-timestamp tie: two qualifying rows, identical `observed_at`/`received_at` — document actual behavior as inherited-undefined (OQI-P3-006), do not assert a specific deterministic winner.
8. Three-role compound rule (the original defect-exposing case).
9. N=10 bound roles.
10. N=100 bound roles — verify no fixed-arity assumption; characterize performance without prematurely optimizing.
11. Writer commits before statement begins — new evidence visible.
12. Writer commits during statement execution (forced-delay pattern) — new evidence NOT visible. **Must be proven on real PostgreSQL.**
13. Writer commits after statement completes — not visible to this Evaluation, visible to the next.
14. Two concurrent writers on two different bound fields during one statement — all-or-nothing visibility, never split.
15. Known-lineage creation race: first-ever evidence for a previously-unknown subject arriving mid-statement — must resolve cleanly to one snapshot's answer, never a hybrid.
16. `EMPTY`→`VALUE` race for one bound field.
17. `VALUE` v1→v2 race for one bound field.
18. Tenant isolation: attempt cross-tenant evidence/field binding, must fail closed exactly as today.
19. `SourceObject` boundary: exact `tenant_id`+`source_object_id`+`source_record_reference` scoping, not mere `source_record_reference` string match.
20. Horizon boundary: evidence exactly at/after the horizon boundary, verify inclusion/exclusion unchanged from current `<=` semantics.
21. No ORM mutable-evidence lazy load after the atomic statement returns.
22. `HISTORICAL` selector equivalence: same atomic selector used for `HISTORICAL` mode produces identical results to the current `HISTORICAL` path.
23. Historical-replay regression: re-run all OQI3-I2-R parent-gated idempotency tests, confirm zero regression from the frontier-selector swap.
24. Compound Kleene regression: re-run the FALSE∧FALSE∧UNKNOWN and TRUE∧UNKNOWN scenarios end-to-end through the new selector, confirm unchanged outcome/observation behavior.
25. `NOT_EVALUABLE` persistence firewall: re-run existing zero-row-written regressions through the new selector path.

Item 12 must be proven on real PostgreSQL, not SQLite or mocked isolation behavior.

## 11. P1 closure condition (binding, not satisfied by this document)

This amendment does **not** close the P1. Publication of this governance amendment is architecture authorization only. The P1 (`OQI3 CURRENT_STATE multi-field evaluation cannot presently prove one coherent evidence frontier against concurrent FieldValueEvidence writers`) closes only when OQI3-I2-R3 proves, with committed evidence:

```
complete frontier = one statement
known lineage = same statement
real PostgreSQL writer-during-statement test = pass
EMPTY/UNKNOWN semantics = preserved
digest = unchanged
Evaluation ID = unchanged
OQI1 = unchanged
OQI2 = unchanged
historical replay = not regressed
unauthorized paths = 0
exact-head CI = green
```

## 12. P3 register (carried forward, one addition)

```
OQI-P3-001  64-bit advisory-hash collision / harmless over-serialization
OQI-P3-002  residual DB tenant defense-in-depth
OQI-P3-003  explicit correspondence scalability
OQI-P3-004  deferred composite evidence lookup index
OQI-P3-005  inherited unlocked historical replay race in OQI1/OQI2
OQI-P3-006  equal-temporal-key latest-evidence tie ambiguity, inherited from OQI1 (§5, new)
```

None of items 001-005 are resolved, weakened, or reclassified by this amendment.

## 13. Scope boundary (binding)

This amendment authorizes exactly: the one-statement atomic frontier query, its two call-site changes, and its regression suite. It does not authorize: any Finding lifecycle code, any change to `BusinessRule`/`InputBinding`/AST/Kleene semantics already frozen by CDD-041/GA/G2, any change to OQI1 or OQI2, any change to `FieldValueEvidence`/`SourceField` schema, any new migration, or any change to the historical-replay idempotency mechanism's own logic (only its equivalence under the new selector need be re-proven).
