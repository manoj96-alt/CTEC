# CDD-047 — OQI-H1 Governed Quality Coverage + Reliance Generalization

Version: 1.0 FROZEN
Status: FROZEN (implementation authorized only via the paired Artifact Authorization companion)
Implementation state: NOT STARTED
Governing authorities: CDD-046 (FROZEN, Nine-Dimension Architecture — this document implements
exactly Boundary 1), `CDD-046-QualityRule-Ownership-Erratum.md` (FROZEN, read as precedent for
`QualityRule`'s corrected shared-platform classification), CDD-039/040/041/042/043/044/045 (FROZEN,
OQI1-7 — read-only consumed, never modified)

Mandatory template: CDD Template v2.2 (this repository's established house style)

**Publication note**: this document freezes the governance decisions produced across OQI-H0
(architecture), OQI-H1-DR (repository-grounded discovery), and explicit Product Owner review of that
discovery (PO-01 through PO-05). Implementation is authorized only by the paired companion,
`CDD-047-OQI-H1-Governed-Quality-Coverage-and-Reliance-Generalization-Artifact-Authorization.md`.

## 1. Purpose

Allow a tenant to declare, per governed ontology subject, which quality dimensions must have
qualifying evaluation coverage before that subject's Reliance may read as `RELIANCE_SUPPORTED` —
closing the epistemic gap CDD-046 §5.6/§12 identified in CDD-044's existing coverage predicate — while
preserving CDD-044's exact current behavior, byte-for-byte, for every tenant that does not opt in.

## 2. Capability claim (exact, binding)

Noetva can: allow a tenant to create a versioned, tenant-owned `QualityCoveragePolicy` naming a set of
required governed quality dimensions for a specific ontology subject; deterministically compute, per
subject, whether every required dimension currently has qualifying persisted evaluation coverage;
generalize the existing Reliance decision function's coverage input to consume this computed result
without modifying the decision function itself; and do all of this while leaving every subject with no
`ACTIVE` policy semantically indistinguishable, in every observable respect, from the pre-H1 system.

No broader claim is authorized. In particular: no claim that any of the six not-yet-implemented
quality dimensions (`ACCURACY`, `UNIQUENESS`, `TIMELINESS`, `INTEGRITY`, `CONFORMITY`,
`REASONABLENESS`) are implemented by this document or its implementation; no claim that
`RELATIONSHIP`-anchored coverage policies achieve real coverage in this phase; no numeric coverage
score, percentage, or weighting of any kind; no public API or frontend surface.

## 3. Product Owner decisions frozen (PO-01 through PO-05)

**PO-01 — Configuration authority.** `QualityCoveragePolicy` configuration requires its own governed
authority, `oqi-coverage:configure`, distinct from `oqi-remediation:authorize` and
`oqi-remediation:report-execution`. `CONFIGURATION AUTHORITY ≠ REMEDIATION AUTHORITY` is preserved
structurally: no code path may accept a remediation scope as satisfying a coverage-configuration
check, or vice versa. §22 below freezes the exact scope requirement; §16 of this document's paired
Artifact Authorization determines the minimum file touched to declare it.

**PO-02 — Unsupported dimensions may be required.** An `ACTIVE` `QualityCoveragePolicy` may name any
`CoverageDimension` member, including the six with no live evaluator. This is intentional governance
expression, not a defect. §13 operationalizes this exactly.

**PO-03 — New crown invariant.** `PARTIAL REQUIRED COVERAGE ≠ SUPPORTED` is formally adopted. §20
freezes its statement and required proof.

**PO-04 — CDD-046 QualityRule correction.** Recorded via the separate, narrow
`CDD-046-QualityRule-Ownership-Erratum.md`, referenced here as precedent, not reproduced. `QualityRule`
is shared platform structure; `QualityCoveragePolicy` remains tenant-owned; no consequence to
`QualityRule`'s schema follows from this.

**PO-05 — Dead `IMPACT_UNKNOWN` branch.** Recorded as a deferred hardening item (§26). Not touched by
H1 in any way.

## 4. `CoverageDimension` — frozen vocabulary

```
CoverageDimension (NEW, closed StrEnum, exactly nine members):
    COMPLETENESS
    VALIDITY
    CONSISTENCY
    ACCURACY
    UNIQUENESS
    TIMELINESS
    INTEGRITY
    CONFORMITY
    REASONABLENESS
```

`CoverageDimension` expresses **governance requirement** — what a tenant may declare it needs.
`QualityDimension` expresses **current evaluator/rule capability** — what the system can actually
evaluate today. The two are structurally independent enums; no code path may treat membership in
`CoverageDimension` as proof that a corresponding evaluator exists.

```
CoverageDimension member exists   ≠   evaluator implemented
```

## 5. `QualityDimension` — frozen, unchanged

`QualityDimension` remains exactly `COMPLETENESS`, `VALIDITY`, `CONSISTENCY` (CDD-039/040, unmodified).
H1 does not add a fourth member, does not touch `_ALLOWED_COMBINATIONS`, does not touch `QualityRule`
construction, and does not touch any of the ≥7 files referencing `QualityDimension` today. Any future
convergence of `QualityDimension` and `CoverageDimension` (per CDD-046 §28's `QualityFindingOrigin`
direction) is explicitly out of scope for H1.

## 6. Policy anchor — frozen

`QualityCoveragePolicy` is anchored exactly to the existing Reliance subject identity:

```
(tenant_id: str, ontology_element_type: OntologyElementType, ontology_element_id: UUID)
```

reusing `OntologyElementType` (`ENTITY` | `RELATIONSHIP`) verbatim — no new anchor-type vocabulary.
**Not authorized in H1**: Information Element anchor, Blueprint anchor, Business Process anchor,
Business Dependency anchor, wildcard anchor, inherited/hierarchical policy, default/global tenant
policy. All deferred, consistent with CDD-046 §43 DD-06.

## 7. Tenant model — frozen

```
SHARED ONTOLOGY ELEMENT   ≠   TENANT COVERAGE POLICY
```

The ontology subject an anchor names remains shared platform structure (unchanged by H1, unchanged by
the §PO-04 erratum). `QualityCoveragePolicy` itself is tenant-owned — every row carries `tenant_id`,
every read/write is tenant-scoped, and cross-tenant reference is rejected at the service layer,
mirroring `OqiRemediationService._decide()`'s existing explicit tenant-mismatch discipline. No
PostgreSQL row-level security exists anywhere in this codebase and none is introduced here —
application-layer enforcement remains authoritative, and frontend filtering is never treated as
authorization.

## 8. `QualityCoveragePolicy` — frozen domain shape

```
QualityCoveragePolicy:
    policy_id                UUID, primary identity
    tenant_id                str
    ontology_element_type    ENTITY | RELATIONSHIP
    ontology_element_id      UUID
    status                   ACTIVE | RETIRED   (closed, exactly two — no DRAFT in H1)
    version_number           int
    previous_version_id      UUID | None   (self-referencing lineage)
    required_dimensions      non-empty set[CoverageDimension]
    created_by                str
    created_on                datetime
```

Binding constraints: no empty `required_dimensions` set may ever be persisted as `ACTIVE`; no
duplicate dimension within one policy's required set; no dimension outside the closed
`CoverageDimension` vocabulary; historical policy versions are immutable once superseded — a new
requirement set is always a new version, never an in-place mutation of a prior version, mirroring
`BusinessDependency`'s own criticality-change discipline (CDD-044 §22-§23).

## 9. Required-dimensions persistence — frozen, normalized

Two tables, not one JSONB/ARRAY column:

```
oqi_quality_coverage_policies             (the policy row itself, per §8's fields minus
                                            required_dimensions)
oqi_quality_coverage_policy_dimensions    (policy_id, dimension) — composite key, one row per
                                            required dimension
```

JSONB and PostgreSQL `ARRAY` are explicitly rejected. Reasoning, frozen: (1) a normalized child table
supports a real database-level `CHECK`/enum-typed constraint on `dimension`, which neither JSONB nor
`ARRAY` can express as strongly; (2) "which required dimensions lack coverage" becomes a plain
anti-join, not array-containment logic; (3) this matches every other closed-vocabulary,
per-item-constrainable pattern already established in this codebase (e.g. the per-participant
structure inside `_validate_consistency_parameters`, even though that one remains JSON-shaped for a
different, already-justified reason — participants there are not a closed enum, dimensions here are);
(4) a future Command Center coverage matrix (deferred, CDD-046 §43 DD-05) benefits from a normalizable
join target now rather than a migration later.

## 10. Policy versioning and activation — frozen

Primary structural precedent: `ImpactPropagationPolicyORM` (CDD-042 §8), not `BusinessDependency`
(CDD-044 §16) — the two existing "versioned governed policy" precedents in this codebase disagree
(`ImpactPropagationPolicy` uses a single-column PK with a `previous_version_id` self-FK chain and a
database-enforced active-uniqueness partial index; `BusinessDependency` uses a composite
`(id, version)` primary key with no database-enforced uniqueness, relying on application discipline
alone). **H1 follows `ImpactPropagationPolicy`'s stronger pattern** — a policy whose entire purpose is
preventing a false-positive `RELIANCE_SUPPORTED` must not rely on application discipline alone for its
own single most important invariant.

```
policy_id             single-column primary key
version_number         explicit, incrementing per logical policy
previous_version_id    self-referencing FK, forming an immutable version chain
status                 ACTIVE | RETIRED
```

## 11. Active-policy uniqueness — frozen, database-enforced

```
UNIQUE ACTIVE (tenant_id, ontology_element_type, ontology_element_id)
```

implemented as a PostgreSQL partial unique index — the exact mechanical shape of
`uq_impact_propagation_policies_one_active` — `WHERE status = 'ACTIVE'`, never a plain
`UniqueConstraint` (which would incorrectly forbid `RETIRED` historical versions from coexisting).
Concurrent activation attempts for the same subject **must** fail closed at the database level — one
transaction succeeds, one raises an integrity error the application surfaces as a conflict, never a
race condition producing two `ACTIVE` rows.

## 12. Unsupported-dimension activation behavior — frozen (PO-02 operationalized)

Worked example, frozen as the canonical test case:

```
ACTIVE policy requires:  {COMPLETENESS, VALIDITY, ACCURACY, TIMELINESS}
Live evaluator coverage exists for:  COMPLETENESS, VALIDITY only.

COMPLETENESS  → covered (subject to §15's mapping)
VALIDITY      → covered (subject to §15's mapping)
ACCURACY      → uncovered (no evaluator exists — not a computation, a structural fact)
TIMELINESS    → uncovered (no evaluator exists)

coverage_satisfied = False
```

**Explicitly prohibited**, all of the following, no exceptions: rejecting policy activation solely
because a named dimension lacks a live evaluator; inventing a synthetic evaluation row; creating a
Finding merely because an evaluator is absent; marking an unsupported dimension `covered`; silently
dropping an unsupported dimension from `required_dimensions`; silently downgrading or auto-retiring the
policy. The maximum truthful interpretation of an uncovered unsupported dimension is exactly: *"this
dimension is required but does not currently have qualifying evaluation coverage."*

## 13. Coverage derivation architecture — frozen

Coverage is **derived on read**, never persisted as its own projection, and computed by a narrow
extension of the existing repository method — no new service class.

```python
def compute_generalized_coverage(*, tenant_id, ontology_element_type, ontology_element_id,
                                   source_object_ids, legacy_any_evaluation_ever_run: bool) -> bool:
    active_policy = get_active_coverage_policy(tenant_id, ontology_element_type, ontology_element_id)
    if active_policy is None:
        return legacy_any_evaluation_ever_run     # identical call, unchanged value
    for dimension in active_policy.required_dimensions:
        if not has_qualifying_coverage_for_dimension(
            tenant_id=tenant_id,
            ontology_element_type=ontology_element_type,
            source_object_ids=source_object_ids,
            dimension=dimension,
        ):
            return False
    return True
```

Bounded cost: at most nine required-dimension checks per subject. Any exception raised anywhere in
this computation **must propagate** — no `except Exception: return True` anywhere in the call chain,
no default-to-covered fallback under any failure condition.

## 14. Qualifying coverage — frozen mapping for currently implemented dimensions

```
COMPLETENESS, VALIDITY  (OQI1):
    Resolve the evaluation's governing QualityRule and filter on QualityRuleORM.dimension.
    No dimension column exists on quality_evaluations itself (verified directly against its
    schema) — the qualifying query is a JOIN quality_evaluations → quality_rules ON rule_id
    WHERE quality_rules.dimension = ? AND quality_evaluations.tenant_id = ?
    AND quality_evaluations.source_object_id IN (source_object_ids).
    Denormalizing `dimension` onto quality_evaluations is NOT authorized in H1 unless
    implementation discovery proves the JOIN is genuinely infeasible — it is not expected to be.

CONSISTENCY  (OQI2):
    OQI2 is, in its entirety, the CONSISTENCY evaluator family today — any qualifying persisted
    QualityComparisonEvaluation row (the existing has_any_evaluation_for_source_objects query,
    unmodified) establishes CONSISTENCY coverage. No additional filter is needed or authorized.

ACCURACY, UNIQUENESS, TIMELINESS, INTEGRITY, CONFORMITY, REASONABLENESS:
    has_qualifying_coverage_for_dimension returns False unconditionally. No table is queried,
    because none exists. This is a structural fact, not a computed negative.
```

## 15. Relationship coverage boundary — frozen (resolves the governing prompt's own STOP condition)

**Discovery finding, confirmed at H1-DR and re-verified here:** legacy coverage computation
(`_compute_coverage`) is gated on `ontology_element_type is OntologyElementType.ENTITY` — for
`RELATIONSHIP` subjects it is hard-coded to contribute `False`. No existing mechanism in this
repository resolves "which source objects/evaluations support a given `RELATIONSHIP` instance" — the
entire evidence-resolution chain (`_resolve_source_object_ids_for_entity` → Entity Resolution reverse
lookup) is `EnterpriseEntity`-specific by construction. Establishing genuine per-dimension coverage for
a `RELATIONSHIP`-anchored policy would require inventing a new evidence-resolution mechanism —
exactly the class of architectural invention the governing prompt requires this document to refuse.

**Frozen resolution, narrow and safe, not a phase-wide STOP:**

```
ANCHOR SCHEMA:  ontology_element_type = RELATIONSHIP remains a valid, storable anchor value
                (§6, §8) — a policy MAY be created and activated against a RELATIONSHIP subject.

COVERAGE COMPUTATION:  for a RELATIONSHIP-anchored ACTIVE policy, has_qualifying_coverage_for_
                dimension returns False for EVERY required dimension, unconditionally, in H1 —
                identical treatment to an unsupported CoverageDimension (§12/§14) — because no
                evidence-resolution mechanism exists, not because of any computed negative result.

CONSEQUENCE:    coverage_satisfied is always False for a RELATIONSHIP-anchored ACTIVE policy in
                H1. Absent an open Finding, Reliance for that subject reads RELIANCE_UNKNOWN,
                never RELIANCE_SUPPORTED, never a fabricated True.

NO-POLICY CASE: unaffected — a RELATIONSHIP subject with no ACTIVE policy preserves its exact
                pre-H1 behavior (coverage contributed only via the existing indirect
                CurrentOntologyImpact-linked-Finding path, §18).
```

This is a deliberate, disclosed H1 boundary, not a defect: it is safe (never produces a false
`SUPPORTED`), backward-compatible (no-policy behavior is untouched), and requires no invented
evaluator model. A future governed phase may introduce a real relationship-evidence-resolution
mechanism; H1 does not attempt it.

## 16. No evaluation-attempt ledger — frozen decision

**Decision: NO**, for H1's scope. COMPLETENESS, VALIDITY (OQI1), and CONSISTENCY (OQI2) all persist an
evaluation row for every attempt regardless of outcome (SATISFIED or VIOLATED) — confirmed directly
against `has_any_evaluation_for_source_objects`'s own docstrings for both families. Neither has an
OQI3-style `NOT_EVALUABLE` zero-row concept. The `NEVER_ATTEMPTED` vs. `ATTEMPTED_BUT_NOT_EVALUABLE`
ambiguity this question is designed to guard against **does not exist for any dimension H1 touches**.
This question must be **reopened, not assumed resolved**, the day a future phase implements `ACCURACY`
or `REASONABLENESS` (both OQI3-shaped, both inheriting the `NOT_EVALUABLE`-zero-row precedent).

## 17. Reliance integration — frozen, exact call-site semantics

`derive_reliance_state` (the domain decision function itself) is **not modified**:

```python
subject_state = compute_subject_finding_state(...)          # UNCHANGED
coverage_satisfied = compute_generalized_coverage(           # generalized per §13
    ..., legacy_any_evaluation_ever_run=subject_state.any_evaluation_ever_run,
)
state, reason_codes = derive_reliance_state(
    any_open_finding=bool(subject_state.open_finding_refs),  # UNCHANGED
    any_evaluation_ever_run=coverage_satisfied,               # generalized VALUE, same parameter
    any_active_impact_unknown=False,                          # UNCHANGED — §26, not touched by H1
)
```

The parameter name `any_evaluation_ever_run` may remain unchanged at the call site if renaming it
would broaden the diff without semantic benefit — its *value* is generalized, its *name* is not
required to change for H1.

## 18. Backward compatibility — frozen, proven

**No `ACTIVE` `QualityCoveragePolicy` for a subject ⇒ H1 behavior == pre-H1 CDD-044 behavior**, for
every reachable input combination, proven by construction rather than asserted: the no-policy branch
of `compute_generalized_coverage` (§13) returns the literal, unmodified
`legacy_any_evaluation_ever_run` value — the exact boolean today's `_compute_coverage`-derived logic
already produces, computed by the exact same call, with zero new logic inserted between computation
and consumption. Since `any_open_finding` and `any_active_impact_unknown` are untouched, and
`derive_reliance_state` itself is untouched, every one of the eight reachable combinations of the three
boolean inputs produces an identical result pre- and post-H1:

| any_open | coverage (no policy) | impact_unknown (always False live) | Result |
|---|---|---|---|
| T | T | T | AT_RISK |
| T | T | F | AT_RISK |
| T | F | T | AT_RISK |
| T | F | F | AT_RISK |
| F | T | T | UNKNOWN (unreachable in live data, §26) |
| F | T | F | SUPPORTED |
| F | F | T | UNKNOWN (INSUFFICIENT_QUALITY_COVERAGE) |
| F | F | F | UNKNOWN (INSUFFICIENT_QUALITY_COVERAGE) |

No migration may create a policy row of any kind, `ACTIVE` or otherwise, for any existing tenant — this
is a release blocker, restated in §23.

## 19. No new Reliance reason code — frozen decision

`INSUFFICIENT_QUALITY_COVERAGE` (existing, `ReasonCode`, unmodified) remains semantically correct for
every case where `coverage_satisfied = False` — whether that's the legacy "zero evaluations of any
family ever ran" case or the new "an `ACTIVE` policy requires more than what's currently covered" case.
**No new `ReasonCode` member is authorized or required for H1.**

## 20. New crown invariant — frozen

```
PARTIAL REQUIRED COVERAGE ≠ SUPPORTED
```

**Required crown proof (frozen as the canonical H1 test case):**

```
GIVEN:  ACTIVE policy requires {COMPLETENESS, VALIDITY, CONSISTENCY}
        only COMPLETENESS has qualifying evaluation evidence
        zero open Findings exist

THEN:   RELIANCE_SUPPORTED is FORBIDDEN
EXPECT: RELIANCE_UNKNOWN, reason INSUFFICIENT_QUALITY_COVERAGE
```

Independent from `NO FINDINGS ≠ TRUSTED`: the latter concerns absence of Findings; this one concerns
insufficiency of *required* evaluation coverage. Both remain binding, simultaneously, and neither
subsumes the other — a subject can have zero Findings and still fail this invariant if its policy's
required dimensions are not all covered.

## 21. Existing crown invariants — reaffirmed, unmodified

```
MAJORITY ≠ TRUTH                    AUTHORIZATION ≠ REMEDIATION      VALID ≠ ACCURATE
AUTHORITY ≠ TRUTH                   REMEDIATION ≠ RESOLUTION         CONSISTENT ≠ ACCURATE
CANDIDATE ≠ TRUTH                   AUTHORIZATION_ID ≠ AUTHORITY     CANONICAL ≠ ACCURATE
AGENT ≠ FACT                        UNKNOWN ≠ LOW                    DUPLICATE CANDIDATE ≠ DUPLICATE FACT
RECOMMENDATION ≠ AUTHORIZATION      NO FINDINGS ≠ TRUSTED             ANOMALY ≠ QUALITY DEFECT
```

plus, newly adopted this document:

```
PARTIAL REQUIRED COVERAGE ≠ SUPPORTED
```

None of the pre-existing fifteen are touched by H1's scope — H1 introduces no agent, no
recommendation, no authorization, no remediation, no candidate, and no accuracy-adjacent concept of
any kind.

## 22. Configuration authority — frozen

```
oqi-coverage:configure
```

A new, distinct governed scope, required for any future mutation (create/activate/retire) of
`QualityCoveragePolicy`. Never satisfied by `oqi-remediation:authorize` or
`oqi-remediation:report-execution` — no code path may accept either as equivalent.
`oqi:read` remains the correct scope for any future *read* access to policy state, consistent with
every other OQI read route today. **H1 itself authorizes no public API** — this scope's declaration
(if implementation requires it to exist in configuration for internal enforcement readiness) is scoped
to the minimum exact file(s) named in the paired Artifact Authorization; its existence does not imply
or require a route.

## 23. No default policies — frozen, release blocker

The H1 migration **must not**: create any policy row of any kind; create any `ACTIVE` policy; infer
required dimensions from existing data; backfill policies for existing tenants; opt any tenant in
automatically. Post-migration, every existing tenant with no manually/service-created policy must
exhibit exactly pre-H1 Reliance semantics — proven in §18, restated here as a release gate: **H1-VM
must fail the release if any tenant's Reliance output differs after migration with zero policies
created.**

## 24. No public API / frontend in H1 — frozen boundary

Not authorized by this document: create-policy API, activate-policy API, retire-policy API,
list-policy API, policy-detail API, coverage-detail API, any frontend policy-management surface, any
Command Center coverage visualization. H1 establishes domain, persistence, coverage derivation,
Reliance integration, the configuration-authority scope declaration (if needed), tests, and
migration/runtime proof — nothing more. These deferred surfaces belong to a later governed boundary
(CDD-046 Boundary 8 and beyond).

## 25. Explainability minimum — frozen

H1 must be internally capable — at the code/query level, with no dedicated API or frontend required —
of deterministically deriving: whether an `ACTIVE` policy exists for a subject; its `policy_id`/
`version_number`; its `required_dimensions`; per-required-dimension covered/uncovered; and the overall
`coverage_satisfied` boolean. **Not authorized**: persisting a coverage percentage, a trust score, an
evidence-confidence value, a weighted coverage figure, or any coverage projection table. All of the
above remain deferred to whatever future phase builds the Command Center read surface.

## 26. Deferred defect — dead `IMPACT_UNKNOWN` branch (recorded, not touched)

`any_active_impact_unknown` is hard-coded `False` at the current Reliance call site
(`oqi_business_impact_service.py`), and `CurrentImpactStatus` is closed to exactly `ACTIVE`/`RESOLVED`
— structurally incapable of representing `IMPACT_UNKNOWN` today. This is an important future-hardening
observation, discovered during OQI-H1-DR. **It is explicitly out of scope for H1.** H1 must not modify
`CurrentImpactStatus`, ontology impact persistence or APIs, Reliance's third decision branch, or any
related test. No opportunistic repair is authorized under this document.

## 27. Adversarial governance review

Twenty targeted challenges, each answered against the frozen design above, not against intention:

1. *Can an unsupported dimension accidentally count as covered?* No — §12/§14 make it a structural
   `False`, never a computed outcome that could drift.
2. *Can no policy change existing behavior?* No — §18 proves identity by construction.
3. *Can a partial policy become Supported?* No — §13's loop returns `False` on the first uncovered
   required dimension; §20 is the direct crown proof.
4. *Can a tenant use another tenant's evaluation?* No — every coverage query is `tenant_id`-scoped,
   and `source_object_ids` are resolved via a tenant-scoped Entity Resolution lookup (§7).
5. *Can two ACTIVE policies exist?* No — §11's database-enforced partial unique index.
6. *Can a missing evaluator generate a fake Finding?* No — §12 explicitly prohibits this; nothing in
   §13/§14's design path touches Finding creation at all.
7. *Can QualityDimension accidentally expand to nine?* No — §5 freezes it untouched; `CoverageDimension`
   is structurally separate (§4).
8. *Can CoverageDimension be mistaken for implemented capability?* Guarded by §4's explicit inequality
   and §27 of the Artifact Authorization's claims-discipline requirement.
9. *Can policy configuration reuse remediation authority?* No — §22 names a distinct scope and
   explicitly forbids substitution.
10. *Can relationship legacy behavior change?* No — §15's no-policy case is explicitly unaffected.
11. *Can H1 accidentally repair IMPACT_UNKNOWN?* No — §26 explicitly forbids touching it.
12. *Can a migration create default policies?* No — §23 is a named release blocker.
13. *Can the seeder opt in accidentally?* No — §23 applies to any repository-side row creation,
    including seeding; the Artifact Authorization must enumerate the seeder as explicitly untouched.
14. *Can a coverage computation exception default True?* No — §13 requires propagation, explicitly
    forbidding any catch-and-default-True path.
15. *Can the normalized dimension table contain an unknown value?* No — §9 requires a database-level
    constraint against the closed `CoverageDimension` vocabulary.
16. *Can an empty policy become ACTIVE?* No — §8 forbids persisting an empty `required_dimensions` set
    as `ACTIVE`.
17. *Can historical policy versions be mutated?* No — §8/§10 require immutability; a change is always a
    new version.
18. *Can policy retirement leave ambiguous active state?* No — retirement is itself a new version with
    `status = RETIRED`; §11's uniqueness index still guarantees at most one `ACTIVE` row at any moment.
19. *Can implementation modify `derive_reliance_state` unnecessarily?* No — §17 explicitly forbids it;
    only the call-site input source is generalized.
20. *Can H1 introduce a trust score?* No — §25 explicitly forbids any numeric coverage figure.

All twenty are structurally safe under the frozen design. Zero defects required a design change during
this review — all were closed by decisions already present in §3-§26, confirming the architecture was
sound entering adversarial review rather than repaired by it.

## 28. Acceptance criteria (binding)

An H1 implementation is acceptable only if: it implements exactly §3-§26 without inventing additional
semantics; it does not modify `derive_reliance_state`, `QualityDimension`, `QualityRule`, or
`CurrentImpactStatus`; it creates no default/backfilled policy rows; it passes §20's crown proof and
every case in §18's truth table as real, executable tests; it enforces §11's uniqueness at the database
level, verified against real PostgreSQL; it satisfies §15's relationship boundary exactly (schema
permits, coverage always resolves `False`); and it satisfies the paired Artifact Authorization's Docker/
runtime verification requirements in full.

## 29. VM requirements (binding, for the future OQI-H1-VM phase)

Independent verification must confirm: authoritative main and approved implementation head; the exact
authorized path set and nothing beyond it; no unauthorized file; CDD-046, its erratum, and this document
byte-identical to their governed hashes; migration exactness (additive only, correct table-count delta,
clean up/down/up round trip); zero default policy rows post-migration; legacy behavior unchanged for
every existing tenant; `QualityDimension` still exactly three members; the six future evaluators still
entirely absent; an unsupported required dimension resolves uncovered; partial required coverage
resolves `UNKNOWN`; zero Findings plus insufficient required coverage does not resolve `SUPPORTED`;
complete required coverage plus zero Findings reproduces exactly today's `SUPPORTED` behavior; tenant
isolation; active-policy uniqueness under concurrency; idempotent re-derivation; full backend
regression; Docker image build, Compose health, migration-in-Docker, and demo-seeder compatibility. Any
material defect found: **STOP before merge.**

## 30. STOP conditions

None encountered in this governance phase. §15 resolved the one genuine STOP-shaped question in the
governing prompt (relationship coverage) via a narrow, safe, non-inventive fallback rather than halting
governance — the fallback itself (`coverage_satisfied` always `False` for that case) is the disclosed,
frozen boundary, not an open question deferred past this document.

## 31. Maximum truthful claim (if H1-I is implemented successfully)

> Noetva can enforce tenant-defined quality-coverage requirements before allowing a governed subject's
> Reliance to become Supported, while preserving legacy Reliance behavior exactly for every tenant that
> has not opted into a coverage policy. A policy may name any of Noetva's nine governed quality
> dimensions — but only Completeness, Validity, and Consistency currently have live evaluator
> implementations; the other six remain governed intent without evaluation capability until separately
> implemented.

## 32. Explicit non-claims

```
NINE DIMENSIONS IMPLEMENTED:              NO
ACCURACY / UNIQUENESS / TIMELINESS /
  INTEGRITY / CONFORMITY / REASONABLENESS
  IMPLEMENTED:                            NO
POLICY MANAGEMENT UI EXISTS:              NO
PUBLIC POLICY CRUD API EXISTS:            NO
RELATIONSHIP-ANCHORED POLICIES ACHIEVE
  REAL COVERAGE:                          NO (§15 — always uncovered in H1)
RELIANCE IS A TRUST SCORE:                NO
SUPPORTED MEANS TRUTH:                    NO
NO FINDINGS MEANS TRUSTED:                NO
```

## 33. Authorization

This CDD is approved for publication following OQI-H0, OQI-H1-DR, and explicit Product Owner decisions
PO-01 through PO-05. CDD-039 through CDD-046 (plus CDD-046's erratum) remain FROZEN and PUBLISHED,
unmodified by this document. Implementation is authorized only via the paired Artifact Authorization
companion, enumerating the exact, closed H1-I file surface.
