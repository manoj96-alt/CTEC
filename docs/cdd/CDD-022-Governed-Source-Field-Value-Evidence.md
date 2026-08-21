# CDD-022 — Governed Source Field-Value Evidence

Version: 1.0 FROZEN
Status: FROZEN
Implementation state: NOT STARTED
Governing authorities: CDD-017 (FROZEN, Canonical Supply Chain Blueprint Requirement Contract, unchanged
— cited for disambiguation, not consumed), CDD-017 G3.5 Canonical Blueprint Seed Artifact Authorization
(FROZEN, unchanged — the direct precedent this CDD's deterministic identity derivation reuses, §6), CDD-018
(FROZEN, Blueprint Conformance Evaluation, unchanged — cited only for disambiguation), CDD-019
(FROZEN, Source-to-Blueprint Semantic Mapping H1-H3, unchanged — the sole authority for
`SourceField`/`SourceObject`/`SourceSystem` identity this CDD extends by one governed hop), CDD-019
H1/H2/H3 artifact-authorization companions (FROZEN, unchanged — H3's own deterministic-seed and
idempotency-test precedent is likewise reused, §6, §21), CDD-020
(FROZEN, Blueprint Information-Element Semantic Coverage Evaluation, unchanged — cited only for
disambiguation), CDD-021 (FROZEN, Blueprint Semantic Gap Impact Context and Remediation Recommendation,
unchanged — cited only for disambiguation), CDD-010 (FROZEN, Cognitive Engine Runtime, unchanged — the
trusted-admission/idempotency authority this CDD's `received_at` contract reuses), CDD-010/CDD-013
Trusted Admission Timestamp and Idempotency Contract Remediation Report (FROZEN, unchanged — the direct
precedent this CDD's replay contract restates)
Mandatory template: CDD Template v2.2

**Publication note**: this Work Order is an architecture authority (CDD Gate: FROZEN), to be published via
`architecture/INDEX.md`'s "Governed implementation work orders" table, following the identical
non-baseline-tracked mechanism already used for CDD-011 through CDD-021 (see §31 for the direct evidence
this CDD does not require a new numbered architecture baseline). No implementation exists yet — this
document does not itself authorize implementation; a separate, subsequent artifact-authorization companion
(mirroring CDD-021's own J1/J2 companion precedent) governs the exact implementation sandbox. Governance
publication (registration in `architecture/INDEX.md`) remains a separate, not-yet-authorized action.

## 1. Objective and business outcome

Establish, as its own governed architecture authority, **Governed Source Field-Value Evidence**: the
capability to persist and retrieve, for a given tenant and a specific already-governed `SourceField`
(CDD-019), authoritative physical evidence of an observed raw value — answering exactly one question:
*"what authoritative observed-value evidence exists for this SourceField?"* This is the prerequisite
capability the H4 Product Owner Architecture Decision identified as missing: no governed mechanism
anywhere in CTEC currently connects a `SourceField` to any observed value. This CDD closes exactly that
gap, and no more. It does **not** evaluate whether the evidence satisfies any Blueprint
`InformationElementRequirement` — that question is explicitly reserved for a future, separately-governed
capability ("H4 — Blueprint Information-Element Conformance Integration," CDD-019 §6, §20), which this
CDD is a strict, load-bearing prerequisite for but does not itself define, design around, or partially
implement.

## 2. Governing authorities

Current frozen: CDD-019 (Source-to-Blueprint Semantic Mapping H1-H3, cited as the **sole** authority for
`SourceField`/`SourceObject`/`SourceSystem` identity — this CDD does not amend, extend, or reinterpret
CDD-019; CDD-019 remains FROZEN and unchanged, and this CDD's own domain type is a new *sibling* to
`SourceField` within the same already-governed package, never a modification of it), CDD-010 and the
CDD-010/CDD-013 Trusted Admission Timestamp and Idempotency Contract Remediation Report (cited as the
authority for the discipline that `received_at` is trust-boundary-owned and never client-controlled, §11 —
not for the duplicate-detection mechanism itself, which §6 governs independently). CDD-017 G3.5 and CDD-019
H3 (both FROZEN, unchanged) are cited as the direct precedent for §6's deterministic-identity derivation
(`BlueprintSeeder`'s/`DemoSemanticMappingSeeder`'s own `uuid5`-under-a-governed-namespace,
existence-check-then-skip pattern) — reused, not amended or extended. CDD-017 (its own top-level Work
Order), CDD-018, CDD-020, and CDD-021 are cited unchanged, solely for the disambiguation in §17 below —
none of them is a governing authority this CDD's own architecture depends on, consumes, or extends.

**Explicit disambiguation from H4 (binding, restated throughout)**: this CDD is not H4. H4 — Blueprint
Information-Element Conformance Integration — remains entirely outside this CDD's authority, undesigned,
and un-numbered (CDD-019 §6, §20; H4 Product Owner Architecture Decision, this session). This CDD
establishes the physical FACT layer H4 would eventually consume; it performs no EVALUATION of any kind
and authorizes none.

**Explicit disambiguation from `SourceObservation` (binding, restated throughout)**: `backend/app/integration/contracts.py`'s
`SourceObservation` (RFC-014/CIM-001, CDD-011) is a categorically different, already-FROZEN capability —
an ephemeral, non-persisted integration DTO scoped exclusively to the Supplier-Risk pipeline, anchored on
`subject_id` (an enterprise-entity identity) with a mandatory `severity: RiskSeverity` field, carrying no
`source_field_id` and no `tenant_id`. CDD-019 §17 already established, independently, that `SourceObservation`
is unrelated to `SourceField`. This CDD does not extend, replace, wrap, persist, or depend on
`SourceObservation` in any way, and does not reinterpret `SourceObservation.value` or
`SourceObservation.severity` as evidence for any `SourceField`. No `SourceObservation` artifact is
authorized for modification by this CDD.

**Explicit disambiguation between the two "integration" packages (binding)**: `backend/app/domain/integration/`
(this CDD's own domain — `SourceSystem`/`SourceObject`/`SourceField`, Gate H's physical source-identity
model) and `backend/app/integration/` (a different, top-level package — RFC-014/CIM-001's Supplier-Risk
integration contracts, including `SourceObservation`) are two distinct, differently-governed packages that
happen to share a name segment. This CDD authorizes work only in the former. Neither package is
authorized for renaming by this CDD.

## 3. Why Governed Source Field-Value Evidence requires its own governance

A CDD-019 companion is only capable of authorizing implementation-level artifact detail for architecture
CDD-019 has *already* defined in its own body. CDD-019 does not define any field-value-evidence
architecture — it explicitly names the underlying question ("how does CTEC obtain authoritative live
source-field values/evidence for information-element conformance evaluation?") as unresolved and states
plainly that it "does not answer or design around that question" (CDD-019 §6). A new, standalone CDD is
therefore the only textually honest instrument — the identical reasoning CDD-018, CDD-019, CDD-020, and
CDD-021 each already used to justify their own standalone status.

## 4. In scope

- A new, persisted, immutable, append-only domain fact — `FieldValueEvidence` (§6) — recording that a raw
  observed representation was admitted for a specific, already-governed `SourceField`.
- Tenant-scoped, identity-based retrieval of the governed evidence set for a `SourceField` (§13).
- Preservation of the existing trusted-admission/idempotency discipline (CDD-010/CDD-013) for the one
  timestamp this CDD's own contract owns (`received_at`; §11).
- A narrowly-scoped, explicitly-labeled test/demo fixture sufficient to prove persistence and retrieval
  end-to-end, reusing the existing H3 physical source identity (§21).

## 5. Out of scope (binding)

Any evaluation of `InformationElementRequirement` conformance or Blueprint satisfaction of any kind (§18
— reserved for H4, not yet governed); any import of, dependency on, or reference to `Blueprint`,
`ConceptRequirement`, `RelationshipRequirement`, `InformationElementRequirement`, `SemanticMapping`,
`SemanticMappingResolution`, H2, Gate I, or Gate J (§18); any modification to `SourceObservation` or any
other Supplier-Risk artifact (§17); any external submission/ingestion API, source-system push endpoint,
browser-submission surface, ETL pipeline, connector framework, batch-ingestion platform, or event-ingestion
mechanism of any kind (§20 — reserved for a future, separately-governed capability); any datatype
interpretation, parsing, coercion, normalization, trimming, or semantic typing of `observed_representation`
(§8); any "current," "latest," "best," "valid," or "non-stale" value-selection semantics (§13); any
retention, archival, purge, or deletion mechanism of any kind (§14 — reserved for a future,
separately-governed capability); any update, correction-in-place, or destructive-overwrite mechanism of any
kind (§12); any new authentication or authorization boundary (§20); any completeness, validity, correctness,
freshness, severity, score, risk, or remediation claim of any kind (§19); any new numbered architecture
baseline (§31).

## 6. Conceptual `FieldValueEvidence` contract (binding)

A new, minimal, immutable domain fact, sibling to `SourceField` within the already-governed
`backend/app/domain/integration/` package (§16):

- `field_value_evidence_id: Identifier` — the deterministic semantic identity of this fact (see below),
  matching every sibling type in `backend/app/domain/integration/`.
- `source_field_id` — governed reference to the already-existing `SourceField` this evidence concerns
  (CDD-019, unmodified).
- `source_record_reference` — the physical source-record identifier that produced the observation (e.g.
  `"100045"`); identifies a physical source record only — never reinterpreted as a canonical enterprise
  entity, resolved Supplier, Blueprint Concept, or Entity Resolution identity of any kind (§10).
- `observed_representation` — the raw, unmodified source representation, exactly as observed (§8).
- `observed_at` — the source-system-asserted observation time.
- `received_at` — the trusted CTEC admission time (§11).

Optionally: `evidence_reference` — an opaque provenance/audit pointer, carrying no independent semantic
weight.

**Forbidden on this contract, under any circumstance**: a directly-stored `tenant_id` (§7); a duplicated
`source_object_id` or `source_system_id` (derivable transitively, never carried directly — mirroring
CDD-021's own "wrap, never duplicate" precedent); any Blueprint, `InformationElementRequirement`, or
`SemanticMapping` identifier; any obligation, mapping-status, Blueprint-satisfaction, completeness,
validity, correctness, or freshness field; any severity, score, or risk field; any remediation field; any
`lifecycle_state`, `governance_status`, `version_number`, `previous_version_id`, `modified_by`, or
`modified_on` field (§12 — this fact is append-only; it has no update lifecycle to version).

If a future Artifact Authorization discovers a field genuinely required beyond this list, implementation
MUST STOP and return it to Product Owner review rather than silently adding it.

**Deterministic identity (binding)**: `field_value_evidence_id` is not a randomly-generated surrogate
key — it is the **stable, deterministic semantic identity** of one admitted `FieldValueEvidence` fact,
derived exclusively from exactly four semantic identity inputs, and from no others: `source_field_id`,
`source_record_reference`, `observed_representation`, `observed_at`. `received_at` MUST NOT participate in
this derivation — it is trusted-admission metadata, not source-observation identity, and including it
would cause a later-arriving retry/replay of the same logical observation to compute a different identity,
violating the replay guarantee (§25). `evidence_reference` MUST NOT participate either — it is optional
provenance and cannot be required to establish identity.

This governs, as binding cases:

- **Identical replay** — identical values for all four inputs MUST resolve to the identical
  `field_value_evidence_id`; no second semantic fact is created, and the originally-persisted `received_at`
  MUST be preserved unchanged (§25).
- **A later correction** (same `source_field_id`/`source_record_reference`, different
  `observed_representation` and/or `observed_at`) — a genuinely **different** `field_value_evidence_id`;
  both facts coexist (§12).
- **The same value re-observed at a different time** (same `source_field_id`/`source_record_reference`/
  `observed_representation`, different `observed_at`) — likewise a different identity; both facts coexist.
- **A different `SourceField` or a different `source_record_reference`** — always a different identity,
  regardless of any other input's value.

The four inputs are combined via the repository's already-established deterministic-identity convention —
the `uuid5`-under-a-governed-namespace pattern already proven by `BlueprintSeeder`/`OntologySeeder`/
`DemoSemanticMappingSeeder` (CDD-017 G3.5, CDD-019 H3) — canonicalizing each input exactly as already
governed elsewhere in the repository, and nowhere else: `source_field_id` via its own canonical string
form; `source_record_reference`/`observed_representation` as their raw, ungoverned strings, with no
trimming, lowercasing, or normalization of any kind (§8, unchanged); and `observed_at` via the same
UTC-normalized ISO-8601 serialization already used for trusted timestamps elsewhere in the repository
(`.astimezone(UTC).isoformat()`, the existing trusted-admission precedent). This CDD does not prescribe the
exact delimiter or library call used to combine them — that remains an Artifact Authorization
implementation detail, consistent with every prior CDD's own level of abstraction — but the four inputs,
their exclusions (`received_at`, `evidence_reference`), and the canonicalization sources being reused (not
invented) are binding.

Because `field_value_evidence_id` is itself deterministically equivalent to the four semantic identity
inputs, its own primary-key uniqueness is sufficient to enforce both halves of the required behavior at
once: replaying identical inputs collides on the same key (satisfying the identical-replay guarantee),
while any legitimately different input produces a different key (preserving the coexistence guarantee,
§12). **No additional database uniqueness constraint — in particular, none over `source_field_id` +
`source_record_reference` alone — is authorized or required**, since such a constraint would incorrectly
block legitimate coexisting observations (§12).

Because the persisted fact is immutable (§12) and never rewritten, a replay whose supplied
`evidence_reference` differs from (or is absent from) the originally-persisted fact does not update, merge,
or overwrite that field — the original fact, including its original `evidence_reference` value if any, is
returned unchanged. No provenance-merging or update behavior is introduced by this CDD.

## 7. Tenant ownership (binding)

`FieldValueEvidence` never stores `tenant_id` directly. Tenant ownership is derived exclusively through
the already-governed chain: `FieldValueEvidence.source_field_id` → `SourceField.source_object_id` →
`SourceObject.tenant_id` — identical in shape to `SourceField`'s own already-governed transitive-tenant
precedent (CDD-019 §18: "no `tenant_id` column — tenant is resolved transitively through
`source_object_id`"). Tenant-scoped retrieval MUST validate the requested tenant through this chain before
returning any evidence. Evidence belonging to one tenant MUST NEVER be returned for a different requested
tenant under any code path. A tenant-ownership mismatch MUST fail explicitly (raising, consistent with
CDD-021 §23's "raise explicitly rather than silently omit or fabricate" precedent) — it MUST NOT be
silently converted into an empty "no evidence found" result, since doing so would hide a violated
ownership invariant rather than surface it.

## 8. Raw value representation (binding)

`observed_representation` is a bounded raw string, preserving physical source representation exactly as
observed — including whitespace, which is never trimmed. Examples of equally valid, unmodified
representations: `"Acme Taiwan Ltd"`, `"0"`, `"false"`, `"2026-08-20"`, `""`. This CDD authorizes no
datatype interpretation, no datatype registry, no JSON/object/collection value system, no parsing, no
coercion, no normalization, and no semantic typing of any kind. `InformationElementRequirement`/Blueprint
carry no type system to interpret against (CDD-017 §11, unchanged) — this CDD does not attempt to invent
one at this layer either. This capability records what was observed; it does not interpret what the
representation means.

## 9. Empty-observation semantics (binding)

Three, and only three, distinct facts are authorized:

1. **No row exists** — no admitted `FieldValueEvidence` fact is represented by this capability for the
   requested `SourceField`/record.
2. **A row exists with `observed_representation = ""`** — the source explicitly supplied an empty
   representation; this is itself evidence, distinct from case 1.
3. **A row exists with a non-empty `observed_representation`** — the source supplied that raw
   representation.

Database/Python `NULL` for `observed_representation` is **not authorized** for this CDD's MVP scope — it
would introduce a fourth, ungoverned semantic state whose meaning this CDD does not define. None of the
three authorized cases may be interpreted, by this CDD or any artifact it authorizes, as: incomplete;
invalid; a missing Blueprint requirement; a failed requirement. Those are evaluation semantics, entirely
outside this capability's authority (§18, §19).

## 10. Source-record identity (binding)

`source_record_reference` identifies the physical source record that produced the observation only (e.g.
row key `"100045"` within `SourceObject` `LFA1`, for `SourceField` `NAME1`) — the same free-text-identity
*concept* `SourceObservation.source_record_reference` already uses (reused as a concept, never as a shared
type or dependency; §17). It MUST NOT be reinterpreted, by this CDD or any artifact it authorizes, as a
canonical-entity identity, a resolved Supplier identity, a Blueprint `ConceptRequirement` identity, or an
Entity Resolution identity of any kind. This CDD governs physical source provenance only.

## 11. Timestamp contract (binding)

- `observed_at` — source-system-asserted observation time, timezone-aware.
- `received_at` — the trusted CTEC admission timestamp, timezone-aware, assigned exactly once by a trusted
  application/runtime admission boundary, **never** authoritatively supplied by a browser or client, and
  preserved unchanged across duplicate submission, retry, or replay of the same admitted evidence —
  restating, not amending, the identical discipline already governed by CDD-010 and the CDD-010/CDD-013
  Trusted Admission Timestamp and Idempotency Contract Remediation Report ("the trusted application
  boundary assigns it exactly once during atomic runtime admission... Replay and retry reuse protected
  handoffs and therefore preserve observation `received_at`").

No other timestamp is authorized by this CDD. In particular: no replay timestamp, no attempt timestamp, no
`modified_at`. A future H4 may independently define and own its own `evaluated_at` — that is H4's own,
later, separate authority, never this CDD's.

## 12. Immutability (binding)

`FieldValueEvidence` is an immutable, append-only fact. No update lifecycle, and no destructive overwrite
of any kind, is authorized by this CDD. A later correction or re-observation from the source system is a
**new**, separate `FieldValueEvidence` fact — never a mutation of an existing row. For example, an initial
observation of `"Acme Taiwan Ltd"` for record `100045`/`NAME1` and a later corrected observation of `"Acme
Taiwan LLC"` for the same record/field may coexist as two separate, immutable facts; the earlier fact is
never rewritten or deleted. This CDD does not determine, and no artifact it authorizes may determine, which
of two or more coexisting facts is current, latest, preferred, correct, valid, or authoritative over
another (§13).

## 13. Retrieval semantics (binding)

Exactly two retrieval operations are authorized:

1. Retrieval by explicit `field_value_evidence_id`.
2. Tenant-scoped retrieval of the governed evidence set for a given `(tenant_id, source_field_id)` pair —
   which may return zero, one, or multiple `FieldValueEvidence` facts (§12).

No other retrieval shape is authorized. In particular, this CDD does not define, and no artifact it
authorizes may define, `get_current_value`, `get_latest_value`, `get_best_value`, `get_valid_value`, or
`get_non_stale_value` — no temporal or business winner-selection semantics of any kind. That capability, if
ever needed, belongs to a future, separately-governed consumer (very plausibly H4 itself), not to this CDD.

## 14. Retention and lifecycle exclusion (binding)

This CDD's MVP scope is append-only and immutable with **no** purge mechanism, no TTL, no automatic
retention scheduler, no archival workflow, and no deletion lifecycle of any kind — and correspondingly no
`lifecycle_state` and no `governance_status` field on `FieldValueEvidence` (§6). This is an explicit,
bounded MVP scope decision, not an accidental omission, and it does **not** establish "retain forever" as
enterprise policy. This CDD simply does not own retention or deletion semantics. A future, separately
governed retention/privacy/storage-lifecycle capability may define archival or deletion without changing
`FieldValueEvidence`'s own meaning or contract.

## 15. Persistence decision (binding)

`FieldValueEvidence` is persisted — unlike the ephemeral, on-demand derivations Gate I/G4/Gate J each
authorize, this capability's entire purpose is durable, reproducible provenance a future H4 evaluation
could point back to even if live source data later changes. This CDD anticipates a new persisted
representation/table, a migration, repository persistence support, and deterministic tests — but drafting
this governance document does not itself authorize creation of any of those artifacts; that boundary is
reserved entirely for a separate, subsequent, CDD-Template-v2.2-compliant Artifact Authorization companion
(§29, mirroring every prior gate's identical two-phase discipline), which does not yet exist and is not
authorized by this document.

## 16. Domain ownership (binding)

`FieldValueEvidence` belongs to the existing physical source-integration domain that already contains
`SourceSystem`, `SourceObject`, and `SourceField` — conceptually, `backend/app/domain/integration/` — as a
new sibling module to `source_field.py`, never a modification of it or of any file in that package. This
follows `SourceField`'s own minimal-dataclass, `Identifier`-typed, no-semantic-vocabulary construction
discipline exactly. See §2 for the explicit, binding disambiguation from the differently-governed
`backend/app/integration/` package.

## 17. Ownership boundary versus existing capabilities

Verified directly against every plausible existing capability:

- **`SourceObservation`** (RFC-014/CIM-001, CDD-011): a categorically different, already-FROZEN capability
  — ephemeral, non-persisted, `subject_id`-anchored, mandatorily `severity`-bearing, no `source_field_id`,
  no `tenant_id`. Not modified, not extended, not depended upon (§2).
- **`Evidence`/`evidences`** (ECOM base model, CDD-005/006/007): a governed vocabulary/lifecycle entity
  linked to `Assertion` via `assertion_evidence`, with no value column, no `tenant_id`, and only a nullable
  `source_object_id` (never `source_field_id`); unused by any application service in the repository. Wrong
  shape and wrong owner; not referenced by any artifact this CDD authorizes.
- **`Assertion`/`Assertion.predicate`** (CDD-003/006, ASM-001): a different, already-FROZEN institutional
  evidence-fact capability, already independently disclaimed as unrelated to `SourceField` by CDD-019 §17.
  Not referenced here either.
- **H4 — Blueprint Information-Element Conformance Integration** (CDD-019 §6, §20; not yet governed,
  un-numbered): the future capability this CDD is a strict prerequisite for. Not designed, not partially
  implemented, not authorized by this CDD under any circumstance (§18).

No ownership overlap identified with any existing or currently-named future capability.

## 18. Blueprint / semantic firewall (binding, critical)

This CDD MUST NOT depend on, import, or reference `Blueprint`, `ConceptRequirement`,
`RelationshipRequirement`, `InformationElementRequirement`, `SemanticMapping`, `SemanticMappingResolution`,
H2, Gate I, or Gate J, in any artifact, in any form. This CDD owns physical `SourceField` evidence only. It
establishes FACT. It does not perform, and no artifact it authorizes may perform, any Blueprint evaluation
of any kind.

## 19. Evidence boundary — FACT / EVALUATION / INFERENCE firewall (binding, critical)

Every statement this CDD's lineage produces, in any artifact, MUST be classifiable as exactly one of:

- **FACT** — the sole category this CDD authorizes, e.g.: *"`LFA1-NAME1` for source record `100045` was
  observed with raw representation `'Acme Taiwan Ltd'` at `observed_at` T1 and was admitted by CTEC at
  `received_at` T2."*
- **EVALUATION** — e.g. *"the Supplier Legal Name requirement is satisfied"* — reserved exclusively for a
  future H4; never produced by any artifact this CDD authorizes.
- **INFERENCE** — any conclusion drawn beyond FACT; never produced by any artifact this CDD authorizes.
- **UNSUPPORTED CLAIM** — anything the available FACT does not establish; in particular, this CDD's own
  artifacts must never state or imply: the Supplier (or any enterprise entity) is valid, approved, or high
  risk; source data is complete, correct, fresh, or stale; remediation of any kind is necessary. None of
  these are ever produced by any artifact this CDD authorizes.

## 20. Submission and ingestion exclusion (binding)

This CDD governs storage and retrieval of already-admitted `FieldValueEvidence` only. Production evidence
submission/ingestion — by what mechanism a real observed value is admitted into CTEC from a real source
system in the first place — is **explicitly out of scope** and is not designed, answered, or partially
answered by this CDD. This CDD authorizes no external HTTP endpoint, no source-system submission API, no
browser-submission surface, no batch-ingestion platform, no ETL pipeline, no connector framework, no
event-ingestion mechanism (Kafka or otherwise), no file-ingestion mechanism, and no new
authentication/authorization boundary of any kind. A future, separately-governed capability must discover
and govern production evidence submission. This CDD's own Artifact Authorization companion (§29) may
authorize only a deterministic, explicitly-labeled test/demo fixture sufficient to prove this CDD's own
persistence and retrieval behavior (§21) — that fixture MUST NOT be treated as, or evolve into, a
production admission contract.

## 21. Deterministic acceptance scenario (binding target)

Reusing the existing, unmodified H3 physical source identity (`H3 Demo ERP` → `LFA1` → `LFA1-NAME1`, CDD-019
H3, unchanged), a deterministic test/demo `FieldValueEvidence` fact — for example, `source_record_reference
= "100045"`, `observed_representation = "Acme Taiwan Ltd"` — must, at minimum, demonstrate:

1. Evidence can be persisted and remains linked to the intended `SourceField`.
2. Tenant ownership is correctly derived through `source_field_id` → `source_object_id` → `tenant_id`.
3. The correct tenant can retrieve the evidence; a different tenant cannot (§7).
4. The raw representation is preserved exactly as supplied, unmodified.
5. An explicit empty representation is distinguishable from the complete absence of a row (§9).
6. Multiple observations for the same `SourceField` may coexist without conflict (§12).
7. An existing observation is never destructively overwritten by a later one (§12).
8. Re-running the deterministic fixture with identical inputs resolves to the same
   `field_value_evidence_id`, creates no duplicate fact, and preserves the originally-persisted
   `received_at` unchanged (§6, §25) — mirroring `BlueprintSeeder`'s own `test_seeder_is_idempotent`
   precedent (CDD-017 G3.5, CDD-019 H3).

This scenario MUST NOT evaluate Supplier Legal Name, invoke H4, invoke Gate I, invoke Gate J, or create or
modify any `SemanticMapping`. The exact deterministic identifiers/timestamps are deferred to the
subsequent Artifact Authorization companion (§29) — not fixed by this governance document itself.

## 22. Application/service boundary

Any application service this CDD's companion eventually authorizes performs persistence and tenant-scoped
retrieval only, matching every existing application-service precedent's discipline of minimal public
surface (`SourceFieldRepository`'s own `create`/`get_by_id`-only precedent, CDD-019 H1). No `Protocol`
dependency beyond what a minimal repository interface requires; no business-rule computation of any kind.

## 23. Security and tenancy boundaries

No new authentication or authorization mechanism, scope, or Keycloak configuration is authorized (no
external surface exists to protect, §20). Tenant isolation is achieved entirely by the transitive
derivation chain already governed for `SourceField` (§7) — no new isolation mechanism is introduced.

## 24. API and frontend exclusions

No external HTTP endpoint, FastAPI router, or API schema is authorized. No frontend, UI, or authoring
surface of any kind is authorized. This matches the default every prior Gate G/H/I/J phase has held:
internal-only capability, with any future external submission surface requiring its own, separately
authorized PAD amendment (§20).

## 25. Determinism and idempotency

Retrieving the same, unchanged `FieldValueEvidence` set for an unchanged `(tenant_id, source_field_id)`
pair MUST yield an identical result on repeated retrieval. Identical replay of the same admitted evidence —
identical `source_field_id`, `source_record_reference`, `observed_representation`, and `observed_at` (§6)
— MUST resolve to the same, already-persisted `field_value_evidence_id` and MUST NOT create a duplicate
semantic fact: on an identity collision, the persisting mechanism MUST return the existing fact unchanged,
performing no write of any kind — mirroring `BlueprintSeeder.load()`'s exact existence-check-then-skip
idempotency pattern (CDD-017 G3.5) — and MUST preserve the originally-assigned `received_at` unchanged,
never replacing it with a new admission timestamp. §6's deterministic identity formula is now the full,
binding duplicate-detection mechanism for this CDD's own authorized scope; CDD-010/CDD-013 remain the
authority only for the discipline that `received_at` is trust-boundary-owned and never client-controlled
(§11), not for the duplicate-detection mechanism itself, since that authority's own mechanism (an
HTTP-admission-boundary client-fingerprint comparison) has no analog within this CDD's own authorized scope
(§20).

## 26. Failure semantics (binding)

A tenant-ownership mismatch (§7) MUST raise explicitly rather than silently return an empty result. If the
`SourceField` referenced by an evidence-retrieval request does not exist, the failure MUST be explicit
rather than silently fabricated as "no evidence" — consistent with CDD-021 §23's identical binding
instruction elsewhere in this governance family.

## 27. Phase scope (binding)

This CDD authorizes exactly one implementation phase: the persisted `FieldValueEvidence` domain type, its
repository, and the deterministic test/demo acceptance fixture (§21). No sub-phase split is authorized or
required — the scope is already the smallest independently-meaningful unit. A single Artifact Authorization
Companion governs the whole of it, mirroring CDD-020's own I1 companion precedent (one companion, one
implementation cycle).

## 28. Authorized business artifacts

None authorized. This CDD introduces no new Business Capability Specification or business-authority
artifact — it implements a physical-evidence-persistence capability over already-governed `SourceField`
identity (CDD-019), matching CDD-018 §23's, CDD-019 §24's, CDD-020 §24's, and CDD-021 §25's identical
precedent.

## 29. Authorized persistence, domain, and implementation artifacts

**Reserved for a future, separately-authorized implementation phase, not authorized by this governance
document itself.** This CDD authorizes the *architecture* of Governed Source Field-Value Evidence
(§6-§27); it does not itself authorize writing any domain type, repository, migration, or test artifact.
The exhaustive artifact-authorization table for the initial implementation phase (mirroring CDD-021's own
J1/J2 companion's exact format) is intentionally deferred to that phase's own CDD-Template-v2.2-compliant
authorization record. Implementation MUST NOT proceed against §6-§27's model without that separate,
subsequent artifact-authorization record existing first — the identical binding precondition CDD-017
§17/§19, CDD-018 §25, CDD-019 §25, CDD-020 §26, and CDD-021 §26 each established, restated here for this
CDD's own authority.

## 30. Authorized configuration artifacts

None authorized. No new environment variable, Keycloak scope, or deployment configuration is authorized by
this CDD (§20, §24 — no external surface means no new scope is needed yet).

## 31. Numbered architecture baseline determination

**No new numbered architecture baseline is required.** Resolved directly from repository precedent,
following the identical method CDD-017 §24, CDD-019 §31, CDD-020 §31, and CDD-021 §32 used: this CDD
introduces no new RFC-tier or PAD-tier document — it cites CDD-010, CDD-017, CDD-018, CDD-019, CDD-020,
and CDD-021 unchanged, and defers any possible future PAD (if an external submission API is ever
authorized, §20) and any possible future RFC (if new vocabulary is ever needed — none is anticipated) to
their own, separate, later publications. CDD-011 through CDD-021 were all published via
`architecture/INDEX.md`'s non-baseline-tracked "Governed implementation work orders" table alone, with no
new `architecture/released/v1.\d+/` directory created for any of them — confirmed structurally exempt from
`scripts/verify_architecture_release.py`'s baseline checks, identical to every prior CDD entry there. This
CDD would follow that identical, now eleven-times-proven pattern.

## 32. Authorization

Authorized by CTEC Product Owner Manoj Nair: this Work Order's freeze to FROZEN governance state, per the
H4 Product Owner Architecture Decision (identifying this capability as a strict, load-bearing prerequisite
for future H4), the Field-Value Evidence Architecture Approval (Product Owner Decisions Y1-Y5), CDD-022
Governance Drafting, the CDD-022 Governance Review (P0 = 0, P1 = 1 — P1-1, `FieldValueEvidence`
identity/idempotency semantics underspecified), the P1-1 Remediation (freezing the deterministic
four-input identity formula, §6), and this Freeze Authorization's own final verification confirming
P0 = 0, P1 = 0. No implementation exists yet — a separate, subsequent artifact-authorization companion is
required before any persistence, domain, application, or test artifact for the initial implementation
phase is created, and that companion itself requires its own separate approval before any such file is
created or modified. Governance publication (registration in `architecture/INDEX.md`) is likewise a
separate, not-yet-authorized action. H4, any external submission/ingestion mechanism, and any
retention/archival/deletion capability are not authorized by this document under any circumstance and each
require, or will require, their own, separate, future governance.
