# CDD-059 Artifact Authorization — I-R2 DNS-Rebinding / Validate-to-Connect IP-Pinning Correction Amendment

Version: 1.0
Status: APPROVED / PUBLISHED / FROZEN
Precedent: `CDD-059-Artifact-Authorization-I-R1-SSRF-Test-Boundary-Correction-Amendment.md` (the direct precedent
for this exact shape — a standalone companion document correcting a stopped VM's findings without reopening
or rewriting any earlier frozen artifact); `CDD-048-Artifact-Authorization-OQI-H2-I-R1-Governance-
Reconciliation-and-Verification-Hardening-Amendment.md` (the program's own established pattern for this kind
of narrow, disclosed, security-hardening correction).
Classification: GOVERNANCE CORRECTION ONLY — one structural transport-architecture correction (destination-
validation/connection binding). No architectural, evidence, tenant, or API change. No implementation
performed by this document. No merge authorized by this document.

## 1. Purpose

`REAL-ENTERPRISE-INGESTION-VM-R1` independently verified the I-R1 SSRF test-boundary correction as sound, but
found a new, independently-reproduced P1: `RestConnector`'s transport validates a destination via one DNS
resolution, then lets `urllib.request`'s own connection machinery perform an **independent second (and third,
and fourth) DNS resolution** to actually open the TCP socket — a classic validate/connect TOCTOU enabling a
DNS-rebinding SSRF bypass. This amendment freezes the smallest correct transport architecture closing that gap
so a subsequent narrow `REAL-ENTERPRISE-INGESTION-I-R2` may implement it. The R1 correction (structural
`EndpointSecurityPolicy` boundary, production/fixture separation, absolute-deny classes) is verified correct
and is **not reopened** by this amendment.

## 2. Independent re-verification of authoritative state (binding)

Freshly re-confirmed, not trusted from the VM-R1 report:
```
origin/main == GitHub main == 5d59eec14f7248e543b806c840d2199c3f66e131
candidate local == candidate origin == GitHub candidate == f9ad6033454311ab2ba40bf5e241c7b3d9334510
working tree clean except the pre-existing, unrelated, untracked docs/product/
```
Neither `main` nor the candidate head moved since VM-R1's own report.

## 3. Independent re-verification of existing governance hashes (binding)

```
docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion.md
    6a8be98707ddf13e5428c2b67b00328eefab1556decc40a7203b12ded5daa055  -- matches, unchanged

docs/cdd/CDD-059-Production-Governed-Enterprise-REST-Ingestion-Artifact-Authorization.md
    431300c64689e2eea6fde4e44121bda5b6af25f869a9fa60f3b7ebda8ceb6e37  -- matches, unchanged

docs/cdd/CDD-059-Artifact-Authorization-I-R1-SSRF-Test-Boundary-Correction-Amendment.md
    96d319a42df00e38a2b38a3c6f0231c07d35542a9dfc9709c175523e68c1e3c1  -- matches, unchanged
```
None of the three is modified by this amendment.

## 4. Independent reproduction of the VM-R1 P1 (binding finding)

Independently reproduced, against the exact candidate `f9ad603`, using a controlled substitute resolver
(never contacting real cloud metadata): a monkeypatched `socket.getaddrinfo` returning a genuinely public-
looking address on its first call and `127.0.0.1` on every subsequent call. Constructing the real
`RestConnector` and calling `fetch_page(page_token=None, ...)` once: the policy's own single `validate()` call
consumed the first (public) answer and passed; the subsequent, independent resolution performed by
`http.client.HTTPSConnection.connect()` (invoked from inside `urllib.request`'s own handler chain, traced via
`traceback.extract_stack()` to `http/client.py:endheaders → _send_output → send → connect → connect →
socket.py:create_connection`) consumed the private answer, and the code proceeded to a genuine TCP connection
attempt against `127.0.0.1:443` (`ConnectionRefusedError`, i.e., a real connection attempt reached that
address — in a real deployment where something listens there, the request would succeed). **Confirmed: not a
VM-R1 misclassification.** The defect is real, structural, and independent of the R1 correction (it exists in
shared transport code regardless of which `EndpointSecurityPolicy` is active).

## 5. Root cause (binding, exact)

```
VALIDATED ADDRESS != CONNECTED ADDRESS
```
`EndpointSecurityPolicy.validate(url)` performs its own `socket.getaddrinfo` and checks the resulting address
set. Separately, `_attempt_fetch` hands the same URL's **hostname string** (never a resolved address) to
`urllib.request`'s opener, which constructs an `http.client.HTTPSConnection` using that hostname; that
connection's own `connect()` method calls `socket.create_connection((host, port), ...)`, which performs its
own, entirely independent `socket.getaddrinfo` at the moment the real socket is opened. Nothing in the
codebase carries the validated address set from the first resolution into the second. This is not a stale-
cache defect, not an insufficient-prohibited-range defect, and not part of the R1 `FixtureEndpointSecurityPolicy`
mechanism — it is a structural gap in how validation and connection are wired together, present since the
original I phase, undetected until this VM-R1 pass.

## 6. R2 central security invariant (binding, exact)

```
FOR EVERY HTTP ATTEMPT (initial endpoint, every next-link, every retry):

    resolve hostname (fresh)
        v
    validate every resolved address (CDD-059 SS32, all-address rule, unchanged)
        v
    select one validated address (SS10 below)
        v
    connect the TCP socket DIRECTLY to that validated address -- never re-resolve the
    hostname for connection purposes
```
No uncontrolled DNS lookup may occur between validation and TCP connect that could change destination
authority.

## 7. Hostname identity survives IP pinning (binding, exact)

Connecting to a literal validated IP must not weaken TLS identity. For a given attempt:
```
logical URL hostname   -> authoritative for: TLS SNI, certificate-hostname verification, HTTP Host header
validated IP address   -> authoritative for: TCP connection destination ONLY
```
A design that verifies the certificate against the validated IP instead of the original hostname is
**not authorized** — it would defeat the entire purpose of using a real enterprise endpoint's own TLS
identity. Investigated and confirmed stdlib-viable (SS24 below): `http.client.HTTPSConnection`'s own
`connect()` method already separates "what address the raw socket connects to" from "what `server_hostname`
is passed to `SSLContext.wrap_socket()`" at the source level — a connection class may be constructed to
target the validated IP for the socket while still passing the original hostname as `server_hostname`.

## 8. All-resolved-address validation semantics (restated, unchanged)

CDD-059 SS32's existing rule is preserved exactly: if resolution returns multiple addresses (e.g., A+AAAA, or
round-robin), **every** resolved address must independently pass policy; if any one fails, the entire URL is
rejected before any connection is attempted. A resolution set of `{public, private}` or `{public, metadata}`
is rejected in full — no partial "pick the safe one and proceed" behavior is authorized.

## 9. Validated-address selection (binding, exact)

After the complete resolution set passes policy (SS8), the connector selects addresses for connection **only
from that same validated set**, in the order `getaddrinfo` returned them (deterministic, matching the order a
correct, unmodified stdlib resolution would naturally try). No address outside this set may ever be used for
connection within the same attempt.

## 10. Connection fallback semantics (binding, exact)

If the connection attempt to the first validated address fails (refused, timeout, unreachable), the connector
may fall back to the **next address already present in the same validated set**, with no new DNS resolution
performed to obtain it. Exhausting the validated set without a successful connection is a genuine
`CONNECTOR_UNAVAILABLE`/`CONNECTOR_TIMEOUT` failure (existing retry/error taxonomy, SS24/SS25 of CDD-059,
unchanged) — never a trigger to re-resolve the hostname within that same attempt.

## 11. No third-party re-resolution (binding, exact — the property that closes the defect)

Once the validated address set is established for an attempt, no component downstream (the HTTP connection
class, any handler in the opener chain, any retry within that same attempt) may be handed the bare,
unresolved hostname for the purpose of selecting a **destination**. The hostname may still be used, explicitly
and only, for: TLS SNI (SS7), certificate-hostname verification (SS7), the HTTP `Host` header (SS21), and
audit/log identity. This is the exact property whose absence VM-R1 found and whose presence this amendment
requires I-R2 to prove, not merely assert.

## 12. Per-attempt fresh resolution (restated, extended)

CDD-059's existing "fresh resolution per request, never cached" requirement is preserved and extended
explicitly to every attempt type:
```
initial endpoint request       -> fresh resolve + validate + pin, this attempt
every next-link (new request)  -> fresh resolve + validate + pin, independent of the previous page
every retry (same attempt's own retry loop, SS13) -> fresh resolve + validate + pin, this retry
```

## 13. Retry semantics (binding, exact)

Each individual retry attempt within `fetch_page`'s existing bounded retry loop (CDD-059 SS24, max 3 attempts,
unchanged) performs its **own** fresh resolve/validate/pin cycle — it does not reuse a previously validated
address from an earlier retry, and it does not skip validation because an earlier retry already validated
something. A retry's own resolution may legitimately return a different address than a prior retry (DNS can
change); the invariant that must hold **within each individual retry** is unchanged: validated address for
that retry == connected address for that retry. A retry must never reuse an address that its own current
resolution no longer validates, and must never let the transport re-resolve independently after that retry's
own validation.

## 14. Next-link semantics (restated, exact)

Unchanged in substance, restated for this amendment's own precision: every next-link is a new attempt, subject
to the identical resolve→validate→pin→connect sequence as the initial endpoint, with SNI/certificate-hostname
verification against the next-link's own hostname (which may differ from the initial endpoint's hostname if a
source legitimately redirects pagination to a different sub-domain — still subject to the full policy).

## 15. Redirects (restated, unchanged)

Redirect-following remains unconditionally disabled (CDD-059 SS32 point 6). This amendment introduces no
redirect capability of any kind, regardless of whether a redirect target would independently pass policy.

## 16. Port authority (restated, unchanged)

HTTPS scheme remains mandatory. Explicit non-443 ports already present in a governed `endpoint_url` remain
permitted exactly as today (`port = parsed.port or 443`) — this amendment does not alter port semantics in
either direction.

## 17. IPv4 and IPv6 (binding, exact)

The corrected transport must pin correctly for both address families. `socket.create_connection` and
`ssl.SSLContext.wrap_socket` both already accept IPv4 and IPv6 literal addresses without special-casing in
the stdlib; the resolution-set validation loop (SS8) already treats both families uniformly (CDD-059 SS32
point 4). I-R2 must prove both explicitly (VM-R2 test matrix).

## 18. IP-literal URL semantics (binding, exact)

If the governed `endpoint_url`'s own hostname is already a literal IP address (e.g. `https://203.0.113.5/`),
no DNS resolution occurs at all (`socket.getaddrinfo` on a literal IP returns that same address), and the
"validated address" and "original hostname" coincide by construction. `server_hostname` passed for SNI/
certificate verification in this case is that same literal IP; the stdlib `ssl` module already supports
verifying a certificate's IP-address SANs when `server_hostname` is itself an IP literal (supported since
Python's `ssl` module gained RFC 2818/6125-compatible IP-address matching) — no special-casing required
beyond passing the value through consistently.

## 19. R1 boundary remains intact (restated, binding)

This amendment changes only the relationship between a validated address and the transport's connection
target. It does not reopen, weaken, or redesign: `ProductionEndpointSecurityPolicy` (still zero exceptions,
still reads no environment variable), `FixtureEndpointSecurityPolicy` (still test-only, still constructor-
supplied exact addresses, still delegates to the same shared range-check logic), or the absolute-deny classes
(link-local/metadata, multicast, reserved, unspecified — still unconditionally denied regardless of any
`allowed_addresses` content). Every R1 crown (A-H) remains a mandatory regression for I-R2/VM-R2.

## 20. Metadata remains absolute deny under the corrected architecture (restated, exact)

Because the corrected transport connects only to an address that already passed the full policy (SS8-SS11), a
DNS-rebinding attempt (public at validation, metadata at would-be connect) can no longer participate at all —
the transport never asks for, or acts on, a second resolution. I-R2 must prove this via a controlled resolver
seam, never by contacting real cloud metadata.

## 21. HTTP Host header (binding, exact)

The outgoing request's `Host` header remains derived from the original URL authority (hostname, plus port
when the URL's own port is non-default), never from the validated literal IP — except in the IP-literal-URL
case (SS18), where they are the same value by construction.

## 22. TLS SNI (binding, exact)

`server_hostname` passed to the TLS handshake remains the original URL hostname, never the validated literal
IP (except SS18's IP-literal case). This is mandatory for any endpoint relying on virtual-hosted HTTPS
(SNI-based routing), which real enterprise REST APIs commonly are.

## 23. Certificate-hostname verification (binding, exact)

Certificate identity verification remains against the original URL hostname, never merely the IP address.
I-R2 must prove this with an explicit negative crown: a certificate issued for the wrong hostname, served from
the correctly pinned validated IP, over a trusted CA, must still fail TLS verification (SS36 of the governing
prompt; carried forward as a binding I-R2/VM-R2 crown requirement).

## 24. Chosen transport design space (binding, non-prescriptive on exact code)

Investigated directly against this repository's actual dependency set (confirmed via `pyproject.toml`: no
`requests`/`httpx`/`aiohttp` production dependency; CDD-059 SS9 froze stdlib `urllib.request` as the
architectural choice) and against Python's own stdlib source (traced via `traceback` instrumentation, SS4):
`http.client.HTTPConnection.connect()` calls `socket.create_connection((self.host, self.port), ...)`, and
`HTTPSConnection.connect()` separately calls `self._context.wrap_socket(self.sock, server_hostname=...)` —
these are two independent steps in the stdlib's own source, meaning a connection class may be constructed
with `self.host` set to the validated literal IP address (so `create_connection` performs no further
resolution) while an overridden `connect()` (or an equivalent hook) supplies the ORIGINAL hostname as
`server_hostname` to `wrap_socket`. `urllib.request.AbstractHTTPHandler.do_open` already accepts an
injectable `http_class` (the connection class), which is how `HTTPSHandler` itself is normally parameterized —
confirming the opener/handler chain already has a stdlib-native seam for exactly this substitution, requiring
no new production dependency.

**No new third-party HTTP dependency is authorized or required.** CDD-059 SS9's stdlib-only architectural
decision remains unchanged and is not reopened by this amendment.

## 25. Ambient proxy adjudication (binding, exact finding and requirement)

Independently tested: `urllib.request.build_opener(...)`, exactly as `RestConnector.__init__` currently calls
it, silently includes a default `ProxyHandler` that honors `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY`/`NO_PROXY`
environment variables **whenever they are set in the process environment** — confirmed by direct
instrumentation (`urllib.request.getproxies()` reflects a freshly-set `HTTPS_PROXY` immediately; the resulting
opener's handler list includes a live `ProxyHandler`). This is a **second, independent** way the actual
connection destination can diverge from the validated address — a governed connector must not silently trust
whatever proxy an operator's environment happens to have configured. **Not previously governed by CDD-059 at
all** (silent, undocumented stdlib default behavior). Frozen requirement: the connector's own opener
construction must explicitly neutralize ambient proxy configuration (the stdlib-native mechanism is passing an
explicitly empty `ProxyHandler({})` into `build_opener`, which is honored in preference to environment-derived
proxy settings) — the connector transport must not inherit ambient proxy configuration of any kind. This is
additive governance (SS27/SS28 of the governing prompt), not a reopening of any existing decision, since no
prior CDD-059 text ever addressed proxy behavior.

## 26. Connection pooling (restated, non-issue, binding)

Confirmed by direct inspection: `urllib.request`'s opener creates a new `http.client` connection object per
`.open()` call and performs no persistent connection reuse across calls; `RestConnector._attempt_fetch` already
calls `self._opener.open(...)` fresh for every single HTTP attempt (every page, every retry). The corrected
transport must preserve this simple, bounded, per-attempt-fresh-connection behavior — no pooling is introduced
by this amendment.

## 27. Mandatory I-R2 test matrix (binding, restated from the governing prompt, frozen as the exact minimum)

```
1.  original rebinding reproduction (SS4's own method) fails against corrected code
2.  safe-then-private second DNS answer cannot redirect the transport's actual connection
3.  private-then-safe resolution correctly rejected at validation (no "recovery" via re-resolution)
4.  {safe, private} resolution set rejected in full
5.  {safe, metadata} resolution set rejected in full
6.  multiple validated safe addresses: fallback only within that same validated set, no new resolution
7.  production private-address deny (R1 regression)
8.  R1 fixture exact-address allow (R1 regression)
9.  metadata absolute deny even under an active fixture policy (R1 regression)
10. TLS SNI positive: pinned IP connection, correct hostname certificate -> succeeds
11. TLS hostname-negative: pinned IP connection, WRONG hostname certificate, trusted CA -> fails closed
12. redirect remains disabled (R1 regression)
13. next-link rebinding: independently resolved/validated/pinned per next-link
14. retry semantics: each retry independently resolves/validates/pins; validated==connected within each retry
15. ambient proxy environment variables have zero effect on connector transport destination
16. IPv4 pinning
17. IPv6 pinning
18. credential canary: zero leakage through any new transport/connection-class code path
19. timeout/resource bounds unchanged and enforced through the corrected transport
20. real Docker HTTPS pinned-transport crown (SS28 below)
```

## 28. Docker requirement (binding)

I-R2/VM-R2 must prove the corrected pinned transport inside a fresh `--no-cache` Docker build, using the
already-authorized, unmodified fixture infrastructure (no Docker Compose change is authorized or expected to
be necessary): the real backend container's production connector code connects to the fixture container's
validated address while independently proving (via whatever minimal, narrowly-scoped instrumentation I-R2
determines, e.g. a resolver-call-count assertion or an equivalent structural check) that no second,
independent destination-resolution occurs between validation and connection, and that TLS SNI/certificate-
hostname verification still succeeds against the fixture's own governed hostname (`connector-fixture`), never
against its IP.

## 29. Exact I-R2 authorized path set (binding — a maximum permitted write set, Model A, per the original
Artifact Authorization's own SS2 framing, carried forward unchanged)

```
CREATE = 0
MODIFY = 2
DELETE = 0
TOTAL  = 2
```

| # | Action | Path | Purpose |
|---|---|---|---|
| 1 | MODIFY | `backend/app/infrastructure/connectors/rest_connector.py` | Introduce the validate-to-connect IP-pinning transport (SS6-SS26): a connection class/opener construction that resolves fresh, validates the full address set, selects and connects only to an already-validated address, preserves the original hostname for SNI/certificate-hostname verification/Host header, and neutralizes ambient proxy configuration. No change to `EndpointSecurityPolicy`/`ProductionEndpointSecurityPolicy`'s own validation logic (SS19) beyond exposing whatever the chosen connection mechanism needs (e.g., the validated address set) to the caller. |
| 2 | MODIFY | `backend/app/tests/test_oqi_connector_ingestion_postgres.py` | Implements the full SS27 test matrix, including the real Docker pinned-transport crown's own host-side proof and any narrow resolver-call-counting test seam needed for items 1-6/13-14 (test-only, mirroring the existing `FixtureEndpointSecurityPolicy` test-only precedent — never a production path). |

No path beyond these 2 is authorized. `backend/app/application/connector_ingestion_service.py` is **not**
authorized for R2 — the pinning correction is fully internal to `RestConnector`'s own construction/connection
logic; `ConnectorIngestionService` continues to construct `RestConnector` with the identical keyword arguments
it already passes, unchanged. No router, schema, migration, Docker Compose, or Keycloak path is authorized or
expected to be necessary — if I-R2 discovers one of these is genuinely required, it must STOP and this
amendment must be extended first (mirroring the R1 amendment's own STOP-and-extend discipline).

## 30. Prohibited paths (restated, unchanged, binding)

Every prohibition in the original Artifact Authorization's SS3 and the R1 amendment's SS12 remains in full
force, unchanged. Additionally prohibited for I-R2 specifically: any change to `EndpointSecurityPolicy`'s or
`ProductionEndpointSecurityPolicy`'s own address-range decision logic (SS19), any change to
`FixtureEndpointSecurityPolicy`'s location or exemption semantics, any new third-party HTTP dependency (SS24),
any redirect-following capability (SS15), any change to `connector_ingestion_service.py`, and any change to
`docker-compose.yml`.

## 31. I-R2 STOP conditions (binding, exhaustive)

I-R2 must STOP and report rather than improvise if:
```
any of the four existing governance hashes drift (SS3)
this amendment's own hash drifts once published
a path beyond the exact 2 in SS29 is found necessary
the connector's actual TCP destination can still differ from its own validated address, under any
    resolver behavior
TLS SNI or certificate-hostname verification is found to target the validated IP instead of the original
    hostname
the HTTP Host header is found to use the validated IP instead of the original URL authority (outside the
    IP-literal case, SS18)
ambient proxy configuration is found to still influence connector transport destination
a new third-party HTTP dependency is found necessary
redirect-following is found to have been enabled, even incidentally
any R1 crown (A-H) regresses
any tenant, evidence, concurrency, or accounting behavior regresses
resource bounds (timeout/size/pagination/field limits) are found weakened
credential leakage is found through any new code path
the Docker pinned-transport crown cannot be made to pass
any new P0/P1 is discovered
```

## 32. Carried-forward invariants (restated, binding, unchanged)

Migration remains exactly `0045_oqi_connector_ingestion`, single head, 126 tables — no schema change
authorized or required. Tenant authority, the `SourceField` two-hop proof, structural composite tenant FKs,
evidence identity/append-only/current-selection semantics, the `SAVEPOINT`-based concurrency correction, the
Production Evaluation boundary, and both R1 replay scenarios are all unchanged and remain mandatory regression
protection for VM-R2. The full original deferred register (CDD-059 SS54) is carried forward unchanged,
including the still-open "zero genuine production enterprise connectors" capability gap.

## 33. API-surface P3 disposition (restated, carried forward, not reopened)

VM-R1's finding that the original Artifact Authorization's "Exactly 5 routes" text is imprecise against the
6 named conceptual operations and 9 actual implemented routes is recorded here as a carried-forward P3
governance-wording note. No API implementation change is authorized by this amendment; the finding does not
require correction for R2 to proceed.

## 34. No architecture change / no scope expansion (restated)

Nothing in this amendment adds, removes, or reinterprets any CDD-059 architectural decision, evidence
semantic, transaction boundary, tenant model, or API contract. The correction is confined to exactly 2 files,
both already owned by this capability, closing a transport-layer TOCTOU gap that existed since the original I
phase and was not previously detected.

## 35. Governance byte-integrity / hash chain (binding)

```
Original CDD-059:                    6a8be98707ddf13e5428c2b67b00328eefab1556decc40a7203b12ded5daa055
Original Artifact Authorization:     431300c64689e2eea6fde4e44121bda5b6af25f869a9fa60f3b7ebda8ceb6e37
R1 amendment:                        96d319a42df00e38a2b38a3c6f0231c07d35542a9dfc9709c175523e68c1e3c1
This amendment's own hash:           computed and recorded at publication time by the publishing phase itself
                                      (this document does not self-hash).
```
None of the three prior documents is modified by this amendment. I-R2 must bind its own work to all four
hashes and STOP if any drifts (SS31).

## 36. P0/P1/P2/P3 (before this amendment; the condition this amendment corrects)

P0 = 0. P1 = 1 (DNS-rebinding validate/connect TOCTOU, corrected by SS6-SS28). P2 = 0 open. P3 = 1 (carried
forward, SS33, no correction required).

## 37. Authorization

This amendment is approved and published as the governance basis for
`REAL-ENTERPRISE-INGESTION-I-R2`. Implementation against SS29's exact 2-path set is authorized only after this
document's own publication and hash computation. `REAL-ENTERPRISE-INGESTION-VM-R2` must independently
re-attack every item in SS27's test matrix and every carried-forward invariant in SS32 before any merge may be
considered — this amendment authorizes correction, not merge.
