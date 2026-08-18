# Architecture Release v1.11

Gate F architecture release (RFC-017 / PAD-003 / CDD-015): publishes the
"Governed Supply Chain Impact & Mitigation Decision" capability
architecture. RFC-017 formally, prospectively authorizes — from this
release forward only, not retroactively claiming prior governance — the ten
existing supply-chain concepts and seven existing relationship types Gate F
depends on, plus three new relationship types (`assembledAt`, `coveredBy`,
`candidateFor`), all as taxonomy data within the existing
`institutional_relationships`/`relationship_types` mechanism RFC-015/RFC-016
already govern. PAD-003 freezes **two** scopes (corrected by Gate F F5.1
governance remediation prior to this baseline's first push/PR/merge — see
below): `supply-chain-impact:read` (retrieval of existing Gate F governed
output) and `supply-chain-impact:evaluate` (governed computation that
creates a new, persisted Decision Evaluation), distinct from
`supplier-risk:read`/`:submit` and explicitly separated from
`entity-resolution:decide`. CDD-015 (published as a governed implementation
work order under `docs/cdd/`, per the CDD-004 through CDD-014 convention —
not a release-directory artifact) defines the Gate F capability contract,
including a small noncanonical runtime persistence extension
(`decision_evaluations`) authorized directly by CDD-015 rather than by RFC,
following the same precedent
`decision_evaluation_records`/`governance_evaluation_records`/`runtime_executions`
were themselves governed by, and now includes CDD Template v2.2's mandatory
exhaustive per-artifact authorization records (§31-35). No canonical entity,
attribute, relationship schema, or Protocol Version change; the ECOM
Physical Data Model remains v1.7, unchanged from baseline v1.10. Unchanged
authorities are inherited from v1.10. This release authorizes architecture
only — no Gate F implementation is authorized by this baseline. The Release
Manifest is the integrity register for this directory.

**F5.1 governance remediation (pre-publication correction)**: Gate F F5
(Implementation Planning) identified two governance gaps in this baseline
before it was ever pushed, reviewed, or merged: CDD-015 lacked CDD Template
v2.2's mandatory artifact-authorization records, and PAD-003's original
single-scope model conflated read and evaluate operations. Both are
corrected directly within this same v1.11 baseline (RFC-017, dependency
matrix, and this baseline's version number are unaffected — the correction
is scoped exactly to PAD-003 and CDD-015) rather than by advancing to a new
baseline version, because this baseline had not yet reached any
shared/authoritative state outside this local repository at the time of
correction.
