# BSP-001 — Browser Security Governance Allowlist

Version: 1.0
Status: AUTHORIZED

Authorized governance paths only:

- `architecture/released/v1.6/BSP-001_Supplier_Risk_Browser_Authentication_and_Session_Profile_v1.0_FROZEN.md`
- `architecture/released/v1.6/PAS-001_Supplier_Risk_Product_API_and_Security_Contract_v1.1_FROZEN.md`
- the remaining Baseline v1.6 Registry, manifest, dependency, consistency, drift, readiness, record,
  and README artifacts enumerated by the CDD-013 clarification allowlist.

BSP-001 selects a public browser Authorization Code + PKCE profile with memory-only tokens. It does
not authorize a BFF, token proxy, backend session service, production identity-provider
configuration, or frontend implementation. All unlisted paths are READ-ONLY.
