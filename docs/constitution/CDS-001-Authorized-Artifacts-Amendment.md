# CDS-001 — Authorized Artifacts Amendment

Version: 1.2
Status: Frozen
Amends: CDS-001 Version 1.0

## Purpose

This amendment separates authorization of business artifacts from engineering responsibility for private implementation artifacts. It applies to every CDD issued after this amendment and to any earlier CDD revised for further implementation.

Version 1.2 supersedes the implementation-artifact authorization rule in Version 1.1. It does not weaken the prohibition against inventing or modifying canonical business semantics.

## Mandatory CDD section

Every CDD must contain one of the following authorization forms.

For a CDD without an approved Business Capability Model:

```text
AUTHORIZED ARTIFACTS

Entities:
- ... or None

Services:
- ... or None

Value Objects:
- ... or None

Enums:
- ... or None
```

Each list is exhaustive for business artifacts created, modified, or exposed by the capability. A category with no authorized business artifacts must state `None` explicitly.

For a CDD implementing an approved Business Capability Model:

```text
AUTHORIZED BUSINESS CAPABILITY

Business Capability Model:
- <authoritative document identifier and version>

Business Artifacts:
- Incorporated by reference from the Business Capability Model

Externally Visible Implementation Contracts:
- ... or None

Canonical Model Changes:
- None
```

The CDD must reference the authoritative business artifacts rather than duplicate them. It must not redefine their names, meanings, attributes, relationships, lifecycle rules, or outcomes.

## Authorization rule

Only business artifacts named in `AUTHORIZED ARTIFACTS` or incorporated by an explicit reference to an approved Business Capability Model may be implemented by the assigned CDD. All other business artifacts are prohibited.

Private implementation artifacts remain the responsibility of engineering and do not require architectural authorization. Examples include internal classes, modules, functions, adapters, mappers, configuration loaders, algorithms, test fixtures, and private request or response models.

An implementation artifact requires explicit architectural authorization when it:

- Becomes part of a public API, event, file, database, or other externally visible contract
- Introduces or changes canonical business meaning
- Introduces or changes a business entity, attribute, relationship, service, value object, enum, outcome, lifecycle, or rule
- Modifies an authoritative business artifact or governed model
- Crosses or bypasses an approved architecture boundary

The following do not constitute authorization:

- Examples
- “Where appropriate” language
- Open-ended lists
- Instructions to infer business artifacts from EAD, a canonical model, a dataset, or implementation convenience
- Folder structures containing artifacts absent from the allowlist
- Artifacts merely mentioned in tests, documentation, or future-extension sections

Authoritative sources still govern the names, attributes, relationships, and meanings of an authorized artifact. Being present in an authoritative source does not by itself authorize implementation in the current CDD, except when the CDD explicitly incorporates the artifacts of an approved Business Capability Model assigned to that CDD.

Engineering freedom never authorizes changes to canonical business semantics.

## Conflict rule

If any requested output, example, test, or instruction requires an unauthorized business artifact, externally visible contract, canonical semantic change, or architecture-boundary change, implementation must stop. Codex must list every conflict and must not silently omit, infer, rename, or substitute the artifact.

If the business authorization or referenced Business Capability Model is missing, incomplete, or ambiguous, implementation must stop and request a corrected CDD. The absence of an exhaustive list of private implementation details is not an ambiguity.

## Review requirement

Every architecture review must verify:

- Every implemented business artifact appears in the CDD allowlist or its explicitly referenced Business Capability Model.
- Every authorized business artifact was either implemented or explicitly reported as blocked.
- No business artifact was inferred from examples, datasets, or adjacent layers.
- No unauthorized business entity, service, value object, enum, outcome, lifecycle, or rule was introduced.
- Private implementation artifacts remain internal and do not alter canonical business semantics.
- Externally visible implementation contracts received explicit architectural authorization.

This authorization audit is part of the CDS-001 five-hat review and architecture-drift check.
