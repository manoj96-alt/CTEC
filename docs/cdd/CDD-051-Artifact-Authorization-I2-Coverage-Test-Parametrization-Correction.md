# CDD-051 Artifact Authorization Amendment — I2 Coverage Test Parametrization Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-051 Artifact Authorization §4 (row 6) only — narrowly, mechanically, without reopening any architecture, dispatch, or coverage-semantic decision
**Precedent:** this repository's established discipline of never modifying a frozen governance artifact's authorized surface in place — every correction is published as its own companion document. Direct precedent: `CDD-051-Artifact-Authorization-Migration-Revision-Length-Correction.md` (identical class of discovered-during-implementation, mechanically-forced correction, OQI-H5-I1).

## 1. Discovered defect

CDD-051 Artifact Authorization §4 row 6 authorizes exactly one new test in
`backend/app/tests/test_oqi_quality_coverage_policy_service.py`
(`test_timeliness_dispatches_to_timeliness_evaluation_repository`) and states "No other test in this file
may change."

That same file already contains a pre-existing, parametrized test, written before H5 existed:

```python
@pytest.mark.parametrize(
    "dimension",
    [
        CoverageDimension.UNIQUENESS,
        CoverageDimension.TIMELINESS,
    ],
)
def test_unsupported_dimension_dispatch_returns_false_without_querying(
    dimension: CoverageDimension,
) -> None:
    ...
    assert result is False
    oqi1_cls.assert_not_called()
    oqi2_cls.assert_not_called()
```

This test asserts that `CoverageDimension.TIMELINESS` is an *unsupported* dimension — returning `False`
without ever querying anything. CDD-051 §25 (implemented in I2 exactly as frozen) makes `TIMELINESS` a
*supported*, dispatching dimension — it now calls `OqiTimelinessEvaluationRepositoryImpl.
has_qualifying_coverage`. Under the frozen `TIMELINESS` branch, this parametrized case now fails with
`AttributeError: 'NoneType' object has no attribute 'execute'` (the test's `_repo()` fixture passes
`session=None`, valid only for the genuinely-unsupported, zero-query dimensions this test is meant to
cover) — a direct, mechanical consequence of implementing exactly what CDD-051 §25 already froze, not a new
architectural decision.

## 2. Exact correction

```
backend/app/tests/test_oqi_quality_coverage_policy_service.py:
  test_unsupported_dimension_dispatch_returns_false_without_querying's
  @pytest.mark.parametrize dimension list:

    [CoverageDimension.UNIQUENESS, CoverageDimension.TIMELINESS]
  →
    [CoverageDimension.UNIQUENESS]
```

No other line in this test function, or in this file beyond the one new test already authorized by row 6,
changes.

## 3. Scope of this correction (binding)

This amendment changes **only** the parametrize list of one pre-existing test — removing the now-factually-incorrect `TIMELINESS` case. It does **not** change:

- the test's assertions, structure, or the `UNIQUENESS` case, which remains genuinely unsupported and
  correctly proven zero-query;
- any other test in this file;
- any dispatch logic, coverage semantics, or CDD-051 §25 decision;
- the accounting in Artifact Authorization §1/§4/§5 (still `MODIFY = 6` for I2 — this is a correction
  within the same authorized file, not an additional path).

## 4. Why this is safe

Purely a mechanical narrowing of a parametrize list to match a dimension's dispatch status, which CDD-051
§25 already froze and I2 implements verbatim. No semantic content, no persisted data, and no other
governance decision depends on this list's exact membership — only on `TIMELINESS` genuinely dispatching
(proven by the newly-added `test_timeliness_dispatches_to_timeliness_evaluation_repository`) and
`UNIQUENESS` genuinely not (unchanged, still proven by this same test).

## 5. Authorization

`test_unsupported_dimension_dispatch_returns_false_without_querying`'s parametrize list is corrected to
`[CoverageDimension.UNIQUENESS]` effective immediately. OQI-H5-I2 implementation resumes using this
corrected list. No other file, table, dispatch branch, or decision in CDD-051 or its Artifact Authorization
is affected.
