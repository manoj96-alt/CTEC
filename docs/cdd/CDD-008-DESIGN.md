# CDD-008 Decision Engine — Design

CDD-008 implements DRM-001 v1.1. It evaluates existing Institutional Knowledge against a referenced governed business policy and creates an immutable Decision Evaluation Record. It does not approve policy, create knowledge, execute recommendations, or expose external query capability.

## Architecture

```mermaid
flowchart LR
    K[Institutional Knowledge] --> A[Decision Application Service]
    P[Governing Business Policy] --> A
    A --> D[Decision Domain Services]
    D --> R[Decision Evaluation Repository]
    R --> S[(Append-only Decision Records)]
    S --> H[History Projection]
    S --> C[Currentness Projection]
```

## Sequence

```mermaid
sequenceDiagram
    participant Caller
    participant Application as DecisionApplicationService
    participant Domain as DecisionEvaluationService
    participant Repository as DecisionEvaluationRepositoryImpl
    participant Database
    Caller->>Application: DecisionEvaluationRequest
    Application->>Domain: evaluate institutional knowledge and policy
    Domain-->>Application: immutable DecisionEvaluationRecord
    Application->>Repository: append DecisionPersistenceModel
    Repository->>Database: verify Institutionalized knowledge
    Repository->>Database: INSERT record
    Application-->>Caller: DecisionEvaluationResponse
```

## Class model

```mermaid
classDiagram
    DecisionApplicationService --> DecisionEvaluationService
    DecisionApplicationService --> DecisionEvaluationRepository
    DecisionEvaluationService --> DecisionEvaluationRecord
    DecisionEvaluationRecord *-- DecisionRecommendation
    DecisionEvaluationRecord *-- DecisionExplanation
    DecisionEvaluationRecord *-- DecisionConfidence
    DecisionConfidence *-- DecisionConfidenceLevel
    DecisionEvaluationRepository <|.. DecisionEvaluationRepositoryImpl
    DecisionEvaluationRepositoryImpl --> DecisionEvaluationORM
```

## Persistence

```mermaid
erDiagram
    KNOWLEDGE_EVALUATION_RECORDS ||--o{ DECISION_EVALUATION_RECORDS : "referenced after Institutionalized validation"
    DECISION_EVALUATION_RECORDS {
        uuid record_identifier PK
        jsonb knowledge_references
        string decision_recommendation
        string evaluation_outcome
        string decision_confidence
        jsonb structured_reasons
        string narrative_explanation
        string governing_policy_reference
        string policy_version
        timestamptz effective_from
        timestamptz produced_timestamp
        string decision_identity_key
    }
```

Knowledge references are stored as a governed reference set because each Decision Evaluation consumes one or more Institutional Knowledge items. Repository validation ensures every reference points to an Institutionalized Knowledge Evaluation. No assertion, semantic resolution, or entity-resolution source can be supplied directly.

The decision identity key is an internal SHA-256 projection key derived from the sorted Supporting Knowledge set, Decision Recommendation, and optional Business Context. It is not a business attribute. RFC-011 currentness orders matching records by Effective From, Produced Timestamp, and Record Identifier, descending; future-effective records are excluded until effective.

PostgreSQL rejects UPDATE and DELETE operations through a dedicated trigger. Human override therefore creates a new record.
