# CDD-032 — Governed Ephemeral What-if Simulation over Source-Evidence Fitness Impact and Remediation

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: RFC-010 (FROZEN, Canonical Enterprise Ontology Boundary — this CDD introduces no
cognitive capability and no canonical entity, §16 below), RFC-013 (FROZEN, Governance Authority and
Evaluation Separation — this CDD is pure Governance Evaluation exposure of a hypothetical, never
Governance Authority, §14, §16 below), CDD-017 (FROZEN, Blueprint Requirement Contract, unchanged), CDD-021
(FROZEN, Gate J, unchanged — not consumed by this CDD, per U-D4), CDD-023 (FROZEN, H4, unchanged — not
consumed by this CDD), CDD-024 (FROZEN, Gate N, unchanged — not consumed by this CDD), CDD-026 (FROZEN,
Gate K, unchanged — not consumed by this CDD, per U-D4), CDD-030 (FROZEN, Gate Q — the origin of this
CDD's own name and mandate: §21 names Gate U "What-if Simulation" and ties its "non-authoritative
requirement" to Gate Q's own untrusted-external-data boundary, §3 below; this CDD does not integrate Gate
Q's MCP client, per U-D2), CDD-031 (FROZEN, Gate T — the sole source of the frozen impact/remediation
service this CDD wraps by call only, never by reimplementation, §5 below)

Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN state via a Product-Owner-directed Gate U0 discovery
phase (which corrected an initially-implicit-but-incorrect framing of Gate U against frozen CDD-030 §21,
establishing that Gate U is What-if Simulation, not a Gate N/Gate T/Gate J/Gate K composition capability) →
Gate U1 Product Owner architecture-decision resolution (U-D1 through U-D4, all Option A) → Gate U2 drafting
→ Gate U3 Product Owner CDD review (disposition B — approve with two non-material corrections: a
single-field `WhatIfSimulationResult`, and this CDD-031-§28-reconciliation note, both applied below,
P0=0/P1=0/P2=0 after correction) → this Gate U4 publication turn. No implementation exists, and none is
authorized by this frozen document — a separate, subsequent Artifact Authorization companion remains
required before any file is created or modified.

## 1. Objective and business outcome

Answer, for an already-governed `InformationElementRequirement` and a caller-supplied **hypothetical**
`EvidenceFitnessStatus`: *if this requirement's evidence fitness were this hypothetical value instead of
whatever it actually is, what structural impact and remediation recommendation would Gate T report?* This
is the first, deliberately narrow implementation of the capability CDD-030 §21 named and deferred: *"Gate U
(What-if Simulation): this CDD's [Gate Q's] untrusted-external-data boundary (§13) is exactly what keeps
Gate U's own non-authoritative requirement satisfiable."* Gate U v1 is bounded to exactly one simulated
question — hypothetical fitness → impact/remediation — computed by calling Gate T's own frozen,
unmodified, zero-I/O impact/remediation service with synthetic input. The result is ephemeral and
non-authoritative: it is never derived from, and never written to, real evidence, mapping, decision, or
ontology state.

## 2. Governing authorities

(restated per header)

## 3. Relationship to CDD-030 §21 and the Gate U0 discovery audit

A Product-Owner-directed Gate U0 discovery/architecture phase confirmed, from CDD-030's own frozen text
(§6, §21, §26) and corroborated by CDD-016, that "Gate U" is a pre-existing, frozen name — *What-if
Simulation* — entirely distinct from any Gate N/Gate T/Gate J/Gate K composition capability. That
composition gap, while real, is explicitly **not** Gate U's responsibility (U-D1) and is deferred to the
post-Gate-U/X cross-gate capability audit. This CDD implements only what CDD-030 §21 actually named.

CDD-031 §28 (frozen, written during Gate T's own drafting, before this identity-correcting discovery)
describes a permissive, not mandatory, future compatibility — *"Gate U may consume Gate T's own
`EvidenceFitnessStatus | None` result as an independent sibling to Gate N's own composed result, keyed by
`information_element_requirement_id`."* This is not exercised by Gate U v1 and does not conflict with
U-D1's deferral of composition to the future cross-gate audit: §28 describes a data-level compatibility
that remains true regardless of what Gate U v1 implements, not a requirement that Gate U's first version
must consume Gate N's result at all.

## 4. Frozen upstream authorities (binding)

Gate T (CDD-031) remains the sole authority for `EvidenceFitnessStatus`, `EvidenceFitnessRemediationAction`,
`InformationElementEvidenceFitnessResult`, and `EvidenceFitnessImpactContext`. This CDD introduces no new
enum member to any of them and no reinterpretation of their semantics. Gate T's
`SourceEvidenceFitnessImpactRemediationApplicationService.derive(...)` is consumed exactly as-is, by direct
call, never modified, never reimplemented, never imported-and-forked.

## 5. Definitions

**Hypothetical fitness state**: a caller-constructed `InformationElementEvidenceFitnessResult` whose
`information_element_requirement_id` **must** correspond to a real, already-governed
`InformationElementRequirement` present in the supplied `Blueprint` (§8) — Gate U v1 answers "what if this
existing requirement's evidence were different," never "what if a new requirement existed." Its
`fitness_status` is caller-supplied and may be any `EvidenceFitnessStatus | None` value, entirely
independent of what Gate T's own real evaluation would currently report for that requirement. Its
`source_field_id` is carried through only as passthrough data (Gate T's impact/remediation service never
dereferences it) and may be synthetic. **Non-authoritative**: the simulation result carries no governance
authority (RFC-013) — it is never treated as, or convertible into, a real Gate T result, a real remediation
directive, or any persisted fact.

## 6. Gate U owned concepts (binding)

Gate U introduces exactly one new application service and one new result type. No new enum (§4). No new
domain entity. No new persistence model. No new ontology concept.

## 7. `WhatIfSimulationResult` contract (binding — new, Gate-U-owned type; U3 Correction 1 applied)

```python
@dataclass(frozen=True, slots=True)
class WhatIfSimulationResult:
    simulated_impact_context: EvidenceFitnessImpactContext
```

This type exists **specifically** so that a Gate U result is never structurally identical to, and can never
be silently mistaken for, a real Gate T `EvidenceFitnessImpactContext` returned directly — even though the
computation inside is exactly Gate T's own unmodified logic. `simulated_impact_context` is the exact,
unmodified `EvidenceFitnessImpactContext` Gate T's own `derive()` method produced for the supplied
hypothetical input — not a reinterpretation, not a subset, not a renamed copy of its fields. Wrapping it in
`WhatIfSimulationResult` is the entire mechanism by which "this is a simulation, not reality" is enforced at
the type level, without a redundant boolean marker field. The hypothetical `InformationElementEvidenceFitnessResult`
the caller supplied remains fully accessible via `simulated_impact_context.fitness_result` — Gate T's own
frozen field — so no second, duplicate top-level field is authorized (a single-field wrapper is deliberate,
not an omission: the earlier two-field draft reviewed at Gate U3 duplicated this same object under a second
name and was corrected before publication).

## 8. `WhatIfSimulationApplicationService` contract (binding)

```python
class WhatIfSimulationApplicationService:
    def simulate(
        self,
        *,
        hypothetical_fitness_result: InformationElementEvidenceFitnessResult,
        blueprint: Blueprint,
    ) -> WhatIfSimulationResult:
        ...
```

Constructs no dependency of its own beyond a direct instantiation of Gate T's unmodified
`SourceEvidenceFitnessImpactRemediationApplicationService` (or an equivalent constructor-injected instance —
deferred to Artifact Authorization, §17). Calls `.derive(fitness_results=(hypothetical_fitness_result,),
blueprint=blueprint)`, takes the single resulting `EvidenceFitnessImpactContext`, and wraps it. Performs no
I/O of any kind — a pure function over two already-in-memory, caller-supplied objects.

## 9. Input contract (binding, U-D2)

The caller supplies `hypothetical_fitness_result` directly — no repository read, no evidence lookup, no
Gate Q/MCP call of any kind. Gate U v1 does not source hypothetical input from any external system. A future,
separately-governed extension may add MCP-sourced hypothesis input (CDD-030 §21's own literal reading); this
CDD authorizes none of it.

## 10. Structural traversal (binding, restated from CDD-031, unchanged)

Owning-`ConceptRequirement`/relationship-context traversal is entirely Gate T's own, entirely unmodified,
entirely un-reimplemented. This CDD adds no traversal logic of its own.

## 11. Determinism (binding)

Identical `hypothetical_fitness_result` + identical `blueprint` → value-equal `WhatIfSimulationResult`,
inherited directly from Gate T's own already-proven determinism (CDD-031 §17). No `datetime.now()`, no
wall-clock field, anywhere in Gate U's own code.

## 12. Failure semantics (binding)

No new exception taxonomy. A hypothetical `information_element_requirement_id` with no owning concept in
the supplied `Blueprint` fails via Gate T's own existing `ValidationException` behavior, propagated
unchanged — Gate U does not catch, wrap, or reinterpret it.

## 13. Persistence / migration boundary (binding, U-D3)

**Zero persistence. Zero migration.** No table, column, cache, log, audit trail, or durable record of any
kind for any simulation result, request, or history. A `WhatIfSimulationResult` exists only for the
duration of the call that produced it.

## 14. API / frontend / MCP / dependency boundary (binding, U-D2, U-D3)

No new REST API endpoint. No frontend artifact. No MCP client invocation, no MCP catalog dependency, no
`mcp_client.py`/`mcp_connector_catalog.py` import of any kind. No new third-party dependency — stdlib only.
Proof lives entirely at the application-service/test layer, mirroring Gate T's, Gate Q's, and every prior
zero-I/O gate's own precedent.

## 15. Frozen Gate I/H4/N/J/K/Q/T firewall (binding)

Gate U does not modify, reinterpret, or import production logic from `semantic_coverage_evaluation.py`,
`information_element_evidence_availability.py`, `information_element_context_availability.py`,
`gap_impact_remediation.py`, `information_element_decision_prerequisite_assessment.py`, `mcp_client.py`,
`mcp_connector_catalog.py`, or `source_evidence_fitness_evaluation.py`. It calls exactly one existing,
unmodified public method of `source_evidence_fitness_impact_remediation.py`
(`SourceEvidenceFitnessImpactRemediationApplicationService.derive`) and consumes its already-public types.

## 16. Non-authoritative guarantee (binding, restated per RFC-013)

A `WhatIfSimulationResult` is Governance Evaluation exposure of a hypothetical only — never Governance
Authority (RFC-013). It must never be written to `field_value_evidence`, `semantic_mapping`, any decision or
readiness record, or any canonical ontology table (RFC-010) under any circumstance. No future extension of
this CDD's contract may silently begin treating a simulation result as authoritative without a new,
separate governance cycle.

## 17. Explicit non-goals (binding)

This CDD does not authorize: composition of Gate N + Gate T + Gate J + Gate K into one governed picture
(explicitly deferred, U-D1, §3); simulation of Gate J's or Gate K's own logic (deferred, U-D4); any Gate
Q/MCP-sourced hypothesis input (deferred, U-D2); any persistence of any kind (U-D3); any new REST API or
frontend surface; any new remediation-execution, approval, workflow, or agent capability (Gate R/S/V's own
future territory, untouched); any generalized Data Quality capability (datatype/format/business-rule/
allowed-domain validation, accuracy scoring, uniqueness, referential integrity, generalized completeness,
generic consistency, generic DQ scoring, confidence, cleansing, automatic correction — all explicitly
deferred to the post-Gate-U/X cross-gate audit, per this CDD's own Gate U0 discovery). This CDD does not
modify CDD-030, CDD-031, or any other frozen CDD.

## 18. Testable invariants

Identical input → value-equal output. No Gate U code path ever calls `datetime.now()`. No Gate U code path
ever writes to persistence. `WhatIfSimulationResult` is never structurally interchangeable with a bare
`EvidenceFitnessImpactContext` at the type level. A hypothetical `information_element_requirement_id` absent
from the supplied `Blueprint` always raises the existing shared `ValidationException`, never silently
returns a partial result. Gate T's own production file remains byte-unchanged before and after Gate U
implementation.

## 19. Acceptance criteria

1. A hypothetical `FIT` fitness state simulates a result whose `remediation_action` is `None`.
2. A hypothetical `STALE` fitness state simulates `REFRESH_SOURCE_EVIDENCE`.
3. A hypothetical `CONFLICTING` fitness state simulates `REVIEW_CONFLICTING_EVIDENCE`.
4. A hypothetical `None` fitness state simulates `remediation_action = None`.
5. The simulated result's structural context (`concept_requirement_id`, `entity_type_id`,
   `relationship_context`) matches exactly what Gate T's own `derive()` would produce for that
   `information_element_requirement_id` against the same `Blueprint`.
6. Repeated simulation with identical input is value-equal.
7. A hypothetical requirement ID absent from the Blueprint raises `ValidationException`.
8. No test or code path writes to any persistence store.
9. `source_evidence_fitness_impact_remediation.py`, and every other frozen production file, pass unmodified,
   with zero behavior change, before and after Gate U implementation.

## 20. Governance firewall / prohibited interpretations

No implementation of this CDD may reinterpret `EvidenceFitnessStatus`, `EvidenceFitnessRemediationAction`,
or any Gate T structural-traversal semantics. Gate U is a pure, ephemeral, read-only-in-effect sibling
consumer of Gate T's own frozen service — it does not supersede, narrow, broaden, or persist anything Gate T
itself does not already produce.

## 21. Rollback

Reverting this CDD's eventual implementation removes two small, self-contained new files with no
existing-file rollback required — no frozen file is ever modified.

## 22. Numbered architecture baseline determination

No new numbered architecture baseline is required, following the identical method every CDD since CDD-016
has used: this CDD cites RFC-010/013 and CDD-017/021/023/024/026/030/031 unchanged, and is registered via
`architecture/INDEX.md`'s existing "Governed implementation work orders" table alone.

## 23. Authorization

This document reached FROZEN status via: Gate U0 discovery (Product-Owner-directed, correcting an
implicit-but-incorrect framing against frozen CDD-030 §21) → Gate U1 Product Owner architecture-decision
resolution (U-D1 through U-D4, all Option A) → Gate U2 drafting → Gate U3 Product Owner CDD review
(disposition B, two non-material corrections applied — single-field `WhatIfSimulationResult`, §3
reconciliation note — P0=0/P1=0/P2=0 after correction) → this Gate U4 publication turn, under which this
document is published and frozen.

Implementation remains unauthorized. A separate, subsequent Artifact Authorization (Gate U5) is required
before any file governed by this CDD may be created or modified, matching every prior CDD's identical
multi-step discipline in this lineage.
