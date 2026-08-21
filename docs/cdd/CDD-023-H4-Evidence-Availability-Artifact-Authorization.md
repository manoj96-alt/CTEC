# CDD-023 — H4 Evidence Availability Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `e75a6892ba705fc6ad89b7faf6889c968c311710`

## 1. Authority and scope

CDD-023 (FROZEN, PUBLISHED) authorizes H4 — Blueprint Information-Element Evidence Availability Evaluation
— as an architecture, but does not itself authorize writing any code against it (CDD-023 §3, §29, §33: "a
separate, subsequent artifact-authorization companion... is required before any file is created or
modified"). This report is that companion, following the identical CDD-Template-v2.2-compliant format
every prior phase in this lineage used (CDD-019's H1/H2/H3, CDD-020's I1, CDD-021's J1/J2, CDD-022's own
companion).

This record was produced through: a fresh, direct re-read of frozen CDD-023 in full, extraction of every
normative MUST/MUST NOT/REQUIRED/FORBIDDEN rule relevant to implementation, direct inspection of every
dependency contract and repository H4 would consume, and an exhaustive search for mechanical/exhaustive-set
test files that could be silently broken by the proposed artifact surface (§3 below) — deliberately
repeating, and this time avoiding, the exact class of gap CDD-022's implementation phase discovered
post-hoc in `test_domain_foundation.py`.

## 2. Objective (binding, restated from CDD-023 §1, §6)

Implement exactly the ephemeral, read-only evidence-availability classification CDD-023 authorizes: for a
tenant and an `InformationElementRequirement` Gate I has already classified `MAPPED`, determine
`NO_EVIDENCE` / `EVIDENCE_EMPTY` / `EVIDENCE_PRESENT` from the resolved `SourceField`'s persisted
`FieldValueEvidence` set, and return the exact, frozen seven-field `InformationElementEvidenceAvailabilityResult`
contract (CDD-023 §11). Never semantic/business satisfaction. Never persisted. Never a second Gate I/H2
resolution path.

## 3. Discovery findings (binding, restated for the record)

- **Domain-artifact placement, confirmed by direct precedent**: `backend/app/tests/test_domain_foundation.py`
  enumerates an exhaustive, hard-coded set of every class declared under exactly five "canonical domain
  roots" (`backend/app/domain/{foundation,integration,operational,semantic,shared}`) — confirmed by direct
  read of `DOMAIN_ROOT`/`canonical_domain_roots`. Gate I's `CoverageStatus`/`InformationElementCoverageResult`/
  `SemanticCoverageEvaluationResult` and Gate J's `Direction`/`RemediationAction`/`RelationshipContextEntry`/
  `GapImpactContext` all live in `backend/app/application/` and were **never** added to this file's
  `declared_classes` set — confirmed by direct grep, zero matches. `backend/app/application/` is not one of
  the five scanned roots. **This is the decisive, precedent-proven reason every H4 artifact in this
  authorization is placed exclusively in `backend/app/application/`, never `backend/app/domain/*`**: doing
  so makes `test_domain_foundation.py` structurally unreachable by this work, closing off the exact class of
  post-hoc authorization gap CDD-022's implementation phase discovered (that phase's own `FieldValueEvidence`
  had no choice but to live in `domain/integration/`, per CDD-022 §6's own binding placement; H4 has no such
  constraint — CDD-023 places no requirement on which layer implements it, and Gate I/Gate J's own precedent
  is unambiguous).
- **`backend/app/integration/` exhaustive-module check, confirmed by direct read**: `test_integration_architecture.py`
  enumerates an exhaustive set of files under `backend/app/integration/` (the Supplier-Risk pipeline
  package, CDD-022 §16/§2's disambiguation firewall — a different package from `backend/app/domain/integration/`).
  H4 does not touch this package in any way; this file requires no modification.
- **No exhaustive check exists over `backend/app/application/` module names**, confirmed by repository-wide
  search: unlike `domain/` and `integration/`, this layer has no closed-set enumeration test. Gate I's and
  Gate J's own additions there required no such file.
- **Migration-head/table-count assertions, confirmed unaffected**: `test_decision_engine.py`,
  `test_governance_engine.py`, `test_knowledge_engine.py`, `test_persistence_integration.py` all currently
  assert revision `"0016_field_value_evidence"` (and `table_count == 60`); CDD-023 §14/§29 authorize no
  migration, so these four files require no modification.
- **`AUTHORIZED_CHANGED_PATHS` mechanism, confirmed by direct read**: `backend/app/tests/test_runtime_architecture.py`
  — Gate I's own entry is exactly three paths (`application/semantic_coverage_evaluation.py`,
  `tests/test_semantic_coverage_evaluation.py`, `tests/test_semantic_coverage_evaluation_postgres.py`); Gate
  J's is the identical three-path shape. This authorization extends it by the identical three-path shape for
  H4 (§4 below).
- **Application-service architectural precedent, confirmed by direct read of `semantic_coverage_evaluation.py`
  and `gap_impact_remediation.py`**: every comparable service in this lineage lives in one single file per
  capability (enum + result dataclass(es) + Protocol(s) + service class together), uses constructor-injected
  `Protocol` dependencies only where real I/O is required (Gate I's `BlueprintLookup`/`MappingResolver`;
  Gate J needs none, since it is pure-function-over-already-in-memory-objects), and derives any `evaluated_at`
  field via `datetime.now(UTC)` **inside the service itself** at evaluation time
  (`SemanticCoverageEvaluationApplicationService.evaluate`'s own `evaluated_at=datetime.now(UTC)`,
  confirmed by direct read) — never supplied by the caller, never derived from persisted-fact timestamps.
  This is the direct precedent resolving CDD-023 §11.7's "invocation metadata only" requirement (§10 below).
- **`FieldValueEvidenceRepositoryImpl.get_by_source_field` ordering, confirmed by direct read**: its own SQL
  query already includes `.order_by(FieldValueEvidenceORM.field_value_evidence_id)` — a database-level UUID
  order that happens to coincide with canonical lexical string order (UUID byte-order comparison and
  canonical-hex-string lexical comparison are equivalent for the same digit encoding). **CDD-023 §11.6
  explicitly forbids deriving output ordering from "database retrieval order"** even where it happens to
  coincide — this authorization therefore requires the H4 service to independently, explicitly sort by
  canonical string form (§9 below), never relying on this incidental coincidence as the ordering mechanism.
- **Application-layer identifier-type convention, confirmed by direct read**: every ephemeral application
  result type in this lineage (`InformationElementCoverageResult.information_element_requirement_id`,
  `SemanticMappingResolution`'s own fields) uses bare `UUID`, never the domain `Identifier` wrapper. H4's
  own result fields follow this identical convention (§6 below).
- **Demo-fixture reuse, confirmed by direct read of `test_semantic_coverage_evaluation_postgres.py`**: Gate
  I's own Postgres acceptance test composes the real, unmodified `DemoSemanticMappingSeeder` for the H3 fixture
  without creating any seeder of its own. H4's Postgres test identically composes `DemoSemanticMappingSeeder`
  and `DemoFieldValueEvidenceSeeder` (both real, unmodified, already merged) — no new seeder file is
  authorized or required (§4).

## 4. Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/application/information_element_evidence_availability.py` | CREATE | CDD-023 §8-§17 | `EvidenceAvailabilityStatus(StrEnum)` — exactly `NO_EVIDENCE`/`EVIDENCE_EMPTY`/`EVIDENCE_PRESENT` (CDD-023 §8); `InformationElementEvidenceAvailabilityResult` — frozen, slotted dataclass, exactly the seven fields CDD-023 §11 binds: `information_element_requirement_id: UUID`, `obligation: Obligation`, `semantic_mapping_resolution: SemanticMappingResolution`, `source_field_id: UUID`, `evidence_availability_status: EvidenceAvailabilityStatus`, `field_value_evidence_ids: tuple[UUID, ...]`, `evaluated_at: datetime`; an `EvidenceProvider(Protocol)` structural contract, satisfied by the existing, unmodified `FieldValueEvidenceRepositoryImpl` (`get_by_source_field(*, tenant_id: str, source_field_id: UUID) -> tuple[FieldValueEvidence, ...]` only — no other method referenced), mirroring `MappingResolver(Protocol)`'s exact shape (§3); `InformationElementEvidenceAvailabilityApplicationService`, constructor-injecting exactly one `evidence_provider: EvidenceProvider` dependency, exposing exactly one public method `evaluate(self, *, coverage_result: SemanticCoverageEvaluationResult) -> tuple[InformationElementEvidenceAvailabilityResult, ...]` implementing §9's exact algorithm. | No `domain/` placement of any kind (§3). No second `Protocol` dependency (no `BlueprintLookup`, no `MappingResolver` — H4 never calls Gate I or H2 itself, §11 below). No fourth `EvidenceAvailabilityStatus` value. No eighth result field. No `tenant_id` field on the result (§13). No `evaluation_id`, no persistence, no ORM import, no `sqlalchemy` import of any kind (this file must remain a pure `application/`-layer module with no direct database access — only `evidence_provider`, a structural `Protocol`, ever touches persistence). No `latest`/`current`/`best` selection logic. No trim/normalize/coerce of `observed_representation`. No risk/impact/severity/remediation field or logic. No trust/confidence/staleness field or logic. No natural-language generation. No new exception type (reuses `ValidationException` only, by propagation — never raised fresh by this file itself except the duplicate-ID invariant check, §9). | Unit tests (Protocol-conforming stub, no DB) + Postgres acceptance tests. |
| `backend/app/tests/test_information_element_evidence_availability.py` | CREATE | CDD-023 §8-§17, §26 | Unit tests (no DB), mirroring `test_semantic_coverage_evaluation.py`'s exact `EvidenceProvider`-stub style — full matrix at §7 below. | No PostgreSQL dependency. No test of `FieldValueEvidenceRepositoryImpl`'s own query logic (proven elsewhere, CDD-022). | Direct test execution. |
| `backend/app/tests/test_information_element_evidence_availability_postgres.py` | CREATE | CDD-023 §8-§17, §26, §27 | Postgres-backed acceptance evidence, composing the real, unmodified `SemanticCoverageEvaluationApplicationService` (for a real Gate I result), the real, unmodified `FieldValueEvidenceRepositoryImpl`, and the new service — against the existing H3/CDD-022 demo fixture (`DemoSemanticMappingSeeder` + `DemoFieldValueEvidenceSeeder`, reused by call only) — full matrix at §7 below. | No new seeder file (§3). No test bypasses `FieldValueEvidenceRepositoryImpl` to query `field_value_evidence` directly. No modification to any seeder. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H/I/J phase | Add exactly the following 3 new string entries to `AUTHORIZED_CHANGED_PATHS`, mirroring Gate I's/Gate J's own identical three-path shape exactly: `"backend/app/application/information_element_evidence_availability.py"`, `"backend/app/tests/test_information_element_evidence_availability.py"`, `"backend/app/tests/test_information_element_evidence_availability_postgres.py"`. | No other entry added, removed, or altered. No change to the subset-comparison logic itself. No wildcard, no directory-level entry. `test_domain_foundation.py` is confirmed unaffected and is NOT added here (§3) — if implementation ever discovers otherwise, implementation MUST STOP and report it rather than silently modifying that file. | Direct test execution. |

No other repository path is authorized. In particular: `backend/app/domain/*`, `backend/app/infrastructure/persistence/*` (including any new repository, model, or migration), `backend/app/integration/*`, `backend/app/api/*`, any frontend file, `backend/app/application/semantic_coverage_evaluation.py`, `backend/app/application/gap_impact_remediation.py`, `backend/app/application/semantic_mapping_resolution.py`, `backend/app/infrastructure/persistence/field_value_evidence_repository.py`, `backend/app/domain/integration/field_value_evidence.py`, `docs/cdd/CDD-023-Blueprint-Information-Element-Evidence-Availability-Evaluation.md`, `docs/cdd/CDD-022-*`, `architecture/INDEX.md`, `architecture/released/*` are **not** authorized for modification.

## 5. Protected artifacts / architecture firewall table

| Protected artifact/class | Why protected | Enforcement in this record |
|---|---|---|
| `FieldValueEvidence`, its repository, its migration (CDD-022) | CDD-022 FROZEN + PUBLISHED; H4 consumes by call only | Not in CREATE/MODIFY list; `get_by_source_field` referenced by call only |
| `SourceObservation` (`backend/app/integration/contracts.py`) | CDD-022 §2/§17 firewall, restated by CDD-023 §23 | Not in CREATE/MODIFY list; no import |
| `SemanticCoverageEvaluationResult`/`InformationElementCoverageResult`/`CoverageStatus` (Gate I, CDD-020) | CDD-023 §17/§19 sole-input firewall | Consumed as a parameter only, never modified; no second resolution path |
| `SemanticMappingResolutionApplicationService` (H2, CDD-019) | CDD-023 §17 — H4 never independently re-resolves | Not imported anywhere in the authorized artifact set |
| `GapImpactContext`/`RemediationAction` (Gate J, CDD-021) | CDD-023 §20 firewall | Not in CREATE/MODIFY list; no import |
| `Blueprint`/`ConceptRequirement`/`InformationElementRequirement` domain model (CDD-017) | CDD-023 §5 — no modification authorized | Not in CREATE/MODIFY list; `InformationElementRequirement`/`Obligation` referenced by type only |
| `architecture/INDEX.md`, `architecture/released/*` | Already published; H4 implementation does not touch governance registration | Not in CREATE/MODIFY list |
| `backend/app/tests/test_domain_foundation.py` | Confirmed structurally unreachable by this work (§3) | Not in CREATE/MODIFY list |

## 6. Domain-model decision (binding, CDD-023 §11)

**No new `domain/` artifact of any kind.** `EvidenceAvailabilityStatus` and `InformationElementEvidenceAvailabilityResult`
are both `application/`-layer artifacts, matching `CoverageStatus`/`InformationElementCoverageResult`'s
identical placement exactly (§3). Both `information_element_requirement_id` and `source_field_id` are typed
`UUID` (bare), never the domain `Identifier` wrapper — matching every other ephemeral application-layer
result type's established convention in this lineage (§3). `semantic_mapping_resolution` is typed exactly
`SemanticMappingResolution` (the existing, unmodified type from `semantic_mapping_repository.py`), embedded
by reference from Gate I's own already-produced `InformationElementCoverageResult.resolution` field — never
independently constructed.

## 7. Application-service decision (binding, CDD-023 §17, §27)

One new file, one new service class: `InformationElementEvidenceAvailabilityApplicationService`, following
`SemanticCoverageEvaluationApplicationService`'s constructor-injection shape exactly, but injecting exactly
one `Protocol` dependency (`evidence_provider: EvidenceProvider`) rather than two, since H4 needs real I/O
for evidence retrieval but zero I/O for mapping resolution (Gate I's result is already supplied as a
parameter, never independently re-fetched — matching Gate J's own "supplied by the caller" pattern for its
own already-in-memory inputs, combined with Gate I's own "inject only what requires real I/O" pattern).

**Why a `Protocol` over the repository directly, rather than over an intermediate application service
(binding justification)**: Gate I's own two `Protocol`s (`BlueprintLookup`, `MappingResolver`) are each
structurally satisfied by an existing *application-layer service* (`BlueprintApplicationService`,
`SemanticMappingResolutionApplicationService`), not a raw repository. CDD-022, however, authorizes no
`application/`-layer service of any kind over `FieldValueEvidence` — its own artifact set is
domain+persistence only (confirmed by direct read of CDD-022's own Artifact Authorization §4), so no such
intermediate service exists for H4 to depend on. `EvidenceProvider` is therefore structurally satisfied
directly by `FieldValueEvidenceRepositoryImpl`, narrowed to expose **exactly** `get_by_source_field`'s
existing signature — `get_by_id` and `create_or_get_existing` are deliberately excluded from the `Protocol`,
since H4 has no legitimate use for either. This narrowing is a strict subset of the real repository's public
interface, with a byte-identical signature for the one method exposed — it does not broaden, reinterpret, or
add any capability to CDD-022's frozen repository contract (CDD-022 §13, §22, §25, unchanged); it exists
solely for the identical testability/decoupling reason every other `Protocol` in this lineage exists (a
unit-test stub, avoiding a real database dependency in `test_information_element_evidence_availability.py`,
§14).

**Exact public method signature (binding)**:

```
def evaluate(
    self, *, coverage_result: SemanticCoverageEvaluationResult
) -> tuple[InformationElementEvidenceAvailabilityResult, ...]:
```

**Exact input (binding)**: exactly one parameter, `coverage_result: SemanticCoverageEvaluationResult` — Gate
I's own already-produced result (CDD-023 §17's sole authorized mapping-resolution input). No separate
`tenant_id` parameter is authorized: `coverage_result.tenant_id` (already a field on that type) is the sole
tenant source for every evidence lookup this evaluation performs — avoiding two independently-suppliable,
potentially-disagreeing tenant inputs. No `blueprint`/`blueprint_name` parameter (H4 does not enumerate
requirements itself; it only classifies entries `coverage_result` already contains).

## 8. Gate I integration / MAPPED-only filtering (binding, CDD-023 §12, §17-§19)

For each `InformationElementCoverageResult` in `coverage_result.information_element_results`:
- If `element.status is not CoverageStatus.MAPPED`: **skip entirely** — no
  `InformationElementEvidenceAvailabilityResult` is constructed for it (CDD-023 §13). `UNMAPPED` MUST NOT
  produce `NO_EVIDENCE` or any other H4 result.
- If `element.status is CoverageStatus.MAPPED`: `element.resolution` is guaranteed non-`None` by Gate I's
  own construction (`SemanticCoverageEvaluationApplicationService.evaluate`'s `status = MAPPED if resolution
  is not None else UNMAPPED`, confirmed by direct read) — this authorization does not require, and MUST
  NOT add, a defensive `None`-check raising a new exception for this case; it is a structural invariant of
  the already-frozen, already-implemented Gate I contract, not a runtime possibility H4 must separately
  guard.

No `Protocol` for Gate I or H2 is authorized on this service (§4's Exclusions column, binding) — the
already-produced `coverage_result` parameter is the only channel by which mapping information enters H4.

## 9. Classification algorithm (binding, exact, CDD-023 §8-§9, §11.6-§11.7)

**Step 0, once per `evaluate(...)` call, before iterating any element (binding — see §10)**:
`invocation_evaluated_at = datetime.now(UTC)`. Computed exactly once per call, never re-computed per
element.

For each `MAPPED` element (§8 above), in this exact order:

1. `source_field_id = element.resolution.source_field_id` (already a bare `UUID` on `SemanticMappingResolution`).
2. `evidence_rows = evidence_provider.get_by_source_field(tenant_id=coverage_result.tenant_id, source_field_id=source_field_id)`
   — propagate any raised `ValidationException` (tenant-ownership mismatch or `SourceField` not found)
   unchanged; do not catch, suppress, or convert it (CDD-023 §16, §26). **No result is constructed for this
   element if this call raises** — the exception propagates out of `evaluate(...)` entirely.
3. Classification (pure `==`/`!=` string comparison only, never `.strip()`, never case-folding, never
   datatype interpretation, CDD-023 §8):
   - `len(evidence_rows) == 0` → `EvidenceAvailabilityStatus.NO_EVIDENCE`.
   - `len(evidence_rows) > 0` and every `row.observed_representation == ""` → `EvidenceAvailabilityStatus.EVIDENCE_EMPTY`.
   - `len(evidence_rows) > 0` and at least one `row.observed_representation != ""` → `EvidenceAvailabilityStatus.EVIDENCE_PRESENT`.
   - Whitespace-only `observed_representation` (e.g. `" "`) counts toward the `!= ""` branch — `EVIDENCE_PRESENT` (CDD-023 §8, binding, no exception).
4. Evidence-ID provenance (CDD-023 §11.6, binding): `field_value_evidence_ids` MUST contain the identity of
   **every** row in `evidence_rows` (the identical set classified in step 3 — no separate filtering pass,
   no non-empty-only subset, no single "winning" row selected).
5. Canonical ordering (CDD-023 §11.6, binding): sort the collected identities by the **ascending lexical
   order of each identifier's canonical string representation** — `sorted(ids, key=str)`, where `str(uuid_value)`
   is the identical "canonical string form" convention CDD-022 §10 already establishes for `source_field_id`'s
   own identity material (`str(uuid_value)`, unmodified — the standard lowercase-hyphenated 36-character
   form) — **independently of `get_by_source_field`'s own database-level ordering**, even though that
   ordering happens to coincide (§3). Implementation MUST NOT remove or rely on this defensive re-sort merely
   because the repository's own query already happens to return the same order.
6. Duplicate-identity invariant (CDD-023 §11.6, binding): if any two rows in `evidence_rows` share the same
   `field_value_evidence_id` (a data-integrity violation, since CDD-022 §25 guarantees domain-verified
   uniqueness), implementation MUST raise `ValidationException` explicitly — never silently deduplicate,
   never silently accept the duplicate as ordinary provenance.
7. `evaluated_at = invocation_evaluated_at` (Step 0's single, already-computed value) — **never** a fresh
   `datetime.now(UTC)` call per element (§10, binding).
8. Construct `InformationElementEvidenceAvailabilityResult` with all seven fields (§6) and append to the
   result tuple.

Final return value MUST be a stable, deterministic ordering across the outer result tuple too, mirroring
`SemanticCoverageEvaluationApplicationService._sorted`'s and `GapImpactRemediationApplicationService._sorted`'s
identical precedent: sort by `information_element_requirement_id`. This ordering rule is not itself stated
by CDD-023, but is a harmless, precedent-mandated implementation detail — CDD-018 §21 (cited unchanged by
this entire lineage) binds exactly this rationale ("stable, deterministic order... so that two evaluations
of unchanged state are not merely equal as sets but structurally identical") for every multi-result
evaluation service descended from it; it introduces no new business semantics CDD-023 did not already imply
by requiring fields 1-6 be deterministic (§10 below, CDD-023 §25).

## 10. `evaluated_at` mechanics (binding, CDD-023 §11.7, §14)

Owned exclusively by `InformationElementEvidenceAvailabilityApplicationService.evaluate` itself — not a
constructor parameter, not a method parameter, not read from any persisted timestamp.

**Cardinality (binding, resolved from CDD-023's own wording)**: CDD-023 §11 defines `evaluated_at` as "the
wall-clock time this ephemeral H4 evaluation **invocation** was performed" — singular, referring to one
`evaluate(...)` call, not to each individual per-element classification performed within it. Therefore
**exactly one `datetime.now(UTC)` call is made per `evaluate(...)` invocation** (§9 Step 0, before any
element is processed), and its single resulting value is assigned identically to `evaluated_at` on **every**
`InformationElementEvidenceAvailabilityResult` that invocation produces — never a fresh, independently-timed
`datetime.now(UTC)` call per element. This is the direct, unambiguous resolution required when
`evaluated_at` is bound as a per-element field (§11) rather than living on a separate outer batch-result
wrapper the way `SemanticCoverageEvaluationResult.evaluated_at` does one layer up (CDD-023 defines no such
wrapper for H4 — `evaluate(...)` returns a bare tuple, §7) — the shared-invocation-instant semantics CDD-023
§11 states in words must therefore be carried on each element explicitly, identically, rather than
structurally guaranteed by a single outer field the way Gate I's own shape guarantees it for free.

This is invocation metadata only and does not transform the ephemeral result into a persisted business
event (CDD-023 §14, restated). Two separate calls to `evaluate(...)` — even with identical input — MAY
(and, in practice, almost always will) yield different `evaluated_at` values; this is expected and does not
constitute non-determinism (CDD-023 §11's own fields-1-6-only determinism scope, restated in §13 below).

## 11. Tenant-isolation decision (binding, CDD-023 §16)

No new isolation mechanism. `coverage_result.tenant_id` (already tenant-scoped by Gate I's own construction)
is passed unchanged into `FieldValueEvidenceRepositoryImpl.get_by_source_field`'s existing `tenant_id`
parameter, which already raises `ValidationException` explicitly on ownership mismatch (CDD-022 §7, §26).
This authorization adds no `tenant_id` column to `FieldValueEvidence` and no `tenant_id` field to
`InformationElementEvidenceAvailabilityResult` (§6) — confirmed absent from the frozen seven-field contract.

## 12. Ephemeral / no-persistence decision (binding, CDD-023 §14)

No ORM model, no migration, no repository, no `evaluation_id`, no update/delete API, no history/replay
table of any kind is authorized anywhere in this artifact set (§4's Exclusions column, binding, repeated).
`InformationElementEvidenceAvailabilityApplicationService` performs no persistence of its own — it is a
pure, read-only orchestration over one already-in-memory parameter (`coverage_result`) and one real,
already-existing repository call (`evidence_provider.get_by_source_field`), matching every other
ephemeral service in this lineage.

## 13. Acceptance criteria

1. `MAPPED` elements with a persisted evidence row bearing a non-empty `observed_representation` classify
   `EVIDENCE_PRESENT`; zero rows classify `NO_EVIDENCE`; all-empty rows classify `EVIDENCE_EMPTY` — proven
   by unit test and against real PostgreSQL using the H3/CDD-022 demo fixture.
2. Whitespace-only `observed_representation` classifies `EVIDENCE_PRESENT`, never `EVIDENCE_EMPTY`, proven
   by unit test (CDD-023 §8).
3. `UNMAPPED` elements produce no `InformationElementEvidenceAvailabilityResult` at all, proven by unit test
   and against real PostgreSQL (the "Risk Event Severity" H3 fixture element).
4. A wrong-tenant evidence lookup raises `ValidationException` explicitly and never collapses into
   `NO_EVIDENCE`, proven against real PostgreSQL.
5. `field_value_evidence_ids` contains every retrieved row's identity for both `EVIDENCE_EMPTY` and
   `EVIDENCE_PRESENT` (never only non-empty rows), in canonical ascending-lexical order, independent of
   database/retrieval order, `observed_at`, `received_at`, `observed_representation`, or `evidence_reference`
   — proven by unit test with a deliberately evidence-content-shuffled/ID-shuffled fixture.
6. A duplicate `field_value_evidence_id` in a retrieved set (constructed via direct ORM manipulation in a
   Postgres test, mirroring CDD-022's own identity-conflict test precedent) raises `ValidationException`
   explicitly rather than silently deduplicating.
7. `obligation` is preserved exactly (`REQUIRED`/`CONDITIONAL`/`OPTIONAL` all classify identically under
   zero evidence — all three yield `NO_EVIDENCE`), proven by unit test; no `CONDITIONAL`-applicability logic
   exists anywhere in the implementation.
8. `source_field_id` always equals the `SourceField` identity embedded in the same result's
   `semantic_mapping_resolution` — proven structurally (the algorithm has no code path that could produce
   disagreement, since both are derived from the same `element.resolution` in one step) and by unit test.
9. `evaluated_at` is timezone-aware UTC and does not affect classification, evidence-ID membership, or
   evidence-ID ordering, proven by unit test (two evaluations of unchanged input differ only in
   `evaluated_at`).
9a. All `InformationElementEvidenceAvailabilityResult` values returned by a single `evaluate(...)` call
    carry an **identical** `evaluated_at` value, even when that call processes multiple `MAPPED` elements —
    proven by unit test using a `coverage_result` with at least two `MAPPED` elements (§10, binding).
10. Repeated evaluation of unchanged Gate I input and unchanged persisted evidence yields identical values
    for all six non-`evaluated_at` fields, proven against real PostgreSQL.
11. No persisted row, migration, or repository exists anywhere in the implementation — confirmed by
    `test_persistence_integration.py`'s unchanged `table_count == 60`/revision assertions requiring no
    modification.
12. `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` passes with the exact 3-path
    `AUTHORIZED_CHANGED_PATHS` extension in §4, and zero unauthorized diff.
13. `test_domain_foundation.py`'s exhaustive `declared_classes` assertion passes **unmodified** — proving
    the domain-placement firewall (§3, §6) holds in practice, not merely in this document's own claim.
14. No risk/impact/severity/priority/remediation/trust/confidence/staleness/freshness field, state, or
    logic exists anywhere in the implementation, confirmed by import-hygiene and literal-string inspection
    (mirroring `test_domain_foundation.py`'s own forbidden-import-scan precedent, applied manually during
    implementation review since no automated scan targets `application/`).

## 14. Test matrix

**Unit tests** (`test_information_element_evidence_availability.py`, no DB, `EvidenceProvider`-conforming
stub mirroring `test_semantic_coverage_evaluation.py`'s exact style):

1. `MAPPED` + zero evidence rows → `NO_EVIDENCE`, `field_value_evidence_ids == ()`.
2. `MAPPED` + one `""` row → `EVIDENCE_EMPTY`, tuple contains that one ID.
3. `MAPPED` + multiple all-`""` rows → `EVIDENCE_EMPTY`, tuple contains all IDs, canonical order.
4. `MAPPED` + one non-empty row → `EVIDENCE_PRESENT`, tuple contains that one ID.
5. `MAPPED` + one empty + one non-empty row → `EVIDENCE_PRESENT`, tuple contains **both** IDs.
6. Whitespace-only (`" "`) `observed_representation` → `EVIDENCE_PRESENT`.
7. `UNMAPPED` element in `coverage_result` → produces no corresponding result in the returned tuple.
8. `REQUIRED` + zero evidence → `NO_EVIDENCE`.
9. `OPTIONAL` + zero evidence → `NO_EVIDENCE`.
10. `CONDITIONAL` + zero evidence → `NO_EVIDENCE`, and no applicability-evaluation code path exists.
11. `obligation` on the result equals the source element's `obligation` exactly, for all three values.
12. `source_field_id` on the result equals `element.resolution.source_field_id` exactly.
13. Evidence-ID tuple is in ascending lexical canonical-string order regardless of the stub's row-return
    order (stub deliberately returns rows in reverse-ID order to prove the service re-sorts, not merely
    passes through).
14. Ordering is unaffected by `observed_at`, `received_at`, `observed_representation`, or `evidence_reference`
    differences among the stubbed rows (constructed so a naive alternate ordering rule would produce a
    different, wrong result).
15. A stubbed duplicate `field_value_evidence_id` across two returned rows raises `ValidationException`.
16. `evaluated_at` is timezone-aware and UTC.
17. Two evaluations of identical stub input differ, at most, in `evaluated_at`.
18. `evidence_provider.get_by_source_field` raising `ValidationException` (simulated by the stub) propagates
    unchanged out of `evaluate(...)`.
19. Multiple `MAPPED` elements in one `coverage_result` each produce their own independent, correctly
    isolated result (no cross-element evidence leakage).
19a. Multiple `MAPPED` elements in one `coverage_result` produce results that all share the **identical**
    `evaluated_at` value (§10, binding) — the stub asserts the timestamp is not freshly computed per
    element.
20. Import-hygiene assertion: the module imports no `sqlalchemy`, no `app.infrastructure.persistence.*`
    (only the `Protocol` name, never a concrete class), no `Blueprint`/`SemanticMapping`/H2/`GapImpactContext`/
    `SourceObservation`.

**Postgres tests** (`test_information_element_evidence_availability_postgres.py`, real
`SemanticCoverageEvaluationApplicationService` + real `FieldValueEvidenceRepositoryImpl`, H3/CDD-022 demo
fixture via `DemoSemanticMappingSeeder` + `DemoFieldValueEvidenceSeeder`):

21. The real demo fixture ("Supplier Legal Name," `MAPPED`, one `FieldValueEvidence` row
    `"Acme Taiwan Ltd"`) classifies `EVIDENCE_PRESENT` with a one-element, correct evidence-ID tuple.
22. "Risk Event Severity" (`UNMAPPED` in the real fixture) produces no result.
23. A wrong-tenant `coverage_result.tenant_id` (constructed via a second, real, isolated tenant/`SourceField`)
    raises `ValidationException` explicitly, never `NO_EVIDENCE`.
24. Repeated evaluation of the unchanged real fixture yields identical classification and identical
    evidence-ID tuple across two calls.
25. A raw-SQL-inserted second `FieldValueEvidence` row (same `SourceField`, different
    `observed_representation`) is included in the evidence-ID tuple alongside the original, proving the
    full-set (not single-row) provenance rule against real persisted multiplicity.
26. A raw-ORM-manipulated duplicate `field_value_evidence_id` (mirroring CDD-022's own identity-conflict
    Postgres test precedent) raises `ValidationException` when evaluated.
27. No new table, migration, or row is created anywhere in the persisted schema as a side effect of running
    `evaluate(...)` (verified by table-count/row-count assertions before and after).

## 15. Runtime architecture impact

Exactly the 3-path `AUTHORIZED_CHANGED_PATHS` extension in §4's `test_runtime_architecture.py` row.
`test_domain_foundation.py` requires no change (§3, §13's acceptance criterion 13 proves this in practice).
No migration-head or table-count assertion requires change (§3).

## 16. Implementation order (preferred, non-binding sequence)

1. `information_element_evidence_availability.py` — `EvidenceAvailabilityStatus`, `InformationElementEvidenceAvailabilityResult`,
   `EvidenceProvider` Protocol, `InformationElementEvidenceAvailabilityApplicationService`.
2. `test_information_element_evidence_availability.py` — full unit matrix (§14, items 1-20).
3. `test_information_element_evidence_availability_postgres.py` — full Postgres matrix (§14, items 21-27).
4. `test_runtime_architecture.py` — the 3-path `AUTHORIZED_CHANGED_PATHS` extension.
5. Run `test_domain_foundation.py` unmodified and confirm it still passes (acceptance criterion 13) —
   explicit proof, not assumption, that the domain-placement firewall held.
6. Run the complete backend suite, `black`/`isort`/`ruff`/`mypy`.
7. Adversarial diff review against this document's Exclusions columns (§4) and firewall table (§5).

## 17. Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the four artifact paths authorized above (three CREATE, one MODIFY)
without new Product Owner authorization. If implementation discovers that any authorized artifact's
Exclusions column cannot be satisfied without touching an unlisted path — in particular
`test_domain_foundation.py`, any file under `backend/app/domain/*`, `backend/app/infrastructure/persistence/*`,
`backend/app/integration/*`, `backend/app/api/*`, or any Blueprint/H2/Gate-I/Gate-J/Gate-N/Gate-P artifact —
implementation MUST STOP and report the exact blocker rather than silently expanding scope, matching every
prior phase's identical binding precondition.

## 18. Explicit exclusions (binding, restated for emphasis)

No API route, FastAPI router, or schema. No frontend, UI, or authoring surface of any kind. No connector or
production-ingestion behavior. No new `LifecycleState`/`GovernanceStatus` value or workflow. No
`SATISFIED`/`UNSATISFIED`/`VALID`/`INVALID`/`CORRECT`/`INCORRECT`/`COMPLETE`/`INCOMPLETE`/`TRUSTED`/`UNTRUSTED`
output state or field, in any form. No risk/impact/severity/priority/remediation/`RemediationAction` output.
No trust score, confidence value, staleness/freshness classification, or gap overlay. No Ask CTEC
integration, LLM/agent behavior, or natural-language generation. No dependency on, wrapping of, or fallback
to `SourceObservation`. No second Gate I/H2 resolution path. No `latest`/`current`/`best`/`preferred`
evidence selection. No `tenant_id` field on the H4 result or on `FieldValueEvidence`. No `evaluation_id`,
persistence, migration, or repository beyond the reused, unmodified `FieldValueEvidenceRepositoryImpl`.

## 19. P0/P1/P2 findings

**Initial drafting-turn self-review**: P0 = 0, P1 = 0, P2 = 0.

**Independent adversarial re-review (this revision)**: found one genuine P1, not caught by the drafting
turn's own self-review — §9/§10 originally specified `evaluated_at = datetime.now(UTC)` computed inside the
per-element loop, meaning a single `evaluate(...)` call processing multiple `MAPPED` elements could assign
each returned result a *different* timestamp. Frozen CDD-023 §11's own wording ("the time this ephemeral H4
evaluation **invocation** was performed," singular) resolves this directly and unambiguously in favor of one
shared timestamp per `evaluate(...)` call — no new Product Owner architecture decision was required.
Remediated by: relocating `evaluated_at` generation to a single Step 0 before the per-element loop (§9);
adding an explicit, binding cardinality rule to §10; adding acceptance criterion 9a (§13) and unit test item
19a (§14) proving the shared-timestamp behavior explicitly. Also strengthened, as non-blocking clarity
improvements requiring no architecture change: §9's canonical-ordering step now cites CDD-022 §10's own
"canonical string form (`str(uuid_value)`)" convention explicitly, closing any residual doubt about what
"canonical string representation" concretely means; §7 now explicitly justifies the `EvidenceProvider`
`Protocol`-over-repository (rather than Protocol-over-service) design choice, since CDD-022 authorizes no
intermediate `application/`-layer service over `FieldValueEvidence` for H4 to depend on instead.

**Post-remediation classification**: **P0 = 0. P1 = 0. P2 = 0.** Re-verified: the `evaluated_at` fix
introduces no new artifact path, no new field, no new exception type, and no change to any of the three
classification states or the four-file allowlist — it is a pure algorithmic-ordering clarification, exactly
the class of amendment §31 of the governing review turn permits without a fresh Product Owner decision.

## 20. Approval state

This document is an **approved artifact-authorization companion**, published to `APPROVED ARTIFACT
AUTHORIZATION` state following the identical Product Owner review-and-approval cycle every prior companion
in this lineage underwent (CDD-017 G2/G3/G3.5, CDD-018 G4, CDD-019 H1/H2/H3, CDD-020 I1, CDD-021 J1/J2,
CDD-022's own companion) — discovery (§3), a drafting-turn self-review (P0=0/P1=0/P2=0), an independent
adversarial re-review that found and remediated one P1 concerning `evaluated_at` cardinality (§19), and
final Product Owner approval. Approval of this record governs exactly the artifact sandbox in §4 above; it
does **not** itself authorize implementation of any artifact listed there — a separate, subsequent Product
Owner implementation authorization remains required before any file listed above is created or modified,
matching every prior phase's identical binding precondition (CDD-023 §29, §33, restated). Parent CDD-023
remains FROZEN and PUBLISHED, unchanged by this approval.
