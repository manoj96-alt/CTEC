# CDD-044 — Ontology Quality Intelligence — Criticality, Business Impact & Explainable Reliance (OQI6)

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-039/040/041/042/043 (FROZEN, OQI1-5 — read-only consumed, never
modified), CDD-015 (FROZEN, Gate F — its `RiskSeverity`/supply-chain-impact traversal pattern is
read as precedent only, its concrete code is never modified or extended by this document)

Mandatory template: CDD Template v2.2

**Publication note**: this document freezes the architecture resolved across OQI6-DR (discovery)
and explicit Product Owner approval of that discovery report. It is the fourth CDD in this
repository to carry forward the `DR → G → I → VM` governed-delivery pattern established for
OQI4/OQI5.

## 1. Purpose

Determine, from deterministic governed evidence alone, why an ontology-quality condition matters to
a specific governed business context, and what level of reliance CTEC can currently defend for the
affected ontology knowledge — using explicit categorical states and first-class unknowns rather than
an arbitrary numeric score or any assertion of universal enterprise truth.

## 2. Capability claim (exact, binding)

CTEC can: attach governed, versioned criticality to an explicit, human-declared statement that a
named business process depends on a specific ontology subject (`BusinessDependency`); deterministically
derive, per dependency, whether an OPEN OQI1/2/3 Finding's OQI4-proven ontology impact identifies a
business consequence for that dependency, distinguishing an identified consequence from the mere
absence of known consequence from insufficient knowledge to conclude either; deterministically derive,
per ontology subject (independent of any particular business dependency), a categorical Reliance
State — `RELIANCE_SUPPORTED`, `RELIANCE_AT_RISK`, or `RELIANCE_UNKNOWN` — from the subject's own
Finding/coverage/ontology-impact evidence; explain every business-impact and reliance conclusion
through a closed, deterministic reason-code vocabulary bound to exact governed provenance; and do all
of this without ever treating agent recommendation, human authorization, external execution claims,
source majority agreement, or source authority metadata as the fact that establishes criticality,
business impact, or reliance.

No broader claim (real business-impact propagation across dependencies, monetary/financial exposure,
model-generated criticality/impact/reliance facts, model-generated explanatory narrative, autonomous
remediation, source write-back, or any frontend/dashboard/graph experience) is authorized by this CDD.

## 3. Why this CDD requires its own governance

OQI1-4 establish deterministic quality and ontology-impact facts. OQI5 establishes a governed,
human-authorized remediation pathway with optional real advisory reasoning. None of OQI1-5 answers
*why a quality condition matters* to a governed business context, or what CTEC can defensibly say
about reliance on the affected knowledge. Gate F (CDD-015) demonstrates, in miniature and for one
hard-coded domain (supply-chain disruption escalation), that ontology traversal can support a
business-consequence judgment — but its entity-type names, traversal depths, and consequence
category (`"Revenue Exposure"`) are frozen directly into Gate F's own application code (`app/
application/supply_chain_impact_api.py`, `app/domain/ontology_copilot/traversal.py`), not
governed as reusable, domain-neutral, per-tenant declared facts. This CDD is the first to introduce a
governed, domain-neutral `BusinessProcess`/`BusinessDependency` model and a governed, categorical
Reliance mechanism, without generalizing or modifying Gate F.

## 4. Definitions

- **Business Process**: a governed, versioned, tenant-scoped named unit of business activity
  (e.g. "Production Planning"), declared by a human, carrying no execution/workflow semantics of its
  own.
- **Business Dependency**: a governed, versioned, tenant-scoped statement that a named
  `BusinessProcess` depends on a specific ontology subject (`ontology_element_type` +
  `ontology_element_id`, the identical closed reference shape CDD-042 already uses — `ENTITY` or
  `RELATIONSHIP`, never an attribute/assertion-level subject). Criticality is a field of this
  statement, not of the ontology subject itself.
- **Criticality**: a governed, closed categorical assignment (`LOW`/`MEDIUM`/`HIGH`/`CRITICAL`) of
  how important one specific `BusinessDependency` is. The same ontology subject may carry different
  criticality in different business contexts. Absence of a governed assignment is
  `CRITICALITY_UNKNOWN`, never `LOW`.
- **Business Impact**: a per-`BusinessDependency` deterministic judgment of whether a governed,
  OQI4-proven ontology impact identifies a business consequence for that dependency's process.
- **Reliance**: a per-ontology-subject (not per-dependency) deterministic, categorical, evidence-bounded
  judgment of whether CTEC can currently defend depending on that subject's ontology knowledge,
  derived exclusively from that subject's own quality-evaluation coverage, open Findings, and OQI4
  ontology-impact state.
- **Reason Code**: one member of a closed, deterministic, non-prose vocabulary explaining a Business
  Impact or Reliance conclusion by naming the exact governed fact that produced it.
- **Coverage**: the deterministic evidence CTEC holds about whether quality evaluation has actually
  run against an ontology subject's evidence, distinct from whether that evaluation's outcome was
  clean.

## 5. In scope

**OQI6-I** (implementation, separately authorized by a future exact Artifact Authorization companion
gated behind this document): `BusinessProcess` (governed, versioned, tenant-scoped, non-BPM);
`BusinessDependency` (governed, versioned, tenant-scoped, criticality-bearing, referencing an OQI4-
shaped ontology subject); deterministic `BusinessImpactEvaluation`/`CurrentBusinessImpact` derivation
from OQI4's existing `CurrentOntologyImpact` and a subject's active `BusinessDependency` rows;
deterministic `RelianceEvaluation`/`CurrentReliance` derivation from an ontology subject's own
Finding/coverage/impact state; a closed reason-code vocabulary and provenance-bound explanation
contract; concurrency-safe current-state read/write design; the exact adversarial and crown test
matrix in §31-32.

## 6. Out of scope (binding)

Business-impact propagation across dependency chains (direct-only, §14). Monetary/financial exposure
of any kind. Model-generated criticality, `BusinessDependency`, business-impact fact, or Reliance
State (§21-22). Model-generated explanatory narrative — deterministic reason codes and provenance
only; grounded narrative generation, if ever built, belongs to OQI7 as a presentation-layer concern
consuming OQI6 facts, never an OQI6-persisted fact. Any modification to OQI1-5 domain or application
files, or to Gate F, Gate S, or Gate V files, or to any OQI1-4 persistence file beyond the four
narrow, additive-only, read-only query-method additions exactly authorized by §49/§49.1. Real source-system write-back.
Autonomous remediation. Any API endpoint (deferred). Any frontend/dashboard/graph UX (OQI7). Business
Process Management execution semantics of any kind (§9).

## 7. Terminology (binding)

```
PRODUCT VISION (marketing/UX language):        Explainable Trust
DETERMINISTIC MECHANISM (this CDD):            Explainable Reliance
DETERMINISTIC ARTIFACT:                        Reliance State / Reliance Assessment
```

"Trust score" and any numeric trust/reliance metric are never used anywhere in OQI6 governance,
domain naming, or persistence.

## 8. Reliance States (binding, closed, exactly three)

```
RELIANCE_SUPPORTED
RELIANCE_AT_RISK
RELIANCE_UNKNOWN
```

### 8.1 RELIANCE_SUPPORTED

Within the governed quality evaluations that CTEC has actually run against this ontology subject's
evidence, at least one such evaluation exists; zero of the subject's Findings across OQI1/2/3 are
currently `OPEN`; and no `CurrentOntologyImpact` row naming this subject currently carries
`IMPACT_UNKNOWN` for an unresolved (`ACTIVE`) impact. It represents a bounded, evidence-based
conclusion that no known unresolved condition prevents reliance under CTEC's governed quality
expectations — **it does not mean the ontology fact is universally true**, and it does not mean every
conceivable quality expectation has been evaluated, only that the ones CTEC has actually run found
nothing currently unresolved.

### 8.2 RELIANCE_AT_RISK

At least one Finding across OQI1/2/3 directly attributable to this ontology subject's own evidence,
or indirectly proven attributable via an `ACTIVE` `CurrentOntologyImpact` row naming this subject, is
currently `OPEN`. This is a statement that a known governed quality condition currently affects this
subject's knowledge sufficiently that reliance is not currently defensible — **it is not a statement
that the underlying ontology fact is false**, only that CTEC cannot currently rule out that it is
wrong.

### 8.3 RELIANCE_UNKNOWN

Either (a) CTEC holds zero persisted quality-evaluation evidence of any OQI1/2/3 family having ever
run against this subject's evidence (§18, coverage), or (b) zero Findings are `OPEN` but at least one
`ACTIVE` `CurrentOntologyImpact` row naming this subject carries `IMPACT_UNKNOWN`. `RELIANCE_UNKNOWN`
must never be presented, sorted, or defaulted as equivalent to `SUPPORTED`, `LOW RISK`, `NO IMPACT`,
or `SAFE` — it is a first-class, legitimate, and frequently correct product result.

## 9. Zero-Findings invariant (binding)

```
ZERO OPEN FINDINGS  ≠  RELIANCE_SUPPORTED
```

Absence of open Findings alone never proves sufficient evaluation coverage (§8.3(a)). This is the
single most important epistemic guardrail in this document.

## 10. Quality-satisfaction invariant (binding)

```
ALL RUN EVALUATIONS SATISFIED  ≠  UNIVERSAL ENTERPRISE TRUTH
```

OQI1/2/3 prove that governed expectations were satisfied against the evidence CTEC actually holds.
They never prove the underlying enterprise fact is universally, permanently true.

## 11. Concept separation (binding)

```
QUALITY            Does governed evidence satisfy governed expectations?         (OQI1/2/3, unmodified)
ONTOLOGY IMPACT     What ontology knowledge is proven affected?                  (OQI4, unmodified)
RELIANCE            Can CTEC currently defend reliance on that knowledge?        (OQI6, this CDD)
CRITICALITY         How important is one specific business dependency?          (OQI6, this CDD)
BUSINESS IMPACT     Does a proven ontology impact identify a business consequence
                    for one specific dependency?                                (OQI6, this CDD)
```

These five concepts are never collapsed into one score. Reliance is deliberately independent of
Criticality/Business Impact (§19); the same underlying quality condition produces the identical
Reliance State regardless of which — or how many, or how critical — business processes depend on the
affected subject.

## 12. Criticality anchor (binding)

**Criticality belongs to `BusinessDependency`, never to an entity type, a specific `EnterpriseEntity`
or ontology relationship, a `Finding`, a `QualityRule`, or an `AgentRecommendation`.** The same
ontology subject may carry different criticality in different business contexts:

```
Material ABC123  →  Production Planning   →  CRITICAL
Material ABC123  →  Sandbox Analytics     →  LOW
```

Neither assignment changes the underlying quality condition or Reliance State for Material ABC123 —
only which `BusinessDependency`'s Business Impact result differs.

## 13. Criticality vocabulary (binding, closed)

```
LOW
MEDIUM
HIGH
CRITICAL
```

An ordering may exist for deterministic sorting/filtering purposes only (`LOW < MEDIUM < HIGH <
CRITICAL`); this ordering carries no quantitative risk, monetary, or probabilistic meaning, and no
numeric weight is ever attached to it for aggregation.

## 14. Unknown criticality (binding)

Absence of a governed, `ACTIVE` `BusinessDependency` criticality assignment for a given dependency
yields the explicit result `CRITICALITY_UNKNOWN` — never `LOW`. No dependency row may be persisted
with a fabricated placeholder criticality merely to avoid a null.

## 15. BusinessProcess domain (binding)

A dedicated, minimal, governed domain object. Required fields (exact ORM/table design is OQI6-I's
own elaboration within this frozen semantics): `tenant_id`; a stable process identity; `version`;
governed `name`; optional bounded `description`; `status` (`ACTIVE`/`RETIRED`, closed); an optional
governed category tag from the minimal seed vocabulary in §17; creation/change provenance
(`created_by`, `created_on`). Versioned: a change to name/description/category creates a new version,
never a silent overwrite of history that a `BusinessImpactEvaluation` has already referenced.

### 15.1 BusinessProcess non-scope (binding)

Explicitly excluded, permanently, from `BusinessProcess`: BPMN or any workflow execution semantics,
process instances, task management, SLA engines, process mining, or any generalized BPM capability.
`BusinessProcess` is a governed reference fact, never an executable model.

## 16. BusinessDependency domain (binding)

A dedicated, governed, versioned, tenant-scoped domain object representing exactly the statement "this
`BusinessProcess` depends on this ontology subject, with this criticality." Required fields: a stable
dependency identity; `version`; `tenant_id`; `business_process_id` (FK); `ontology_element_type`
(`ENTITY`|`RELATIONSHIP`, the identical closed CDD-042 `OntologyElementType` vocabulary — no
attribute/assertion-level subject, since no evidence-backed attribute-level ontology lineage exists,
per OQI4's own §14 limitation carried forward unchanged); `ontology_element_id`; `criticality`
(§13-14); `status` (`ACTIVE`/`RETIRED`, closed); creation/change provenance. A criticality change is
a new governed version, never an in-place field mutation — historical `BusinessImpactEvaluation` rows
retain the criticality that was `ACTIVE` at their own construction time (§23).

### 16.1 Dependency absence (binding)

```
NO ACTIVE BusinessDependency RECORDED FOR A SUBJECT  ≠  NO BUSINESS IMPACT
```

CTEC's dependency coverage is inherently partial — a human has not necessarily declared every real
business reliance. Absence of a declared, `ACTIVE` dependency for an ontology subject that OQI4 has
proven impacted yields `BUSINESS_IMPACT_UNKNOWN` for that subject in general (there is, definitionally,
no per-dependency `BusinessImpactEvaluation` row to produce, since there is no dependency to evaluate
against) — this is a first-class "we do not know of a declared reliance," never a claim that no
process actually relies on it.

## 17. Business-impact category vocabulary (binding, minimal, extensible via governance)

An optional governed category tag on `BusinessProcess`, from this minimal seed set:

```
OPERATIONAL
FINANCIAL
COMPLIANCE
CUSTOMER
ANALYTICS
```

This vocabulary is a categorical descriptive tag, never a computed or inferred value, and never a
gateway to monetary quantification (§20). Extending this set is a governance action (a future,
explicit CDD-044 amendment), not an implementation-time or reference-pack-time decision — but no
supply-chain-specific value (`"Procurement"`, `"Order Fulfillment"`, etc.) may be frozen into this
core vocabulary; such specialization belongs to a future reference pack's own `BusinessProcess`
instance data, not to core category names.

## 18. Coverage model (binding, load-bearing)

CTEC's three quality-evaluation families have three different persistence disciplines for what "was
evaluated" means, and none of them today maintains a positive, queryable "applicable expectations
vs. evaluated expectations" ledger:

- **OQI1**: binary `SATISFIED`/`VIOLATED` (`app/domain/oqi/evaluation.py`). A Finding exists only for
  `VIOLATED`. There is no persisted evidence of a `SATISFIED` evaluation having actually run, distinct
  from "this rule was never evaluated at all," beyond whatever evaluation-run ledger OQI6-I's own
  coverage query is able to derive from OQI1's own evaluation history (not Finding history).
- **OQI2**: comparison observations (`CROSS_SOURCE_VALUE_CONFLICT`/`CROSS_SOURCE_PARTICIPANT_VALUE_
  MISSING`) drive Finding lifecycle; a `QualityComparisonEvaluation` row is persisted for every
  evaluation pass regardless of outcome (CDD-040 §9-14) — this family *does* carry a genuine "an
  evaluation ran" ledger.
- **OQI3**: `SATISFIED`/`VIOLATED`/`NOT_APPLICABLE` are persisted rows; **`NOT_EVALUABLE` produces zero
  persisted row at all** (CDD-041 §13, by deliberate design) — "never evaluated" and "evaluated as
  NOT_EVALUABLE" are therefore indistinguishable from row absence alone.

**Frozen coverage rule**: for a given ontology subject, "at least one quality evaluation has run"
(§8.3(a)'s `RELIANCE_SUPPORTED` precondition) is satisfied if and only if at least one persisted
evaluation row of any OQI1/OQI2/OQI3 family exists whose evidence resolves to that subject —
regardless of that evaluation's own outcome. `NOT_APPLICABLE` and `NOT_EVALUABLE` results do not by
themselves prevent `RELIANCE_SUPPORTED` (a rule correctly judged inapplicable, or an OQI3 evaluation
that produced no row because its own inputs were not evaluable, is not an open quality condition) —
but if the *only* evidence CTEC holds for a subject is an OQI3 `NOT_EVALUABLE` non-row (i.e., zero
other evaluation rows of any family exist), coverage is not established, and the result is
`RELIANCE_UNKNOWN` under (a), not `RELIANCE_SUPPORTED`. OQI6 introduces no new percentage, weighted
denominator, or "expectation completeness" computation — coverage is a boolean existence predicate
over real persisted evaluation rows, nothing more.

## 19. Reliance subject (binding)

The identical closed reference shape CDD-042 already established: `(tenant_id, ontology_element_type,
ontology_element_id)`, `ontology_element_type ∈ {ENTITY, RELATIONSHIP}`. No attribute/assertion-level
Reliance subject exists, for the identical reason OQI4 itself excludes one (§16). **Reliance is
assessed at the ontology-subject level, deliberately independent of any `BusinessDependency`** — this
is the frozen resolution of §92-93's ambiguity: had Reliance instead been computed per-dependency,
criticality would inevitably leak into the reliance computation (a `CRITICAL` dependency's owner would
be tempted to see a "worse" reliance state than a `LOW` dependency's owner for the identical
underlying quality condition). Keeping Reliance subject-level and Business Impact dependency-level
cleanly enforces §19's separation as an architectural fact, not merely a documentation promise.

## 20. Business-impact derivation (binding)

```
Quality Finding (OQI1/2/3, unmodified)
        |
        v
OQI4 CurrentOntologyImpact (unmodified; read-only)
        |
        v
Ontology Subject (ontology_element_type + ontology_element_id)
        |
        v
Active BusinessDependency row(s) naming that subject  (zero, one, or many)
        |
        v
Per-dependency BusinessImpactEvaluation
```

For one `(ontology subject, active BusinessDependency)` pair:

```
CurrentOntologyImpact.status = ACTIVE, outcome = IMPACTED   →  BUSINESS_IMPACT_IDENTIFIED
CurrentOntologyImpact.status = ACTIVE, outcome = IMPACT_UNKNOWN  →  BUSINESS_IMPACT_UNKNOWN
CurrentOntologyImpact.status = RESOLVED, or no relevant impact row exists  →  NO_KNOWN_BUSINESS_IMPACT
```

If the ontology subject carries a proven, `ACTIVE`, `IMPACTED` `CurrentOntologyImpact` row but **no**
`ACTIVE` `BusinessDependency` names that subject at all, no `BusinessImpactEvaluation` row is produced
for that subject (there is no dependency to evaluate) — this is `BUSINESS_IMPACT_UNKNOWN` at the
subject level (§16.1), reported distinctly from any dependency-scoped result.

## 21. Business-impact vocabulary (binding, closed — final wording)

```
BUSINESS_IMPACT_IDENTIFIED
NO_KNOWN_BUSINESS_IMPACT
BUSINESS_IMPACT_UNKNOWN
```

`BUSINESS_IMPACT_IDENTIFIED` is used in preference to OQI6-DR's working term `BUSINESS_IMPACT_KNOWN`
— "identified" more precisely names a positive, proven consequence rather than merely "known," which
could be misread as "known to be absent." `NO_KNOWN_BUSINESS_IMPACT` (never bare "NO BUSINESS
IMPACT," per §22) requires: an `ACTIVE`, `ACTIVE`-dependency-eligible `CurrentOntologyImpact` row
exists with outcome `NO_IMPACT`, or the impact row's status is `RESOLVED`. `BUSINESS_IMPACT_UNKNOWN`
covers every insufficient-knowledge case: `IMPACT_UNKNOWN` outcome, or no `ACTIVE` dependency exists
to evaluate against.

## 22. NO_KNOWN_BUSINESS_IMPACT proof burden (binding)

`NO_KNOWN_BUSINESS_IMPACT` requires an `ACTIVE` `BusinessDependency` naming the subject AND OQI4's own
proof (`CurrentOntologyImpact.outcome = NO_IMPACT` or `status = RESOLVED`) that the specific quality
condition does not currently affect that subject. It never means "there exists no business
consequence anywhere in the enterprise" — only that, for this one declared dependency, OQI4 found no
current proven impact.

## 23. BUSINESS_IMPACT_UNKNOWN (binding, mandatory first-class state)

Applies whenever: OQI4's own outcome is `IMPACT_UNKNOWN` for the subject; or no `ACTIVE`
`BusinessDependency` exists naming an otherwise-impacted subject; or the relevant
`CurrentOntologyImpact` row itself does not yet exist. `IMPACT_UNKNOWN` may never be silently
converted to `NO_KNOWN_BUSINESS_IMPACT` or to a `LOW`-criticality-flavored inference — it remains
`BUSINESS_IMPACT_UNKNOWN` until governed evidence resolves it (§24).

## 24. OQI4 `IMPACT_UNKNOWN` firewall (binding, restated)

```
OQI4 IMPACT_UNKNOWN  →  cannot silently become NO_KNOWN_BUSINESS_IMPACT
OQI4 IMPACT_UNKNOWN  →  cannot silently become "LOW business impact"
```

Unknown ontology impact remains unknown unless a fresh OQI4 evaluation resolves it — OQI6 introduces
no independent mechanism to resolve ontology-impact uncertainty.

## 25. Direct business impact only (binding, v1 boundary)

OQI6 v1 computes **direct** business impact only: one dependency's declared subject, evaluated against
that exact subject's own `CurrentOntologyImpact`. No transitive business-process propagation (e.g. "if
Production Planning is impacted, does downstream Shipping inherit impact?") exists in this scope. Any
future propagated business-impact capability requires its own separate governed propagation policy —
it is not authorized, implied, or scaffolded by this document.

## 26. OQI4 propagation ≠ OQI6 business propagation (binding)

CDD-042's own governed `ImpactPropagationPolicy` (deny-by-default, versioned relationship-type
enrollment) determines whether *ontology* impact propagates across relationship instances — this is
already active, unmodified, and consumed as-is by OQI6 through `CurrentOntologyImpact`. It does not
and cannot authorize any *business-process* propagation of its own; the two propagation questions are
independent, and OQI6 introduces zero mechanism for the second.

## 27. Monetary impact (binding, prohibited in v1)

**NOT AUTHORIZED.** No dollar, revenue, or cost exposure may be inferred, computed, or persisted from
Finding severity, criticality, quality dimension, ontology impact, or `AgentRecommendation`. Gate F's
own `$10,000,000` materiality threshold (`decision_engine/configuration.py`) is precedent that this
repository already requires monetary thresholds to be **governed constants supplied by a human**, not
computed — but that is Gate F's own separate, unmodified policy input, not a reusable OQI6 evidence
source. A future monetary-impact capability requires its own explicit governed financial-evidence
architecture; absent it, monetary impact remains permanently `UNKNOWN / NOT EVALUATED` in this scope.

## 28. Criticality/reliance separation (binding, restated with example)

```
CRITICALITY DOES NOT DIRECTLY CHANGE RELIANCE STATE.
```

```
Same open quality condition on ontology subject X:

X → BusinessDependency(Production Planning, CRITICAL)   →  Business Impact IDENTIFIED
X → BusinessDependency(Sandbox Analytics, LOW)           →  Business Impact IDENTIFIED

X's own Reliance State                                   →  RELIANCE_AT_RISK  (identical, either way)
```

Business consequence differs by context; the epistemic reliance conclusion about X's own knowledge
does not become more or less true because a business process happens to care more.

## 29. Criticality ≠ quality truth (binding, restated)

A `BusinessDependency`'s criticality assignment or version change never alters any `QualityEvaluation`,
`Finding`, or OQI4 `CurrentOntologyImpact` row. Criticality changes only affect future
`BusinessImpactEvaluation`/`CurrentBusinessImpact` reads for that dependency.

## 30. Business impact ≠ reliance (binding, restated)

A `CRITICAL`-context `BUSINESS_IMPACT_IDENTIFIED` result is never automatically equivalent to
`RELIANCE_AT_RISK` for the underlying subject — Reliance is derived exclusively per §8/§18/§19 from
the subject's own coverage/Finding/impact state, never from any `BusinessDependency` or
`BusinessImpactEvaluation` fact. (In practice they will very often coincide, since an `IMPACTED`
subject usually also has an `OPEN` Finding — but the derivations remain architecturally independent,
and a future subject could in principle have `RELIANCE_AT_RISK` with zero declared dependencies, i.e.
zero computable business impact at all.)

## 31. Multiple Findings, multiple families, multiple dependencies (binding)

**Multiple Findings** on one subject: existence-predicate aggregation only — any `OPEN` Finding of
any family, referencing the subject directly or via an `ACTIVE` impacted `CurrentOntologyImpact` row,
produces `RELIANCE_AT_RISK`; no averaging, weighting, or severity scoring across Findings is ever
computed. **Multiple quality families** (OQI1/OQI2/OQI3): composed via the identical existence
predicate — their outcomes are never treated as commensurable numeric dimensions, only as independent
sources of "is there an open condition" and "has evaluation coverage occurred" facts (§18).
**Multiple dependencies** on one subject: `BusinessImpactEvaluation` is computed **per dependency**,
never collapsed to a single "highest criticality" result — all governed contexts remain independently
visible (a future OQI7 summary view may sort/highlight by criticality for display convenience, but
the underlying per-dependency detail is never discarded or hidden by OQI6 itself).

## 32. N-source / majority / authority / agent invariants (binding, restated for OQI6)

```
N-SOURCE REALITY:            preserved through OQI2's own observations; OQI6 never collapses
                              "4 agree, 1 conflicts, 1 missing" into a single opaque percentage.
MAJORITY SOURCE AGREEMENT:   ≠ TRUTH.
SOURCE AUTHORITY:            ≠ TRUTH. May exist as evidence/context only.
AGENT RECOMMENDATION:        ≠ TRUTH, ≠ CRITICALITY, ≠ BUSINESS IMPACT, ≠ RELIANCE STATE.
```

## 33. OQI5 non-authority over OQI6 facts (binding)

None of the following restores or alters a Reliance State or Business Impact conclusion:

```
an existing AgentRecommendation referencing a candidate for this subject
a human RemediationAuthorization decision
an External Remediation Claim (execution report)
```

Only fresh immutable source evidence, processed by the owning OQI1/2/3 deterministic evaluator (and,
where relevant, a subsequent OQI4 re-evaluation), changes the underlying Finding/impact state that
OQI6 then reads. OQI6 introduces zero new evaluation logic and zero direct Finding/impact mutation of
its own.

## 34. AI boundary (binding)

Explicitly prohibited, unconditionally: LLM-generated criticality; LLM-generated `BusinessDependency`
or `BusinessProcess`; LLM-generated business-impact fact; LLM-generated Reliance State;
LLM-generated monetary exposure. No OQI6 domain object, table, or evaluation function may accept model
output as an input to any of the above. This boundary is structural (no code path exists), not merely
a policy statement enforced by convention.

## 35. Model-generated narrative (binding, out of OQI6 v1)

OQI6 owns deterministic facts, reason codes, and provenance chains only. If grounded narrative
generation over those deterministic facts is ever built, it is an OQI7 presentation-layer concern,
consuming OQI6's frozen contract (§39-41) read-only — it is never itself persisted as an OQI6 fact,
and this document authorizes no such capability.

## 36. Reason-code vocabulary (binding, closed, minimal)

```
OPEN_QUALITY_CONDITION            an OPEN Finding directly or impact-linked to the subject exists
INSUFFICIENT_QUALITY_COVERAGE     zero quality-evaluation rows of any family exist for the subject
ONTOLOGY_IMPACT_UNKNOWN           relevant CurrentOntologyImpact.outcome = IMPACT_UNKNOWN
BUSINESS_DEPENDENCY_UNKNOWN       no ACTIVE BusinessDependency names an otherwise-impacted subject
CRITICALITY_UNKNOWN               no ACTIVE criticality assignment exists for a named dependency
REMEDIATION_PENDING               an AgentRecommendation/RemediationAuthorization exists for a
                                   directly-referenced Finding but has not yet resulted in a fresh
                                   re-evaluation (advisory annotation only — never state-changing,
                                   per §33)
```

Reason codes are deterministic identifiers, never generated prose; every Reliance/Business-Impact
result carries the exact subset of these codes that produced it, and nothing else.

## 37. Provenance (binding)

Every `BusinessImpactEvaluation` and `RelianceEvaluation` row binds, at minimum, to: the exact
Finding identity/`state_revision`(s) considered; the exact `CurrentOntologyImpact`/underlying
`OntologyImpactEvaluation` identity considered; for business impact, the exact `BusinessDependency`
identity and version (and transitively its `BusinessProcess` identity/version); the exact set of
reason codes produced; `tenant_id`. No presentation text is persisted — only these deterministic
references and reason codes.

## 38. Historical immutability (binding)

`BusinessImpactEvaluation` and `RelianceEvaluation` rows are immutable once created. A later change
to Finding state, `BusinessDependency`/criticality, OQI4 impact, or coverage never rewrites a
previously-created evaluation row — it produces a new one, exactly as OQI1-4's own evaluation ledgers
already behave.

## 39. Current-state projections (binding)

Two mutable current-projection tables are required, mirroring OQI4's own immutable-evaluation /
mutable-current-projection pairing (`OntologyImpactEvaluation`/`CurrentOntologyImpact`) — this pattern
is reused because it has already been proven correct three times in this repository (OQI1's evidence
frontier, OQI3's atomic frontier, OQI4's impact projection), not merely copied by default:

- `CurrentBusinessImpact`: one mutable row per `(tenant_id, business_dependency_id)`, pointing at the
  latest `BusinessImpactEvaluation` for that dependency.
- `CurrentReliance`: one mutable row per `(tenant_id, ontology_element_type, ontology_element_id)`,
  pointing at the latest `RelianceEvaluation` for that subject.

Both projections carry no independent truth of their own — they are indexed pointers to the latest
immutable evaluation, exactly as `CurrentOntologyImpact` already is. This is necessary rather than
computed-on-read because a future OQI7 "what needs attention" summary view must be able to query
current state efficiently across many subjects/dependencies without re-deriving every historical
evaluation on every read.

## 40. Evaluation mode (binding)

OQI6 does not introduce a distinct `HISTORICAL`/`CURRENT_STATE` evaluation-mode parameter analogous to
OQI1's — each evaluation write is simply an immutable append (§38) plus a current-projection upsert
(§39); "historical" access is simply querying the immutable ledger directly by identity, with no
separate mode flag required.

## 41. Temporal coherence and concurrency (binding, load-bearing)

A `CurrentBusinessImpact`/`CurrentReliance` read that mixes an old Finding/impact state with a newer
`BusinessDependency` version (or vice versa) would manufacture an internally-inconsistent result that
no single coherent evaluation ever actually produced. Following this repository's own established
precedent for exactly this class of problem (OQI1's atomic evidence frontier, OQI3's CTE +
window-function frontier, OQI4's single recursive CTE folding graph traversal and propagation-policy
eligibility into one statement), any OQI6 current-state read/write that spans Finding state,
`CurrentOntologyImpact`, and `BusinessDependency`/criticality **must** be performed as one coherent
PostgreSQL statement or one explicit transaction snapshot, not as sequential, independently-committed
application-level reads. Where a mutable current-projection write requires serialization against
concurrent writers, OQI6 uses its own new, dedicated `pg_advisory_xact_lock` seed, distinct from every
OQI1/2/3/4 seed already in use — the exact seed value is OQI6-I's own implementation detail, frozen
here only as a requirement, not a specific integer.

## 42. Replay and idempotency (binding)

Repeated identical evaluation input must converge to the same immutable evaluation row (deterministic
identity derived from tenant + subject/dependency + exact contributing state — Finding
`state_revision`(s), impact evaluation identity, dependency version — never a random UUID, mirroring
every predecessor OQI evaluation's identity discipline) and must not create a duplicate current
projection row.

## 43. BusinessProcess / BusinessDependency lifecycle (binding)

`ACTIVE`/`RETIRED`, closed, for both. Retiring a `BusinessProcess` or `BusinessDependency` changes
only future/current computation eligibility — it never deletes or rewrites historical
`BusinessImpactEvaluation` rows that already referenced it. Destructive deletion of any governed
OQI6 fact is prohibited; retirement/versioning is the only lifecycle transition, consistent with this
repository's established precedent (OQI4's `ImpactPropagationPolicy` versioning, OQI5's `AgentRole`
versioning).

## 44. Criticality change (binding, restated)

A criticality change on a `BusinessDependency` is a new governed version. Historical
`BusinessImpactEvaluation` rows retain the criticality value that was `ACTIVE` at their own
construction time (via the versioned `business_dependency_id` + version they reference) — they are
never silently reinterpreted under a later criticality value.

## 45. Persistence plan (binding)

Six new tables, each justified individually — this is an independently re-derived count (two governed
reference domains × one table each, plus one immutable-ledger/current-projection pair each for
business impact and for reliance), not a quota carried forward from discovery by default:

| Table | Purpose | New governed fact | Why not derivable | Identity | Tenant boundary | Mutability | Versioned | Lifecycle |
|---|---|---|---|---|---|---|---|---|
| `oqi_business_processes` | governed named business process | a human declared this process exists | no existing table names business processes | stable id + version | `tenant_id` | insert-only per version | yes | ACTIVE/RETIRED |
| `oqi_business_dependencies` | governed dependency + criticality | a human declared this process depends on this ontology subject, with this importance | no existing table connects a business concept to an ontology subject with governed criticality | stable id + version | `tenant_id` | insert-only per version | yes | ACTIVE/RETIRED |
| `oqi_business_impact_evaluations` | immutable per-dependency impact ledger | deterministic proof of business consequence at one point in governed state | must be immutable and independently auditable, exactly like every other OQI evaluation ledger | deterministic digest of contributing state | `tenant_id` | immutable | N/A (append-only) | N/A |
| `current_business_impacts` | mutable current pointer per dependency | fast current-state read for future OQI7 | avoids re-deriving full history on every read; mirrors `CurrentOntologyImpact` | `(tenant_id, business_dependency_id)` | `tenant_id` | mutable (pointer only) | N/A | reflects dependency lifecycle |
| `oqi_reliance_evaluations` | immutable per-subject reliance ledger | deterministic proof of reliance conclusion at one point in governed state | must be immutable/auditable, independent of any dependency | deterministic digest of contributing state | `tenant_id` | immutable | N/A (append-only) | N/A |
| `current_reliance` | mutable current pointer per ontology subject | fast current-state read for future OQI7 | avoids re-deriving full history on every read; mirrors `CurrentOntologyImpact` | `(tenant_id, ontology_element_type, ontology_element_id)` | `tenant_id` | mutable (pointer only) | N/A | reflects subject's own evolving state |

No seventh table is authorized. If OQI6-I discovers this exact six-table model is insufficient or
excessive, that is a governance contradiction requiring a STOP and a return to Product Owner review —
not a silent implementation-time table addition or removal.

## 46. Table count (binding)

```
CURRENT (verified against real migrated schema, this document's own preflight): 94
TARGET:                                                                          100
NEW TABLES:                                                                      6
```

## 47. Migration (frozen as plan; not created by this document)

Next migration revision, verified against the 32-character `alembic_version.version_num` constraint
(the exact defect class that previously hit OQI2 and OQI5-I1): `0026_oqi6_reliance` — 18 characters,
safe. Filename may be more descriptive (filenames are unconstrained, only the `revision` string value
is constrained, per the established OQI2/OQI5 precedent): `0026_oqi6_criticality_business_impact_
reliance.py`. `down_revision = "0025_oqi5_agent_reasoning"` (current verified head). Expected
transition: `94 → 100`.

## 48. Migration round-trip requirement (binding)

The future Artifact Authorization must require a real-PostgreSQL round trip proving `94 → 100 → 94 →
100` with exact table-count assertions at each step, mirroring the exact discipline already proven at
OQI4/OQI5.

## 49. OQI4 firewall (binding)

No modification to any OQI4 domain or application file, and no write path of any kind into any OQI4
table. **Direct repository read-method verification finding**: `OntologyImpactEvaluationRepository`
(`oqi_ontology_impact_evaluation_repository.py`) exposes `get_current_impacts_for_finding` (queried
by Finding) and `get_evaluation` (queried by evaluation id), but exposes no existing method to read
`CurrentOntologyImpact` rows by ontology subject (`ontology_element_type` + `ontology_element_id`) —
exactly what §19/§58 require. OQI6-I is therefore authorized exactly one narrow, additive-only,
read-only query method addition to this one existing file (e.g. a
`get_current_impacts_for_subject(...)` method returning `CurrentOntologyImpact` rows for a given
tenant/subject) — it may add no other method, no write method, no schema change, and no change to
any existing method's behavior. This is the same narrow-additive-modification class OQI5-I2 itself
used for its own single authorized semantic MODIFY (§37 of CDD-043).

## 49.1 OQI1/OQI2/OQI3 coverage-read firewall (binding)

**Direct repository read-method verification finding**: none of `oqi_quality_evaluation_repository.py`
(OQI1), `oqi_cross_source_evaluation_repository.py` (OQI2), or
`oqi_business_rule_evaluation_repository.py` (OQI3) currently exposes a method to determine whether
at least one evaluation row of that family has ever been persisted for a given ontology subject —
exactly what §18's coverage rule requires. OQI6-I is authorized exactly one narrow, additive-only,
read-only query method addition to each of these three existing files (e.g. a
`has_any_evaluation_for_subject(...)` method per family) — the same narrow-additive class as §49,
each modifying no other method and adding no write path. Four files total across §49/§49.1 receive
this class of change; no fifth predecessor file may be touched under this authorization.

## 50. OQI5 firewall (binding)

No modification to any of: `ModelProvider`, `AgentRole`, `AgentRun`, `AgentEvidencePacket`,
`AgentRecommendation`, `RemediationCase`, `RemediationCandidate`, `RemediationInstruction`,
`RemediationAuthorization`, or their persistence/migration files. OQI6 may read
`RemediationCase`/`AgentRecommendation` state only for the advisory, non-authoritative
`REMEDIATION_PENDING` reason code (§36) — never write to any OQI5 table, never let an
`AgentRecommendation` field influence a Reliance/Business-Impact/Criticality computation. If a future
implementation discovers this read-only consumption is insufficient, that is a STOP-worthy
architecture question for separate Product Owner review, not an OQI6-authorized OQI5 modification.

## 51. Gate F firewall (binding)

No modification to any Gate F file (`app/application/supply_chain_impact_api.py`,
`app/domain/ontology_copilot/traversal.py`, `app/domain/decision_engine/*` as consumed by Gate F,
`app/integration/adapters/gate_f/*`, `app/integration/contracts.py`'s `RiskSeverity`/`SourcingStatus`,
or CDD-015 and its Artifact Authorization). Gate F remains historical predecessor behavior,
architecturally distinct from OQI6 (Gate F: should we requalify a second supplier source given a live
disruption event; OQI6: does an open quality Finding affect knowledge a business process relies on).
Potential future convergence between Gate F's hard-coded pattern and OQI6's governed model is
explicitly out of scope and not authorized by this document.

## 52. Source-write firewall (binding, restated)

No enterprise source-system write-back of any kind is introduced by OQI6.

## 53. OQI7 firewall (binding)

No frontend, dashboard, or graph-visualization implementation. OQI6 freezes only the deterministic
semantic contract OQI7 will eventually consume (§54-56) — no endpoint naming, no UI component, no
generated narrative.

## 54. OQI7-ready deterministic contract (binding, semantic only)

OQI6's eventual read surface must be sufficient, without OQI7 ever reconstructing an answer from raw
database internals, to answer:

```
What knowledge requires attention?           (subjects/dependencies with AT_RISK reliance or
                                               IDENTIFIED business impact)
Why is reliance at risk / unknown?            (reason codes + provenance chain)
Which quality Findings contribute?            (Finding identities + state_revisions in provenance)
Which ontology impact proves the connection?  (CurrentOntologyImpact / evaluation identity)
Which business process depends on it?         (BusinessDependency → BusinessProcess chain)
What criticality applies?                     (per-dependency criticality, or CRITICALITY_UNKNOWN)
What remains unknown, and why?                (reason codes naming the exact unknown dimension)
What changed after remediation/re-evaluation? (new evaluation rows superseding old ones, same
                                               immutable-ledger-plus-current-pointer pattern already
                                               proven by OQI1-4)
```

## 55. Why-should-I-care contract (binding)

Deterministic data sufficient for "this quality condition matters because...": `finding_id` +
`state_revision`, the `CurrentOntologyImpact`/evaluation identity that proved ontology relevance, the
`business_dependency_id`(s) + `business_process_id`(s) affected, the criticality of each, and the
resulting `BusinessImpactEvaluation` reason codes — every element a governed reference, zero generated
prose.

## 56. Why-can-I-rely / negative-explanation contract (binding)

Deterministic data sufficient for "reliance is SUPPORTED / AT_RISK / UNKNOWN because...", including the
mandatory negative/unknown cases:

```
"Reliance is UNKNOWN because quality coverage is insufficient"
    → reason code INSUFFICIENT_QUALITY_COVERAGE, zero evaluation rows found

"Business impact is UNKNOWN because ontology impact is unknown"
    → reason code ONTOLOGY_IMPACT_UNKNOWN, CurrentOntologyImpact.outcome = IMPACT_UNKNOWN

"Business impact is UNKNOWN because no governed dependency establishes whether this
 ontology subject is used by a business process"
    → reason code BUSINESS_DEPENDENCY_UNKNOWN, zero ACTIVE BusinessDependency rows
```

Unknown explanations are a product feature, not a failure mode, and must be as fully supported by
OQI6's contract as positive explanations.

## 57. Required epistemic table (binding, minimum rows)

| Condition | CTEC knows | CTEC does NOT know | Business Impact | Reliance |
|---|---|---|---|---|
| OPEN Finding, OQI4 IMPACTED, ACTIVE dependency exists | impact + dependency + criticality | — | BUSINESS_IMPACT_IDENTIFIED | RELIANCE_AT_RISK |
| OPEN Finding, OQI4 IMPACT_UNKNOWN | quality defect exists | ontology reach | BUSINESS_IMPACT_UNKNOWN | RELIANCE_AT_RISK |
| RESOLVED Finding, coverage sufficient, no other open condition | historical defect + resolution + current clean coverage | nothing new | per dependency, from current impact state | RELIANCE_SUPPORTED |
| No Finding ever evaluated for subject | nothing evaluated | everything | BUSINESS_IMPACT_UNKNOWN (no dependency evaluable either way) | RELIANCE_UNKNOWN |
| OQI4 IMPACTED, no ACTIVE dependency declared | ontology reach proven | business relevance | BUSINESS_IMPACT_UNKNOWN | RELIANCE_AT_RISK (Finding still OPEN) |
| ACTIVE dependency exists, no criticality assigned | dependency relationship exists | importance | evaluable (impact result independent of criticality) | unaffected (Reliance ≠ f(criticality)) |
| Only an OQI3 NOT_EVALUABLE non-row exists (zero other evaluation rows) | nothing positively evaluated | whether rule conditions were ever met | BUSINESS_IMPACT_UNKNOWN | RELIANCE_UNKNOWN |
| N-source conflict (OQI2), Finding OPEN | disagreement + support counts preserved | which value is "true" | per dependency, unaffected by dissent shape | RELIANCE_AT_RISK |
| AgentRecommendation + human authorization + external execution report exist, Finding not yet re-evaluated | a remediation action was reported | whether it actually worked | unaffected | RELIANCE_AT_RISK unchanged (REMEDIATION_PENDING annotation only) |

## 58. Required Reliance decision table (binding, deterministic, no weighting)

| Any OPEN Finding referencing subject (direct or via ACTIVE IMPACTED CurrentOntologyImpact)? | ≥1 evaluation row ever run for subject? | Any ACTIVE relevant IMPACT_UNKNOWN? | Result |
|---|---|---|---|
| Yes | — | — | `RELIANCE_AT_RISK` |
| No | No | — | `RELIANCE_UNKNOWN` |
| No | Yes | Yes | `RELIANCE_UNKNOWN` |
| No | Yes | No | `RELIANCE_SUPPORTED` |

## 59. Required Business Impact decision table (binding, per dependency)

| ACTIVE BusinessDependency exists? | Relevant CurrentOntologyImpact | Result |
|---|---|---|
| No | (any) | `BUSINESS_IMPACT_UNKNOWN` (subject-level; no dependency to evaluate) |
| Yes | `ACTIVE`, outcome `IMPACTED` | `BUSINESS_IMPACT_IDENTIFIED` |
| Yes | `ACTIVE`, outcome `IMPACT_UNKNOWN` | `BUSINESS_IMPACT_UNKNOWN` |
| Yes | `ACTIVE`, outcome `NO_IMPACT`, or `RESOLVED`, or no relevant row yet | `NO_KNOWN_BUSINESS_IMPACT` |

## 60. Worked examples (binding, mandatory)

**IMPACT_UNKNOWN (mandatory)**: Finding OPEN, OQI4 outcome `IMPACT_UNKNOWN` → Business Impact
`BUSINESS_IMPACT_UNKNOWN` (reason `ONTOLOGY_IMPACT_UNKNOWN`), Reliance `RELIANCE_AT_RISK` (reason
`OPEN_QUALITY_CONDITION` — the open Finding alone is sufficient regardless of impact uncertainty).

**No criticality (mandatory)**: `ACTIVE` dependency exists, no criticality assignment → dependency's
Business Impact is still computable (§59 does not require criticality), reported with
`CRITICALITY_UNKNOWN` as an additional descriptive fact, never blocking the impact result and never
affecting Reliance.

**No dependency (mandatory)**: OQI4 `IMPACTED`, zero `ACTIVE` dependencies → `BUSINESS_IMPACT_UNKNOWN`
(reason `BUSINESS_DEPENDENCY_UNKNOWN`); Reliance is unaffected by dependency absence and remains
`RELIANCE_AT_RISK` from the open Finding alone.

**Resolved → reopen**: historical `BusinessImpactEvaluation`/`RelianceEvaluation` rows for the earlier
state are never rewritten; a Finding's `RESOLVED` transition (via the existing, unmodified OQI1/2/3/4
re-evaluation path) produces new evaluation rows and updates the current-projection pointers only;
reopening later produces further new rows, exactly mirroring OQI1-4's own reopen discipline.

**Multiple dependencies (mandatory)**: `Material ABC123 → Production Planning (CRITICAL)`, `→
Reporting (MEDIUM)`, `→ Sandbox Analytics (LOW)` — three independent `BusinessImpactEvaluation`/
`CurrentBusinessImpact` rows, all visible; Material ABC123's own single `RelianceEvaluation` is
computed once, independent of which or how many dependencies exist.

## 61. Test obligations (minimum set, binding)

`BusinessProcess`/`BusinessDependency` versioning and lifecycle; criticality context and
`CRITICALITY_UNKNOWN`; direct business impact derivation for all three §59 outcomes; missing-dependency
`BUSINESS_IMPACT_UNKNOWN`; `IMPACT_UNKNOWN` firewall; monetary-inference absence (explicit grep-style
test); all three §58 Reliance outcomes including zero-Finding and insufficient-coverage cases;
OQI3 `NOT_EVALUABLE`-only coverage case (§18); multiple Findings/multiple families/multiple
dependencies aggregation; N-source conflict preservation through Business Impact; authority-conflict
non-resolution; resolved-Finding and reopened-Finding historical immutability; current-state replay
idempotency; concurrency (real PostgreSQL, per §41's advisory-lock requirement); tenant isolation
across every new table; OQI4 read-only integration; OQI5 non-authority (`AgentRecommendation` cannot
alter any OQI6 fact); Gate F firewall (no Gate F file touched); source-write firewall.

## 62. Required crown tests (binding, exact, minimum ten)

1. **N-source business impact**: `SAP/PLM/MES = ABC123, SupplierPortal = XYZ999, PIM = missing` → OQI2
   Finding OPEN → OQI4 IMPACTED on Material ABC123 → `ACTIVE` dependency on Production Planning,
   `CRITICAL` → `BUSINESS_IMPACT_IDENTIFIED` → `RELIANCE_AT_RISK`. Dissent (`XYZ999`) preserved
   visibly in the underlying OQI2 evaluation; never presented as resolved truth.
2. **Unknown impact**: Finding OPEN, OQI4 `IMPACT_UNKNOWN` → `BUSINESS_IMPACT_UNKNOWN`,
   `RELIANCE_AT_RISK`; assert no code path can produce `NO_KNOWN_BUSINESS_IMPACT` from this input.
3. **No dependency**: OQI4 `IMPACTED`, zero `ACTIVE` dependencies → `BUSINESS_IMPACT_UNKNOWN` at
   subject level; assert zero `BusinessImpactEvaluation` rows are created (nothing to evaluate).
4. **Remediation/restoration**: Finding OPEN → `RELIANCE_AT_RISK` → OQI5 `AgentRecommendation` +
   human `RemediationAuthorization` + External Remediation Claim recorded → assert Reliance remains
   `RELIANCE_AT_RISK` (reason `REMEDIATION_PENDING` added, not a state change) until fresh evidence
   drives the real, unmodified OQI1/2/3 evaluator to `SATISFIED`/resolve the Finding → only then
   re-evaluate OQI6 → Reliance changes only if §58's proof burden is now met. Assert zero direct
   Finding mutation anywhere in OQI6 code.
5. **Reopen**: `RESOLVED` → later fresh violating evidence → real evaluator → same Finding
   `REOPENED` → current Reliance responds via a new evaluation row; assert the prior, now-historical
   `RelianceEvaluation` row is byte-unchanged.
6. **Criticality separation**: identical underlying quality condition, two dependencies at `LOW` and
   `CRITICAL` → assert identical subject-level Reliance State, differing only in per-dependency
   Business Impact criticality context.
7. **Silence does not earn reliance**: zero Findings, zero evaluation rows ever persisted for a
   subject → assert `RELIANCE_UNKNOWN`, never `RELIANCE_SUPPORTED`.
8. **AI cannot alter OQI6 facts**: attempt, via direct function call, to have an `AgentRecommendation`
   or its referenced candidate value influence a criticality assignment, a `BusinessDependency` field,
   a `BusinessImpactEvaluation` outcome, or a `RelianceEvaluation` outcome — assert this is
   structurally impossible (no code path accepts an `AgentRecommendation`/`AgentRun` reference as an
   input to any of these four computations).
9. **Tenant isolation**: tenant A must not be able to read or have computed against it tenant B's
   `BusinessProcess`, `BusinessDependency`, `CurrentOntologyImpact`, or any OQI6 evaluation/current-
   projection row — assert fail-closed for every new table.
10. **No money**: assert no OQI6 computation path can produce, accept, or persist a monetary value;
    assert Gate F's `RiskSeverity`/Revenue-Exposure computation is never invoked by or leaked into any
    OQI6 code path.

## 63. Firewalls carried forward (binding, restated)

QualityRule/OQI1, OQI2 comparison semantics, OQI3 Kleene/seed-3/atomic-frontier, OQI4
impact/propagation-policy semantics, OQI5 remediation/agent-reasoning semantics, Gate S, Gate V, Gate
F: all untouched. No frontend/dashboard (OQI7). No monetary impact. No autonomous remediation. No
source write-back.

## 64. Defect register (carried forward, binding)

```
OQI-P3-001  64-bit advisory-hash collision / harmless over-serialization
OQI-P3-002  residual DB tenant defense-in-depth
OQI-P3-003  explicit correspondence scalability
OQI-P3-004  deferred composite evidence lookup index
OQI-P3-005  inherited historical replay race in OQI1/OQI2
OQI-P3-006  equal-temporal-key latest-evidence tie ambiguity
OQI-P3-007  no relationship types currently enrolled as propagation-eligible
OQI-P3-008  stale "Implementation state: NOT STARTED" doc-header drift in CDD-035/CDD-037
OQI-P3-009  no live-provider certification exists yet (nothing built); future operational debt
```
None closed by this document. The prior OQI5-VM merge-authority process violation is explicitly not
an OQI product P3 (a process-discipline finding, not a product defect). Gate F/OQI6 conceptual overlap
(§3, §51) remains a disclosed observation, not a defect, unless a real correctness conflict is later
demonstrated.

## 65. Migration plan (frozen as plan; not created by this document, restated)

See §47-48. `0026_oqi6_reliance` (revision string, 18 characters, safe), filename
`0026_oqi6_criticality_business_impact_reliance.py`, `down_revision = "0025_oqi5_agent_reasoning"`,
table transition `94 → 100`.

## 66. Implementation authorization relationship

Publication and freeze of this CDD does NOT itself authorize implementation. A companion Artifact
Authorization enumerates the exact, closed OQI6-I file surface. A further, separate Product Owner
implementation authorization remains required before OQI6-I may begin.

## 67. Maximum truthful claim (if OQI6-I is implemented successfully)

> OQI6 proves CTEC Ontology Quality Intelligence can deterministically connect governed
> ontology-quality conditions and OQI4-proven ontology impact to versioned business-process
> dependencies and contextual criticality; distinguish identified business impact from epistemic
> uncertainty without treating missing dependency knowledge as proof of no impact; derive
> categorical, evidence-bounded Reliance States without arbitrary trust scores; preserve quality
> coverage, unknowns, N-source disagreement, source authority, and remediation state without
> converting any of them into truth; and expose deterministic reason/provenance chains sufficient to
> explain why affected ontology knowledge can be relied upon, is at risk, or cannot yet be assessed.

## 68. Explicit non-claims

```
UNIVERSAL ENTERPRISE TRUTH:                NOT ESTABLISHED
RELIANCE_SUPPORTED = UNIVERSALLY TRUE:     NO
ZERO FINDINGS = RELIANCE_SUPPORTED:        NO
MAJORITY = TRUTH:                          NO
SOURCE AUTHORITY = TRUTH:                  NO
AGENT = TRUTH:                             NO
UNKNOWN = LOW:                             NO
UNKNOWN = NO IMPACT:                       NO
CRITICALITY CHANGES QUALITY TRUTH:         NO
CRITICALITY DIRECTLY CHANGES RELIANCE:     NO
ARBITRARY TRUST SCORE:                     NOT AUTHORIZED
MONETARY IMPACT:                           NOT AUTHORIZED
BUSINESS IMPACT PROPAGATION:               NOT IMPLEMENTED
LLM-GENERATED CRITICALITY:                 NOT AUTHORIZED
LLM-GENERATED BUSINESS IMPACT FACT:        NOT AUTHORIZED
LLM-GENERATED RELIANCE STATE:              NOT AUTHORIZED
MODEL-GENERATED OQI6 NARRATIVE:            NOT IMPLEMENTED
SOURCE WRITE-BACK:                         NOT IMPLEMENTED
AUTONOMOUS REMEDIATION:                    NOT IMPLEMENTED
OQI7 UI:                                   NOT IMPLEMENTED
```

## 69. Authorization

This CDD is approved for publication following explicit Product Owner architecture decisions across
OQI6-DR. CDD-039/040/041/042/043 and CDD-015's governance remain FROZEN and PUBLISHED, unchanged by
this document.
