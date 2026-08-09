# RFC-014 — Cognitive Capability Integration, Handoff, and Transaction Policy

Version: 1.1 DRAFT
Status: RELEASE CANDIDATE
Current: NO
Authority: NON-AUTHORITATIVE — PENDING REGISTRY RELEASE
Scope: Supplier-risk / single-source-versus-dual-source vertical slice only

## 1. Purpose

This draft defines the minimum cross-capability policy needed to integrate the existing Cognitive Engine capabilities for one bounded flow:

`Supplier risk event → ERM → SRM → ASM → KRM → DRM → GRM → governance result for a sourcing recommendation`

It does not authorize implementation. It does not define a universal integration platform, product API, user interface, distributed runtime, new business entity, or new persistence model.

## 2. Governing authorities

This draft must remain consistent with the current frozen authorities registered in `architecture/INDEX.md`, including EAH-001, RFC-010, RFC-011, RFC-013, CAM-001, ERM-001 v2.2, SRM-001 v2.2, ASM-001 v2.2, AEM-001 v1.1, KRM-001 v1.4, DRM-001 v1.2, GEM-001 v1.1, GRM-001 v1.2, EIC-001 v1.2, EOM-001 v1.2, ESM-001 v1.2, PAD-001 v1.4, and CDD-010 v1.3.

RFCs govern cross-capability boundaries. Each Business Capability Specification remains the sole authority for semantics inside its assigned capability. RFC-014 must not redefine those semantics.

## 3. Decisions

All decisions in this section are **bounded MVP semantics** for the supplier-risk / single-source-versus-dual-source vertical slice. They establish no reusable enterprise-wide risk, sourcing, or integration vocabulary.

### 3.0 Source Observation contract

`SourceObservation` is a governed evidence-and-provenance integration contract. It is not a canonical business entity, CEO extension, or new persistence model. It contains exactly:

- Observation Identifier;
- Source System Reference and Source Record Reference;
- Subject Type and Subject Identifier;
- Observation Type and Observation Value or Severity;
- Observed Timestamp and Received Timestamp;
- Evidence Reference; and
- Schema Version.

The contract preserves an authorized observation supplied at the enterprise boundary. It neither establishes an Assertion nor grants institutional standing. The Source System owns `observed_at`; the receiving boundary owns `received_at`. Both are timezone-aware UTC. SourceObservation resolves content access for this slice without adding a payload attribute to Source Object. Its relationship to the canonical Source Object reference requires an explicit compatibility check before approval.

### 3.1 Integration envelope ownership and versioning

CIM-001 owns the structure and meaning of the Cognitive Integration Envelope for this vertical slice. The envelope is an integration contract, not a canonical entity or persistent business artifact.

Every envelope carries an `integration_contract_version`. A running execution uses one immutable version from admission through completion. A version change that modifies required fields, interpretation, gating, or handoff compatibility requires a governed CIM-001 revision. Runtime protocol versioning remains owned by EIC/PAD and is not replaced by the integration-contract version.

The runtime owns only governed runtime metadata and opaque payload transport. A capability adapter owns validation of its CIM-001 step contract and translation to its capability's already-governed interface. The runtime must not inspect or transform business content.

### 3.2 Ordered execution and outcome gates

The only permitted order is ERM → SRM → ASM → KRM → DRM → GRM. No step may be bypassed.

| Step | Outcome that permits progression | Outcomes that stop progression without technical failure |
|---|---|---|
| ERM | Resolved | Possible Resolution; Unresolved |
| SRM | Resolved | Possible Resolution; Unresolved |
| Pre-ASM evidence determination | Complete and non-conflicting | Indeterminate |
| ASM | Established | Candidate; Rejected |
| KRM | Institutionalized | Candidate; Rejected |
| DRM | Recommended | Candidate; Rejected |
| GRM | Terminal for this integration | All governed outcomes are returned as the final governance result |

A stopping business outcome is authoritative business output from the capability that produced it. It is not converted into another capability's input and is not reported as a runtime failure.

For this bounded MVP, missing or conflicting evidence produces `INDETERMINATE`. ASM-001 v2.2 permits only Established, Candidate, and Rejected; therefore `INDETERMINATE` cannot silently become an Assertion Outcome. The minimum amendment must either add that outcome to ASM or govern it as a pre-ASM integration determination that stops before an Assertion Record is created.

The bounded supplier-risk proposition is: **at the Assertion's effective time, the identified supplier has an active risk condition supported by governed Source Observations.** The subject is the ERM-resolved supplier, the semantic interpretation is produced by SRM, the effective time is the caller-provided provenance-bearing business time, and the evidence is the governed SourceObservation set plus the ERM/SRM records. Predicate and object references must resolve to existing governed canonical vocabulary; this draft does not create them.

### 3.2.1 Sourcing-status determination

Sourcing status is evaluated for exactly one Material, one Facility or Region scope, and one Effective Time:

- `SINGLE_SOURCE`: exactly one qualified, approved, contractually eligible supplier with usable capacity.
- `DUAL_SOURCE`: two or more such suppliers.
- `NO_QUALIFIED_SOURCE`: zero such suppliers.
- `INDETERMINATE`: required evidence is missing or conflicting.

Qualification, approval, contractual eligibility, usable capacity, Material, Facility, and Region retain their authoritative meanings. RFC-014 does not infer them from a supplier count or invent missing standing.

### 3.2.2 Closed recommendation vocabulary and bounded rules

The only recommendation values are:

- `CONTINUE_MONITORING`
- `QUALIFY_SECOND_SOURCE`
- `ACTIVATE_APPROVED_SECOND_SOURCE`
- `ESCALATE_FOR_HUMAN_REVIEW`
- `NO_AUTOMATED_RECOMMENDATION`

The bounded rules are:

| Condition | Recommendation |
|---|---|
| Low risk with adequate sourcing coverage | `CONTINUE_MONITORING` |
| Material risk with `SINGLE_SOURCE` | `QUALIFY_SECOND_SOURCE` |
| High or Critical risk with an operationally ready second source | `ACTIVATE_APPROVED_SECOND_SOURCE` |
| Missing/conflicting evidence or exceptional policy conditions | `ESCALATE_FOR_HUMAN_REVIEW` |
| Governance rejection or inability to form a valid decision | `NO_AUTOMATED_RECOMMENDATION` |

`Material risk`, `adequate sourcing coverage`, `High`, `Critical`, `operationally ready`, and `exceptional policy conditions` must be supplied by a versioned governed policy. Adapters may not define their thresholds.

When Governance rejects a previously produced DRM recommendation, `NO_AUTOMATED_RECOMMENDATION` is the final integration recommendation. The prior immutable Decision Evaluation Record remains unchanged and traceable.

Recommendations never directly execute supplier, sourcing, contractual, operational, or financial actions.

### 3.2.3 GRM standing

The bounded integration standing vocabulary is:

- `APPROVED`: actionable by an authorized downstream human or system.
- `CONDITIONALLY_APPROVED`: actionable only after every recorded condition is verified as satisfied.
- `PENDING_REVIEW`, `REJECTED`, and `INDETERMINATE`: non-actionable.

These are integration-result standings, not replacements for the frozen GRM outcomes Compliant, Non-Compliant, Exception Granted, and Requires Review. A minimum GRM clarification must govern the exact mapping and the representation/verification of recorded conditions before this standing can be produced. No adapter may infer the mapping.

### 3.3 Business stop versus technical runtime failure

A **business stop** occurs when a governed determination or capability outcome does not pass the next-step gate. If a capability was invoked, its successfully created immutable record is preserved. The integration result identifies the terminal gate/capability, business result, and produced record references.

A **technical runtime failure** occurs when the current step cannot validate or execute its contract, cannot atomically persist its authorized records/projections, violates concurrency controls, or encounters an unexpected technical fault. The adapter returns a safe classified failure to the runtime; ESM records `Failed` in accordance with its authority.

Business rejection must never be mapped to `Failed`. Technical failure must never be represented as a business outcome.

EOM-001 v1.2 currently states that incomplete required capability coordination produces external `Failed`, while ESM exposes only Accepted, Executing, Completed, and Failed. A minimum EOM clarification is required to authorize a successful business stop as `Completed`; otherwise this section conflicts with the frozen runtime authority.

### 3.4 Transaction boundaries and partial persistence

Each capability step owns one capability-local transaction. Within that transaction, creation of the immutable evaluation record, its evidence/reference rows, and any externally determined currentness/history projection changes required by that capability must succeed or fail atomically.

A successful step commits before the next step begins. There is no cross-capability database transaction. A later failure does not roll back, delete, mutate, or compensate previously committed immutable records. Previously committed records retain their business and provenance standing.

No integration-level persistence table, saga, outbox, compensation record, or distributed transaction is authorized by this draft.

### 3.5 Replay after partial execution

CDD-010 idempotency remains `(protocol_version, request_identifier)` with atomic process-local first admission.

- Identical replay in the same runtime process returns the existing execution and starts no work.
- Different-payload replay returns idempotency conflict and starts no work.
- Active and terminal replay return existing process-local execution state.
- A failed execution is not resumed.
- Retrying after failure requires a new request identifier and therefore a new execution.
- A new execution may create new immutable evaluation records; it must not overwrite or mutate records committed by the failed execution.
- Reuse of prior successful step results, durable resumption, distributed idempotency, and process-restart recovery are outside scope and require separate governance.

### 3.6 Authenticated authority and evidence propagation

Authentication and authorization occur outside the Cognitive Engine in accordance with PAD. The integration receives only a verified authority-context reference from the trusted invocation boundary. It must not authenticate a person, infer authority, or treat an opaque caller identifier as business authority.

Acceptance Evidence is governed by AEM-001 and produced under Governance Authority in accordance with RFC-013. Exception Authorization is governed by GEM-001. The integration may propagate their validated identifiers and governed fields to the capability that consumes them. It must not create, approve, fabricate, weaken, or reinterpret either artifact.

Acceptance Evidence may reach KRM only when supplied through an authenticated authorized action or an already-governed authority source. Exception Authorization may reach GRM only under the same rule.

`AuthorityContext` is an immutable trusted integration contract propagated separately from the opaque business payload. It contains exactly:

- authenticated Principal Identifier and Principal Type;
- Tenant or Organization Reference;
- Roles and Scopes;
- Authorization Decision and Authorization Reference;
- Trust Source;
- delegation details when applicable;
- Request Identifier and Correlation Identifier;
- Issued Timestamp and Expiration Timestamp; and
- Schema Version.

Caller claims embedded inside the business payload are never authoritative. AuthorityContext contains no credential secret. Its timestamps are timezone-aware UTC. Because EIC/CDD-010 currently define only runtime metadata plus one opaque payload, a minimum invocation/runtime contract clarification is required before AuthorityContext can be transported separately.

### 3.6.1 Timestamp ownership

- Runtime owns `admitted_at`.
- Each capability owns its `started_at` and `completed_at`.
- Source systems own SourceObservation `observed_at`.
- The receiving boundary owns SourceObservation `received_at`.
- Caller-provided effective timestamps remain provenance-bearing business inputs and are never rewritten as production timestamps.
- Every trusted timestamp is timezone-aware UTC.

Existing BCS `Produced Timestamp` remains the capability-owned record-creation timestamp. A minimum runtime contract clarification is required because CDD-010 does not currently expose `admitted_at` or step timing metadata.

### 3.7 Final result and record-reference retrieval

The integration result is a process-local execution result associated with the EIC Execution Identifier. It contains:

- correlation and request identifiers;
- integration-contract version;
- terminal capability and integration disposition;
- produced immutable record references accumulated through the completed steps;
- the DRM recommendation and outcome when produced; and
- the GRM outcome and Governance Attestation when produced.

The result does not create a new business record. It must not expose an assertion, knowledge item, recommendation, or attestation that the relevant capability did not produce.

CDD-010 currently exposes execution state but not interpreted business results. A future CDD may authorize a result-retrieval port and adapters after CIM-001 is approved. Product API and durable result persistence remain outside scope.

### 3.8 Error classification and safe observability

Adapters classify technical faults into these integration-level categories:

1. Contract Validation Failure
2. Authority Validation Failure
3. Persistence or Concurrency Failure
4. Capability Execution Failure
5. Unexpected Technical Failure

These are technical integration classifications, not business outcomes and not new canonical concepts. External error details must be safe and stable. Logs and metrics may contain execution, correlation, request, capability, record-reference, error-category, and safe error-code values. They must not contain opaque payload bytes, secrets, source rows, authority credentials, evidence contents, business narratives, or stack traces in externally visible responses.

## 4. Explicit exclusions

RFC-014 does not authorize:

- a universal integration framework;
- production adapters or service wiring;
- a product-facing API or UI;
- distributed execution, messaging, or durable orchestration;
- new persistence structures;
- new CEO entities, attributes, or relationships;
- business semantics outside the explicitly authorized bounded MVP rules in this draft;
- parsing EDT-001 as if it were the canonical model;
- bypass of ERM or SRM to create an Assertion;
- automatic creation of Acceptance Evidence or Exception Authorization; or
- calling a recommendation approved, actionable, or governed beyond what GRM explicitly establishes.

## 5. Conformance rules

An implementation conforms only if it:

1. executes the six capabilities in the fixed order;
2. applies every outcome gate exactly;
3. preserves immutable records and capability-local transactions;
4. distinguishes business stops from technical failures;
5. propagates only values authorized by CIM-001 and the governing BCS;
6. preserves provenance and produced-record references;
7. keeps runtime payloads opaque outside adapters;
8. enforces CDD-010 process-local replay semantics; and
9. exposes no unsafe payload or authority information through observability.

## 6. Architecture drift check

- New business entity introduced: No.
- Existing entity modified: No.
- Relationship changed: No.
- Canonical attribute invented: No.
- RFC violated: No known violation; this draft is not authoritative.
- Architecture layer bypassed: No.
- Technology outside the authoritative technology architecture introduced: No.

## 7. Frozen-authority conflicts and minimum amendments

RFC-014 cannot be approved until the following exact conflicts are resolved through governed clarification releases:

1. **ASM-001 v2.2:** only Established, Candidate, and Rejected are authorized. Minimum amendment: govern `INDETERMINATE` as a pre-ASM integration result, or explicitly add it to ASM through a BCS clarification. The former avoids changing the BCS and is preferred.
2. **EOM-001 v1.2:** incomplete required coordination is `Failed`. Minimum amendment: distinguish successful outcome-gated completion from technical partial failure and permit ESM `Completed` for the former.
3. **EIC-001 v1.2 / CDD-010 v1.3:** invocation and step envelopes contain runtime metadata plus opaque payload only. Minimum amendment: authorize a separately propagated immutable AuthorityContext and runtime-owned `admitted_at`, without making either business payload.
4. **GRM-001 v1.2:** GRM outcome vocabulary differs from the new integration standing vocabulary and has no recorded-condition verification contract. Minimum amendment: define the exact outcome-to-standing mapping and condition verification boundary without transferring Governance Authority into Governance Evaluation.
5. **DRM-001 v1.2:** free-text recommendation permits the closed vocabulary, but the bounded rules and sourcing-status inputs are not current DRM authority. Minimum clarification: recognize RFC-014/CIM-001 as the cross-capability policy for this slice; do not generalize the vocabulary.
6. **Canonical Source Object:** it has no payload attribute. Minimum clarification: approve SourceObservation as a noncanonical evidence/provenance integration contract linked by Source System and Source Record references; do not modify CEO or the Physical Model.
7. **Canonical vocabulary availability:** review found no frozen value-level definition or identifier for the required Relationship Type and Institutional Concept representing `active risk condition`. The assertion cannot be implemented until existing governed values are cited or separate CEO vocabulary governance approves them.

Until these decisions are governed, RFC-014 remains DEVELOPMENT / NON-AUTHORITATIVE and CDD-011 remains blocked.

### 7.1 Proposed amendment dependencies

The review drafts are ASM-001 v2.3, EOM-001 v1.3, EIC-001 v1.3, CDD-010 Trusted Runtime Control Metadata Clarification v1.0, GRM-001 v1.3, CVR-001 v1.0, and DRM-001 v1.3. These references are proposals only. None is an authoritative dependency until separately approved, published, registered, and included in a governed architecture baseline.
