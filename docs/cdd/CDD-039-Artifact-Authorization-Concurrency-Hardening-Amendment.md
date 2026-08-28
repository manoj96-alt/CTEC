# CDD-039 — Artifact Authorization Concurrency Hardening Amendment (OQI1-GR)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-028-Ontology-Modeling-Read-Authority-Artifact-Authorization-Amendment.md`,
`CDD-036-Migration-Head-Regression-Assertion-Defect-Authorization.md` (separate-companion-document
amendment pattern; the original Artifact Authorization is never silently rewritten in place)
Classification: ARTIFACT AUTHORIZATION AMENDMENT (Primary: CONCURRENCY-MECHANISM HARDENING;
Severity: P3, non-blocking, raised and resolved proactively before any implementation began)

## 1. Purpose

Supersedes, in its entirety, **Section 12 ("Concurrency implementation mechanism")** of
`CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-Artifact-Authorization.md` (v1.0).
No other section of that document, and no section of `CDD-039-Ontology-Quality-Intelligence-
Deterministic-Foundation.md` (FROZEN) or of OQI Foundation Contract v1.2, is altered, reopened, or
reinterpreted by this amendment. The original Artifact Authorization file remains byte-identical to
its OQI1-G publication state; wherever it says "this document's Sec12" or "the Sec12 advisory-lock
mechanism," the mechanism frozen below now governs.

## 2. Context / problem statement

OQI1-G's Artifact Authorization froze a PostgreSQL evaluation-authority lock keyed by
application-side XOR-folding the deterministic 128-bit `quality_finding_id` UUID into a signed
64-bit integer, then calling `pg_advisory_xact_lock(bigint)`. The Product Owner flagged this as a
knowingly avoidable many-to-one authority-key compression and required investigation of whether a
PostgreSQL/repository-compatible alternative provides stronger isolation before implementation
begins — without reopening the already-approved concurrency *semantic* (CDD-039 Sec24: authority
acquired before evidence selection, obtainable before any Finding row exists, held through commit).

## 3. Frozen semantic (restated, unchanged, not reopened)

```
Acquire exclusive CURRENT_STATE evaluation authority
        v
Select evidence
        v
Evaluate
        v
Persist QualityEvaluation
        v
Mutate QualityFinding
        v
Assign/increment state_revision
        v
Commit
        v
Release authority
```

One authority holder at a time per (tenant, quality_condition_id, `EvaluationSubject`); authority
obtainable before any `QualityFinding` row exists; HISTORICAL evaluations never acquire it. This
amendment changes only *how* the lock key is computed, never this behavior.

## 4. Authority-domain definition (unchanged)

The lock must represent exactly one (tenant, quality_condition_id, `EvaluationSubject`) triple — the
same triple `quality_finding_id` (CDD-039 Sec28) already deterministically identifies. Same lineage
must map to the same authority domain; different lineages should map to different domains as
strongly as a 64-bit space allows. The lock must not be broadened to (tenant, quality_condition_id,
SourceObject, SourceField) alone, which would serialize unrelated records unnecessarily.

## 5. PostgreSQL advisory-lock semantics (verified)

`pg_advisory_xact_lock(bigint)` and `pg_advisory_xact_lock(int, int)` are **separate lock
namespaces** — PostgreSQL tags locks taken via the two forms distinctly internally, so a lock
acquired with one form can never collide with a lock acquired via the other, regardless of numeric
value. Both forms address a 64-bit-sized key space in total (one `bigint`, or two `int4` halves);
neither form encodes more raw information than the other — two 32-bit integers do not "add up" to
more than one 64-bit integer. Both are transaction-scoped identically under the `_xact_` variants:
automatic release on `COMMIT`, `ROLLBACK`, or connection loss, no explicit unlock required, and both
work before any row exists because the key is an arbitrary application-chosen integer with no
relationship to table data. PostgreSQL provides zero guarantee against collision between two
semantically-different tags that happen to reduce to the same integer(s) in either form — that
responsibility belongs entirely to the caller, which is the exact question this amendment resolves.

## 6. Existing repository precedent (discovered during this investigation — decisive finding)

CTEC already contains **two** production, CI-proven advisory-lock precedents, neither previously
consulted when OQI1-G drafted its original mechanism:

```
backend/app/runtime/persistence/repository.py:876  (RuntimeExecutionRepository._lock_replay_identity)
    identity = f"{original_execution_id}:{authorization.authorization_reference}:{authorization.correlation_id}"
    SELECT pg_advisory_xact_lock(hashtextextended(:identity, 0))

backend/app/infrastructure/persistence/semantic_mapping_repository.py:221  (SemanticMappingRepositoryImpl.create)
    SELECT pg_advisory_xact_lock(hashtext(:tenant_id), hashtext(:element_id))
```

Both let **PostgreSQL itself** compute the hash from a text value, rather than the application
hand-rolling bit manipulation in Python. This is the correct precedent to reuse (Sec10's own
instruction to check for a reusable primitive before inventing one) — with one caveat, analyzed next.

## 7. Why the two-int form (`hashtext(a), hashtext(b)`) is not the right precedent to copy here

The two-int precedent hashes two **semantically independent** strings separately (tenant, element).
For OQI1's authority domain, the natural split would be something like
`hashtext(tenant_id + quality_condition_id), hashtext(source_object_id + source_record_reference +
source_field_id)`. This does **not** improve — and can **degrade** — collision resistance relative
to a single 64-bit hash: OQI1's realistic common case is many `EvaluationSubject`s sharing the same
`tenant_id` and `quality_condition_id` (one governed rule evaluated across many records for one
tenant). When that shared half is held fixed, a collision between two *different* subjects reduces
to a collision on the *other* 32-bit half alone — a 32-bit birthday bound (~2^16 concurrently active
distinct subjects for a 50% collision chance), not a 64-bit one. The single-bigint form, hashing the
**entire** concatenated identity as one string, always draws on the full 64-bit space for any pair of
differing identities, regardless of which components happen to match. The single-bigint
`_lock_replay_identity` pattern is therefore the correct precedent, not the two-int
`semantic_mapping_repository.py` pattern, despite the latter superficially looking like it "uses two
keys instead of one."

## 8. XOR-fold analysis (the mechanism being replaced)

The original mechanism (`quality_finding_id.bytes[0:8] XOR quality_finding_id.bytes[8:16]`) is
deterministic and uses the full 128 bits of input, but is bespoke, unreviewed application code with
no prior repository precedent, requiring correct big-endian/signed-integer handling to be
independently re-verified by every future reader. It does not add real entropy-mixing beyond what
`quality_finding_id`'s own `uuid5` (SHA-1-based) construction already provides, and — unlike
`hashtextextended` — is not a function PostgreSQL itself computes, so the database and application
must independently agree on byte order and sign interpretation, a source of exactly the kind of
subtle bug this review exists to catch before it ships.

## 9. Collision consequence analysis (unchanged conclusion, now applies to the new mechanism too)

A lock-key collision between two different `quality_finding_id`s (under either mechanism) means:
Worker B's `pg_advisory_xact_lock` call blocks until Worker A's transaction (a wholly unrelated
Finding) commits or rolls back. The lock key is consumed by exactly one statement and never again
referenced; every subsequent read/write in the transaction is keyed by the real `tenant_id`,
`quality_condition_id`, `canonical_subject_identity`, and `quality_finding_id` values, never by the
lock key. Therefore a collision:
- **cannot** cause one Finding to be read, written, or mutated in place of another;
- **cannot** cross a tenant boundary in data visibility or mutation (every query still filters by
  the real `tenant_id`);
- **cannot** corrupt `state_revision` (computed from the real Finding row, independent of the lock
  key);
- **can only** cause additional, unnecessary serialization latency between two unrelated evaluations.

Deliberate/adversarial exploitation is not a live concern for OQI1: there is no API of any kind
(CDD-039 Sec8), so no external caller can choose or influence `source_record_reference`,
`quality_condition_id`, or evaluation timing to engineer a targeted collision. This would need
reassessment only if and when a future Gate exposes OQI evaluation to external, high-frequency,
caller-controlled triggering — out of OQI1's frozen scope, not a defect in it.

## 10. Comparison matrix

| Option | Collision-free authority | First-Finding safe | Lock before evidence | Tx-scoped | Extra table | Extra files | Correctness risk | Complexity | Recommendation |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| A. Original XOR-fold bigint | No (64-bit space) | Yes | Yes | Yes | No | 0 | None (collision harmless) | Bespoke bit-manipulation code | Superseded |
| B. Two-int `hashtext(a),hashtext(b)` | No (64-bit space; degrades to 32-bit when a shared component is fixed) | Yes | Yes | Yes | No | 0 | None, but weaker in the common case | Low | Rejected (Sec7) |
| C. Python SHA-256-derived 64-bit key | No (64-bit space) | Yes | Yes | Yes | No | 0 | None | Needs app-side hash import, no precedent | Rejected (no benefit over G) |
| D. Dedicated persisted lock-row table | Yes (full 128-bit PK) | Yes | Yes | Yes | **Yes** | +1–2 (model+migration) | None | New table, migration, cleanup/growth concerns, widens 20-file budget | Rejected (Sec14: correctness-perfect but architecturally heavier than the risk warrants) |
| E. Upsert QualityEvaluation/QualityFinding row as lock target | N/A | **No** — QualityEvaluation identity needs the evidence digest/horizon not yet known pre-selection; QualityFinding must not be created on first SATISFIED | — | — | — | — | Violates frozen semantics | Rejected (Sec15) |
| F. SERIALIZABLE isolation | N/A | Uncertain — needs app-wide retry-on-serialization-failure machinery with no repository precedent | Not before-row-exists native | — | No | Broad blast radius | Unproven for this shape | High (new failure-handling paradigm) | Rejected (Sec16: do not broaden isolation globally) |
| **G. Single-bigint `pg_advisory_xact_lock(hashtextextended(identity, seed))`, reusing `_lock_replay_identity`'s exact shape** | No (64-bit space, but full space preserved for every comparison, Sec7) | **Yes** | **Yes** | **Yes** | No | 0 | None (collision harmless, Sec9) | Lowest — one proven repository pattern, zero new bit-manipulation code | **Selected** |

## 11. Selected mechanism (binding, supersedes original Sec12 in full)

```
OqiQualityEvaluationRepository.acquire_evaluation_authority(...) issues:

    SELECT pg_advisory_xact_lock(hashtextextended(:identity, :seed))

:identity = the exact same delimited string already required to compute quality_finding_id
            (CDD-039 Sec28's uuid5 input: tenant_id + quality_condition_id + subject_type +
            canonical_subject_identity, CDD-039 Sec20) -- produced by one shared string-
            construction function used for BOTH the uuid5 call and this lock call, so the lock's
            authority domain can never silently drift from the Finding identity domain it must
            match.

:seed     = the fixed integer constant 1 (OQI_ADVISORY_LOCK_SEED = 1), chosen only so OQI1's hash
            outputs are statistically independent of backend/app/runtime/persistence/repository.py's
            pre-existing use of the identical pg_advisory_xact_lock(bigint) form with seed 0 -- two
            unrelated subsystems must never coincidentally serialize against each other merely
            because they picked the same seed.
```

No Python-side struct-packing, byte-slicing, or XOR-folding is authorized. `hashtextextended`
returns a signed 64-bit integer computed entirely by PostgreSQL.

## 12. Rationale

1. **Preserves CDD-039 exactly** — CDD-039 Sec24/Sec42 explicitly deferred the SQL mechanism to the
   Artifact Authorization; this amendment touches only that deferred layer, never CDD-039 itself.
2. **First-Finding safe** — the key is derived from the identity string, never from an existing row's
   primary key; identical to the property the original mechanism already had.
3. **Evidence selection under authority** — unchanged; this amendment does not touch the acquire →
   select-evidence → evaluate → persist → mutate → commit → release ordering.
4. **Collision characteristics** — unchanged in raw bit-count (64 bits) but the *comparison* is
   always over the full 64 bits for every pair of differing identities (Sec7), unlike the two-int
   alternative, and the computation itself is now a single already-proven repository function call
   rather than new bit-manipulation code.
5. **Correctness consequence of any collision** — strictly limited to harmless additional
   serialization latency (Sec9); never data, tenant, or state-integrity corruption.
6. **Rejected alternatives** — B degrades in the common shared-tenant/shared-condition case (Sec7);
   C adds complexity with no benefit over reusing an existing DB-native function; D adds a table,
   migration, and lifecycle-management burden disproportionate to a risk that is already harmless;
   E violates already-frozen identity/lifecycle ordering; F requires an unproven, broad,
   precedent-free isolation-and-retry paradigm.
7. **Implementation file budget** — **unchanged**. This amendment corrects the *content* of
   `oqi_quality_evaluation_repository.py`'s planned `acquire_evaluation_authority` implementation
   only; it does not add, remove, or rename any authorized path.

## 13. Tenant isolation, deadlock, connection-pool, rollback proofs

- **Tenant isolation**: `tenant_id` is a direct component of `:identity`; a collision (Sec9) can at
  most cause waiting, never cross-tenant data visibility or mutation, since every subsequent query
  still filters by the real `tenant_id` column value.
- **Deadlock**: OQI1 acquires exactly one authority lock per transaction (one Finding lineage per
  `evaluate_current_state()` call); no code path acquires a second advisory lock within the same
  transaction, so no lock-ordering deadlock can arise from this mechanism.
- **Connection-pool safety**: `pg_advisory_xact_lock` (both forms) is strictly transaction-scoped —
  it is released automatically at `COMMIT`/`ROLLBACK`/connection loss and never persists across a
  pooled connection's reuse by a different logical caller. OQI1 uses only the `_xact_` variant,
  never the session-scoped `pg_advisory_lock`.
- **Rollback/failure**: if the transaction fails after acquiring authority but before commit, the
  lock releases automatically on rollback; no ledger row, no Finding mutation, and no
  `state_revision` change is left partially applied, and a retry acquires the same lock cleanly.

## 14. state_revision / domain-firewall confirmation (unchanged, restated)

The lock key participates in **no** identity: not `quality_finding_id`, not `evaluation_id`, not
`state_revision`. It is pure synchronization infrastructure, never surfaced in any domain model,
API (none exists), dashboard, ontology graph, or trust explanation — consistent with CDD-039's own
raw-value/domain-leakage discipline (Sec36).

## 15. Implementation file budget (unchanged)

```
CREATE = 15
MODIFY = 5
DELETE = 0
TOTAL  = 20
```

Identical to OQI1-G's original accounting. `oqi_quality_evaluation_repository.py` remains the same
authorized path; only the internal mechanism its `acquire_evaluation_authority` method must
implement has changed.

## 16. P0/P1/P2/P3

```
P0 = 0
P1 = 0
P2 = 0
P3 = 1  -- retained, not eliminated: the underlying lock-key space is still 64 bits, and a
           theoretical collision remains possible. This is honestly kept as a documented, accepted,
           non-blocking implementation characteristic (Sec9), not reclassified to P3=0 merely to
           report a clean number -- the mechanism is meaningfully hardened (proven repository
           precedent replaces bespoke bit-manipulation code, and the full 64-bit space is preserved
           for every comparison instead of degrading in the common shared-component case), but the
           raw collision-space size is unchanged.
```

## 17. Authorization

This amendment is approved and frozen as a standalone governance artifact, following the
established repository precedent (Sec-Precedent header) of never silently rewriting an
already-approved Artifact Authorization in place. `CDD-039-Ontology-Quality-Intelligence-
Deterministic-Foundation.md` and `CDD-039-Ontology-Quality-Intelligence-Deterministic-Foundation-
Artifact-Authorization.md` (v1.0) both remain byte-identical to their OQI1-G publication state. OQI1
implementation remains NOT AUTHORIZED; a further, separate Product Owner implementation
authorization is required before any of the 20 authorized files may be created or modified, this
time against the Section 11 mechanism above rather than the original Section 12 text it supersedes.
