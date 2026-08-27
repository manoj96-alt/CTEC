# CDD-036 — Migration-Head Regression Assertion Defect Authorization

Version: 1.0
Status: APPROVED FOR DEFECT IMPLEMENTATION
Precedent: `CDD-015-Optional-Client-Scopes-Regression-Assertion-Defect-Authorization.md`

## Purpose

This post-freeze authorization permits the minimum correction needed to bring four pre-existing
regression tests' hardcoded repository-schema expectations back into alignment with the repository state
that necessarily results from the already-frozen Gate S migration `0018_gate_s_approval`. It does not
alter CDD-036's semantics, Gate S's architecture, the consequential capability's scope, or any Gate S
implementation file. It authorizes exact, literal, test-only corrections, nothing else.

## Root-cause record (binding, factual)

Four pre-existing tests, none of them Gate-S-specific in domain (Decision Engine, Governance Engine,
Knowledge Engine, and generic Persistence Integration), each assert the current Alembic migration head
as a literal string:

```
backend/app/tests/test_decision_engine.py:307        assert revision == "0017_ontology_change_proposal"
backend/app/tests/test_governance_engine.py:388       assert revision == "0017_ontology_change_proposal"
backend/app/tests/test_knowledge_engine.py:305        assert revision == "0017_ontology_change_proposal"
backend/app/tests/test_persistence_integration.py:27  assert revision == "0017_ontology_change_proposal"
```

`test_persistence_integration.py` additionally asserts the total number of schema tables:

```
backend/app/tests/test_persistence_integration.py:28  assert table_count == 61
```

Gate S's Artifact Authorization (§4) authorizes exactly one new migration, `0018_gate_s_approval`
(`down_revision = "0017_ontology_change_proposal"`), which mechanically becomes the new repository
migration head the instant it is applied, and which creates exactly two new tables —
`gate_s_approval_requests` and `gate_s_governed_notes` — per CDD-036 §19. Neither the Gate S Artifact
Authorization nor CDD-036 itself authorized modifying these four pre-existing files, because their
existence and content were not part of Gate S's discovery; the conflict was discovered mechanically
during S2 implementation reconciliation, by running the full backend regression suite against the
restored Gate S candidate implementation.

Mechanically verified during S2/this remediation:
- `revision == "0017_ontology_change_proposal"` is true before Gate S's migration is applied, and
  becomes `"0018_gate_s_approval"` once it is (verified via direct `alembic upgrade head` + SQL query
  against a live database, both before and after applying `0018_gate_s_approval`).
- `table_count` is exactly `61` before Gate S's migration, and exactly `63` after (verified via direct
  SQL query against `information_schema.tables`, both before and after) — precisely `+2`, exactly the
  two tables CDD-036 §19 authorizes.
- No other expectation in `test_persistence_integration.py` (its `test_repository_crud`,
  `test_unit_of_work_rolls_back_on_error`, and `test_database_configuration_requires_url` functions) is
  affected by Gate S's migration.
- `test_decision_engine.py`'s and `test_knowledge_engine.py`'s secondary assertions
  (`trigger_count == 1`, scoped to a specific named trigger — `decision_evaluation_records_immutable`
  and `knowledge_evaluation_records_immutable` respectively) and `test_governance_engine.py`'s secondary
  assertion (`trigger_count == 1`, scoped to `governance_evaluation_records_immutable`) are each scoped
  to one specific, unrelated, already-existing trigger name — Gate S's migration creates no trigger of
  any kind, so none of these three secondary assertions is affected.
- No fifth file was found to be mechanically affected (confirmed via `grep -rn
  "0017_ontology_change_proposal" backend/app/tests/*.py`, which returns exactly these four matches).
- No production or runtime code change is required to resolve any of these four failures — the fix in
  every case is a literal-value correction to a test's own hardcoded expectation.

This is analogous in kind to the precedent `CDD-015-Optional-Client-Scopes-Regression-Assertion-Defect-Authorization.md`:
a correctly-written regression assertion, accurate at the time its own capability was implemented,
becomes stale the moment a later, separately-governed, fully authorized capability legitimately changes
the shared repository state the assertion hardcoded.

## Product impact (binding, factual)

None to any runtime behavior, API contract, authorization decision, or Gate S capability — this defect
exists entirely within four pre-existing tests' hardcoded expectations. Its only effect, until corrected,
is to cause those four tests to fail the moment Gate S's already-frozen, already-authorized migration is
applied — a false-positive regression failure, not a sign of any actual defect in Gate S, Gate M, the
Decision Engine, the Governance Engine, the Knowledge Engine, or general persistence.

## Narrow supersession (binding — exact scope, nothing else)

CDD-036 remains the sole semantic authority for Gate S. This document does not supersede, reopen, or
reinterpret any CDD-036 decision, and does not modify the Gate S Artifact Authorization's own text. It
narrowly authorizes bringing four pre-existing tests' literal expectations back into alignment with the
exact repository state CDD-036's own already-frozen migration produces — it does not authorize any
change to what CDD-036 requires, and it does not establish a standing or generalized authorization for
any future migration. A future migration that stales these or other hardcoded expectations again
requires its own, separate remediation authorization.

## Exact changed-path authorization

| Path | Operation | Governing authority | Purpose | Prohibited changes |
|---|---|---|---|---|
| `backend/app/tests/test_decision_engine.py` | MODIFY | This authorization | Update the migration-head expectation only: `"0017_ontology_change_proposal"` → `"0018_gate_s_approval"`. | No change to `trigger_count == 1` or any other assertion; no change to any other test in this file. |
| `backend/app/tests/test_governance_engine.py` | MODIFY | This authorization | Update the migration-head expectation only: `"0017_ontology_change_proposal"` → `"0018_gate_s_approval"`. | No change to `trigger_count == 1` or any other assertion; no change to any other test in this file. |
| `backend/app/tests/test_knowledge_engine.py` | MODIFY | This authorization | Update the migration-head expectation only: `"0017_ontology_change_proposal"` → `"0018_gate_s_approval"`. | No change to `trigger_count == 1` or any other assertion; no change to any other test in this file. |
| `backend/app/tests/test_persistence_integration.py` | MODIFY | This authorization | Update exactly two expectations: the migration-head expectation, `"0017_ontology_change_proposal"` → `"0018_gate_s_approval"`; and the total schema table-count expectation, `61` → `63`. | No change to `test_repository_crud`, `test_unit_of_work_rolls_back_on_error`, `test_database_configuration_requires_url`, or any other assertion in `test_connection_and_migration` beyond the two named above. |

```
AUTHORIZED_NEW    = 0
AUTHORIZED_CHANGE = 4
TOTAL IMPLEMENTATION SURFACE = 4
```

No fifth path is authorized. In particular, **not authorized**: any change to any Gate S implementation
file (the 16 paths in the Gate S Artifact Authorization); any change to `keycloak/ctec-realm.json`; any
change to CDD-036 or its Artifact Authorization; any change to any Gate R, Gate Q, Gate M, or other
frozen governance document; any change to any migration file, including `0018_gate_s_approval.py`
itself; any change to `backend/app/tests/test_runtime_architecture.py`.

## Assertion-strength requirement (binding)

Each corrected assertion must continue to fail under every condition it already correctly detected: an
unexpected migration head (any value other than `"0018_gate_s_approval"`), and, for
`test_persistence_integration.py`, any schema-table-count value other than exactly `63`. The only claim
updated is the specific literal value each assertion checks against — matching the new, mechanically
correct, already-authorized repository state — not the kind of property each test enforces.

## Non-generalization requirement (binding — intentional, explicit)

Unlike this document's own precedent (`CDD-015-...-Defect-Authorization.md`, which generalized its
corrected assertion into a form robust against all future, unrelated additions), this remediation
deliberately does **not** generalize any of the four corrected assertions into a dynamic or
migration-agnostic form (for example, reading the actual current Alembic head programmatically instead
of a literal string). The Product Owner explicitly declined to authorize a standing or generalized
future-migration mechanism in this remediation. Each corrected assertion remains a literal-value check,
exactly as before, updated only to the exact values Gate S's `0018_gate_s_approval` migration produces.
A future migration that stales these values again will require its own, separate remediation
authorization; this document does not pre-authorize or streamline that future work.

## Test-integrity firewall (binding)

The future correction must not: delete, skip, or `xfail` any of the four tests; rename any of them to
evade execution; weaken, broaden, or alter any other assertion in any of the four files; change any
production or runtime code; or introduce any generalized/parameterized migration-head mechanism (see
Non-generalization requirement above).

## Gate S firewall (restated)

Gate S's own 16-file implementation surface (per the Gate S Artifact Authorization) is not touched,
widened, or otherwise affected by this document. The preserved Gate S candidate implementation (Git
stash `gate-s-implementation-pending-s2`, commit `a5949881995e240a1ab937bf098a84d0835f6e3a`) remains
exactly as it was reconciled during S2 and is not modified by this remediation. Once this remediation is
independently merged, Gate S S2 may resume from its own preserved implementation, restore it against the
new authoritative main, and independently rerun its own complete validation suite — success here does
not imply success there.

## Cross-gate firewall

This document does not touch or authorize: Gate R; Gate Q; Gate V; Gate W; any frontend file; MCP
execution; the six-stage cognitive runtime; generalized Data Quality; Simulation execution; any other
gate's governance or implementation surface.

## Validation / acceptance contract

Before this future implementation may be accepted: (1) exact 4-file diff, CREATE=0/MODIFY=4/DELETE=0;
(2) each corrected assertion still fails under the Assertion-strength requirement's negative scenarios;
(3) no assertion beyond the ones named in the Exact changed-path authorization table is altered in any
of the four files; (4) `test_gate_s_approval_service.py`, `test_gate_s_approval_router.py`,
`test_gate_s_approval_postgres.py`, and `test_runtime_architecture.py` (Gate S's own authorized test
surface) remain unmodified by this remediation and pass unchanged; (5) full backend suite passes with
migration `0018_gate_s_approval` applied; (6) `docker compose config --quiet` passes; (7) CDD-036, the
Gate S Artifact Authorization, and every other tracked frozen governance document remain byte-identical;
(8) exact-head CI passes before merge; (9) post-merge CI passes.

## Publication / implementation boundary

**Publication/freeze of this document does NOT itself authorize implementation.** A separate, subsequent
Product Owner implementation authorization is required before any of the four named files may be
modified — matching every prior gate's identical multi-step discipline in this lineage, and matching
this document's own precedent.

## Authorization

This Defect Authorization is approved for publication, reached via Gate S S2 (mechanical discovery of
the migration-head regression during implementation reconciliation) → Product Owner decision (narrow
authorization, then amended to include the `table_count` expectation upon a second mechanical finding) →
this publication turn. CDD-036 and the Gate S Artifact Authorization remain FROZEN and PUBLISHED,
unchanged by this document.
