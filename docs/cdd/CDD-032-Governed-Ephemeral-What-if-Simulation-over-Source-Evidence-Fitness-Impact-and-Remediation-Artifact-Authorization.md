# CDD-032 — Governed Ephemeral What-if Simulation over Source-Evidence Fitness Impact and Remediation — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `410bd82b8b8e31e9a567fdf6928f02864b20be28`

## 1. Purpose

Enumerates exactly which repository artifacts Gate U implementation may create or modify to satisfy frozen
CDD-032 — and nothing more. This document alone does not authorize implementation; a separate, subsequent
Product Owner implementation authorization remains required.

This record was produced through: discovery against the actual repository (Gate U5, tracing every proposed
artifact to CDD-032's own text, re-verifying `source_evidence_fitness_impact_remediation.py`'s exact public
contract fresh from disk, confirming it remains unmodified since its own Gate T8 implementation commit) and
an adversarial review finding zero genuine architecture gaps beyond what CDD-032 itself already resolved —
the one point CDD-032 §8 explicitly deferred to this document (direct instantiation vs.
constructor-injection of Gate T's impact/remediation service) resolves unambiguously by existing repository
precedent (§6 below), requiring no Product Owner decision.

## 2. Implementation objective

Prove, entirely through one new, standalone application service, that CTEC can compute an ephemeral,
non-authoritative "what if" impact/remediation simulation for a caller-supplied hypothetical Gate T fitness
state, by direct, unmodified call to Gate T's own frozen
`SourceEvidenceFitnessImpactRemediationApplicationService.derive(...)` — without any new persistence, any
new dependency, any modification to Gate T or any other frozen producer, and without establishing MCP
integration, execution, approval, agent orchestration, generalized Data Quality, or Gate N/J/K composition.

## 3. Exact artifact allowlist

CREATE:
- `backend/app/application/what_if_simulation.py`
- `backend/app/tests/test_what_if_simulation.py`

MODIFY (exact change only, nothing else in the file):
- `backend/app/tests/test_runtime_architecture.py` — exactly one new, additive, comment-labeled Gate U block
  in `AUTHORIZED_CHANGED_PATHS` listing exactly the 2 CREATE paths above. No unrelated architecture-test
  refactor.

```
AUTHORIZED_NEW    = 2
AUTHORIZED_CHANGE = 1
TOTAL IMPLEMENTATION SURFACE = 3
```

No 4th implementation path is authorized under any circumstance without a new, separate Product Owner
decision. There is no exception for a small, mechanical, convenient, formatting-only, test-only,
configuration-only, "or equivalent," wildcard, directory-level, or otherwise "harmless" additional file.

## 4. Dependency contract (binding)

**No new dependency is authorized.** `backend/pyproject.toml` and any lockfile remain unchanged. The new
module uses only Python standard-library `dataclasses` and `typing`.

## 5. Explicitly not required / not authorized

**No Postgres integration test.** Gate U performs zero I/O (CDD-032 §8) and delegates 100% of structural
traversal to Gate T's own `derive()` method, which is already proven against a real, Postgres-sourced
`Blueprint` in `test_source_evidence_fitness_impact_remediation_postgres.py`. Re-proving that same traversal
correctness here would duplicate existing coverage without adding evidence value — directly mirroring H4's
own precedent for not re-testing `FieldValueEvidenceRepositoryImpl`'s query logic a second time. No new
repository method. No `dependency_container.py` wiring — Gate U has no router and therefore no
`Container`-mediated dependency. No `backend/app/main.py` change — no new REST endpoint. No
`keycloak/ctec-realm.json` change — no new authentication mechanism. No MCP client/catalog dependency of any
kind.

## 6. Module contracts (binding)

**`what_if_simulation.py`**:

```python
@dataclass(frozen=True, slots=True)
class WhatIfSimulationResult:
    simulated_impact_context: EvidenceFitnessImpactContext

class WhatIfSimulationApplicationService:
    def simulate(
        self,
        *,
        hypothetical_fitness_result: InformationElementEvidenceFitnessResult,
        blueprint: Blueprint,
    ) -> WhatIfSimulationResult: ...
```

`simulate` constructs `SourceEvidenceFitnessImpactRemediationApplicationService()` **directly, inline, with
no constructor injection** — resolving the one question CDD-032 §8 explicitly deferred to this document.
Gate T's own impact/remediation service is confirmed, by direct read of its frozen source, to declare no
`__init__` of its own (a zero-argument-constructible, stateless, pure-function class). Every other zero-I/O
sibling service in this codebase (`GapImpactRemediationApplicationService`,
`InformationElementContextAvailabilityApplicationService`) is likewise instantiated directly in tests and
callers, never constructor-injected — constructor injection in this codebase is reserved for real I/O
dependencies (`EvidenceProvider`, `BlueprintLookup`, `MappingResolver`) that benefit from test-double
substitution; Gate T's own service has no I/O to substitute, so injecting it would add indirection with no
testability benefit. `simulate` calls `.derive(fitness_results=(hypothetical_fitness_result,),
blueprint=blueprint)`, takes the single resulting `EvidenceFitnessImpactContext` (guaranteed exactly one
result for exactly one input by Gate T's own cardinality-preserving contract, confirmed by direct read of
`derive`'s list-comprehension implementation), and wraps it in `WhatIfSimulationResult`. Imports
`EvidenceFitnessImpactContext` from `source_evidence_fitness_impact_remediation.py` and
`InformationElementEvidenceFitnessResult` from `source_evidence_fitness_evaluation.py` — already-public
output type consumption only, matching Gate N's own precedent, never production logic import.

## 7. Persistence / migration / API / frontend / dependency (binding)

Migration: **NONE**. New persistence: **NONE**. New REST API endpoint: **NONE**. Frontend: **NONE**. Real
model provider: **NOT AUTHORIZED**. MCP client/catalog integration: **NOT AUTHORIZED**.
`backend/app/core/dependency_container.py`: **unchanged**. `backend/app/main.py`: **unchanged**.
`keycloak/ctec-realm.json`: **unchanged**.

## 8. Forbidden implementation areas

`semantic_coverage_evaluation.py`; `information_element_evidence_availability.py`;
`information_element_context_availability.py`; `information_element_decision_prerequisite_assessment.py`;
`gap_impact_remediation.py`; `mcp_client.py`; `mcp_connector_catalog.py`;
`source_evidence_fitness_evaluation.py`; `source_evidence_fitness_impact_remediation.py` (consumed by call
only, never modified); CDD-032 itself; every other frozen CDD/AA; released architecture; any `frontend/*`
file; any migration file; `keycloak/ctec-realm.json`; `backend/app/core/dependency_container.py`;
`backend/app/main.py`.

## 9. Test obligations

(1) hypothetical `FIT` → `remediation_action = None`; (2) hypothetical `STALE` →
`REFRESH_SOURCE_EVIDENCE`; (3) hypothetical `CONFLICTING` → `REVIEW_CONFLICTING_EVIDENCE`; (4) hypothetical
`None` fitness_status → `remediation_action = None`; (5) simulated structural context
(`concept_requirement_id`, `entity_type_id`, `relationship_context`) matches exactly what Gate T's own
`derive()` produces for the identical input; (6) repeated simulation with identical input is value-equal;
(7) a hypothetical `information_element_requirement_id` absent from the supplied `Blueprint` raises the
existing, unmodified `ValidationException`; (8) no persistence side effect — structural, no
session/repository object reachable anywhere in the module; (9)
`source_evidence_fitness_impact_remediation.py`, and every other frozen production file, pass unmodified
with zero behavior change, verified by diff; (10) `WhatIfSimulationResult` is never structurally
interchangeable with a bare `EvidenceFitnessImpactContext` at the type level; (11) module imports no
`Session`/`Repository`/ORM/`sqlalchemy` symbol and no MCP module; (12) module never calls `datetime.now()`.
No production-grade simulation-history or generalized-DQ test infrastructure of any kind — exactly these 12,
nothing broader.

## 10. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the approved
implementation baseline before implementation-branch creation; CDD-032 changes; this Artifact Authorization
changes; any §3 path proves insufficient; a 4th implementation file is required; any §8 forbidden file
appears necessary; persistence, migration, API, frontend, authentication, Keycloak, MCP, or a new dependency
becomes necessary; the module contract in §6 would need to change; CI cannot pass without scope expansion;
Gate J or Gate K simulation, or Gate N/T/J/K composition, appears necessary to satisfy an acceptance
criterion. No exception for a "small harmless extra file." Total implementation surface is exactly 3 files;
no 4th is authorized under any circumstance without a new Product Owner decision.

## 11. Future Data Quality firewall

Gate U simulates exactly the two dimensions Gate T itself evaluates — freshness and exact-value conflict —
as frozen by CDD-031, exposed hypothetically per CDD-032. This Artifact Authorization does not authorize,
and no implementation under it may introduce, datatype validation, format validation, business-rule
validation, allowed-domain validation, accuracy scoring, uniqueness checking, generalized completeness
rules, referential-integrity DQ rules, generic consistency rules, generic DQ scoring, confidence, cleansing,
or automatic correction. Gate J simulation, Gate K simulation, and the Gate N/T/J/K composition gap remain
explicitly deferred (CDD-032 §17, U-D1, U-D4) — this Artifact Authorization does not preempt them.

## 12. Authorization

This Artifact Authorization is **approved for publication**, reached via Gate U5 (discovery, drafting, and
adversarial review conducted together in one Product-Owner-authorized turn, P0=0/P1=0/P2=0, zero Product
Owner Artifact Authorization decisions required — the one point CDD-032 §8 deferred to this document
resolved unambiguously by existing repository precedent, §6 above). **Publication/freeze of this Artifact
Authorization does NOT itself authorize Gate U implementation.** A separate, subsequent Product Owner
implementation authorization (Gate U6) is required before any file in §3 may be created or modified —
matching every prior CDD's identical multi-step discipline in this lineage.
