# CIM-001 — Cognitive Integration Contract Model

Version: 1.1 DRAFT
Status: DEVELOPMENT
Current: NO
Authority: NON-AUTHORITATIVE
Scope: Supplier-risk / single-source-versus-dual-source vertical slice only

## 1. Purpose and boundary

CIM-001 defines a proposed field-level contract for the bounded integration governed by draft RFC-014. It is not an implementation authorization, canonical model, database model, universal message format, or product API.

No field in this draft creates business meaning. A field that lacks frozen semantic authority is marked `UNRESOLVED` and cannot be implemented.

The supplier-risk, sourcing-status, recommendation, standing, SourceObservation, AuthorityContext, and timestamp rules below are **bounded MVP semantics authorized for this vertical slice only**. They are not universal canonical vocabulary.

## 2. Value-origin classification

Every non-runtime value has exactly one origin classification:

| Classification | Meaning |
|---|---|
| Already governed | Meaning and permitted use exist in a current frozen authority. |
| Caller-supplied | Provided by the trusted caller and validated as a governed reference/value. |
| Deterministically derived | Reproducibly computed from governed inputs under an approved contract; no inference of new business meaning. |
| Policy-supplied | Supplied by an identified, versioned governed policy. |
| Authorized-human-supplied | Supplied by an authenticated actor with governed authority. |
| Unresolved — BCS clarification required | No frozen authority currently defines the value or its use. |

## 3. Integration envelope

The envelope wraps the runtime's opaque payload. Adapters may decode only the version of CIM-001 they implement.

| Field | Cardinality | Origin | Provenance and rule |
|---|---:|---|---|
| `integration_contract_version` | 1 | Already governed after CIM approval | Immutable for the execution; validated at first adapter. |
| `protocol_version` | 1 | Already governed / caller-supplied | EIC/PAD request; preserved unchanged by every step. |
| `request_identifier` | 1 | Already governed / caller-supplied | EIC request and CDD-010 idempotency key component. |
| `correlation_identifier` | 1 | Already governed / caller-supplied | EIC request; preserved unchanged. |
| `session_identifier` | 0..1 | Already governed / caller-supplied | PAD protocol identifier; no business meaning. |
| `execution_identifier` | 1 after admission | Already governed / deterministically derived | Assigned by EIC runtime admission; preserved unchanged. |
| `authority_context` | 1 | Caller-supplied from trusted boundary | Separate immutable contract defined in Section 4; never part of opaque business payload. Requires EIC/CDD-010 clarification. |
| `admitted_at` | 1 after admission | Deterministically derived | Runtime-owned, timezone-aware UTC admission timestamp. Requires runtime clarification. |
| `original_request` | 1 | See Section 4 | Immutable supplier-risk request. |
| `current_step_payload` | 1 | See Sections 6–11 | Exactly one step contract at a time. |
| `produced_record_references` | 0..6 | Already governed / prior capability output | Append-only accumulation of immutable record references. |

## 4. Trusted AuthorityContext schema

AuthorityContext is not a business entity or credential. Caller claims inside the opaque business payload are ignored for authority decisions.

| Field | Cardinality | Origin | Provenance and rule |
|---|---:|---|---|
| `authenticated_principal_identifier` | 1 | Caller-supplied from trusted boundary | Identity established by the Product Layer/authentication authority. |
| `authenticated_principal_type` | 1 | Caller-supplied from trusted boundary | Governed principal classification; must not be inferred from payload. |
| `tenant_or_organization_reference` | 1 | Caller-supplied from trusted boundary | Authorized scope of the invocation. |
| `roles` | 0..* | Caller-supplied from trusted boundary | Verified role claims. |
| `scopes` | 0..* | Caller-supplied from trusted boundary | Verified authorization scopes. |
| `authorization_decision` | 1 | Caller-supplied from trusted boundary | Verified decision, not recomputed by capability adapters. |
| `authorization_reference` | 1 | Caller-supplied from trusted boundary | Traceable reference to the decision. |
| `trust_source` | 1 | Caller-supplied from trusted boundary | Authority that authenticated and authorized the request. |
| `delegation_details` | 0..1 | Authorized-human-supplied | Required only for delegated authority; contains reference/scope, not credentials. |
| `request_identifier` | 1 | Already governed | Must equal runtime request identifier. |
| `correlation_identifier` | 1 | Already governed | Must equal runtime correlation identifier. |
| `issued_at` | 1 | Caller-supplied from trusted boundary | Timezone-aware UTC. |
| `expires_at` | 1 | Caller-supplied from trusted boundary | Timezone-aware UTC and later than issued time. |
| `schema_version` | 1 | Already governed after approval | Immutable AuthorityContext contract version. |

## 5. SourceObservation schema

SourceObservation is a governed evidence-and-provenance integration contract, not a canonical entity or persistence model.

| Field | Cardinality | Origin | Provenance and rule |
|---|---:|---|---|
| `observation_identifier` | 1 | Caller-supplied | Stable source-observation identifier. |
| `source_system_reference` | 1 | Caller-supplied | Existing Source System reference. |
| `source_record_reference` | 1 | Caller-supplied | Reference to the source record; may link to Source Object without extending it. |
| `subject_type` | 1 | Caller-supplied | Declared source subject classification; resolved meaning still requires ERM/SRM. |
| `subject_identifier` | 1 | Caller-supplied | Source-local subject identifier, not canonical identity. |
| `observation_type` | 1 | Caller-supplied | Source-observed type, not an Institutional Concept. |
| `observation_value_or_severity` | 1 | Caller-supplied | Source value/severity; policy interpretation occurs later. |
| `observed_at` | 1 | Caller-supplied | Source-system-owned, timezone-aware UTC. |
| `received_at` | 1 | Deterministically derived | Receiving-boundary-owned, timezone-aware UTC. |
| `evidence_reference` | 1 | Caller-supplied | Traceable evidence reference; does not itself grant governed standing. |
| `schema_version` | 1 | Already governed after approval | Immutable SourceObservation contract version. |

## 6. Supplier-risk integration request schema

| Field | Cardinality | Origin | Field-level provenance |
|---|---:|---|---|
| `risk_observations` | 1..* | Caller-supplied | SourceObservation contracts from Section 5. Missing/conflicting required observations yield `INDETERMINATE`. |
| `supplier_source_object_references` | 1..* | Caller-supplied | Existing Source Object references supporting supplier identity resolution. |
| `supplier_material_source_object_references` | 1..* | Caller-supplied | Existing Source Object references proposed as sourcing evidence; business interpretation is unresolved. |
| `business_context_reference` | 1 | Caller-supplied | Existing canonical Context reference. |
| `risk_event_effective_from` | 1 | Caller-supplied | Source-observed effective time; validation semantics require clarification. |
| `entity_resolution_policy_version` | 1 | Policy-supplied | Version accepted by ERM-001. |
| `semantic_resolution_policy_version` | 1 | Policy-supplied | Version accepted by SRM-001. |
| `assertion_policy_version` | 1 | Policy-supplied | Version accepted by ASM-001. |
| `knowledge_policy_version` | 1 | Policy-supplied | Version accepted by KRM-001. |
| `decision_policy_reference` | 1 | Policy-supplied | Governed business-policy reference accepted by DRM-001. |
| `decision_policy_version` | 1 | Policy-supplied | Version of the referenced decision policy. |
| `governance_policy_reference` | 1 | Policy-supplied | Governed business-policy reference accepted by GRM-001. |
| `governance_policy_version` | 1 | Policy-supplied | Version of the referenced governance policy. |
| `acceptance_evidence` | 0..1 | Authorized-human-supplied | AEM-001 fields/reference; required only if KRM outcome is Institutionalized. Must not be fabricated. |
| `exception_authorization` | 0..1 | Authorized-human-supplied | GEM-001 fields/reference; supplied only for Exception Granted. Must not be fabricated. |
| `material_reference` | 1 | Caller-supplied | Existing canonical Enterprise Entity reference for the specific material after required identity resolution. |
| `facility_or_region_reference` | 1 | Caller-supplied | Existing governed reference defining the sourcing scope. |
| `effective_time` | 1 | Caller-supplied | Provenance-bearing business input; timezone-aware UTC. |
| `supplier_eligibility_observations` | 1..* | Caller-supplied | Evidence for qualified, approved, contractually eligible, and usable-capacity determinations. |

## 7. Bounded MVP derived values

| Value | Allowed vocabulary/rule | Origin |
|---|---|---|
| `supplier_risk_assertion_determination` | Active risk condition at effective time, or `INDETERMINATE` for missing/conflicting evidence | Policy-supplied plus deterministically derived from governed SourceObservations |
| `sourcing_status` | `SINGLE_SOURCE`, `DUAL_SOURCE`, `NO_QUALIFIED_SOURCE`, `INDETERMINATE` | Deterministically derived using the exact qualified/approved/contractually-eligible/usable-capacity count rule |
| `recommendation` | `CONTINUE_MONITORING`, `QUALIFY_SECOND_SOURCE`, `ACTIVATE_APPROVED_SECOND_SOURCE`, `ESCALATE_FOR_HUMAN_REVIEW`, `NO_AUTOMATED_RECOMMENDATION` | Policy-supplied under RFC-014's closed rule table |
| `governance_standing` | `APPROVED`, `CONDITIONALLY_APPROVED`, `PENDING_REVIEW`, `REJECTED`, `INDETERMINATE` | Unresolved until GRM mapping clarification is approved |

No recommendation directly executes a supplier, sourcing, contractual, operational, or financial action.

## 8. Produced-record reference set

| Field | Producer | Rule |
|---|---|---|
| `enterprise_entity_resolution_record_reference` | ERM | Present after successful ERM evaluation, including business-stop outcomes. |
| `semantic_resolution_record_reference` | SRM | Present after successful SRM evaluation. |
| `assertion_record_reference` | ASM | Present after successful ASM evaluation. |
| `knowledge_evaluation_record_reference` | KRM | Present after successful KRM evaluation. |
| `decision_evaluation_record_reference` | DRM | Present after successful DRM evaluation. |
| `governance_evaluation_record_reference` | GRM | Present after successful GRM evaluation. |

References are accumulated without replacing earlier references. They carry traceability, not duplicated business provenance.

## 9. Runtime → ERM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Supporting Source Object references | Caller-supplied | Request supplier/risk source references. |
| Source names used for candidate discovery | Unresolved | Current Source Object preserves no source payload or approved business-name field. |
| Enterprise Entity candidate set | Deterministically derived | Repository query under an approved candidate-discovery contract. |
| ERM policy version | Policy-supplied | Request policy reference/version. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | ERM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |
| Human override | Authorized-human-supplied | Absent by default; permitted only under ERM-001 authority. |

### Output and gate

ERM returns the immutable Enterprise Entity Resolution Record reference, outcome, resolved Enterprise Entity reference when present, confidence, reasons, explanation, and policy version. Only `Resolved` advances. The handoff preserves the request and appends the record reference.

## 10. ERM → SRM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Enterprise Entity reference | Prior capability output | Resolved ERM record. |
| ERM record reference | Prior capability output | Produced-record set. |
| Supporting Source Object references | Caller-supplied / prior envelope | Original request. |
| Context reference | Caller-supplied | Original request. |
| Source terms | Caller-supplied / deterministically derived | Extracted from SourceObservation under its schema; remain source terms until SRM resolves meaning. |
| Institutional Concept candidate set | Deterministically derived | Concept repository query under approved semantic candidate discovery. |
| SRM policy version | Policy-supplied | Original request. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | SRM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |

### Output and gate

SRM returns the immutable Semantic Resolution Record reference, outcome, resolved Institutional Concept reference when present, confidence, reasons, explanation, and policy version. Only `Resolved` advances.

## 11. SRM → ASM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Subject Enterprise Entity reference | Prior capability output | Resolved ERM record. |
| Object Institutional Concept reference | Prior capability output | Resolved SRM record. |
| ERM and SRM evidence references | Prior capability output | Produced-record set. |
| Context reference | Caller-supplied | Original request. |
| Relationship Type reference | Policy-supplied | Existing canonical predicate representing the approved active-risk-condition proposition; existence must be verified. |
| Assertion effective date | Caller-supplied | Risk-event effective time, subject to clarification. |
| Internal assertion score inputs | Policy-supplied / deterministically derived | Bounded supplier-risk policy applied to governed SourceObservations. Missing/conflicting evidence stops pre-ASM as `INDETERMINATE`. |
| ASM policy version | Policy-supplied | Original request. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | ASM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |

### Output and gate

ASM returns the immutable Assertion Record reference, outcome, confidence, explanation, and evidence traceability. Only `Established` advances. No adapter may create an Assertion without both ERM and SRM record references.

## 12. ASM → KRM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Assertion reference | Prior capability output | Established ASM record. |
| Evaluation outcome inputs | Policy-supplied | Identified knowledge policy; exact supplier-risk rule unresolved. |
| Knowledge confidence inputs | Policy-supplied / deterministically derived | Approved knowledge policy applied to governed evidence. |
| Evaluation reasons and explanation | Deterministically derived | Policy evaluation output; must not be adapter-authored. |
| Acceptance Evidence | Authorized-human-supplied | AEM-001 artifact supplied through verified authority context. |
| Rejection explanation | Policy-supplied or authorized-human-supplied | Required only for Rejected under KRM-001. |
| Effective From | Caller-supplied / policy-supplied | Risk effective date or policy-defined effective date; selection requires clarification. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | KRM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |

### Output and gate

KRM returns the immutable Knowledge Evaluation Record reference and outcome. Only `Institutionalized` establishes Institutional Knowledge and advances. Decision consumes the Institutional Knowledge outcome, not merely an evaluation record with another outcome.

## 13. KRM → DRM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Institutional Knowledge references | Prior capability output | Institutionalized KRM outcome; repository must validate standing. |
| Recommendation | Policy-supplied | One closed RFC-014 recommendation derived from governed risk and sourcing status. |
| Business context reference | Caller-supplied | Original request. |
| Enterprise constraint references | Policy-supplied | Governed sourcing policy, if defined. |
| Decision policy reference/version | Policy-supplied | Original request. |
| Policy-satisfied indicator | Deterministically derived | Evaluation against referenced governed policy. |
| Outcome, confidence, explanation | Policy-supplied / deterministically derived | DRM evaluation of the bounded rule and Institutional Knowledge; inability to form a valid decision yields `NO_AUTOMATED_RECOMMENDATION`. |
| Effective From | Caller-supplied / policy-supplied | Selection requires clarification. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | DRM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |

### Output and gate

DRM returns the immutable Decision Evaluation Record reference, recommendation, outcome, confidence, explanation, and policy traceability. Only `Recommended` advances. DRM must not create new Knowledge or alter Knowledge.

## 14. DRM → GRM contract

### Input

| Value | Origin | Exact source |
|---|---|---|
| Governed-record reference | Prior capability output | Decision Evaluation Record reference. |
| Governed-record type | Already governed / deterministically derived | Constant identifying the governed record as a Decision Evaluation Record; exact registered token requires contract approval. |
| Governance policy reference/version | Policy-supplied | Original request. |
| Policy-satisfied and human-review inputs | Deterministically derived / policy-supplied | Governance policy evaluation. |
| Exception Authorization | Authorized-human-supplied | GEM-001 artifact; required only for Exception Granted. |
| Outcome, confidence, explanation | Policy-supplied / deterministically derived | GRM policy evaluation. |
| Effective From | Policy-supplied | Governance policy effective date. |
| Capability `started_at` / `completed_at` / Produced Timestamp | Deterministically derived | GRM-owned, timezone-aware UTC. Produced Timestamp retains its BCS meaning as record creation time and must fall within the capability interval. |

### Output

GRM returns the immutable Governance Evaluation Record reference, Governance Outcome, Governance Attestation, confidence, explanation, and policy traceability. This is terminal. Governance standing may be emitted only after the frozen GRM clarification defines the exact mapping and conditional-verification contract.

## 15. Final governance-result schema

| Field | Cardinality | Origin | Rule |
|---|---:|---|---|
| `execution_identifier` | 1 | Already governed | EIC execution reference. |
| `request_identifier` | 1 | Already governed | Original request. |
| `correlation_identifier` | 1 | Already governed | Original request. |
| `integration_contract_version` | 1 | Already governed after approval | Version executed. |
| `terminal_capability` | 1 | Deterministically derived | Last capability that successfully produced an outcome. |
| `integration_disposition` | 1 | Deterministically derived | `CHAIN_COMPLETED` or `STOPPED_BY_BUSINESS_OUTCOME`; technical failure remains ESM `Failed`. This is technical metadata, not a business outcome. |
| `produced_record_references` | 1 | Prior capability outputs | All records produced before termination. |
| `decision_recommendation` | 0..1 | Prior capability output | Present only if DRM produced it. |
| `decision_outcome` | 0..1 | Prior capability output | Present only if DRM produced it. |
| `governance_outcome` | 0..1 | Prior capability output | Present only if GRM completed. |
| `governance_attestation` | 0..1 | Prior capability output | Business outcome established by GRM; not an independently persisted artifact. |
| `governance_standing` | 0..1 | Prior capability output after clarification | One bounded standing value; absent until GRM mapping is approved. |
| `governed_sourcing_recommendation` | 0..1 | Prior DRM/GRM output | Closed recommendation plus GRM standing. Governance rejection returns `NO_AUTOMATED_RECOMMENDATION` without mutating the prior DRM record. It never executes an action. |

## 16. Error contract

| Category | Trigger | Runtime effect | Safe result |
|---|---|---|---|
| Contract Validation Failure | Envelope or step contract invalid | Failed | Category, safe code, capability, correlation/execution references. |
| Authority Validation Failure | Required authority/evidence invalid or absent | Failed | No credential or evidence content. |
| Persistence or Concurrency Failure | Capability-local atomic write fails | Failed | No database details. |
| Capability Execution Failure | Capability raises a governed technical exception | Failed | Sanitized adapter code only. |
| Unexpected Technical Failure | Unclassified technical fault | Failed | Generic safe code; internal diagnostics protected. |

A valid business outcome that fails an outcome gate is returned through the final-result schema, never through this error contract.

## 17. Frozen-authority compatibility findings

1. ASM-001 v2.2 has no `INDETERMINATE` outcome. CIM uses it as a pre-ASM determination pending approval of that minimum clarification.
2. EOM-001 v1.2 maps incomplete required coordination to `Failed`; outcome-gated successful completion requires an EOM clarification.
3. EIC-001/CDD-010 do not carry AuthorityContext separately or expose `admitted_at`; their contracts require clarification before implementation.
4. GRM-001 v1.2 outcomes do not directly equal the bounded integration-standing values and do not define condition verification; a GRM clarification is required.
5. Existing canonical Relationship Type and Institutional Concept references for the supplier-risk proposition must be verified; CIM does not create them.

## 18. Architecture drift check

- New business entity: No.
- Existing entity or attribute changed: No.
- Canonical relationship changed: No.
- New persistence model: No.
- Business semantic value invented: No; unresolved values are explicitly blocked.
- Layer bypass: No.
- Technology introduced: No.

## 19. Approval blockers

CIM-001 cannot become authoritative until the five compatibility findings in Section 17 have governed resolutions and the resulting schema is reviewed against the six capability interfaces.

The proposed review dependencies are ASM-001 v2.3, EOM-001 v1.3, EIC-001 v1.3, CDD-010 Trusted Runtime Control Metadata Clarification v1.0, GRM-001 v1.3, CVR-001 v1.0, and DRM-001 v1.3. Their presence in this draft does not mark any finding resolved.
