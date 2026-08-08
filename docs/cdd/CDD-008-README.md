# CDD-008 — Decision Engine

Status: Implementation complete; awaiting formal review and freeze.

The Decision Engine answers one question: given existing Institutional Knowledge and a governed business policy, what should the enterprise recommend?

It supports Recommended, Candidate, and Rejected evaluations; business confidence classification; structured and narrative explanation; policy-version traceability; append-only history; human override through replacement records; and RFC-011 currentness determination.

An Enterprise Decision exists only for a Recommended evaluation. The engine never executes the recommendation.

## Configuration

The following `CTEC_` environment settings are supported:

- `DECISION_POLICY_REFERENCE`
- `DECISION_POLICY_VERSION`
- `DECISION_HIGH_CONFIDENCE_THRESHOLD`
- `DECISION_MEDIUM_CONFIDENCE_THRESHOLD`

Configuration selects implementation behavior only. DRM-001 remains the authority for business meaning.

## Verification

Run `make lint`, `make typecheck`, and `make test`. PostgreSQL migration tests require `CTEC_TEST_DATABASE_URL`.

## Repository tree

```text
cognitive-engine/backend/app/
├── application/
│   └── decision_engine.py
├── domain/decision_engine/
│   ├── configuration.py
│   ├── model.py
│   └── service.py
├── infrastructure/persistence/
│   ├── decision_repository.py
│   ├── migrations/versions/0006_decision_evaluation.py
│   └── models/decision_evaluation.py
└── tests/test_decision_engine.py

docs/cdd/
├── CDD-008-DESIGN.md
├── CDD-008-README.md
└── CDD-008-REVIEW.md
```

## Files created

- `cognitive-engine/backend/app/application/__init__.py`
- `cognitive-engine/backend/app/application/decision_engine.py`
- `cognitive-engine/backend/app/domain/decision_engine/__init__.py`
- `cognitive-engine/backend/app/domain/decision_engine/configuration.py`
- `cognitive-engine/backend/app/domain/decision_engine/model.py`
- `cognitive-engine/backend/app/domain/decision_engine/service.py`
- `cognitive-engine/backend/app/infrastructure/persistence/decision_repository.py`
- `cognitive-engine/backend/app/infrastructure/persistence/migrations/versions/0006_decision_evaluation.py`
- `cognitive-engine/backend/app/infrastructure/persistence/models/decision_evaluation.py`
- `cognitive-engine/backend/app/tests/test_decision_engine.py`
- `docs/cdd/CDD-008-DESIGN.md`
- `docs/cdd/CDD-008-README.md`
- `docs/cdd/CDD-008-REVIEW.md`

## Files modified

- `cognitive-engine/backend/app/core/config.py`
- `cognitive-engine/backend/app/infrastructure/persistence/models/__init__.py`
- `cognitive-engine/backend/app/tests/test_knowledge_engine.py`
- `cognitive-engine/backend/app/tests/test_persistence_integration.py`
