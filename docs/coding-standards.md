# Coding Standards

Follow CDS-001: SOLID, Clean Architecture, DDD, and repository boundaries. Business logic belongs only in future domain services. API and UI code may not access persistence. Use explicit typing, structured logs without secrets, tests for behavior, and the configured formatters, linters, and type checkers. Do not create domain entities outside an approved layer specification.

Every CDD must also satisfy the frozen CDS-001 Authorized Artifacts Amendment. The CDD must exhaustively name its permitted business Entities, Services, Value Objects, and Enums, or explicitly incorporate the authoritative business artifacts of an approved Business Capability Model. Private implementation artifacts remain an engineering responsibility unless they become externally visible, modify canonical business semantics, or cross an architecture boundary.
