# Architecture Clarification Report — Experience Backend Phase 1

Status: **BLOCKED — clarification required before implementation**  
Scope reviewed: CTEC Alpha Phase 1 Experience Backend work order  
Runtime changes made: **None**

## Executive finding

The requested product journey is not implementable without inventing business semantics or bypassing frozen cognitive-capability contracts.

The work order correctly defines the Experience Backend as a consumer of the Cognitive Engine. However, it does not define the governed inputs required to transform uploaded source content into Entity Resolution, Semantic Resolution, Assertion, Knowledge, Decision, and Governance evaluations. Existing cognitive services cannot derive those inputs merely from a file and question without matching policy, semantic interpretation, assertion construction, acceptance evidence, decision policy, and governance policy decisions.

The instruction to stop on business ambiguity therefore applies.

## Blocking clarifications

### ACR-EB-001 — “Enterprise Ontology is built” conflicts with the frozen boundary

The journey states that CTEC imports files and then the “Enterprise Ontology is built.” The same work order says the Experience Backend shall not create ontology, while RFC-010 freezes the Canonical Enterprise Ontology before cognitive execution.

**Required decision:** Confirm that upload creates only Source Objects and that `/ontology` exposes the already-frozen ontology plus references to existing cognitive records. It must not create canonical entities, attributes, relationships, Entity Types, Relationship Types, or Institutional Concepts.

### ACR-EB-002 — File-to-Source-Object mapping is unspecified

The unit of import is undefined:

- one Source Object per file, CSV row, worksheet row, JSON document/node, or PDF page/block;
- how a Source System is selected or supplied;
- which frozen Source Object attributes receive filename, media type, location, row/page position, checksum, and raw content;
- whether raw binary files are retained and, if so, where;
- duplicate-upload and re-upload identity rules.

Choosing any of these rules would define externally visible provenance semantics.

**Required decision:** Provide a frozen Import Mapping Contract defining Source Object granularity, Source System selection, provenance mapping, raw-file retention, deterministic identity, duplicate handling, and transaction behavior for CSV, XLSX, JSON, and PDF.

### ACR-EB-003 — Cognitive pipeline inputs cannot be inferred from uploaded content

The frozen capabilities require governed inputs that the work order does not provide:

- Entity Resolution requires candidate identity evidence and resolution-policy inputs.
- Semantic Resolution requires candidate Institutional Concepts, Context, and supporting resolution/source references.
- Assertion requires a subject, predicate, object, Context, and prior resolution evidence.
- Knowledge requires an Assertion and outcome-appropriate Acceptance Evidence or rejection explanation.
- Decision requires Institutional Knowledge, a recommendation, policy satisfaction, explanation, and confidence inputs.
- Governance requires a governed record, governing policy evaluation, and GEM-001 authorization for Exception Granted.

The Experience Backend is prohibited from inventing these values, and the work order expressly excludes AI reasoning.

**Required decision:** Define an authoritative Pipeline Input Contract or a governed deterministic demonstration fixture that supplies every required input to each existing capability without deriving new business meaning in the Experience layer.

### ACR-EB-004 — Supported-question mappings are incomplete

The six supported phrases are listed, but their structured request contracts are not defined. In particular:

- how “Supplier ABC” resolves to a Source Object or Enterprise Entity;
- whether question matching is exact, case-insensitive, parameterized, or synonym-aware;
- which current record and policy scope each question targets;
- what “everything” includes;
- what “High Risk” means and which existing Assertion or Institutional Knowledge expresses it;
- what “rejected” refers to: Resolution, Assertion, Knowledge, Decision, or Governance outcome.

**Required decision:** Provide a versioned question-routing matrix mapping every supported question form to required parameters, target capability/read model, result fields, and no-match/ambiguous-match behavior.

### ACR-EB-005 — Supplier onboarding meaning is undefined

“Can I onboard Supplier ABC?” requires a business policy, an Enterprise Decision recommendation, and a Governance evaluation. No authoritative specification defines onboarding eligibility, the relevant Institutional Knowledge set, the governing policy, or how outcomes become a user-facing yes/no answer.

**Required decision:** Supply a governed onboarding demonstration policy and its exact mappings to existing Knowledge, Decision, and Governance inputs. The Experience Backend must only present the resulting records; it cannot define onboarding policy.

### ACR-EB-006 — Answer composition rules are unspecified

The response must contain Business Answer, Confidence, Explanation, Evidence, Governance, Current Records, and References, but the work order does not define:

- which capability owns the displayed confidence when several records have confidence;
- how conflicting or missing current records are represented;
- whether Business Answer is a projection of Decision Outcome, Governance Outcome, or both;
- how Evidence is traced without duplicating provenance;
- whether historical or future-effective records may participate.

**Required decision:** Define the response composition matrix and precedence rules. RFC-011 must govern currentness independently for each record identity.

### ACR-EB-007 — Read boundary between Experience Backend and Cognitive Engine is undefined

CDD-009 prohibits an external Governance query capability while allowing internal repository reads for history, currentness, and traceability. The new work order authorizes Experience endpoints such as `/history/{id}` and `/governance/{id}`, but no published Cognitive Engine consumer interface exists for all requested reads.

Direct access from Experience services to Cognitive Engine ORM models or repositories would bypass the application boundary established in `AGENTS.md`.

**Required decision:** Authorize and define a read-only Cognitive Engine consumer port for currentness, history, traceability, ontology, and graph projections, or explicitly authorize a narrowly scoped adapter. The Experience Backend should depend on that port, not persistence internals.

### ACR-EB-008 — Pipeline transaction and failure semantics are missing

The work order does not specify whether the six-stage pipeline is atomic, resumable, or append-as-completed; how retries avoid duplicate immutable records; or how partial failure is returned.

**Required decision:** Define correlation identity, idempotency, stage status, transaction boundaries, retry behavior, and partial-failure behavior without introducing mutable lifecycle state into RFC-011 records.

### ACR-EB-009 — Parser dependency authority is incomplete

Python is authorized, but no approved libraries are named for XLSX and PDF parsing. Implementing those formats requires additional packages beyond the current runtime dependencies.

**Required decision:** Confirm permitted parser libraries within TAS-001—for example, an approved XLSX reader and PDF text extractor—and define whether scanned/image-only PDFs are unsupported because OCR is not authorized.

### ACR-EB-010 — Sample-data phase and deliverable conflict

The repository structure labels `sample-data/` as Phase 3, while the Phase 1 deliverables require Sample Data and the final objective requires `Supplier.csv`.

**Required decision:** Confirm whether Phase 1 may add a minimal deterministic `Supplier.csv` fixture or must reuse EDT-001 v3 without modification.

## Recommended minimum clarification package

Implementation can begin without changing the Canonical Enterprise Ontology if architecture supplies these four governed contracts:

1. **Import Mapping Contract** — file granularity, provenance, identity, storage, and Source System rules.
2. **Pipeline Input Contract** — complete authorized inputs for ERM through GRM, including demonstration policies and evidence.
3. **Question Routing and Answer Composition Contract** — exact supported intents, parameters, response precedence, and ambiguity behavior.
4. **Cognitive Engine Consumer Port** — application-level commands and read projections available to product-experience consumers.

Parser-library approval and Phase 1 sample-data scope should be recorded alongside those contracts.

## Architecture drift check

- No new business entity introduced: **PASS**
- No existing entity modified: **PASS**
- No relationship changed: **PASS**
- No attribute invented: **PASS**
- No RFC violated: **PASS**
- No architecture layer bypassed: **PASS**
- No technology outside TAS-001 introduced: **PASS**
- No Cognitive Engine implementation modified: **PASS**

These checks pass because implementation stopped before code, persistence, dependencies, APIs, or runtime configuration were changed.
