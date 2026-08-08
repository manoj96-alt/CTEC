# CDD-006 Architecture Clarification Report

Status: HISTORICAL — RESOLVED
Capability: Assertion  
Authority: ASM-001 v1.0 FROZEN

## Resolution

- Resolved By: ASM-001 v2.0, SRM-001 v2.1, and RFC-011
- Resolution Date: 2026-08-08
- Superseding Version(s): ASM-001 v2.1

ASM-001 v2.0 supplied the complete Assertion business contract, while ASM-001 v2.1 and RFC-011 aligned immutable history and externally determined currentness. This report is retained only as historical review evidence and is excluded from current release-gate blocker evaluation.

## Finding

ASM-001 v1.0 defines the Assertion capability boundary and intent but does not fully specify the Assertion Record’s business semantics. CDD-006 cannot choose the missing semantics because CDS-001 assigns business vocabulary, artifacts, lifecycle, and meaning exclusively to the BCS.

## Required clarifications

1. **Assertion representation**
   - `Assertion` is defined only as “governed enterprise belief.”
   - The specification does not state whether an Assertion Record references the existing canonical Assertion, contains a structured subject/predicate/object belief, or contains literal statement text.
   - The illustrative sentence does not authorize a record representation or cardinality.

2. **Assertion Outcome is absent from the record**
   - ASM-001 defines Established, Candidate, and Rejected outcomes, but `Assertion Outcome` is not an attribute in the Assertion Record Specification.
   - The record cannot preserve or trace its outcome without adding an unauthorized business attribute.

3. **Outcome-to-assertion rules**
   - The specification does not define whether all three outcomes contain the same Assertion representation, whether Candidate may contain multiple proposed assertions, or whether Rejected retains the rejected belief.

4. **Identity of an “identical assertion”**
   - Current-belief cardinality is keyed by Enterprise Entity plus “identical assertion,” but equality is undefined.
   - A deterministic external history key cannot be created until the governed identity components of an Assertion are defined.

5. **Evidence consistency rules**
   - Minimum evidence cardinality is defined, but the specification does not state whether the Enterprise Entity Resolution Record and Semantic Resolution Record must refer to the record’s Enterprise Entity, or whether the Semantic Resolution Record must be the current interpretation.

6. **Human override scope**
   - ASM-001 permits a replacement record but does not define which business values an authorized user may override: Assertion, outcome, Business Confidence, or any combination.

7. **Superseded authority reference**
   - ASM-001 v1.0 traces to SRM-001 v2.0. The frozen authority used by CDD-005 is SRM-001 v2.1, which supersedes v2.0 and defines the evidence artifact consumed by Assertion.

## Requested business decisions

Issue a frozen ASM-001 revision that defines:

- the Assertion representation and cardinality;
- Assertion Outcome as an explicit record attribute;
- outcome-specific Assertion rules;
- the identity rule for current-belief history;
- evidence consistency constraints;
- permitted human-override scope; and
- SRM-001 v2.1 as the semantic-resolution authority.

## Architecture drift check

- No canonical entity, attribute, or relationship was introduced or modified.
- No EAH, RFC, EAD, ERM, SRM, ASM, Logical Model, or Physical Model was modified.
- No architecture layer was bypassed.
- No technology was introduced.
- No CDD-006 implementation code was created.

CDD-006 implementation is stopped until a frozen ASM revision resolves these business-artifact semantics.
