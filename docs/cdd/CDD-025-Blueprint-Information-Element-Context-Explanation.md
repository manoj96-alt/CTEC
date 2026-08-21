# CDD-025 — Blueprint Information-Element Context Explanation

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: PAD-001 (FROZEN, AUTHORITATIVE, Product-Internal Deterministic Capability
Boundary Clarification, unchanged — the deterministic-boundary test this CDD's entire architecture
satisfies), CDD-017 through CDD-024 (all FROZEN, unchanged, cited below by section), the existing
Gate D Ask CTEC / ontology_copilot implementation (unchanged, extended per §6)
Mandatory template: CDD Template v2.2

**Publication note**: this document reached FROZEN governance state via draft → independent
adversarial freeze review → remediation (one P1 fixed: an ambiguity in §9/§19 where the ordinary
Blueprint-not-found outcome could have been indistinguishable from a genuine
`UPSTREAM_INTEGRITY_FAILURE`, since Gate I's own `evaluate()` raises `ValidationException` rather than
returning `None` for an unresolvable Blueprint name — remediated by adding an explicit Step 0
Blueprint-resolution check in §9, performed by Gate P itself before Gate I is ever invoked) →
final freeze verification, with P0 = 0, P1 = 0, P2 = 0. It is **not yet published**: publication into
`architecture/INDEX.md` remains a separate, subsequent Product Owner authorization, matching every
prior CDD's identical multi-step discipline in this lineage (freeze and publication are always two
distinct, separately authorized steps). No implementation exists, and none is authorized by this
frozen document — a separate, subsequent Artifact Authorization companion remains required after
publication, before any file is created or modified.

## 1. Objective and business outcome

Extend the existing Ask CTEC capability (Gate D, Priority 6) with a deterministic explanation path
for governed Blueprint `InformationElementRequirement` context: given a bounded natural-language
question naming exactly one Blueprint and one Information Element, resolve the requirement, consume
Gate N's (CDD-024) already-composed context-availability result, and render a fixed-template,
non-fabricated explanation of exactly what CTEC already knows — never a judgment about whether that
context is sufficient, correct, or ready.

## 2. Governing authorities

PAD-001 (cited unchanged; its §2 item 1 deterministic-boundary test is the legal basis for this CDD
requiring no new PAD). CDD-017 (Blueprint/Obligation, unchanged, consumed for name resolution only).
CDD-020 (Gate I, unchanged, consumed only as an intermediate call Gate P itself must make to satisfy
Gate N's own input contract). CDD-021 (Gate J, unchanged, explicitly excluded from this CDD's scope,
§8). CDD-022 (FieldValueEvidence, unchanged, never directly consumed). CDD-023 (H4, unchanged,
consumed only as an intermediate call, identical role to Gate I). CDD-024 (Gate N, unchanged, the
**sole** authoritative source of this CDD's `(coverage_status, evidence_availability_status)`
semantics, §7).

## 3. Why Gate P requires its own governance

None of CDD-017 through CDD-024 authorizes any natural-language rendering, Ask CTEC integration, or
external API exposure of their own output — each explicitly reserves "Gate P" by name and explicitly
withholds consumption authorization (CDD-021 §19, CDD-023 §22, CDD-024 §21, restated verbatim). A
new, standalone CDD is the only textually honest instrument, identical reasoning to every prior
standalone CDD in this lineage.

## 4. In scope

A single new deterministic intent added to the existing Ask CTEC endpoint (§6): parse a bounded
question naming one Blueprint and one Information Element; resolve it via the existing, unmodified
`BlueprintApplicationService`; obtain Gate I's and H4's already-existing evaluation results; compose
them via Gate N's already-existing, unmodified `InformationElementContextAvailabilityApplicationService`;
render exactly one fixed-template explanation from the composed result (§11-§12).

## 5. Out of scope (binding)

Any LLM, agent, MCP client/server, embeddings, RAG, vector database, or probabilistic generation of
any kind (§17, binding, absolute). Any consumption of `GapImpactContext`/`RemediationAction` (Gate J,
§8, Product Owner decision, binding). Any cross-`InformationElementRequirement` aggregation, Blueprint-
wide summary, percentage, score, or ranking (§16, Gate K firewall). Any trust, confidence, freshness,
staleness, correctness, validity, quality, risk, severity, priority, or readiness judgment of any kind
(§16). Any direct query of `SemanticMapping`, `SourceField`, `FieldValueEvidence`, or `SourceObservation`
(§9, §15). Any modification to `Blueprint`/`ConceptRequirement`/`InformationElementRequirement`/
`RelationshipRequirement`/`Obligation` (§10). Any persistence, migration, or new authentication
mechanism (§14, §13).

## 6. Relationship to Ask CTEC / Gate D (binding)

Gate P extends the existing `POST /api/v1/ontology-copilot/ask` endpoint with a second, independent
`SupportedIntent` — it does not create a parallel API surface. The existing
`PRODUCTS_DEPENDING_ON_SUPPLIER` intent, its traversal logic, and its answer composition remain
entirely unmodified. The existing OIDC/`TrustedPrincipal`/scope/rate-limit/audit stack is reused
verbatim (§13). The existing `ontology-copilot:ask` scope is confirmed sufficient (no Keycloak change
authorized or required) since authorization is enforced at the endpoint, not per-intent.

## 7. Gate N firewall / sole composition-authority boundary (binding)

`InformationElementContextAvailabilityApplicationService.compose(...)` (CDD-024, unmodified) is the
**sole** authoritative source of `(coverage_status, evidence_availability_status)`. Gate P must not
reimplement, approximate, or bypass any part of Gate N's own composition-integrity contract (CDD-024
§10). Gate P is a *caller* of Gate N (supplying Gate N's required `coverage_result` and
`evidence_availability_results` parameters via its own calls to Gate I and H4, §9) — it does not, and
cannot, modify Gate N itself.

## 8. Gate J exclusion (binding, Product Owner decision)

`GapImpactContext` and `RemediationAction.REVIEW_SEMANTIC_MAPPING` (CDD-021) are **not** consumed by
this CDD. No import of `gap_impact_remediation.py` anywhere in this CDD's authorized artifact set. A
later, separately-authorized extension may allow Ask CTEC to explain Gate J's structural/remediation
context; this CDD does not design, name, or imply that extension's architecture.

## 9. Exact input contract (binding)

For one question, Gate P resolves exactly one `(blueprint_name, information_element_name)` pair to
one `InformationElementRequirement`, then performs exactly:
0. `BlueprintApplicationService.get_approved_by_name(blueprint_name)` (unmodified) — once, **before**
   any other step. If this returns `None`, Gate P MUST return `BLUEPRINT_NOT_FOUND` (§19) immediately
   and MUST NOT proceed to step 1. This step exists precisely so that the ordinary "no such Approved
   Blueprint" case is never routed through Gate I's own internal resolution (step 1 below) — see the
   binding disambiguation in §19.
1. `SemanticCoverageEvaluationApplicationService.evaluate(blueprint_name=..., tenant_id=...)` (Gate I,
   unmodified) — once. (Gate I internally re-resolves the Blueprint by name as part of its own
   unmodified contract; by construction this can only fail here in the narrow race window where the
   Blueprint's Approved status changed between step 0 and step 1 within the same request — see §19.)
2. `InformationElementEvidenceAvailabilityApplicationService.evaluate(coverage_result=...)` (H4,
   unmodified) — once, using step 1's result.
3. `InformationElementContextAvailabilityApplicationService().compose(coverage_result=..., evidence_availability_results=...)`
   (Gate N, unmodified) — once, using steps 1-2's results.
4. Locate the single composed result matching the resolved `information_element_requirement_id`.

No independent H2/`SemanticMapping`/`SourceField`/`FieldValueEvidence` query at any point (§15).

## 10. Blueprint resolution boundary (binding)

Blueprint resolution reuses `BlueprintApplicationService.get_approved_by_name(blueprint_name)`
(unmodified, CDD-017/CDD-020 precedent) exactly. Information-Element resolution matches
`element_name` (`CanonicalName.value`) via **exact string equality** (no fuzzy matching, no
normalization beyond the identical `" ".join(text.strip().split())` whitespace-collapse convention
`intent.py` already applies to question text) against every `InformationElementRequirement` across
every `ConceptRequirement` in the resolved Blueprint. Zero matches → `INFORMATION_ELEMENT_NOT_FOUND`
(§19). More than one match (a name colliding across concepts) → `INFORMATION_ELEMENT_AMBIGUOUS`
(§19) — never an arbitrary first-match selection. This CDD introduces no modification to `Blueprint`,
`ConceptRequirement`, `InformationElementRequirement`, `RelationshipRequirement`, or `Obligation`.
`Obligation` is read and passed through only — never reinterpreted as priority, severity, readiness,
or risk (§16).

## 11. Exact output contract (binding)

One result per question, containing exactly:
- `status: GatePAskStatus` (§19)
- `blueprint_id: UUID`, `blueprint_version_number: int`
- `information_element_requirement_id: UUID`
- `information_element_name: str`
- `obligation: Obligation`
- `coverage_status: CoverageStatus | None` (populated only when `status is ANSWERED`)
- `evidence_availability_status: EvidenceAvailabilityStatus | None`
- `answer: str`
- `reason: str | None`

No `tenant_id` field (call-scoped only, matching every prior result-type convention in this lineage).
No field beyond this list — no `trust_score`, `confidence_score`, `readiness`, `risk_score`, or
equivalent, without explicit Product Owner re-approval.

## 12. Natural-language rendering contract (binding)

Rendering is template-only, one fixed sentence per governed fact, each traceable 1:1 to a field in
§11 — never free-text generation, never inference. Approved template vocabulary (binding, exact):
- `MAPPED` → "CTEC has an Approved semantic mapping for this requirement."
- `UNMAPPED` → "CTEC does not currently have an Approved semantic mapping for this requirement."
- `EVIDENCE_PRESENT` → "Governed non-empty evidence has been observed for the resolved SourceField."
- `EVIDENCE_EMPTY` → "Governed evidence has been observed for the resolved SourceField, but it is
  empty."
- `NO_EVIDENCE` → "No governed evidence has been observed for the resolved SourceField."
- `evidence_availability_status is None` (i.e. `coverage_status is UNMAPPED`) → "Evidence
  availability is not applicable, since no mapping exists to resolve a SourceField from."

Templates MUST NOT be composed, concatenated, or reworded to produce or imply: trusted/untrustworthy,
confident/unconfident, fresh/stale, correct/incorrect, valid/invalid, complete/incomplete, high/low
quality, high/low risk, severity, priority, ready/not ready, satisfied/unsatisfied, blocker, critical,
or failed.

## 13. Tenant / auth / API boundary (binding)

`TrustedPrincipal.tenant_id` is the sole tenant source, identical to the existing router's own
discipline — never accepted from the request body. Existing OIDC → `TrustedPrincipal` → scope check
(`ontology-copilot:ask`, unchanged) → rate limit → security audit stack reused verbatim; no new
authentication mechanism, scope, or Keycloak configuration is authorized. This CDD extends the
existing `POST /api/v1/ontology-copilot/ask` endpoint with a new intent — no new route is authorized
or required at the governance level; exact request/response schema extension is deferred to the
Artifact Authorization.

## 14. Persistence / migration boundary (binding)

None. Gate P is read-only and ephemeral — it persists nothing, migrates nothing, and owns no ORM
model, table, or column. Confirmed by direct repository inspection: none of Gate I, H4, or Gate N
persist anything either; Gate P inherits the identical justification one layer further.

## 15. Raw evidence / SourceObservation / FieldValueEvidence firewall (binding)

Zero direct dependency on `SourceObservation` or `FieldValueEvidence` — no import, no query, at any
point in this CDD's authorized artifact set. Gate P consumes only H4's and Gate N's already-governed
classifications. No "latest," "best," "winning," "freshest," or "highest-confidence" evidence-selection
logic of any kind is authorized — that ranking, if it were ever legitimate, belongs exclusively to H4
(CDD-023), which already declines to perform it.

## 16. Gate K firewall (binding, load-bearing)

Gate P operates on exactly one `InformationElementRequirement` per question — no cross-element
aggregation, no Blueprint-wide summary, no coverage/completeness percentage, no readiness score, no
ranking, no prioritization, in any artifact, in any form. Explicit non-equivalences (binding):
`REQUIRED`+`MAPPED`+`EVIDENCE_PRESENT` ≠ READY/TRUSTED/VALID/COMPLETE/SATISFIED.
`REQUIRED`+`UNMAPPED` ≠ BLOCKER/CRITICAL/HIGH PRIORITY/FAILED. `Obligation` is passthrough only (§10)
and never gates, weights, or otherwise influences the rendered explanation's content beyond appearing
as its own reported field.

## 17. LLM / agent / MCP firewall (binding, absolute)

No LLM provider integration (OpenAI, Anthropic, Gemini, or any other), no model selector, no model
registry, no model authorization/policy, no prompt construction, no embeddings, no RAG, no vector
database, no probabilistic natural-language generation, no agent framework, no tool execution, no MCP
client, no MCP server, no autonomous reasoning of any kind is authorized anywhere in this CDD's scope.
The structured output contract (§11) is deliberately self-contained so that a future, separately-
governed LLM-backed capability could consume it without requiring this CDD's own redesign — this CDD
does not name, design, or imply that future capability's architecture in any way.

## 18. Security considerations

No prompt-injection surface exists (no LLM, §17). The only external-facing change is a new intent on
an already-hardened, already-authenticated endpoint — no new attack surface beyond what the existing
Ask CTEC endpoint already carries. Question-length bound reused from the existing `AskRequest` schema
convention (`max_length=500`) unless the Artifact Authorization determines a narrower bound is
warranted for the new intent's own regex family.

## 19. Failure semantics (binding)

```
GatePAskStatus:
  ANSWERED
  UNSUPPORTED_QUESTION
  BLUEPRINT_NOT_FOUND
  INFORMATION_ELEMENT_NOT_FOUND
  INFORMATION_ELEMENT_AMBIGUOUS
  UPSTREAM_INTEGRITY_FAILURE
```

Every non-`ANSWERED` status MUST return `coverage_status = None`, `evidence_availability_status =
None`, and a machine-readable `reason` code — never a fabricated answer.

`BLUEPRINT_NOT_FOUND` is triggered **exclusively** by step 0 of §9 (`BlueprintApplicationService.get_approved_by_name`
returning `None`) — this is the ordinary, expected "no such Approved Blueprint" outcome, not an
integrity violation, and MUST be distinguished from `UPSTREAM_INTEGRITY_FAILURE` below.

`UPSTREAM_INTEGRITY_FAILURE` covers any `ValidationException` raised by Gate I, H4, or Gate N during
steps 1-4 of the pipeline (§9) — including the narrow race condition where step 0's Blueprint
resolution succeeds but Gate I's own internal re-resolution at step 1 subsequently fails (e.g. the
Blueprint's Approved status changed between the two calls within the same request). It MUST propagate
as this explicit status, never silently collapse into `UNMAPPED`, `NO_EVIDENCE`, `BLUEPRINT_NOT_FOUND`,
or any other classification.

## 20. Determinism (binding)

For identical Blueprint state, identical persisted evidence, and identical question text, Gate P MUST
produce an identical result. Inherited for free from Gate I/H4/Gate N's own already-proven
determinism plus a deterministic (non-fuzzy) name-resolution rule (§10).

## 21. Acceptance scenarios (minimum)

A. "Supplier Legal Name" in the canonical Blueprint → `ANSWERED`, `MAPPED` + `EVIDENCE_PRESENT`,
   rendered explanation contains no trust/correctness/completeness/readiness claim — proven against
   the existing H3/CDD-022/H4 demo fixture, no new seeder.
B. "Risk Event Severity" → `ANSWERED`, `UNMAPPED` + `None`, rendered explanation states no mapping
   exists and evidence availability is not applicable — contains no "missing data"/"bad data"/
   "invalid"/"high risk"/"critical"/"not ready"/"failed" claim.
C. Unknown Information Element name → `INFORMATION_ELEMENT_NOT_FOUND`.
D. Unsupported question phrasing → `UNSUPPORTED_QUESTION`, matching existing Ask CTEC behavior
   exactly.

## 22. Candidate implementation-layer placement (governance-level only)

Extends the existing `backend/app/domain/ontology_copilot/` and `backend/app/application/ontology_copilot_api.py`
artifacts rather than a parallel package — exact file/class boundaries deferred entirely to the
future Artifact Authorization.

## 23. Non-claims

This CDD does not authorize: any LLM/agent/MCP capability (§17); any Gate J consumption (§8); any
cross-element aggregation or Gate K capability (§16); any trust/confidence/freshness/quality/risk
judgment of any kind; any new authentication mechanism or Keycloak change (§13); any persistence or
migration (§14); any modification to Blueprint, Gate I, H4, Gate N, or Gate J; the implementation
itself (deferred to a separate, subsequent Artifact Authorization).

## 24. Rollback

Backend-only, additive, no schema/migration — no rollback risk beyond reverting the new intent's code
path.

## 25. Compatibility

No breaking change to the existing `PRODUCTS_DEPENDING_ON_SUPPLIER` intent, its router, or its
schema — this CDD is purely additive to the existing Ask CTEC surface.

## 26. Observability and performance

Not applicable at this architecture-governance stage; deferred to implementation.

## 27. Numbered architecture baseline determination

No new numbered architecture baseline required — follows the identical non-baseline-tracked
`architecture/INDEX.md` publication pattern used by CDD-011 through CDD-024.

## 28. Authorization

**GOVERNANCE FROZEN — NOT YET PUBLISHED.** This document is Version 1.0 FROZEN, Status: FROZEN,
reached via draft → independent adversarial freeze review → remediation (§9/§19 Blueprint-not-found
disambiguation) → final freeze verification, with P0 = 0, P1 = 0, P2 = 0 confirmed.

**Publication is a separate, not-yet-authorized step.** Freezing this document's content is distinct
from publishing it into `architecture/INDEX.md` — every prior CDD in this lineage treated freeze and
publication as two separately authorized turns, and this document follows the identical discipline: it
must not be committed, pushed, or added to `architecture/INDEX.md` until a separate Product Owner
publication authorization is given.

No implementation exists, and none is authorized by this frozen document. A separate, subsequent
Artifact Authorization companion remains required after publication, before any file is created or
modified. Gate I, H4, Gate N, and Gate J remain entirely outside this document's authority and remain
unchanged.
