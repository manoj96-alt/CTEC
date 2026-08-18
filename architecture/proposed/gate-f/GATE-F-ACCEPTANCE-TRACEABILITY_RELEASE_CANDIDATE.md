# Gate F — Acceptance Traceability (Release Candidate)

Status: RELEASE CANDIDATE PLANNING ARTIFACT — NON-AUTHORITATIVE — NOT
IMPLEMENTATION AUTHORITY. Maps every major Gate F business claim to its
architecture authority and future test obligation.

| Business claim | Architecture authority | Future test obligation |
|---|---|---|
| Supplier risk → evidence | Existing `locatedIn`/`exposedTo` chain + `assertions`/`assertion_evidence` (CDD-015 §5, §15) | Evidence-linkage test (existing pattern, `assertion_evidence` composite PK) |
| Supplier → material | Existing `supplies` relationship type (RFC-017 §1) | Existing ontology/traversal tests |
| Material → product/BOM | Existing `usedIn`/`defines` relationship types (RFC-017 §1) | Existing ontology/traversal tests |
| Product → facility | New `assembledAt` relationship type (RFC-017 §3a) | New ontology seed test + traversal test |
| Revenue exposure | Existing `generatesRevenue` relationship type (RFC-017 §1); no aggregation engine (CDD-015 §27) | Existing traversal test; explicit negative test that no rollup logic exists |
| Candidate supplier | New `candidateFor` relationship type (RFC-017 §3c), instantiated per (Alternate Supplier, Material) pair (CDD-015 §9) | Cardinality test (CDD-015 §29) |
| Qualification | `assertions` attached via `institutional_relationship_assertions` (CDD-015 §9) | Domain unit test + cardinality test |
| Capacity | Same mechanism | Domain unit test + cardinality test |
| Lead time | Same mechanism | Domain unit test + cardinality test |
| Cost | Same mechanism | Domain unit test + cardinality test |
| Mitigation recommendation | DRM, `decision_evaluation_records` (CDD-015 §11, §13, §16 item 4) | DRM adapter test |
| Decision Evaluation (correlation) | New `decision_evaluations` table (CDD-015 §16) | Migration test, cardinality test |
| GRM `HUMAN_APPROVAL_REQUIRED` | `governance_evaluation_records`, one per group (CDD-015 §12, §16 item 5) | GRM adapter test, negative test (no approval action producible) |
| Tenant isolation | `decision_evaluations.tenant_id` (direct) + application-layer invariant for children (CDD-015 §16 item 7, §19) | Tenant-isolation test asserting rejection on violation |
| Authorization | `supply-chain-impact:read` (PAD-003), no `entity-resolution:decide` crossing (PAD-003 §7) | Scope-enforcement test, negative test |
| Replay/recovery | Existing six-stage checkpoint model unmodified; `decision_evaluation_id` lifecycle (CDD-015 §20) | Replay/recovery test with simulated retry |
| Historical reproducibility | `decision_evaluation_records`/`governance_evaluation_records` append-only, policy-versioned, referencing frozen decision-time facts (CDD-015 §16, §24) | Point-in-time reproduction test |
| No approval | No approve/reject/conditional-approve code path (CDD-015 §12, §14; PAD-003 §10) | Negative test: endpoint inventory contains no mutating action |
| No execution | No ERP/PO/contract/supplier-activation action (CDD-015 §6, §27) | Negative test: no execution-capable code path exists |

## Coverage note

Every row above traces to a specific, already-written CDD-015/RFC-017/PAD-003
section — none of these obligations are newly invented by this document. This
table exists to make the trace explicit and reviewable in one place, not to
create new architecture authority.
