# CDD-007 Architecture Clarification Report

Status: HISTORICAL — RESOLVED
Capability: Knowledge  
Authority: KRM-001 v1.1 FROZEN

## Finding

KRM-001 v1.1 defines the Knowledge capability boundary, the Knowledge Evaluation Record, and its outcome-specific requirements. CDD-007 additionally requires Acceptance Evidence Validation, Knowledge Outcome Evaluation, ordered evaluation history, and deterministic current-record selection. The authoritative business specification does not fully define the semantics needed for those operations.

Implementing them now would require Engineering to invent business attributes or decision rules for a Governance-owned artifact. CDS-001 and CDD-007 prohibit that.

## Required clarifications

### 1. Acceptance Evidence contract

KRM-001 defines Acceptance Evidence as documented evidence produced by Governance and consumed by Knowledge, but it does not define:

- the minimum information by which Knowledge can reference the evidence;
- whether a Knowledge Evaluation Record references exactly one or one-or-more evidence items;
- how the evidence identifies the Assertion whose acceptance it demonstrates;
- how the applicable policy and policy version are associated with the evidence; or
- whether Acceptance Evidence is immutable.

CDD-007 cannot define an Acceptance Evidence DTO or persistence representation without choosing these business semantics.

### 2. Acceptance Evidence validation result

CDD-007 authorizes Acceptance Evidence Validation, but the authorities do not define what validation establishes. It is unclear whether validation means:

- verifying only that evidence is present;
- verifying that it was produced by an authorized Governance capability;
- verifying that it applies to the referenced Assertion;
- verifying that it satisfies the referenced policy version; or
- some combination of these conditions.

The distinction is material because only demonstrated institutional acceptance may establish Institutional Knowledge.

### 3. Outcome precedence and invalid combinations

KRM-001 states the requirements for each outcome but does not define the result when inputs conflict. In particular:

- both valid Acceptance Evidence and a Rejection Explanation may be supplied;
- Acceptance Evidence may be supplied but fail validation;
- a Rejection Explanation may be absent when policy evaluation rejects an Assertion; or
- no evidence may be supplied while an explicit outcome is requested.

Engineering cannot safely choose whether these cases are Candidate, Rejected, or invalid without defining business outcome semantics.

### 4. Ordered history and currentness

KRM-001 says that current knowledge understanding is determined from the ordered history of evaluation records, but it does not define:

- whether ordering uses `Produced Timestamp`, `Effective From`, or both;
- how ties are resolved deterministically;
- how future-effective records participate in currentness; or
- whether a later-produced backdated record becomes current.

CDD-007 cannot implement the “only one current Knowledge Evaluation” rule or a current-record query without this decision.

### 5. Human override to Candidate

KRM-001 requires new Acceptance Evidence or a new Rejection Explanation “as appropriate” when an override changes Evaluation Outcome. The required input for an override to Candidate is not stated, nor is it clear whether an override may change only Knowledge Confidence while retaining the prior outcome evidence.

## Requested business decisions

Issue a frozen KRM clarification, or an authoritative Governance capability contract referenced by KRM, that defines:

1. the minimum Acceptance Evidence business contract and cardinality;
2. the complete Acceptance Evidence validation meaning;
3. outcome precedence and invalid input combinations;
4. the ordering and effective-dating rule used to determine current knowledge understanding; and
5. the permitted Human Override transitions and their required supporting information.

The clarification should remain technology-neutral. Engineering can then choose DTOs, schema, repositories, configuration format, and APIs without changing business meaning.

## Architecture drift check

- No EAH or RFC was changed or violated.
- No CEO entity, attribute, or relationship was introduced or modified.
- No EAD, ERM, SRM, ASM, or KRM artifact was modified.
- No Logical Model or Physical Model was modified.
- No architecture layer was bypassed.
- No technology was introduced.
- No CDD-007 runtime, persistence, migration, API, or test code was created.

## Resolution

- Resolved By: AEM-001 v1.0, RFC-011, and KRM-001 v1.2
- Resolution Date: 2026-08-08
- Superseding Version(s): AEM-001 v1.1; KRM-001 v1.3; RFC-013

This report is retained only as historical review evidence and is excluded from current release-gate blocker evaluation.

- AEM-001 v1.0 supplies the immutable Acceptance Evidence contract and validation rules.
- RFC-011 v1.0 supplies deterministic immutable-record ordering and currentness rules.
- KRM-001 v1.2 references both frozen authorities.

CDD-007 implementation resumed after these documents were frozen. The original findings are retained as an auditable record of why implementation initially stopped.
