# CDD-015 — Optional Client Scopes Regression Assertion Defect Authorization

Version: 1.0
Status: APPROVED FOR DEFECT IMPLEMENTATION
Precedent: `CDD-028-Governed-Visual-Ontology-Modeling-Keycloak-Scope-Defect-Authorization.md`,
`CDD-029-Information-Element-Context-Keycloak-Scope-Defect-Authorization.md`

## Purpose

This post-freeze authorization permits the minimum correction needed to bring one Gate F regression
test's assertion back into alignment with what CDD-015 actually requires. It does not alter Gate F's
semantics, authority, API behavior, or Keycloak scope requirements, and it does not alter
`keycloak/ctec-realm.json` in any way. It authorizes a test-only correction, nothing else.

## Root-cause record (binding, factual)

`backend/app/tests/test_gate_f_api_security.py::test_keycloak_unrelated_scope_assignments_unchanged`,
introduced in commit `e6dcec7` ("Gate F F-I3: expose authenticated supply-chain impact API"), asserts:

    assert set(client["optionalClientScopes"]) == {
        "supplier-risk:submit", "supplier-risk:retry", "supplier-risk:replay", "entity-resolution:decide",
    }

CDD-015 §34's own "Authorized Configuration Artifacts" table states, for the Keycloak realm change that
introduced Gate F's own scopes: "No change to any existing scope block (`supplier-risk:*`,
`entity-resolution:*`, `ontology-copilot:ask`). No grant of `entity-resolution:decide` to the demo
persona." This is the entirety of what CDD-015 requires of `optionalClientScopes` — that Gate F's own
implementation not alter existing entries or grant `entity-resolution:decide` to the demo persona. It
does not require, anywhere, that this shared array's total membership remain frozen forever against
all future, separately-governed additions.

The test's exact-equality assertion was a correct, narrowly-scoped regression guard for Gate F's own
implementation commit at the time it was written — proving that commit's own diff didn't disturb
unrelated configuration. Carrying that assertion forward as a permanent invariant is broader than
CDD-015 itself ever required, and it incorrectly rejects any later, separately-governed capability's
legitimate addition to the same shared array — as first observed when GAP-11's own frozen, approved
Keycloak Scope Defect Authorization (`CDD-028-...`) correctly added three new optional scopes and this
test failed as a result, despite GAP-11's own implementation being fully correct and fully authorized.

## Product impact (binding, factual)

None to Gate F's own runtime, API, or authorization behavior — this defect exists entirely within test
code. Its only effect is to incorrectly reject any future, unrelated, correctly-governed addition to
`ctec-frontend.optionalClientScopes`, as a false-positive regression failure.

## Narrow supersession (binding — exact scope, nothing else)

CDD-015 remains the sole semantic authority for Gate F. This document does not supersede, reopen, or
reinterpret any CDD-015 decision. It narrowly authorizes bringing one regression test's assertion back
into alignment with CDD-015's own actual, narrower requirement — it does not authorize any change to
what that requirement is.

## Exact changed-path authorization

| Path | Operation | Governing authority | Purpose | Prohibited changes | Required validation |
|---|---|---|---|---|---|
| `backend/app/tests/test_gate_f_api_security.py` | MODIFY | This authorization | Replace `test_keycloak_unrelated_scope_assignments_unchanged`'s exact-equality assertion on `optionalClientScopes` with a subset assertion proving the same four historically-relevant scopes remain present, while preserving the existing `entity-resolution:decide not in defaultClientScopes` assertion verbatim. | No modification to any other test in this file; no modification to any other file; no weakened, skipped, or deleted assertion; no special-casing of `ontology-modeling` or any other specific future scope name. | Full targeted execution of this file; full backend suite; `docker compose config --quiet`. |

```
AUTHORIZED_NEW    = 0
AUTHORIZED_CHANGE = 1
TOTAL IMPLEMENTATION SURFACE = 1
```

No second implementation file is authorized. In particular, **not authorized**: any change to
`keycloak/ctec-realm.json`; any `backend/app/api/*` file; any frontend file; either GAP-11
implementation file (`keycloak/ctec-realm.json`, `test_ontology_modeling_router.py` — GAP-11's own,
separately-governed surface); CDD-015; the Gate F implementation authority embedded in CDD-015 §34; the
GAP-11 Defect Authorization; any other frozen governance artifact.

## Assertion-strength requirement (binding)

The corrected assertion must continue to fail if: `supplier-risk:submit`, `supplier-risk:retry`, or
`supplier-risk:replay` disappears from `optionalClientScopes`; `entity-resolution:decide` disappears
from `optionalClientScopes`; or `entity-resolution:decide` appears in `defaultClientScopes`. The only
claim removed is "no additional legitimately-governed optional scope may ever exist" — a claim CDD-015
never established. This is a correction to match the governing contract, not a weakening of Gate F's
own enforced properties.

## Genericity requirement (binding)

The corrected test must not reference `ontology-modeling`, Gate M, GAP-11, or any other specific
future capability by name. It must express Gate F's own invariant in a form that remains correct
regardless of what else is later, separately, and legitimately added to the same shared array.

## Test-integrity firewall (binding)

The future correction must not: delete, skip, or `xfail` the test; rename it to evade execution;
weaken or alter any other assertion in this file or any sibling Gate F test; change any production
code, Keycloak configuration, or authorization behavior; or introduce a broad "anything passes"
condition.

## GAP-11 firewall (restated)

GAP-11's own implementation surface (`keycloak/ctec-realm.json`, `test_ontology_modeling_router.py`)
remains exactly as authorized by its own Defect Authorization and is not touched, widened, or
otherwise affected by this document. Once this correction is independently merged, GAP-11 R5 may
resume from its own preserved implementation and must independently rerun its own complete validation
suite — success here does not imply success there.

## Cross-gate firewall

This document does not touch or authorize: GAP-8; Gate R; Gate S; Gate V; Gate W; generalized Data
Quality; Simulation execution; MCP execution; any Gate F↔H-U composition; POST-U/X-DEBT-6 (remains
RESOLVED/CLOSED); CDD-034 behavior; Evidence Fitness frontend exposure; GAP-11 itself.

## Validation / acceptance contract

Before this future implementation may be accepted: (1) exact 1-file diff, CREATE=0/MODIFY=1/DELETE=0;
(2) the corrected assertion still fails under each of the four negative scenarios in the
Assertion-strength requirement above; (3) the corrected assertion makes no reference to any specific
future scope name; (4) `test_keycloak_demo_persona_has_both_gate_f_scopes` and every other existing
test in this file remain unmodified and passing; (5) `test_runtime_architecture.py` passes unmodified;
(6) full backend suite passes; (7) frontend regression suite (format/lint/typecheck/tests/build)
passes unmodified; (8) `docker compose config --quiet` passes; (9) `scripts/verify_architecture_release.py`
passes; (10) CDD-015 and every other tracked frozen governance document remain byte-identical; (11)
exact-head CI passes before merge; (12) post-merge CI passes; (13) post-merge re-execution of the
corrected test and its four negative scenarios is independently reverified.

## Publication / implementation boundary

**Publication/freeze of this document does NOT itself authorize implementation.** A separate,
subsequent Product Owner implementation authorization is required before `test_gate_f_api_security.py`
may be modified — matching every prior gate's identical multi-step discipline in this lineage.

## Authorization

This Defect Authorization is approved for publication, reached via POST-X-TEST-DEBT-1 R0 (discovery) →
R1 (drafting, Product Owner approval) → this R2 publication turn. CDD-015 remains FROZEN and PUBLISHED,
unchanged by this approval.
