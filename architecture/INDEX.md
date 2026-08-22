# CTEC Architecture Release Registry

This file is the sole authoritative registry for released CTEC architecture. Engineering work must resolve architecture documents through this registry, never from personal Downloads folders, email attachments, unmerged branches, or legacy documentation paths.

## Registry control

| Registry Version | Status | Current | Authority | Approval |
|---:|---|---|---|---|
| 1.9 | FROZEN | YES | AUTHORITATIVE | Gate F architecture release (RFC-017 / PAD-003 / CDD-015) |

## Release policy

- `architecture/released/v1.11/` is the current bounded amendment baseline and inherits unchanged authorities from v1.10.
- `architecture/released/v1.0/` and `architecture/released/v1.1/` are retained for historical traceability only.
- A document is authoritative only when it appears in the Authoritative artifacts table with lifecycle status `FROZEN` and authority `AUTHORITATIVE`.
- Superseded documents must not be used for implementation.
- A new or revised document becomes authoritative only through an approved registry update in the same commit that adds the released artifact.
- Every baseline must have a complete Architecture Release Manifest. Regeneration and checksum verification are mandatory whenever an architecture artifact is added, superseded, or frozen.
- Each artifact has exactly one lifecycle status: `DEVELOPMENT`, `FROZEN`, `SUPERSEDED`, or `HISTORICAL`. Currentness, authority, disposition, and baseline membership are separate fields and are not lifecycle statuses.
- Valid governance combinations are exclusively: `FROZEN + YES + AUTHORITATIVE`, `DEVELOPMENT + NO + NON-AUTHORITATIVE`, `SUPERSEDED + NO + NON-AUTHORITATIVE`, and `HISTORICAL + NO + NON-AUTHORITATIVE`.
- Composite lifecycle status values are prohibited. Every registered artifact must carry exactly one Status, one Current value, and one Authority value.
- Every `SUPERSEDED` artifact must identify its approved replacement.
- Exactly one `FROZEN + YES + AUTHORITATIVE` version is permitted per artifact identifier, unless the Registry explicitly records that no approved version exists.
- An authoritative artifact may depend only on another `FROZEN + YES + AUTHORITATIVE` artifact. `DEVELOPMENT`, `SUPERSEDED`, and `HISTORICAL` dependencies are prohibited.
- Governance status is assigned only by this registry and the corresponding Release Manifest. Filename suffixes such as `_FROZEN`, embedded labels, and directory placement are informational only.
- Document versions and architecture-baseline versions are independent. For example, ERM-001 v2.2 belongs to architecture baseline v1.1.

## Constitutional governance

EAH-001 is the versioned constitutional architecture authority, not a silently mutable living handbook. Changes require an approved, versioned clarification or architecture release; an atomic registry update; and Release Manifest regeneration. When authorities conflict, the hierarchy defined by EAH-001 and CDS-001 governs. An unresolved same-level conflict is a stop condition.

The official capability term is **Business Capability Specification (BCS)**. Business Capability Model (BCM) is deprecated. The [Architecture Glossary](released/v1.2/ARCHITECTURE-GLOSSARY-v1.2_FROZEN.md) governs terminology used by current architecture and engineering artifacts.

## Authoritative artifacts — Architecture Baseline v1.3

| Document | Version | Supersedes | Status | Current | Authority | Location |
|---|---:|---|---|---|---|---|
| Enterprise Constitution | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/The%20Constitutional%20Theory%20of%20Enterprise%20Cognition%20-%20Version%201.0.docx) |
| EAH-001 | 1.5 | 1.4 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/EAH-001_ECOM_Architecture_Handbook_v1.5_FROZEN.docx) |
| RFC-010 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/RFC-010_Canonical_Enterprise_Ontology_Boundary_v1.0_FROZEN.docx) |
| RFC-011 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/RFC-011_Immutable_Record_Lifecycle_and_Currentness_v1.0_FROZEN.docx) |
| RFC-012 | 1.0 | RFC-0001 through RFC-0009 as architecture authorities | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/RFC-012_Constitutional_Reconciliation_v1.0_FROZEN.docx) |
| RFC-013 | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/RFC-013_Governance_Authority_and_Evaluation_Separation_v1.2_FROZEN.docx) |
| RFC-014 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.4/RFC-014_Cognitive_Capability_Integration_Handoff_and_Transaction_Policy_v1.3_FROZEN.md) |
| RFC-015 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.8/RFC-015_Tenant_Ownership_Physical_Model_Authorization_v1.0_FROZEN.md) |
| RFC-016 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.9/RFC-016_Institutional_Relationship_Canonical_Authorization_and_Tenant_Ownership_v1.0_FROZEN.md) |
| RFC-017 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.11/RFC-017-Gate-F-Supply-Chain-Semantic-Vocabulary-Authorization_v1.0_FROZEN.md) |
| RSP-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.3/RSP-001_Runtime_Security_Retention_and_Replay_Authority_v1.0_FROZEN.md) |
| CIM-001 | 1.1 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CIM-001-Cognitive-Integration-Contract-Model-v1.1_FROZEN.md) |
| CVR-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CVR-001_Supplier_Risk_Canonical_Vocabulary_Clarification_v1.0_FROZEN.docx) |
| ARCH-005 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCH-005-Bounded-Supplier-Risk-Vocabulary-Ownership-v1.0_FROZEN.md) |
| PAD-EIC Compatibility Clarification | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/PAD-EIC-Legacy-Invocation-Compatibility-Clarification-v1.0_FROZEN.md) |
| Product-Internal Deterministic Capability Boundary Clarification (PAD-001) | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.9/PAD-001-Product-Internal-Deterministic-Capability-Boundary-Clarification-v1.0_FROZEN.md) |
| Local Development Identity Provider and Demo Persona Authorization Boundary (PAD-002) | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.10/PAD-002-Local-Development-Identity-Provider-and-Demo-Persona-Authorization-Boundary_v1.0_FROZEN.md) |
| Gate F Impact and Mitigation Access Boundary (PAD-003) | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.11/PAD-003-Gate-F-Impact-Mitigation-Access-Boundary_v1.0_FROZEN.md) |
| CDD-010 | 1.5 | 1.4 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.7/CDD-010_Trusted_Admission_Identity_Clarification_v1.5_FROZEN.md) |
| CDD-012 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.5/CDD-012_Authenticated_Replay_Clarification_v1.3_FROZEN.md) |
| RCP-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.5/RCP-001_Authenticated_Replay_Execution_Contract_v1.0_FROZEN.md) |
| CAM-001 | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CAM-001_Canonical_Projection_Model_v1.2_FROZEN.docx) |
| Architecture Glossary | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCHITECTURE-GLOSSARY-v1.2_FROZEN.md) |
| Baseline Record | 1.9 | Baseline Record v1.8 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.7/BASELINE-RECORD-v1.9_FROZEN.md) |
| Architecture Consistency Report | 1.12 | 1.11 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.11/ARCHITECTURE-CONSISTENCY-REPORT-v1.12_FROZEN.md) |
| Architecture Drift Report | 1.8 | 1.7 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.7/ARCHITECTURE-DRIFT-REPORT-v1.8_FROZEN.md) |
| Architecture Remediation Report | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCHITECTURE-REMEDIATION-REPORT-v1.2_FROZEN.md) |
| Release Readiness Report | 1.8 | 1.7 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.7/RELEASE-READINESS-REPORT-v1.8_FROZEN.md) |
| PMM-001 | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.4/PMM-001_Runtime_Persistence_Role_Mapping_v1.2_FROZEN.md) |
| CDS-001 | 1.3 | CDS-001 v1.2 and Authorized Artifacts Amendment | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CDS-001_Codex_Development_Standard_v1.3_FROZEN.docx) |
| CDD-003 Revision 2 | 2.0 | CDD-003 Foundation Reference Model | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CDD-003-Revision-2-Complete-Canonical-Enterprise-Ontology.md) |
| ECOM Physical Data Model | 1.7 | 1.6 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.9/ECOM_Physical_Data_Model_v1_7.sql) |
| PAS-001 | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.7/PAS-001_Trusted_Receipt_Timestamp_Clarification_v1.2_FROZEN.md) |
| IDP-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.4/IDP-001_Provider_Neutral_OIDC_Identity_Validation_Contract_v1.0_FROZEN.md) |
| BSP-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.6/BSP-001_Supplier_Risk_Browser_Authentication_and_Session_Profile_v1.0_FROZEN.md) |
| ERM-001 | 2.2 | 2.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ERM-001_Enterprise_Entity_Resolution_Business_Capability_Specification_v2.2_FROZEN.docx) |
| SRM-001 | 2.2 | 2.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/SRM-001_Semantic_Resolution_Business_Capability_Specification_v2.2_FROZEN.docx) |
| ASM-001 | 2.3 | 2.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ASM-001_Assertion_Business_Capability_Specification_v2.3_FROZEN.docx) |
| AEM-001 | 1.1 | 1.0 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/AEM-001_Acceptance_Evidence_Business_Specification_v1.1_FROZEN.docx) |
| KRM-001 | 1.5 | 1.4 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/KRM-001_Knowledge_Business_Capability_Specification_v1.5_FROZEN.docx) |
| DRM-001 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/DRM-001_Decision_Business_Capability_Specification_v1.3_FROZEN.docx) |
| GEM-001 | 1.2 | 1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/GEM-001_Governance_Exception_Business_Specification_v1.2_FROZEN.docx) |
| GRM-001 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/GRM-001_Governance_Business_Capability_Specification_v1.3_FROZEN.docx) |
| EIC-001 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.3_FROZEN.docx) |
| EOM-001 | 1.4 | 1.3 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.3/EOM-001-Durable-Recovery-Clarification-v1.4_FROZEN.md) |
| ESM-001 | 1.3 | 1.2 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.3_FROZEN.docx) |
| PAD-001 | 1.5 | 1.4 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/PAD-001_Product_Access_Protocol_Specification_v1.5_FROZEN.docx) |
| ARCH-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCH-001-Persistence-Bootstrap-and-Canonical-Mapping.md) |
| ARCH-003 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCH-003-Persistence-Bootstrap-and-Metadata-Policy.md) |
| ARCH-004 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/ARCH-004-Canonical-Bootstrap-Values.md) |
| CDD Template | 2.2 | CDD Template v2.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CDD_TEMPLATE_v2.2_FROZEN.docx) |
| CDD Authorization Gap Review | 1.1 | 1.0 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/CDD-AUTHORIZATION-GAP-REVIEW-v1.1_FROZEN.md) |
| Dependency Resolution Report | 1.1 | 1.0 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/DEPENDENCY-RESOLUTION-REPORT-v1.1_FROZEN.md) |
| Architecture Dependency Matrix | 1.11 | 1.10 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.11/DEPENDENCY-MATRIX-v1.11.csv) |
| RND-001 | 1.0 | — | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/RND-001_Architecture_Registry_Normalization_v1.0_FROZEN.md) |
| RELEASE-README | v1.2 | v1.1 | FROZEN | YES | AUTHORITATIVE | [Document](released/v1.2/README.md) |

All artifacts in this table are current and authoritative within Architecture Baseline v1.4.

## Development artifacts — non-binding

These artifacts remain in the release package for traceability. They are not authoritative and may not approve implementation.

| Document | Version | Supersedes | Status | Current | Authority | Location |
|---|---:|---|---|---|---|---|
| TAS-001 Part 1 | 1.0 | — | DEVELOPMENT | NO | NON-AUTHORITATIVE | [Document](released/v1.2/TAS-001_Part1_YC_Prototype_Technology_Architecture.docx) |
| ECOM Logical Data Model | 1.3 | — | DEVELOPMENT | NO | NON-AUTHORITATIVE | [Document](released/v1.2/ECOM_Logical_Data_Model_v1_3.md) |
| EAD-001 | 1.3 | — | DEVELOPMENT | NO | NON-AUTHORITATIVE | [Document](released/v1.2/EAD-001_Enterprise_Attribute_Dictionary_v1_3.xlsx) |

## Governed implementation work orders

CDD gate state is distinct from architecture-artifact lifecycle status.

| Work Order | Version | CDD Gate | Implementation State | Location |
|---|---:|---|---|---|
| CDD-009 Governance Engine | 1.1 | FROZEN | IMPLEMENTED | [Authorization](../docs/cdd/CDD-009-AUTHORIZATION.md) · [Evidence](../docs/cdd/CDD-009-RECONCILIATION-REPORT.md) |
| CDD-010 Cognitive Engine Runtime Shell | 1.3 | FROZEN | IMPLEMENTED | [Work order](../docs/cdd/CDD-010-Cognitive-Engine-Runtime.md) · [Resolved clarification](../docs/cdd/CDD-010-ARCHITECTURE-CLARIFICATION.md) · [Gate report](../docs/cdd/CDD-010-PREIMPLEMENTATION-GATE-REPORT.md) · [Evidence](../docs/cdd/CDD-010-IMPLEMENTATION-EVIDENCE.md) |
| CDD-011 Supplier-Risk Capability Integration | 1.0 | FROZEN | IMPLEMENTED / VERIFIED | [Work order](../docs/cdd/CDD-011-Supplier-Risk-Capability-Integration.md) · [Gate report](../docs/cdd/CDD-011-PREIMPLEMENTATION-GATE-REPORT.md) · [Evidence](../docs/cdd/CDD-011-IMPLEMENTATION-EVIDENCE.md) · [Closure report](../docs/cdd/Closure-Gate-2-CDD-011-Implementation-and-Validation-Report.md) |
| CDD-012 Durable Execution Persistence and Recovery | 1.2 | FROZEN | IMPLEMENTED / VERIFIED | [Work order](../docs/cdd/CDD-012-Durable-Execution-Persistence-and-Recovery.md) · [Gate report](../docs/cdd/CDD-012-PREIMPLEMENTATION-GATE-REPORT.md) · [Evidence](../docs/cdd/CDD-012-IMPLEMENTATION-EVIDENCE.md) · [Closure report](../docs/cdd/Closure-Gate-3-CDD-012-Durable-Persistence-and-Recovery-Report.md) |
| CDD-013 Supplier Risk Application API and Security Boundary | 1.0 | FROZEN | IMPLEMENTED / VERIFIED | [Work order](../docs/cdd/CDD-013-Supplier-Risk-Application-API-and-Security-Boundary.md) · [Gate report](../docs/cdd/CDD-013-PREIMPLEMENTATION-GATE-REPORT.md) · [Evidence](../docs/cdd/CDD-013-IMPLEMENTATION-EVIDENCE.md) · [Closure report](../docs/cdd/Closure-Gate-4-CDD-013-Application-API-and-Security-Boundary-Implementation-Report.md) |
| CDD-014 Supplier Risk Business Workflow and User Experience | 1.0 | FROZEN | IMPLEMENTED / VERIFIED | [Work order](../docs/cdd/CDD-014-Supplier-Risk-Business-Workflow-and-User-Experience-DRAFT.md) · [Gate report](../docs/cdd/CDD-014-PREIMPLEMENTATION-GATE-REPORT.md) · [Closure report](../docs/cdd/Closure-Gate-5-CDD-014-Supplier-Risk-Business-Workflow-and-User-Experience-Implementation-Report.md) |
| CDD-015 Governed Supply Chain Impact and Mitigation Decision | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision.md) · [Resolved clarification](../docs/cdd/CDD-015-Governed-Impact-Decision-Policy-Clarification-and-Remediation-Report.md) · [Runtime composition clarification](../docs/cdd/CDD-015-Runtime-Composition-Clarification-and-Remediation-Report.md) · [Demo data and read-projection clarification](../docs/cdd/CDD-015-Deterministic-Demo-Data-and-Read-Projection-Clarification-and-Remediation-Report.md) |
| CDD-016 Governed Supplier-Risk Frontend Experience | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-016-Governed-Supplier-Risk-Frontend-Experience.md) |
| CDD-017 Canonical Supply Chain Blueprint Requirement Contract | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-017-Canonical-Supply-Chain-Blueprint-Requirement-Contract.md) · [G2 persistence/domain artifact authorization](../docs/cdd/CDD-017-G2-Persistence-Domain-Artifact-Authorization.md) · [G3 internal application service artifact authorization](../docs/cdd/CDD-017-G3-Internal-Application-Service-Artifact-Authorization.md) · [G3.5 canonical Blueprint seed artifact authorization](../docs/cdd/CDD-017-G3.5-Canonical-Blueprint-Seed-Artifact-Authorization.md) |
| CDD-018 Blueprint Conformance Evaluation | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-018-Blueprint-Conformance-Evaluation.md) · [G4 artifact authorization](../docs/cdd/CDD-018-G4-Blueprint-Conformance-Artifact-Authorization.md) |
| CDD-019 Source-to-Blueprint Semantic Mapping (H1-H3) | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-019-Source-to-Blueprint-Semantic-Mapping.md) · [H1 artifact authorization](../docs/cdd/CDD-019-H1-Source-Field-Semantic-Mapping-Artifact-Authorization.md) · [H2 artifact authorization](../docs/cdd/CDD-019-H2-Semantic-Mapping-Resolution-Artifact-Authorization.md) · [H3 artifact authorization](../docs/cdd/CDD-019-H3-Deterministic-Mapping-Demonstration-Artifact-Authorization.md) |
| CDD-020 Blueprint Information-Element Semantic Coverage Evaluation | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-020-Blueprint-Information-Element-Semantic-Coverage-Evaluation.md) · [I1 artifact authorization](../docs/cdd/CDD-020-I1-Semantic-Coverage-Evaluation-Artifact-Authorization.md) |
| CDD-021 Blueprint Semantic Gap Impact Context and Remediation Recommendation | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-021-Blueprint-Semantic-Gap-Impact-Context-and-Remediation-Recommendation.md) · [J1/J2 artifact authorization](../docs/cdd/CDD-021-J1-J2-Gap-Impact-Context-and-Remediation-Artifact-Authorization.md) |
| CDD-022 Governed Source Field-Value Evidence | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-022-Governed-Source-Field-Value-Evidence.md) · [Artifact authorization](../docs/cdd/CDD-022-Field-Value-Evidence-Artifact-Authorization.md) |
| CDD-023 Blueprint Information-Element Evidence Availability Evaluation | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-023-Blueprint-Information-Element-Evidence-Availability-Evaluation.md) · [H4 artifact authorization](../docs/cdd/CDD-023-H4-Evidence-Availability-Artifact-Authorization.md) |
| CDD-024 Blueprint Information-Element Context Availability Composition | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-024-Blueprint-Information-Element-Context-Availability-Composition.md) · [Artifact authorization](../docs/cdd/CDD-024-Context-Availability-Composition-Artifact-Authorization.md) |
| CDD-025 Blueprint Information-Element Context Explanation | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-025-Blueprint-Information-Element-Context-Explanation.md) · [Artifact authorization](../docs/cdd/CDD-025-Context-Explanation-Artifact-Authorization.md) |
| CDD-026 Blueprint Information-Element Decision-Prerequisite Assessment | 1.0 | FROZEN | NOT STARTED | [Work order](../docs/cdd/CDD-026-Blueprint-Information-Element-Decision-Prerequisite-Assessment.md) |

## Historical review artifacts

Artifacts in this section preserve architecture-review history. They are not architecture authorities and are excluded from release-gate validation and automated architecture blocker checks. Original findings remain unchanged; the Resolution section records the governing artifacts that closed them.

| Review Artifact | Status | Current | Authority | Resolved By | Location |
|---|---|---|---|---|---|
| CDD-004 Architecture Clarification Report | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — ERM-001 v2.1; RFC-011; superseded by ERM-001 v2.2 | [Report](../docs/cdd/CDD-004-ARCHITECTURE-CLARIFICATION.md) |
| CDD-005 Architecture Clarification Report | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — SRM-001 v2.0; SRM-001 v2.1; RFC-011 | [Report](../docs/cdd/CDD-005-ARCHITECTURE-CLARIFICATION.md) |
| CDD-005 Architecture Clarification Report — SRM-001 v2.0 Residuals | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — SRM-001 v2.1; RFC-011 | [Report](../docs/cdd/CDD-005-ARCHITECTURE-CLARIFICATION-v2.md) |
| CDD-006 Architecture Clarification Report | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — ASM-001 v2.0; SRM-001 v2.1; RFC-011; superseded by ASM-001 v2.1 | [Report](../docs/cdd/CDD-006-ARCHITECTURE-CLARIFICATION.md) |
| CDD-007 Architecture Clarification Report | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — AEM-001 v1.0; RFC-011; KRM-001 v1.2; superseded by AEM-001 v1.1, KRM-001 v1.3, RFC-013 | [Report](../docs/cdd/CDD-007-ARCHITECTURE-CLARIFICATION.md) |
| PWD-001 Architecture Clarification Report | HISTORICAL | NO | NON-AUTHORITATIVE | RESOLVED — PAD-001 v1.2; EIC-001 v1.1; EOM-001 v1.1; ESM-001 v1.1 | [Report](../docs/architecture/PWD-001-ARCHITECTURE-CLARIFICATION.md) |
| Closure Gate 1C Clarification Release and Architecture Remediation Closure Report | HISTORICAL | NO | NON-AUTHORITATIVE | CLOSED — Architecture Baseline v1.3; RFC-014 v1.1; CIM-001 v1.1 | [Report](../docs/architecture/Closure-Gate-1C-Clarification-Release-and-Architecture-Remediation-Closure-Report.md) |

## Historical implementation artifacts

These records document completed or superseded implementation work. They do not govern architecture and are excluded from current release-gate blocker checks.

| Artifact | Status | Current | Authority | Governing or Superseding Artifact | Location |
|---|---|---|---|---|---|
| CDD-003 Foundation Reference Model v2.1 | HISTORICAL | NO | NON-AUTHORITATIVE | SUPERSEDED — CDD-003 Revision 2 v2.0 | [Record](../docs/cdd/CDD-003-Foundation-Reference-Model.md) |
| CDD-004 Enterprise Entity Resolution Engine v4.0 | HISTORICAL | NO | NON-AUTHORITATIVE | SUPERSEDED — CDD-004 implementation under ERM-001 v2.2 | [Record](../docs/cdd/CDD-004_Enterprise_Entity_Resolution_Engine_v4.0.docx) |
| CDD-004 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — ERM-001 v2.2; RFC-011 | [Record](../docs/cdd/CDD-004-README.md) |
| CDD-005 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — SRM-001 v2.1; RFC-011 | [Record](../docs/cdd/CDD-005-README.md) |
| CDD-006 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — ASM-001 v2.1; RFC-011 | [Record](../docs/cdd/CDD-006-README.md) |
| CDD-007 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — KRM-001 v1.3; AEM-001 v1.1; RFC-011; RFC-013 | [Record](../docs/cdd/CDD-007-README.md) |
| CDD-008 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — DRM-001 v1.1; RFC-011 | [Record](../docs/cdd/CDD-008-README.md) |
| CDD-009 implementation record | HISTORICAL | NO | NON-AUTHORITATIVE | IMPLEMENTED — GRM-001 v1.2; GEM-001 v1.1; RFC-011; RFC-013 | [Record](../docs/cdd/CDD-009-README.md) |

## Historical baseline — v1.0

All documents below are `SUPERSEDED` and retained only for audit history.

| Document | Version | Superseded By | Status | Current | Authority | Location |
|---|---:|---|---|---|---|---|
| RFC-0001 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0001%20-%20Enterprise%20Knowledge%20Specification%20v1.0.docx) |
| RFC-0002 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0002%20-%20Enterprise%20Ontology%20Specification%20v1.0.docx) |
| RFC-0003 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0003%20-%20Institutional%20Acts%20Specification%20v1.0.docx) |
| RFC-0004 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0004%20-%20Enterprise%20Knowledge%20Graph%20Specification%20v1.0.docx) |
| RFC-0005 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0005%20-%20Decision%20Assembly%20Specification%20v1.0.docx) |
| RFC-0006 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0006%20-%20Enterprise%20Memory%20Specification%20v1.0.docx) |
| RFC-0007 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0007%20-%20Enterprise%20Reasoning%20Specification%20v1.0.docx) |
| RFC-0008 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0008%20-%20Enterprise%20Decision%20Specification%20v1.0.docx) |
| RFC-0009 | 1.0 | RFC-012 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-0009%20-%20Enterprise%20Learning%20Specification%20v1.0.docx) |
| SRM-001 | 1.0 | SRM-001 v2.0 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/SRM-001_Semantic_Resolution_Business_Capability_Specification_v1.0_FROZEN.docx) |
| SRM-001 | 2.0 | SRM-001 v2.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/SRM-001_Semantic_Resolution_Business_Capability_Specification_v2.0_FROZEN.docx) |
| ASM-001 | 1.0 | ASM-001 v2.0 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ASM-001_Assertion_Business_Capability_Specification_v1.0_FROZEN.docx) |
| ASM-001 | 2.0 | ASM-001 v2.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ASM-001_Assertion_Business_Capability_Specification_v2.0_FROZEN.docx) |
| ERM-001 | 2.1 | ERM-001 v2.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ERM-001_Enterprise_Entity_Resolution_Business_Capability_Specification_v2.1_FROZEN.docx) |
| AEM-001 | 1.0 | AEM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/AEM-001_Acceptance_Evidence_Business_Specification_v1.0_FROZEN.docx) |
| KRM-001 | 1.2 | KRM-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/KRM-001_Knowledge_Business_Capability_Specification_v1.2_FROZEN.docx) |
| DRM-001 | 1.0 | DRM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/DRM-001_Decision_Business_Capability_Specification_v1.0_FROZEN.docx) |
| EIC-001 | 1.0 | EIC-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.0_FROZEN.docx) |
| EOM-001 | 1.0 | EOM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EOM-001_Cognitive_Engine_Orchestration_Architecture_v1.0_FROZEN.docx) |
| ESM-001 | 1.0 | ESM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.0_FROZEN.docx) |
| PAD-001 Product Access Architecture | 1.0 | PAD-001 Protocol v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/PAD-001_Product_Access_Architecture_v1.0_FROZEN.docx) |
| PAD-001 Product Access Protocol | 1.1 | PAD-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/PAD-001_Product_Access_Protocol_Specification_v1.1_FROZEN.docx) |
| PAD-001 Product Access Protocol | 1.2 | PAD-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/PAD-001_Product_Access_Protocol_Specification_v1.2_FROZEN.docx) |
| CDS-001 | 1.2 | CDS-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CDS-001_Codex_Development_Standard_v1.2_FROZEN.docx) |
| CDS-001 Authorized Artifacts Amendment | 1.2 | CDS-001 v1.3 (consolidated) | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CDS-001-Authorized-Artifacts-Amendment.md) |
| CDD Template | 2.0 | CDD Template v2.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CDD_TEMPLATE_v2.0_FROZEN.docx) |
| CDD Template | 2.1 | CDD Template v2.2 — non-compliant authorization model | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CDD_TEMPLATE_v2.1_FROZEN.docx) |
| EAH-001 | 1.3 | EAH-001 v1.4 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EAH-001_ECOM_Architecture_Handbook_v1.3_FROZEN.docx) |
| RFC-013 | 1.0 | RFC-013 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RFC-013_Governance_Authority_and_Evaluation_Separation_v1.0_FROZEN.docx) |
| CAM-001 | 1.0 | CAM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CAM-001_Canonical_Projection_Model_v1.0_FROZEN.docx) |
| SRM-001 | 2.1 | SRM-001 v2.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/SRM-001_Semantic_Resolution_Business_Capability_Specification_v2.1_FROZEN.docx) |
| ASM-001 | 2.1 | ASM-001 v2.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ASM-001_Assertion_Business_Capability_Specification_v2.1_FROZEN.docx) |
| KRM-001 | 1.3 | KRM-001 v1.4 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/KRM-001_Knowledge_Business_Capability_Specification_v1.3_FROZEN.docx) |
| DRM-001 | 1.1 | DRM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/DRM-001_Decision_Business_Capability_Specification_v1.1_FROZEN.docx) |
| GEM-001 | 1.0 | GEM-001 v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/GEM-001_Governance_Exception_Business_Specification_v1.0_FROZEN.docx) |
| GRM-001 | 1.1 | GRM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/GRM-001_Governance_Business_Capability_Specification_v1.1_FROZEN.docx) |
| EIC-001 | 1.1 | EIC-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.1_FROZEN.docx) |
| EOM-001 | 1.1 | EOM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EOM-001_Cognitive_Engine_Orchestration_Architecture_v1.1_FROZEN.docx) |
| ESM-001 | 1.1 | ESM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.1_FROZEN.docx) |
| PAD-001 Product Access Protocol | 1.3 | PAD-001 v1.4 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/PAD-001_Product_Access_Protocol_Specification_v1.3_FROZEN.docx) |
| EAH-001 | 1.2 | EAH-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EAH-001_ECOM_Architecture_Handbook_v1.2_FROZEN.docx) |
| EAH-001 | 1.1 | EAH-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/EAH-001_ECOM_Architecture_Handbook_v1.1.docx) |
| Architecture Glossary | 1.0 | Architecture Glossary v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ARCHITECTURE-GLOSSARY-v1.0_FROZEN.md) |
| CDD Authorization Gap Review | 1.0 | CDD Authorization Gap Review v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/CDD-AUTHORIZATION-GAP-REVIEW-v1.0_FROZEN.md) |
| ASM-001 | 2.2 | ASM-001 v2.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/ASM-001_Assertion_Business_Capability_Specification_v2.2_FROZEN.docx) |
| DRM-001 | 1.2 | DRM-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/DRM-001_Decision_Business_Capability_Specification_v1.2_FROZEN.docx) |
| GRM-001 | 1.2 | GRM-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/GRM-001_Governance_Business_Capability_Specification_v1.2_FROZEN.docx) |
| EIC-001 | 1.2 | EIC-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.2_FROZEN.docx) |
| EOM-001 | 1.2 | EOM-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/EOM-001_Cognitive_Engine_Orchestration_Architecture_v1.2_FROZEN.docx) |
| PAD-001 | 1.4 | PAD-001 v1.5 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/PAD-001_Product_Access_Protocol_Specification_v1.4_FROZEN.docx) |
| EAH-001 | 1.4 | EAH-001 v1.5 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/EAH-001_ECOM_Architecture_Handbook_v1.4_FROZEN.docx) |
| RFC-013 | 1.1 | RFC-013 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/RFC-013_Governance_Authority_and_Evaluation_Separation_v1.1_FROZEN.docx) |
| CAM-001 | 1.1 | CAM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/CAM-001_Canonical_Projection_Model_v1.1_FROZEN.docx) |
| Architecture Glossary | 1.1 | Architecture Glossary v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/ARCHITECTURE-GLOSSARY-v1.1_FROZEN.md) |
| KRM-001 | 1.4 | KRM-001 v1.5 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/KRM-001_Knowledge_Business_Capability_Specification_v1.4_FROZEN.docx) |
| GEM-001 | 1.1 | GEM-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/GEM-001_Governance_Exception_Business_Specification_v1.1_FROZEN.docx) |
| ESM-001 | 1.2 | ESM-001 v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.2_FROZEN.docx) |
| Baseline Record | 1.3 | Baseline Record v1.4 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/BASELINE-RECORD-v1.3_FROZEN.md) |
| Architecture Consistency Report | 1.2 | Architecture Consistency Report v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/ARCHITECTURE-CONSISTENCY-REPORT-v1.2_FROZEN.md) |
| Architecture Drift Report | 1.2 | Architecture Drift Report v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/ARCHITECTURE-DRIFT-REPORT-v1.2_FROZEN.md) |
| Architecture Remediation Report | 1.1 | Architecture Remediation Report v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Report](../docs/architecture/Closure-Gate-1A-Minimum-Authority-Amendment-Review-Package.md) |
| Release Readiness Report | 1.2 | Release Readiness Report v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/RELEASE-READINESS-REPORT-v1.2_FROZEN.md) |
| Architecture Dependency Matrix | 1.1 | Architecture Dependency Matrix v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/DEPENDENCY-MATRIX-v1.1.csv) |
| Dependency Resolution Report | 1.0 | Dependency Resolution Report v1.1 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.1/DEPENDENCY-RESOLUTION-REPORT-v1.0_FROZEN.md) |
| Baseline Record | 1.1 | Baseline Record v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/BASELINE-RECORD-v1.1_FROZEN.md) |
| Architecture Consistency Report | 1.1 | ACR-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ARCHITECTURE-CONSISTENCY-REPORT-v1.1_FROZEN.md) |
| Architecture Drift Report | 1.1 | ADR-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/ARCHITECTURE-DRIFT-REPORT-v1.1_FROZEN.md) |
| Release Readiness Report | 1.1 | RRR-001 v1.2 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/RELEASE-READINESS-REPORT-v1.1_FROZEN.md) |
| Baseline Record | 1.2 | Baseline Record v1.3 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.0/BASELINE-RECORD-v1.2_FROZEN.md) |
| ECOM Physical Data Model | 1.5 | ECOM Physical Data Model v1.6 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.4/ECOM_Physical_Data_Model_v1_5.sql) |
| Architecture Consistency Report | 1.8 | Architecture Consistency Report v1.9 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.7/ARCHITECTURE-CONSISTENCY-REPORT-v1.8_FROZEN.md) |
| Architecture Dependency Matrix | 1.7 | Architecture Dependency Matrix v1.8 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.7/DEPENDENCY-MATRIX-v1.7.csv) |
| ECOM Physical Data Model | 1.6 | ECOM Physical Data Model v1.7 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.8/ECOM_Physical_Data_Model_v1_6.sql) |
| Architecture Consistency Report | 1.9 | Architecture Consistency Report v1.10 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.8/ARCHITECTURE-CONSISTENCY-REPORT-v1.9_FROZEN.md) |
| Architecture Dependency Matrix | 1.8 | Architecture Dependency Matrix v1.9 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.8/DEPENDENCY-MATRIX-v1.8.csv) |
| Architecture Consistency Report | 1.10 | Architecture Consistency Report v1.11 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.9/ARCHITECTURE-CONSISTENCY-REPORT-v1.10_FROZEN.md) |
| Architecture Dependency Matrix | 1.9 | Architecture Dependency Matrix v1.10 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.9/DEPENDENCY-MATRIX-v1.9.csv) |
| Architecture Consistency Report | 1.11 | Architecture Consistency Report v1.12 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.10/ARCHITECTURE-CONSISTENCY-REPORT-v1.11_FROZEN.md) |
| Architecture Dependency Matrix | 1.10 | Architecture Dependency Matrix v1.11 | SUPERSEDED | NO | NON-AUTHORITATIVE | [Document](released/v1.10/DEPENDENCY-MATRIX-v1.10.csv) |

## Runtime dependency chain

The runtime authorities form one directional dependency chain. PAD does not redefine the responsibilities owned by EIC, EOM, or ESM.

| Order | Artifact | Current Version | Responsibility |
|---:|---|---:|---|
| 1 | PAD-001 | 1.5 | Product-facing protocol contracts and transport boundary |
| 2 | EIC-001 | 1.3 | Exclusive Cognitive Engine invocation boundary |
| 3 | EOM-001 | 1.3 | Post-admission orchestration of the approved capability chain |
| 4 | ESM-001 | 1.3 | Execution-state lifecycle, transitions, and terminality |

## Architecture Release Manifests

The Architecture Release Manifest is the authoritative integrity register for its baseline. It records governance metadata and SHA-256 checksums for every released artifact. Each manifest excludes itself because self-checksumming is not stable; its checksum is pinned below and protected by repository history. Run `make verify-architecture` before every release, merge, or architecture validation.

| Baseline | Status | Manifest | Manifest SHA-256 |
|---|---|---|---|
| v1.11 | CURRENT | [RELEASE-MANIFEST-v1.11.xlsx](released/v1.11/RELEASE-MANIFEST-v1.11.xlsx) | `ffa555afcda7d73fa39ec9459d94f691ca094e0a1560ca773550eace41ea7ddd` |
| v1.10 | HISTORICAL | [RELEASE-MANIFEST-v1.10.xlsx](released/v1.10/RELEASE-MANIFEST-v1.10.xlsx) | `da039e6401907b1962166a369633cd5100af339e60cc41286b8be1901c39bee4` |
| v1.9 | HISTORICAL | [RELEASE-MANIFEST-v1.9.xlsx](released/v1.9/RELEASE-MANIFEST-v1.9.xlsx) | `4036e7d96e738189cbe69f97756ea3a54ef804ce5a60d4f61ef62d67d4293c7d` |
| v1.8 | HISTORICAL | [RELEASE-MANIFEST-v1.8.xlsx](released/v1.8/RELEASE-MANIFEST-v1.8.xlsx) | `e8e947af8f2bee7fe2b064e3976a937aab4a181a22321efe4b6a67fdc01153f4` |
| v1.7 | HISTORICAL | [RELEASE-MANIFEST-v1.7.xlsx](released/v1.7/RELEASE-MANIFEST-v1.7.xlsx) | `a589d5aa471b2338277439801e60a62be7f35e4ee2169b8c626e40e283ee5566` |
| v1.6 | HISTORICAL | [RELEASE-MANIFEST-v1.6.xlsx](released/v1.6/RELEASE-MANIFEST-v1.6.xlsx) | `b9175b9afbba278c2fb365002174874a2578c9b012b3e0c73a90bfb71e1536aa` |
| v1.5 | HISTORICAL | [RELEASE-MANIFEST-v1.5.xlsx](released/v1.5/RELEASE-MANIFEST-v1.5.xlsx) | `2db925f4f28983dc7d12b12fcf58b806d1816a0ba52aaff465b8996fd2c2780a` |
| v1.4 | HISTORICAL | [RELEASE-MANIFEST-v1.4.xlsx](released/v1.4/RELEASE-MANIFEST-v1.4.xlsx) | `d7fd45a87acae813a5507660e37dad99cca8189a374033a167c83aeeee0ff183` |
| v1.3 | HISTORICAL | [RELEASE-MANIFEST-v1.3.xlsx](released/v1.3/RELEASE-MANIFEST-v1.3.xlsx) | `0fdf443911a0821f5828498612e3af50f525ef1d7ddedaa6b12a8f4414e671e7` |
| v1.2 | HISTORICAL | [RELEASE-MANIFEST-v1.2.xlsx](released/v1.2/RELEASE-MANIFEST-v1.2.xlsx) | `489cb3d8844562e3ffc8638afaa6a065862023bdfe64871245e09e92fa549b5a` |
| v1.1 | HISTORICAL | [RELEASE-MANIFEST-v1.1.xlsx](released/v1.1/RELEASE-MANIFEST-v1.1.xlsx) | `121bf46e4eeb3849f2fdc00116fc8955dc482341afa0846451fd4d71f5a2f850` |
| v1.0 | HISTORICAL | [RELEASE-MANIFEST-v1.0.xlsx](released/v1.0/RELEASE-MANIFEST-v1.0.xlsx) | `2e0a466d897eb7de0addf521325502cd2b1ef20f4ba5e97dd4b740cd0f9e031e` |

`released/v1.1/SHA256SUMS` is retained as a legacy partial checksum list and is not the integrity authority. The restored ECOM Physical Data Model v1.3 was independently verified against the project reference library and the frozen CDD-002 archive before registration.

## Baseline v1.1 publication evidence

| Evidence | Value |
|---|---|
| Governed release commit | `834582b754157a87a1924fa2b592ed9cbfcc3ee9` |
| GitHub commit | [Architecture: finalize Baseline v1.1 governed release](https://github.com/manoj96-alt/CTEC/commit/834582b754157a87a1924fa2b592ed9cbfcc3ee9) |
| Current Registry | [architecture/INDEX.md](https://github.com/manoj96-alt/CTEC/blob/834582b754157a87a1924fa2b592ed9cbfcc3ee9/architecture/INDEX.md) |
| Consistency evidence | [ACR-001 v1.2](https://github.com/manoj96-alt/CTEC/blob/834582b754157a87a1924fa2b592ed9cbfcc3ee9/architecture/released/v1.1/ARCHITECTURE-CONSISTENCY-REPORT-v1.2_FROZEN.md) |
| Drift evidence | [ADR-001 v1.2](https://github.com/manoj96-alt/CTEC/blob/834582b754157a87a1924fa2b592ed9cbfcc3ee9/architecture/released/v1.1/ARCHITECTURE-DRIFT-REPORT-v1.2_FROZEN.md) |
| Readiness evidence | [RRR-001 v1.2](https://github.com/manoj96-alt/CTEC/blob/834582b754157a87a1924fa2b592ed9cbfcc3ee9/architecture/released/v1.1/RELEASE-READINESS-REPORT-v1.2_FROZEN.md) |
| Integrity manifest | [Release Manifest v1.1](https://github.com/manoj96-alt/CTEC/blob/834582b754157a87a1924fa2b592ed9cbfcc3ee9/architecture/released/v1.1/RELEASE-MANIFEST-v1.1.xlsx) |

## CDD-009 implementation evidence

CDD-009 is governed implementation evidence, not an Architecture Baseline v1.1 artifact. Its integration does not alter a frozen architecture artifact and therefore does not regenerate either Architecture Release Manifest. The authorized `governance_evaluation_records` table is registered here as a capability-owned **immutable source record** extension under PMM-001; the canonical `governances` table remains a read-only canonical outcome projection.

| Evidence | Value |
|---|---|
| Implementation status | `IMPLEMENTED / FROZEN` |
| Source commit | [`5fa51e7`](https://github.com/manoj96-alt/CTEC/commit/5fa51e7) |
| Reconciled candidate commit | [`c45f3096df173a092ae3b078c615a6bed9698404`](https://github.com/manoj96-alt/CTEC/commit/c45f3096df173a092ae3b078c615a6bed9698404) |
| Merge commit | [`16b96a8c0359a28f5d4324d745c9dbab6d074a1f`](https://github.com/manoj96-alt/CTEC/commit/16b96a8c0359a28f5d4324d745c9dbab6d074a1f) |
| Authorization evidence | [CDD-009 authorization](https://github.com/manoj96-alt/CTEC/blob/16b96a8c0359a28f5d4324d745c9dbab6d074a1f/docs/cdd/CDD-009-AUTHORIZATION.md) |
| Review evidence | [CDD-009 reconciliation report](https://github.com/manoj96-alt/CTEC/blob/16b96a8c0359a28f5d4324d745c9dbab6d074a1f/docs/cdd/CDD-009-RECONCILIATION-REPORT.md) |
| Reviewer decision | `APPROVED — zero P0/P1 findings` |
| Unit test result | `97 passed; 9 PostgreSQL tests skipped; 89.79% coverage` |
| PostgreSQL integration result | `106 passed; 0 skipped; 94.81% coverage; PostgreSQL 15.17; Alembic head 0007_governance_eval` |
| Quality result | `Ruff PASS; Black PASS; isort PASS; mypy PASS (163 source files)` |
| Architecture validation | `PASS — registry/schema, dependency, checksum, manifest and drift checks` |
| Changed-artifact authorization | `PASS — exact path/action allowlist; no unauthorized artifacts changed` |

## CDD-010 implementation evidence

CDD-010 is governed implementation evidence, not an Architecture Baseline v1.1 artifact. Its integration does not alter a frozen architecture artifact and therefore does not regenerate either Architecture Release Manifest. The implementation is a process-local runtime shell only; production capability adapters and semantic handoff mappings remain outside CDD-010.

| Evidence | Value |
|---|---|
| Implementation status | `IMPLEMENTED / FROZEN` |
| Approved governance base | [`47031682d54ee27406e25d6c3a52ac704be0eebb`](https://github.com/manoj96-alt/CTEC/commit/47031682d54ee27406e25d6c3a52ac704be0eebb) |
| Implementation commit | [`c44914b4dc58223dde1221c703356c974093c79e`](https://github.com/manoj96-alt/CTEC/commit/c44914b4dc58223dde1221c703356c974093c79e) |
| Pull request | [PR #28](https://github.com/manoj96-alt/CTEC/pull/28) |
| Merge commit | [`c70afc43de71ec94ed2a8f1eb32a8cdb8dc56c5e`](https://github.com/manoj96-alt/CTEC/commit/c70afc43de71ec94ed2a8f1eb32a8cdb8dc56c5e) |
| Implementation evidence | [CDD-010 implementation evidence](../docs/cdd/CDD-010-IMPLEMENTATION-EVIDENCE.md) |
| Reviewer decision | `APPROVED — zero P0/P1 findings and zero unauthorized changes` |
| Test result | `15 focused runtime tests passed; 112 backend tests passed; 9 existing persistence tests skipped; 90.73% backend coverage` |
| CI result | `PASS — backend, frontend, and container jobs for PR #28` |
| Quality result | `Ruff PASS; Black PASS; isort PASS; mypy PASS (175 source files); frontend quality PASS` |
| Architecture validation | `PASS — registry/schema, dependency, checksum, manifest, authorization, and drift checks` |

## CDD-011 implementation evidence

CDD-011 is governed implementation evidence, not an Architecture Baseline v1.3 artifact. Its closure does not alter a frozen architecture authority and therefore does not regenerate an Architecture Release Manifest or the Architecture Dependency Matrix. The implementation remains the bounded, application-neutral, in-process supplier-risk adapter chain; durable execution persistence and product access remain outside CDD-011.

| Evidence | Value |
|---|---|
| Implementation status | `IMPLEMENTED / VERIFIED / FROZEN` |
| Approved implementation base | [`36221b64346cd2a8696985f1a3b787daf42f7dc6`](https://github.com/manoj96-alt/CTEC/commit/36221b64346cd2a8696985f1a3b787daf42f7dc6) |
| Implementation commit | [`312dca991362500e9db2f32f5d839c38f77724e1`](https://github.com/manoj96-alt/CTEC/commit/312dca991362500e9db2f32f5d839c38f77724e1) |
| Implementation pull request | [PR #33](https://github.com/manoj96-alt/CTEC/pull/33) |
| Implementation merge | [`01c7d068f75eccbab579502512adbd5504b75a6d`](https://github.com/manoj96-alt/CTEC/commit/01c7d068f75eccbab579502512adbd5504b75a6d) |
| Closure-report pull request | [PR #34](https://github.com/manoj96-alt/CTEC/pull/34) |
| Closure-report merge | [`1f04d0aff3220b5c5c3be9713a1f04bb62fa402a`](https://github.com/manoj96-alt/CTEC/commit/1f04d0aff3220b5c5c3be9713a1f04bb62fa402a) |
| Implementation evidence | [CDD-011 implementation evidence](../docs/cdd/CDD-011-IMPLEMENTATION-EVIDENCE.md) |
| Closure report | [Closure Gate 2 report](../docs/cdd/Closure-Gate-2-CDD-011-Implementation-and-Validation-Report.md) |
| Test result | `25 focused tests passed; 125 backend tests passed; 9 environment-dependent tests skipped; 90.61% coverage` |
| CI result | `PASS — backend, frontend, and container jobs for PRs #33 and #34` |
| Architecture validation | `PASS — Registry, dependency, checksum, manifest, authorization, and release-boundary checks` |
