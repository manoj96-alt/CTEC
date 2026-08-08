# CDD-009 — Governance Engine

Status: Implementation complete; awaiting formal review and freeze.

The Governance Engine answers one question: can the enterprise trust this immutable cognitive record under its governing enterprise policy?

It supports Compliant, Non-Compliant, Exception Granted, and Requires Review evaluations; business confidence classification; structured and narrative explanation; policy traceability; GEM-001 exception validation; append-only history; human override through replacement records; RFC-011 currentness; and outcome-neutral Governance Attestation derivation.

Governance evaluates only. It does not modify governed records or policies, authorize exceptions, execute operational action, persist Governance Attestations, or persist Enterprise Trust.

## Configuration

The following `CTEC_` environment settings are supported:

- `GOVERNANCE_POLICY_REFERENCE`
- `GOVERNANCE_POLICY_VERSION`
- `GOVERNANCE_AUTHORIZED_EXCEPTION_AUTHORITIES`
- `GOVERNANCE_HIGH_CONFIDENCE_THRESHOLD`
- `GOVERNANCE_MEDIUM_CONFIDENCE_THRESHOLD`

Configuration selects implementation behavior only. GRM-001 and GEM-001 remain authoritative for business meaning.

## Verification

Run `make lint`, `make typecheck`, and `make test`. PostgreSQL migration tests require `CTEC_TEST_DATABASE_URL`.

## Repository tree

```text
cognitive-engine/backend/app/
├── application/
│   └── governance_engine.py
├── domain/governance_engine/
│   ├── __init__.py
│   ├── configuration.py
│   ├── model.py
│   └── service.py
├── infrastructure/persistence/
│   ├── governance_repository.py
│   ├── migrations/versions/0007_governance_evaluation.py
│   └── models/governance_evaluation.py
└── tests/test_governance_engine.py

docs/cdd/
├── CDD-009-DESIGN.md
├── CDD-009-README.md
└── CDD-009-REVIEW.md
```

## Files created

- `cognitive-engine/backend/app/application/governance_engine.py`
- `cognitive-engine/backend/app/domain/governance_engine/__init__.py`
- `cognitive-engine/backend/app/domain/governance_engine/configuration.py`
- `cognitive-engine/backend/app/domain/governance_engine/model.py`
- `cognitive-engine/backend/app/domain/governance_engine/service.py`
- `cognitive-engine/backend/app/infrastructure/persistence/governance_repository.py`
- `cognitive-engine/backend/app/infrastructure/persistence/migrations/versions/0007_governance_evaluation.py`
- `cognitive-engine/backend/app/infrastructure/persistence/models/governance_evaluation.py`
- `cognitive-engine/backend/app/tests/test_governance_engine.py`
- `docs/cdd/CDD-009-DESIGN.md`
- `docs/cdd/CDD-009-README.md`
- `docs/cdd/CDD-009-REVIEW.md`

## Files modified

- `.env.example`
- `cognitive-engine/backend/app/core/config.py`
- `cognitive-engine/backend/app/infrastructure/persistence/models/__init__.py`
- `cognitive-engine/backend/app/tests/test_decision_engine.py`
- `cognitive-engine/backend/app/tests/test_knowledge_engine.py`
- `cognitive-engine/backend/app/tests/test_persistence_integration.py`
