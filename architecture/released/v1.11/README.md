# Architecture Release v1.11

Gate F architecture release (RFC-017 / PAD-003 / CDD-015): publishes the
"Governed Supply Chain Impact & Mitigation Decision" capability
architecture. RFC-017 formally, prospectively authorizes — from this
release forward only, not retroactively claiming prior governance — the ten
existing supply-chain concepts and seven existing relationship types Gate F
depends on, plus three new relationship types (`assembledAt`, `coveredBy`,
`candidateFor`), all as taxonomy data within the existing
`institutional_relationships`/`relationship_types` mechanism RFC-015/RFC-016
already govern. PAD-003 freezes the new `supply-chain-impact:read` read
scope and its access boundary, distinct from `supplier-risk:read` and
explicitly separated from `entity-resolution:decide`. CDD-015 (published as
a governed implementation work order under `docs/cdd/`, per the CDD-004
through CDD-014 convention — not a release-directory artifact) defines the
Gate F capability contract, including a small noncanonical runtime
persistence extension (`decision_evaluations`) authorized directly by
CDD-015 rather than by RFC, following the same precedent
`decision_evaluation_records`/`governance_evaluation_records`/`runtime_executions`
were themselves governed by. No canonical entity, attribute, relationship
schema, or Protocol Version change; the ECOM Physical Data Model remains
v1.7, unchanged from baseline v1.10. Unchanged authorities are inherited
from v1.10. This release authorizes architecture only — no Gate F
implementation is authorized by this baseline. The Release Manifest is the
integrity register for this directory.
