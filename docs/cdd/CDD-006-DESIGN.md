# CDD-006 Assertion Engine — Design

ASM-001 v2.0 is the sole authority for Assertion business semantics. Every creation path requires governed Enterprise Entity Resolution and Semantic Resolution evidence for the same Subject.

```mermaid
flowchart LR
  EER[Enterprise Entity Resolution Record] --> AE[Assertion Evaluation]
  SR[Semantic Resolution Record] --> AE
  SPO[Subject + Relationship Type + Institutional Concept + Context] --> AE
  AE --> AR[Immutable Assertion Record]
  AR --> DB[(Append-only records and evidence links)]
  AR --> HP[(External current-belief history)]
```

```mermaid
sequenceDiagram
  participant Caller
  participant Engine
  participant Store
  Caller->>Engine: SPO proposition + governed evidence
  Engine-->>Caller: immutable Assertion Record
  Caller->>Store: append(record)
  Store->>Store: verify both evidence types reference Subject
  Store->>Store: insert record and advance external history
```

```mermaid
classDiagram
  AssertionEngine --> AssertionPolicy
  AssertionEngine --> GovernedEvidence
  AssertionEngine --> AssertionRecord
  AssertionRecordStore --> AssertionRecord
```

Persistence adds one immutable record table, two evidence junction tables with foreign keys to CDD-004/005 records, and one external history projection keyed by Subject, Predicate, Object, and Context. The existing CEO and canonical physical tables are unchanged.
