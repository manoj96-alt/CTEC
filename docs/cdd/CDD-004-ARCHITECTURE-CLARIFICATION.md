# CDD-004 Architecture Clarification Report

Status: Resolved by ERM-001 v2.1  
Work order: CDD-004 Enterprise Entity Resolution Engine v5.0  
Authoritative business capability: ERM-001 v2.0 (Frozen)

## Stop decision

Implementation is stopped before code or schema changes. The frozen business specification contains unresolved semantics that engineering cannot choose without redefining the Enterprise Entity Resolution Record.

## Resolution

ERM-001 v2.1 resolves all three clarifications and explicitly authorizes CDD-004 to resume after that revision is committed and frozen:

- Resolution history is maintained outside the immutable Resolution Record; no existing record field is updated for archival or supersession.
- A Resolution Record represents one enterprise understanding and may reference one or more supporting Source Objects; only one active record exists for that enterprise understanding.
- Business Confidence is independent of Resolution Outcome; all High, Medium, and Low classifications are valid for every outcome.

## Clarification 1 — Immutability versus archival transition

ERM-001 v2.0 requires all of the following:

- CP-003: Resolution records are immutable and never updated or deleted.
- CP-004: Historical records are archived.
- Human Override: a new record is produced while the previous active record is archived.
- The record specification includes `Record Status` (`Active` or `Archived`).
- The record specification includes `Superseded By`, an optional reference to a newer record.

An initially active record cannot later acquire `Archived` status or a `Superseded By` reference without updating that record. Moving those values into a separate mutable projection is technically possible, but deciding that the projection is outside the business record would define business-artifact semantics that ERM-001 does not currently authorize engineering to define.

### Required architecture decision

Choose one authoritative rule:

1. **Immutable payload with mutable lifecycle metadata** — explicitly state that `Record Status` and `Superseded By` are lifecycle metadata permitted to change while all other record content remains immutable.
2. **Fully append-only record** — replace mutable status/supersession attributes with a separate, explicitly authorized append-only lifecycle or supersession artifact/projection and define how current state is derived.
3. **Immutable record versions** — authorize creation of a replacement record version representing the archived predecessor, and define identity/version semantics.

## Clarification 2 — Active-record cardinality with multiple supporting Source Objects

ERM-001 v2.0 requires:

- one active Enterprise Entity Resolution Record per Source Object;
- only evaluated Source Objects as supporting evidence; and
- `Supporting Source Objects` as a plural collection on one record.

The specification does not identify a distinct initiating or subject Source Object. Therefore, when one record contains multiple supporting Source Objects, it is unclear whether that record:

- is the active record for every supporting Source Object;
- is active for one primary Source Object, with the others serving only as evidence; or
- belongs to another resolution scope not represented by the current attributes.

### Required architecture decision

Define the record's cardinality and active-slot rule:

1. **One subject Source Object per record** — authorize a subject/primary Source Object reference distinct from supporting evidence.
2. **One record governs every supporting Source Object** — state that the active uniqueness constraint applies to every Source Object in the supporting collection.
3. **Another governed resolution scope** — name and authorize that scope in ERM-001.

## Clarification 3 — Unresolved outcome confidence

ERM-001 requires every record to carry Business Confidence (`High`, `Medium`, or `Low`) and permits an `Unresolved` outcome. It does not explicitly state whether every unresolved record must use `Low`, or whether `High`/`Medium` confidence may describe confidence in the unresolved conclusion.

Engineering thresholds can be configured, but the allowed relationship between the business outcome and business confidence classification is business semantics.

### Required architecture decision

Define the permitted Outcome × Business Confidence combinations, or state that all nine combinations are valid.

## Non-blocking engineering choices after clarification

Once the business rules above are frozen, engineering can independently select:

- schema layout, indexes, ORM mappings, and repository interfaces;
- internal numeric scoring and threshold configuration;
- normalization and alias-provider implementation;
- API and DTO shapes;
- dependency injection, logging, and caching; and
- deterministic transaction and concurrency controls.

## Architecture drift check

- No new business entity introduced.
- No existing entity modified.
- No relationship changed.
- No canonical attribute invented.
- No RFC violated.
- No architecture layer bypassed.
- No technology introduced.
- No code, migration, canonical model, EAD, or ERM artifact modified.

## Resume condition

CDD-004 implementation may resume only after the three required business decisions are resolved in ERM-001 (or by an architecture artifact with authority to clarify ERM-001) and frozen.
