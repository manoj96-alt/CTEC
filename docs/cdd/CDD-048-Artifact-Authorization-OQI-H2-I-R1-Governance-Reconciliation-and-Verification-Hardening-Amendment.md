# CDD-048 — Artifact Authorization OQI-H2-I-R1 Governance Reconciliation and Verification Hardening Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` (OQI-H1-I-R1
— the direct precedent for retroactively authorizing a fixed set of necessary paths discovered during
implementation, disclosed rather than concealed); `CDD-047-Artifact-Authorization-CI-Migration-Head-
Closure-Amendment.md` (OQI-H1-CI — the direct precedent for the CI table-count correction specifically,
including the same explicit CI exclusion from the original authorization this amendment now closes).
Classification: GOVERNANCE RECONCILIATION + VERIFICATION HARDENING (retroactive path authorization for
already-necessary, already-disclosed implementation paths; one new, narrow security/provenance
correction; one mechanical table-count correction; one CI path authorization; expanded test-matrix
authorization. No architectural or semantic change to CDD-048.)

## 1. Purpose

OQI-H2-I produced a real, working, regression-tested implementation of the frozen CDD-048 architecture,
committed transparently at `d0e113dd0d06e03b6e87276773e45e32e1d2afe4` with full disclosure in its own
commit message of every path touched beyond the original 30-path Artifact Authorization. OQI-H2-I's own
final report correctly refused to claim H2-VM readiness, disclosing: (a) 17 paths written before formal
amendment; (b) a table-count estimate (108) that undercounted the actual schema delta (109); (c) a
provenance defect in `HUMAN_VERIFIED_EVIDENCE` (`verifying_actor_id` accepted from the request body,
never bound to the authenticated caller); (d) an incomplete test matrix; (e) no Docker/compose runtime
verification. This amendment formally reconciles (a)-(b), authorizes the exact narrow correction for
(c), and authorizes the exact narrow additional paths needed to close (d). Docker verification (e) is
performed under this same phase using only already-authorized paths (no source changes required for
verification itself).

This amendment does not reopen, reinterpret, or redesign any part of CDD-048's frozen semantics.

## 2. Context

Independently re-derived (not trusted from the H2-I report) via `git diff --name-status`, `git diff
--stat`, and `git show --stat --oneline`, all three cross-checked and in agreement:
`01958f8276483980966f7e19ace3c2b0f8ae7fcd..d0e113dd0d06e03b6e87276773e45e32e1d2afe4` touches exactly 39
paths (39 files changed, 4133 insertions(+), 45 deletions(-)). Set-differenced programmatically against
every exact path literal named in the original Artifact Authorization (30 paths, CREATE=19/MODIFY=11,
recount confirmed): 22 of the 39 are within the original 30; 17 are not; 8 of the original 30 were never
written at all (7 planned test files consolidated into one crown file, plus
`oqi_remediation_agent_service.py`, determined during implementation not to require any change for H2 to
function correctly — CDD-048's own MODIFY row 6 for that file was worded "only if this file's own copy
requires updating," and it did not).

## 3. Exhaustive fresh discovery — the 17 extra paths

Each of the 17 was independently re-inspected via `git diff --stat` for this amendment (not accepted on
the prior report's word). Every one is a small, purely additive diff (at most one deletion per file,
each such deletion being a list-membership addition, e.g. inserting a new entry into an existing
enumeration — never a removal of existing functionality):

| # | Path | Diff size | Purpose |
|---|---|---|---|
| 1 | `backend/app/application/oqi_business_rule_evaluation_service.py` | +13/-0 | Passes the new `violation_type` kwarg to `apply_business_rule_finding_transition` at its one existing call site, keyed off `rule.dimension` — required for CDD-048 §14/§20's frozen `CONTEXTUAL_PLAUSIBILITY_VIOLATION` semantics to actually reach a persisted Finding. |
| 2 | `backend/app/infrastructure/persistence/models/oqi_business_rule_finding.py` | +13/-1 | Adds the `violation_type` column CDD-048 §14/§20 itself specifies (finding-type-equivalent for `dimension=REASONABLENESS`). |
| 3 | `backend/app/infrastructure/persistence/models/oqi_business_rule.py` | +19/-1 | Adds the `dimension` column CDD-048 §14 itself specifies ("A BusinessRule must have an explicit governed purpose/dimension" — frozen, not discretionary). |
| 4 | `backend/app/infrastructure/persistence/oqi_business_rule_evaluation_repository.py` | +35/-1 | Threads `violation_type` through ORM↔domain conversion (required for #1/#2 to round-trip); adds the REASONABLENESS branch of `has_qualifying_coverage_for_dimension`, mirroring the ACCURACY branch already authorized on `oqi_quality_coverage_policy_repository.py` — CDD-048 §23 requires both dimensions' coverage to be real, not synthesized. |
| 5 | `backend/app/infrastructure/persistence/oqi_business_rule_repository.py` | +3/-0 | Threads `dimension` through ORM↔domain conversion (required for #3 to round-trip). |
| 6 | `backend/app/infrastructure/persistence/oqi_remediation_repository.py` | +82/-0 | Adds `get_accuracy_candidate_support`, a narrow, additive, read-only method (explicitly not on the `OqiRemediationRepository` Protocol, mirroring the established `has_qualifying_coverage_for_dimension` precedent) — required for CDD-048 §24's frozen requirement that Accuracy candidates be evidence-backed, not fabricated. |
| 7 | `backend/app/tests/test_oqi_business_impact.py` | table-count only | Mechanical: current-head table-count literal, stale the moment 0028-0030 exist. |
| 8 | `backend/app/tests/test_oqi_business_rule_postgres.py` | table-count + column-set | Mechanical table-count, plus the `business_rules` exhaustive-column-set assertion, stale the moment `dimension` (item #3) exists. |
| 9 | `backend/app/tests/test_oqi_ontology_impact_postgres.py` | table-count only | Mechanical. |
| 10 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | behavioral | `QualityDimension` grew 3→4 members — CDD-048 §7/§14's own frozen, direct consequence; the test asserting "exactly 3, unmodified" is describing pre-H2 CDD-047 behavior H2 was explicitly authorized to change. |
| 11 | `backend/app/tests/test_oqi_quality_coverage_policy_postgres.py` | table-count + structural | Mechanical table-count, plus a genuine structural fix: the test's own migration round-trip downgraded to a hardcoded distant revision (`0026_oqi6_reliance`) instead of bracketing to its own boundary (`0027_h1_coverage_policy`) first — the exact "Classification D" defect class `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` already fixed once for other tests, now recurring here because H2 extended head beyond H1 for the first time. Left unfixed, this stranded the shared session-scoped test database below head for every subsequent test in the same pytest session. |
| 12 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | behavioral | ACCURACY/REASONABLENESS coverage dispatch is no longer unconditionally `False` — CDD-048 §23's own frozen, direct consequence; the test asserting the pre-H2 "unsupported dimension" behavior for these two specific dimensions was describing exactly what H2 was authorized to change, and two new tests were added proving the *correct* new dispatch (mirroring the existing `test_completeness_and_validity_dispatch_to_oqi1`/`test_consistency_dispatches_to_oqi2` precedent). |
| 13 | `backend/app/tests/test_oqi_remediation_agent_i2.py` | table-count only | Mechanical. |
| 14 | `backend/app/tests/test_oqi_remediation_i1.py` | table-count only | Mechanical. |
| 15 | `backend/app/tests/test_persistence_integration.py` | table-count only | Mechanical. |
| 16 | `backend/app/tests/test_runtime_architecture.py` | firewall exception | `QualityEvaluationORM`/`QualityEvaluationEvidenceORM`/`QualityFindingORM` now have a second legitimate construction site (`oqi_accuracy_evaluation_repository.py`, CDD-048 §7's own explicit design — Accuracy is deliberately OQI1-storage-shaped) — the firewall test's single-site assertion is relaxed to name exactly these two authorized sites, not "any file." The `AUTHORIZED_CHANGED_PATHS` allowlist in this same file was **not** touched (see §6 below — that remaining failure is addressed separately in this amendment, not silently patched inside this file). |
| 17 | `keycloak/ctec-realm.json` | scope entries only | **Already pre-authorized by the original frozen document's own text** (§4, "Unauthorized paths": *"`keycloak/ctec-realm.json` MAY be modified, narrowly, for exactly those two entries plus their `optionalClientScopes` references... implicitly authorized alongside row 10"*) — re-verified here: the actual diff touches only the two `clientScope` objects and their two `optionalClientScopes` references, nothing else. This is the one item of the 17 that requires no retroactive authorization at all. |

**Historical disclosure, stated explicitly and without euphemism**: items 1–16 above were written during
OQI-H2-I, *before* this amendment's publication and *before* any formal authorization for them existed
beyond CDD-048's own general framing. This is the same sequence CDD-047's own governance history followed
twice (OQI-H1-I-R1, OQI-H1-CI) — a gap is discovered during implementation or regression, and a narrow,
disclosed, retroactive amendment is published rather than either (a) silently treating the gap as already
covered, or (b) reverting genuinely necessary work to preserve an illusion of clean sequencing. Item 17
alone was genuinely pre-authorized before it was written.

## 4. Disposition of every extra path

All 17 are **RETAIN**. None is reverted. Justification, per item, is the "Purpose" column of §3 above;
in every case the change is either (a) a direct, unavoidable consequence of a semantic fact CDD-048
itself already froze (the `dimension`/`violation_type` columns, the `QualityDimension` member count, the
ACCURACY/REASONABLENESS coverage dispatch), (b) a narrow, additive, read-only capability with no existing
call site depending on its absence (item 6, mirroring an already-accepted precedent), (c) a mechanical
table-count correction of the exact kind this repository's own established process requires after any
migration lands, or (d) a genuine structural test-isolation bug fix following an already-established
fix pattern. No item was found, on inspection, to be discretionary, opportunistic, or avoidable.

## 5. Table-count correction — 108 → 109

**Root cause, independently proven, not assumed:**

```
0027_h1_coverage_policy: 102 tables (confirmed, unchanged, real PostgreSQL)

0028_oqi_h2_reference_evidence — op.create_table() call sites (verified by grep, not estimated):
    oqi_reference_evidence_assertions
    oqi_governed_reference_dataset_entries
    oqi_human_verified_evidence_entries
    oqi_business_rule_derived_reference_entries
    oqi_reference_evidence_conflicts
    oqi_reference_evidence_conflict_members
  = 6 new tables

0029_oqi_h2_accuracy_dimension — op.create_table() call sites:
    oqi_quality_evaluation_reference_evidence
  = 1 new table

0030_oqi_h2_reasonableness — op.add_column() only, zero op.create_table() call sites
  = 0 new tables

Total new tables: 6 + 1 + 0 = 7
102 + 7 = 109  (confirmed against real PostgreSQL: SELECT count(*) ... = 109)
```

CDD-048 §28's original estimate of "108" underscored the reference-evidence-conflict subsystem by one
table — the conflict-membership normalization child (`oqi_reference_evidence_conflict_members`) was
omitted from the original count, an estimation error in the frozen document, not a later architecture
change. **Architecture, semantic scope, and migration design are unchanged** — this is a pure arithmetic
correction to a document that itself explicitly deferred exact schema-shape counting to implementation
(CDD-048 §11 already stated the exact table names; only the *sum* was miscounted).

This correction is **not** license for any further schema expansion — it corrects one already-fixed,
already-implemented number, nothing else.

## 6. CI / migration regression paths

Exhaustive `grep -rn` across the repository for `102`, `108`, `109`, `0027_h1_coverage_policy`, and every
migration-head/table-count-shaped literal, cross-referenced against the 17-path inventory above, finds
exactly one remaining stale, unauthorized-to-touch location: `.github/workflows/ci.yml` lines 148-153
(`[ "$count" -eq 102 ]`). This file was explicitly, deliberately excluded from OQI-H2-I's own authorized
scope (its predecessor, `CDD-047-...-CI-Migration-Head-Closure-Amendment.md`, establishes this exact
exclusion-then-separate-amendment pattern as the governing precedent). The migration-head check
immediately above it (`.github/workflows/ci.yml` lines 139-146) already resolves dynamically via
`alembic heads` and requires **no change** — reconfirmed by inspection, this amendment does not touch it.

**Authorized correction**: `.github/workflows/ci.yml`, exactly one line (153), from `[ "$count" -eq 102 ]`
to `[ "$count" -eq 109 ]` (and its accompanying message text). No weakening of any kind: the check remains
a strict equality, never `>=`, never `|| true`, never `continue-on-error`.

## 7. Exact R1 authorized path set (new, beyond the 17 retroactively authorized above)

```
CREATE = 1
MODIFY = 3
DELETE = 0
```

| # | Path | Purpose |
|---|---|---|
| 1 (CREATE) | `backend/app/tests/test_oqi_h2_authorization_and_tenant_isolation.py` | Router-level authorization-separation adversarial tests (§8 A-G) via FastAPI `TestClient` + dependency overrides, mirroring `test_oqi_api_router.py`'s established pattern; real-PostgreSQL tenant-isolation adversarial tests for Reference Evidence/conflicts/Accuracy (§15). |
| 2 (MODIFY) | `.github/workflows/ci.yml` | Exactly the one-line table-count correction in §6, narrowly. |
| 3 (MODIFY) | `backend/app/api/oqi/router.py` | Bind `verifying_actor_id` (and, for consistency within the same provenance-trust class, `created_by` on both reference-evidence routes) to `authenticated.principal_id` — never from the request body. Already an authorized/touched file from the original 30-path set; this is a further, narrow, additive change within R1's own explicit mandate (§7 of the governing prompt), not a new path. |
| 4 (MODIFY) | `backend/app/api/oqi/schemas.py` | Remove `verifying_actor_id`/`created_by` fields from the two request schemas entirely (per the governing prompt's explicit preference: "prefer removing caller control... entirely from the external API contract"). Already an authorized/touched file; further narrow change within R1's mandate. |

`backend/app/tests/test_oqi_h2_accuracy_reasonableness_crown.py` (already CREATE-authorized in the
original document) is substantially extended in place to close the remaining frozen test-matrix
obligations (§9-§18 of the governing prompt) — this requires no new path authorization, since the file
itself was already fully authorized for creation and its content was never frozen to a fixed set of
functions.

`backend/app/application/oqi_reference_evidence_service.py` (already authorized) keeps its existing
`verifying_actor_id`/`created_by` parameters unchanged at the service-layer boundary — the governing
prompt's own guidance ("if internal service interfaces require actor_id, the API/application boundary
must populate it") is followed exactly: the fix is at the router boundary only, so this file requires
no further change for the provenance fix (it may still gain call-site updates purely to reflect the
router no longer forwarding an untrusted value, verified narrow in §21 execution).

## 8. Human-verified-evidence actor-provenance correction — frozen requirement

`RecordHumanVerifiedEvidenceRequest`/`AssertGovernedReferenceDatasetRequest` (`api/oqi/schemas.py`) lose
their `verifying_actor_id`/`created_by` fields entirely. `router.py`'s
`record_human_verified_evidence`/`assert_governed_reference_dataset` routes populate both exclusively
from `authenticated.principal_id` (the cryptographically-verified JWT subject, per
`TrustedPrincipal.principal_id` — never a request-body field, query parameter, or arbitrary header).
`OqiReferenceEvidenceService`'s own method signatures are unchanged (internal boundary, trusted caller
already assumed). Binding normative requirement: `persisted verifying actor == authenticated principal
identity`, structurally, not by convention — an authenticated Bob can never cause "Alice" to be persisted
as the verifying actor, because no code path ever reads an actor identity from anywhere other than
`authenticated.principal_id`.

## 9. Complete frozen test-matrix requirement

CDD-048 §31's full matrix (A1-A13, R1-R10, F1-F10, RC1-RC5, CY1-CY6, C1-C11) must be behaviorally proven,
not re-scoped. Consolidation into fewer test functions via parametrization is acceptable; omission of
semantic coverage is not. This amendment authorizes exactly the one new test file (§7) plus substantial
extension of the already-authorized crown file to satisfy this in full.

## 10. Docker/runtime completion requirement

Full Docker build (backend + frontend) and fresh compose-stack runtime verification (§25-§30 of the
governing prompt) is required before any claim of H2-VM readiness. This requires no new source path —
verification only.

## 11. No architecture change

Nothing in this amendment adds, removes, or reinterprets any CDD-048 dimension, Finding type, Reference
Evidence form, crown invariant, or downstream-integration decision. Every correction here is either
mechanical (table count, CI literal), retroactive-authorization-of-already-necessary-work, a narrow
security/provenance hardening explicitly requested by governance, or test-completion.

## 12. No scope expansion into later dimensions

Uniqueness, Timeliness, Integrity, Conformity remain untouched and unauthorized, exactly as CDD-048 froze.

## 13. STOP conditions for this amendment's own execution

If, during R1 implementation: (a) any additional path beyond §7 is discovered necessary — STOP, publish a
further narrow amendment, do not improvise; (b) the actor-provenance fix cannot be achieved without
touching a file outside §7 — STOP, extend this amendment first; (c) any CY1-CY6 adversarial construction
is found to actually succeed (i.e., a real circularity is possible) — STOP, this is an implementation
defect requiring its own fix authorization, not silently patched; (d) Docker verification reveals a
material defect — STOP before any completion claim.

## 14. Governance byte-integrity

CDD-048 main and Artifact Authorization remain byte-identical to their frozen hashes (re-verified
immediately before this amendment's publication):
```
f3739f0f8590f351770c3fd4356242296308a51743432c3af2fc8ac317e92533  CDD-048 main
1574932dadf1afe16cf82e7a9e7432fa86464f959b99e53f738f0b532410a471  CDD-048 Artifact Authorization
```
Neither is modified by this amendment.

## 15. Governance precedent followed

`CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` and
`CDD-047-Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md`, both cited above, establish the
exact pattern this amendment follows: standalone companion document, never an in-place rewrite of an
already-approved authorization; explicit classification of every correction as mechanical vs. structural
vs. new-capability; explicit disclosure of what preceded formal authorization; explicit non-expansion of
architecture.

## 16. P0/P1/P2/P3 (before this amendment)

P0 = 0. P1 = 1 (`verifying_actor_id` provenance defect, addressed by §8). P2 = several (incomplete test
matrix, no Docker verification — addressed by §9-§10). P3 = 0.

## 17. Authorization

This amendment is approved for publication as the governance basis for OQI-H2-I-R1. Implementation
against §7-§10 is authorized only after this document's own publication and hash computation — never
before, and this document's own §3 discloses precisely where that ordering was necessarily reversed for
the original 16 retroactively-authorized paths (a gap discovered during implementation, exactly as
CDD-047's own precedent), with item 17 the sole exception genuinely pre-authorized in advance.
