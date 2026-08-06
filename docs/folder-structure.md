# Folder Structure

- `backend/app/api`: HTTP delivery for health, public config, and version only.
- `backend/app/core`: cross-cutting configuration, logging, errors, and composition.
- `backend/app/domain`: reserved domain-module boundaries; empty in CDD-001.
- `backend/app/application`: reserved use-case boundary; empty in CDD-001.
- `backend/app/infrastructure`: reserved adapters; no persistence implementation in CDD-001.
- `frontend/app`: App Router pages and layout.
- `frontend/components`: reusable presentation-only components.
- `deployment`: reserved deployment extensions; Compose remains at repository root.
- `datasets/edt-001`: immutable demo dataset versions; no loader is implemented in CDD-001.
- `tools`: reserved reusable engineering utilities; unlike one-off `scripts`, tools may become tested packages in an assigned later layer.
- `docs`: architecture and developer guidance.
