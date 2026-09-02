# CDD-049 — Artifact Authorization H3-I-R1 Information Element and Test-Path Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-048-Artifact-Authorization-OQI-H2-I-R1-Governance-Reconciliation-and-Verification-Hardening-Amendment.md`
(OQI-H2-I-R1 — the direct precedent for this exact class of gap: implementation discovers, before
completion, that (a) a frozen architecture assumption requires re-verification against real repository
state, and (b) mechanical test-path corrections are required beyond the original Artifact Authorization's
exact list); `CDD-047-Artifact-Authorization-Mechanical-Migration-Head-Regression-Amendment.md` (the
original precedent for retroactive, disclosed, narrow path authorization).
Classification: GOVERNANCE RECONCILIATION (one architectural-feasibility re-verification, closing a
STOP H3-I correctly raised; one narrow additive Artifact Authorization extension for three mechanically-
necessary test-path corrections. No change to CDD-049's frozen semantics, schema, evaluator contract,
Consistency-projection algorithm, remediation design, authorization scope, or crown invariants.)

## 1. Purpose

OQI-H3-I implemented CDD-049 §4-§25 exactly (domain, persistence, 3 migrations, evaluator, Consistency
G0 algorithm, remediation, coverage, Keycloak — all real-PostgreSQL-verified, all static gates clean —
commit `d2afe4472fca8138c828d2123959a4f1133902d5`), then correctly STOPPED before the seeder, reporting
two findings: (a) an apparent Information Element architectural prerequisite gap, and (b) an Artifact
Authorization insufficiency discovered via the mandatory full regression run. This amendment
independently re-verifies both findings against real repository state, resolves (a) as **Option A** —
the governed Information Element model exists and is already populated in the real system; H3's crown
scenario merely needs a genuine instantiation for its own semantic concept, achievable entirely through
already-existing, unmodified production code called from the already-authorized `demo_oqi_seeder.py` —
and resolves (b) by authorizing exactly three additional test-file corrections, narrow and mechanical,
mirroring CDD-048's own H2-I-R1 precedent for the identical defect class.

## 2. Context — independently re-derived

Re-verified against `oqi-h3/conformity-canonical-standards` at `d2afe4472fca8138c828d2123959a4f1133902d5`:
`git diff --name-status f2022fc7afb62a36e9a0115c9b621f3de599a133...HEAD` shows exactly 17 paths (8 CREATE,
9 MODIFY), every one a member of the original CDD-049 Artifact Authorization's 28-path set. **Zero
unauthorized writes occurred.** H3-I correctly stopped before touching the 11 remaining authorized paths
(2 test files, `demo_oqi_seeder.py`, `.github/workflows/ci.yml`, 7 mechanical table-count re-pins) and
before touching any of the three paths identified in §5 below (which were, at that time, genuinely
unauthorized).

## 3. Information Element gap — independently reproduced, then re-investigated

**Reproduction (confirmed identical to H3-I's own report)**: against a freshly `alembic upgrade head`-ed
database with no further seeding, `blueprints` / `concept_requirements` / `information_element_
requirements` / `semantic_mappings` are all genuinely 0 rows.

**The critical re-investigation H3-I did not perform**: this reproduction is **incomplete** — it omits
the standard, already-existing, already-governed seeding sequence every real deployment runs
(`backend/docker-entrypoint.sh`: `alembic upgrade head` → `OntologySeeder(session).load()` →
`BlueprintSeeder(session).load()`, in that order, before the server starts). Independently running this
exact sequence against the same freshly-migrated database:

```
OntologySeeder().load()   -> 11 entity_types populated (System Actor, Supplier, Material, BOM, Product,
                              Facility, Region, Contract, Risk Event, Revenue Exposure, Alternate Supplier)
BlueprintSeeder().load()  -> blueprints = 1 ("CTEC Semiconductor Supply Chain Blueprint")
                              concept_requirements = 10
                              information_element_requirements = 2
                              ("Supplier Legal Name", "Risk Event Severity")
```

**Conclusion (binding)**: `MODEL EXISTS BUT IS UNINSTANTIATED FOR THIS CONCEPT` — not `MODEL DOES NOT
SUPPORT H3`. The Blueprint / `ConceptRequirement` / `InformationElementRequirement` governed structure is
real, already-populated in every real deployment, and fully capable of representing "Manufacturing
Country" — it simply does not yet contain that specific element, because no prior phase (OQI1 through
H2) ever needed it. This is a **data gap for one new semantic concept**, not an architectural gap. H3-I's
own STOP was the correct, fail-closed response to an *incomplete* reproduction — disclosed and corrected
here, not silently patched.

## 4. `QualityRule.information_element_requirement_id` — resolved

Independently re-confirmed: `String(200)`, no FK, populated today with the free-text value
`"ier-country-of-origin"` on the existing H2 Accuracy rule. This field predates H3 (added when Accuracy's
`QualityRule` was first authored in H2) and was **never** connected to the real `information_element_
requirements` table — a pre-existing, disclosed-but-uncorrected looseness (CDD-049 §8 itself already
named it: "no FK constraint currently enforced at that layer — an existing, pre-H3 looseness this
document does not need to correct to proceed"). CDD-049 did **not** conflate this field with the governed
table; §8 explicitly froze a *stricter* new column (`CanonicalStandard.information_element_requirement_id`,
a real `Uuid()` FK) specifically because this existing field's own looseness was already known. H3's own
new `QualityRule` rows (for Conformity, created fresh by the seeder) will populate this field with the
**real** `InformationElementRequirement` UUID (as a string), never a free-text label — resolving the
mismatch prospectively without touching the pre-existing Accuracy rule or its own field value.

## 5. R1 architectural decision — OPTION A (frozen)

**APPROVED.** `CanonicalStandard` remains anchored exclusively to a governed Information Element,
exactly as CDD-049 §8 froze. No SourceField fallback is introduced. The genuine prerequisite chain for
H3's own crown scenario:

```
Blueprint ("OQI-H3 Conformity Demo Blueprint", a NEW, separately-named, Approved Blueprint --
           never superseding or modifying the existing canonical "CTEC Semiconductor Supply Chain
           Blueprint", whose own ConceptRequirement/InformationElementRequirement set (§3) is
           untouched)
    -> ConceptRequirement (referencing the ALREADY-SEEDED "Supplier" EntityType -- no new EntityType)
        -> InformationElementRequirement ("Manufacturing Country")
    <- approved SemanticMapping (SAP SourceField -> "Manufacturing Country")
    <- approved SemanticMapping (PLM SourceField -> "Manufacturing Country")
```

Constructed entirely via **already-existing, unmodified production code**: `app.domain.blueprint`'s
`Blueprint`/`ConceptRequirement`/`InformationElementRequirement`/`Obligation` dataclasses,
`BlueprintRepositoryImpl.create()` (one existing, unmodified transaction call — the exact same method
`blueprint_seed.py` itself calls), `app.domain.semantic_mapping.SemanticMapping`, and
`SemanticMappingRepositoryImpl.create()` (also existing, unmodified). **No product code file is created
or modified for this chain** — only `demo_oqi_seeder.py` (already authorized, §7 row 9 of the original
Artifact Authorization) gains the calls, following exactly the same "reference existing governed
structure, seed deterministic configuration" pattern `blueprint_seed.py` itself already established for
the canonical Blueprint.

## 6. Governed prerequisite vs. demo fixture — explicit classification (binding)

```
Blueprint domain classes / BlueprintRepositoryImpl / SemanticMapping domain class /
SemanticMappingRepositoryImpl                          EXISTING PRODUCTION CAPABILITY, reused unmodified
"Supplier" EntityType                                    EXISTING, already-seeded governed data
"OQI-H3 Conformity Demo Blueprint" + its one
  ConceptRequirement + one InformationElementRequirement  NEW, deterministic SEEDER CONFIGURATION
                                                          (demo_oqi_seeder.py, already authorized)
Two approved SemanticMapping rows (SAP, PLM)              NEW, deterministic SEEDER CONFIGURATION
                                                          (demo_oqi_seeder.py, already authorized)
```

**No genuinely new production code is required or authorized by this amendment for the Information
Element chain itself.**

## 7. Three test-path omissions — independently re-verified (not merely trusted from H3-I's report)

| # | Path | Exact current assertion | H3-caused reason | Original AA member? |
|---|---|---|---|---|
| 1 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | `test_quality_dimension_is_exactly_four_after_h2_accuracy`: `assert len(list(QualityDimension)) == 4` and an exact 4-member value set | `QualityDimension` correctly grows to 5 (`CONFORMITY` added, CDD-049 §4) — identical defect class to CDD-048 H2-I-R1's own 3→4 correction of this exact same test | No |
| 2 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | `test_unsupported_dimension_dispatch_returns_false_without_querying`, parametrized over `[UNIQUENESS, TIMELINESS, INTEGRITY, CONFORMITY]`, asserting no repository is constructed | `CONFORMITY` now dispatches to `OqiConformityEvaluationRepositoryImpl` and must be removed from this list, mirroring `test_accuracy_dispatches_to_accuracy_repository`'s exact established pattern (a new `test_conformity_dispatches_to_conformity_evaluation_repository` test is required, not merely a deletion) | No |
| 3 | `backend/app/tests/test_runtime_architecture.py` | `test_oqi1_quality_foundation_respects_every_firewall`: `_construction_sites("QualityEvaluationORM")`, `_construction_sites("QualityEvaluationEvidenceORM")`, `_construction_sites("QualityFindingORM")` each asserted to equal exactly the two existing sites (`oqi_accuracy_evaluation_repository.py`, `oqi_quality_evaluation_repository.py`) | `oqi_conformity_evaluation_repository.py` is a genuine, governed, CDD-049 §14-authorized third construction site for all three ORM classes (Conformity is OQI1-storage-shaped) — `QualityRuleORM`'s own single-site assertion is unaffected (Conformity constructs no new `QualityRuleORM`, reusing the existing single site) | No |

All three independently confirmed via direct source inspection this phase, not accepted on the prior
report's word. **The exact assertions above are the ones this amendment authorizes correcting — nothing
broader.** The firewall's allowlist discipline itself (an exact, closed set, never a directory-level
exemption) is preserved, extended by exactly one entry per ORM class.

## 8. Full-regression arithmetic — reconciled exactly (no double-counting)

H3-I's fresh full-regression run (`1811 passed, 10 failed`) is reconciled to exactly 10 distinct causes,
none overlapping:

| # | Test node ID | Cause | H3-caused? | Already authorized? | Requires this amendment? |
|---|---|---|---|---|---|
| 1 | `test_oqi_business_impact.py::test_migration_round_trips_94_100_94_100` | stale H2-era table-count literal | mechanical consequence of H3's migrations | Yes (original AA row 13) | No |
| 2 | `test_oqi_business_rule_postgres.py::test_table_count_is_86` | stale table-count literal | mechanical | Yes (row 14) | No |
| 3 | `test_oqi_ontology_impact_postgres.py::test_migration_round_trips_cleanly` | stale table-count/head literal | mechanical | Yes (row 15) | No |
| 4 | `test_oqi_quality_coverage_policy_domain.py::test_quality_dimension_is_exactly_four_after_h2_accuracy` | §7 item 1 | semantic-mechanical | **No — this amendment, §9 row 1** | Yes |
| 5 | `test_oqi_quality_coverage_policy_service.py::test_unsupported_dimension_dispatch_returns_false_without_querying[CONFORMITY]` | §7 item 2 | semantic-mechanical | **No — this amendment, §9 row 2** | Yes |
| 6 | `test_oqi_remediation_agent_i2.py::test_migration_round_trips_90_94_90_94` | stale table-count literal | mechanical | Yes (row 16) | No |
| 7 | `test_oqi_remediation_i1.py::test_migration_round_trips_86_90_86_90` | stale table-count literal | mechanical | Yes (row 17) | No |
| 8 | `test_persistence_integration.py::test_connection_and_migration` | stale table-count literal | mechanical | Yes (row 18) | No |
| 9 | `test_runtime_architecture.py::test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` | pre-existing, untracked `docs/product/` — independently re-proven this phase to be the sole cause (see §11) | No — pre-existing, unrelated | N/A (explicitly out of scope, CDD-049 §34) | No |
| 10 | `test_runtime_architecture.py::test_oqi1_quality_foundation_respects_every_firewall` | §7 item 3 | semantic-mechanical | **No — this amendment, §9 row 3** | Yes |

**Exactly 10 causes, exactly 10 failures — no double-counting, no ambiguity carried forward.** Row 9's
`docs/product/` causality is unchanged from the H2-VM precedent (same mechanism, same untracked
directory) and is independently reconfirmed unaffected by any H3 change (H3 touches zero files under
`docs/`).

## 9. R1 Artifact Authorization — exact additive allowlist

```
CREATE = 0
MODIFY = 4
DELETE = 0
TOTAL  = 4
```

| # | Path | CREATE/MODIFY | Exact permitted correction |
|---|---|---|---|
| 1 | `backend/app/tests/test_oqi_quality_coverage_policy_domain.py` | MODIFY | `test_quality_dimension_is_exactly_four_after_h2_accuracy` → rename/update to assert exactly 5 members including `CONFORMITY` (§7 item 1). No loosening to `>=`/subset/`contains`. No other test in this file may change. |
| 2 | `backend/app/tests/test_oqi_quality_coverage_policy_service.py` | MODIFY | Remove `CONFORMITY` from the unsupported-dimension parametrize list; add one new test, `test_conformity_dispatches_to_conformity_evaluation_repository`, mirroring `test_accuracy_dispatches_to_accuracy_repository`'s exact structure (§7 item 2). No other test in this file may change. |
| 3 | `backend/app/tests/test_runtime_architecture.py` | MODIFY | Add `"infrastructure/persistence/oqi_conformity_evaluation_repository.py"` to the expected site list for `QualityEvaluationORM`, `QualityEvaluationEvidenceORM`, and `QualityFindingORM` in `test_oqi1_quality_foundation_respects_every_firewall` (§7 item 3). `QualityRuleORM`'s assertion is unchanged. No other test in this file may change under this authorization (mechanical table-count/path work for this file, if any is later discovered, requires its own separate authorization). |
| 4 | `backend/app/infrastructure/persistence/demo_oqi_seeder.py` | MODIFY (already listed in the original AA row 9 — restated here only to make explicit that the Information Element/SemanticMapping construction calls described in §5-§6 are within that existing authorization's scope, not a new grant) | Add the H3 Information Element prerequisite chain (§5) using only existing, unmodified `Blueprint`/`ConceptRequirement`/`InformationElementRequirement`/`SemanticMapping` domain classes and `BlueprintRepositoryImpl`/`SemanticMappingRepositoryImpl`, plus the frozen H3 crown scenario itself (CDD-049 §30). No modification to `blueprint_repository.py`, `semantic_mapping_repository.py`, `blueprint_seed.py`, or any Blueprint/SemanticMapping domain file. |

No IE/seeder path beyond row 4 is authorized — §5/§6 proved no new production file is necessary. No API
or frontend authorization is added; CDD-049 §26's absolute prohibition is unchanged.

## 10. Unchanged, reaffirmed (binding)

Table count remains exactly **114** (independently re-verified this phase against real PostgreSQL,
unchanged from CDD-049 §28/AA §5). The Accuracy firewall (CDD-049 §18/PO-H3-02) is unchanged and
unaffected by this amendment. The ER firewall (CDD-049 §13/§35 STOP condition 4) is unchanged. All eight
new and twenty preserved crown invariants (CDD-049 §32) are unchanged. The three already-committed
migrations (`0031_oqi_h3_canonical_standard`, `0032_oqi_h3_conformity_evidence`,
`0033_oqi_h3_consistency_proj`) are unchanged and require no amendment — the shortened `0033` revision id
remains exactly as mechanically pre-authorized by the original Artifact Authorization §5, not touched
again here.

## 11. Historical honesty (binding, disclosed without euphemism)

H3-I stopped correctly and disclosed both findings honestly. Finding (a) (Information Element
prerequisite) is resolved here as a re-verification defect in H3-I's own reproduction methodology — not
a flaw in CDD-049's frozen architecture, and not a flaw in H3-I's judgment to stop rather than guess.
Finding (b) (Artifact Authorization insufficiency) is a genuine, disclosed gap in the original CDD-049
Artifact Authorization, closed narrowly here, mirroring the exact CDD-048 H2-I-R1 precedent for the
identical defect class (a new dimension's addition mechanically invalidating a fixed set of pre-existing
test assertions elsewhere in the suite). No implementation write occurred against either finding before
this amendment's publication.

## 12. Governance byte-integrity

CDD-049 main and original Artifact Authorization remain byte-identical to their frozen hashes (re-verified
immediately before this amendment's publication):
```
a45242b6a821a984031c1c3238aeed13b0c5d4f570c443e8510cf04f0bf3eaa4  CDD-049 main
0cd38498f8df59dd282992857ae01dc566bec9279531e9309b83a154f90e323f  CDD-049 Artifact Authorization
```
Neither is modified by this amendment.

## 13. Authorization

This amendment is approved for publication as the governance basis for OQI-H3-I-R1. Implementation
against §9's 4-path allowlist is authorized only after this document's own publication and hash
computation — never before.
