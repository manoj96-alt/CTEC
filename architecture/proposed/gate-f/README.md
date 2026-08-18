# Gate F — Architecture Release Candidate Package (HISTORICAL REVIEW TRAIL)

**PUBLISHED.** Gate F architecture was published by F4 as part of baseline
**v1.11** on 2026-08-18. The authoritative documents are now:

- `architecture/released/v1.11/RFC-017-Gate-F-Supply-Chain-Semantic-Vocabulary-Authorization_v1.0_FROZEN.md`
- `architecture/released/v1.11/PAD-003-Gate-F-Impact-Mitigation-Access-Boundary_v1.0_FROZEN.md`
- `docs/cdd/CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision.md`
  (CDD Gate: FROZEN, Implementation State: NOT STARTED)

**Everything in this `architecture/proposed/gate-f/` directory is now
NON-AUTHORITATIVE HISTORICAL REVIEW-TRAIL MATERIAL**, preserved for audit
traceability of the F0-F3 process only. Do not cite it as architecture
authority — cite the `architecture/released/v1.11/` and `docs/cdd/`
documents above instead.

---

Status (as of F3, prior to publication — retained below for historical
context): **RELEASE CANDIDATE / NON-AUTHORITATIVE / NOT RELEASED / NOT
IMPLEMENTATION AUTHORITY.** Nothing in this directory is registered in
`architecture/INDEX.md` and nothing here may be cited as architecture
authority until separately published. It exists for Product Owner
release-candidate review, produced by Gate F F2 (Proposed Architecture
Package Drafting) following Gate F F0 (Discovery) and F1 (Decision
Analysis); verified/corrected by Gate F F2.1 (Architecture Evidence &
Persistence Verification) and F2.2 (Persistence Correlation and RFC-010
Compliance Design); and promoted to release-candidate status by Gate F F3
(Architecture Finalization & Release-Candidate Preparation) after full
package consistency and dependency verification.

## Contents

- `RFC-017-Gate-F-Supply-Chain-Semantic-Vocabulary-Authorization_RELEASE_CANDIDATE.md`
  — the minimum new canonical relationship-type vocabulary Gate F requires
  (three new relationship types; zero new concepts), plus narrow, prospective
  ratification of the pre-existing, previously-ungoverned
  `SUPPLIER-RISK-ONTOLOGY-V1` vocabulary Gate F depends on.
- `PAD-003-Gate-F-Impact-Mitigation-Access-Boundary_RELEASE_CANDIDATE.md` —
  the one new read scope (`supply-chain-impact:read`) Gate F requires, and
  its boundary against `supplier-risk:read`, `entity-resolution:read`/`:decide`,
  and `ontology-copilot:ask`.
- `CDD-015-Governed-Supply-Chain-Impact-and-Mitigation-Decision_RELEASE_CANDIDATE.md`
  — the Gate F vertical capability contract: business journey, architecture
  reuse, engine responsibilities, persistence (including the noncanonical
  `decision_evaluations` extension), security, and acceptance criteria.
- `GATE-F-ARCHITECTURE-DECISION-TRACE.md` — maps each Product Owner Gate F
  F1 decision to where it lands in this package.
- `GATE-F-ARCHITECTURE-CONSISTENCY-REPORT_RELEASE_CANDIDATE.md` — Gate F F3's
  verification that the package introduces none of the 18 forbidden
  architecture patterns, and that the package is internally consistent.
- `DEPENDENCY-MATRIX-v1.11.csv` — proposed dependency-matrix rows for the
  next architecture baseline, if Gate F is authorized and published.
- `GATE-F-RELEASE-MANIFEST-PLAN_RELEASE_CANDIDATE.md` — planning artifact for
  the eventual `RELEASE-MANIFEST-v1.11.xlsx`, produced only at publication.
- `GATE-F-IMPLEMENTATION-READINESS_RELEASE_CANDIDATE.md` — likely
  implementation workstreams implied by the candidate architecture, planning
  only.
- `GATE-F-ACCEPTANCE-TRACEABILITY_RELEASE_CANDIDATE.md` — maps every major
  Gate F business claim to its architecture authority and future test
  obligation.

## What this package does NOT do

It does not modify `architecture/released/*` or `architecture/INDEX.md`. It
does not implement any backend, frontend, migration, test, or scope. It does
not modify or retire `/demo/supplier-risk`. It does not implement human
approval, execution, or any of the six protected future platform
capabilities (Supply Chain Blueprint, Source-to-Blueprint Semantic Mapping,
Profiling + Gap Engine, Gap Impact + Remediation Engine, Decision
Requirements, Decision Readiness). It is not yet published — release-candidate
naming is not authorization; publication is a separate, later Product Owner
decision.

## Review sequence

1. `GATE-F-ARCHITECTURE-DECISION-TRACE.md` — orientation.
2. `GATE-F-ARCHITECTURE-CONSISTENCY-REPORT_RELEASE_CANDIDATE.md` — verification results.
3. `RFC-017-..._RELEASE_CANDIDATE.md` — semantic authorization.
4. `PAD-003-..._RELEASE_CANDIDATE.md` — access boundary.
5. `CDD-015-..._RELEASE_CANDIDATE.md` — capability contract, cites both above.
6. `DEPENDENCY-MATRIX-v1.11.csv`, `GATE-F-RELEASE-MANIFEST-PLAN_RELEASE_CANDIDATE.md` — release-shape planning.
7. `GATE-F-IMPLEMENTATION-READINESS_RELEASE_CANDIDATE.md`, `GATE-F-ACCEPTANCE-TRACEABILITY_RELEASE_CANDIDATE.md` — forward planning, informational only.

## Status of open questions

F2.1/F2.2 closed the evidence questions the Product Owner required before
architecture finalization: RFC-010's primary text was read directly, the
Gate F decision-time persistence contract was proven against a realistic
multi-material/multi-candidate case, F2.1's rejected convention-based
correlation approach was replaced with the explicit `decision_evaluations`
extension (persistence classification **P3**), and the Logical/Physical
Model/EAD-001 compliance question was resolved definitively — see
`GATE-F-ARCHITECTURE-DECISION-TRACE.md`'s "F2.2 outcomes." F3 found and
corrected two internal cross-reference errors in `CDD-015` (see
`GATE-F-ARCHITECTURE-CONSISTENCY-REPORT_RELEASE_CANDIDATE.md`) and confirmed
no other contradiction exists in the package. Remaining open items are
listed in the decision trace's final section; none are blocking for Product
Owner release-candidate review.
