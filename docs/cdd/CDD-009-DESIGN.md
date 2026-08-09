# CDD-009 Governance Engine — Design

CDD-009 implements GRM-001 v1.2 and consumes GEM-001 v1.1 under RFC-013 v1.1. It evaluates one existing immutable cognitive record against a configured governing enterprise policy and appends one immutable Governance Evaluation Record. The outcome-neutral Governance Attestation is derived from that record and is never persisted independently. Enterprise Trust is neither modeled nor persisted.

## Architecture

```mermaid
flowchart LR
    C[Immutable Cognitive Record] --> A[Governance Application Service]
    P[Governing Enterprise Policy] --> A
    X[Exception Authorization] -. "Exception Granted only" .-> A
    A --> D[Governance Domain Services]
    D --> R[Governance Evaluation Repository]
    R --> S[(Append-only Governance Records)]
    S --> H[History Projection]
    S --> U[Currentness Projection]
    D --> T[Derived Governance Attestation]
```

## Sequence

```mermaid
sequenceDiagram
    participant Caller
    participant Application as GovernanceApplicationService
    participant Domain as GovernanceEvaluationService
    participant Repository as GovernanceEvaluationRepositoryImpl
    participant Database
    Caller->>Application: GovernanceEvaluationRequest
    Application->>Application: validate policy and exception authorization
    Application->>Domain: evaluate governed record
    Domain-->>Application: immutable GovernanceEvaluationRecord
    Application->>Repository: append GovernancePersistenceModel
    Repository->>Database: verify governed record exists
    Repository->>Database: INSERT record
    Application->>Domain: derive outcome-neutral attestation
    Application-->>Caller: GovernanceEvaluationResponse
```

## Class model

```mermaid
classDiagram
    GovernanceApplicationService --> GovernanceEvaluationService
    GovernanceApplicationService --> GovernanceEvaluationRepository
    GovernanceApplicationService --> ExceptionAuthorizationValidationService
    GovernanceEvaluationService --> GovernanceEvaluationRecord
    GovernanceEvaluationRecord *-- GovernanceExplanation
    GovernanceEvaluationRecord *-- GovernanceConfidence
    GovernanceConfidence *-- GovernanceConfidenceLevel
    GovernanceAttestationService --> GovernanceEvaluationRecord
    GovernanceEvaluationRepository <|.. GovernanceEvaluationRepositoryImpl
    GovernanceEvaluationRepositoryImpl --> GovernanceEvaluationORM
```

## Persistence

```mermaid
erDiagram
    IMMUTABLE_COGNITIVE_RECORD ||--o{ GOVERNANCE_EVALUATION_RECORDS : "governed record reference"
    GOVERNANCE_EVALUATION_RECORDS {
        uuid record_identifier PK
        uuid governed_record_reference
        string governed_record_type
        string governance_outcome
        string governance_confidence
        jsonb structured_reasons
        string narrative_explanation
        string governing_policy_reference
        string policy_version
        uuid exception_authorization_reference
        timestamptz effective_from
        timestamptz produced_timestamp
    }
```

The repository validates the governed record reference against exactly one authorized cognitive-record table selected by Governed Record Type. The type is not a new canonical entity or enum; it is the GRM-defined business attribute constrained to the five authorized cognitive record types.

Governance identity is Governed Record Reference plus Governing Policy Reference. Policy Version participates in history, not identity. RFC-011 currentness orders matching records by Effective From, Produced Timestamp, and Record Identifier, descending, and excludes future-effective records.

For Exception Granted, the application validates the supplied GEM-001 authorization authority, policy and version, effective period, and expiration. The authorization is consumed without modification and only its authorized reference is recorded. PostgreSQL rejects UPDATE and DELETE operations through a dedicated trigger. Human override appends a replacement record.
