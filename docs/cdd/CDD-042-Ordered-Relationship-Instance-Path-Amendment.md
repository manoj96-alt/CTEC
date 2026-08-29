# CDD-042 Ordered Relationship-Instance Path Amendment

**Status:** APPROVED GOVERNANCE CLARIFICATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-042 §9 ("Multiple paths") — narrowly, a wording clarification of path *identity*, without reopening any other part of §9 or any other section of CDD-042
**Precedent:** same class of narrow companion clarification as every prior CDD-039/040/041 amendment in this governance lineage — a new document, never an in-place edit of frozen text

## 1. Discovered ambiguity

CDD-042 §9 froze: "Path *evidence* is deduplicated by **node-set** and capped at the shortest 3 distinct paths per element per evaluation."

OQI4-I's implementation (`_deduplicate_and_cap_paths` in `oqi_ontology_impact_evaluation_service.py`) deduplicates by the traversed relationship-instance identities, not by the set of intermediate ontology entities visited. Independent adversarial review during OQI4-I-R1 found the implementation's own dedup key was, in fact, an **unordered** `frozenset` of relationship-instance IDs — matching neither a literal node-set reading nor the ordered-sequence semantics the architecture actually requires for correct explainability (CDD-042 §16's path-provenance contract: "which relationship IDs, which path" must be reconstructable exactly as traversed).

## 2. Why "node-set" was never the correct reading

A path proof exists to answer, deterministically, *why* a given ontology element is impacted (CDD-042 §16). That answer is the exact relationship-instance chain traversed — its membership **and** its order. Two observations proved a literal node-set (or an unordered edge-set) reading insufficient:

1. **Parallel edges collapse incorrectly under a naive set reading of anything coarser than the edge sequence itself.** Three distinct relationship instances `R1`, `R2`, `R3`, each independently connecting `A` to the same target `D`, must remain three distinct path proofs (CDD-042 §9's own path cap exists precisely to bound cases like this) — not one, which a shared-intermediate-node reading could wrongly suggest since all three share the identical (empty) intermediate node-set.
2. **Order is semantically load-bearing.** The same relationship instances traversed in a different order (where the graph's own topology permits more than one valid traversal order) are answering a different "why" than the original order — collapsing them to one proof would silently discard provenance CDD-042 §16 requires to be reconstructable.

## 3. Frozen clarification (binding)

> **Path identity is the ordered sequence of relationship instances traversed** from a directly-impacted anchor to the propagated target. Two path proofs are the same proof if, and only if, their ordered relationship-instance sequences are identical — in both membership and order.

Consequences, all already true of the recursive CTE's own `rel_path` array construction (CDD-042 §9's SQL, unchanged) and now explicitly frozen at the *identity* layer:

- **Parallel edges are distinct.** `A─R1→D`, `A─R2→D`, `A─R3→D` yield one `CurrentOntologyImpact` row on `D` (§11's identity already excludes path — unchanged) with **three** distinct path proofs, subject to the unchanged 3-path cap.
- **Exact duplicates collapse.** The same ordered relationship-instance sequence discovered more than once by query mechanics (e.g., a policy matching a relationship type via more than one active-policy row, or incidental row-order effects) deduplicates to **one** path proof.
- **Order distinguishes.** Two candidate paths sharing the same relationship-instance membership but traversed in a different order are distinct proofs, not the same proof — the general case this amendment exists to freeze, whether or not this repository's current fixture graphs happen to construct one today.

## 4. Scope of this amendment (binding boundary)

This amendment changes **only** the identity definition of "path evidence" deduplication in CDD-042 §9. It explicitly does **not** reopen, and no other part of CDD-042 is affected by it:

- Direct Impact or its definition (§4-§7) — unchanged.
- `IMPACT_UNKNOWN`/`NO_IMPACT`/`IMPACTED` epistemic semantics (§5) — unchanged.
- The governed `ImpactPropagationPolicy` model, deny-by-default rule, direction, or versioning (§8) — unchanged.
- The single recursive-CTE snapshot invariant, the policy-in-same-statement requirement, tenant filtering, or cycle safety (§9's other paragraphs) — unchanged.
- The **path cap** ("shortest 3 distinct paths per element") — unchanged, still exactly 3.
- The **depth ceiling** (10) — unchanged.
- `CurrentOntologyImpact`/`OntologyImpactEvaluation` identity formulas (§11) — unchanged; §11 already excludes path from current-impact identity, and this amendment does not add path back into it.
- Finding-family integration (§10) — unchanged.
- The Artifact Authorization's exact file-level authorization (CREATE=12/MODIFY=9/DELETE=0/TOTAL=21) — unchanged; this amendment authorizes no new path and requires none, since the affected file (`oqi_ontology_impact_evaluation_service.py`) was already MODIFY-authorized.

## 5. Implementation conformance

OQI4-I-R1 corrected `_deduplicate_and_cap_paths`'s dedup key from an unordered `frozenset[UUID]` over relationship-instance IDs to the ordered `tuple[UUID, ...]` already carried on `PropagatedPathCandidate.relationship_ids` (itself already order-preserving, built directly from the recursive CTE's `rel_path` array) — a narrow, one-function correction within the already-authorized file, requiring no schema change, no new table, no migration change, and no change to the path cap or depth ceiling. Regression coverage was added proving: parallel edges remain distinct (pre-existing test, unaffected), an exact-duplicate ordered sequence deduplicates to one proof (new), and two candidates sharing relationship-instance membership in different order are retained as distinct proofs (new).

## 6. Authorization

CDD-042 §9's path-evidence deduplication is corrected to read "ordered relationship-instance sequence" in place of "node-set," with the exact semantics frozen in §3 above, effective immediately. No other governance, schema, authorization, or architecture decision in CDD-042 is affected.
