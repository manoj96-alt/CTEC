# CDD-005 Architecture Clarification Report

Status: BLOCKING  
Capability: Semantic Resolution  
Authority reviewed: EAH-001, RFC-010, CDD-003 Revision 2, EAD-001, ERM-001 v2.1, SRM-001 v1.0, CDS-001 v1.2

## Finding

CDD-005 cannot be implemented without selecting business semantics that SRM-001 v1.0 does not currently specify. CDS-001 makes the BCS the sole authority for business vocabulary, artifacts, lifecycle, semantics, and boundaries; engineering therefore cannot make these selections.

## Required clarifications

1. **Semantic Interpretation representation**
   - SRM-001 defines it as “Enterprise meaning assigned” but does not state whether it references an existing Institutional Concept, Relationship Type, another governed vocabulary item, or a literal value.
   - RFC-010 says Semantic Resolution consumes Enterprise Entity, Institutional Concept, and Relationship Type. The exact permitted target and cardinality remain undefined.

2. **Business Context representation**
   - SRM-001 says “Business domain or context in which meaning applies.” It does not specify whether this is a Business Domain reference, Context reference, either type, both types, or a literal description.
   - Choosing among these options would define a business relationship and is not an engineering decision.

3. **Supporting Evidence types and cardinality**
   - SRM-001 defines “references to supporting records” without identifying permitted record types, minimum cardinality, or whether Source Object and Enterprise Entity Resolution Record are both mandatory evidence.
   - The inputs list alone does not define the Resolution Record’s provenance contract.

4. **Immutable record versus Record Status**
   - SRM-001 requires immutable Semantic Resolution Records and also places mutable-looking `Active` or `Archived` Record Status inside the record.
   - It does not state whether status is immutable at creation, whether archiving creates a new record, or whether lifecycle history must be maintained outside the record as ERM-001 v2.1 requires for entity resolution.

5. **Current interpretation and record cardinality**
   - SRM-001 does not define the business key for one enterprise understanding or how the current Semantic Resolution Record is selected when meaning differs by context or policy version.
   - Archive behavior and human override cannot be implemented consistently until this is defined.

6. **Outcome-to-interpretation rule**
   - The three outcomes are listed, but SRM-001 does not state whether `Possible Resolution` must reference one proposed interpretation, may reference multiple candidates, or whether `Unresolved` must omit Semantic Interpretation.

7. **Business Confidence applicability**
   - Business Confidence is independent of outcome, but SRM-001 does not explicitly confirm that every High/Medium/Low classification is valid for every outcome. ERM-001 v2.1 made this explicit for identity resolution; applying that rule here by analogy would invent semantic-resolution business meaning.

## Requested business decisions

Issue an SRM-001 revision that explicitly defines:

- the permitted references/cardinality for Semantic Interpretation;
- the permitted references/cardinality for Business Context;
- permitted Supporting Evidence record types and minimum cardinality;
- immutable-record lifecycle, external history policy, and current-record determination;
- outcome constraints on Semantic Interpretation; and
- the Business Confidence/outcome validity matrix.

## Architecture drift check

- No business entity was introduced.
- No existing entity was modified.
- No canonical relationship was changed.
- No canonical attribute was invented.
- No RFC was violated.
- No architecture layer was bypassed.
- No technology outside TAS-001 was introduced.
- No CDD-005 implementation code was created.

Implementation is stopped until a frozen SRM revision resolves these points.
