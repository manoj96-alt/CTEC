# CTEC Architecture Release Registry

This file is the sole authoritative registry for released CTEC architecture. Engineering work must resolve architecture documents through this registry, never from personal Downloads folders, email attachments, unmerged branches, or legacy documentation paths.

## Release policy

- `architecture/released/v1.1/` is the current architecture baseline.
- `architecture/released/v1.0/` is retained for historical traceability only.
- A document is authoritative only when this registry marks it `CURRENT` and its location is inside the current release baseline.
- Superseded documents must not be used for implementation.
- A new or revised document becomes authoritative only through an approved registry update in the same commit that adds the released artifact.
- Every baseline must have a complete Architecture Release Manifest. Regeneration and checksum verification are mandatory whenever an architecture artifact is added, superseded, or frozen.
- Governance status is assigned only by this registry and the corresponding Release Manifest. Filename suffixes such as `_FROZEN`, embedded labels, and directory placement are informational only.
- Document versions and architecture-baseline versions are independent. For example, ERM-001 v2.2 belongs to architecture baseline v1.1.

## Constitutional governance

EAH-001 is the versioned constitutional architecture authority, not a silently mutable living handbook. Changes require an approved, versioned clarification or architecture release; an atomic registry update; and Release Manifest regeneration. When authorities conflict, the hierarchy defined by EAH-001 and CDS-001 governs. An unresolved same-level conflict is a stop condition.

The official capability term is **Business Capability Specification (BCS)**. Business Capability Model (BCM) is deprecated. The [Architecture Glossary](released/v1.1/ARCHITECTURE-GLOSSARY-v1.0_FROZEN.md) governs terminology used by current architecture and engineering artifacts.

## Current architecture baseline — v1.1

| Document | Current Version | Supersedes | Status | Location |
|---|---:|---|---|---|
| Enterprise Constitution | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/The%20Constitutional%20Theory%20of%20Enterprise%20Cognition%20-%20Version%201.0.docx) |
| EAH-001 | 1.3 | 1.2 | CURRENT / FROZEN / AUTHORITATIVE | [Document](released/v1.1/EAH-001_ECOM_Architecture_Handbook_v1.3_FROZEN.docx) |
| RFC-010 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/RFC-010_Canonical_Enterprise_Ontology_Boundary_v1.0_FROZEN.docx) |
| RFC-011 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/RFC-011_Immutable_Record_Lifecycle_and_Currentness_v1.0_FROZEN.docx) |
| RFC-012 | 1.0 | RFC-0001 through RFC-0009 as architecture authorities | CURRENT / FROZEN | [Document](released/v1.1/RFC-012_Constitutional_Reconciliation_v1.0_FROZEN.docx) |
| RFC-013 | 1.0 | Ambiguous use of “Governance” in AEM-001 and KRM-001 | CURRENT / FROZEN | [Document](released/v1.1/RFC-013_Governance_Authority_and_Evaluation_Separation_v1.0_FROZEN.docx) |
| CAM-001 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/CAM-001_Canonical_Projection_Model_v1.0_FROZEN.docx) |
| Architecture Glossary | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/ARCHITECTURE-GLOSSARY-v1.0_FROZEN.md) |
| PMM-001 | 1.0 | — | CURRENT / FROZEN / AUTHORITATIVE | [Document](released/v1.1/PMM-001_Persistence_Role_Mapping_v1.0_FROZEN.docx) |
| CDS-001 | 1.3 | CDS-001 v1.2 and Authorized Artifacts Amendment | CURRENT / FROZEN | [Document](released/v1.1/CDS-001_Codex_Development_Standard_v1.3_FROZEN.docx) |
| TAS-001 Part 1 | 1.0 | — | CURRENT / DEVELOPMENT | [Document](released/v1.1/TAS-001_Part1_YC_Prototype_Technology_Architecture.docx) |
| CDD-003 Revision 2 | 2.0 | CDD-003 Foundation Reference Model | CURRENT / FROZEN / AUTHORITATIVE | [Document](released/v1.1/CDD-003-Revision-2-Complete-Canonical-Enterprise-Ontology.md) |
| ECOM Logical Data Model | 1.3 | Earlier logical models | CURRENT / DEVELOPMENT | [Document](released/v1.1/ECOM_Logical_Data_Model_v1_3.md) |
| ECOM Physical Data Model | 1.3 | Earlier physical models | CURRENT / FROZEN | [Document](released/v1.1/ECOM_Physical_Data_Model_v1_3.sql) |
| EAD-001 | 1.3 | Earlier attribute dictionaries | CURRENT / DEVELOPMENT | [Document](released/v1.1/EAD-001_Enterprise_Attribute_Dictionary_v1_3.xlsx) |
| ERM-001 | 2.2 | 2.1 | CURRENT / FROZEN | [Document](released/v1.1/ERM-001_Enterprise_Entity_Resolution_Business_Capability_Specification_v2.2_FROZEN.docx) |
| SRM-001 | 2.1 | 2.0 | CURRENT / FROZEN | [Document](released/v1.1/SRM-001_Semantic_Resolution_Business_Capability_Specification_v2.1_FROZEN.docx) |
| ASM-001 | 2.1 | 2.0 | CURRENT / FROZEN | [Document](released/v1.1/ASM-001_Assertion_Business_Capability_Specification_v2.1_FROZEN.docx) |
| AEM-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/AEM-001_Acceptance_Evidence_Business_Specification_v1.1_FROZEN.docx) |
| KRM-001 | 1.3 | 1.2 | CURRENT / FROZEN | [Document](released/v1.1/KRM-001_Knowledge_Business_Capability_Specification_v1.3_FROZEN.docx) |
| DRM-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/DRM-001_Decision_Business_Capability_Specification_v1.1_FROZEN.docx) |
| GEM-001 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/GEM-001_Governance_Exception_Business_Specification_v1.0_FROZEN.docx) |
| GRM-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/GRM-001_Governance_Business_Capability_Specification_v1.1_FROZEN.docx) |
| EIC-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.1_FROZEN.docx) |
| EOM-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/EOM-001_Cognitive_Engine_Orchestration_Architecture_v1.1_FROZEN.docx) |
| ESM-001 | 1.1 | 1.0 | CURRENT / FROZEN | [Document](released/v1.1/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.1_FROZEN.docx) |
| PAD-001 | 1.3 | 1.2 | CURRENT / FROZEN | [Document](released/v1.1/PAD-001_Product_Access_Protocol_Specification_v1.3_FROZEN.docx) |
| ARCH-001 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/ARCH-001-Persistence-Bootstrap-and-Canonical-Mapping.md) |
| ARCH-003 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/ARCH-003-Persistence-Bootstrap-and-Metadata-Policy.md) |
| ARCH-004 | 1.0 | — | CURRENT / FROZEN | [Document](released/v1.1/ARCH-004-Canonical-Bootstrap-Values.md) |
| CDD Template | 2.1 | CDD Template v2.0 | CURRENT / FROZEN | [Document](released/v1.1/CDD_TEMPLATE_v2.1_FROZEN.docx) |

## Historical review artifacts

Artifacts in this section preserve architecture-review history. They are not architecture authorities and are excluded from release-gate validation and automated architecture blocker checks. Original findings remain unchanged; the Resolution section records the governing artifacts that closed them.

| Review Artifact | Status | Resolved By | Location |
|---|---|---|---|
| CDD-004 Architecture Clarification Report | HISTORICAL — RESOLVED | ERM-001 v2.1; RFC-011; superseded by ERM-001 v2.2 | [Report](../docs/cdd/CDD-004-ARCHITECTURE-CLARIFICATION.md) |
| CDD-005 Architecture Clarification Report | HISTORICAL — RESOLVED | SRM-001 v2.0; SRM-001 v2.1; RFC-011 | [Report](../docs/cdd/CDD-005-ARCHITECTURE-CLARIFICATION.md) |
| CDD-005 Architecture Clarification Report — SRM-001 v2.0 Residuals | HISTORICAL — RESOLVED | SRM-001 v2.1; RFC-011 | [Report](../docs/cdd/CDD-005-ARCHITECTURE-CLARIFICATION-v2.md) |
| CDD-006 Architecture Clarification Report | HISTORICAL — RESOLVED | ASM-001 v2.0; SRM-001 v2.1; RFC-011; superseded by ASM-001 v2.1 | [Report](../docs/cdd/CDD-006-ARCHITECTURE-CLARIFICATION.md) |
| CDD-007 Architecture Clarification Report | HISTORICAL — RESOLVED | AEM-001 v1.0; RFC-011; KRM-001 v1.2; superseded by AEM-001 v1.1, KRM-001 v1.3, RFC-013 | [Report](../docs/cdd/CDD-007-ARCHITECTURE-CLARIFICATION.md) |
| PWD-001 Architecture Clarification Report | HISTORICAL — RESOLVED | PAD-001 v1.2; EIC-001 v1.1; EOM-001 v1.1; ESM-001 v1.1 | [Report](../docs/architecture/PWD-001-ARCHITECTURE-CLARIFICATION.md) |

## Historical implementation artifacts

These records document completed or superseded implementation work. They do not govern architecture and are excluded from current release-gate blocker checks.

| Artifact | Status | Governing or Superseding Artifact | Location |
|---|---|---|---|
| CDD-003 Foundation Reference Model v2.1 | HISTORICAL — SUPERSEDED | CDD-003 Revision 2 v2.0 | [Record](../docs/cdd/CDD-003-Foundation-Reference-Model.md) |
| CDD-004 Enterprise Entity Resolution Engine v4.0 | HISTORICAL — SUPERSEDED | CDD-004 implementation under ERM-001 v2.2 | [Record](../docs/cdd/CDD-004_Enterprise_Entity_Resolution_Engine_v4.0.docx) |
| CDD-004 implementation record | HISTORICAL — IMPLEMENTED | ERM-001 v2.2; RFC-011 | [Record](../docs/cdd/CDD-004-README.md) |
| CDD-005 implementation record | HISTORICAL — IMPLEMENTED | SRM-001 v2.1; RFC-011 | [Record](../docs/cdd/CDD-005-README.md) |
| CDD-006 implementation record | HISTORICAL — IMPLEMENTED | ASM-001 v2.1; RFC-011 | [Record](../docs/cdd/CDD-006-README.md) |
| CDD-007 implementation record | HISTORICAL — IMPLEMENTED | KRM-001 v1.3; AEM-001 v1.1; RFC-011; RFC-013 | [Record](../docs/cdd/CDD-007-README.md) |
| CDD-008 implementation record | HISTORICAL — IMPLEMENTED | DRM-001 v1.1; RFC-011 | [Record](../docs/cdd/CDD-008-README.md) |

## Historical baseline — v1.0

All documents below are `SUPERSEDED` and retained only for audit history.

| Document | Version | Superseded By | Status | Location |
|---|---:|---|---|---|
| RFC-0001 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0001%20-%20Enterprise%20Knowledge%20Specification%20v1.0.docx) |
| RFC-0002 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0002%20-%20Enterprise%20Ontology%20Specification%20v1.0.docx) |
| RFC-0003 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0003%20-%20Institutional%20Acts%20Specification%20v1.0.docx) |
| RFC-0004 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0004%20-%20Enterprise%20Knowledge%20Graph%20Specification%20v1.0.docx) |
| RFC-0005 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0005%20-%20Decision%20Assembly%20Specification%20v1.0.docx) |
| RFC-0006 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0006%20-%20Enterprise%20Memory%20Specification%20v1.0.docx) |
| RFC-0007 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0007%20-%20Enterprise%20Reasoning%20Specification%20v1.0.docx) |
| RFC-0008 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0008%20-%20Enterprise%20Decision%20Specification%20v1.0.docx) |
| RFC-0009 | 1.0 | RFC-012 | SUPERSEDED | [Document](released/v1.0/RFC-0009%20-%20Enterprise%20Learning%20Specification%20v1.0.docx) |
| SRM-001 | 1.0 | SRM-001 v2.0 | SUPERSEDED | [Document](released/v1.0/SRM-001_Semantic_Resolution_Business_Capability_Specification_v1.0_FROZEN.docx) |
| SRM-001 | 2.0 | SRM-001 v2.1 | SUPERSEDED | [Document](released/v1.0/SRM-001_Semantic_Resolution_Business_Capability_Specification_v2.0_FROZEN.docx) |
| ASM-001 | 1.0 | ASM-001 v2.0 | SUPERSEDED | [Document](released/v1.0/ASM-001_Assertion_Business_Capability_Specification_v1.0_FROZEN.docx) |
| ASM-001 | 2.0 | ASM-001 v2.1 | SUPERSEDED | [Document](released/v1.0/ASM-001_Assertion_Business_Capability_Specification_v2.0_FROZEN.docx) |
| ERM-001 | 2.1 | ERM-001 v2.2 | SUPERSEDED | [Document](released/v1.0/ERM-001_Enterprise_Entity_Resolution_Business_Capability_Specification_v2.1_FROZEN.docx) |
| AEM-001 | 1.0 | AEM-001 v1.1 | SUPERSEDED | [Document](released/v1.0/AEM-001_Acceptance_Evidence_Business_Specification_v1.0_FROZEN.docx) |
| KRM-001 | 1.2 | KRM-001 v1.3 | SUPERSEDED | [Document](released/v1.0/KRM-001_Knowledge_Business_Capability_Specification_v1.2_FROZEN.docx) |
| DRM-001 | 1.0 | DRM-001 v1.1 | SUPERSEDED | [Document](released/v1.0/DRM-001_Decision_Business_Capability_Specification_v1.0_FROZEN.docx) |
| EIC-001 | 1.0 | EIC-001 v1.1 | SUPERSEDED | [Document](released/v1.0/EIC-001_Cognitive_Engine_Invocation_Architecture_v1.0_FROZEN.docx) |
| EOM-001 | 1.0 | EOM-001 v1.1 | SUPERSEDED | [Document](released/v1.0/EOM-001_Cognitive_Engine_Orchestration_Architecture_v1.0_FROZEN.docx) |
| ESM-001 | 1.0 | ESM-001 v1.1 | SUPERSEDED | [Document](released/v1.0/ESM-001_Cognitive_Engine_Execution_State_Architecture_v1.0_FROZEN.docx) |
| PAD-001 Product Access Architecture | 1.0 | PAD-001 Protocol v1.1 | SUPERSEDED | [Document](released/v1.0/PAD-001_Product_Access_Architecture_v1.0_FROZEN.docx) |
| PAD-001 Product Access Protocol | 1.1 | PAD-001 v1.2 | SUPERSEDED | [Document](released/v1.0/PAD-001_Product_Access_Protocol_Specification_v1.1_FROZEN.docx) |
| PAD-001 Product Access Protocol | 1.2 | PAD-001 v1.3 | SUPERSEDED | [Document](released/v1.0/PAD-001_Product_Access_Protocol_Specification_v1.2_FROZEN.docx) |
| CDS-001 | 1.2 | CDS-001 v1.3 | SUPERSEDED | [Document](released/v1.0/CDS-001_Codex_Development_Standard_v1.2_FROZEN.docx) |
| CDS-001 Authorized Artifacts Amendment | 1.2 | CDS-001 v1.3 | SUPERSEDED / CONSOLIDATED | [Document](released/v1.0/CDS-001-Authorized-Artifacts-Amendment.md) |
| CDD Template | 2.0 | CDD Template v2.1 | SUPERSEDED | [Document](released/v1.0/CDD_TEMPLATE_v2.0_FROZEN.docx) |
| EAH-001 | 1.2 | EAH-001 v1.3 | SUPERSEDED | [Document](released/v1.0/EAH-001_ECOM_Architecture_Handbook_v1.2_FROZEN.docx) |
| EAH-001 | 1.1 | EAH-001 v1.2 | SUPERSEDED | [Document](released/v1.0/EAH-001_ECOM_Architecture_Handbook_v1.1.docx) |

## Runtime dependency chain

The runtime authorities form one directional dependency chain. PAD does not redefine the responsibilities owned by EIC, EOM, or ESM.

| Order | Artifact | Current Version | Responsibility |
|---:|---|---:|---|
| 1 | PAD-001 | 1.3 | Product-facing protocol contracts and transport boundary |
| 2 | EIC-001 | 1.1 | Exclusive Cognitive Engine invocation boundary |
| 3 | EOM-001 | 1.1 | Post-admission orchestration of the approved capability chain |
| 4 | ESM-001 | 1.1 | Execution-state lifecycle, transitions, and terminality |

## Architecture Release Manifests

The Architecture Release Manifest is the authoritative integrity register for its baseline. It records governance metadata and SHA-256 checksums for every released artifact. Each manifest excludes itself because self-checksumming is not stable; its checksum is pinned below and protected by repository history. Run `make verify-architecture` before every release, merge, or architecture validation.

| Baseline | Status | Manifest | Manifest SHA-256 |
|---|---|---|---|
| v1.1 | CURRENT | [RELEASE-MANIFEST-v1.1.xlsx](released/v1.1/RELEASE-MANIFEST-v1.1.xlsx) | `6232910fa5edf746922fe267e0261ddfd14cbddc1db18f47293bac1faa19db0d` |
| v1.0 | HISTORICAL | [RELEASE-MANIFEST-v1.0.xlsx](released/v1.0/RELEASE-MANIFEST-v1.0.xlsx) | `37f1b046e0035e431bb6705a7f7555f65ac42cace21f47722ede119f73732d76` |

`released/v1.1/SHA256SUMS` is retained as a legacy partial checksum list and is not the integrity authority. The restored ECOM Physical Data Model v1.3 was independently verified against the project reference library and the frozen CDD-002 archive before registration.
