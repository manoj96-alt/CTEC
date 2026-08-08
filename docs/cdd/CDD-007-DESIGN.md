# CDD-007 Knowledge Engine — Design

KRM-001 v1.3 is the authority for Knowledge semantics, AEM-001 v1.1 defines Acceptance Evidence under RFC-013 Governance Authority, and RFC-011 v1.0 defines immutable-record currentness.

```mermaid
flowchart LR
  AR[Assertion Record] --> KE[Knowledge Evaluation]
  AE[Acceptance Evidence] --> EV[Evidence Validation]
  EV --> KE
  KP[External Knowledge Policy] --> KE
  KE --> KR[Immutable Knowledge Evaluation Record]
  KR --> IH[Institutional Knowledge when Institutionalized]
  KR --> DB[(Append-only persistence)]
  DB --> CP[Currentness projection using RFC-011]
```

```mermaid
sequenceDiagram
  participant Caller
  participant Engine
  participant EvidenceValidator
  participant Store
  Caller->>Engine: Assertion + outcome + evidence + explanation
  Engine->>EvidenceValidator: validate AEM-001 evidence
  EvidenceValidator-->>Engine: valid
  Engine-->>Caller: immutable Knowledge Evaluation Record
  Caller->>Store: append(record)
  Store->>Store: verify Assertion exists
  Store->>Store: insert only
  Caller->>Store: current(assertion, as_of)
  Store-->>Caller: RFC-011 ordered current record
```

```mermaid
classDiagram
  KnowledgeEngine --> KnowledgePolicy
  KnowledgeEngine --> AcceptanceEvidenceValidator
  KnowledgeEngine --> AcceptanceEvidence
  KnowledgeEngine --> KnowledgeEvaluationRecord
  KnowledgeEvaluationStore --> KnowledgeEvaluationRecord
```

```mermaid
erDiagram
  ASSERTION_RECORDS ||--o{ KNOWLEDGE_EVALUATION_RECORDS : evaluated_by
  KNOWLEDGE_EVALUATION_RECORDS {
    uuid record_id PK
    uuid assertion_record_id FK
    string outcome
    uuid acceptance_evidence_id
    datetime effective_from
    datetime produced_at
  }
```

Acceptance Evidence remains Governance-owned and is referenced, not created or duplicated. Currentness is computed from `Effective From`, `Produced Timestamp`, and `Record Identifier`; no lifecycle state is stored in the immutable record.
