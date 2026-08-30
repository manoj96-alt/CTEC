# CDD-045 — Ontology Quality Intelligence: Flagship Explainable Product Experience (OQI7)

**Status:** APPROVED GOVERNANCE FREEZE
**Version:** 1.0
**Governs:** OQI7 — the product/UX/API layer over the closed OQI1–OQI6 intelligence capability
**Predecessors (frozen, unmodified, consumed only):** CDD-039 (OQI1), CDD-040 (OQI2), CDD-041 (OQI3),
CDD-042 (OQI4), CDD-043 (OQI5), CDD-044 (OQI6), CDD-033 (Enterprise UX / Gate X) as narrowly amended by
`CDD-033-OQI7-Placeholder-Supersession-Amendment.md`
**Companion:** `CDD-045-Ontology-Quality-Intelligence-Flagship-Explainable-Product-Experience-Artifact-Authorization.md`

## 1. Canonical purpose

> OQI7 makes CTEC's closed Ontology Quality Intelligence capability (OQI1–OQI6) understandable, explorable,
> and actionable to real product personas, without weakening any epistemic or governance boundary those six
> capabilities established. OQI7 is a product-serving read/composition layer and a flagship UX — it is not a
> seventh intelligence engine. It introduces zero new deterministic facts; it explains the facts OQI1–OQI6
> already produce.

## 2. Canonical product name

**Ontology Quality Intelligence**, short form **OQI**. Historical "Generalized Data Quality" terminology
(CDD-033) remains historical evidence only — CDD-033 itself is not renamed or edited.

## 3. Live baseline verified at governance time

```
Local main = origin/main = GitHub main = b634d0af457333329efdb00ecd180a634e8be5c1
Migration head (verified against real PostgreSQL, not the migration-chain file alone): 0026_oqi6_reliance
Live table count (verified against real PostgreSQL):                                   100
OQI1-6: CLOSED. Zero OQI1-6 semantic modification authorized by this CDD.
```

## 4. CDD-033 compatibility — explicit determination

Read CDD-033 and its Artifact Authorization directly and in full at governance time. Findings:

- CDD-033 §8 froze `/quality` as a binding top-level enterprise IA domain. **OQI7 fits inside it without
  requiring a new top-level route.**
- CDD-033 §8/§15/§18 froze the literal labels "Rules [PLANNED]", "Findings [PLANNED]", "DQ Impact [PLANNED]"
  and CDD-033 Artifact Authorization §14 **explicitly and bindingly prohibited** live routes at
  `/quality/rules`, `/quality/findings`, `/quality/impact` — exactly the routes OQI7 needs.
- **CDD-033 amendment was required** and is published as `CDD-033-OQI7-Placeholder-Supersession-Amendment.md`
  (this amendment's SHA-256 recorded in §21 below), narrowly superseding only the PLANNED/prohibited status of
  those four concepts to the exact extent this CDD governs their live replacement. No other CDD-033 decision,
  relocation rule, or firewall is touched.

## 5. Product domain / navigation (frozen)

`/quality` remains the sole top-level OQI route. No `/oqi` or `/ontology-quality-intelligence` top-level
route is authorized. Within `/quality`:

```
/quality                          -- OQI Command Center (replaces the 4 PLANNED placeholder cards)
/quality/evidence-fitness         -- unchanged, pre-existing, untouched by this CDD
/quality/findings                 -- Findings list (was: PLANNED "Findings")
/quality/findings/{findingId}     -- Finding detail: Evidence / Ontology Impact / Business Impact /
                                      Reliance / Agent Investigation / Remediation tabs
```

"Rules" (OQI3) and "DQ Impact"/"Ontology Impact" (OQI4) do **not** become standalone top-level pages — they
are investigated in the context of a Finding, never browsed in the abstract (rule/dependency *authoring* is
explicitly OUT, §14). "Remediation" (OQI5) is a tab within Finding detail, not a standalone route, because a
remediation case is always scoped to a specific Finding's lifecycle.

Product navigation does **not** mirror OQI1–OQI6 as user-facing labels. Those remain implementation/governance
capability boundaries, invisible to the product.

## 6. Executive product question (frozen)

> **Can I rely on my enterprise knowledge, where is it at risk, why does it matter, and what is being done
> about it?**

The Command Center must let an executive answer this from real backend state in approximately 5–10 seconds,
with zero fabricated or placeholder value.

## 7. Command Center (frozen contract)

Hero: OQI6 Reliance-state distribution, three raw counts, no score:

```
Reliance Supported   <count>
Reliance At Risk     <count>
Reliance Unknown     <count>
```

Supporting cards (each independently gated on §9's metric-contract discipline):

```
Critical business dependencies affected   <count>   -- RELIANCE_AT_RISK subjects with >=1 ACTIVE
                                                         CRITICAL BusinessDependency
Open Findings                             <count>   -- OPEN status across OQI1/OQI2/OQI3 families
Active agent investigations               <count>   -- AgentRun rows without a terminal
                                                         recommendation yet
Pending human authorization               <count>   -- OQI5-I1 RemediationAuthorization rows in
                                                         PENDING status
```

No card renders if its backing query cannot be truthfully defined. A capability with no governed aggregate is
absent from the Command Center, never represented by a fabricated number (mirroring CDD-033 §11's own
Overview rule).

## 8. Trust score — prohibited (frozen)

No `trust_score`, `reliability_score`, `confidence_score`, `business_impact_score`, `criticality_score`,
`quality_health_score`, or any hidden numeric-to-truth mapping may exist anywhere in OQI7, in any layer. OQI7
may not reintroduce through UI or API response shape what CDD-044 architecturally rejected. This is a release-
blocking firewall, verified adversarially at OQI7-VM via static/AST inspection exactly as CDD-044 established
for OQI6 itself.

## 9. Metric contract discipline (frozen)

Every OQI7 metric (Command Center card, list-view count, badge count) must define, before implementation:
business question, tenant scope, current/historical mode, exact numerator, exact denominator (if any), time
horizon, UNKNOWN handling, and backend source. **No percentage is authorized unless its denominator is
positively, governedly closed.** The following are explicitly rejected for OQI7-I1/I2 (no governed denominator
exists at governance time):

```
"% Reliance Supported" / "% trusted" / "% healthy" / "% coverage" / "Quality Health Score" / any weighted
composite of Reliance + criticality + impact + agent output.
```

The following raw counts and immutable-ledger-backed trends **are** authorized (each backed by a real,
already-persisted, immutable evaluation ledger — OQI1's evidence frontier, OQI2/OQI3's evaluation ledgers,
OQI4's `OntologyImpactEvaluation`, OQI6's `oqi_reliance_evaluations`/`oqi_business_impact_evaluations`):

```
Reliance-state counts (current)
Open-Finding counts (current, per family/status/criticality/Reliance filter)
Findings-opened / Findings-resolved (trend, bounded time window)
Reliance-state transitions (trend, bounded time window)
```

## 10. Finding experience (frozen)

Finding list: multi-dimension filter/sort (criticality, Reliance state, status, quality family, age) — **no
composite priority score** (CDD-044's own criticality-vs-reliance separation extends here: sorting dimensions
stay independent, never blended into one ranking number). Finding detail: single page, durable URL, tabbed
sub-experiences (Evidence / Ontology Impact / Business Impact / Reliance / Agent Investigation / Remediation),
matching this repository's own `app/supplier-risk/executions/[id]` precedent for page-vs-modal choice.

Quality-dimension honesty: OQI7 must distinguish, per Finding family, `implemented` (OQI1 completeness/
validity, OQI2 N-source consistency, OQI3 governed business rules) from `not implemented` — OQI7 must never
imply all DAMA/DMBOK dimensions are covered.

## 11. Evidence experience (frozen, signature capability)

For OQI2 N-source Findings, render every governed participant literally — agreement, dissent, and missingness
all visible, none omitted:

```
SAP               ABC123
PLM               ABC123
MES               ABC123
Supplier Portal   XYZ999    <- disagrees
PIM               (missing)
```

If an OQI5-I1 `RemediationCandidate` exists for the Finding, show it as a separately labeled, non-blended
line: `Leading candidate: ABC123 — basis: 4 governed peers observed ABC123 — Candidate, not established
truth.` Source-authority metadata renders as a labeled badge on its row, never as a correctness indicator.

For OQI1 single-source Findings (`MISSING_VALUE`/`ENUM_MEMBERSHIP`/`FORMAT_VIOLATION`/`RANGE_VIOLATION`,
using OQI1's exact implementation vocabulary), render observed value vs. expected constraint. For OQI3
business-rule Findings, render the rule's governed plain-language condition and the specific triggering
input — never raw AST. `NOT_EVALUABLE` renders as its own distinct, non-green badge state, meaning "CTEC
could not evaluate this governed expectation with sufficient evidence" — never PASS, never absent.

## 12. Ontology Impact experience (frozen)

Preserve OQI4's exact closed vocabulary `IMPACTED` / `NO_IMPACT` / `IMPACT_UNKNOWN` (verified directly against
`backend/app/domain/oqi_ontology_impact/evaluation.py:73-79`, `class ImpactOutcome(StrEnum)`). `IMPACT_UNKNOWN`
renders as "Ontology impact cannot currently be determined" — never "No impact," never a muted/grey/absent
treatment. Graph rendering shows entity-level nodes only; **no attribute-level edge may ever be drawn**,
because OQI4 itself never proved attribute-level lineage (CDD-042's own limitation) — OQI7 must not manufacture
what OQI4 refused to. ReactFlow is the frozen graph library (§15).

## 13. Business Impact experience (frozen)

Verified directly against `backend/app/domain/oqi_business_impact/impact.py:34-42`,
`class BusinessImpactOutcome(StrEnum)`: exact three values `BUSINESS_IMPACT_IDENTIFIED`,
`NO_KNOWN_BUSINESS_IMPACT`, `BUSINESS_IMPACT_UNKNOWN`. Product labels:

```
BUSINESS_IMPACT_IDENTIFIED  -> "Identified business impact -- {process}, criticality {X}"
NO_KNOWN_BUSINESS_IMPACT    -> "No known business impact"     (never "No business impact exists")
BUSINESS_IMPACT_UNKNOWN     -> "Business impact cannot currently be determined"  (never "0 impact")
```

Every `BusinessDependency` for a subject renders as its own card — **never collapsed to the single
highest-criticality dependency.** Criticality is a labeled property of the dependency card, never rendered as
a property of the entity itself: the same `Material ABC123` may legitimately show `Production Planning /
CRITICAL`, `Reporting / MEDIUM`, and `Sandbox Analytics / LOW` simultaneously, and the UI must never collapse
this into "Material ABC123 = CRITICAL." Criticality vocabulary is exactly `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`
(verified against `backend/app/domain/oqi_business_impact/dependency.py:22-31`, `class Criticality(StrEnum)`)
— no numeric conversion beyond the existing internal sort order, never exposed as a score.

## 14. Business Process / Dependency administration — OUT (frozen)

OQI7 consumes pre-configured, governed `BusinessProcess`/`BusinessDependency` records. It does not author,
edit, or retire them. Quality-rule authoring (OQI3) is likewise OUT — OQI7 explains/evaluates existing
governed rules, it does not build a rule-authoring studio. If OQI7-I1/I2 implementation discovers an
unavoidable configuration dependency (e.g., no governed records exist to demo against), that is a **STOP for
Product Owner decision**, not a silent scope expansion.

## 15. Ontology graph library (frozen)

**ReactFlow** is the frozen OQI7 graph direction, verified as the already-live pattern in this repository
(`frontend/app/ontology-studio/_components/ontology-graph.tsx` and
`frontend/app/demo/supplier-risk/_components/ontology-explorer-stage.tsx` both import from `"reactflow"`).
**Cytoscape is present in `frontend/package.json` but is verified, by direct repository-wide search, to be
imported by zero files anywhere in `frontend/app`, `frontend/components`, or `frontend/lib`** — it is
pre-existing, unused dependency weight, not an active pattern. No Cytoscape removal is authorized by this CDD
(§16 of the OQI7-G phase prompt is explicit that OQI7 is not a dependency-cleanup project) — Cytoscape is left
untouched. No new graph library, and no new chart library, is authorized; OQI7-I2 trend visualization (§9's
authorized trends) uses existing design-system primitives or minimal hand-rolled SVG, consistent with this
codebase's observed preference for zero incidental dependencies.

## 16. Explainable Reliance experience (frozen, primary product mechanism)

Verified directly against `backend/app/domain/oqi_business_impact/reliance.py:31-47`: exact three states
`RELIANCE_SUPPORTED`, `RELIANCE_AT_RISK`, `RELIANCE_UNKNOWN` (`class RelianceState(StrEnum)`), and exact six
closed reason codes (`class ReasonCode(StrEnum)`): `OPEN_QUALITY_CONDITION`, `INSUFFICIENT_QUALITY_COVERAGE`,
`ONTOLOGY_IMPACT_UNKNOWN`, `BUSINESS_DEPENDENCY_UNKNOWN`, `CRITICALITY_UNKNOWN`, `REMEDIATION_PENDING`.

Product vision remains **Explainable Trust**; the deterministic backend mechanism is **Explainable Reliance**.
Product copy: *"CTEC does not assign an arbitrary trust score. It explains whether available governed evidence
supports reliance on enterprise knowledge, shows where reliance is at risk, and explicitly identifies where
CTEC does not yet know enough."*

State language (frozen, exact):

```
RELIANCE_SUPPORTED -> "Reliance Supported" -- bounded: "Available governed evidence satisfies the
                        minimum requirements CTEC can currently establish for reliance." Never "Trusted,"
                        never "100% correct," never "universally true."
RELIANCE_AT_RISK    -> "Reliance At Risk" -- "Governed quality evidence identifies a condition affecting
                        reliance." Never "False," never "this fact is wrong."
RELIANCE_UNKNOWN    -> "Reliance Unknown" -- "CTEC does not currently have sufficient governed evidence
                        to determine whether reliance is supported." Never "Low Risk," never muted/grey
                        styling implying "nothing to see" -- equal visual weight to At Risk (§18-19).
```

Reliance detail view: state + the exact reason-code list (rendered as plain-language bullets, never free
generated prose) + contributing Finding links + Reliance-history timeline sourced from the immutable
`oqi_reliance_evaluations` ledger.

## 17. Silence is not health (frozen invariant)

```
zero open Findings              != Reliance Supported
no governed dependency recorded != no business impact
not evaluated                   != satisfied
NOT_EVALUABLE                   != PASS
```

Empty states must preserve this explicitly: "No Findings match this view" — never "Everything looks good!"
unless coverage is separately, governedly proven sufficient (which OQI7 v1 cannot claim in the general case).

## 18. Agent Investigation experience (frozen)

Verified against `backend/app/domain/oqi_remediation_agent/role.py:22-30`
(`class RecommendationType(StrEnum)`: exactly `RECOMMEND_CANDIDATE`, `REQUEST_STEWARD_INVESTIGATION`,
`NO_REMEDIATION_RECOMMENDED`) and `run.py:280-289` (`class AgentRunResultState(StrEnum)`: exactly
`SUCCEEDED`, `FAILED`, `REJECTED_OUTPUT`). Both specialist `AgentAssessment`s render side-by-side, never
collapsed — disagreement is displayed, never voted away. The synthesizer's output is labeled
**"Recommendation,"** never "Decision." No private chain-of-thought is ever requested, persisted, or exposed
— only persisted structured outputs.

**Synthesizer-only recommendation — explicitly resolved (Product Owner decision):** OQI7 distinguishes
`"Recommendation basis: Specialist-supported"` (both specialist `AgentAssessment`s available) from
`"Recommendation basis: Synthesizer-only — specialist assessments unavailable"` (per the OQI5-VM-disclosed
edge case where both specialists fail but the synthesizer's own independent provider call still succeeds) —
a non-blocking provenance line, not a warning, not a rejection.

Provider failure renders as "Agent investigation unavailable," with zero effect on deterministic quality
truth — AI is optional to deterministic OQI, always.

## 19. Human Authority experience (frozen)

Recommendation and Authorization render as two visually distinct tiers, never merged. Authorization detail
shows principal, timestamp, exact instruction, target candidate, and the Finding `state_revision` it was
authorized against, with a visible **staleness badge** if that revision has since drifted (directly backed by
OQI5-I1's real digest-recomputation fail-closed behavior — no new backend logic required, only exposing the
existing `REMEDIATION_ACTION_MISMATCH` outcome).

## 20. Remediation / Re-evaluation experience (frozen)

Language (frozen, exact — never any variant implying CTEC wrote to a source system, since no source
write-back capability exists anywhere in CTEC):

```
Authorized for external remediation
External remediation reported
Awaiting fresh evidence
Re-evaluation pending
Resolved -- confirmed by fresh evidence and re-evaluation on {date}
```

**Execution != resolution is mandatory and must be visually un-collapsible**, not merely textually correct in
a tooltip: render as an explicit stepper (Authorized -> Externally Reported -> Awaiting Fresh Evidence ->
Re-evaluation Pending -> Resolved/Still At Risk), never a single ambiguous "remediation status" badge. The
full lifecycle (Finding opened -> Agent investigation -> Recommendation -> Human authorization -> External
remediation -> Fresh evidence -> Deterministic re-evaluation -> Finding resolved/reopens -> OQI4 re-evaluation
-> OQI6 re-evaluation -> Reliance updated) is a first-class, immutable-ledger-backed timeline feature — not
manufactured from UI-side timestamps.

## 21. Governance provenance

```
CDD-033 amendment: CDD-033-OQI7-Placeholder-Supersession-Amendment.md
```

(hash recorded in the companion Artifact Authorization document, computed at publication time)

## 22. API architecture principle (frozen)

**Backend owns semantic aggregation. Frontend owns presentation composition only.** React must never
independently derive Finding truth, Reliance state, Business Impact state, candidate truth, or authorization
validity from raw data — every product-facing meaning is computed server-side and delivered as an already-
meaningful field.

Verified directly: **zero OQI API routes exist anywhere in `backend/app/api/`** at governance time (`find
backend/app/api -iname "*oqi*"` returns nothing). OQI7-I1 is therefore a from-scratch product-serving API
layer over closed OQI1–OQI6 domain capability, not an extension of any existing router.

Route namespace and conventions (verified directly against `backend/app/api/information_element_evidence_fitness/router.py`
and `backend/app/api/api_versions/router.py`):

```
prefix = "/api/v1/oqi"     (matches Gate W's existing /api/v1 versioning -- CDD-038, no parallel scheme)
tags   = ["oqi"]
_ENDPOINT_CLASSIFICATION = "OQI_API_V1"   (same constant-naming convention as every existing domain router)
Tenant: TrustedPrincipal.tenant_id via the existing `principal` dependency (app.api.supplier_risk.dependencies)
        -- no new tenant mechanism.
RBAC:   new scope `oqi:read` for all read surfaces; the two consequential actions (authorize, report
        execution) reuse OQI5-I1's existing authority checks, exposed through new HTTP routes only (new
        transport, not new authority) -- new scopes `oqi-remediation:authorize` and
        `oqi-remediation:report-execution`, mirroring the existing `governed-approval:decide`/`request`
        two-scope pattern (Gate S).
```

## 23. Read-model contracts (frozen, field-level)

Each contract below is backend-computed; the frontend renders it without inference.

**Command Center** (`GET /api/v1/oqi/command-center`): `reliance_supported_count: int`,
`reliance_at_risk_count: int`, `reliance_unknown_count: int`, `critical_dependencies_at_risk_count: int`,
`open_findings_count: int`, `active_agent_investigations_count: int`, `pending_human_authorizations_count: int`.
All tenant-scoped from `principal.tenant_id`.

**Finding list** (`GET /api/v1/oqi/findings?family=&status=&criticality=&reliance_state=&cursor=&limit=`):
paginated array of `{finding_id, finding_family, condition_label, status, first_seen_at, last_seen_at,
affected_subject: {entity_id, entity_type}, highest_criticality: Criticality|null,
reliance_state: RelianceState|null}`.

**Finding detail** (`GET /api/v1/oqi/findings/{finding_id}`): `{finding_id, finding_family, condition_label,
status, state_revision, first_seen_at, last_seen_at}` plus links to the five sub-resources below (fetched
lazily by the frontend per active tab, avoiding one giant payload).

**Evidence** (`GET /api/v1/oqi/findings/{finding_id}/evidence`): `{participants: [{source_system,
observed_value: str|null, is_missing: bool, is_authoritative: bool}], candidate: {candidate_id,
proposed_value, supporting_participant_count, status: "CANDIDATE_NOT_TRUTH"} | null}`.

**Ontology Impact** (`GET /api/v1/oqi/findings/{finding_id}/ontology-impact`): `{outcome: ImpactOutcome,
direct_entity: {entity_id, entity_type} | null, propagated_path: [{relationship_instance_id,
relationship_type, from_entity, to_entity}] | null}` — `propagated_path` omitted entirely (not
empty-arrayed) when outcome is not IMPACTED via propagation, to avoid implying a null-but-present edge.

**Business Impact** (`GET /api/v1/oqi/findings/{finding_id}/business-impact`): `{outcome:
BusinessImpactOutcome, dependencies: [{business_process_name, criticality: Criticality,
business_dependency_version}]}` — `dependencies` array preserves every governed dependency, never collapsed.

**Reliance** (`GET /api/v1/oqi/findings/{finding_id}/reliance` — actually subject-scoped, see §92 discovery
note; exposed here per-Finding for convenience): `{state: RelianceState, reason_codes: [ReasonCode],
contributing_finding_ids: [UUID], history: [{state: RelianceState, evaluated_at, triggering_finding_id}]}`.

**Agent Investigation** (`GET /api/v1/oqi/findings/{finding_id}/agent-investigation`): `{specialist_a:
{assessment_text, referenced_candidate_id} | {failed: true}, specialist_b: (same shape),
recommendation: {type: RecommendationType, candidate_id: UUID|null, rationale: str,
basis: "SPECIALIST_SUPPORTED"|"SYNTHESIZER_ONLY"} | null}`. All free-text fields are model output, rendered
as plain escaped text — never `dangerouslySetInnerHTML`.

**Remediation** (`GET /api/v1/oqi/findings/{finding_id}/remediation`): `{case_status, candidate, recommendation
(as above), authorization: {principal, decided_at, instruction, authorized_against_state_revision,
is_stale: bool} | null, external_execution: {reported_at} | null}`.

**Actions**: `POST /api/v1/oqi/remediation/authorizations/{authorization_id}/decide`,
`POST /api/v1/oqi/remediation/authorizations/{authorization_id}/report-execution` — thin HTTP wrappers over
OQI5-I1's existing `RemediationAuthorization` service methods; zero new authority logic.

## 24. Database / migration (frozen)

**Zero new tables. Zero new migration.** OQI7-I1 is a pure read/composition layer over the 100 tables already
closed by OQI1–OQI6. If OQI7-I1 implementation discovers a genuine need for new persistence (e.g., a
materialized read-model table for performance), that is a **STOP for Product Owner decision** — not something
this CDD pre-authorizes.

## 25. Security (frozen)

Model-generated text (agent assessments, recommendations, rationale) and source evidence values are untrusted
display content end-to-end — plain-text rendering only, React's default JSX escaping, never raw HTML from
either source. Every Finding/impact/authorization ID is tenant-scoped at the query layer — cross-tenant IDOR
must fail closed. Sensitive-evidence masking policy is explicitly **deferred** — no existing repository policy
resolves it, and this CDD does not invent one; if OQI7-I1 implementation discovers it would expose a category
of evidence to users who could not previously see it, that is a STOP for Product Owner governance, not a
silent default.

## 26. Firewalls (frozen)

```
OQI1-6 semantics: UNCHANGED. Consumed via new read-only API composition only.
OQI5 domain classes (ModelProvider, AgentRole, AgentRun, AgentEvidencePacket, AgentRecommendation,
  RemediationCase, RemediationCandidate, RemediationInstruction, RemediationAuthorization): UNMODIFIED.
  OQI7-I1's two write endpoints call existing service methods; they do not touch these class definitions.
Gate F: UNMODIFIED. Gate F's "Revenue Exposure" concept never appears in OQI7 as business-impact language.
Source write-back: ABSENT, unchanged.
Human authority: unchanged -- AI cannot approve, cannot self-authorize, cannot forge a principal.
Monetary impact: ABSENT -- no dollar/revenue/cost figure derived from criticality, Findings, or OQI6 state
  anywhere in OQI7.
OQI-H (enterprise hardening), Docker, Azure, Gate Y/Z: not referenced, not designed toward.
Business Process / Dependency administration UI, quality-rule authoring UI, source-connector configuration UI,
  bulk human authorization: OUT.
```

## 27. Delivery sequence (frozen)

```
OQI7-D (closed) -> OQI7-G (this document) -> OQI7-I1 (Backend + Product-Serving API)
  -> OQI7-I2 (Flagship /quality Frontend/UX, consumes frozen I1 contracts) -> OQI7-VM (adversarial
  product-truth + integration + merge)
```

No further split is authorized without a genuine newly-discovered architectural boundary. I1 decides meaning;
I2 renders it; neither may reopen the other's decisions without a governance amendment.

## 28. Test requirements (frozen, minimum)

**OQI7-I1** must prove: tenant isolation, RBAC enforcement, IDOR resistance, pagination/filtering/sorting
correctness, `IMPACT_UNKNOWN`/`NO_KNOWN_BUSINESS_IMPACT`/`RELIANCE_UNKNOWN` preservation through the API layer
(no downgrade introduced by serialization), N-source missingness/disagreement preservation, candidate-not-
truth labeling in the API response itself, specialist-disagreement and synthesizer-only-basis exposure,
authorization staleness exposure, external-remediation != resolution in API semantics, zero trust score/
monetary field anywhere in any response schema, zero new authority created by the two action endpoints.

**OQI7-I2** must prove: Command Center renders real counts with zero score, UNKNOWN states render with equal
visual weight to At Risk (not muted), Finding list/detail render every UI Truth Table (§29) constraint
correctly, missing/dissenting N-source participants remain visible, ontology graph never draws an attribute-
level edge, business-impact cards are never collapsed to "highest only," specialist disagreement is visible
by default, remediation stepper never collapses execution into resolution, empty/error/loading states are
honest and distinct, accessibility (existing `axe-core`/`vitest-axe` wiring exercised for every new page,
non-color-only status encoding), model-output/source-value rendering is XSS-safe, deep-linking works for every
Finding.

**OQI7-VM** must adversarially prove, as named concrete crown tests: (1) Executive truth — Command Center
answers the executive question from real backend state, zero fake score; (2) N-source disagreement fully
visible; (3) Majority != truth — candidate stays labeled "Candidate, not truth" even at 4-vs-1 support;
(4) `IMPACT_UNKNOWN` never renders as no impact; (5) Silence — zero Findings without proven sufficient coverage
never renders Reliance Supported; (6) Contextual criticality — same entity, multiple dependencies, multiple
criticalities, never collapsed to one entity-global value; (7) Agent disagreement visible end-to-end through
the UI; (8) Recommendation and Authorization remain visually distinct; (9) External remediation does not
resolve the Finding in either API or UI; (10) Real evaluator resolution changes downstream product state only
after fresh evidence, proven end-to-end; (11) Cross-tenant Finding/case/dependency IDs fail closed at both API
and UI; (12) Hostile model/source text cannot become executable UI content.

## 29. UI Truth Table (frozen, binding)

| Backend truth | UI may say | UI must NOT say |
|---|---|---|
| `RELIANCE_SUPPORTED` | "Reliance Supported" | "Trusted" / "100% correct" / "Verified true" |
| `RELIANCE_AT_RISK` | "Reliance At Risk" | "False" / "Wrong" / "Broken" |
| `RELIANCE_UNKNOWN` | "Reliance Unknown — insufficient evidence to assess" | "Low Risk" / neutral/grey styling |
| `IMPACT_UNKNOWN` | "Ontology impact cannot currently be determined" | "No impact" / "Low impact" |
| `NO_KNOWN_BUSINESS_IMPACT` | "No known business impact" | "No business impact exists" / "Safe" |
| `BUSINESS_IMPACT_UNKNOWN` | "Business impact cannot currently be determined" | "0 impact" / blank |
| `BUSINESS_IMPACT_IDENTIFIED` + criticality X | "Identified business impact — {process}, criticality {X}" | "{X} business impact" |
| N governed peers observed value V | "N governed peers observed {V}" | "{V} is correct" |
| Source marked authoritative | "Governed authoritative source" | "Truth" |
| `RemediationCandidate` exists | "Candidate — not established truth" | "Correct value" / "Golden value" |
| `AgentAssessment` | "Specialist Assessment" | "Fact" |
| `RecommendationType.RECOMMEND_CANDIDATE` | "Recommendation" | "Decision" |
| `RemediationAuthorization` decided | "Authorized by {principal} at {time}" | "Remediated" / "Fixed" |
| External remediation reported | "External remediation reported — awaiting fresh evidence" | "Finding resolved" / "Quality restored" |
| Finding → RESOLVED via real evaluator | "Resolved — confirmed by fresh evidence and re-evaluation on {date}" | "AI fixed it" / "Agent resolved it" |
| `NOT_EVALUABLE` | "Insufficient evidence to evaluate" | "Passed" |
| No Findings match a filter | "No Findings match this view" | "Everything looks good!" / "All clear" |

## 30. Maximum truthful claim

> CTEC Ontology Quality Intelligence provides an explainable enterprise experience for understanding where
> governed source-evidence quality affects ontology knowledge, why affected knowledge matters to business
> processes, whether available governed evidence supports reliance, how governed agents reason about
> remediation candidates, what humans authorize, and whether fresh evidence actually resolves the underlying
> quality condition.

## 31. Nonclaims (frozen)

```
UNIVERSAL TRUTH: NOT ESTABLISHED
MAJORITY = TRUTH: NO
SOURCE AUTHORITY = TRUTH: NO
AGENT = TRUTH: NO
RELIANCE_SUPPORTED = UNIVERSALLY CORRECT: NO
ZERO FINDINGS = TRUSTED: NO
UNKNOWN = LOW: NO
IMPACT_UNKNOWN = NO IMPACT: NO
NO_KNOWN_BUSINESS_IMPACT = UNIVERSAL NO IMPACT: NO
CRITICALITY = ENTITY-GLOBAL: NO
AGENT RECOMMENDATION = DECISION: NO
HUMAN AUTHORIZATION = REMEDIATION COMPLETE: NO
EXTERNAL REMEDIATION = FINDING RESOLVED: NO
TRUST SCORE: NONE
MONETARY OQI IMPACT: NONE
SOURCE WRITE-BACK: NONE
AUTONOMOUS AI REMEDIATION: NONE
```
