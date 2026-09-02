# CDD-046 — QualityRule Ownership Erratum (OQI-H1-G)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-041-OQI3-I2-Provenance-Compound-Semantics-Historical-Replay-Amendment.md` (companion-
amendment pattern for a defect disclosed after publication, never an in-place rewrite of an
already-frozen CDD), `CDD-033-OQI7-Placeholder-Supersession-Amendment.md` (same-number amendment
precedent)
Classification: FACTUAL CORRECTION ONLY (tenant-ownership classification of one existing artifact;
does not reopen any other CDD-046 decision, does not authorize any QualityRule schema change, does
not authorize any implementation)

## 1. Purpose

Corrects one factual error in `CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md` (FROZEN),
discovered during OQI-H1-DR's repository-grounded discovery of Boundary 1. This amendment does not
reopen, weaken, or reinterpret any other part of CDD-046's frozen nine-dimension architecture.

## 2. Reference

`docs/cdd/CDD-046-OQI-Hardening-Nine-Dimension-Architecture.md`, §30 "Tenant model," row:

> `| Tenant rule instance (\`QualityRule\` row) | TENANT-OWNED | Existing precedent, unchanged |`

## 3. Exact incorrect statement

CDD-046 §30 classifies `QualityRule` as `TENANT-OWNED`, and states this classification reflects
"existing precedent, unchanged." Both the classification and the "unchanged precedent" framing are
incorrect.

## 4. Source-grounded correction

Direct verification against `backend/app/infrastructure/persistence/models/oqi_quality_rule.py`
(the `QualityRuleORM` class backing the `quality_rules` table) shows **no `tenant_id` column
anywhere in the model** — confirmed by reading the complete class definition, not inferred from a
partial match. The table's own governed identity is `quality_condition_id` (globally unique via a
partial unique index enforcing exactly one `ACTIVE` version per `quality_condition_id`, with no
tenant qualifier in that index). A parallel check of `backend/app/domain/oqi/quality_rule.py`
confirms **zero occurrences of the string `tenant` anywhere in the file** — no tenant-scoping logic
exists at the domain layer either.

This is consistent with `QualityRule.information_element_requirement_id` referencing
`InformationElementRequirement`, which is itself confirmed shared, global, product-owned structure
(`backend/app/infrastructure/persistence/models/blueprint.py`'s own docstring: "no `tenant_id`
anywhere," CDD-017 §9). A governed quality expectation tied to a shared Information Element
requirement is naturally shared platform structure itself, not a per-tenant artifact — the same
category as `entity_types`/`relationship_types`, not the same category as `QualityEvaluation` or
`QualityFinding` (both of which do carry `tenant_id`, confirmed directly, and remain correctly
classified as tenant-owned everywhere else in CDD-046 and in prior governance).

**Corrected classification:**

```
QualityRule (quality_rules table)   :  SHARED PLATFORM STRUCTURE, under the current implementation.
```

## 5. Non-effect on QualityCoveragePolicy

This correction does not alter, weaken, or cast doubt on any OQI-H1 architecture decision.
`QualityCoveragePolicy` was never derived from `QualityRule`'s tenant-ownership classification — its
own tenant-owned status was independently established by direct analogy to `BusinessDependency`
(CDD-044 §16) and `ImpactPropagationPolicy` (CDD-042 §8), both of which are tenant-owned rows
referencing shared platform anchors, exactly the shape `QualityCoveragePolicy` also takes. That
reasoning is unaffected by this erratum.

```
QualityCoveragePolicy   :  remains TENANT-OWNED. Unchanged by this erratum.
```

## 6. Explicit non-consequences (binding)

This erratum authorizes **none** of the following, and none may be inferred from it:

- No redesign of `QualityRule` is authorized.
- No `tenant_id` column is added to `QualityRule`, `quality_rules`, or any related migration.
- No change to `QualityRule`'s identity, versioning, activation, or validation behavior.
- No change to any evaluator, any Finding type, any test, any API route, or any frontend surface.
- No reopening of CDD-039's own frozen `QualityRule` architecture.

## 7. Confirmation

CDD-046's nine-dimension architecture — all 58 sections, all 33 architecture decisions, all 35
adversarial scenarios, all adopted crown invariants — remains frozen and unaffected by this
correction, except for the single §30 table row named in §3 above.

## 8. Repository evidence supporting this correction

```
File:    backend/app/infrastructure/persistence/models/oqi_quality_rule.py
Finding: QualityRuleORM declares no `tenant_id` column; identity keyed on
         `quality_condition_id` via a partial unique index with no tenant qualifier.

File:    backend/app/domain/oqi/quality_rule.py
Finding: zero occurrences of "tenant" anywhere in the file (grep-verified).

File:    backend/app/infrastructure/persistence/models/blueprint.py
Finding: InformationElementRequirement (referenced by QualityRule) is itself confirmed
         shared/global, no tenant_id, per its own module docstring (CDD-017 §9).

Baseline verified against: HEAD 5e3e7be5a038ada9929afb8b91ccdd3d2e5ded83 == origin/main, unchanged
throughout OQI-H0, OQI-H1-DR, and OQI-H1-G.
```

## 9. Effective governance interpretation

Everywhere CDD-046 or a future document reasons about which artifacts are shared platform structure
versus tenant-owned, `QualityRule` is to be read as **shared platform structure**, joining
`entity_types`, `relationship_types`, `institutional_concepts`, and `Blueprint`/
`InformationElementRequirement` in that category — never as a tenant-owned artifact. `QualityRule`'s
own evaluation output (`QualityEvaluation`) and any Finding derived from it remain tenant-owned,
exactly as previously and correctly documented.

## 10. Authorization

This erratum is approved for publication as a narrow, source-grounded correction. CDD-046 remains
byte-identical and FROZEN; this document is its sole authorized companion correction to date.
