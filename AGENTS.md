# CTEC Engineering Playbook

This playbook applies to all work under `ctec/`.

## Coding standards

- Follow CDS-001, SOLID, Clean Architecture, Domain-Driven Design, and the Repository Pattern.
- Prefer explicit, typed, testable code with the fewest necessary dependencies.
- Business logic belongs only in domain services authorized by the current CDD.
- API and UI code must not access persistence directly.

## Review process

Every CDD must pass CR-001 before it can be frozen:

1. Gate A — Repository and Architecture Review
2. Gate B — Code Quality Review
3. Gate C — Business Workflow Review

Complete the CDS-001 five-hat review and architecture-drift check at every gate.

If a CDD references an approved Business Capability Specification (BCS), that BCS is the sole authority for business semantics. Reviewers must not require duplication of those semantics within the CDD.

## Git workflow

- Keep commits scoped to one assigned layer or review correction.
- Do not combine formatting-only changes with unrelated behavior.
- Never commit `.env`, secrets, local caches, coverage output, or build artifacts.
- Run `make lint`, `make typecheck`, and `make test` before review.
- Run `make verify-architecture` before every architecture release, merge, or architecture validation. Any missing artifact, unregistered artifact, or checksum mismatch is a release blocker.

## Naming conventions

- Python: `snake_case` modules/functions, `PascalCase` types, `UPPER_SNAKE_CASE` constants.
- TypeScript: `kebab-case` filenames, `PascalCase` components/types, `camelCase` values.
- Domain terms must match the frozen Constitution, RFCs, models, and attribute dictionary exactly.

## Architecture rules

- Resolve every authoritative architecture artifact through `architecture/INDEX.md`. Never use personal Downloads folders, attachments, legacy documentation paths, or unmerged branches as architecture sources.
- Treat the baseline `RELEASE-MANIFEST-<version>.xlsx` referenced by the registry as the authoritative integrity register. Regenerate it whenever an architecture artifact is added, superseded, or frozen; the manifest itself is protected by its SHA-256 recorded in the registry.
- Governance status comes only from the Architecture Registry and Release Manifest. Filename suffixes such as `_FROZEN`, embedded document labels, and directory placement are informational and never establish authority.
- Only documents marked `CURRENT` in the registry may govern implementation. `SUPERSEDED` artifacts are retained for audit history only.
- Architecture Clarification Reports marked `HISTORICAL — RESOLVED` or `HISTORICAL — PARTIALLY RESOLVED` are review evidence, not governing architecture. Release-gate validation and automated blocker checks must exclude their historical findings; any explicitly identified open finding in a partially resolved report remains governed by the current artifact named in its Resolution section.
- Architecture and the assigned CDD always override implementation convenience.
- Do not introduce or modify business entities, relationships, or attributes without explicit authorization.
- Respect dependency direction and modular-monolith boundaries; do not add microservices.
- Stop at the assigned layer. Report missing specifications rather than inventing behavior.
- Use RFC-011 immutable-record terminology for cognitive capabilities: `current_record_identifier`, `record_history`, and `historical_record_references`. Currentness must be determined externally from ordered immutable history; no cognitive record changes state from active to archived. Legacy physical column names may remain only as documented compatibility details.

## Authorized artifacts

Every CDD must contain an explicit `AUTHORIZED ARTIFACTS` section listing the exact business Entities, Services, Value Objects, and Enums it may implement, or explicitly incorporate the authoritative business artifacts of an approved Business Capability Specification (BCS). Private implementation artifacts are engineering responsibilities and need no architectural authorization unless they become externally visible, change canonical business semantics, or cross an architecture boundary. Examples, datasets, and adjacent layers do not authorize business artifacts. If business authorization is absent or ambiguous, stop before implementation.

## Prompt rules

- Treat CDS, CDD, Constitution, RFC, TAS, logical model, physical model, attribute dictionary, and dataset documents as authoritative.
- Perform an architecture-drift check before completion.
- Record design decisions, alternatives, and rejection reasons.
