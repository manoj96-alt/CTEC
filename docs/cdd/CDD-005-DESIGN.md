# CDD-005 Semantic Resolution — Design

SRM-001 v2.1 is the sole authority for business semantics. The implementation consumes existing CEO artifacts unchanged.

```mermaid
flowchart LR
  EER[Enterprise Entity Resolution Record] --> CD[Semantic Candidate Discovery]
  SO[Source Object] --> CD
  IC[Institutional Concepts] --> CD
  CTX[Governed Context] --> SR[Semantic Resolution]
  CD --> SR --> RR[Immutable Semantic Resolution Record]
  RR --> DB[(Append-only records)]
  RR --> HP[(Current-understanding projection)]
```

```mermaid
sequenceDiagram
  participant Caller
  participant Engine
  participant Store
  Caller->>Engine: evidence, context, governed concepts
  Engine-->>Caller: immutable semantic resolution record
  Caller->>Store: append(record)
  Store->>Store: insert record and advance external history
```

```mermaid
classDiagram
  SemanticResolutionEngine --> SemanticResolutionPolicy
  SemanticResolutionEngine --> CandidateSemanticInterpretation
  SemanticResolutionEngine --> SemanticResolutionRecord
  SemanticResolutionStore --> SemanticResolutionRecord
```

The physical implementation adds append-only `semantic_resolution_records` and an externally maintained `semantic_resolution_history` projection. No canonical physical table is modified. In accordance with RFC-011, current understanding is determined from ordered immutable record history keyed by Enterprise Entity plus Context. No Semantic Resolution Record changes state from active to archived. Legacy projection column names remain physical compatibility details only.
