# PAD-001 v1.5 — Product-Internal Deterministic Capability Boundary Clarification

Version: 1.0
Status: FROZEN
Current: YES
Authority: AUTHORITATIVE
Approval: Product Owner authorization, Gate D0/D1

## 0. Purpose

This clarification resolves the "Track 2" architecture blocker identified
during Priority 6 ("Ontology Copilot / Ask CTEC") discovery: whether a
synchronous, read-only, deterministic capability may be implemented as
ordinary Product-Layer logic, or whether it must be admitted as a PAC-002
"Question" through PAD-001's asynchronous Execution-Identifier/poll pattern.

Per `architecture/INDEX.md`'s Constitutional governance section and the
Architecture Glossary's EAH-001 entry: *"If two current artifacts at the same
authority level conflict, implementation must stop until architecture
governance issues a clarification."* This is that clarification, not a new
RFC or CDD — it defines no new canonical entity, attribute, relationship,
Protocol Version, or business semantics, and changes no existing one. It only
draws a boundary that PAD-001's own text leaves implicit.

## 1. Problem statement

PAD-001 v1.5 §1 states: *"All products built on CTEC SHALL communicate with
the Cognitive Engine exclusively through the Product Access Protocol. No
product SHALL access Cognitive Engine internals directly."* §10 (PAC-002,
"Question Protocol") is unconditionally asynchronous — *"PAC-002 is
asynchronous. Acceptance acknowledges protocol validation only. Execution
completion is retrieved using PAC-006 and the returned Execution
Identifier"* — with no read-only exception, and lists "Ontology Request" as
one of its five Request Categories.

Separately, PAD-001 §6 and §21-22 define the Cognitive Engine's
responsibilities exhaustively and by function: Source Object creation, Entity
Resolution, Semantic Resolution, Assertion, Knowledge, Decision, Governance,
business reasoning, confidence, explainability generation, history
generation, current-record determination, and Enterprise Ontology Projection
generation — i.e., ERM/SRM/ASM/KRM/DRM/GRM. RFC-010 §3 independently confirms
the identical taxonomy. CIM-001 v1.1 scopes that same chain to "Supplier-risk
/ single-source-versus-dual-source vertical slice only."

A capability that parses a user's natural-language question into a typed
traversal request, walks only already-persisted governed data, and composes a
templated answer from the result — performing no entity resolution, no
assertion, no knowledge institutionalization, no decision, and no governance
evaluation — does not perform any function PAD-001 §6/§21-22 assigns to the
Cognitive Engine. Read by function rather than by surface label ("a
question"), such a capability is Product-Layer-internal deterministic logic,
not a Cognitive Engine invocation, and PAD-001's Product Access Protocol —
which governs product-to-Cognitive-Engine communication — does not apply to
it. This clarification makes that reading explicit rather than leaving it to
be inferred inconsistently capability by capability.

**This clarification does not resolve, and does not attempt to resolve,
whether Gate C's Entity Resolution Steward API — which does perform what its
own name calls "Entity Resolution," one of PAD-001's six named Cognitive
Engine functions, synchronously and outside any Engine Access Facade or
EIC-001 admission — is compliant with PAD-001 §21. No document in this
repository has ever reviewed Gate C against PAD-001. That is a distinct,
pre-existing question this clarification does not extend to, and is flagged
separately rather than folded into this ruling.**

## 2. Additive authoritative language

1. A capability is Product-Layer-internal deterministic logic, not a Cognitive
   Engine invocation under PAD-001, when it satisfies all of the following:
   deterministic; read-only; consumes only the frozen Canonical Enterprise
   Ontology and/or already-persisted governed instance data; invokes none of
   ERM, SRM, ASM, KRM, DRM, or GRM; performs no enterprise business decision;
   creates no assertion, knowledge, decision, or governance record; uses no
   LLM or other non-deterministic inference; and performs no mutation of any
   ontology or business record.
2. Such a capability is not a PAC-002 "Question" and is not subject to
   PAC-002's asynchronous Execution-Identifier/poll requirement, regardless of
   whether its user-facing surface is phrased as a question.
3. Such a capability remains subject to every other applicable governance
   boundary: it must not access Cognitive Engine internals or persistence
   reserved to a capability engine (PAD-001 §21), must respect tenant
   ownership boundaries for any instance data it reads (RFC-015 and its
   successors), and must not introduce, modify, or supersede any canonical
   entity, attribute, or relationship (RFC-010 §10).
4. This clarification authorizes no specific capability. A capability must
   still independently demonstrate, at implementation time, that it in fact
   satisfies every characteristic in item 1 — this is a boundary definition,
   not a blanket exemption.
5. If a future capability's read-only exploration surface begins to perform
   any function reserved to the Cognitive Engine under PAD-001 §6/§21-22 (for
   example, synthesizing a business recommendation rather than reporting a
   governed fact), it falls outside this clarification and requires PAC-002
   admission or further governance review at that time.

## 3. Supported behavior at this release

No new PAC-00x protocol category is created. PAC-002's asynchronous
requirement for genuine Cognitive Engine Questions is unchanged. No existing
Protocol Version, default, or capability's governance status changes. This
clarification only states which capabilities are, and are not, within
PAD-001's Cognitive Engine boundary in the first place. This publication does
not authorize an LLM.

## 4. Traceability

PAD-001 v1.5; CIM-001 v1.1 (scope: supplier-risk / single-source-versus-dual-source
vertical slice only); RFC-010 v1.0 §3, §10; RFC-015 v1.0; RFC-016 v1.0; EAH-001
v1.5; Architecture Glossary v1.2 (`architecture/released/v1.2/ARCHITECTURE-GLOSSARY-v1.2_FROZEN.md`,
line 19: same-authority-level-conflict clarification rule).

## 5. Authorization

Authorized by CTEC Product Owner Manoj Nair on 2026-08-15: the boundary
definition in §2, and the explicit non-extension to Gate C noted in §1, were
approved (Gate D0). Gate D1 completes registry publication: this document's
FROZEN status and the atomic `architecture/INDEX.md` update land together in
this baseline.
