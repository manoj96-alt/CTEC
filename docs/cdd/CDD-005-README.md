# CDD-005 Semantic Resolution Engine

CDD-005 assigns governed Institutional Concepts to identified Enterprise Entities within one governed Context. It supports resolved, possible, and unresolved outcomes; explainable candidate interpretations; Business Confidence; immutable records; external history; human override; and policy traceability.

Configuration uses `CTEC_SEMANTIC_*`. No assertions, knowledge, governance, AI reasoning, or CEO changes are included.

Run from `cognitive-engine/backend/`: `black --check .`, `ruff check app`, `mypy app`, and `pytest`.

Changed areas are `domain/semantic_resolution`, semantic persistence models/store/migration, configuration, tests, and these CDD-005 documents.
