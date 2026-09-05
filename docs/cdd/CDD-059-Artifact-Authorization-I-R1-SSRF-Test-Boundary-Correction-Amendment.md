# CDD-059 Artifact Authorization — I-R1 SSRF Test-Boundary Correction Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-048-Artifact-Authorization-OQI-H2-I-R1-Governance-Reconciliation-and-Verification-Hardening-Amendment.md`
(the direct precedent for this exact shape — a standalone companion document correcting a stopped VM's
findings without reopening or rewriting the original frozen CDD/Artifact Authorization); `CDD-050-Artifact-
Authorization-H4-R1-Reference-Tenant-Isolation-Correction-Amendment.md` (the direct precedent for a security-
hardening-specific R1 correction).
Classification: GOVERNANCE CORRECTION ONLY — one structural security-boundary correction (SSRF test-fixture
reachability), one retroactive path authorization (mechanical domain-class-allowlist synchronization), one
wording correction (historical migration table-count instructions), one test-design correction (replay-crown
clock semantics). No architectural or semantic change to CDD-059. No implementation performed by this
document. No merge authorized by this document.

## 1. Purpose

`REAL-ENTERPRISE-INGESTION-VM` independently verified, attacked, and stopped candidate
`real-enterprise-ingestion/rest-connector` at `14cf0f2a803b47580e457f4737ecfd391120471b` — **NO MERGE** —
citing one P1 security defect and one unauthorized-path governance violation, plus two lesser, non-blocking
findings. This amendment corrects exactly those four findings, and only those four, so a subsequent narrow
`REAL-ENTERPRISE-INGESTION-I-R1` may implement the smallest safe correction against the stopped candidate.
CDD-059's architecture, evidence semantics, tenant model, transaction boundaries, concurrency handling, and
every invariant not named below remain frozen, unchanged, and unquestioned.

## 2. Independent re-verification of authoritative state (binding)

Freshly re-confirmed, not trusted from the VM report:
```
origin/main == GitHub main == 5d59eec14f7248e543b806c840d2199c3f66e131
candidate local == candidate origin == GitHub candidate == 14cf0f2a803b47580e457f4737ecfd391120471b
no PR exists for real-enterprise-ingestion/rest-connector (gh pr list --state all: empty)
working tree clean except the pre-existing, unrelated, untracked docs/product/ (predates this program)
```
Neither `main` nor the candidate head moved since VM's own report. Governance publication commit
`80224fb01bb98af1db7aa750f9f85af198c281cf` unchanged.

## 3. Independent re-verification of original governance hashes (binding)

```
docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion.md
    6a8be98707ddf13e5428c2b67b00328eefab1556decc40a7203b12ded5daa055  -- matches, unchanged

docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion-Artifact-Authorization.md
    431300c64689e2eea6fde4e44121bda5b6af25f869a9fa60f3b7ebda8ceb6e37  -- matches, unchanged
```
Neither original document is modified by this amendment. This amendment is a standalone companion, exactly
the pattern `CDD-047`/`CDD-048`'s own R1 amendments established and CDD-050's H4-R1 amendment repeated.

## 4. VM findings independently re-derived (not accepted on the VM report's word)

**R1-A (SSRF).** Independently re-read `backend/app/infrastructure/connectors/rest_connector.py` at
`14cf0f2`: `_test_allowed_addresses()` reads `os.environ.get("CTEC_CONNECTOR_TEST_ALLOWED_ADDRESSES", "")`
unconditionally — no `settings.environment` check, no build/test-profile gate, nothing distinguishing a
production process from a test process at the code level. Independently re-ran the exact adversarial probe
(DNS resolution monkeypatched to `169.254.169.254`, the allowlist env var set to that same address): the
policy **allows** it. Confirmed. This is a genuine, structural defect, exactly as VM found — not a
misclassification.

**R1-B (`test_domain_foundation.py`).** Independently re-diffed `5d59eec..14cf0f2` for this file: exactly
five class-name literals added (`ConnectorFailureKind`, `ConnectorRecord`, `ConnectorPage`,
`ConnectorFetchFailure`, `EnterpriseConnector`) to an existing exhaustive allowlist, nothing else touched.
Independently re-confirmed this file appears nowhere in the original Artifact Authorization's 28-path table
and nowhere in its §3 prohibitions either — it is simply absent, and §2's own text ("No path beyond these 28
is authorized") makes that absence a violation regardless of substantive benignness. Confirmed, not
misclassified.

**R1-C (historical table counts).** Independently re-diffed both files: `test_oqi_business_impact.py`'s
`test_r3tim01_to_m03_migration_round_trip` and `test_oqi_ontology_impact_postgres.py`'s
`test_oqi4r1ti10_migration_upgrade_after_downgrade_restores_protected_schema` each contain exactly one
`assert _table_count() == 123` line **left unchanged** (immediately following a `alembic.command.downgrade`
to a named pre-0044/0045 revision), bracketed by two other `123 -> 126` occurrences in the same function that
**were** changed (the at-head assertions before and after). Independently re-ran both tests as committed: both
pass. Independently reproduced the AA's literal instruction ("123 -> 126, no other line changes") applied to
the middle assertion too: both tests then fail with `assert 123 == 126`-shaped errors, confirming the
literal instruction is factually wrong for these two specific occurrences. Confirmed, not misclassified. **No
file content in either test requires any further change** — the candidate is already semantically correct;
only the AA's own wording requires correction (§8 below).

**R1-D (replay crown).** Independently re-read `test_replay_crown_identical_response_twice_converges` in
`test_oqi_connector_ingestion_postgres.py`: both runs use `_service(session)`, which binds
`clock=lambda: NOW` (a fixed module-level constant) for both calls, and the fixture record carries no
`__observed_at__` key (forcing the `run_started_at` fallback, CDD-059 §10). The test's own inline comment
concedes a fixed clock is required to force the appearance of convergence. Independently re-verified,
against the actual production code with two real, distinct `datetime.now(UTC)` clock values ~1.2s apart
(never a fixed constant): (a) with a genuine per-record `__observed_at__`, two separate runs converge to
exactly one evidence row, `evidence_written`/`duplicate_records` = (1,0) then (0,1) — genuine cross-run
idempotence, independent of any clock artifice; (b) without a per-record timestamp, two separate runs produce
exactly two evidence rows, (1,0) then (1,0) — genuinely new evidence each run, exactly as CDD-059 §10 itself
discloses as an accepted, non-defective consequence. **Production code is correct in both scenarios.** The
shipped test demonstrates neither scenario faithfully; it demonstrates a third, artificial hybrid that would
not occur under a real deployment clock. Confirmed as a test-design gap, not a production or governance
defect, and not merge-blocking on its own — corrected here because it fits cleanly within an already-
authorized file and R1's own explicit mandate (§22 of the governing prompt).

No VM finding was found to be a misclassification. All four proceed to correction below.

## 5. R1 scope boundary (binding, exhaustive)

This amendment governs exactly:
```
1. SSRF test-fixture reachability boundary (structural correction)
2. test_domain_foundation.py authorization (retroactive, mechanical, exact)
3. historical migration table-count instruction wording (correction, zero file bytes)
4. replay-crown test design (two explicit scenarios, real-clock semantics)
```
No other capability work is authorized or implied. OAuth2, Basic auth, mTLS, custom enterprise CA, any
scheduler/CDC/webhook mechanism, any frontend path, any LLM/agent wiring, any correspondence/SemanticMapping
production-creation path, any remediation or evaluation-chain change, and any evidence-schema or tenant-model
change all remain exactly as CDD-059 froze them — untouched, unauthorized, unquestioned.

## 6. R1-A — corrected SSRF architecture (binding, exact)

### 6.1 Governing principle

```
TEST FIXTURE REACHABILITY != GENERAL SSRF EXCEPTION
ENVIRONMENT VARIABLE PRESENCE != TEST MODE
NO PRODUCTION-CONSTRUCTIBLE CODE PATH MAY DISABLE PRIVATE/LOOPBACK/METADATA DESTINATION PROTECTION
```

### 6.2 Structural design (binding, exact — I-R1 must implement exactly this shape)

```python
class EndpointSecurityPolicy(Protocol):
    def validate(self, url: str) -> None: ...   # raises SSRFRejected

class ProductionEndpointSecurityPolicy:
    """The ONLY policy any production code path may construct. Reads no
    environment variable. Behaviorally identical to CDD-059 SS32 as
    originally frozen: scheme + fresh-DNS-resolution + full-address-set
    range check against every prohibited range, zero exceptions."""
    def validate(self, url: str) -> None: ...

class FixtureEndpointSecurityPolicy:
    """TEST-ONLY. Never imported or constructed by any production module
    (backend/app/api/**, backend/app/application/connector_ingestion_service.py's
    own default wiring, backend/app/core/dependency_container.py). Constructed
    exclusively by test code, which itself reads whatever env var/fixture
    configuration it likes and passes the result in as a plain, immutable
    constructor argument -- this class itself never touches os.environ."""
    def __init__(self, *, allowed_addresses: frozenset[str]) -> None: ...
    def validate(self, url: str) -> None:
        # Identical resolution + range-check logic to Production, with
        # exactly one exception: a resolved address that is BOTH loopback-
        # or-private(RFC1918)/IPv6-unique-local AND an exact string match
        # in `allowed_addresses` is permitted. Link-local (169.254.0.0/16
        # and fe80::/10 -- this range subsumes every cloud metadata
        # address of every vendor), multicast, reserved, and unspecified
        # remain UNCONDITIONALLY denied regardless of `allowed_addresses`
        # content -- §6.5 below. CIDR, hostname, and wildcard entries in
        # `allowed_addresses` have no effect (exact resolved-IP-string
        # match only, mirroring the original SS32 exact-match design).
```

`RestConnector.__init__` gains one new keyword-only parameter,
`endpoint_security_policy: EndpointSecurityPolicy = ProductionEndpointSecurityPolicy()`, used for **both** the
initial endpoint (construction time) and every subsequent next-link (pagination time) — replacing every
existing call to the current module-level `validate_endpoint_url` function with
`self._endpoint_security_policy.validate(url)`. `ConnectorIngestionService.__init__` gains the identical
optional parameter, defaulting to `ProductionEndpointSecurityPolicy()`, threaded through to both its own
config-time endpoint check (`configure_connector`) and to the `RestConnector` it constructs inside
`run_connector` — the same policy instance/type is used at both checkpoints CDD-059 SS32 point 5 requires.

### 6.3 Production construction boundary (binding, exact — the central invariant)

`backend/app/api/oqi_connector/router.py`'s `connector_ingestion_service` dependency provider constructs
`ConnectorIngestionService(session)` with **no** `endpoint_security_policy` argument, today and after I-R1 —
confirmed by direct inspection this is the *only* production construction site for `ConnectorIngestionService`
in the entire authorized API surface. Because the parameter defaults to `ProductionEndpointSecurityPolicy()`
and no production file constructs it any other way, **no runtime configuration, environment variable, or
request payload can ever cause the production process to use anything but the Production policy.** Obtaining
`FixtureEndpointSecurityPolicy` requires a source-code change (importing and calling it directly) — a
categorically different, far higher bar than "set an environment variable," and one that already implies
arbitrary code execution inside the process, at which point SSRF is no longer the attacker's limiting
constraint. `backend/app/core/dependency_container.py` remains untouched (still authorized-but-unnecessary,
§27 of the governing VM-R1... i.e. this amendment's own §11) — the corrected design requires no change to it,
since the router's own hard-coded construction call is the entire boundary.

### 6.4 Test fixture construction boundary (binding, exact)

Only test code (`backend/app/tests/test_oqi_connector_ingestion_postgres.py`, and any ad hoc VM/CI
verification script that is not itself a repository path) may import `FixtureEndpointSecurityPolicy` and pass
it explicitly into a directly-constructed `ConnectorIngestionService(session,
endpoint_security_policy=FixtureEndpointSecurityPolicy(allowed_addresses=...))`. The `allowed_addresses`
value itself may continue to be sourced from `CTEC_CONNECTOR_TEST_ALLOWED_ADDRESSES` for operator/CI
convenience — but that environment-variable read now happens **only inside test code**, never inside
`rest_connector.py` or any other production module. Post-I-R1, `rest_connector.py` must contain **zero**
references to `CTEC_CONNECTOR_TEST_ALLOWED_ADDRESSES` — this is a binding, directly-verifiable (`grep`)
acceptance criterion for I-R1/VM-R1.

### 6.5 Absolute-deny destinations (binding, exact)

Even with an active `FixtureEndpointSecurityPolicy` and a matching entry in `allowed_addresses`, the following
remain **unconditionally prohibited, with no exception mechanism of any kind**:
```
169.254.0.0/16   (link-local -- subsumes every cloud metadata address: AWS/GCP 169.254.169.254,
                  Azure IMDS 169.254.169.254, and any other vendor's link-local-hosted metadata service)
fe80::/10        (IPv6 link-local, same rationale)
224.0.0.0/4, ff00::/8   (multicast)
240.0.0.0/4      (reserved)
0.0.0.0/8, ::    (unspecified)
```
Only loopback (`127.0.0.0/8`, `::1/128`) and RFC1918-private/IPv6-unique-local (`10.0.0.0/8`,
`172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`) may ever be exempted, and only by an exact resolved-address
match against `allowed_addresses` — because those are the only ranges the mandated Docker-bridge and host-
loopback fixture topologies actually use (Artifact Authorization §8); the fixture has no legitimate reason to
ever occupy a link-local, multicast, reserved, or unspecified address, so no exception for those ranges is
ever needed or authorized.

### 6.6 Exact-address-only semantics (binding, restated)

`allowed_addresses` entries are matched by exact resolved-IP-string equality only. No CIDR, no hostname, no
wildcard. A malformed entry has no effect (never crashes, never matches, never silently widens). This
preserves the one genuinely good property of the original mechanism — VM's own attack matrix (CIDR rejected,
hostname rejected, malformed-entry-inert) is carried forward as a regression requirement for I-R1/VM-R1.

### 6.7 Every other SSRF control remains active (binding, restated)

`FixtureEndpointSecurityPolicy` overrides only the address-range decision. It changes nothing about: HTTPS-
only scheme enforcement, TLS certificate verification (`ssl.create_default_context`, always on;
`CTEC_CONNECTOR_TEST_CA_BUNDLE` remains a wholly separate control — §6.9 below), hostname verification,
redirect-following (still disabled unconditionally), fresh-DNS-resolution-per-call, response-size bounds,
timeout bounds, or any pagination/record/field bound.

### 6.8 Redirect and next-link semantics under the fixture policy (binding)

Because `RestConnector` threads the *same* `endpoint_security_policy` instance through both the initial
endpoint and every next-link, a fixture's own next-link is validated by the identical policy — an
`allowed_addresses` set naming exactly one fixture container's address does not become a pivot to any other
destination, approved or not. A next-link pointing at the metadata range, a neighboring unapproved private
address, or any address not in the exact `allowed_addresses` set fails closed exactly as production traffic
would.

### 6.9 TLS/CA separation (restated, unchanged)

`CTEC_CONNECTOR_TEST_CA_BUNDLE` (or its constructor-parameter equivalent) governs *only* which CA the TLS
handshake trusts. It has never controlled, and must never be made to control, which network destinations are
reachable — that is `EndpointSecurityPolicy`'s exclusive concern. This separation already exists in the
candidate and requires no correction; restated here as a binding acceptance criterion so I-R1 does not
conflate the two while implementing §6.2-§6.4.

## 7. R1-A mandatory I-R1/VM-R1 crowns (binding, exact)

```
Crown A -- production/default: no policy override; private address (e.g. 10.0.0.5) -> rejected.
Crown B -- metadata under active fixture policy: FixtureEndpointSecurityPolicy(allowed_addresses={"169.254.169.254"})
           constructed explicitly by test code -> validate() on that exact address STILL rejected (§6.5).
Crown C -- exact fixture, valid cert: FixtureEndpointSecurityPolicy(allowed_addresses={<real fixture IP>});
           genuine HTTPS request to that exact address with a trusted-CA cert -> permitted, genuine 2xx.
Crown D -- neighboring private address: same active fixture policy; a DIFFERENT private address not in
           allowed_addresses -> rejected.
Crown E -- CIDR: allowed_addresses={"10.0.0.0/8"} (deliberately malformed for this mechanism); resolved
           10.0.0.5 -> rejected (no CIDR matching).
Crown F -- redirect: fixture policy active; fixture issues a 3xx to a prohibited destination -> rejected,
           never followed (redirect-disabled is independent of the policy).
Crown G -- next-link pivot: fixture policy active; first page's next-link points at an address outside
           allowed_addresses -> rejected.
Crown H -- production construction: direct inspection (and, where feasible, an import-graph/AST-level
           assertion mirroring test_domain_foundation.py's own technique) proving no file under
           backend/app/api/**, backend/app/core/dependency_container.py, or
           connector_ingestion_service.py's own default parameter value can construct or receive a
           FixtureEndpointSecurityPolicy. This is the single most important crown in this amendment.
```

## 8. R1-B — `test_domain_foundation.py` authorization (binding, exact)

`backend/app/tests/test_domain_foundation.py` is retroactively authorized as **MODIFY**, for exactly one
purpose: adding the five exact class-name literals already present in the candidate's own diff (§4 above) to
the pre-existing exhaustive allowed-class set. No other change to this file is authorized: not the removal of
any existing class name, not any loosening of the "no forbidden imports" half of the same test, not any
change to the five canonical domain roots it scans, and no wildcard/pattern-based acceptance replacing the
exhaustive literal set. I-R1 must re-diff this file against `14cf0f2` and confirm byte-for-byte identity with
the already-committed change (no new content is required — the candidate's own version of this file is
already exactly correct and is carried forward unchanged into I-R1).

## 9. R1-C — historical table-count wording correction (binding, exact)

The original Artifact Authorization's items 21-28 read: *"Mechanical only: identical `123` -> `126`
table-count-literal bump. No other line changes."* This is corrected, for exactly the two affected items
(24: `test_oqi_business_impact.py`; 26: `test_oqi_ontology_impact_postgres.py`), to:

> Mechanical for every **current-head** table-count assertion in this file: `123` -> `126`. **Exception**: any
> assertion checking table count immediately after an `alembic.command.downgrade(...)` to a named revision
> older than `0044_oqi4_r1_current_tenancy` must remain at its correct historical value for that revision (do
> not bump) — that boundary is unaffected by migrations 0044/0045 and a mechanical bump would assert a
> falsehood. Verify each occurrence's own surrounding context before applying the literal; do not pattern-
> match the bare digits.

This corrects the governing instruction's own wording only. It does not require, and does not authorize, any
further change to either file's actual content — both are already correct on the candidate (§4 above). Items
21, 22, 23, 25, 27, 28 are unaffected (independently re-confirmed each contains no historical-revision-
boundary assertion of this kind; every occurrence in those six files is a current-head check, correctly
bumped as originally instructed).

## 10. R1-D — replay-crown test design (binding, exact)

`backend/app/tests/test_oqi_connector_ingestion_postgres.py` (already CREATE-authorized, carried forward) is
corrected to freeze two explicit, separately-named replay scenarios, replacing the single fixed-clock
`test_replay_crown_identical_response_twice_converges`:

**Scenario 1 — source-timestamp replay (genuine cross-run idempotence).** A fixture record carrying a real
per-record `__observed_at__` value. Two connector runs, each constructed with its own genuinely distinct clock
value (a real advancing clock, or at minimum two explicit, textually-different `datetime` literals — never
the same fixed constant reused for both runs). Required: run 1 `evidence_written=1`/`duplicate_records=0`;
run 2 `evidence_written=0`/`duplicate_records=1`; exactly one total evidence row. This is the genuine replay-
safety proof CDD-059 §9 requires.

**Scenario 2 — no-source-timestamp observation (NOT a replay defect).** A fixture record carrying no
`__observed_at__` value. Two connector runs, each with its own genuinely distinct clock value. Required: run 1
`evidence_written=1`; run 2 **also** `evidence_written=1` (not a duplicate); exactly two total, immutable
evidence rows, distinguished by their own distinct `observed_at`. The test must state explicitly, in its own
name and an inline comment, that this is CDD-059 §10's own disclosed, accepted consequence of a source with
no real event-time concept — never framed as, or confused with, a replay-safety failure.

Both scenarios must use genuinely distinct clock values between their two runs (a real clock, or two
explicit literals differing by a non-trivial interval) — never the shared fixed `NOW` constant reused
unchanged for both calls, which is what made the original single test's convergence an artifact of test
construction rather than proof of either governed behavior.

## 11. Exact I-R1 authorized path set (binding — a maximum permitted write set, Model A, per the original
Artifact Authorization's own §2 framing, carried forward unchanged for this amendment)

```
CREATE = 0
MODIFY = 3
DELETE = 0
TOTAL  = 3
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | MODIFY | `backend/app/infrastructure/connectors/rest_connector.py` | Introduce `EndpointSecurityPolicy`/`ProductionEndpointSecurityPolicy` (§6.2); `RestConnector.__init__` gains the `endpoint_security_policy` parameter (§6.2); remove the module-level `validate_endpoint_url` function and its own `os.environ.get("CTEC_CONNECTOR_TEST_ALLOWED_ADDRESSES", ...)` read entirely (§6.4) — post-change, this file must contain zero references to that environment variable. `FixtureEndpointSecurityPolicy` is NOT defined here (test-only, §6.4) — it belongs in item 3. |
| 2 | MODIFY | `backend/app/application/connector_ingestion_service.py` | `ConnectorIngestionService.__init__` gains the optional `endpoint_security_policy` parameter, defaulting to `ProductionEndpointSecurityPolicy()` (§6.2), threaded through both `configure_connector`'s config-time check and `run_connector`'s `RestConnector` construction. No other change. |
| 3 | MODIFY | `backend/app/tests/test_oqi_connector_ingestion_postgres.py` | Defines `FixtureEndpointSecurityPolicy` (test-only, §6.2/§6.4) and constructs it explicitly wherever a real-network crown currently relies on the removed environment-variable mechanism; implements Crowns A-H (§7); implements the corrected replay scenarios (§10); carries forward the already-correct `test_domain_foundation.py` change unchanged (§8, that file itself requires no further edit — it is already correct on the candidate and is not touched again by I-R1). |

No path beyond these 3 is authorized. `backend/app/tests/test_domain_foundation.py`,
`backend/app/tests/test_oqi_business_impact.py`, and `backend/app/tests/test_oqi_ontology_impact_postgres.py`
require **zero** further byte changes — their current (candidate) content is already correct and is carried
forward unchanged; they are retroactively authorized (§8) or textually reconciled (§9) by this amendment
without requiring I-R1 to touch them again. `backend/app/core/dependency_container.py` remains untouched
(§6.3) — the corrected design requires no wiring change. No migration path is authorized or required (§13 of
the governing prompt; confirmed independently, §6 above introduces zero schema impact).

## 12. Prohibited paths (restated, unchanged from the original Artifact Authorization, binding)

Every prohibition in the original document's §3 remains in full force, unchanged: no path under
`backend/app/domain/oqi*`, no evaluation/remediation service file, no existing OQI7 router/schemas/
dependencies, no migration other than the already-existing `0045_oqi_connector_ingestion` (none new, none
modified), no ORM model file, no frontend path, no `Dockerfile`/`docker-entrypoint.sh`, no prior CDD or its
Artifact Authorization, no delete of any kind, no refactor of `FieldValueEvidenceRepositoryImpl` or
`SourceFieldRepositoryImpl` beyond what was already carried forward. Additionally prohibited for I-R1
specifically: any change to `docker-compose.yml`, `keycloak/ctec-realm.json`, or `backend/app/main.py` (all
three already correctly authorized-and-implemented by the original candidate; this amendment finds no defect
in any of them).

## 13. I-R1 STOP conditions (binding, exhaustive)

I-R1 must STOP and report rather than improvise if:
```
original CDD-059 or Artifact Authorization hashes drift from §3
this amendment's own hash (§16) drifts once published
a path beyond the exact 3 in §11 is found necessary
production API/router/service construction is found to retain any path (direct or indirect, including a
    default-parameter value reachable from production wiring) for supplying/activating
    FixtureEndpointSecurityPolicy
169.254.169.254 or any other link-local/multicast/reserved/unspecified address can be authorized through
    FixtureEndpointSecurityPolicy under any allowed_addresses content
a non-exact-match mechanism (CIDR, hostname, wildcard) is found to work
a redirect or next-link bypass is found to work under an active fixture policy
TLS/hostname verification is weakened anywhere, for any reason
the Docker fixture crown requires any production-facing SSRF exception beyond §6.2-§6.5
test_domain_foundation.py's forbidden-import half is found to require any weakening
either historical table-count assertion (§9) is found to require a value other than 123
either replay scenario (§10) cannot be made to pass with genuinely distinct clock values
any previously-green tenant, concurrency, evidence, or accounting crown regresses
any new P0/P1 is discovered
```

## 14. Carried-forward invariants (restated, binding, unchanged)

Migration remains exactly `0045_oqi_connector_ingestion`, single head, 126 tables — no schema change
authorized or required. Composite tenant-qualified FKs, the `SourceField` two-hop tenant-authority proof, and
`TrustedPrincipal` as sole tenant authority are unchanged and untouched. The `SAVEPOINT`-based concurrency
correction VM found sound is unchanged and carried forward as regression protection (its own crown remains
mandatory for VM-R1). The Production Evaluation boundary (`connector → evidence → stop`; `/oqi/evaluate`
separate and unmodified) is unchanged. The full original deferred register (CDD-059 §54) is carried forward
unchanged, including the still-open "zero genuine production enterprise connectors" capability gap — not
removable except by a future connector VM's own successful, independent closure.

## 15. No architecture change / no scope expansion (restated)

Nothing in this amendment adds, removes, or reinterprets any CDD-059 architectural decision, evidence
semantic, transaction boundary, or API contract. Every correction here is either a structural security-
boundary fix confined to exactly 3 already-authorized-or-owned files, a retroactive authorization of an
already-necessary, already-disclosed mechanical change, a wording correction to the governing document itself
(zero implementation bytes), or a test-design correction within an already-authorized test file.

## 16. Governance byte-integrity / hash chain (binding)

```
Original CDD-059:                    6a8be98707ddf13e5428c2b67b00328eefab1556decc40a7203b12ded5daa055
Original Artifact Authorization:     431300c64689e2eea6fde4e44121bda5b6af25f869a9fa60f3b7ebda8ceb6e37
This amendment's own hash:           computed and recorded at publication time, immediately below this line,
                                      by the publishing phase itself (this document does not self-hash).
```
Neither original document is modified by this amendment. I-R1 must bind its own work to all three hashes
(the two originals, unchanged, plus this amendment's own) and STOP if any drifts (§13).

## 17. P0/P1/P2/P3 (before this amendment; the condition this amendment corrects)

P0 = 0. P1 = 1 (R1-A, corrected by §6-§7). P2 = 2 (R1-B, corrected by §8; R1-C, corrected by §9) + 1 test-
design gap (R1-D, corrected by §10). P3 = 0 (no change to the deferred register, §14).

## 18. Authorization

This amendment is approved and published as the governance basis for
`REAL-ENTERPRISE-INGESTION-I-R1`. Implementation against §11's exact 3-path set is authorized only after this
document's own publication and hash computation. `REAL-ENTERPRISE-INGESTION-VM-R1` must independently re-
attack every crown named in §7 and every carried-forward invariant in §14 before any merge may be considered
— this amendment authorizes correction, not merge.
