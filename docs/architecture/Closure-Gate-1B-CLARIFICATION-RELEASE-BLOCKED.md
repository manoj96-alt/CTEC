# Closure Gate 1B — CLARIFICATION RELEASE BLOCKED

Version: 1.0
Status: DEVELOPMENT — BLOCKED
Current: NO
Authority: NON-AUTHORITATIVE
Approved base: `c65ec1a474aeff762887edb15a134006189b37eb`

## 1. Decision

Publication did not occur. Two explicit pre-publication prerequisites are not determined by existing frozen authority:

1. canonical Enterprise ownership for the two vocabulary values; and
2. legacy invocation-version compatibility for the new trusted control-metadata contract.

No release artifact was moved to `architecture/released`, no Registry or current manifest was changed, no commit or push occurred, and no production or test file changed.

## 2. Pre-publication checks completed

- `origin/main` remained exactly `c65ec1a474aeff762887edb15a134006189b37eb` after fetch.
- Before this required blocker report was created, the working tree contained exactly the 27 reviewed Gate 1B governance and release-candidate paths.
- Current Registry/release validation passed: 103 Registry entries, 91 released artifacts, and 77 approved dependencies.
- No production, test, API, persistence, UI, deployment, or capability-integration path was changed.
- CDD-010 remained FROZEN / IMPLEMENTED and its runtime code was untouched.

## 3. Deterministic vocabulary UUID candidates

The repository-authorized deterministic method is UUIDv5 using frozen `BOOTSTRAP_SEED_NAMESPACE` `00000000-0000-0000-0000-000000000008` and the existing seed-loader name construction `uuid5(namespace, "{category}:{value}")`.

| Vocabulary value | UUIDv5 name | Deterministic UUID candidate |
|---|---|---|
| `SUPPLIER_RISK_CONDITION` | `institutional_concept:SUPPLIER_RISK_CONDITION` | `cdbb90c4-6518-59cd-aa13-989d2717a256` |
| `HAS_ACTIVE_RISK_CONDITION` | `relationship_type:HAS_ACTIVE_RISK_CONDITION` | `de39e820-d95c-51ce-9cd3-da98cb072a36` |

The values are distinct, RFC 4122 version 5 identifiers and reproducible in every environment. They are not yet authoritative assignments because ownership is unresolved. Once approved, CVR-001 must record the namespace, exact UTF-8 names, resulting UUIDs, immutability rule, and collision/uniqueness verification.

## 4. P0 — Canonical vocabulary owner is not authorized

The Physical Model requires Institutional Concept ownership by an Enterprise. The repository contains `ECOM Platform`, UUID `00000000-0000-0000-0000-000000000004`, but `backend/app/core/bootstrap.py` explicitly classifies this and related identifiers as “Implementation support constants. Not part of the Canonical Logical Model. Required solely to satisfy referential integrity during deterministic bootstrap.”

ARCH-004 governs the bootstrap Enterprise Entity, not the use of the implementation-support Enterprise as the business/governance owner of newly approved canonical vocabulary. `CTEC Architecture` appears as a document authority/owner, but no frozen artifact establishes it as a canonical Enterprise with an Enterprise Identifier.

Using either as vocabulary owner would silently expand its authority. No other exact repository-authorized vocabulary-owning Enterprise was found.

### Minimum governance decision required

Issue a narrowly scoped Canonical Vocabulary Ownership clarification that does exactly one of the following:

1. explicitly authorizes existing `ECOM Platform` Enterprise `00000000-0000-0000-0000-000000000004` to own the two CVR-001 values, while stating whether this supersedes or narrowly qualifies the implementation-support-only restriction; or
2. identifies another already-existing, governed Enterprise Identifier and cites the frozen authority establishing its vocabulary ownership.

The clarification must not create a new organization, Enterprise, entity type, table, attribute, or general-purpose ownership policy.

## 5. P0 — Legacy invocation compatibility is undefined

PAD-001 v1.4 requires Protocol Version, Engine Version, and Capability Versions, but does not define compatibility, downgrade, missing-field, or unsupported-version behavior. EIC-001 v1.2 defines the version terms and invocation rejection categories but does not define negotiation or legacy behavior. CDD-010 v1.3 implements its existing opaque invocation contract without the proposed trusted control-metadata version.

Therefore existing authority does not determine:

- whether absence of AuthorityContext is valid under the existing Protocol Version;
- whether it is invalid under the new integration contract version;
- how unsupported versions are classified;
- how version/metadata conflicts are rejected; or
- whether downgrade or upgrade is allowed.

### Minimum clarification required

Add the following bounded compatibility rule to the EIC-001 v1.3/PAD traceability release and CDD-010 companion clarification, then repeat Gate 1B review:

1. Existing CDD-010 Protocol Versions and invocations remain byte-for-byte valid and behaviorally unchanged. They do not invoke RFC-014/CIM-001 production integration.
2. The new trusted-control-metadata contract is available only under an explicitly identified new Protocol Version.
3. Absence of AuthorityContext is valid only for a supported legacy Protocol Version. It is a deterministic `Validation Failure` for the new Protocol Version.
4. AuthorityContext supplied with a legacy Protocol Version is a deterministic `Validation Failure` and is never ignored.
5. Unsupported Protocol Versions are deterministically rejected as `Invalid Invocation` before admission and create no Execution Identifier.
6. Conflicting control-metadata schema versions or request/correlation identifiers are deterministic `Validation Failure` results before admission.
7. No implicit downgrade, upgrade, default-to-latest behavior, or semantic reinterpretation is permitted.
8. Version rejection is protocol rejection, not ESM execution failure.

The exact new Protocol Version identifier must be approved and recorded. This clarification changes no existing CDD-010 behavior and does not authorize implementation.

## 6. Validation status

| Gate | Result |
|---|---|
| Approved base | PASS |
| Exact reviewed 27-path boundary before blocker report | PASS |
| Vocabulary UUID determinism and uniqueness | PASS as candidates; authoritative assignment blocked by ownership |
| Enterprise ownership | BLOCKED |
| Legacy invocation compatibility | BLOCKED |
| Current architecture/Registry/checksum/dependency validation | PASS |
| Publication eligibility | BLOCKED |
| Production/test boundary | PASS — zero changes |

## 7. Required next action

Approve the minimum ownership and invocation-compatibility clarifications above. The affected release candidates must then be revised, rerendered, rechecksummed, and re-reviewed through a replacement Gate 1B report before publication.

CDD-011 remains blocked. No publication, merge, release, or implementation is authorized by this report.
