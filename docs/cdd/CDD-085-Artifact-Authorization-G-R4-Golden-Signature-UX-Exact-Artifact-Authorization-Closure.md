# CDD-085 — Artifact Authorization G-R4 Golden Signature UX Exact Artifact Authorization Closure (NOETVA-GOLDEN-SIGNATURE-UX-G-R1)

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-085-Artifact-Authorization-G-R3-Golden-Signature-UX-Plural-Remediation-Authority-Amendment.md`
(the architecture this closure resolves the one remaining path ambiguity in, and nothing else)
Classification: PATH-CLOSURE ONLY. No architecture, domain semantics, migration design, contract shape, or
product behavior decided by G-R3 is reopened, reconsidered, or altered by this amendment. Its sole content is
resolving G-R3's own disclosed ambiguity — the exact literal test-file ownership for migration verification
and Entity Resolution coverage — by direct repository convention inspection, and republishing one
fully self-consistent literal Artifact Authorization table with counts that are independently re-derivable
from the table itself.
Governs: this amendment only. `CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original
companion Artifact Authorization, `CDD-085-Artifact-Authorization-G-R1-Entity-Resolution-Flush-Ordering-
Amendment.md`, `CDD-085-Artifact-Authorization-G-R2-Golden-Parity-Test-Fixture-Transaction-Isolation-
Amendment.md`, `CDD-085-Artifact-Authorization-G-R3-Golden-Signature-UX-Plural-Remediation-Authority-
Amendment.md`, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion Artifact Authorization are
all unmodified, unreopened, and remain FROZEN exactly as originally published.

## 1. Purpose

`NOETVA-GOLDEN-SIGNATURE-UX-G` closed with a self-disclosed, narrow ambiguity: its own §27.3/§27.4 left the
exact filenames for migration verification and Entity Resolution test coverage unresolved — proposing either
reuse of an existing file or creation of a new one, "implementation must independently confirm," and (for one
frontend file) an explicit CREATE/MODIFY fork. This is incompatible with this program's exact-path
implementation discipline. This amendment resolves every such fork by direct inspection of this repository's
own established conventions, changing zero architecture.

**Disclosed in the interest of the same honesty this program applies to itself throughout:** independently
recounting G-R3's own §27.2 literal table against its own §27.4 narrative this phase found they did not
agree (§27.2 lists 8 frontend production MODIFY paths and, across §27.3, 2 backend test MODIFY paths plus 1
frontend test MODIFY path; §27.4's narrative said "17 (9 backend + 2 backend test + 6 frontend production
files)," undercounting by 3). This is exactly the failure mode this closure phase exists to eliminate. G-R3's
*architecture* is unaffected — every individual path it named remains correct — only its own summary
arithmetic was inconsistent with its own table. This amendment's §7 table is independently re-derived from
scratch and its own count is re-verified against itself before publication (§9).

## 2. Context — independently re-verified this phase

```
origin/main                                  91e90b5812a123d08d58e78347f7283d285921f6  (re-fetched,
                                              re-confirmed)
product/noetva-demo-readiness-final @        b254372b9632c0bd16174678e2ba7f2afd95688c  (unchanged; this
                                              amendment does not touch it)
PR #250                                      OPEN, headRefOid unchanged
PR #249 / #248 (historical)                  OPEN, unchanged
product/noetva-demo-readiness-g-r4 @         82aeb0ac0c2a4b129114abff27223ba5a562fde9  (unchanged; not
                                              rewritten by this amendment)
```

All seven prior governance hashes independently re-hashed this phase against the unmodified `b254372b...`
(six) and `82aeb0ac...` (G-R3 itself) refs — byte-identical:

```
CDD-085                    c813b47b60a324de798ddbc6097b6b0b4be9806cd9ed720274f1be62d1c9b984
CDD-085 AA                 7ac0d7454a174b0c8e6202062153f827ff8a11a8c121e6ebaebdadc651fe39b4
CDD-085 G-R1                bcc4fc8fe8c435d1a9c44079c059065ab15aba3070f5fd1b3bf7163502038efb
CDD-086                    02f893bdf8d310dd0e8270879928c2c5ed1eb30aebae4d42ae7185346347dd67
CDD-086 AA                  162bb163a2af5394caddab5f35c5451d242090d2829dca1a39d33a268fcf9bd7
CDD-085 G-R2                fb7d90ec8500387d09ccb75310b1022cccae93e7f8e5f5e4b5949905ec51587f
CDD-085 G-R3                2e1ba7485781855a9398a6a52e93d5ecd5903ef00073a50b8eda48f3d9114c71
```

## 3. G-R3 architecture — explicitly reaffirmed, not reopened

Every decision in G-R3 §3–§26 (Prepare contract, plural response contract, deterministic ordering, SUPERSEDED
semantics, single-effective-approval invariant, parent-case locking, DB partial unique index, migration
design, execution-report/re-evaluation preservation, the explicit-rejection residual's out-of-scope status,
plural frontend UX, Entity Resolution queue preservation, the entity-keyed lookup contract, the resolved-
identity frontend route, the exact `direct_entity_id` prop thread, the no-seed/no-agent/no-runbook-change
constraints, and the implementation composition strategy) is unchanged and remains binding exactly as
published. This amendment touches only the test-ownership portion of §27.3 and the accounting in §27.4.

## 4. Migration verification — test owner resolved

**Repository convention, independently inspected this phase:** this codebase's own established pattern for
"a migration adds a structural DB constraint enforcing a domain invariant" is to test it inside the
*feature's own existing PostgreSQL integration test file*, never a standalone migration-only test file.
Confirmed by direct read of the precedent this program's own G-R3 cited (CDD-052/053/054/055's tenant-
isolation migrations): their verification — schema shape, FK presence/absence, migration round-trip, data
preservation, and fail-closed-on-invalid-pre-existing-data — lives inside `backend/app/tests/
test_oqi_business_impact.py` (`test_migration_creates_expected_oqi6_schema`, `test_ti05_old_fk_absent`,
`test_ti06_new_fk_present_with_exact_shape`, `test_ti09_migration_round_trip_preserves_valid_dependency_
data`, `test_ti10_migration_fails_closed_on_invalid_legacy_cross_tenant_data`) and `test_oqi_ontology_impact_
postgres.py` — not a dedicated migration-test file. `backend/app/tests/test_production_remediation_
orchestration_postgres.py` (already an authorized MODIFY path in G-R3 for domain-behavior coverage) is the
exact analogous, correct, convention-matching owner for migration `0048`'s own verification (backfill
correctness, `NOT NULL`, FK presence, partial unique index rejecting a second `APPROVED` row at the database
layer directly, and the defensive pre-check's fail-closed behavior on synthetic pre-existing-violation data).
**No new migration-test file is authorized or required.**

## 5. Entity Resolution backend test ownership — resolved

Three existing files, inspected directly this phase, already own the exact three responsibilities G-R3 left
unresolved:

```
backend/app/tests/test_entity_resolution_steward_api_postgres.py
    Already owns EntityResolutionStewardApi service-layer behavior, including the closely analogous
    test_get_case_returns_none_for_another_tenants_understanding_key. Correct owner for: the new entity-
    keyed lookup's found/multiple-source-record/unknown-entity behavior, and a regression guard confirming
    QUEUE_OUTCOMES/queue() remain unmodified.

backend/app/tests/test_entity_resolution_steward_router.py
    Already owns HTTP/router-layer behavior, including the closely analogous test_get_case_not_found_
    returns_404. Correct owner for: the new GET /entities/{entity_id} route's 200/404 semantics and scope
    enforcement.

backend/app/tests/test_entity_resolution_tenant_isolation.py
    Already the dedicated, exact-purpose home for cross-tenant tests, including the closely analogous
    test_tenant_a_cannot_list_or_get_tenant_b_case. Correct owner for: the new lookup's wrong-tenant
    fail-closed behavior.
```

**No new Entity Resolution backend test file is authorized or required.**

## 6. Entity Resolution / remediation frontend test ownership — resolved

```
frontend/tests/oqi-finding-detail.test.tsx
    Independently inspected this phase: already mocks and varies direct_entity_id (null vs. a real value,
    confirmed present at lines using EMPTY_REMEDIATION-adjacent fixtures) as part of its existing Finding-
    detail page-level integration coverage, and already owns the "remediation, authorization, resolution"
    describe block (including the exact-purpose precedent "external remediation reported keeps the Finding
    OPEN, never says Resolved"). Correct owner for: entity-specific Evidence href construction from
    direct_entity_id, absent-entity-ID behavior, and the full-page two-candidate rendering integration
    (Prepare through to both US and MX visible) as part of this file's existing end-to-end page flow.

frontend/tests/oqi-remediation-actions.test.tsx
    Already the dedicated owner of dialog-level interaction contracts (DecideAuthorizationDialog,
    ReportExecutionDialog, the RemediationStepper's exact state mapping, RemediationPanel's own governed-
    truth-boundary wording) -- confirmed unchanged from G-R3's own correct identification. Correct owner
    for: the Prepare control's own API-invocation/refresh contract, APPROVED/SUPERSEDED wording at the
    dialog/action level, and disabled-sibling-action behavior.
```

**No new frontend test file is authorized or required.** G-R3's own explicit CREATE/MODIFY fork for this
responsibility is resolved: MODIFY only, against these two pre-existing files.

## 7. Final literal Artifact Authorization

### 7.1 CREATE (3)

```
1. backend/app/infrastructure/persistence/migrations/versions/0048_oqi_remediation_authorization_mutual_exclusion.py
2. frontend/app/data/entity-resolution/entities/[entityId]/page.tsx
3. frontend/app/data/entity-resolution/entities/[entityId]/_components/resolved-entity-detail.tsx
```

### 7.2 MODIFY (24)

Backend production (9):

```
4.  backend/app/domain/oqi_remediation/authorization.py
5.  backend/app/application/oqi_remediation_service.py
6.  backend/app/infrastructure/persistence/oqi_remediation_repository.py
7.  backend/app/infrastructure/persistence/models/oqi_remediation.py
8.  backend/app/api/oqi/schemas.py
9.  backend/app/api/oqi/router.py
10. backend/app/application/oqi_product_experience_service.py
11. backend/app/application/entity_resolution_steward_api.py
12. backend/app/api/entity_resolution/router.py
```

Frontend production (8):

```
13. frontend/lib/auth/config.ts
14. frontend/lib/oqi/api-client.ts
15. frontend/lib/oqi/contracts.ts
16. frontend/app/quality/findings/[findingId]/_components/remediation-panel.tsx
17. frontend/app/quality/findings/[findingId]/page.tsx
18. frontend/app/quality/findings/[findingId]/_components/evidence-panel.tsx
19. frontend/lib/entity-resolution/contracts.ts
20. frontend/lib/entity-resolution/api-client.ts
```

Backend test (5):

```
21. backend/app/tests/test_production_remediation_orchestration_postgres.py
22. backend/app/tests/test_oqi_api_postgres.py
23. backend/app/tests/test_entity_resolution_steward_api_postgres.py
24. backend/app/tests/test_entity_resolution_steward_router.py
25. backend/app/tests/test_entity_resolution_tenant_isolation.py
```

Frontend test (2):

```
26. frontend/tests/oqi-remediation-actions.test.tsx
27. frontend/tests/oqi-finding-detail.test.tsx
```

### 7.3 VERIFY ONLY (1)

```
28. frontend/app/quality/findings/[findingId]/_components/remediation-stepper.tsx
    Reads only case_status; implementation must confirm this remains true and unaffected by the plural
    candidate change before treating it as untouched. If verification proves an edit is genuinely required:
    STOP, return to governance -- no edit to this file is authorized by this amendment.
```

### 7.4 PROHIBITED (explicit, non-exhaustive, restated from G-R3 §27.5, unchanged)

```
keycloak/ctec-realm.json
backend/app/application/entity_resolution_steward_api.py's queue()/QUEUE_OUTCOMES/list_cases/get_case()
  bodies (the file itself is MODIFY-authorized in §7.2 for one additive method only, §5 of G-R3)
backend/app/infrastructure/persistence/migrations/versions/0047_oqi_h6_uniqueness.py or any earlier migration
any DemoOqiSeeder file
any agent code path
docs/demo/NOETVA-GOLDEN-DEMO-RUNBOOK.md
PR #250, #249, #248
product/noetva-demo-readiness-final, -i-r2, -r1 (and their exact SHAs)
```

### 7.5 DELETE (0)

No path is authorized for deletion.

## 8. Count consistency — narrative

```
CREATE       = 3
MODIFY       = 24  (9 backend production + 8 frontend production + 5 backend test + 2 frontend test)
VERIFY ONLY  = 1
DELETE       = 0
TOTAL        = 28
```

## 9. Independent recount from the literal table (§7)

Counting the numbered entries directly: §7.1 lists items 1–3 (3 items). §7.2 lists items 4–27 (24 items: 9 +
8 + 5 + 2 = 24). §7.3 lists item 28 (1 item). §7.5 lists zero items. **3 + 24 + 1 + 0 = 28**, matching §8
exactly, and matching the highest item number (28) in the consecutively-numbered table. No path appears in
more than one category — independently re-checked by scanning §7.1–§7.3 for duplicate path strings; none
found.

## 10. Implementation composition contract — unchanged from G-R3, restated

The future implementation phase (`NOETVA-GOLDEN-SIGNATURE-UX-I`) must construct its new candidate from
exactly `b254372b9632c0bd16174678e2ba7f2afd95688c` plus this amendment's own governance commit plus G-R3's own
governance commit (both cherry-picked in sequence, mirroring `NOETVA-CI-BACKEND-ISOLATION-I-R1`'s own proven
composition method), then implement **only** the 28 literal paths in §7 — no path outside this exact,
closed set, and no further "or equivalent" resolution left to implementation's own judgment. `product/
noetva-demo-readiness-final` and PR #250 are not advanced; a new PR is required.

## 11. Authorization

This amendment is approved and published as a standalone governance artifact, following this program's
established convention of never silently rewriting an already-approved Artifact Authorization in place.
`CDD-085-Noetva-Demo-Readiness-Golden-Story-Architecture.md`, its original companion Artifact Authorization,
its G-R1, G-R2, and G-R3 amendments, `CDD-086-Generic-Finding-Detail-Parity.md`, and its own companion
Artifact Authorization all remain FROZEN, unmodified, and fully authoritative. G-R3's own architecture is
unchanged in every particular; this amendment's sole effect is resolving its disclosed path ambiguity into
the exact, fully self-consistent, independently-recounted 28-path table in §7. No implementation write
against any path has occurred as part of this amendment. Implementation readiness is reauthorized to resume,
under the identifier `NOETVA-GOLDEN-SIGNATURE-UX-I`, bound to exactly the 28 paths in §7 and no others.
