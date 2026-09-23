## CDD

- CDD identifier and title:
- Assigned layer:
- Related issue:

## Summary

Describe what this pull request changes and why.

## Scope

- [ ] This pull request implements exactly one CDD.
- [ ] Only the assigned layer is implemented.
- [ ] No unrelated refactoring or feature work is included.

## Architecture drift check

- [ ] No new business entity was introduced without authorization.
- [ ] No existing entity was modified without authorization.
- [ ] No relationship was changed without authorization.
- [ ] No attribute was invented.
- [ ] No RFC was violated.
- [ ] No architecture layer was bypassed.
- [ ] No technology outside TAS-001 was introduced.

List and explain any approved deviations, or write `None`:

## CR-001 review gates

- [ ] Gate A — Repository and Architecture Review passed.
- [ ] Gate B — Code Quality Review passed.
- [ ] Gate C — Business Workflow Review passed or was recorded as not applicable.

## Five-hat review

- [ ] Principal Software Engineer — PASS
- [ ] Chief Architect — PASS
- [ ] Enterprise Business User — PASS
- [ ] Startup CTO — PASS
- [ ] QA Engineer — PASS

## Validation

List the exact commands run and their results:

```text
make lint
make typecheck
make test
```

## Design decisions

Record decisions, reasons, alternatives, and rejection reasons.

## Remaining work

List work explicitly deferred to later CDDs.
