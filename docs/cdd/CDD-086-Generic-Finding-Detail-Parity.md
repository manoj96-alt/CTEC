# CDD-086 — Generic Finding Detail Parity

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `NOETVA-INTEGRITY-FINDING-DETAIL-DR` (this phase's own preceding, independently-revalidated
discovery); CDD-084 H6-G-R1 and CDD-050 H4-R1 (the established repository pattern of a narrow correction
governed independently of the phase that first surfaced the gap)
Classification: LIST/DETAIL REGISTRY ASYMMETRY (primary) + CLOSED-ENUM GUARDED-CONVERSION GAP (secondary,
downstream)
Governs: a new, independent implementation against `origin/main` (`75d11b460240147c35d4d91023ee4a47a6dbea9a`).
Does not govern, modify, or depend on `product/noetva-demo-readiness-i` (`aba8f5b5f8693a234dd3d96ef427a57a1d4a806a`)
in any way.

## 1. Purpose

Freezes the smallest correct repair for a defect independently discovered and root-caused by
`NOETVA-INTEGRITY-FINDING-DETAIL-DR`: a Finding visible through Noetva's generic Findings list is, for three
storage families, **not retrievable** through the generic Finding-detail contract that same list implies.

Originally reported as an Integrity-only defect. DR proved it is broader: **Integrity, Timeliness, and
Uniqueness storage families all suffer the identical gap**, introduced independently by two different prior
implementation phases (H5-I2 and H6-I2), each of which extended Finding *list* visibility for its own new
family without extending the shared Finding *detail* resolution method to match.

## 2. Independent revalidation performed this phase

Re-confirmed directly against a fresh worktree checked out from `origin/main` (not reused from DR):

```
list_findings()      6 family branches: OQI1, OQI2, OQI3, FindingStorageFamily.INTEGRITY (x2 models),
                      FindingStorageFamily.TIMELINESS, FindingStorageFamily.UNIQUENESS
_resolve_finding()    3 family branches only: OQI1, OQI2, OQI3 -- final `return None` for anything else
```

Every generic-detail tab method (`get_finding_detail`, `get_evidence`, `get_ontology_impact`,
`get_business_impact`, `get_reliance`, `get_agent_investigation`, `get_remediation`) calls
`self._resolve_finding(...)` as its first line -- confirmed by direct grep, 8 call sites total (one is
`get_remediation`'s internal staleness re-check).

`get_uniqueness_candidate_detail` (the dedicated H6 pair-detail endpoint) uses a structurally separate
lookup (`self._uniqueness_evaluation_repo.get_finding(finding_id)`), never `_resolve_finding` -- confirmed
unaffected by both the defect and this fix.

`RemediationFindingFamily(finding.family.value)` is constructed unconditionally at exactly three call sites:
`get_evidence` (line 841), `get_agent_investigation` (line 1021), `get_remediation` (line 1085) -- confirmed
by direct grep against the fresh worktree.

Frontend: exactly one `<Link href={\`/quality/findings/${item.finding_id}\`}>` for every Finding row
regardless of family (`app/quality/findings/page.tsx`) -- confirmed unchanged, no per-family routing exists
or is needed.

Migration head: `0047_oqi_h6_uniqueness`, unchanged -- confirmed the Integrity/Timeliness/Uniqueness storage
tables already exist (created by their own original migrations); this defect is pure application dispatch
logic, never a schema gap.

No STOP condition (§39 of the governing prompt) was triggered by this revalidation.

## 3. Capability name (binding)

Governed as **Generic Finding Detail Parity**, covering Integrity, Timeliness, and Uniqueness together --
never narrowed back to "Integrity Finding Detail Fix." All three families share one root cause and are fixed
by one localized change.

## 4. Frozen problem statement

```
A Finding returned by Noetva's generic Findings list must be retrievable through the generic Finding-detail
contract, for the same tenant and the same finding_id.

Violation: list_findings() supports {OQI1, OQI2, OQI3, INTEGRITY, TIMELINESS, UNIQUENESS};
           _resolve_finding() supports only {OQI1, OQI2, OQI3}.

Therefore INTEGRITY/TIMELINESS/UNIQUENESS rows are LISTABLE but NOT RETRIEVABLE.
```

## 5. Primary design principle (binding)

```
LISTABLE -> RETRIEVABLE.

NOT: RETRIEVABLE -> EVERY CAPABILITY MUST EXIST.
```

Generic detail parity means the page can honestly explain the Finding. It does not mean Integrity, Timeliness,
or Uniqueness gain remediation, agent execution, propagated ontology impact, or any capability they do not
already, genuinely have. Unsupported capability remains honestly unsupported/unknown/empty.

## 6. Preserved invariants (binding, restated, unchanged by this correction)

```
UNKNOWN != LOW
AGENT != FACT
RECOMMENDATION != AUTHORIZATION
REMEDIATION != RESOLUTION
DUPLICATE CANDIDATE != DUPLICATE FACT
CONFIRM_DUPLICATE != MERGE_ENTITY
NO IMPACT EVALUATION != NO IMPACT
NO REMEDIATION CASE != REMEDIATED
```

Nothing in this correction manufactures capability merely because generic detail now loads.

## 7. Production fix path (binding)

```
MODIFY (exactly one production file):

  backend/app/application/oqi_product_experience_service.py
```

No router change (the route handler purely delegates to the service, confirmed by direct read -- no
per-family logic exists in `router.py`'s `get_finding_detail`/list handlers). No frontend change (§2, §20).
No second production path.

## 8. `_resolve_finding()` contract (binding)

Extend `_resolve_finding()` with branches for `IntegrityStructuralFindingORM`, `IntegrityReferenceFindingORM`,
`TimelinessFindingORM`, and `UniquenessFindingORM`, mirroring the exact query pattern and
`condition_label` derivation `list_findings()` already uses for each (structural/reference `finding_type`;
Timeliness `finding_type`; Uniqueness's fixed `"DUPLICATE_ENTERPRISE_ENTITY_CANDIDATE"` label). No second,
divergent interpretation of any of these four storage families.

## 9. Tenant-safety contract (binding)

Every new branch must preserve the existing pattern exactly: a row resolves only when both `finding_id`
matches (`session.get`) **and** `tenant_id` matches. Wrong tenant and unknown ID both yield
`404 OQI_FINDING_NOT_FOUND` (or `None` at the service layer) -- no unscoped `session.get()` result may ever
be returned without a tenant check, matching the model every existing branch already establishes.

## 10. `_resolve_entity()` / subject-resolution contract (binding)

Extend entity resolution for Business Impact and Reliance to route Integrity/Timeliness/Uniqueness through
the same per-family resolvers `list_findings()` already calls: `resolve_integrity_structural_finding_subject`,
`resolve_integrity_reference_finding_subject`, `resolve_timeliness_finding_subject`,
`resolve_uniqueness_finding_subject` (`OqiBusinessImpactRepositoryImpl`, unmodified). The existing
`FindingFamily`-typed path (`resolve_finding_subject`, whose final branch is
`raise AssertionError("unreachable: unknown finding_family ...")`) remains untouched and continues to serve
OQI1/OQI2/OQI3 exactly as today -- it is never called with a `FindingStorageFamily` value. No new
ontology/entity-resolution semantics are introduced; only reuse of already-existing, already-correct
resolvers.

## 11. Evidence contract (binding)

`get_evidence()` must not construct `RemediationFindingFamily(finding.family.value)` when the resolved
family is outside `{OQI1, OQI2, OQI3}`. For Integrity/Timeliness/Uniqueness, skip that lookup and return the
legitimate result already supported by existing data: empty `participants` (no OQI2-style cross-source
comparison exists for these families, matching the existing OQI1/OQI3 "legitimately never populate evidence"
precedent) and `candidate=None`. Never fabricate participants.

## 12. Ontology Impact contract (binding)

Unchanged. `get_ontology_impact()` already degrades honestly: `get_current_impacts_for_finding` performs a
plain string-keyed query with no enum reconstruction, so passing a `FindingStorageFamily` value causes no
crash -- it correctly finds zero rows (independently confirmed empirically: zero `current_ontology_impacts`/
`ontology_impact_evaluations` rows exist for any family but OQI2 in the demo tenant, since OQI4 evaluation has
never been run for Integrity/Timeliness/Uniqueness) and returns `ImpactOutcome.IMPACT_UNKNOWN`. This
correction authorizes zero change to `get_ontology_impact()` or to OQI4 evaluation. `IMPACT_UNKNOWN` is never
reinterpreted as `NO_IMPACT` or any other outcome.

## 13. Business Impact contract (binding)

`get_business_impact()` operates through the existing, unmodified generic dependency machinery
(`list_active_dependencies_for_subject`, `get_current_impact_status_for_subject`,
`derive_business_impact_outcome`) once §10's extension resolves a real `entity_id` for the newer families. If
a real dependency exists, it is shown, exactly as it already is for OQI1-3. If none exists, the existing
honest `BUSINESS_IMPACT_UNKNOWN` result is returned, unchanged. No dependency is seeded or manufactured by
this correction.

## 14. Reliance contract (binding)

`get_reliance()` operates through the existing, unmodified `CurrentRelianceORM`/`OqiRelianceEvaluationORM`
lookups once §10's extension resolves a real `entity_id`. DR empirically proved a real Timeliness Finding
correctly and legitimately produces `BUSINESS_IMPACT_IDENTIFIED`/`RELIANCE_AT_RISK` once the entity resolves
-- this correction preserves that exact behavior. No family is hardcoded to any Reliance state; Integrity and
Uniqueness are not made `AT_RISK` for symmetry where no real dependency/evaluation supports it.

## 15. Agent Investigation contract (binding)

`get_agent_investigation()` must not construct `RemediationFindingFamily(finding.family.value)` for
Integrity/Timeliness/Uniqueness. For these families, skip the case/run lookup entirely and return the
existing honest empty result: `AgentInvestigationRow(specialists=(), recommendation=None)`. No agent
execution capability is granted to any of these families by this correction; no output is seeded.

## 16. Remediation contract (binding)

`get_remediation()` must not construct `RemediationFindingFamily(finding.family.value)` for
Integrity/Timeliness/Uniqueness. For these families, skip the case lookup entirely and return the existing
honest empty result: `RemediationRow(case_status=None, candidate=None, recommendation=None,
authorization=None, external_execution=None)`. No remediation case is created or implied. H6's own dedicated
adjudication semantics (`get_uniqueness_candidate_detail`, `OqiUniquenessCandidateRepositoryImpl`) remain
entirely separate and are not touched by this correction.

## 17. Closed-enum decision (binding)

`FindingFamily` (`app.domain.oqi_ontology_impact.evaluation`, OQI4's own) and `RemediationFindingFamily`
(`app.domain.oqi_remediation.case`, aliased `FindingFamily` in the service module) both remain closed to
their current `{OQI1, OQI2, OQI3}` membership. Neither is broadened to include `INTEGRITY`, `TIMELINESS`, or
`UNIQUENESS` — doing so would imply a broader semantic participation (remediation-case identity, OQI4
propagation-evaluation identity) that does not exist for these families today. The fix is localized guarded
conversion (§18) at the call sites, never enum broadening.

## 18. Guarded-conversion rule (binding)

At exactly the three identified call sites (`get_evidence`, `get_agent_investigation`, `get_remediation`):
construct `RemediationFindingFamily(finding.family.value)` **only** when the resolved family is a member of
`FindingFamily` (i.e. is genuinely `OQI1`/`OQI2`/`OQI3`); for any other resolved family, skip the
construction and the dependent case/candidate lookup entirely, returning that method's own honest
empty/unsupported result as specified in §11/§15/§16. No other call site requires this guard (independently
re-confirmed: exactly these three, no more, no fewer).

## 19. Uniqueness pair-detail boundary (binding)

The existing dedicated `get_uniqueness_candidate_detail` endpoint (and its frontend consumer,
`fetchUniquenessCandidateDetail`) is preserved exactly as-is. This correction does not merge, replace, or
route through it. The resulting product behavior: generic Finding detail (context/tabs, now honestly
retrievable) plus, for Uniqueness specifically and only after generic detail already succeeds, the existing
dedicated pair-detail call layers on exactly as the frontend already implements (`finding.finding_family ===
"UNIQUENESS" ? await fetchUniquenessCandidateDetail(...) : null`, unmodified).

## 20. Frontend decision (binding)

**Zero frontend change**, confirmed by revalidation (§2): the frontend already sends the exact `finding_id`
the list API returned, to the one generic route, for every family, and already layers the Uniqueness-specific
fetch on top only after the generic call succeeds. Backend parity alone restores the frontend's own,
already-correct, already-intended behavior. No workaround, no family-specific routing hack is authorized or
needed.

## 21. Schema/migration decision (binding)

**Zero migration.** No new table, no FK change, no enum migration, no persistence-model redesign. All
required data already exists in `integrity_structural_findings`, `integrity_reference_findings`,
`timeliness_findings`, and `oqi_uniqueness_findings` (confirmed: migration head remains `0047_oqi_h6_uniqueness`,
unchanged; these tables were created in migrations 0034-0047, already present, already correctly written and
read by `list_findings()`).

## 22. OQI semantic-change decision (binding)

**Zero.** No evaluator change, no Finding-generation change, no OQI4 evaluator expansion, no Reliance
algorithm change, no remediation architecture change, no agent architecture change. This is product-serving
read-contract parity only.

## 23. Implementation method (binding, exhaustive)

```
A. Extend _resolve_finding() using the exact query/condition-label semantics already proven in
   list_findings() (§8).
B. Extend subject/entity resolution for the four newer storage-family branches using the already-existing
   per-family resolvers list_findings() already calls (§10).
C. Guard the RemediationFindingFamily(finding.family.value) construction at exactly the three identified
   call sites (§18).
D. Preserve existing behavior for OQI1/OQI2/OQI3 exactly -- zero change to any of their three original
   branches, zero change to get_ontology_impact() (§12), zero change to get_uniqueness_candidate_detail()
   (§19).
E. Do nothing else.
```

No central registry rewrite, no generic polymorphic repository, no `FindingFamily` enum redesign, no
storage-family architecture redesign, no service decomposition, no router redesign, no frontend redesign are
authorized by this document. Those remain out of scope, future cleanup if ever pursued.

## 24. Deferred register

```
- OQI4 evaluation for Integrity/Timeliness/Uniqueness (would let Ontology Impact show real DIRECT/PROPAGATED
  impact instead of honest IMPACT_UNKNOWN) -- explicitly deferred, not required to fix this defect honestly.
- Whole-suite local test-isolation characteristic (27 backend / 1 frontend pre-existing failures, DR-
  classified UNRELATED to this correction) -- explicitly out of scope; PARITY-I must still run and honestly
  report the full regression; final Demo-VM must independently revisit before external-demo certification.
- Golden Demo runbook's Uniqueness-detail step (currently describes behavior main does not yet support) --
  explicitly deferred to Demo-VM composition, not authorized for edit in this narrow correction (§30 of the
  governing prompt).
```

## 25. Authorization

This document, together with its companion Artifact Authorization, is approved and published as the exact,
binding architecture for Generic Finding Detail Parity. Implementation may proceed only against the paths
authorized there; any deviation requires a narrow governance amendment, never a unilateral implementation-time
decision, exactly as every prior phase in this program.
