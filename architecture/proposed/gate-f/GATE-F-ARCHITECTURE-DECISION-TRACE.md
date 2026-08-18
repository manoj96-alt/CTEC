# Gate F — Architecture Decision Trace

Status: PROPOSED / NON-AUTHORITATIVE. Maps each Product Owner Gate F F1
decision to where it lands in the proposed package
(`RFC-017`, `PAD-003`, `CDD-015`), the implementation implication, and the
future-gate implication.

| # | Product Owner F1 Decision | RFC-017 | PAD-003 | CDD-015 | Implementation implication | Future-gate implication |
|---|---|---|---|---|---|---|
| 1 | Impact analysis placement: Option-C-refined — no seventh cognitive engine | — | — | §6-13, §26 | New logic lives in Ask CTEC (unmodified) + new adapters into the existing six ports. `runtime/orchestration.py` and `runtime/recovery.py` are not touched. | Keeps the six-stage contract free for any future capability to reuse the same adapter pattern, instead of being permanently reshaped around supplier risk. |
| 2 | RFC required for new canonical semantics; CDD-only authority rejected | Whole document | — | §31 (cites, does not self-authorize) | Three new relationship types (§3a-3c) plus retroactive ratification of the pre-existing 7 types/10 concepts (§6) — all under RFC authority, none under CDD-only authority. | Closes the SUPPLIER-RISK-ONTOLOGY-V1 governance gap for good, so later gates don't inherit it or repeat the pattern. |
| 3 | One new read scope | — | Whole document | §18, §21, §25 (cites, does not self-authorize) | `supply-chain-impact:read` (recommended name, PAD-003 §2) gates every new Gate F endpoint. No scope proliferation — one scope for the entire read surface. | Establishes the "one scope per bounded capability" pattern for whatever vertical slice comes after Gate F. |
| 4 | Human-authority-required belongs to GRM | — | §3, §7 | §12, §14, §28.4 | GRM (not DRM's `HumanOverrideService`) produces `HUMAN_APPROVAL_REQUIRED` as a `governance_evaluation_records` outcome. | Establishes GRM, not DRM, as the architectural home for any future "does this decision need a human" question — relevant to future Decision Readiness. |
| 5 | Hybrid persistence | §5 (no schema change) | — | §16-17, §20 | Dependency path stays derived-on-read (no new table); the decision snapshot reuses `decision_evaluation_records` + `governance_evaluation_records` unmodified. | No new canonical entity for Gate F means no migration debt for a future gate to work around. |
| 6 | No generalized revenue aggregation | §1 (reuses `generatesRevenue` as-is) | — | §17, §27 | Revenue exposure is a single-hop read off the existing Product→Revenue-Exposure edge; no rollup engine. | Leaves room for a future, genuinely general revenue-aggregation capability to be designed properly later, rather than inheriting a supplier-risk-shaped one. |
| 7 | Reuse Contract if semantically valid | §2, §3b | — | §5, §9 | `Contract` concept reused unchanged; only the missing `Material→Contract` edge (`coveredBy`) is added. No "Supply Agreement" concept created. | Avoids a duplicate-concept problem a future gate would otherwise have to reconcile. |

## Protected future capabilities — explicit mapping

| Future capability | Status in Gate F | Seam it would use later |
|---|---|---|
| Supply Chain Blueprint | DEFERRED / NOT GATE F | The same `EntityType`/`RelationshipType`/`InstitutionalConcept` taxonomy RFC-017 extends |
| Source-to-Blueprint Semantic Mapping | DEFERRED / NOT GATE F | `institutional_relationships`/`assertions` instance data, populated the same way Gate F populates its own |
| Profiling + Gap Engine | DEFERRED / NOT GATE F | `assertions`' existing `effective_from`/`effective_to`/`governance_status` columns, unmodified by Gate F |
| Gap Impact + Remediation Engine | DEFERRED / NOT GATE F | Same seam as Profiling/Gap; note "remediation" is a reused word in this codebase for governance-process contract fixes (CDD-012/013/014 remediation reports) — unrelated concept, flagged to avoid future confusion |
| Decision Requirements | DEFERRED / NOT GATE F | Not implemented; Gate F's own bounded readiness check (§12) is explicitly flagged as provisional, not this capability |
| Decision Readiness | DEFERRED / NOT GATE F | Same as above — CDD-015 §26 states this explicitly |

## Open items this package does not resolve

- Whether revenue exposure ever needs cross-product rollup beyond the
  single-hop `generatesRevenue` read (F1 §34.3) — deferred to real business
  requirements, not decided by this package.
- The RFC-010 primary-text evidentiary caveat (RFC-017 §5) — RFC-010 is a
  `.docx` file not read directly; the taxonomy-mechanism authorization
  argument rests on RFC-016's quotation of it.
