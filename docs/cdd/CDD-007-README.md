# CDD-007 Knowledge Engine

CDD-007 evaluates an existing Assertion using externally produced Acceptance Evidence and creates an immutable Knowledge Evaluation Record.

Only an `Institutionalized` outcome establishes Institutional Knowledge. `Candidate` and `Rejected` records preserve evaluation history without creating Institutional Knowledge. Governance approval is never granted or produced by this capability.

The implementation includes typed domain records, configurable confidence classification and authorized authorities, AEM-001 evidence validation, human override through replacement records, append-only PostgreSQL persistence, and RFC-011 currentness queries.

Decision, Governance, Experience, Reasoning, Learning, and canonical-model changes remain out of scope.

## Files changed

- `backend/app/domain/knowledge_engine/` — immutable artifacts, evidence validation, evaluation, confidence, and override.
- `backend/app/infrastructure/persistence/knowledge_evaluation_store.py` — append and RFC-011 history/currentness queries.
- `backend/app/infrastructure/persistence/models/knowledge_evaluation.py` — dedicated ORM model.
- `backend/app/infrastructure/persistence/migrations/versions/0005_knowledge_evaluation_records.py` — append-only schema and mutation trigger.
- `backend/app/core/config.py` — external knowledge-policy configuration.
- `backend/app/tests/test_knowledge_engine.py` — domain, configuration, persistence, history, and migration tests.
- `docs/cdd/CDD-007-*` — design, clarification history, review, and this handoff.
