# Gate F — Proposed Architecture Package

Status: **PROPOSED / NON-AUTHORITATIVE / NOT RELEASED / NOT IMPLEMENTATION
AUTHORITY.** Nothing in this directory is registered in
`architecture/INDEX.md` and nothing here may be cited as architecture
authority. It exists for Product Owner review only, produced by Gate F F2
(Proposed Architecture Package Drafting) following Gate F F0 (Discovery) and
F1 (Decision Analysis), and verified/corrected by Gate F F2.1 (Architecture
Evidence & Persistence Verification), with its persistence-correlation
design and RFC-010 compliance finalized by Gate F F2.2 (Persistence
Correlation and RFC-010 Compliance Design).

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
architecture finalization: RFC-010's primary text was read directly, and the
Gate F decision-time persistence contract was proven against a realistic
multi-material/multi-candidate case. F2.2 then replaced F2.1's
convention-based correlation approach (rejected by the Product Owner) with a
small, explicit, noncanonical `decision_evaluations` persistence extension
(CDD-015 §16-17, persistence classification **P3**), and resolved the
Logical Model/Physical Model/EAD-001 compliance question definitively rather
than leaving it as a residual item — see
`GATE-F-ARCHITECTURE-DECISION-TRACE.md`'s "F2.2 outcomes." Remaining open
items are listed in that document's final section; none are blocking for
Product Owner review.
