# CDD-065 — Azure Entra OIDC Tenant-Claim R2 Correction Amendment

**Status:** FROZEN
**Originating phase:** AZURE-DEV-ENTRA-TENANT-CLAIM-R2 (DRG → I → VM-PREDEPLOY → VM-RUNTIME)
**Amends:** CDD-064 (`docs/cdd/CDD-064-Azure-Entra-OIDC-Tenant-Claim-Artifact-Authorization.md`, SHA-256 `aacb6574fcca8576bb6d60081d00ce20fa9bd5fd280527f20f92d92edc82d787`, commit `48a8602a55700ff2eace0863d49dcf3b4e156ec3`, PR #208, OPEN, not merged)
**Scope:** Corrects exactly one invalidated architectural assumption in CDD-064 — that a `Namespace` field lets the restricted outgoing claim name `tenant_id` be saved. Real Microsoft Entra evidence disproves this. Everything else CDD-064 froze (parser decision, Bicep parameter/env-var shape, security invariants, two-stage verification model, R1/R2-scope-claim non-regression) remains valid and is not reopened.

---

## 1. Authoritative baseline at freeze

Main SHA: `e0188319236bd96711331538a6efacc2d0d4fb40` — independently re-verified against `origin/main` and GitHub `main`. CDD-064 (PR #208, commit `48a8602a`) and its R1 implementation (PR #209, commit `68aaab702821941a2273e2ee5b5840eeada341b2`) both re-confirmed OPEN, `mergeable`, unmerged, at their expected head SHAs. Neither PR is touched by this document.

## 2. New real-Azure evidence

The operator attempted the exact CDD-064 §4 mechanism: `Enterprise applications → noetva-dev-backend-api → OIDC-based Sign-on → Attributes & Claims → Manage claim`, with **Name** `tenant_id`, **Namespace** `https://noetva.ai/claims`, **Source** Directory schema extension. Azure **still** displays "This claim type is restricted" and Save remains disabled. No claim was saved. The pre-existing directory attribute `tenant_id` was not touched.

## 3. Root cause reconciliation (supersedes CDD-064 §3's namespace conclusion)

CDD-064 §3 correctly identified `tenant_id` as a permanent member of Microsoft's JWT restricted claim set. It incorrectly inferred, from the documentation phrase *"if you need a URI pattern, you can put that in the Namespace field,"* that supplying a Namespace produces a compound identifier no longer literally equal to the restricted string, and would therefore escape the restriction. **Real Azure evidence disproves this inference.** Independent re-verification (Microsoft Q&A guidance on an equivalent restricted-claim scenario, group claims) confirms the actual, documented mechanics: *"If you select a restricted name for the name of your custom group claim, the claim will be ignored [or rejected] at runtime"* — the restriction check is evaluated against the literal **Name** field itself, independent of whatever Namespace is supplied alongside it. A Namespace changes how the claim is *displayed/prefixed*; it does not change whether the underlying **Name** is on the restricted list. This is now empirically confirmed, not merely inferred.

**Correction:** the fix is not to wrap the restricted name in a namespace — it is to **stop naming the outgoing claim `tenant_id` at all** and use a different, non-restricted **Name** instead. Everything else about the restriction (permanent, no custom-signing-key override, platform-wide, applies identically via the portal UI or a Microsoft Graph `claimsMappingPolicy`) remains exactly as CDD-064 §3 stated and is not superseded.

## 4. Final Microsoft-supported access-token mechanism (confirms CDD-064 §6 mechanism unchanged; supersedes only the claim-name assumption)

Independently re-verified via Microsoft Learn's "Directory extension attributes in claims" reference, which gives the literal, authoritative claims-mapping-policy shape for exactly this scenario:

```json
{
    "ClaimsMappingPolicy": {
        "Version": 1,
        "IncludeBasicClaimSet": "false",
        "ClaimsSchema": [{
                "Source": "User",
                "ExtensionID": "extension_xxxxxxx_test",
                "JWTClaimType": "http://schemas.contoso.com/identity/claims/exampleclaim"
            }
        ]
    }
}
```

This confirms, from Microsoft's own reference example, that **`ExtensionID` (the source directory attribute) and `JWTClaimType` (the outgoing claim name) are two independent, separately-named fields of the same claim-schema entry.** The `JWTClaimType` in Microsoft's own example is not restricted-list text and is not required to match the source attribute's name. The Enterprise Application **Attributes & Claims** portal UI (the mechanism CDD-064 already used, and the mechanism the real evidence in §2 was obtained through) is a UI layer over this exact same underlying policy object — it enforces the identical restricted-claim-set check (confirmed in CDD-064 §3 and reconfirmed here), and is GA, not preview. A raw Microsoft Graph `claimsMappingPolicy` would be subject to the identical restriction (the restriction is documented against `ClaimsSchema`/`JwtClaimType` itself, not against the portal UI specifically) and offers no advantage here — switching to it is **not warranted** and is **not authorized** by this artifact. The portal-UI mechanism, unchanged from CDD-064, remains the governed mechanism.

**Mechanism verdict: unchanged from CDD-064 §6.** Configure on `noetva-dev-backend-api`'s own Enterprise Application entry (the resource/API service principal, audience `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`) — never the frontend's. This remains correct and is not reopened.

## 5. Final outgoing JWT claim name

**Frozen: `noetva_tenant_id`.** Verified directly against the complete Microsoft Entra JWT restricted claim set (independently re-fetched in full from Microsoft Learn's "Claims customization" reference in this same investigation) — `noetva_tenant_id` does not appear anywhere in that list, and does not begin with the separately-restricted `xms_` prefix. It is a plain, non-URI identifier, consistent with the documented statement that a claim name *"doesn't strictly need to follow a URI pattern"* — no `Namespace` field is required or authorized for this claim (leave it empty in the portal).

**Why this may be frozen as a concrete literal now, unlike CDD-064's placeholder:** CDD-064's uncertainty was about an unpredictable *concatenation* (Namespace + Name → some unknown compound string Entra would render, an assumption that in fact never even saved). Here there is no concatenation to predict: with Namespace left empty, the outgoing claim key **is** the literal Name value, verbatim — Noetva is choosing this string, not waiting to observe what Entra derives from two inputs. The only fact that still requires real-Azure confirmation (Stage 2, §17) is that the portal **accepts and saves** this specific non-restricted name (expected, based on the restricted-list check being a literal-match against `tenant_id` and its listed neighbors, none of which is `noetva_tenant_id`) and that the resulting real access token actually carries it.

## 6. Directory extension source (supersedes nothing; reaffirms CDD-064 §5)

The existing custom directory attribute `tenant_id` (already created, per real-Azure evidence; not deleted or mutated by any phase to date) remains the correct, unchanged **source**. Per §4's Microsoft reference, its internal `ExtensionID` takes the form `extension_<b2c-extensions-app-appId-no-dashes>_tenant_id`. **This value is never guessed or hand-typed by Noetva engineering or by this artifact.** The Enterprise Application Attributes & Claims portal UI resolves it automatically when the operator selects **Source → Directory schema extension → Application `b2c-extensions-app` → attribute `tenant_id`** from its own dropdown (exactly CDD-064 Step 22.1/22.2's existing procedure) — the operator never needs to know or type the literal `extension_...` string. If a future phase ever needs the literal string directly (e.g., to author a raw Microsoft Graph `claimsMappingPolicy` instead of using the portal UI — not authorized by this artifact), the safe, non-guessing method is `GET https://graph.microsoft.com/v1.0/applications/{b2c-extensions-app-object-id}/extensionProperties` via Microsoft Graph, never invention.

## 7. Backend compatibility (reaffirms CDD-064 §7, unchanged)

`backend/app/core/config.py`'s `oidc_tenant_claim: str = "tenant_id"` and `backend/app/api/supplier_risk/authentication.py`'s `claims.get(self._settings.oidc_tenant_claim)` require no change: a flat-dict lookup by an arbitrary string key already handles `noetva_tenant_id` exactly as it would have handled any namespaced URI string, or `tenant_id` itself. **No production parser or config-schema change is authorized or required by this correction**, exactly as CDD-064 concluded.

## 8. Bicep / runtime configuration (supersedes CDD-064 §8's placeholder instruction only)

The `oidcTenantClaim` Bicep parameter and `CTEC_OIDC_TENANT_CLAIM` env-var wiring, already implemented in PR #209 exactly per CDD-064 §8's structural shape (parameter declaration, module forwarding, `backendEnvVars` entry), **remain correct and are not reopened.**

**Superseded:** the four environment parameter files' value. CDD-064 §8 required the placeholder `REPLACE_WITH_ENTRA_TENANT_CLAIM_NAME` because the namespaced-claim string was unpredictable and, as §2/§3 now show, was never going to work at all. That reasoning no longer applies (§5). **Authorize replacing the placeholder in all four environment parameter files with the concrete literal:**
```json
"oidcTenantClaim": { "value": "noetva_tenant_id" }
```
This mirrors CDD-063's `oidcScopeClaim: "scp"` precedent exactly: a deterministic, Noetva-chosen, non-secret, non-tenant-specific literal, safe to commit to source ahead of the real portal configuration step, with the real-Entra behavior still verified only at Stage 2 (§17) — never assumed operationally proven by Stage 1 alone.

## 9. `acceptMappedClaims` re-verdict (reaffirms CDD-064 §10, unchanged)

Nothing about renaming the outgoing claim from a namespaced string to `noetva_tenant_id` changes the `acceptMappedClaims`/AADSTS501461 analysis: the backend's Application ID URI, `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`, remains in the application-GUID form the rule permits without a custom signing key, for a single-tenant app registration. **`acceptMappedClaims: true` remains required and justified.** `isFallbackPublicClient` remains **rejected** — no new evidence has been presented for it, and CDD-064 §10's finding stands unmodified.

## 10. Tenant-isolation security analysis (reaffirms CDD-064 §9, unchanged)

Nothing in this correction touches how the directory attribute is populated or who controls it. The admin-only assignment path (Users → profile → custom attribute, never the `noetva-dev-signup-signin` self-service flow) is unaffected. No email/header/`tid`/`oid`/`sub`/dual-claim fallback is introduced. The backend's fail-closed behavior on a missing/malformed configured claim is unaffected by which literal claim name is configured.

## 11. R1 implementation (PR #209) disposition

PR #209 remains the correct implementation foundation and is **not superseded**. It requires a narrow follow-up commit on the same branch, changing only:
- the four environment parameter files' `oidcTenantClaim` value (placeholder → `noetva_tenant_id`, §8);
- the representative test claim key used in the six CDD-064-governed tests (from the invalidated namespaced string to `noetva_tenant_id` — same six test *shapes*, same assertions, only the literal changes);
- the deployment guide's Part 22 (correct the "Namespace escapes the restriction" claim to reflect §2/§3's real evidence; change the instructed portal action from Name=`tenant_id`+Namespace to Name=`noetva_tenant_id`+no Namespace; state the frozen literal directly rather than "capture and record" language, since it is now predetermined).

**No new file is authorized.** The exact path set is unchanged from CDD-064 §13 — the same eight files, already modified once by PR #209, each requiring one additional, narrow edit:

```
CREATE = 0
MODIFY = 8
DELETE = 0
```

| # | Path |
|---|---|
| 1 | `infra/azure/main.bicep` *(no change expected; re-verify only)* |
| 2 | `infra/azure/resources.bicep` *(no change expected; re-verify only)* |
| 3 | `infra/azure/environments/dev/main.parameters.json` |
| 4 | `infra/azure/environments/staging/main.parameters.json` |
| 5 | `infra/azure/environments/demo/main.parameters.json` |
| 6 | `infra/azure/environments/prod/main.parameters.json` |
| 7 | `backend/app/tests/test_oidc_authentication.py` |
| 8 | `docs/deployment/azure/NOETVA-AZURE-ZERO-TO-DEPLOYMENT-GUIDE.md` |

**Explicitly prohibited**, unchanged from CDD-064 §13: `backend/app/core/config.py`; `backend/app/api/supplier_risk/authentication.py`; `docker-compose.yml`; `keycloak/ctec-realm.json`; any `frontend/*` path; any `.github/workflows/*` path; any R1(scope-length) or R2(scope-claim, CDD-063) governed value or artifact; any database schema/migration file; CDD-064 or CDD-065 themselves.

## 12. Frozen test contract (supersedes only the literal claim string in CDD-064 §12; test shapes unchanged)

The same six governed test functions already implemented in PR #209 are retained with the same assertions; only the representative claim-key constant changes:
```python
NAMESPACED_TENANT_CLAIM = "https://noetva.ai/claims/tenant_id"  # superseded
```
becomes
```python
AZURE_TENANT_CLAIM = "noetva_tenant_id"
```
(rename the constant for clarity; a plain identifier is no longer "namespaced"). Update each test's use of the old constant and any docstring language describing it as "namespaced" or "representative, pending real capture" — the value is now the actual frozen, Azure-bound literal, not a stand-in. The `tid`-never-substitutes and both-present-only-configured-trusted tests, the missing/ambiguous fail-closed tests, and the local-default/R2-scp regression re-confirmations all carry over unchanged in structure.

## 13. Real-Azure Stage 2 verification requirement (supersedes CDD-064 §17 Stage 2 item 3-4 wording only; all other Stage 2 items carry over)

Decoding the real backend access token must show:
1. `aud` = `api://3a880f13-985d-4a71-be05-20f97b9bcfa3`.
2. `scp` contains the expected delegated scopes (R2/CDD-063, unaffected).
3. `noetva_tenant_id` = `noetva-dev-tenant` (the frozen literal, §5/§8 — no longer an unresolved placeholder to discover).
4. `tid` = `8f9e2dee-5a5b-4b33-9044-4d11691899de`.
5. `tid` is confirmed **not** consulted as the business tenant (the backend reads only `noetva_tenant_id`, per the unchanged parser, §7).
6. The deployed Container App's environment has `CTEC_OIDC_TENANT_CLAIM=noetva_tenant_id` exactly.
7. An authenticated request with the correct claim succeeds, scoped to the correct tenant.
8. A token missing the claim, or carrying an unknown tenant value, is rejected.
9. Cross-tenant isolation is genuinely observed against two distinct real tenant values.

**Only Stage 2 success may declare this correction operationally CLOSED**, exactly per CDD-064 §18's terminology rule (`PASS + SOURCE MERGED — TENANT-CLAIM OPERATIONAL VERIFICATION PENDING AZURE EXECUTION`, never "CLOSED," until Stage 2 succeeds).

## 14. DEV-user assignment and PostgreSQL prerequisite (reaffirms CDD-064 §11 guide content, unchanged)

Unchanged from CDD-064: an administrator sets `tenant_id` = `noetva-dev-tenant` on the first DEV test user's directory profile (Users → New user → custom-attribute section), never via self-service sign-up. A legitimate Noetva application-tenant row for `noetva-dev-tenant` must exist in the DEV PostgreSQL database before the backend will accept that business tenant end-to-end (existing application-authorization-layer behavior, unaffected by this correction, already documented in Part 22.4/Part 34's negative-test table).

## 15. GitHub variable/secret decision (reaffirms CDD-064 §14, unchanged)

No new GitHub Actions variable or secret. `noetva_tenant_id` is non-secret, deterministic, provider-specific configuration naming material, exactly like `scp` (CDD-063) — it belongs solely in the governed environment parameter files.

## 16. Security invariants (binding, unchanged from CDD-064 §15, re-affirmed against this correction)

All 15 invariants in CDD-064 §15 remain binding without modification. This correction changes only which literal string names the outgoing Azure claim; it changes nothing about who controls the underlying value, what happens on a missing/malformed claim, or whether `tid`/`oid`/`sub` may ever substitute.

## 17. Two-stage verification model (binding; Stage 1 items updated for the new literal, Stage 2 per §13)

### Stage 1 — Pre-deployment source certification
1. Exact authorized diff — still the same 8 paths (§11), no ninth path.
2. Bicep unchanged (re-verify only; no edit expected).
3. All four environment parameter files parse and contain `"oidcTenantClaim": { "value": "noetva_tenant_id" }` — placeholder fully resolved, no `REPLACE_WITH_ENTRA_TENANT_CLAIM_NAME` remaining anywhere.
4. `resources.bicep` still genuinely emits `CTEC_OIDC_TENANT_CLAIM` from the parameter (unchanged from R1; re-verify).
5. All 6 tenant-claim tests (§12) pass using the new `AZURE_TENANT_CLAIM` literal.
6. R2(CDD-063) `scp` tests re-confirmed unchanged.
7. Local-default (`tenant_id`) test re-confirmed unchanged.
8. Full backend regression passes (or reproduces only pre-existing, independently-baseline-confirmed failures, exactly as already established in the R1-I phase).
9. `black`/`isort`/`ruff`/`mypy` clean.
10. Frontend regression unaffected (no frontend file in the diff).
11. Local Keycloak/Docker regression unaffected (`docker exec` re-confirms neither `CTEC_OIDC_SCOPE_CLAIM` nor `CTEC_OIDC_TENANT_CLAIM` reaches the local container).
12. GitHub CI green on the exact candidate.
13. R1(scope-length)/R2(scope-claim) non-regression re-confirmed.
14. No unauthorized path in the diff.
15. CDD-064 and CDD-065 both re-verified byte-identical by SHA-256 at every subsequent phase boundary.
16. Placeholder tripwire: zero remaining occurrences of `REPLACE_WITH_ENTRA_TENANT_CLAIM_NAME` anywhere in the repository.

**Stage 1 success authorizes merging the source correction only.**

### Stage 2 — Post-deployment real-Entra certification
Per §13 above. **Only Stage 2 success may declare this correction operationally CLOSED.**

## 18. Exact allowed terminology (unchanged from CDD-064 §18)

> **PASS + SOURCE MERGED — TENANT-CLAIM OPERATIONAL VERIFICATION PENDING AZURE EXECUTION**

Never "CLOSED" until Stage 2 succeeds.

## 19. Frozen phase sequence

```
R2-G (this document, AZURE-DEV-ENTRA-TENANT-CLAIM-R2-DRG)
→ R2-I            (narrow follow-up commit on PR #209's branch: resolve the 4 placeholders to noetva_tenant_id,
                    update the 6 tests' literal, correct the guide's Part 22 portal instructions; Stage 1 verification)
→ R2-VM-PREDEPLOY (adversarially re-verify Stage 1; merge PR #209, and PR #208 auto-merges by ancestry per this
                    repository's established pattern)
→ [Azure/Entra External ID execution — configure Name=noetva_tenant_id, no Namespace, Source=Directory schema
    extension→tenant_id; confirm Save succeeds this time; assign the DEV test user; deploy]
→ R2-VM-RUNTIME    (Stage 2 — the only phase permitted to declare this correction operationally CLOSED)
```

---

*This document authorizes governance only. It does not implement, deploy, or verify anything itself. It amends CDD-064 additively; CDD-064 is not edited in place and remains available in full for historical/audit reference, with §§3, 4 (namespace-escape conclusion), 8 (placeholder instruction), and 12/17 (literal-dependent test/Stage-1 items) superseded exactly as stated above.*
