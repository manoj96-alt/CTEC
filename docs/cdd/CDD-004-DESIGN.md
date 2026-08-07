# CDD-004 Enterprise Entity Resolution — Design

## Authority

This implementation consumes the frozen Canonical Enterprise Ontology and implements only ERM-001 v2.1. It introduces no canonical entity, attribute, or relationship.

## Architecture

```mermaid
flowchart LR
  SO[Source Objects] --> CD[Candidate Discovery]
  EE[Existing Enterprise Entities] --> CD
  CD --> CE[Candidate Evaluation]
  CE --> ER[Resolution Engine]
  ER --> RR[Immutable Resolution Record]
  RR --> DB[(Append-only record table)]
  RR --> HP[(Mutable history projection)]
```

The Resolution Record is an immutable domain value and append-only database row. Active/archive history is maintained outside it in an implementation projection, as required by ERM-001 v2.1.

## Sequence

```mermaid
sequenceDiagram
  participant Caller
  participant Engine
  participant Store
  Caller->>Engine: Source names + existing Enterprise Entities
  Engine->>Engine: Normalize, discover, evaluate
  Engine-->>Caller: Immutable Resolution Record
  Caller->>Store: append(record)
  Store->>Store: insert record; advance history projection
```

## Class model

```mermaid
classDiagram
  class EntityResolutionEngine
  class ResolutionPolicy
  class ResolutionCandidate
  class EnterpriseEntityResolutionRecord
  class EntityResolutionStore
  EntityResolutionEngine --> ResolutionPolicy
  EntityResolutionEngine --> ResolutionCandidate
  EntityResolutionEngine --> EnterpriseEntityResolutionRecord
  EntityResolutionStore --> EnterpriseEntityResolutionRecord
```

## Persistence

```mermaid
erDiagram
  ENTERPRISE_ENTITIES ||--o{ ENTERPRISE_ENTITY_RESOLUTION_RECORDS : "may resolve to"
  ENTERPRISE_ENTITY_RESOLUTION_RECORDS ||--o| ENTERPRISE_ENTITY_RESOLUTION_HISTORY : "is active in"
  ENTERPRISE_ENTITY_RESOLUTION_RECORDS {
    uuid record_id PK
    uuid enterprise_entity_id FK
    json supporting_source_object_ids
    string outcome
    string business_confidence
    json structured_reasons
    string narrative_explanation
    datetime produced_at
    string policy_version
  }
```

- `enterprise_entity_resolution_records`: append-only ERM business artifacts.
- `enterprise_entity_resolution_history`: implementation-owned active/archive projection.
- No canonical physical-model table is changed.
- The history projection is keyed by the deterministic digest of the supporting Source Object set.

## Configuration

Policy version and thresholds are externalized through `CTEC_RESOLUTION_*` settings. Internal numeric scores are implementation details; only High, Medium, and Low are exposed as Business Confidence.
