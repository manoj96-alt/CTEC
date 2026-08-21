# CDD-022 — Field-Value Evidence Artifact Authorization

Version: 1.0
Status: APPROVED ARTIFACT AUTHORIZATION
Authority base: `91bfe4644b72806929f7addb0653e426cedec9a8`

## 1. Authority and scope

CDD-022 §29 defers the exhaustive per-file artifact-authorization record for its initial implementation
phase to a separate, subsequent, CDD-Template-v2.2-compliant document, explicitly mirroring CDD-021's own
J1/J2 companion's exact format and governance-cycle discipline (CDD-022 §3, §29). This report is that
record for **CDD-022's single, undivided implementation phase** (CDD-022 §27: "exactly one implementation
phase... No sub-phase split is authorized or required"). This is a standalone companion to CDD-022,
following the identical companion precedent already used nine times across CDD-017, CDD-018, CDD-019,
CDD-020, and CDD-021.

This record was produced through: artifact discovery (§3, no CDD-022 governance gap, no unresolved
architecture decision, fourteen-artifact proposed surface); a Product Owner content review that found two
P1s (collision-unsafe naive delimiter concatenation; seeder-only, non-structural identity ownership); a
remediation cycle resolving both via a length-prefixed canonical encoding and domain-owned identity
derivation/verification (§7, §10); and a final adversarial re-verification confirming P0 = 0, P1 = 0. No
implementation exists yet, and none is authorized by this record's approval alone — a separate, subsequent
Product Owner implementation authorization is still required before any file listed below is created or
modified (CDD-022 §29, restated).

## 2. Objective (binding, restated from CDD-022 §1, §6)

Persist and retrieve, for a given tenant and a specific already-governed `SourceField` (CDD-019,
unmodified), an immutable, append-only `FieldValueEvidence` fact recording a raw observed representation —
answering only *"what authoritative observed-value evidence exists for this SourceField?"* Establishes
FACT only. Performs no Blueprint or `InformationElementRequirement` evaluation, never invokes H2 or Gate I,
and never depends on `SourceObservation`. Larger than the typical single-artifact companion in this
lineage because CDD-022 §27 explicitly authorizes domain, persistence, migration, and deterministic-fixture
artifacts together as one undivided phase, unlike CDD-019/020/021's own narrower application-service-only
companions that reused already-existing persistence.

## 3. Repository evidence inspected (binding, restated for the record)

- **Domain construction precedent**: `backend/app/domain/integration/source_field.py`,
  `source_object.py`, `source_system.py` (all frozen, unmodified, CDD-019) — confirmed directly this turn:
  `@dataclass(frozen=True, slots=True)`, `Identifier`-typed FK fields, `__post_init__` validation checking
  `Identifier` type, non-empty/length-bounded text for governed-name fields, and explicit
  timezone-awareness checks on every `datetime` field (`if value.tzinfo is None: raise
  ValidationException(...)`). `FieldValueEvidence` mirrors this construction discipline exactly.
- **Text value-object incompatibility, confirmed by direct read**: `backend/app/domain/shared/value_objects/reference.py`
  — every existing text value object (`CanonicalName`, `BusinessName`, `Description`, `ReferenceCode`)
  shares one `_validate_text` helper that **rejects empty or whitespace-only text**
  (`if not value.strip(): raise ValidationException(...)`). This directly conflicts with CDD-022 §9's
  binding requirement that `observed_representation = ""` be an explicitly permitted, distinct fact. None
  of the four existing value objects may be used for `observed_representation`; it is therefore typed as a
  plain, unwrapped `str`, with domain validation limited to `isinstance(value, str)` — no non-empty check,
  no strip, no normalization (CDD-022 §8, §9). `source_record_reference` and `evidence_reference` are
  likewise plain `str`/`str | None` for the identical reason — `ReferenceCode`'s only existing usage
  (`backend/app/domain/foundation/country.py`, an ISO-style country code) is a narrower, unrelated
  semantic concept and is not reused here to avoid misapplying it.
- **Deterministic-identity precedent, confirmed by direct read — and its limits**: `BlueprintSeeder._stable_id`
  (`blueprint_seed.py`), `OntologySeeder._stable_id` (`ontology_seed.py`), and
  `DemoSemanticMappingSeeder._stable_id` (`demo_semantic_mapping_seeder.py`) each independently implement
  `uuid5(BOOTSTRAP_SEED_NAMESPACE, f"{<module's own SEED_VERSION constant>}:{...}")` over a naive
  colon-joined string. **Adversarial review of this Artifact Authorization (Product Owner Decision, this
  turn) found this naive form is not collision-safe when applied to CDD-022's own unrestricted raw-string
  inputs**: `source_record_reference = "100045:extra"` + `observed_representation = "Acme Taiwan Ltd"`
  produces the identical joined material as `source_record_reference = "100045"` +
  `observed_representation = "extra:Acme Taiwan Ltd"` — a real collision between two facts CDD-022 §6
  requires to have different identity. The three existing seeders never encountered this because their own
  "name" inputs are always small, curated, colon-free literals hardcoded in the seeder's own source — never
  arbitrary external text — so their precedent does not resolve collision-safety for `FieldValueEvidence`.
  **Approved replacement (Product Owner Decision, this turn)**: a length-prefixed, self-delimiting
  canonicalization (§7 below) — each of the four semantic-identity components is encoded as `<its own
  UTF-8 byte length>:<its own raw bytes>` before concatenation, making the encoding uniquely decodable
  (each component's boundary is declared, not inferred from delimiter characters that may themselves appear
  inside raw source data) — a standard technique (the same principle as Bencode/netstring encoding),
  provably free of the collision class demonstrated above.
- **Domain-layer/`app.core` import precedent, confirmed by direct read**: `backend/app/domain/governance_engine/configuration.py`
  and `backend/app/domain/decision_engine/configuration.py` already import from `app.core` — confirming the
  domain layer importing pure constants from `app.core.bootstrap` (as `FieldValueEvidence` now does for
  `BOOTSTRAP_SEED_NAMESPACE`, per the domain-owned identity decision below) is not a new architectural
  layering exception; `bootstrap.py` itself contains only constants (UUIDs, strings, one datetime), no I/O
  and no framework code.
- **Identity-ownership precedent, confirmed by direct read — and its limits**: `BlueprintSeeder`'s own
  `_stable_id` lives in the seeder (infrastructure layer), and nothing in `Blueprint`'s own domain
  `__post_init__` verifies that a supplied `blueprint_id` actually matches a re-derivation from the
  Blueprint's other fields — the domain type simply trusts whatever `Identifier` it is given. **Adversarial
  review found this precedent, if followed literally for `FieldValueEvidence`, would let any caller
  construct a semantically-duplicate fact under an arbitrary, non-deterministic ID, defeating CDD-022 §25's
  replay guarantee structurally, not merely by convention (Product Owner Decision, this turn).**
  `FieldValueEvidence` therefore departs from `Blueprint`'s own precedent in this one respect: identity
  derivation and verification are domain-owned (§7 below) — every construction, whether via the new
  `FieldValueEvidence.new(...)` factory or via direct rehydration from a persisted row, re-derives the
  expected ID from the object's own four semantic fields and raises `ValidationException` on mismatch, in
  `__post_init__`, uniformly for both paths.
- **Timestamp canonicalization precedent, confirmed by direct read**: `backend/app/application/supplier_risk_api.py`
  line 102, `received_at = admitted_at.astimezone(UTC).isoformat()` — the existing, governed
  trusted-timestamp-to-string serialization this CDD's identity formula reuses for `observed_at` (CDD-022
  §6), exactly as CDD-022's own text already specifies.
- **Migration precedent, confirmed by direct read**: `0015_source_field_semantic_mapping.py` (CDD-019 H1)
  — every UUID primary key, including `blueprints.blueprint_id`/`concept_requirements.concept_requirement_id`
  which are *always* application-supplied deterministic values (never left to the database default), still
  carries `server_default=sa.text("gen_random_uuid()")` — the default is a fallback for unset values only
  and does not conflict with an application-computed deterministic ID being supplied explicitly on every
  insert. `field_value_evidence_id`'s column follows this identical, four-times-proven pattern.
- **Idempotent-write precedent, confirmed by direct read — refined this turn**: `BlueprintSeeder.load()`
  performs its own existence check before calling the repository, with no idempotency logic in the
  repository itself. **Product Owner Decision (this turn) refines this for `FieldValueEvidence`**: because
  identity is now domain-verified (above), a genuine "same ID, different semantic content" case can only
  arise from a corrupted/tampered persisted row, not from normal replay — this defensive check belongs in
  the repository, not the seeder, since it is about *persistence* correctness (comparing an incoming
  domain object against whatever the database actually holds under that ID), not about *deriving* identity.
  `FieldValueEvidenceRepositoryImpl` therefore owns one bounded, idempotent write operation —
  `create_or_get_existing` (§7, §10 below) — while `DemoFieldValueEvidenceSeeder` owns only fixture
  orchestration and never re-implements the identity algorithm itself.
- **Failure-signaling precedent, confirmed by direct read**: every "raise explicitly" requirement across
  this entire lineage (H2's ambiguity, Gate I's blueprint-not-found, Gate J's owning-concept-not-found,
  CDD-021 §23/§26) raises the single, already-governed `ValidationException`
  (`backend/app/domain/shared/exceptions.py`), distinguished only by message text — never a newly-invented
  exception subclass per failure mode. CDD-022 §26's tenant-mismatch/not-found distinctions follow this
  identical precedent exactly, via distinct message text, not distinct exception types.
- **Migration-registry consequence, confirmed by direct read**: `test_decision_engine.py`,
  `test_governance_engine.py`, `test_knowledge_engine.py`, and `test_persistence_integration.py` each
  assert the exact current Alembic head revision string (`"0015_source_field_semantic"`);
  `test_persistence_integration.py` additionally asserts the exact current table count (`59`). Adding
  `0016_field_value_evidence` as the new head mechanically requires updating these five assertions
  (revision string in all four; table count `59` → `60` in `test_persistence_integration.py` only) — a
  purely mechanical consequence of the migration existing, not a new architecture decision.
- **H3 companion structural precedent, confirmed by direct read**: `DemoSemanticMappingSeeder`
  (`demo_semantic_mapping_seeder.py`) — "Never invoked by normal production bootstrap... has its own,
  separate, manually-run CLI entrypoint," refuses every non-exact tenant, proven by a non-DB unit test
  (`test_demo_semantic_mapping_seeder.py`, tenant-refusal cases) and a Postgres test
  (`test_demo_semantic_mapping_seeder_postgres.py`, idempotency + resolution proof). The new
  `DemoFieldValueEvidenceSeeder` and its two test files mirror this exact structure.
- **`AUTHORIZED_CHANGED_PATHS` mechanism**: `backend/app/tests/test_runtime_architecture.py` — confirmed
  unchanged mechanism, extended identically by every prior Gate G/H/I/J phase; this record extends it by
  the full 13-path CREATE+MODIFY surface below (excluding itself).

## 4. Authorized artifacts

| Artifact and path | Action | Authority | Purpose | Exclusions | Evidence |
|---|---|---|---|---|---|
| `backend/app/domain/integration/field_value_evidence.py` | CREATE | CDD-022 §6-§12, §25 | `FieldValueEvidence` — frozen, slotted dataclass, sibling to `SourceField`: `field_value_evidence_id: Identifier`, `source_field_id: Identifier`, `source_record_reference: str`, `observed_representation: str`, `observed_at: datetime`, `received_at: datetime`, `evidence_reference: str \| None`. Also defines, in the same module (Product Owner Decision, this turn — domain-owned identity, no separate helper file): the fixed constant `_IDENTITY_ALGORITHM_VERSION = "FIELD_VALUE_EVIDENCE_IDENTITY_V1"`; a module-level `derive_field_value_evidence_id(*, source_field_id: UUID, source_record_reference: str, observed_representation: str, observed_at: datetime) -> UUID` function implementing the length-prefixed canonicalization (§7); and a `FieldValueEvidence.new(cls, *, source_field_id, source_record_reference, observed_representation, observed_at, received_at, evidence_reference=None) -> FieldValueEvidence` classmethod that calls `derive_field_value_evidence_id(...)` and constructs the instance with the derived ID. `__post_init__` validates: `field_value_evidence_id`/`source_field_id` are `Identifier`; `source_record_reference` is non-empty `str`; `observed_representation` is `str` (no non-empty check — `""` explicitly permitted, CDD-022 §9); `evidence_reference` is `str` or `None`; `observed_at`/`received_at` are timezone-aware `datetime`; and — for **every** construction, whether via `.new()` or the raw constructor (used by the repository for rehydration) — re-derives `derive_field_value_evidence_id(...)` from the instance's own four semantic fields and raises `ValidationException` if it does not equal the supplied `field_value_evidence_id` (Product Owner Decision, this turn — domain-owned identity verification, §7). | No `tenant_id` field. No `source_object_id`/`source_system_id` field. No Blueprint/`InformationElementRequirement`/`SemanticMapping` field. No `lifecycle_state`/`governance_status`/`version_number`/`previous_version_id`/`modified_by`/`modified_on` field. No normalization, trimming, or datatype coercion of `observed_representation`/`source_record_reference`/`evidence_reference` anywhere. No mutation method. No second identity-derivation implementation anywhere else in the authorized artifact set (§7). | Unit construction + identity-derivation tests (no DB). |
| `backend/app/infrastructure/persistence/models/field_value_evidence.py` | CREATE | CDD-022 §6, §15 | `FieldValueEvidenceORM` (`field_value_evidence`, mirroring `SourceFieldORM`'s naming precedent): `field_value_evidence_id` (`Uuid`, PK, `server_default=gen_random_uuid()` — CDD-019 H1's four-times-proven pattern; always application-supplied in practice), `source_field_id` (`Uuid`, FK → `source_fields.source_field_id`, not null), `source_record_reference` (`String(1000)`, not null), `observed_representation` (`String(1000)`, not null), `observed_at` (`DateTime(timezone=True)`, not null), `received_at` (`DateTime(timezone=True)`, not null), `evidence_reference` (`String(1000)`, nullable). Indexes: `source_field_id`, `observed_at`, `received_at`. | No `tenant_id` column. No `source_object_id`/`source_system_id` column. No lifecycle/governance/version column. No uniqueness constraint beyond the primary key (§6 below). | Postgres persistence test. |
| `backend/app/infrastructure/persistence/field_value_evidence_repository.py` | CREATE | CDD-022 §13, §22, §25 | `FieldValueEvidenceRepository` (`Protocol`) + `FieldValueEvidenceRepositoryImpl`: `create_or_get_existing(evidence: FieldValueEvidence) -> FieldValueEvidence` (Product Owner Decision, this turn, replacing a plain `create`) — looks up `evidence.field_value_evidence_id` via `get_by_id`; if absent, persists `evidence` and returns it unchanged; if present, compares the persisted row's own `source_field_id`/`source_record_reference`/`observed_representation`/`observed_at` against `evidence`'s — if all four match (the expected replay case, since identity is domain-derived from exactly these four, §7), returns the **existing, already-persisted** fact unchanged (its original `received_at` and `evidence_reference` preserved, the incoming object's own `received_at`/`evidence_reference` discarded, never written); if any of the four differ (only possible via a corrupted/tampered row, since identity is domain-verified on construction), raises `ValidationException` with an explicit "identity conflict" message — never overwrites, never mutates, never treats it as a new fact; `get_by_id(field_value_evidence_id: UUID) -> FieldValueEvidence \| None`; `get_by_source_field(*, tenant_id: str, source_field_id: UUID) -> tuple[FieldValueEvidence, ...]` — joins through `source_fields.source_object_id` → `source_objects.tenant_id` to validate tenant ownership (CDD-022 §7), raising `ValidationException` with an explicit "tenant ownership mismatch" message if the `SourceField` exists but resolves to a different tenant, and a distinct "SourceField not found" message if it does not exist at all (CDD-022 §26) — both via the existing `ValidationException`, distinguished by message only (no new exception type). No update or delete method of any kind beyond `create_or_get_existing`'s own bounded semantics. | No `Protocol` dependency beyond `Session`. No import of `Blueprint`/`SemanticMapping`/H2/Gate I/Gate J. No identity-derivation logic of its own (calls only `FieldValueEvidence`'s domain-owned mechanism indirectly, via comparing already-constructed domain objects — never recomputes `derive_field_value_evidence_id` itself). No "latest wins" or provenance-merging behavior. | Postgres persistence test. |
| `backend/app/infrastructure/persistence/migrations/versions/0016_field_value_evidence.py` | CREATE | CDD-022 §15 | Alembic migration `revision = "0016_field_value_evidence"`, `down_revision = "0015_source_field_semantic"`. Creates exactly the `field_value_evidence` table and its three indexes (row 2 above), FK to `source_fields.source_field_id`. `downgrade()` drops them in reverse order, mirroring `0015`'s exact structure. | No `tenant_id` column. No compound uniqueness constraint over `(source_field_id, source_record_reference)` (CDD-022 §6 — would incorrectly block legitimate coexisting observations). No modification to any existing table. No ENUM type created or reused (no lifecycle/governance vocabulary on this table). | Migration upgrade/downgrade test against real PostgreSQL. |
| `backend/app/infrastructure/persistence/demo_field_value_evidence_seeder.py` | CREATE | CDD-022 §20, §21 | `DemoFieldValueEvidenceSeeder`, mirroring `DemoSemanticMappingSeeder`'s exact structure and module docstring discipline ("Never invoked by normal production bootstrap... has its own, separate, manually-run CLI entrypoint"). `seed(self) -> DemoFieldValueEvidenceSeedSummary` (frozen dataclass: `field_value_evidence_id`, `source_field_id`, `source_record_reference`, `observed_representation`): refuses every non-`BOOTSTRAP_DEMO_TENANT_ID` context (mirroring H3's exact tenant-refusal precedent, enforced by only ever resolving the already-seeded demo `SourceField` for `LFA1-NAME1`); calls the existing, unmodified `DemoSemanticMappingSeeder(session).seed()` first (mirroring H3's own "calls `BlueprintSeeder(session).load()` first" precedent) to resolve the real `LFA1-NAME1` `SourceField`; constructs the fact via `FieldValueEvidence.new(source_field_id=..., source_record_reference="100045", observed_representation="Acme Taiwan Ltd", observed_at=<fixed constant>, received_at=<seed-time timestamp>)` — the **domain-owned** factory (§4 row 1) computes `field_value_evidence_id`; calls `repository.create_or_get_existing(evidence)` (§4 row 3) and returns a summary built from whichever fact that call returns (new or pre-existing). Contains **no** identity-derivation logic of its own — `_stable_id`/`uuid5`/`BOOTSTRAP_SEED_NAMESPACE` do not appear in this module (Product Owner Decision, this turn). | No production ingestion API. No new `SourceSystem`/`SourceObject`/`SourceField`/`SemanticMapping` row (reuses H3's existing ones by call only). No evaluation of Supplier Legal Name. No invocation of H4, Gate I, or Gate J. No `SourceObservation` row created. No second deterministic fact/tenant seeded beyond the one CDD-022 §21 requires. No duplicated identity-derivation implementation of any kind (§7). | Unit test (tenant refusal); Postgres acceptance test (idempotency + coexistence + tenant isolation). |
| `backend/app/tests/test_field_value_evidence_persistence.py` | CREATE | CDD-022 §6-§12, §25 | Unit tests (no DB), mirroring `test_source_field_persistence.py`'s construction-test style: (1) valid construction via `.new()` with a non-empty `observed_representation`; (2) `observed_representation = ""` accepted via `.new()`; (3) whitespace-only `observed_representation` preserved unmodified (not rejected, not trimmed); (4) `observed_representation = None` rejected (`ValidationException`); (5) naive (non-tz-aware) `observed_at` rejected; (6) naive `received_at` rejected; (7) `evidence_reference = None` accepted; (8) the dataclass is frozen — attempting attribute assignment raises `FrozenInstanceError`, proving immutability structurally (CDD-022 §12). **Identity/collision evidence (Product Owner Decision, this turn)**: (9) `.new()` with identical `(source_field_id, source_record_reference, observed_representation, observed_at)` yields the identical `field_value_evidence_id` across two separate calls; (10) `source_record_reference = "100045:extra"` + `observed_representation = "Acme Taiwan Ltd"` yields a **different** ID than `source_record_reference = "100045"` + `observed_representation = "extra:Acme Taiwan Ltd"` — the exact delimiter-shift counter-example found during review; (11) `source_record_reference = "a:b"` + `observed_representation = "c"` yields a different ID than `source_record_reference = "a"` + `observed_representation = "b:c"`; (12) `observed_representation = ""` yields a different ID than any non-empty value for otherwise-identical inputs; (13) `observed_representation = " "` (single space) yields a different ID than `observed_representation = ""`; (14) a `observed_representation` containing multi-byte UTF-8 characters (e.g. `"Ácme"`) yields a deterministic ID computed from its true UTF-8 byte length, not its Python `len()` character count (constructed to differ from a same-character-count, different-byte-length ASCII string, proving byte-length — not character-count — governs the encoding); (15) changing only `source_field_id`, only `observed_at`, or only `source_record_reference` each yields a different ID (closing CDD-022 §6's four "always different identity" cases exhaustively); (16) directly constructing `FieldValueEvidence(field_value_evidence_id=Identifier(uuid4()), ...)` with an arbitrary, non-derived ID for otherwise-valid semantic inputs raises `ValidationException` — proving domain-owned identity verification rejects an inconsistent supplied identity, exercising the exact same `__post_init__` code path the repository uses when rehydrating a persisted row (CDD-022 §25, Product Owner Decision this turn); (17) two `observed_at` values representing the identical instant under different UTC offsets (e.g. `2026-08-20T10:00:00-07:00` and `2026-08-20T17:00:00+00:00`) yield the identical `field_value_evidence_id` — proving `.astimezone(UTC)` normalization, not literal offset text, governs the canonical timestamp encoding; (18) holding all four identity inputs fixed and varying only `received_at` across two `.new()` calls yields the identical `field_value_evidence_id` — an explicit proof of `received_at`'s exclusion from identity, distinct from case (9)'s "same inputs" proof; (19) likewise varying only `evidence_reference` yields the identical `field_value_evidence_id`; (20) `observed_representation = "Acme"` yields a different ID than `observed_representation = "ACME"` for otherwise-identical inputs — proving raw case is preserved and never normalized (CDD-022 §8). | No PostgreSQL dependency. No test of persistence/repository behavior (covered elsewhere). No test asserting a severity/score/satisfaction field (none exists). | Direct test execution. |
| `backend/app/tests/test_field_value_evidence_persistence_postgres.py` | CREATE | CDD-022 §7, §12, §13, §25 | Postgres-backed acceptance evidence, composing the real, unmodified `SourceFieldRepositoryImpl`/`SourceObjectRepositoryImpl` against the existing H3 fixture (reused by call only via `DemoSemanticMappingSeeder`): (1) evidence persists via `create_or_get_existing` and round-trips via `get_by_id`; (2) `get_by_source_field(tenant_id=<correct>, ...)` returns the evidence; (3) `get_by_source_field(tenant_id=<wrong>, ...)` raises `ValidationException` (tenant-ownership mismatch) — never an empty result (CDD-022 §7, §26); (4) a nonexistent `source_field_id` raises a distinctly-messaged `ValidationException` (CDD-022 §26); (5) zero evidence for an otherwise-valid `SourceField` returns an empty tuple, not an exception; (6) two `FieldValueEvidence` facts differing only in `observed_representation` coexist as separate rows (CDD-022 §12); (7) two facts differing only in `observed_at` coexist; (8) the earlier fact's row is never overwritten or deleted by inserting the later one; (9) a fact with `observed_representation = ""` is retrievable and distinct from the complete absence of a row for the same `source_field_id`/`source_record_reference` (CDD-022 §9); (10) `evidence_reference` persists as `NULL` when omitted. **Idempotency/conflict evidence (Product Owner Decision, this turn)**: (11) calling `create_or_get_existing` twice with two separately-constructed but semantically-identical `FieldValueEvidence` objects (same four identity inputs, deliberately different `received_at`/`evidence_reference` on the second call) persists exactly one row, returns the **first** call's object (with the first call's own `received_at`) from the second call, and the table's row count remains one; (12) an identity-conflict is provoked by directly manipulating the persisted row's `observed_representation` via raw SQL after the first insert, then calling `create_or_get_existing` again with the original (pre-manipulation) domain object — asserting `ValidationException` is raised, never a silent overwrite or a silently-returned mismatched fact. | No test asserts against H4/Blueprint-evaluation behavior. No test bypasses `SourceFieldRepositoryImpl` to query `source_fields` directly. No modification to `BlueprintSeeder`, `DemoSemanticMappingSeeder`, or any file they depend on. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_demo_field_value_evidence_seeder.py` | CREATE | CDD-022 §20, §21 | Unit tests (no DB), mirroring `test_demo_semantic_mapping_seeder.py`'s exact tenant-refusal parametrized-test style: the seeder refuses every context that does not resolve to `BOOTSTRAP_DEMO_TENANT_ID`. | No PostgreSQL dependency. | Direct test execution. |
| `backend/app/tests/test_demo_field_value_evidence_seeder_postgres.py` | CREATE | CDD-022 §21, §25 | Postgres-backed: (1) seeding twice yields an identical summary (`first == second`) and creates no second row — the deterministic-identity/replay proof (CDD-022 §25, mirroring `test_seeder_is_idempotent`'s exact precedent); (2) the seeded evidence's `source_field_id` resolves to the real, existing H3 `LFA1-NAME1` `SourceField`; (3) the seeded evidence is retrievable via `FieldValueEvidenceRepositoryImpl.get_by_source_field` under the demo tenant and not under a different tenant. | No test asserts against H4/Gate-I-shaped behavior. No test bypasses the real H3 mechanism. No `SourceObservation` row created or asserted against. | Direct test execution (requires `CTEC_TEST_DATABASE_URL`). |
| `backend/app/tests/test_runtime_architecture.py` | MODIFY | CDD-010/CDD-012 mechanism, reused by every prior Gate G/H/I/J phase | Add exactly the following 13 new string entries to `AUTHORIZED_CHANGED_PATHS`: `"backend/app/domain/integration/field_value_evidence.py"`, `"backend/app/infrastructure/persistence/models/field_value_evidence.py"`, `"backend/app/infrastructure/persistence/field_value_evidence_repository.py"`, `"backend/app/infrastructure/persistence/migrations/versions/0016_field_value_evidence.py"`, `"backend/app/infrastructure/persistence/demo_field_value_evidence_seeder.py"`, `"backend/app/tests/test_field_value_evidence_persistence.py"`, `"backend/app/tests/test_field_value_evidence_persistence_postgres.py"`, `"backend/app/tests/test_demo_field_value_evidence_seeder.py"`, `"backend/app/tests/test_demo_field_value_evidence_seeder_postgres.py"`, `"backend/app/tests/test_decision_engine.py"`, `"backend/app/tests/test_governance_engine.py"`, `"backend/app/tests/test_knowledge_engine.py"`, `"backend/app/tests/test_persistence_integration.py"`. | No other entry added, removed, or altered. No change to the subset-comparison logic itself. No wildcard, no directory-level entry. | Direct test execution. |
| `backend/app/tests/test_decision_engine.py` | MODIFY | Mechanical migration-head consequence (§3 evidence above) | Update the single existing assertion `assert revision == "0015_source_field_semantic"` → `"0016_field_value_evidence"`. No other line changed. | No change to `trigger_count == 1` or any other assertion in the file. | Direct test execution (Postgres). |
| `backend/app/tests/test_governance_engine.py` | MODIFY | Mechanical migration-head consequence | Update the single existing revision assertion identically. No other line changed. | Same as above. | Direct test execution (Postgres). |
| `backend/app/tests/test_knowledge_engine.py` | MODIFY | Mechanical migration-head consequence | Update the single existing revision assertion identically. No other line changed. | Same as above. | Direct test execution (Postgres). |
| `backend/app/tests/test_persistence_integration.py` | MODIFY | Mechanical migration-head consequence | Update the revision assertion identically, and `table_count == 59` → `table_count == 60`. No other line changed. | No change to `test_repository_crud` or any other test in the file. | Direct test execution (Postgres). |

No other repository path is authorized. In particular: `backend/app/domain/blueprint/*`, `backend/app/application/blueprint_conformance.py`,
`semantic_coverage_evaluation.py`, `gap_impact_remediation.py`, `semantic_mapping_resolution.py`,
`semantic_mapping_repository.py`, `source_field_repository.py` (existing, unmodified), any file under
`backend/app/integration/` (the Supplier-Risk contracts package, disambiguated from
`backend/app/domain/integration/` — CDD-022 §2, §16), `backend/app/api/*`, any frontend file,
`architecture/INDEX.md`, `architecture/released/*`, and any H4/Gate-N/Gate-P artifact are **not** authorized
for modification.

## 5. Protected artifacts / architecture firewall table

| Protected artifact/class | Why protected | Enforcement in this record |
|---|---|---|
| `SourceObservation` (`backend/app/integration/contracts.py`) | CDD-022 §2, §17 firewall — categorically different, wrong-shaped, already-FROZEN capability | Not in CREATE/MODIFY list; no import; no shared type |
| `backend/app/integration/` (top-level Supplier-Risk package) | Disambiguation firewall (CDD-022 §2, §16) — different package from `backend/app/domain/integration/` | Not in CREATE/MODIFY list; no import |
| `Blueprint`/`ConceptRequirement`/`RelationshipRequirement`/`InformationElementRequirement` (CDD-017) | Blueprint/semantic firewall (CDD-022 §18) | Not in CREATE/MODIFY list; no import anywhere in the authorized artifacts |
| `SemanticMapping`/`semantic_mapping_resolution.py` (H2) | H2 firewall (CDD-022 §18, §20) | Not in CREATE/MODIFY list; no import |
| `semantic_coverage_evaluation.py` (Gate I) / `gap_impact_remediation.py` (Gate J) | Firewall (CDD-022 §18) | Not in CREATE/MODIFY list; no import |
| `source_field.py`, `source_object.py`, `source_system.py` (domain, CDD-019) | `FieldValueEvidence` is a new sibling, never a modification | Not in MODIFY list |
| `source_field_repository.py`, `source_object_repository.py`, `source_system_repository.py` (existing) | Reused by call (FK join) only, never modified | Not in MODIFY list |
| `architecture/INDEX.md` | Already published for CDD-022 (governance publication, prior phase) — implementation must not touch it | Not in CREATE/MODIFY list |
| Any ORM lifecycle/governance-status ENUM (`lifecyclestate_t`/`governancestatus_t`) | CDD-022 §14 — no lifecycle/governance vocabulary on `field_value_evidence` | Not referenced by the migration row above |

## 6. Domain contract implementation boundary (binding, CDD-022 §6)

Exactly the seven fields in §4 row 1 above, no more, no fewer. `field_value_evidence_id`'s own primary-key
uniqueness (enforced by the migration, §4 row 4) is the *sole* uniqueness constraint authorized — no
compound constraint over `(source_field_id, source_record_reference)` under any circumstance (CDD-022 §6).

## 7. Deterministic identity implementation boundary (binding, CDD-022 §6, §25 — amended by Product Owner
   Decision, this turn, superseding the naive-concatenation form originally drafted here)

**Ownership**: identity derivation and verification are **domain-owned**, exclusively inside
`backend/app/domain/integration/field_value_evidence.py` (§4 row 1) — never in the repository, the seeder,
the ORM, or the migration. No second implementation of this algorithm is authorized anywhere in the
artifact set (§13).

**Canonical encoding (binding)**: each of the four semantic identity components is encoded as a
length-prefixed, self-delimiting segment — `<UTF-8 byte length of the component>:<the component's own raw
UTF-8 bytes>` — computed via `len(value.encode("utf-8"))`, **byte length, never Python character count**
(distinct for any text containing multi-byte UTF-8 characters). The four components are canonicalized as:
`source_field_id` via its own canonical string form (`str(uuid_value)`, unmodified); `source_record_reference`
and `observed_representation` as their exact raw strings — no trimming, case change, escaping, whitespace
normalization, or parsing of any kind; `observed_at` via `observed_at.astimezone(UTC).isoformat()` (the
existing trusted-timestamp serialization precedent, §3) — **binding consequence, made explicit**: two
timezone-aware `observed_at` values representing the identical instant under different UTC offsets
normalize to the identical canonical string and therefore the identical `field_value_evidence_id`, since
`astimezone(UTC)` compares equal instants regardless of the offset they were originally expressed in. A
fixed algorithm-version marker,
`_IDENTITY_ALGORITHM_VERSION = "FIELD_VALUE_EVIDENCE_IDENTITY_V1"`, is itself the first length-prefixed
segment — it is **not** a `FieldValueEvidence` field, not persisted, not lifecycle/version metadata; it
exists solely to make the algorithm explicit and versioned. `received_at` and `evidence_reference` MUST
NOT appear anywhere in this material under any circumstance.

**Collision safety**: because every segment's byte length is declared immediately before its own content,
the concatenated material is uniquely decodable — no combination of delimiter characters occurring *inside*
any raw component (e.g., a literal `:`) can shift a component boundary, because boundaries are determined
by the declared byte counts, not by scanning for delimiter characters. This is the standard self-delimiting
(length-prefixed / netstring-style) encoding technique, and it is provably free of the exact collision class
found during review (`source_record_reference = "100045:extra"` + `observed_representation = "Acme Taiwan
Ltd"` vs. `source_record_reference = "100045"` + `observed_representation = "extra:Acme Taiwan Ltd"` — these
now produce different byte sequences: `"12:100045:extra16:Acme Taiwan Ltd..."` vs.
`"6:10004521:extra:Acme Taiwan Ltd..."`, unambiguously distinct).

**Derivation**: `field_value_evidence_id = uuid5(BOOTSTRAP_SEED_NAMESPACE, canonical_material)`, reusing
the existing, already-governed `BOOTSTRAP_SEED_NAMESPACE` (§3 precedent) — no new namespace introduced.

**Verification (binding, new this turn)**: `FieldValueEvidence.__post_init__` re-derives this formula from
the instance's own `source_field_id`/`source_record_reference`/`observed_representation`/`observed_at` on
**every** construction — both fresh construction via `.new()` and rehydration via the raw constructor (used
by the repository when loading a persisted row) — and raises `ValidationException` if the supplied
`field_value_evidence_id` does not match. A caller cannot establish a semantically-duplicate fact under an
arbitrary, non-derived ID; a corrupted or tampered persisted row fails explicitly on rehydration rather than
silently constructing an inconsistent domain object.

Changing `_IDENTITY_ALGORITHM_VERSION` in any future revision requires new governance (CDD-022 amendment or
successor) — it is not an implementation-level free variable.

## 8. Persistence/migration boundary (binding, CDD-022 §15)

Exactly the table, columns, FK, and indexes in §4 rows 2 and 4. No `tenant_id` column. No update or delete
capability on the repository (§4 row 3).

## 9. Tenant-isolation boundary (binding, CDD-022 §7)

Enforced exclusively inside `FieldValueEvidenceRepositoryImpl.get_by_source_field`, by joining
`field_value_evidence.source_field_id` → `source_fields.source_object_id` → `source_objects.tenant_id` and
comparing against the caller-supplied `tenant_id` — raising `ValidationException` (distinct message per
§4 row 3) on mismatch or absence, never returning an empty result silently.

## 10. Replay/idempotency boundary (binding, CDD-022 §25 — amended by Product Owner Decision, this turn)

Owned by `FieldValueEvidenceRepositoryImpl.create_or_get_existing` (§4 row 3), not the seeder. Exactly
three cases, all binding:

1. **First create** — no row exists under the (domain-derived) `field_value_evidence_id` → persist the
   supplied fact, return it unchanged.
2. **Identical replay** — a row already exists under that ID, and its own four semantic-identity fields
   match the supplied fact's → return the **existing, already-persisted** fact; no write occurs; the
   supplied fact's own `received_at`/`evidence_reference` are discarded, never persisted; the original
   `received_at` is preserved exactly.
3. **Identity conflict** — a row already exists under that ID, but its own four semantic-identity fields do
   not match the supplied fact's (only reachable via persisted-data corruption, since identity is
   domain-derived and domain-verified on every construction, §7) — raise `ValidationException` explicitly;
   never overwrite, never mutate, never return either fact as if it were an accepted replay.

The seeder (§4 row 5) calls this one repository operation exactly once per fact and contains no
identity-derivation or collision-handling logic of its own.

## 11. Deterministic fixture boundary (binding, CDD-022 §20, §21)

Exactly the one fact specified in §4 row 5, against the existing, unmodified H3 identity. No second tenant,
no second fact, no production admission path.

## 12. Acceptance criteria

1. `FieldValueEvidence` construction succeeds for a non-empty `observed_representation` and separately for
   `observed_representation = ""`, proven by unit test.
2. `observed_representation = None`, naive `observed_at`, and naive `received_at` each raise
   `ValidationException` explicitly, proven by unit test.
3. `field_value_evidence_id` is deterministic: identical `(source_field_id, source_record_reference,
   observed_representation, observed_at)` yields the identical ID on repeated computation, proven both by
   unit test (`.new()` called twice) and against real PostgreSQL by re-running
   `DemoFieldValueEvidenceSeeder.seed()` twice and asserting an identical summary with no second row
   created.
4. The length-prefixed canonical encoding is collision-safe: the delimiter-shift counter-example found
   during review, and a second independent counter-example, each produce different IDs, proven by unit
   test (CDD-022 §6, §7 of this amendment).
5. A `field_value_evidence_id` supplied inconsistently with its own semantic identity inputs — whether via
   direct domain construction or via a corrupted persisted row — is rejected explicitly
   (`ValidationException`), never silently accepted, proven by unit test and by a Postgres conflict test
   (§7, §10 of this amendment).
6. The original `received_at` survives replay unchanged, and a differing `evidence_reference` on replay
   neither mutates the existing fact nor creates a second one, proven against real PostgreSQL via
   `create_or_get_existing`.
7. Two facts differing only in `observed_representation`, or only in `observed_at`, coexist as separate
   rows without conflict, proven against real PostgreSQL.
8. The correct tenant retrieves seeded evidence; a different tenant's retrieval raises `ValidationException`
   explicitly, proven against real PostgreSQL.
9. `evidence_reference` persists as `NULL` when omitted, proven against real PostgreSQL.
10. `SourceObservation`, `Blueprint`, `SemanticMapping`, H2, Gate I, and Gate J are never imported by any
    artifact in this report — proven by module import-hygiene inspection (matching every prior companion's
    identical import-hygiene test precedent).
11. `test_changed_files_match_cdd_010_and_cdd_012_exhaustive_allowlists` passes with the exact 13-path
    `AUTHORIZED_CHANGED_PATHS` extension in §4, and zero unauthorized diff.
12. `alembic upgrade head` / `alembic downgrade` round-trips cleanly against real PostgreSQL for
    `0016_field_value_evidence`, and the four mechanical migration-head assertions (§4) pass at the new
    revision/table-count.

## 13. Implementation stop conditions (binding)

Implementation MUST NOT expand beyond the fourteen artifact paths authorized above (nine CREATE, five
MODIFY) without new Product Owner authorization. If implementation discovers that any authorized artifact's
Exclusions column cannot be satisfied without touching an unlisted path (in particular: any file under
`backend/app/integration/`, `backend/app/api/*`, any Blueprint/H2/Gate-I/Gate-J/H4 artifact, or
`architecture/INDEX.md`), implementation MUST STOP and report the exact blocker rather than silently
expanding scope. If canonicalizing `source_field_id`/`observed_at` for identity derivation is found to
require any behavior beyond §7's exact formula, implementation MUST STOP and return that as a Product Owner
decision rather than inventing a variant. All identity-derivation and identity-verification logic MUST live
inside `backend/app/domain/integration/field_value_evidence.py` alone (§7) — if implementation finds this
genuinely impossible without a second file, implementation MUST STOP and report the exact reason rather
than silently adding one (reassessed and confirmed unnecessary as of this amendment, §3, §7). Changing
`_IDENTITY_ALGORITHM_VERSION` is never an implementation-level choice under any circumstance (§7).

## 14. Migration rollback expectations

`downgrade()` drops the three indexes and the `field_value_evidence` table, in the reverse order of
creation, mirroring `0015_source_field_semantic_mapping.py`'s exact `downgrade()` structure. No data
migration, no backfill, no dependency on any other table's rollback.

## 15. Publication/approval state

This document is an **approved artifact-authorization companion**, published to `APPROVED ARTIFACT
AUTHORIZATION` state following the identical Product Owner review-and-approval cycle every prior companion
(CDD-017 G2/G3/G3.5, CDD-018 G4, CDD-019 H1/H2/H3, CDD-020 I1, CDD-021 J1/J2) underwent — discovery (§3), a
content review that found and resolved two P1s (§1), and Product Owner approval. Approval of this record
governs exactly the artifact sandbox in §4 above; it does **not** itself authorize implementation of any
artifact listed there — a separate, subsequent Product Owner implementation authorization remains required
before any file listed above is created or modified.
