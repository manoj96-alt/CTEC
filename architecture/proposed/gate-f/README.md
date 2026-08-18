# Gate F — Proposed Architecture Package

Status: **PROPOSED / NON-AUTHORITATIVE / NOT RELEASED / NOT IMPLEMENTATION
AUTHORITY.** Nothing in this directory is registered in
`architecture/INDEX.md` and nothing here may be cited as architecture
authority. It exists for Product Owner review only, produced by Gate F F2
(Proposed Architecture Package Drafting) following Gate F F0 (Discovery) and
F1 (Decision Analysis), and verified/corrected by Gate F F2.1 (Architecture
Evidence & Persistence Verification).

## Contents

- `RFC-017-Gate-F-Supply-Chain-Semantic-Vocabulary-Authorization_PROPOSED.md`
  — the minimum new canonical relationship-type vocabulary Gate F requires
  (three new relationship types; zero new concepts), plus retroactive
  ratification of the pre-existing, previously-ungoverned
  `SUPPLIER-RISK-ONTOLOGY-V1` vocabulary Gate F depends on.
- `PAD-003-Gate-F-Impact-Mitigation-Access-Boundary_PROPOSED.md` — the one
  new read scope (`supply-chain-impact:read`, recommended name) Gate F
  requires, and its boundary against `supplier-risk:read`,
  `entity-resolution:read`/`:decide`, and `ontology-copilot:ask`.
- `CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision_PROPOSED.md`
  — the Gate F vertical capability contract: business journey, architecture
  reuse, engine responsibilities, persistence, security, and acceptance
  criteria.
- `GATE-F-ARCHITECTURE-DECISION-TRACE.md` — maps each Product Owner Gate F
  F1 decision to where it lands in this package.

## What this package does NOT do

It does not modify `architecture/released/*` or `architecture/INDEX.md`. It
does not implement any backend, frontend, migration, test, or scope. It does
not modify or retire `/demo/supplier-risk`. It does not implement human
approval, execution, or any of the six protected future platform
capabilities (Supply Chain Blueprint, Source-to-Blueprint Semantic Mapping,
Profiling + Gap Engine, Gap Impact + Remediation Engine, Decision
Requirements, Decision Readiness).

## Review sequence

1. `GATE-F-ARCHITECTURE-DECISION-TRACE.md` — orientation.
2. `RFC-017-...` — semantic authorization.
3. `PAD-003-...` — access boundary.
4. `CDD-015-...` — capability contract, cites both above.

## Status of open questions

F2.1 closed the two evidence questions the Product Owner required before
architecture finalization: RFC-010's primary text was read directly and
confirms (does not merely support by inference) RFC-017's approach, and the
Gate F decision-time persistence contract was proven against a realistic
multi-material/multi-candidate case — CDD-015's persistence sections were
corrected to specify the exact mechanism required (see
`GATE-F-ARCHITECTURE-DECISION-TRACE.md`'s "F2.1 verification outcomes").
Remaining open items are listed in that document's final section; none are
blocking for Product Owner review.
