# CDD-031 — Governed Source-Evidence Fitness Evaluation and Ontology Impact — Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `2d212a31db16d38042933ed78691ef300f575a09`

## 1. Purpose

Enumerates exactly which repository artifacts Gate T implementation may create or modify to satisfy frozen
CDD-031 — and nothing more. This document alone does not authorize implementation; a separate, subsequent
Product Owner implementation authorization remains required.

This record was produced through: discovery against the actual repository (Gate T5, tracing every proposed
artifact to CDD-031's own text, confirming placement precedent via `test_domain_foundation.py`'s exhaustive
domain-class scan and the `AUTHORIZED_CHANGED_PATHS` mechanism in `test_runtime_architecture.py`), an
adversarial Product Owner review (Gate T6, resolving four genuine Artifact-Authorization-level contract
decisions — T5-D1 through T5-D4 — plus edge-case and precedence confirmations, P0=0/P1=0/P2=0 after
resolution), and explicit Product Owner approval of the reviewed contract.

## 2. Implementation objective

Prove, entirely through two new, standalone application services, that CTEC can: (a) classify already-`MAPPED`,
already-`EVIDENCE_PRESENT` `InformationElementRequirement`s as `FIT`/`STALE`/`CONFLICTING` using only
`FieldValueEvidence.observed_at` and exact-value comparison, governed by a caller-supplied `as_of` and a fixed
7-day threshold; and (b) derive independent structural-impact context and deterministic remediation
recommendations for those classifications — without any new persistence, any new dependency, any modification
to Gate I/H4/Gate N/Gate J/Gate Q, and without establishing any generalized Data Quality, trust-scoring, or
confidence capability.

## 3. Exact artifact allowlist

CREATE:
- `backend/app/application/source_evidence_fitness_evaluation.py`
- `backend/app/application/source_evidence_fitness_impact_remediation.py`
- `backend/app/tests/test_source_evidence_fitness_evaluation.py`
- `backend/app/tests/test_source_evidence_fitness_evaluation_postgres.py`
- `backend/app/tests/test_source_evidence_fitness_impact_remediation.py`
- `backend/app/tests/test_source_evidence_fitness_impact_remediation_postgres.py`

MODIFY (exact change only, nothing else in the file):
- `backend/app/tests/test_runtime_architecture.py` — exactly one new, additive, comment-labeled Gate T block in
  `AUTHORIZED_CHANGED_PATHS` listing exactly the 6 CREATE paths above. No unrelated architecture-test refactor.

```
AUTHORIZED_NEW    = 6
AUTHORIZED_CHANGE = 1
TOTAL IMPLEMENTATION SURFACE = 7
```

No 8th implementation path is authorized under any circumstance without a new, separate Product Owner
decision. There is no exception for a small, mechanical, convenient, formatting-only, test-only,
configuration-only, "or equivalent," wildcard, directory-level, or otherwise "harmless" additional file.

## 4. Dependency contract (binding)

**No new dependency is authorized.** `backend/pyproject.toml` and any lockfile remain unchanged. Both new
modules use only Python standard-library `dataclasses`, `datetime`, `enum`, `typing`, and `uuid`.

## 5. Explicitly not required / not authorized

`backend/app/core/dependency_container.py` must remain unchanged — Gate T has no router and therefore no
`Container`-mediated dependency. `backend/app/main.py` must remain unchanged — no new REST endpoint is
authorized. `keycloak/ctec-realm.json` must remain unchanged — no new authentication mechanism. Gate T's
`EvidenceProvider` Protocol is declared locally, fresh, inside `source_evidence_fitness_evaluation.py` — it
must **not** import H4's own local `EvidenceProvider` Protocol from `information_element_evidence_availability.py`,
even though the two are structurally identical; this is a deliberate zero-coupling choice (Gate T6 Issue #5),
not an oversight. `Direction` and the relationship-context-entry type in
`source_evidence_fitness_impact_remediation.py` are likewise declared locally and fresh — they must **not**
import from, and no implementation may create a new shared/common module to deduplicate against,
`gap_impact_remediation.py`'s own `Direction`/`RelationshipContextEntry` (CDD-031's own text forbids importing
that file at all; Gate T6 Issue #6 additionally confirms no 8th file is authorized merely to deduplicate ~30
lines).

## 6. Module contracts (binding)

**`source_evidence_fitness_evaluation.py`**:

```python
class EvidenceProvider(Protocol):
    def get_by_source_field(
        self, *, tenant_id: str, source_field_id: UUID
    ) -> tuple[FieldValueEvidence, ...]: ...

class EvidenceFitnessStatus(StrEnum):
    FIT = "FIT"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"

@dataclass(frozen=True, slots=True)
class InformationElementEvidenceFitnessResult:
    information_element_requirement_id: UUID
    source_field_id: UUID
    fitness_status: EvidenceFitnessStatus | None

class SourceEvidenceFitnessEvaluationApplicationService:
    def __init__(self, *, evidence_provider: EvidenceProvider) -> None: ...

    def evaluate(
        self,
        *,
        evidence_availability_results: tuple[InformationElementEvidenceAvailabilityResult, ...],
        tenant_id: str,
        as_of: datetime,
    ) -> tuple[InformationElementEvidenceFitnessResult, ...]: ...
```

Emits exactly one `InformationElementEvidenceFitnessResult` for every element in the supplied H4 tuple (Gate
T6 Decision T5-D3) — `fitness_status=None` for `NO_EVIDENCE`/`EVIDENCE_EMPTY`, a computed `FIT`/`STALE`/
`CONFLICTING` value for `EVIDENCE_PRESENT`. `UNMAPPED` requirements remain structurally absent, since they
are never present in the H4 tuple Gate T consumes — Gate T takes **no** additional Gate I `coverage_result`
input to manufacture `None` entries for them. `information_element_requirement_id` and `source_field_id` are
read directly from each H4 result. `source_field_id` drives the `get_by_source_field` retrieval (CDD-031 §9).
Rows are grouped by `source_record_reference`, excluding empty `observed_representation` rows (CDD-031 §5,
T-D7), before conflict comparison (exact/raw, T-D4) and freshness comparison (`observed_at` vs. caller-supplied
`as_of`, strict `>7 days`, T-D3/T-D8; future-dated rows contribute to `STALE`, T-D9) are applied per group, then
rolled up per requirement with `CONFLICTING > STALE > FIT` precedence (T-D6). Output sorted by
`information_element_requirement_id` (implementation hygiene, not a CDD-031 mandate). **No** `evaluated_at`,
**no** `field_value_evidence_ids`, **no** `obligation`, **no** confidence, score, or generic quality field of
any kind (Decisions T5-D1, T5-D2, T5-D4).

**`source_evidence_fitness_impact_remediation.py`**:

```python
class Direction(StrEnum):
    OUTGOING = "OUTGOING"
    INCOMING = "INCOMING"

class EvidenceFitnessRemediationAction(StrEnum):
    REFRESH_SOURCE_EVIDENCE = "REFRESH_SOURCE_EVIDENCE"
    REVIEW_CONFLICTING_EVIDENCE = "REVIEW_CONFLICTING_EVIDENCE"

@dataclass(frozen=True, slots=True)
class EvidenceFitnessRelationshipContextEntry:
    relationship_type_id: UUID
    direction: Direction
    other_entity_type_id: UUID

@dataclass(frozen=True, slots=True)
class EvidenceFitnessImpactContext:
    fitness_result: InformationElementEvidenceFitnessResult
    concept_requirement_id: UUID
    entity_type_id: UUID
    relationship_context: tuple[EvidenceFitnessRelationshipContextEntry, ...]
    remediation_action: EvidenceFitnessRemediationAction | None

class SourceEvidenceFitnessImpactRemediationApplicationService:
    def derive(
        self,
        *,
        fitness_results: tuple[InformationElementEvidenceFitnessResult, ...],
        blueprint: Blueprint,
    ) -> tuple[EvidenceFitnessImpactContext, ...]: ...
```

Processes every `InformationElementEvidenceFitnessResult` supplied (mirroring Gate J's own "process every
element, remediate conditionally" pattern). Reimplements Gate J's owning-`ConceptRequirement`/
relationship-context traversal *pattern* locally (mirroring `_find_owning_concept`/`_relationship_context`
exactly in shape) — never imports from, extends, or modifies `gap_impact_remediation.py`. Zero I/O.
Remediation: `fitness_status=None` → `None`; `FIT` → `None`; `STALE` → `REFRESH_SOURCE_EVIDENCE`;
`CONFLICTING` → `REVIEW_CONFLICTING_EVIDENCE`. No positive `NO_ACTION_REQUIRED` literal is authorized (CDD-031
§16 permits exactly two remediation members).

## 7. Persistence / migration / API / frontend (binding)

Migration: **NONE**. New persistence: **NONE**. New ORM entity: **NONE**. Schema modification: **NONE**. New
repository method: **NONE**. Modified repository method: **NONE**. New REST API endpoint: **NONE**. Frontend:
**NONE**. `backend/app/core/dependency_container.py`: **unchanged**. `backend/app/main.py`: **unchanged**.
`keycloak/ctec-realm.json`: **unchanged**. Authentication/authorization model: **unchanged**. MCP invocation,
agent invocation, external remediation execution: **NOT AUTHORIZED**. The existing, unmodified
`FieldValueEvidenceRepositoryImpl.get_by_source_field(...)` is the sole evidence-retrieval path.

## 8. Forbidden implementation areas

`semantic_coverage_evaluation.py`; `information_element_evidence_availability.py`;
`information_element_context_availability.py`; `gap_impact_remediation.py`; `mcp_client.py`;
`mcp_connector_catalog.py`; CDD-031 itself; every other frozen CDD/AA; released architecture; any `frontend/*`
file; any migration file; `keycloak/ctec-realm.json`; `backend/app/core/dependency_container.py`;
`backend/app/main.py`. No import from `gap_impact_remediation.py` under any circumstance, including for
pattern reuse — the traversal shape is reimplemented locally, never imported.

## 9. Test obligations

**Eligibility/shape:** (1) `NO_EVIDENCE` → `fitness_status=None`; (2) `EVIDENCE_EMPTY` → `fitness_status=None`;
(3) `EVIDENCE_PRESENT` → exactly one of `FIT`/`STALE`/`CONFLICTING`; (4) one result per H4 tuple element
received; (5) `source_field_id` present; (6) `obligation` absent from the dataclass; (7) `evaluated_at` absent
from the dataclass; (8) `field_value_evidence_ids` absent from the dataclass; (9) repeated evaluation with
identical inputs and identical `as_of` produces value-equal results.

**Freshness/conflict:** (10) exactly 7 days old remains `FIT`; (11) older than 7 days produces `STALE`; (12)
future-dated evidence produces `STALE`; (13) identical values in a comparable group do not conflict; (14)
differing non-empty values in the same comparable group produce `CONFLICTING`; (15) differing values in
*different* `source_record_reference` groups do not conflict merely because they differ; (16) all-empty
comparable groups are excluded.

**T6 edge cases:** (17) an all-empty group plus a fresh, non-conflicting group on the same requirement →
`FIT`; (18) a group mixing one empty row with two differing non-empty rows → `CONFLICTING`; (19) a
future-dated row that is also part of a conflicting group → `CONFLICTING`; (20) old evidence that is also
conflicting → `CONFLICTING`; (21) one stale group plus another conflicting group on the same requirement →
`CONFLICTING`.

**Remediation:** (22) `FIT` → `None`; (23) `fitness_status=None` → `None`; (24) `STALE` →
`REFRESH_SOURCE_EVIDENCE`; (25) `CONFLICTING` → `REVIEW_CONFLICTING_EVIDENCE`; (26) owning-concept/
relationship traversal follows the Gate J structural pattern without importing from
`gap_impact_remediation.py`; (27) a missing owning concept produces the existing shared `ValidationException`
behavior.

**Failure/isolation/integration:** (28) repository evidence-retrieval failures propagate the existing
repository `ValidationException` unchanged; (29) tenant isolation is preserved; (30) Postgres integration
validates fitness evaluation against real repository-backed evidence; (31) Postgres integration validates
impact/remediation against a real, Postgres-sourced `Blueprint`.

No production-grade Data Quality test infrastructure of any kind — exactly these 31, nothing broader.

## 10. Implementation stop conditions

Implementation must STOP and return to Product Owner review if: `origin/main` moves from the approved
implementation baseline before implementation-branch creation; CDD-031 changes; this Artifact Authorization
changes; any §3 path proves insufficient; an 8th implementation file is required; any §8 forbidden file
appears necessary; persistence, migration, API, frontend, authentication, Keycloak, or a new dependency
becomes necessary; the module contracts in §6, the `EvidenceFitnessStatus` members, or the
`EvidenceFitnessRemediationAction` members would need to change; CI cannot pass without scope expansion; any
datatype/format/business-rule/allowed-domain validation, accuracy scoring, uniqueness checking, generalized
completeness, referential-integrity DQ rule, generic consistency rule, generic DQ scoring, confidence,
cleansing, or automatic correction appears necessary to satisfy an acceptance criterion (§9). No exception for
a "small harmless extra file." Total implementation surface is exactly 7 files; no 8th is authorized under
any circumstance without a new Product Owner decision.

## 11. Future Data Quality firewall

Gate T evaluates exactly two dimensions — freshness and exact-value conflict — as frozen by CDD-031. This
Artifact Authorization does not authorize, and no implementation under it may introduce, datatype validation,
format validation, business-rule validation, allowed-domain validation, accuracy scoring, uniqueness checking,
generalized completeness rules, referential-integrity DQ rules, generic consistency rules, generic DQ scoring,
confidence, cleansing, automatic correction, source-data mutation, DQ workflow, or DQ approval state. After
Gate T, Gate U, and Gate X are complete, a separate cross-gate capability audit will determine whether
additional governed capability is required for the broader chain (Observed Evidence → Governed DQ Rule/
Requirement → DQ Finding → Information Element → Ontology Concept/Relationship → Supply-Chain Requirement/
Function → Business Impact → Remediation Recommendation → Explanation/Provenance). Nothing in this Artifact
Authorization may preempt that future, separately-governed design.

## 12. Authorization

This Artifact Authorization is **approved for publication**, reached via Gate T5 (discovery/drafting) → Gate
T6 (Product Owner review, Decisions T5-D1 through T5-D4 resolved, P0=0/P1=0/P2=0) → Gate T7 (this publication
turn). **Publication/freeze of this Artifact Authorization does NOT itself authorize Gate T implementation.**
A separate, subsequent Product Owner implementation authorization (Gate T8) is required before any file in §3
may be created or modified — matching every prior CDD's identical multi-step discipline in this lineage
(CDD-025 through CDD-030).
