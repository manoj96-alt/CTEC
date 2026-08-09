# IDP-001 — Provider-Neutral OIDC Identity Validation Contract

Version: 1.0  
Status: FROZEN  
Owner: ECOM Platform Enterprise (`00000000-0000-0000-0000-000000000004`)  
Approval: CDD-013 bounded governance decision

The production verifier accepts bearer access tokens only and validates signature and JOSE header
against keys obtained from the configured trusted issuer's OIDC/JWKS metadata. Deployment
configuration exclusively owns issuer, audience, discovery/JWKS endpoint, permitted asymmetric
algorithms, subject claim, tenant claim, scope/role claims, cache lifetime, refresh behavior, and
clock skew. Callers cannot select or override them.

Required validation includes signature, algorithm allowlist, issuer, audience, expiration,
not-before, subject, one unambiguous tenant, and configured authorization claims. Unsigned,
malformed, expired, premature, algorithm-substituted, unverifiable, missing, ambiguous, or
conflicting tokens fail before capability execution. Unknown keys trigger one bounded refresh;
unavailable discovery/keys fail closed. JWKS caching is bounded and supports rotation.

Only the validated principal ID/type, tenant/organization, normalized allowlisted roles/scopes,
issuer trust source, token timing bounds, and a server-generated authorization-decision reference
may contribute to AuthorityContext. Raw tokens, signatures, credentials, complete claim sets, and
sensitive claim values are never logged or persisted. Safe diagnostic codes expose no verification
internals.

CDD-013 selects `PyJWT[crypto]` 2.13.x as the production implementation: MIT licensed, compatible
with Python 3.12, asymmetric algorithm allowlists and `PyJWKClient`. Dependency ownership belongs
to the ECOM Platform Enterprise. Upgrades require tests and a vulnerability/license review;
rollback restores the prior lock/dependency declaration and deployment image. Custom cryptography
and decode-only authentication are prohibited.

