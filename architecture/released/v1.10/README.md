# Architecture Release v1.10

Gate E architecture release (PAD-002): publishes the "Local Development
Identity Provider and Demo Persona Authorization Boundary" clarification,
freezing Keycloak as CTEC's local/demo-only reference OIDC identity provider
alongside the existing, unaffected provider-neutral OIDC/JWKS authentication
architecture. Establishes the canonical local issuer/JWKS networking model,
the `tenant_id` and audience claim contracts, the least-privilege primary
demo persona (`supplier-risk:read`, `entity-resolution:read`,
`ontology-copilot:ask`), and the single authoritative `NEXT_PUBLIC_OIDC_SCOPE`
configuration path. No canonical entity, attribute, relationship, or Protocol
Version changes; the ECOM Physical Data Model remains v1.7, unchanged from
baseline v1.9. Unchanged authorities are inherited from v1.9. The Release
Manifest is the integrity register for this directory.
