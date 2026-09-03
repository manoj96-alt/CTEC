# CDD-049 — Artifact Authorization H3-VM-R1 CI Type-Safety Amendment (OQI-H3-VM-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-047-Artifact-Authorization-CI-Migration-Head-Closure-Amendment.md` (OQI-H1-CI — the direct
precedent for this exact defect class: a legitimately-authorized H-phase change invalidates a
pre-existing assertion in a file entirely outside that phase's own Artifact Authorization, discovered
only once real CI ran against the merged candidate); `CDD-049-Artifact-Authorization-H3-I-R1-Information-
Element-and-Test-Path-Amendment.md` (OQI-H3-I-R1 — the direct precedent for narrow, additive,
implementation-blocking governance correction within the H3 track itself)
Classification: TEST-DOUBLE PROTOCOL CONFORMANCE GAP (mechanical, type-level correction only; no
architectural, semantic, Protocol-shape, production-behavior, or CI-strength change of any kind)

## 1. Purpose

Authorizes the exact, narrow correction of a single stale test double discovered by GitHub CI's
whole-package `mypy app` check on PR #184 (`oqi-h3/conformity-canonical-standards` → `main`), running
against the fully OQI-H3-VM-adversarially-verified candidate `f8dbdc049421bc3289032b5625370b0f4b2e5ffe`.
The `backend` check failed; `frontend` and `containers` passed. `backend/app/tests/test_oqi_cross_source_
evaluation_service.py` is a pre-existing, pre-H3 unit-level test file for `OqiCrossSourceEvaluationService`
that was never named in either the original CDD-049 Artifact Authorization (28 paths) or the OQI-H3-I-R1
amendment (4 paths). This amendment closes that gap under its own explicit, narrow authorization, exactly
mirroring the OQI-H1-CI precedent's reasoning: the original Artifact Authorization correctly scoped H3's
own implementation surface, but neither it nor the R1 amendment anticipated that scope would leave a
type-level assertion in an out-of-scope file uncorrected once whole-package `mypy` — not run in isolation
against only the AA-authorized file list during implementation or VM — was exercised by real CI.

## 2. Context — independently re-derived, not merely trusted from the OQI-H3-VM report

OQI-H3-VM (this session, prior turn) ran `mypy` scoped to the 15 files it had touched and reported them
clean. It did not run `mypy app` (the whole package, exactly as CI's `.github/workflows/ci.yml:31` does)
until after opening PR #184, at which point GitHub CI's own `backend` check failed. This session
independently re-fetched the exact failing CI run for head SHA `f8dbdc049421bc3289032b5625370b0f4b2e5ffe`
(`gh run view 33707510368 --log-failed`) and independently reproduced the identical failure locally via
`cd backend && python3 -m mypy app`:

```
Found 26 errors in 1 file (checked 587 source files)
```

Every one of the 26 diagnostics is the identical message, at 26 distinct call sites (lines 166, 199, 223,
246, 315, 332, 351, 367, 402, 435, 451, 484, 515, 536, 589, 606, 618, 637, 649, 677, 688, 715, 769, 787,
815, 849), all in `backend/app/tests/test_oqi_cross_source_evaluation_service.py`:

```
error: Argument "evaluation_repository" to "OqiCrossSourceEvaluationService" has incompatible type
"_FakeRepository"; expected "ComparisonEvaluationRepository"  [arg-type]
note: "_FakeRepository" is missing following "ComparisonEvaluationRepository" protocol member:
note:     link_canonical_projection
```

Independently confirmed: zero diagnostics anywhere else in the 587-file package. This collapses to exactly
one root cause, not 26 independent ones.

## 3. Root-cause analysis (independently re-derived)

`ComparisonEvaluationRepository` (`backend/app/application/oqi_cross_source_evaluation_service.py:102`) is
a `Protocol`. CDD-049 §17 (frozen, original AA MODIFY row 3) legitimately extended it with one new member:

```python
def link_canonical_projection(
    self, *, evaluation_id: UUID, participant_role: str, canonical_value_id: UUID, standard_version: int
) -> None: ...
```

The production implementation, `OqiCrossSourceEvaluationRepositoryImpl.link_canonical_projection`
(`backend/app/infrastructure/persistence/oqi_cross_source_evaluation_repository.py:181-199`), independently
confirmed to carry the byte-identical signature and to be exercised correctly (real PostgreSQL, OQI-H3-VM
§S/§K8), already conforms — it is not the defect.

`backend/app/tests/test_oqi_cross_source_evaluation_service.py` predates H3 entirely (it is the OQI2
service-level unit-test file, unrelated to Postgres, using a hand-written `_FakeRepository` test double at
line 54). It was never named in the original CDD-049 Artifact Authorization or the H3-I-R1 amendment
because H3's own implementation never needed to touch it — every one of its tests constructs
`OqiCrossSourceEvaluationService` with `canonical_standard_lookup` omitted (defaulting to `None`, CDD-049
§16's own Case-A/legacy-unchanged guarantee), so `link_canonical_projection` is never actually invoked by
any test in this file — confirmed by grep: the file contains zero references to `canonical_standard_lookup`
or `link_canonical_projection` anywhere in its 900+ lines. This is a **purely static, structural Protocol-
conformance gap**, not a functional or behavioral one: `_FakeRepository` never needs to exhibit new
behavior, only to type-check as satisfying the Protocol's now-larger shape.

```
H3 architectural defect:              NO
Conformity/Consistency semantic defect: NO
Production code defect:               NO -- OqiCrossSourceEvaluationRepositoryImpl already conforms
Protocol-shape defect:                 NO -- the Protocol's extension was itself already authorized by
                                        the original CDD-049 Artifact Authorization MODIFY row 3
Test behavioral defect:                NO -- no test in this file exercises the new member; none needs to
Authorization defect:                  YES -- the original AA and the R1 amendment both correctly scoped
                                        out this file (H3's own implementation never required touching
                                        it), but neither anticipated that this exclusion would leave a
                                        type-level assertion stale once whole-package mypy, run for the
                                        first time by real CI, was exercised against it
```

## 4. Minimum correction design

`_FakeRepository` gains exactly one new method, `link_canonical_projection`, with the exact production
Protocol signature, implemented by appending a `("link_canonical_projection", ...)` tuple to
`self.call_log` — the identical idiom every one of its five existing methods already uses (lines 62-90).
This is the smallest behaviorally honest implementation: consistent with the file's own established
pattern, requires no new fixture/state, asserts nothing new (no existing or new test currently needs to
assert on this call, since it is never invoked), and is trivially extensible by a future test that does.

**Explicitly not authorized by this amendment:** removing or weakening the Protocol member; adding
`# type: ignore`; typing the parameter as `Any`; excluding this file from mypy; suppressing or downgrading
the CI check; modifying `OqiCrossSourceEvaluationService`, `ComparisonEvaluationRepository`,
`OqiCrossSourceEvaluationRepositoryImpl`, or any other production file; modifying any other test file;
modifying any existing assertion, fixture, or test case in the target file.

## 5. Exact new path authorization

```
CREATE = 0
MODIFY = 1
DELETE = 0
```

```
MODIFY  backend/app/tests/test_oqi_cross_source_evaluation_service.py
```

Exactly one path. No other file is authorized by this amendment. Specifically **not** authorized: any
production source file (all already conform or are unaffected); any other test file (whole-package mypy,
independently re-run, confirms zero diagnostics anywhere else); any migration; any CI workflow file (the
existing `mypy app` step itself requires no change — it is already correctly whole-package and already a
required, blocking check; this amendment corrects the codebase to satisfy it, never the reverse).

## 6. Semantic-strength requirement — confirmed preserved

The `ComparisonEvaluationRepository` Protocol is unchanged in shape (still exactly five members, as CDD-049
originally authorized). `mypy app`'s CI step is unchanged (still whole-package, still a required, blocking
check, `--strict`, no new exclusion). No test assertion in the target file is weakened, removed, or
loosened. No `type: ignore`, `Any`, or `--ignore-errors` is introduced anywhere.

## 7. Unchanged, reaffirmed (binding)

Table count remains exactly **114** (unaffected — this amendment touches zero schema/migration surface).
The Accuracy firewall (CDD-049 §18/PO-H3-02), the ER firewall (CDD-049 §13/§35 STOP condition 4), the
Information Element anchor (CDD-049 §8, independently re-attacked and confirmed compliant by OQI-H3-VM),
and all crown invariants (CDD-049 §32) are unchanged and unaffected by this amendment. The three H3
migrations and both prior amendments (`CDD-049-Artifact-Authorization-H3-I-R1-Information-Element-and-
Test-Path-Amendment.md`) require no further change.

## 8. Governance byte-integrity

Independently re-hashed immediately before this document was written and confirmed byte-identical to
their prior publication values:

```
a45242b6a821a984031c1c3238aeed13b0c5d4f570c443e8510cf04f0bf3eaa4
  CDD-049-OQI-H3-Governed-Conformity-and-Canonical-Standards.md
0cd38498f8df59dd282992857ae01dc566bec9279531e9309b83a154f90e323f
  CDD-049-OQI-H3-Governed-Conformity-and-Canonical-Standards-Artifact-Authorization.md
ff0736cd2f674f053a1914deedbbe788b26d8c1f661120ce6bb536f9f7634ded
  CDD-049-Artifact-Authorization-H3-I-R1-Information-Element-and-Test-Path-Amendment.md
```

This document is the sole new artifact. No prior governance file is modified.

## 9. Historical honesty (binding, disclosed without euphemism)

OQI-H3-VM correctly stopped rather than opportunistically repair the unauthorized file during adversarial
verification (`OQI-H3-VM: STOPPED — CI DEFECT`). This is the exact discipline the OQI-H1-CI precedent
established: a required CI check failing on an out-of-scope path is a genuine, if narrow, governance gap
— never a license to silently patch it inside an already-verified candidate commit, and never a reason to
weaken the check that caught it. No implementation write occurred against this file before this
amendment's publication.

## 10. P0/P1/P2/P3

```
Before this amendment: P0 = 0, P1 = 1 (required GitHub CI check failing on the exact adversarially-
                        verified candidate, for a reason entirely outside every prior phase's authorized
                        scope), P2 = 0, P3 = 0
After this amendment:   P0 = 0, P1 = 0, P2 = 0, P3 = 0 (pending the one-file correction §5 authorizes and
                         its own fresh whole-package mypy / test / CI re-verification)
```

## 11. Authorization

This amendment is approved and published as a standalone governance artifact, following the established
repository precedent (OQI-H1-CI, OQI-H3-I-R1) of never silently rewriting an already-approved Artifact
Authorization in place, and never folding an out-of-scope correction into an already-verified
implementation commit. Implementation against §5's single-path authorization is authorized only after this
document's own publication and hash computation — never before. OQI-H3 merge readiness is reauthorized to
resume against this corrected surface, under the identifier OQI-H3-VM-R1.
