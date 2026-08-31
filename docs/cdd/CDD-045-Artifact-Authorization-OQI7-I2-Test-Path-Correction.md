# CDD-045 Artifact Authorization Amendment — OQI7-I2 Test-Path Correction

**Status:** APPROVED ARTIFACT AUTHORIZATION AMENDMENT
**Version:** 1.0
**Amends:** CDD-045 Artifact Authorization §3, OQI7-I2 row, one unnumbered MODIFY entry only — narrowly,
mechanically, without adding, removing, or renaming any other path, and without reopening CDD-045's
architecture, CDD-033's historical decisions, or the CDD-033 OQI7 companion amendment's route authorization
**Precedent:** same class of correction as
`CDD-043-Artifact-Authorization-I2-Accounting-Correction.md` — a narrow, implementation-discovered path
misattribution in an already-frozen governance document, corrected via companion document rather than
in-place edit

## 1. Discovered defect

At OQI7-I2 implementation-start preflight (before any file was created or modified — the implementation
attempt correctly stopped and left the repository completely clean), direct inspection of the CDD-045
Artifact Authorization §3 OQI7-I2 table found this unnumbered MODIFY row:

```
MODIFY | frontend/tests/gate-x-navigation.test.tsx | update expected /quality domain content assertions
to reflect the live OQI Command Center replacing the PLANNED placeholder cards; no other navigation-array
assertion changed
```

Direct inspection of `frontend/tests/gate-x-navigation.test.tsx` in full shows it contains **no `/quality`
domain content assertions of any kind**. Its three tests exercise only `SiteShell`'s top-level primary/
secondary navigation arrays (the frozen CDD-033 §8 domain list — `Overview`, `Data`, `Ontology`, `Context`,
`Quality`, `Intelligence`, `Integrations`, `Governance`, `Administration` — plus a forbidden-nav-item list
and utility links), rendered against a stub `<p>Page content</p>` child. It never imports or renders
`QualityPage`. The `/quality` domain's label and route (`"Quality"` / `/quality`) are unaffected by anything
inside the `/quality` page itself, so no assertion in this file is capable of failing as a consequence of
replacing that page's internal content.

The actual PLANNED-placeholder content assertions the authorization row's purpose text describes live in a
**different file, `frontend/tests/gate-x-honesty.test.tsx`**, which is not named anywhere in the OQI7-I2
Artifact Authorization:

```tsx
it("generalized Data Quality concepts remain visibly Planned and non-interactive", () => {
  render(<QualityPage />);
  for (const name of ["Rules", "Findings", "DQ Impact", "Remediation"]) {
    const heading = screen.getByRole("heading", { name });
    const card = heading.closest("section");
    expect(card).not.toBeNull();
    expect(within(card as HTMLElement).queryByRole("link")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).queryByRole("button")).not.toBeInTheDocument();
    expect(within(card as HTMLElement).getByText("Planned")).toBeInTheDocument();
  }
});
```

This test renders the real `QualityPage`, requires the four named headings' enclosing `<section>` to contain
zero links, zero buttons, and the literal text `"Planned"`. The authorized OQI7-I2 change to
`frontend/app/quality/page.tsx` (replacing these four `PLANNED_CONCEPTS` cards with the live Command Center)
will deterministically make this exact assertion fail — the Command Center is, by design, interactive and no
longer displays "Planned" for these concepts.

Notably, the same Artifact Authorization document's own row 16 (`frontend/tests/oqi-product-truth.test.tsx`)
already describes itself as "mirroring `gate-x-honesty.test.tsx`'s own enforcement pattern" — independent
confirmation that `gate-x-honesty.test.tsx` was the file this authorization's author had in mind for this
class of rendered-content honesty assertion, and that the MODIFY row simply named the wrong path.

## 2. Independent proof of Outcome A (exact swap), per OQI7-GC1's own required method

**Does `gate-x-navigation.test.tsx` require I2 modification? NO.** Read in full (86 lines): it asserts only
the `SiteShell` primary-nav label/href array, a forbidden-nav-item list, and secondary utility links. None of
its assertions reference `/quality` page content, `QualityPage`, `PLANNED_CONCEPTS`, or any of the four named
capability strings. The frozen 9-domain nav array is unaffected by OQI7-I2's authorized page-content change.
No assertion in this file can fail as a result of the authorized OQI7-I2 implementation.

**Does `gate-x-honesty.test.tsx` require I2 modification? YES.** Read in full (233 lines): its
`"generalized Data Quality concepts remain visibly Planned and non-interactive"` test (lines 121-137) renders
`QualityPage` and asserts the exact four cards OQI7-I2 is authorized to replace remain non-interactive
"Planned" placeholders. Without modifying this test, the authorized OQI7-I2 implementation would leave this
test in a permanent, deterministic failing state — a real, provable, direct consequence of the frozen
authorization's own §3 row 1 (`command-center.tsx`) and its `page.tsx` MODIFY row, not a hypothetical.

This file's seven *other* tests (Overview fabrication firewall, Ontology Model Completeness naming, Quality
landing page capability-detail firewall checking `"FIT"/"STALE"/"CONFLICTING"`, Evidence Fitness consumer-
action scope, Simulation non-authority markers, Integrations MCP-execution firewall, Governance
approval-queue firewall, Administration authority-invention firewall, and the context-identifiers-only test)
are unrelated to the four PLANNED cards and require no OQI7-I2 change — confirmed by direct reading, not
assumption. **Outcome A (exact swap) is proven**, not Outcome B (both files) or Outcome C (a different file
entirely).

## 3. CDD-045 and CDD-033 companion amendment — confirmed unaffected

`grep -n "gate-x-navigation\|gate-x-honesty"` against both `CDD-045-Ontology-Quality-Intelligence-Flagship-
Explainable-Product-Experience.md` and `CDD-033-OQI7-Placeholder-Supersession-Amendment.md` returns **zero
hits in either document** — neither file names either test path anywhere. The path misattribution is isolated
entirely to the one Artifact Authorization row identified in §1. CDD-045's semantic architecture, the CDD-033
companion amendment's route-supersession authorization, and historical CDD-033 itself require **no change**
and are **not modified** by this correction.

## 4. Exact correction

```
CDD-045 Artifact Authorization §3, OQI7-I2 table, one unnumbered MODIFY row:

REMOVE:
MODIFY | frontend/tests/gate-x-navigation.test.tsx | update expected /quality domain content
assertions to reflect the live OQI Command Center replacing the PLANNED placeholder cards; no
other navigation-array assertion changed

ADD:
MODIFY | frontend/tests/gate-x-honesty.test.tsx | update exactly the
"generalized Data Quality concepts remain visibly Planned and non-interactive" test (and only that
test) to assert the new governed truth for whichever of Rules/Findings/DQ Impact/Remediation OQI7-I2
actually makes live, per CDD-045's own authorized scope -- evolving the assertion from enforcing the
old PLANNED-placeholder contract to enforcing the new governed contract, never merely deleting it. No
other test in gate-x-honesty.test.tsx (Overview fabrication firewall, Ontology Model Completeness
naming, Quality-page capability-detail firewall, Evidence Fitness consumer-action scope, Simulation
non-authority markers, Integrations MCP-execution firewall, Governance approval-queue firewall,
Administration authority-invention firewall, context-identifiers-only test) may be touched.
```

`gate-x-navigation.test.tsx` is removed from OQI7-I2's authorized path set entirely -- it requires no
modification and must not be touched by OQI7-I2.

## 5. Corrected effective OQI7-I2 authorization (unique paths unchanged at 18)

```
CREATE = 16   (unchanged, rows 1-16 of §3, untouched by this correction)
MODIFY = 2    (semantic; frontend/app/quality/page.tsx unchanged;
               frontend/tests/gate-x-honesty.test.tsx replaces frontend/tests/gate-x-navigation.test.tsx)
DELETE = 0
TOTAL  = 18
```

**Independent double-count reconciliation**: Count derivation A (summary arithmetic):
`16 CREATE + 2 semantic MODIFY + 0 DELETE = 18`. Count derivation B (literal enumeration): the corrected §3
table has 16 numbered CREATE rows + 2 unnumbered MODIFY rows (`page.tsx`, `gate-x-honesty.test.tsx`) =
`16 + 2 = 18`. Both derivations agree at **18** -- identical to the pre-correction total. Only the identity
of one MODIFY path changed; the count did not.

## 6. Scope of this correction (binding)

Changes only the identity of one MODIFY path in CDD-045 Artifact Authorization §3's OQI7-I2 table. It does
**not** change:

- the total OQI7-I2 path count (18, unchanged);
- any CREATE path (all 16 remain exactly as frozen);
- the other semantic MODIFY path (`frontend/app/quality/page.tsx`, unchanged);
- OQI7-I1's authorization (§2, entirely unaffected -- OQI7-I1 is already closed and merged);
- any CDD-045 architecture, UI Truth Table, API contract, firewall, or product decision;
- the CDD-033 OQI7 companion amendment's route-supersession authorization;
- historical CDD-033 itself, which remains frozen and unedited;
- any other section of the CDD-045 Artifact Authorization (§1-2, §4-10 unaffected).

## 7. Why this is safe

Purely a path-identity correction reconciling an authorization row's own stated purpose with the file that
actually carries that responsibility, independently proven by direct inspection of both candidate files'
complete contents rather than assumed. No new implementation surface is authorized beyond what the original
row's own purpose text already described -- this correction only points that already-authorized purpose at
the file capable of fulfilling it. No CREATE path is added or removed; the total unique-path count is
unchanged at 18.

## 8. Authorization

CDD-045 Artifact Authorization §3's OQI7-I2 MODIFY row naming `frontend/tests/gate-x-navigation.test.tsx` is
corrected to name `frontend/tests/gate-x-honesty.test.tsx` instead, with the narrow, exact purpose stated in
§4 above, effective immediately. OQI7-I2 implementation, when re-authorized, proceeds using this corrected
path set: **CREATE = 16, MODIFY = 2 (`frontend/app/quality/page.tsx` and
`frontend/tests/gate-x-honesty.test.tsx`), DELETE = 0, TOTAL = 18 unique authorized paths**.
`frontend/tests/gate-x-navigation.test.tsx` is not an authorized OQI7-I2 path and must not be modified by
OQI7-I2. No other file, table, architecture decision, or governance document is affected. CDD-045, the
original Artifact Authorization, and the CDD-033 OQI7 companion amendment remain byte-identical and
unmodified -- this is a companion correction only. OQI7-I2 implementation itself is not started by this
document.
