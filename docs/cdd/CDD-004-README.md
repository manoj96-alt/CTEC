# CDD-004 Enterprise Entity Resolution Engine

CDD-004 answers one question: which existing Enterprise Entity does a Source Object represent?

The engine normalizes source and enterprise names, discovers and evaluates candidates, classifies the outcome and Business Confidence, produces an explanation, and returns an immutable ERM-001 v2.1 Resolution Record. Human override produces a new record; it never mutates prior understanding. The persistence adapter appends records and maintains active/archive history outside those records.

Policy version and numeric thresholds are configured through `CTEC_RESOLUTION_*` environment settings. Numeric scores remain internal engineering details.

This capability does not create Enterprise Entities and performs no semantic resolution, assertions, knowledge, governance, reasoning, learning, or recommendation work.

## Repository tree

```text
backend/app/
├── core/config.py
├── domain/identity_resolution/
│   ├── model.py
│   └── service.py
├── infrastructure/persistence/
│   ├── entity_resolution_store.py
│   ├── migrations/versions/0002_entity_resolution.py
│   └── models/entity_resolution.py
└── tests/
    ├── test_identity_resolution.py
    └── test_identity_resolution_persistence.py
docs/cdd/
├── CDD-004-DESIGN.md
├── CDD-004-README.md
└── CDD-004-REVIEW.md
```

## Files changed

The CDD adds the identity-resolution domain package, append-only persistence adapter and migration, unit and PostgreSQL integration tests, external policy settings, and its design/review documentation. Existing CDD-003 guard tests now explicitly scope their exact-set checks to canonical CEO artifacts, preserving those frozen checks while excluding the separately authorized ERM artifact.

## Verification

From `backend/`:

```bash
ruff check app
mypy app
pytest
```

PostgreSQL persistence coverage runs when `CTEC_TEST_DATABASE_URL` is set.
