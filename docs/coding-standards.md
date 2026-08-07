# Coding Standards

Follow CDS-001: SOLID, Clean Architecture, DDD, and repository boundaries. Business logic belongs only in future domain services. API and UI code may not access persistence. Use explicit typing, structured logs without secrets, tests for behavior, and the configured formatters, linters, and type checkers. Do not create domain entities outside an approved layer specification.

Every CDD must also satisfy the frozen CDS-001 Authorized Artifacts Amendment. The CDD must exhaustively name permitted Entities, Services, Value Objects, and Enums; an omitted category must explicitly state `None`. Everything else is prohibited.
