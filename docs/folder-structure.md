# Folder Structure

- `cognitive-engine/backend/app/api`: HTTP delivery for health, public config, and version only.
- `cognitive-engine/backend/app/core`: cross-cutting configuration, logging, errors, and composition.
- `cognitive-engine/backend/app/domain`: reserved domain-module boundaries; empty in CDD-001.
- `cognitive-engine/backend/app/application`: reserved use-case boundary; empty in CDD-001.
- `cognitive-engine/backend/app/infrastructure`: reserved adapters; no persistence implementation in CDD-001.
- `cognitive-engine/frontend/app`: App Router pages and layout.
- `cognitive-engine/frontend/components`: reusable presentation-only components.
- `cognitive-engine/deployment`: reserved deployment extensions; Compose remains at repository root.
- `sample-data/edt-001`: immutable demo dataset versions; no loader is implemented in CDD-001.
- `cognitive-engine/tools`: reserved reusable engineering utilities; unlike one-off `cognitive-engine/scripts`, tools may become tested packages in an assigned later layer.
- `docs`: architecture and developer guidance.
