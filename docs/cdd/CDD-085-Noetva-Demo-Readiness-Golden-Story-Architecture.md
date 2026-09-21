# CDD-085 — Noetva Demo Readiness: Golden Story Architecture

Version: 1.0 FROZEN
Status: FROZEN (architecture — implementation authorized only via the companion Artifact Authorization)
Implementation state: NOT STARTED
Precedent phase: `NOETVA-DEMO-READINESS-DR` (same program), concluding `COMPLETE — GOLDEN DEMO STORY +
FORWARD-ONLY SCREEN JOURNEY RESOLVED — READY FOR DEMO-READINESS-G`. This document resolves DR's open
decisions and freezes them as binding architecture. It does not reopen DR's own discovery — every fact DR
established about the live product (menu inventory, seed data, API surface, the live remediation loop, the
Integrity 404, the Ask CTEC failure) is treated here as given, re-cited only where a decision depends on it.

**Publication note**: this document freezes the *Golden Demo story and connected-data architecture*. It
authorizes no implementation directly; implementation is authorized only through this document's companion
Artifact Authorization (`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture-Artifact-Authorization.md`),
mirroring every prior CDD/AA pairing in this repository exactly.

## 1. Authoritative baseline

```
HEAD (this worktree):  75d11b460240147c35d4d91023ee4a47a6dbea9a  (= origin/main, fresh worktree)
origin/main:           75d11b460240147c35d4d91023ee4a47a6dbea9a  (unchanged since H6 closure)
GitHub main:           75d11b460240147c35d4d91023ee4a47a6dbea9a  (independently cross-checked)
Governance branch:     product/noetva-demo-readiness-g (new, from origin/main, clean worktree)
Highest existing CDD:  CDD-084 (+ its G-R1 amendment)  →  this document is CDD-085
```

No origin/main movement occurred between DR and this phase. This is a pure product-storytelling /
demo-readiness phase, not another OQI capability — it consumes H1-H6 exactly as frozen and modifies none of
their governance.

## 2. Mission (binding, restated)

Freeze the smallest legitimate set of product changes that turn the existing, real Noetva application into
one coherent, forward-moving, truthful Golden Demo. This is **not** a new demo application, **not** a
parallel architecture, and **not** a product redesign. It is the minimum seed-data, one contextual
navigation link, and two small copy/placeholder corrections needed to make the real product tell one
story.

## 3. Golden Story — frozen

**Business framing**: a global electronics company is ten days from launching **Aurora X1**. Maya, Director
of Supply Chain Intelligence, is asked by leadership: *"Are we ready to launch?"* A launch-critical supplier
is represented inconsistently across enterprise systems (SAP vs. PLM disagree on Country of Origin). The
problem is not one bad field — it is that neither Maya nor her company's AI has one defensible, governed
understanding of enterprise reality.

**Protagonist**: Maya, Director of Supply Chain Intelligence — revalidated from DR, no change. She plausibly
owns exactly the decision the live product's real remediation-authorization flow requires (`UPDATE_FIELD`,
governed-reference-evidence-based).

**Governed investigation subject**: the real, live `EnterpriseEntity` DR found (currently displayed as
"Demo Supplier (OQI Showcase)"), renamed per §5 below. Aurora X1 is the *business-stakes frame*, never the
literal investigated entity, per DR's own proven boundary (§6 of the governing prompt; no `Aurora`, `Battery
Pack`, `Battery Cell`, or `Shipment` entity type exists, and none is authorized to be invented).

## 4. Presenter framing vs. governed product fact (binding distinction)

Every spoken line in the Story Contract (§13 of this document, and the companion final report) is classified
as exactly one of:

```
LIVE PRODUCT FACT       — a real, persisted, queryable value (a Finding, an evidence value, a Reliance
                            state, an authorization record).
SEEDED DEMO FACT         — a real, persisted value this document's own Artifact Authorization creates
                            (the Golden Supplier's name, the Aurora X1 Product, the ontology edges).
PRESENTER BUSINESS FRAMING — spoken narrative color with no corresponding database row (e.g. "ten days
                            before launch," "leadership is asking").
FUTURE CAPABILITY        — explicitly named as not yet live (Agent Investigation's honest empty state,
                            Gate F's deferred status).
```

No screen, script, or test may blur these categories. "Ten days before launch" is PRESENTER BUSINESS
FRAMING and must never be rendered as if it were a persisted system fact, because it is not seeded anywhere
and this document does not authorize seeding a launch-date field.

## 5. Golden Supplier identity — frozen

```
Old (developer-facing):  "Demo Supplier (OQI Showcase)"
New (frozen):            "Meridian Cell Components"
```

A professional, pronounceable, fictional name; avoids `Demo`/`Test`/`Widget`/`Showcase`/`Sample`/`Foo`/`Bar`
per the governing prompt's explicit list; avoids confusion with any real company. This is a **display-string
change only** — the entity's ID (`_SUPPLIER_ENTITY_ID`), all five of its existing OQI evaluations, its
`Reliance` mechanics, and its `entity_type_name` ("System Actor" — an existing, correct typing this document
does not alter) are structurally unchanged.

The business dependency display name is also frozen:

```
Old:  "Supplier Qualification (Demo)"
New:  "Aurora X1 Supplier Qualification"
```

Display-string change only — `Criticality.HIGH` and the dependency's structural role are unchanged.

## 6. Golden Product decision — frozen

**Aurora X1 is authorized as a real, minimal, seeded `Product`-type `EnterpriseEntity`.** `Product` is
already a governed, already-instantiated ontology concept (H4's own Structural Integrity demo scenario
already creates `Product`-type entities using this exact mechanism) — this is new *instance data* using an
existing entity type, not new architecture.

## 7. Golden ontology relationship — frozen

DR found the live Golden Supplier has **zero** ontology relationships, which structurally prevents any
propagated (as opposed to direct) ontology-impact visualization. Independently re-derived this phase: the
governed Supplier Risk ontology has no direct Supplier→Product relationship type — only a three-hop
governed chain: `supplies` (Supplier→Material), `usedIn` (Material→BOM), `defines` (BOM→Product). This
document authorizes exactly that three-hop chain, reusing three already-governed relationship types,
**adding two new entities** (one `Material`, one `BOM`) plus the already-authorized `Product` (§6):

```
Meridian Cell Components  --supplies-->  Aurora X1 Battery Cell (Material)
Aurora X1 Battery Cell    --usedIn-->    Aurora X1 Bill of Materials (BOM)
Aurora X1 Bill of Materials --defines--> Aurora X1 (Product)
```

Three edges, three new entities beyond the Supplier/Product already discussed — the minimum the *existing*
ontology's own modeling requires to truthfully connect a Supplier to a Product. No new relationship type,
no new entity type, no direct Supplier→Product shortcut is authorized (none exists in governance, and
inventing one would be exactly the "broad new ontology modeling" §6/§19 of the governing prompt forbids).

**Explicit, honest limitation (binding disclosure)**: this document does **not** claim, and implementation
must not claim, that seeding this relationship chain automatically makes OQI4's `propagated_path` become
non-null for the Golden Supplier's existing Consistency Finding. Whether OQI4's propagation algorithm
traverses `supplies`/`usedIn`/`defines` edges for an OQI1-3-family Finding is not verified by this governance
phase (DR observed `propagated_path: null` even for the *direct* entity impact of the currently-unconnected
Supplier, and propagation triggers for the H4/Structural-Integrity family are the only ones this program has
previously confirmed). Implementation/VM must verify this live and report the true result — direct impact
only, or genuinely propagated — never assume or fabricate propagation. Independent of that question, the
relationship chain is real and valuable on its own: it makes the Ontology Explorer graph and an Ask CTEC
"which products depend on Meridian Cell Components" query truthfully answerable, which they are not today.

## 8. H6 Uniqueness alignment — frozen

DR found H6's demo trio ("H6 Demo Duplicate Widget" / "H6 DEMO DUPLICATE WIDGET" / "H6 Demo Distinct
Gadget") uses `Product`-type entities structurally disconnected from the Golden Supplier story. Rather than
authorizing a *second*, parallel `UniquenessPolicy` scoped to the Supplier's own entity type (a larger,
less-minimal change), this document authorizes the smaller option: **reuse the existing Product-type H6
policy and its three existing entity slots verbatim, renaming only their display strings** to make the
*already-seeded* `Aurora X1` Product (§6) the canonical member of the Uniqueness pair:

```
H6 member A (canonical, = the SAME "Aurora X1" Product entity created in §7's relationship chain):
    "Aurora X1"
H6 member B (candidate duplicate — same canonical_name, different casing, exactly mirroring H6's own
    existing demo mechanism):
    "AURORA X1"
H6 distinct control (SATISFIED, unrelated canonical name):
    "Nimbus S2 Controller"
```

This requires **zero new `UniquenessPolicy` row** — the existing Product-type policy (`_H6_POLICY_ID`)
governs it unchanged. It requires renaming three display strings and reusing the exact same canonical-name
casing-variant mechanism already proven throughout H6's own crown. **Zero H6 semantic, blocking, adjudication,
or constraint behavior is touched** (§9 below).

## 9. H6 architecture preservation (binding, restated verbatim from CDD-084)

This document authorizes zero change to: `canonical_name` blocking; H6 candidate qualification; H6 database
constraints (five tables, nine tenant-qualified composite FKs, the `member_a_id < member_b_id` CHECK, the
closed `REJECT_NOT_DUPLICATE`/`CONFIRM_DUPLICATE` adjudication-action set); H6 Finding identity; H6's
zero-remediation-candidate dispatch; H6's no-auto-merge/no-deactivate guarantee. Demo Readiness *consumes*
H6 exactly as CDD-084 and its G-R1 amendment froze it — it does not reopen either document.

## 10. OQI dimension story — frozen

The primary demo spine demonstrates exactly the six dimensions that already, genuinely, converge on the
Golden Supplier and its now-connected Product: **Consistency** (SAP vs. PLM), **Accuracy** (governed
reference evidence), **Reasonableness** (implausible order quantity), **Conformity** (canonical-form
compliance), **Timeliness** (stale evidence), and **Uniqueness** (the Aurora X1 duplicate-candidate, §8).
Completeness/Validity/Integrity remain real, mentionable-for-breadth capabilities, never forced into the
primary spine.

## 11. Integrity 404 — frozen disposition

DR live-reproduced a real defect: `ORPHAN_REFERENCE`, `RELATIONSHIP_CARDINALITY_VIOLATION`, and
`MISSING_REQUIRED_RELATIONSHIP` findings list correctly but 404 on the generic Finding-detail route. This is
**not** a Demo Readiness task. This document authorizes zero fix to that route. Governance decision: track it
as a **separate, narrow engineering closure** (working name `NOETVA-INTEGRITY-FINDING-DETAIL-R1`, no CDD
number reserved here, per normal procedure) to be opened independently of this program. The Golden Demo's
own frozen route order (§13) never visits an Integrity Finding — this is enforced by construction, not by
hiding the defect. **No external-demo certification may be granted while this defect remains reproducible**,
per §25/§91 of the governing prompt, restated here as binding.

## 12. Ask CTEC — frozen disposition

DR live-reproduced the shipped example question ("Which products depend on TSMC?") failing
(`NO_MATCHING_ENTITY`) because no governed `TSMC` entity exists. Seeding a real `TSMC` entity would require
substantially building out the currently-inert EDT-001 dataset — explicitly out of this phase's minimal-change
scope. **Decision: Option B.** The placeholder question is authorized to change to **"Which products depend
on Meridian Cell Components?"** — a question the now-connected ontology (§7) can genuinely attempt to answer.
**Ask CTEC is classified EXTENDED DEMO ONLY (25-30 minute deep dive), not primary Golden Demo**, until
Implementation/VM live-confirms the corrected question returns a real, correct, non-empty answer (`Aurora
X1`). This document does not assume that result — see §7's own disclosed limitation.

## 13. Golden Demo Story Contract (frozen screen order)

Resolving the governing prompt's own explicit request (§10-§12) to correct DR's cognitive ordering while
eliminating harmful backtracking, this document freezes the following exact sequence. The key resolution:
DR's "quality tour first, identity/ontology after" order is corrected to visit **Identity and Ontology before
completing the Finding's own remaining tabs**, using the Finding-detail page's *already-existing* `?tab=`
URL-state mechanism (`frontend/app/quality/findings/[findingId]/page.tsx`'s own `setTab`, confirmed
unmodified in source this phase) to return via a **direct deep link**, not a re-click through already-seen
tabs. This is deliberately not counted as backtracking — the audience never re-sees content, never re-picks
the entity, and the finding_id is carried in the URL throughout, exactly as `EMPTY_STATE`/tab-URL precedent
already establishes elsewhere in this product.

```
1.  Overview                                     (/overview)                         — PROBLEM
2.  Finding Detail — Evidence tab                (/quality/findings/{id})            — EVIDENCE
3.  Entity Resolution                            (/data/entity-resolution)           — IDENTITY
4.  Ontology Explorer                            (/ontology/explorer)                — ONTOLOGY
5.  Finding Detail — Ontology Impact tab         (/quality/findings/{id}?tab=ontology-impact)  — deep link back, continuing the SAME investigation
6.  Finding Detail — Business Impact tab         (same route, tab switch)            — SO WHAT
7.  Finding Detail — Explainable Reliance tab    (same route, tab switch)            — TRUST/USE
8.  Finding Detail — Agent Investigation tab     (same route, tab switch)            — USE (honest empty state)
9.  Finding Detail — Remediation tab             (same route, tab switch)            — ACT / human authority / re-evaluation
10. Findings list, filtered to Uniqueness        (/quality/findings)                 — UNIQUENESS entry
11. Uniqueness Pair Detail                       (/quality/findings/{h6-id})         — CONFIRMATION ≠ RESOLUTION, no auto-merge
12. Overview (return)                            (/overview)                         — CLOSE, deliberate narrative callback
```

Step 5's "return" to `/quality/findings/{id}` is the one deliberate exception to zero-repeated-routes,
justified explicitly: it is a same-investigation continuation via direct tab deep-link, not a re-search, not
a re-navigation through intervening menus, and it is the minimum contextual-navigation change identified
after evaluating the alternative (leaving Identity/Ontology for later, which DR itself already tried and
which the governing prompt explicitly asked to be reconsidered). The Findings-list → Uniqueness-pair → final
Overview sequence at the end is new-forward movement, never a repeat.

## 14. Contextual navigation — the one authorized frontend link

To make step 2→3 (Evidence → Entity Resolution) and step 4→5 (Ontology Explorer → back to Finding Detail)
feel like continuous investigation rather than a menu hunt, this document authorizes **exactly one** new
contextual link: on the Finding Detail page's Evidence tab, a link reading "View resolved entity" pointing
to `/data/entity-resolution` (present only when the Finding's family is `OQI2`, the family that has a real,
non-empty resolution case). No other frontend navigation change is authorized. This is not a navigation
redesign — the primary menu (`site-shell.tsx`) is untouched.

## 15. Agent Investigation — frozen honest boundary (restated, no change needed)

Independently re-confirmed this phase, reading the current source: the existing copy already reads exactly
*"Live agent reasoning has not been invoked for this Finding,"* using the established `not-invoked` status
vocabulary (CDD-079 §10, CDD-081 §14) — already correct, already honest, already distinguishes "not invoked"
from "broken." **Zero change authorized or needed here.** `OqiRemediationAgentService.reason_about_case`
remains callable only from tests, confirmed unchanged this phase; no execution trigger of any kind is
authorized.

## 16. Remediation / human authority / re-evaluation — frozen (no change needed)

DR proved this live, end-to-end, against the real API: `prepare` → real candidate → `PENDING` authorization
→ named-human `APPROVE` → `report-execution` → Finding remains `OPEN` (state revision increments, evidence
unchanged). This is real, already-shipped production behavior. This document authorizes zero change to the
remediation, authorization, or re-evaluation architecture — it is the signature demo moment exactly as-is.

## 17. Gate F — frozen classification: DEFERRED

Per the governing prompt's own default preference and DR's finding that Gate F uses a wholly separate seeder
and entity universe (`demo_gate_f_seeder.py`, distinct supplier IDs): **Gate F is classified DEFERRED — not
authorized for this phase, in any duration (3-minute, 10-15-minute, or 25-30-minute).** Aligning it with the
Golden Supplier would require modifying a second, independently-scoped seeder this document has not
investigated deeply enough to safely authorize touching, and the governing prompt's own default is to keep
it out absent a "genuinely small and natural" alignment — which this phase did not find. No Gate F path is
authorized by the companion Artifact Authorization. This may be revisited as a future, separately-governed
phase.

## 18. Demo reset architecture — frozen

DR found demo actions durably mutate state (a real authorization/execution was created and never
automatically reverted). Independently confirmed this phase: the repository already has a `Makefile` with
`migrate`/`seed`/`reset-db` targets and a `backend/app/infrastructure/persistence/database_cli.py` CLI;
`reset_database()` performs `alembic downgrade base` → `upgrade head` against whatever `CTEC_DATABASE_URL`
is configured, with **no environment guard of any kind** — a real, pre-existing safety gap, not something
Demo Readiness introduces, but one this document must not build on unguarded.

This document authorizes an **additive** extension to the existing CLI/Makefile (never a parallel
mechanism):

```
database_cli.py demo-reset
    1. requires an explicit environment guard (both must hold, or the command STOPS with a clear error and
       makes zero database change):
       a. CTEC_DEMO_RESET_ALLOWED=true is set in the calling environment
       b. the resolved CTEC_DATABASE_URL host is one of an explicit local/demo allowlist
          (e.g. "localhost", "127.0.0.1", "postgres" — the Docker Compose service name) — never a
          bare "any URL the caller supplies" check
    2. calls the EXISTING reset_database() (downgrade base -> upgrade head) -- reused, not reimplemented
    3. re-runs the EXISTING OntologySeeder + BlueprintSeeder (the same two calls docker-entrypoint.sh
       already makes)
    4. runs the (now Golden-Story-updated) DemoOqiSeeder -- never the EDT-001 SeedLoader, which remains
       the separate, already-existing `make seed` target, untouched and unrelated to the Golden Demo

database_cli.py demo-verify
    reads back and asserts the exact deterministic contract in §19 below; exits non-zero with a clear
    message identifying exactly which assertion failed, on any mismatch.
```

Makefile gains two new targets, `demo-reset` and `demo-verify`, calling the above. No existing Makefile
target's behavior changes.

## 19. Deterministic Golden Demo state contract — frozen

After `demo-reset`, `demo-verify` must confirm exactly:

```
Golden Supplier "Meridian Cell Components" exists (System Actor type), tenant = BOOTSTRAP_DEMO_TENANT_ID
Country-of-Origin evidence: SAP = "US", PLM = "MX" (unchanged from current seeder)
OQI2 Consistency Finding: OPEN, family=OQI2
Business dependency "Aurora X1 Supplier Qualification": Criticality = HIGH
Reliance state for the Supplier: RELIANCE_AT_RISK
Zero pending remediation authorization exists for the OQI2 Finding (no contamination from a prior demo run)
Zero external-execution report exists for the OQI2 Finding
Ontology chain exists: Meridian Cell Components -supplies-> Aurora X1 Battery Cell -usedIn->
    Aurora X1 Bill of Materials -defines-> Aurora X1
"Aurora X1" Product entity exists
H6 Uniqueness candidate exists for the pair ("Aurora X1" / "AURORA X1"), Finding OPEN, zero adjudication
"Nimbus S2 Controller" exists, SATISFIED, no candidate
```

A prior demo session's remediation authorization/execution-report is exactly the kind of contamination
`demo-reset`'s full downgrade/upgrade (step 2 of §18) already clears — restated here as the reason a full
schema reset, not a mere re-seed, is required (a bare re-run of the idempotent `DemoOqiSeeder` alone would
leave prior authorization/execution rows in place, since those live in tables `DemoOqiSeeder` never touches).

## 20. Reset safety (binding, restated)

`demo-reset` must fail closed: absent both guard conditions in §18.1, it must refuse to run and must make
zero database change — never a partial downgrade. This is the same fail-closed discipline this entire
governed program has applied to every other destructive operation.

## 21. Visual/terminology contract — frozen

Authorized display-string changes only (§5, §8, §12); avoid `Demo`/`Test`/`Widget`/`Showcase`/`Sample` in
any Golden-Demo-visible string. No component redesign, no CSS/layout rework, no new design-system component.
Product name (`Noetva`) and category framing are unchanged (governing prompt §55) — not addressed further
here.

## 22. Trust principles mapped to real screens (restated, not a slogan page)

```
MAJORITY ≠ TRUTH / AUTHORITY ≠ TRUTH   — Evidence tab (SAP/PLM both preserved, neither privileged)
CANDIDATE ≠ TRUTH                       — Ontology Impact tab / Entity Resolution (resolved, not assumed)
AGENT ≠ FACT                            — Agent Investigation tab (honest empty state)
RECOMMENDATION ≠ AUTHORIZATION          — Remediation tab, candidate vs. authorization as separate steps
AUTHORIZATION ≠ REMEDIATION             — Remediation tab, authorization vs. execution-report as separate steps
REMEDIATION ≠ RESOLUTION                — Remediation tab, Finding stays OPEN after execution report (signature moment)
UNKNOWN ≠ LOW / NO FINDINGS ≠ TRUSTED   — Reliance tab (an explicit reason code, never a bare score)
DUPLICATE CANDIDATE ≠ DUPLICATE FACT    — Uniqueness Pair Detail
CONFIRMATION ≠ MERGE                    — Uniqueness Pair Detail (no merge/deactivate control exists)
```

## 23. Explicit non-goals (binding, restated for Demo Readiness)

New OQI dimensions; SourceRecord Uniqueness; strong-identifier blocking; fuzzy matching; entity merge or
consolidation; new agent-execution architecture; new remediation architecture; new Reliance states; new
ontology relationship types or entity types; global navigation redesign; new database schema or migration;
Gate F/OQI data-universe merger; new MCP execution capability; broad Intelligence-menu redesign; any change
to H1-H6 CDDs, H6's AA, or H6's G-R1 amendment.

## 24. STOP conditions (binding, exhaustive)

Implementation must STOP and return for renewed governance rather than improvise, if: a migration is found
genuinely necessary; any H6 semantic, blocking, or constraint behavior would need to change; the
`supplies`/`usedIn`/`defines` chain cannot be expressed through existing relationship-type/entity-type
primitives as frozen in §7; the Ontology-Impact→Entity-Resolution link (§14) requires touching any file
beyond the one named in the companion Artifact Authorization; Agent Investigation would need any execution
capability; tenancy, authentication, or database constraints would need to weaken in any way; the
`demo-reset` guard cannot be implemented as a true fail-closed check; any existing H1-H6 test would need to
weaken to pass.

## 25. Authorization

This CDD is approved and published as FROZEN. Implementation is authorized only against the exact path list,
schema, and test matrix frozen in the companion
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture-Artifact-Authorization.md`. This document itself
authorizes no code, seed-data, migration, test, or frontend change.
