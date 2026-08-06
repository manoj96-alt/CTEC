# Architecture Overview

CTEC is a modular monolith with dependency direction from delivery and infrastructure toward application and domain boundaries. CDD-001 implements only the composition root and delivery scaffolding. Domain module directories are placeholders and contain no entities or behavior. PostgreSQL is provisioned but has no CTEC tables or migrations. No later-layer capability is implemented.

The canonical Constitution, RFC, TAS, logical-model, physical-model, and dataset references are maintained in the project-level `reference-library/`. The matching directories under `docs/` are documentation boundaries, not copies of those frozen sources.
