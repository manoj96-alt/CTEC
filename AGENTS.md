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

## Git workflow

- Keep commits scoped to one assigned layer or review correction.
- Do not combine formatting-only changes with unrelated behavior.
- Never commit `.env`, secrets, local caches, coverage output, or build artifacts.
- Run `make lint`, `make typecheck`, and `make test` before review.

## Naming conventions

- Python: `snake_case` modules/functions, `PascalCase` types, `UPPER_SNAKE_CASE` constants.
- TypeScript: `kebab-case` filenames, `PascalCase` components/types, `camelCase` values.
- Domain terms must match the frozen Constitution, RFCs, models, and attribute dictionary exactly.

## Architecture rules

- Architecture and the assigned CDD always override implementation convenience.
- Do not introduce or modify business entities, relationships, or attributes without explicit authorization.
- Respect dependency direction and modular-monolith boundaries; do not add microservices.
- Stop at the assigned layer. Report missing specifications rather than inventing behavior.

## Authorized artifacts

Every CDD must contain an explicit `AUTHORIZED ARTIFACTS` section listing the exact business Entities, Services, Value Objects, and Enums it may implement, or explicitly incorporate the authoritative business artifacts of an approved Business Capability Model. Private implementation artifacts are engineering responsibilities and need no architectural authorization unless they become externally visible, change canonical business semantics, or cross an architecture boundary. Examples, datasets, and adjacent layers do not authorize business artifacts. If business authorization is absent or ambiguous, stop before implementation.

## Prompt rules

- Treat CDS, CDD, Constitution, RFC, TAS, logical model, physical model, attribute dictionary, and dataset documents as authoritative.
- Perform an architecture-drift check before completion.
- Record design decisions, alternatives, and rejection reasons.
