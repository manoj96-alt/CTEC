# CDD-085 — Artifact Authorization G-R1 Entity Resolution Flush-Ordering Amendment (NOETVA-DEMO-READINESS-G-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-084-Artifact-Authorization-H6-G-R1-Frontend-Test-Path-And-U19-Correction-Amendment.md` (the
direct precedent for this exact governance shape: an implementation phase correctly SIGNALS a genuine need
outside its own Artifact Authorization's path ceiling by stopping before writing, closed by a narrow,
standalone, additive amendment); `CDD-050-Artifact-Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md`
(further precedent for the same defect class: a real, adversarially-reproduced runtime defect closed by the
narrowest correct application-layer fix, with the database constraint left untouched and fully credited)
Classification: PRE-EXISTING CORRECTNESS DEFECT (flush-ordering hazard in `EntityResolutionStore.append()`,
introduced 2026-08-06, dormant until exposed by the Golden Demo's new deterministic reset/reseed lifecycle) +
PATH-AUTHORIZATION GAP (the one file containing the correct fix is outside CDD-085 AA's original 7-path
ceiling)
Governs: `product/noetva-demo-readiness-i` worktree, STOPPED before any commit (no candidate commit exists;
governs the preserved, uncommitted working-tree state described in §2)

## 1. Purpose

Authorizes the exact, narrow, additive correction of the one governance-compliance gap
NOETVA-DEMO-READINESS-I independently found and correctly stopped in front of, reported as:

```
NOETVA-DEMO-READINESS-I: STOPPED — GOVERNANCE AMENDMENT REQUIRED —
demo-reset (CDD-085 §18) deterministically fails with a ForeignKeyViolation on
enterprise_entity_resolution_history because EntityResolutionStore.append()
(backend/app/infrastructure/persistence/entity_resolution_store.py, not in the CDD-085 AA 7-path ceiling)
lacks the same explicit session.flush() that its sibling append_decision() already uses to force
record-before-history insert ordering.
```

**CDD-085 itself, and its own original companion Artifact Authorization, are not modified, not reopened, and
remain FROZEN exactly as originally published.** This amendment closes a governance-process gap the original
Artifact Authorization's own text already anticipated and named the required response to ("if implementation
discovers a genuine need to touch an unnamed path, implementation must STOP and return for a narrow
amendment") — implementation discovered the need and correctly stopped, exactly as required. §21 below
records this explicitly: the stopped session is not described as noncompliant, because it was not.

## 2. Context and preserved stopped state (independently re-derived this phase, not merely trusted from I's report)

This phase operated from a separate, clean governance worktree checked out directly from the governance
branch tip, independent of the stopped implementation worktree, per the governing prompt's own subagent/
worktree-isolation rule:

```
origin/main                                         75d11b460240147c35d4d91023ee4a47a6dbea9a  (exact match to
                                                     expected authoritative main; independently re-confirmed
                                                     via `git fetch origin main` + `git rev-parse origin/main`)
product/noetva-demo-readiness-g @ 996a928           `git merge-base --is-ancestor 75d11b4... 996a928...`
                                                     → confirmed ancestor
CDD-085 hash (re-verified, this phase's own worktree)   c813b47b60a324de798ddbc6097b6b0b4be9806cd9ed720274f1be62d1c9b984
CDD-085 AA hash (re-verified, this phase's own worktree) 7ac0d7454a174b0c8e6202062153f827ff8a11a8c121e6ebaebdadc651fe39b4
```

Both hashes are byte-identical to their originally published values. Neither file drifted.

**Local-`main` divergence, disclosed for the record (does not affect this amendment).** The primary
worktree's local `main` branch ref (`5d59eec...`, an unrelated "production-remediation/orchestration"
lineage) is not an ancestor of `origin/main` and vice versa — two independently-advanced local/remote
pointers in the same physical repository, evidently from concurrent, unrelated work in this same shared
clone. `origin/main` — the shared, authoritative reference every governance hash and branch ancestry claim in
this program is actually anchored to — matches the governing prompt's expected value exactly
(`75d11b460240147c35d4d91023ee4a47a6dbea9a`). No commit relevant to this amendment exists on the divergent
local-`main` lineage; it is disclosed here only in the interest of not silently omitting an observed anomaly,
per this program's own disclosure discipline. It does not constitute "authoritative main moved
incompatibly" (§33 STOP condition 9 of the governing prompt): the one branch that matters for this amendment
— `origin/main` — has not moved at all since H6-VM-R1's own merge.

**Stopped implementation worktree preservation, independently re-verified.** The
`product/noetva-demo-readiness-i` worktree was left exactly as reported, untouched by this phase:

```
$ git status --porcelain   (in the preserved implementation worktree, read-only, never written by this phase)
 M Makefile
 M backend/app/infrastructure/persistence/database_cli.py
 M backend/app/infrastructure/persistence/demo_oqi_seeder.py
 M frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx
 M frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx
```

No commit exists on this branch beyond the inherited `996a928` governance-freeze commit. All five
modifications are exactly the five MODIFY paths CDD-085 AA §3 already authorizes; both CREATE paths (§2 rows
1-2 of the original AA) remain intentionally not yet written, since the D13/D14 reset-integration tests they
require cannot pass honestly until this amendment's fix lands. This phase did not modify, stage, reset,
clean, stash, or rewrite any file in that worktree.

## 3. Independent reproduction (performed fresh, in a separate clean worktree and separate Docker containers — not reused from I's environment)

Reproduced from scratch, against the unmodified `996a928` baseline (no implementation-phase edits present at
all — no `demo-reset`/`demo-verify` commands exist yet at this commit; `demo_oqi_seeder.py` still carries its
pre-rename, pre-Aurora-chain content):

```
Container:      genuinely fresh postgres:17-alpine, port 55450, never touched before this run
Migrate:        alembic upgrade head (fresh, head 0047_oqi_h6_uniqueness) — succeeds
Reproduction:   OntologySeeder(session).load(); session.commit()
                BlueprintSeeder(session).load(); session.commit()
                DemoOqiSeeder(session).seed(); session.commit()
                using create_session_factory(engine) (§5 below) — the exact session construction
                database_cli.py's seed()/demo_reset() use — called directly, with zero code from the stopped
                implementation worktree involved
Result:         IDENTICAL FAILURE, first-ever seed call, genuinely fresh database:

sqlalchemy.exc.IntegrityError: (psycopg.errors.ForeignKeyViolation) insert or update on table
"enterprise_entity_resolution_history" violates foreign key constraint "fk_eer_history_tenant_active_record"
DETAIL:  Key (tenant_id, active_record_id)=(ctec-demo-tenant, 9210d44a-2d87-5f28-b3a8-1b9eacfee86a) is not
present in table "enterprise_entity_resolution_records".
[SQL: INSERT INTO enterprise_entity_resolution_history (understanding_key, tenant_id, active_record_id,
archived_record_ids, updated_at) VALUES ...]
[parameters: two rows batched via cursor.executemany — the SAP and PLM resolution history rows]
```

This is materially stronger evidence than NOETVA-DEMO-READINESS-I's own reproduction: it proves the defect is
**not** specific to a second reset cycle, not specific to `demo_reset()`'s own not-yet-committed code, and not
an artifact of any prior test methodology against a reused container. It reproduces on the **first-ever**
`DemoOqiSeeder.seed()` call against a **truly virgin** database, using only pre-existing, already-committed,
already-authorized-adjacent code.

**Controlled isolation of the exact variable (root-cause proof, not inference).** A second, equally fresh
container (port 55451) ran the identical sequence with one variable changed — `sessionmaker(engine)` (default
`autoflush=True`) in place of `create_session_factory(engine)` (`autoflush=False`) — and **succeeded**. This
isolates the trigger precisely to the `autoflush=False` session configuration `database_cli.py` uses
throughout (`seed()` already, and the stopped `demo_reset()`), not to anything about the Golden Demo change
set, the reset lifecycle in the abstract, or container reuse.

## 4. Exact FK / tables involved

```
Child table (violating INSERT):   enterprise_entity_resolution_history
Parent table (missing row):        enterprise_entity_resolution_records
Constraint:                        fk_eer_history_tenant_active_record
Constraint definition (independently read from
  backend/app/infrastructure/persistence/models/entity_resolution.py,
  EnterpriseEntityResolutionHistoryModel.__table_args__):
    ForeignKeyConstraint(
        ["tenant_id", "active_record_id"],
        ["enterprise_entity_resolution_records.tenant_id", "enterprise_entity_resolution_records.record_id"],
        name="fk_eer_history_tenant_active_record",
    )
```

Independently confirmed the child row genuinely depends on the parent record existing first — this is not
inferred from the constraint's name alone; the constraint's own column mapping (`active_record_id` →
`record_id`) was read directly from the model source.

## 5. SQLAlchemy session configuration (independently verified)

```
backend/app/infrastructure/persistence/session.py:

def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False, autoflush=False)
```

`autoflush=False` is genuinely configured, confirmed by direct source read (not inferred from behavior).
`database_cli.py`'s pre-existing `seed()` function, and the stopped `demo_reset()`, both construct their
session via this exact factory. No other automatic flush occurs on this call path before the final
`session.commit()` — confirmed by the §3 reproduction: the failure is raised at the flush `commit()` performs
internally, with both pending resolution-record and resolution-history rows (across two separate `append()`
calls, per the batched `executemany` parameters) flushed together in one operation.

## 6. `EntityResolutionStore.append()` — verified sequence

Independently read in full, `backend/app/infrastructure/persistence/entity_resolution_store.py:95-121`:

```
self.session.add(self._to_model(record))              # active record queued, NOT flushed (autoflush=False)
key = self.understanding_key(record.supporting_source_object_ids)
record_history = self.session.get(EnterpriseEntityResolutionHistoryModel, key)   # plain SELECT, no autoflush
if record_history is None:
    self.session.add(EnterpriseEntityResolutionHistoryModel(..., current_record_identifier=record.record_id, ...))
else:
    ...  # re-point existing history row
```

Confirmed: no `session.flush()` call anywhere in `append()`. Both the active record and the (new-case)
history row remain pending, unflushed, until whatever later operation triggers a flush — in every real call
site, that is the final `session.commit()` at the end of `seed()`/`demo_reset()`.

## 7. Database-level dependency and ORM ordering analysis

`enterprise_entity_resolution_history` is real Table-level metadata (`ForeignKeyConstraint` in
`__table_args__`, §4) — SQLAlchemy's schema layer knows the constraint exists. **Zero `relationship()`
declarations exist between `EnterpriseEntityResolutionRecordModel` and `EnterpriseEntityResolutionHistoryModel`**
(`grep -n "relationship("` against `models/entity_resolution.py` → zero matches, independently confirmed).
SQLAlchemy's unit-of-work flush-ordering between different mapper classes is driven by `relationship()`-based
`DependencyProcessor`s, not by raw `Table.foreign_keys` metadata alone — so, absent a `relationship()`, the
relative INSERT order of two mapper classes across a single flush is not guaranteed to respect a real,
separately-declared FK. This class-level claim is not overstated beyond what this repository's own evidence
shows: it is precisely the situation `append_decision()`'s own existing comment already documents (§8), and
it is precisely what the §3 controlled reproduction demonstrates empirically, twice, deterministically.

## 8. `append_decision()` precedent — independently confirmed

`entity_resolution_store.py:157-163`, read in full:

```python
self.session.add(self._to_model(record))
# Force the new record's INSERT to hit the database before the
# history row's UPDATE, which references it via a foreign key
# (fk_eer_history_tenant_active_record). The two mapped classes
# have no ORM relationship() between them, so SQLAlchemy's
# automatic flush-ordering cannot be relied on here.
self.session.flush()
history.historical_record_references = [...]
history.current_record_identifier = record.record_id
...
```

Exact placement: immediately after the active record is added to the session, immediately before any
dependent-history mutation. Reason (verbatim from the method's own docstring/comment, not paraphrased): the
same FK, the same absent `relationship()`, the same ordering hazard `append()` has. `append()` is
structurally equivalent in this one specific regard — both add an active resolution record, then either
create or mutate a dependent history row in the same unit of work — and the identical pattern (a single
`self.session.flush()` inserted at the equivalent point) is directly, safely reusable.

## 9. Git-history analysis (independently performed, proves history — not developer intent)

```
b71dcb7  2026-08-06  CDD-004: Implement enterprise entity resolution engine
                      — append() introduced, in its current unflushed shape

f2a642e  2026-08-14  Gate C: add tenant-safe Entity Resolution Steward workspace
                      — append_decision() introduced NEW, with the explicit self.session.flush() and its
                        ordering comment, from its very first commit
                      — append()'s own diff in this SAME commit is independently confirmed to be a PURELY
                        MECHANICAL extraction (session.add(model) → self.session.add(self._to_model(record)),
                        moving the record-construction code into a new _to_model() staticmethod so
                        append_decision() could reuse it) — zero flush was added to append() in this commit,
                        and no other commit since has touched append()'s flush behavior
```

This proves the sequence of events (append() predates append_decision(); append_decision() received the
explicit ordering fix; append() never received the equivalent correction) directly from the diff content, not
from inference about why. No claim is made here about why the developer did not backport the fix to
append() at the time — only that they did not, and the diff shows the extraction commit touched append()
for an unrelated, purely mechanical reason.

## 10. Pre-existing-defect proof (independently confirmed)

```
$ git log -S"resolution_store.append(" --format='%H %ad %s' --date=short \
    -- backend/app/infrastructure/persistence/demo_oqi_seeder.py
  2026-08-31  Docker-I: reproducible governed OQI demo environment   (both SAP/PLM append() call sites)
  2026-09-02  implementation: add governed OQI H4 integrity          (a third append() call site)

$ git show 996a928daea913214c5cfe1cb1c1c109ac4ae87a -- \
    backend/app/infrastructure/persistence/demo_oqi_seeder.py
  (empty diff — CDD-085's own G-phase freeze commit touched zero bytes of this file)
```

All three `resolution_store.append(...)` call sites in `demo_oqi_seeder.py` predate CDD-085 by days to
weeks. The Golden Demo Aurora ontology-chain code (CDD-085 AA §3 row 1, part (c)) is structural-only — new
`EnterpriseEntity`/`InstitutionalRelationship` rows — and independently confirmed to never call
`EntityResolutionStore` at all. **Classification confirmed: PRE-EXISTING CORRECTNESS DEFECT, EXPOSED BY THE
NEW DETERMINISTIC RESET/RESEED LIFECYCLE — not a Golden Demo regression.**

Additionally confirmed: `backend/app/infrastructure/persistence/seed_loader.py` (the unrelated, untouched
EDT-001 production dataset path, CDD-085 AA §4) never references `EntityResolutionStore` — this defect is
scoped to `DemoOqiSeeder`'s own resolution-record seeding, not a general production hazard on every ingest
path. `backend/docker-entrypoint.sh` (independently read in full) never calls `DemoOqiSeeder` either — only
`OntologySeeder`/`BlueprintSeeder`, using `sessionmaker(engine)` with **default** `autoflush=True` — which
is exactly why this dormant defect has never before been exercised by any existing, already-shipped code
path. It took the Golden Demo's own new deterministic full-reset-then-reseed lifecycle (§18/§20 of CDD-085,
the first caller anywhere in the repository to run `DemoOqiSeeder` through an `autoflush=False` session) to
expose it.

## 11. Why demo-reset exposes the defect (independently validated, exact runtime sequence)

```
reset database (alembic downgrade base -> upgrade head, wipes all rows)
    -> OntologySeeder / BlueprintSeeder (idempotent, unaffected)
    -> DemoOqiSeeder.seed(), inside `with factory() as session:` where factory = create_session_factory(engine)
    -> three EntityResolutionStore.append() calls, each queuing an active-record add and a history add,
       none flushed between them (autoflush=False)
    -> session.commit() at the very end of demo_reset()/seed()
    -> commit's implicit flush processes ~dozens of pending objects across many mapper classes in one
       operation; absent relationship()-based ordering info for these two specific classes (§7), the
       history-table INSERTs are emitted before the still-pending records-table INSERTs are visible
    -> ForeignKeyViolation
```

Independently re-run three times in this phase (§3's two containers plus §12's two additional containers
below) with 100% reproducibility and byte-identical failing UUIDs each time it was not fixed — deterministic,
not a flake.

## 12. Caller-workaround analysis (empirically tested, not merely reasoned — §13 of the governing prompt required this, not assumed)

Two distinct caller-side workarounds were empirically tested, via Python monkeypatching in a disposable
verification script (never written to any repository file, never committed):

```
TEST — flush placed BETWEEN the two append() CALLS (a workaround entirely reachable from
       demo_oqi_seeder.py, an already-authorized file, never touching entity_resolution_store.py):
       EntityResolutionStore.append wrapped to call self.session.flush() immediately after it returns,
       fresh container (port 55452), full seed() run
RESULT: FAILS — identical ForeignKeyViolation

TEST — flush placed INSIDE append(), between its own two internal session.add() calls (the proposed fix,
       verified here only by monkeypatch — entity_resolution_store.py was NOT edited on disk):
       fresh container (port 55453), full seed() run
RESULT: SUCCEEDS
```

This directly answers the governing prompt's §13 requirement: a caller-side flush — whether placed after
`seed()` returns (already effectively what `session.commit()` does — proven to fail, §3) or between the two
`append()` *calls* (proven to fail here) — cannot fix this, because both objects inside a single `append()`
call are added to the session together, before control ever returns to any caller. Only a flush placed
**between the record-add and the history-add, inside `append()` itself**, changes the outcome. No workaround
confined to `demo_oqi_seeder.py` or `database_cli.py` (both already-authorized) is sufficient. The fix must
live in `entity_resolution_store.py`.

## 13. Narrowest correct fix — verified by monkeypatch, not merely proposed

The same fresh-container test (§12, port 55453) additionally proved the fix's correctness beyond "no
exception raised":

```
history rows after fix, fresh seed:            3  (SAP, PLM, and the third pre-existing call site)
tenant_id on every row:                         ctec-demo-tenant  (correct, matches every record)
current_record_identifier on every row:         equals that record's own record_id  (correct linkage)
historical_record_references on every row:      []  (correct — first-ever append() for each understanding_key)
```

A second full reset+reseed cycle (downgrade base -> upgrade head -> reseed, same container, same monkeypatch)
was then run to independently verify repeatability (mirroring the future D17 obligation, §25 below):

```
second cycle result:                            SUCCEEDS
history rows after second cycle:                3  (unchanged — no accumulation, no duplication, no
                                                     cross-cycle contamination)
```

The narrowest correct fix is confirmed: exactly one additional `self.session.flush()` call inside
`EntityResolutionStore.append()`, placed immediately after `self.session.add(self._to_model(record))` and
before `self.session.get(EnterpriseEntityResolutionHistoryModel, key)` — the semantic position "after the
active resolution record has been added to the session and before the dependent history row is allowed to
persist," mirroring `append_decision()`'s own already-proven placement (§8) as closely as structurally
appropriate. Current line numbers (subject to normal movement, not frozen as brittle anchors): between lines
97 and 99 of `entity_resolution_store.py` as read in this phase's worktree.

## 14. Why no schema change is required

The FK correctly rejected a child row whose parent had not yet reached the database — this is the constraint
doing exactly its job (governing principle, restated per §19 of the governing prompt: DATABASE CONSTRAINT
FAILURE ≠ DATABASE DEFECT). §4's constraint definition is unmodified by this amendment. Zero migration is
authorized or required.

## 15. Why no transaction-boundary or session-factory redesign is required

`create_session_factory`'s `autoflush=False` configuration is unmodified and unquestioned by this amendment —
it is a deliberate, pre-existing, whole-application setting (`session.py`), not something this one call site's
defect implicates broadly. `demo_reset()`'s own commit ownership (`session.commit()` once, at the end, inside
`database_cli.py`) is unmodified. The fix is exactly one additional flush inside one method; it changes only
*when* the already-pending parent INSERT is flushed, never who owns the transaction, never the commit
boundary itself.

## 16. Amendment authorization — effective Artifact Authorization

CDD-085's companion Artifact Authorization
(`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture-Artifact-Authorization.md`) is amended to add
exactly one MODIFY row to its existing §3 table:

```
MODIFY  backend/app/infrastructure/persistence/entity_resolution_store.py
        Inside EntityResolutionStore.append() only: add exactly one self.session.flush() call, placed
        immediately after self.session.add(self._to_model(record)) and immediately before
        self.session.get(EnterpriseEntityResolutionHistoryModel, key) — mirroring append_decision()'s
        own existing, already-proven pattern (§8/§13 of this amendment) as closely as structurally
        appropriate. No other line in this file may change: no formatting churn, no opportunistic
        cleanup, no change to _assert_source_objects_owned_by_tenant, _to_model, append_decision,
        list_current_records, get_current_record, get_history, get_record_by_id, or any exception
        class. No relationship() added. No FK removed, weakened, or deferred. No constraint changed.
        No mapper architecture change. No global autoflush change. No session-factory change. No
        commit-boundary change inside append() (append() still never calls session.commit() itself).
```

No other implementation path is authorized by this amendment. The original 7 paths (§2-§3 of the original
CDD-085 AA) are unchanged, in every particular, including their own permitted-modification text.

## 17. Fix-scope negative proof (binding, restated per governing-prompt §16-§18)

This amendment authorizes zero change to: resolution semantics; resolution identity; decision semantics;
history semantics; tenant ownership; the FK structure or any constraint; transaction boundaries beyond the
one flush's placement; commit ownership; any public API; any model/mapped-class definition; any schema; any
migration. It does not authorize adding `relationship()`, removing or deferring the FK, changing the
constraint, enabling global autoflush, changing the session factory, committing inside `append()`, or any
broader restructuring of Entity Resolution persistence. Migration count: zero, before and after.

## 18. Updated exact Artifact Authorization accounting

```
Original authorized paths (CDD-085 AA §1):        CREATE = 2, MODIFY = 5, DELETE = 0, TOTAL = 7
This amendment's addition (§16, one MODIFY):       CREATE = 0, MODIFY = 1, DELETE = 0, TOTAL = 1
Updated total authorized implementation paths:     CREATE = 2, MODIFY = 6, DELETE = 0, TOTAL = 8
```

This document itself (§20) is a 9th path but is self-authorizing (governance documents authorize their own
publication, per every prior phase's identical convention) and is not counted against the implementation-path
total above.

## 19. Updated/effective test obligations

D13 ("no merge/deactivate action exists for the pair") and D14 ("candidate Finding is OPEN, no adjudication
exists in fresh-seed state") are unaffected in substance by this amendment — they were never blocked by this
defect. D16 ("demo-reset removes prior contamination") and D17 ("two consecutive demo-reset + re-seed cycles
produce semantically identical Golden Demo state") now additionally serve, per the governing prompt's own
§22, as the integration proof that Entity Resolution record/history persistence ordering no longer breaks
reseeding — both are directly exercised by this amendment's own §13 verification and must continue to pass
once the real (non-monkeypatched) fix lands. Per the governing prompt's §23, implementation may add one
additional, narrowly-scoped regression assertion inside the already-authorized
`backend/app/tests/test_noetva_demo_readiness_golden_story.py` (CDD-085 AA §2 row 1) proving: the active
resolution record and its history row persist without FK violation across `demo-reset`; tenant identifiers
match; history references the correct active record; repeated reset/reseed succeeds without duplication;
`append_decision()` behavior is unchanged (mirrors §24 items 1-8 of the governing prompt). No additional test
file is authorized by this amendment; the existing D16/D17 obligations and this one added assertion are
sufficient and must not be weakened.

## 20. Amendment artifact path

```
CREATE = 1
MODIFY = 0
DELETE = 0
TOTAL  = 1
```

```
CREATE  docs/cdd/CDD-085-Artifact-Authorization-G-R1-Entity-Resolution-Flush-Ordering-Amendment.md
        This document. No other path touched by this amendment's own publication.
```

## 21. Historical honesty (binding, disclosed without euphemism)

NOETVA-DEMO-READINESS-I correctly stopped before writing to an unauthorized path, exactly as CDD-085 AA's own
binding text required ("if implementation discovers a genuine need to touch an unnamed path, implementation
must STOP and return for a narrow amendment"). It did not touch `entity_resolution_store.py`. It did not work
around the defect from an authorized file. It did not weaken the FK. It did not fabricate a passing test for
broken functionality by leaving the two CREATE-path deliverables (test file, runbook) unwritten rather than
writing a dishonest or skipped test. This amendment is prospective, not corrective of any violation — there
was none. The stopped session's own STOP report's root-cause analysis (session config, `append()` sequence,
FK dependency, `append_decision()` precedent, git history, pre-existing-defect classification) is
independently re-confirmed accurate in every particular by this phase's own from-scratch re-derivation (§3-§10
above); no claim in the original STOP report was found to be inflated, assumed, or unverified.

## 22. G-R1 STOP conditions (binding, exhaustive — restated for the record; none triggered this phase)

```
 1. failure could not be reproduced.                                                     NOT TRIGGERED (§3)
 2. the FK was found not to be the reported dependency.                                  NOT TRIGGERED (§4)
 3. append() was found to already flush correctly.                                       NOT TRIGGERED (§6)
 4. append_decision() precedent was found materially different.                          NOT TRIGGERED (§8)
 5. the one-line flush was found not to correctly resolve ordering.                       NOT TRIGGERED (§13)
 6. a broader transaction redesign was found required.                                   NOT TRIGGERED (§15)
 7. a schema change was found required.                                                  NOT TRIGGERED (§14)
 8. more than one additional implementation path was found required.                     NOT TRIGGERED (§16)
 9. original frozen governance was found to have drifted.                                NOT TRIGGERED (§2)
10. authoritative main was found to have moved incompatibly.                             NOT TRIGGERED (§2)
```

## 23. P0/P1/P2/P3

```
Before this amendment: P0 = 1 (demo-reset, a CDD-085 §18-required deliverable, deterministically fails on
                        every invocation — reproduced on a genuinely fresh database with zero implementation-
                        phase code involved)
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending NOETVA-DEMO-READINESS-I-R1's own full,
                        independent re-verification of the updated 8-path authorized set, the real
                        (non-monkeypatched) fix, and the complete original I verification bar)
```

## 24. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent (CDD-039, CDD-049-Artifact-Authorization-H3-VM-R1, CDD-050-Artifact-Authorization-H4-R1,
CDD-084-Artifact-Authorization-H6-G-R1) of never silently rewriting an already-approved Artifact Authorization
in place, and never authorizing an implementation-time decision to expand scope unilaterally.
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md` and its original companion Artifact Authorization
remain FROZEN, unmodified, and fully authoritative. This amendment's §16 authorizes exactly one additional
MODIFY path — `backend/app/infrastructure/persistence/entity_resolution_store.py`, exactly one
`self.session.flush()` line inside `append()`, no other change — bringing the effective implementation
ceiling to CREATE=2, MODIFY=6, DELETE=0, TOTAL=8. No implementation write against any path has occurred as
part of this amendment; it is a governance-artifact-only correction, and the preserved
`product/noetva-demo-readiness-i` worktree (§2) may resume from its current state once this amendment is
frozen and pushed. Demo Readiness implementation readiness is reauthorized to resume, under the identifier
NOETVA-DEMO-READINESS-G-R1 → NOETVA-DEMO-READINESS-I-R1, only after I-R1's own complete, independent
re-verification per §32 of the governing prompt.
