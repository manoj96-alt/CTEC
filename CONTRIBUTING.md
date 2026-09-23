# Contributing to CTEC

CTEC is developed as a sequence of controlled Codex Development Documents (CDDs). Architecture correctness takes precedence over implementation convenience.

## One CDD, one pull request

Each CDD must correspond to exactly one pull request. Do not combine multiple CDDs or unrelated maintenance in the same branch.

Examples:

- PR #1 — CDD-001 Project Foundation
- PR #2 — CDD-002 Persistence Layer
- PR #3 — CDD-003 Canonical Domain Layer

Use a branch named `agent/cdd-NNN-short-description` and a pull-request title beginning with the CDD identifier.

## Development workflow

1. Create or assign the CDD issue using the CDD issue form.
2. Read the approved CDD and all referenced Constitution, RFC, model, TAS, EAD, and dataset artifacts.
3. Implement only the assigned layer and obey its stop rule.
4. Add or update tests and documentation in the same pull request.
5. Run the local quality gates:

   ```bash
   make lint
   make typecheck
   make test
   ```

6. Complete the pull-request template, architecture-drift check, CR-001 gates, and five-hat review.
7. Obtain CODEOWNER approval before merge.
8. Squash or merge according to the repository's configured GitHub policy; do not bypass required checks.

## Commit and review scope

- Keep commits focused and use imperative summaries.
- Never commit secrets, `.env`, generated output, caches, or customer data.
- Do not introduce technologies outside TAS-001.
- Do not invent or alter business entities, relationships, attributes, or terminology.
- Report a missing specification rather than filling the gap by assumption.

See [ARCHITECTURE.md](ARCHITECTURE.md), [the Engineering Playbook](AGENTS.md), and [CR-001](docs/review/CR-001.md).
