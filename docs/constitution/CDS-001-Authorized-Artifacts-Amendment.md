# CDS-001 — Authorized Artifacts Amendment

Version: 1.1  
Status: Frozen  
Amends: CDS-001 Version 1.0

## Purpose

This amendment replaces inference-based implementation scope with an explicit allowlist. It applies to every CDD issued after this amendment and to any earlier CDD revised for further implementation.

## Mandatory CDD section

Every CDD must contain the following section:

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

Each list is exhaustive. A category with no authorized artifacts must state `None` explicitly.

## Authorization rule

Only artifacts named in `AUTHORIZED ARTIFACTS` may be created by the assigned CDD. Everything else is prohibited.

The following do not constitute authorization:

- Examples
- “Where appropriate” language
- Open-ended lists
- Instructions to infer artifacts from EAD, a model, a dataset, or implementation convenience
- Folder structures containing artifacts absent from the allowlist
- Artifacts merely mentioned in tests, documentation, or future-extension sections

Authoritative sources still govern the names, attributes, relationships, and meanings of an authorized artifact. Being present in an authoritative source does not by itself authorize implementation in the current CDD.

## Conflict rule

If any requested output, folder, example, test, or instruction requires an artifact not listed in `AUTHORIZED ARTIFACTS`, implementation must stop. Codex must list every conflict and must not silently omit, infer, rename, or substitute artifacts.

If the section is missing, incomplete, or ambiguous, implementation must stop and request a corrected CDD.

## Review requirement

Every architecture review must verify:

- Every created artifact appears in the CDD allowlist.
- Every allowlisted artifact was either implemented or explicitly reported as blocked.
- No artifact was inferred from examples or adjacent layers.
- No unauthorized entity, service, value object, or enum was introduced.

This authorization audit is part of the CDS-001 five-hat review and architecture-drift check.
