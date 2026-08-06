# CDD-003 — Foundation Reference Model

Version: 2.1  
Status: Development

## Objective

Implement only the immutable reference entities that describe the enterprise foundation. This layer defines canonical structure and language. It contains no workflows, cognition, governance decisions, persistence, APIs, or business processes.

## Authorized artifacts

### Entities

- Enterprise
- Enterprise Type
- Business Domain
- Country
- Institutional Concept
- Entity Type
- Relationship Type

### Services

None.

### Value objects

- Identifier
- Canonical Name
- Business Name
- Description
- Reference Code

### Enums

- Lifecycle State
- Governance Status

Everything else is prohibited.

## Authorized exceptions

- Domain Exception
- Validation Exception

## Validation boundary

Only structural validation is authorized: required values, declared types, EAD lengths, UUID validity, required references, and timezone-aware timestamps. Business rules, workflows, lifecycle transitions, governance decisions, inference, identity matching, and semantic interpretation are prohibited.

## Stop boundary

CDD-004 and every non-foundation entity or service are out of scope.
