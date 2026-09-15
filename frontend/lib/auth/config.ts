export interface BrowserAuthConfig {
  authority: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  apiOrigin: string;
  scope: string;
}

// CDD-066/CDD-074: the single, authoritative list of Noetva backend
// capability scopes the frontend requests at sign-in. Provider-specific
// wire-format qualification (CDD-074) is applied on top of this list --
// never maintain a second, manually duplicated copy of these ten names.
const BACKEND_CAPABILITY_SCOPES = [
  "supplier-risk:read",
  "entity-resolution:read",
  "ontology-copilot:ask",
  "ontology-modeling:read",
  "oqi-remediation:authorize",
  "oqi-remediation:report-execution",
  "oqi:read",
  "information-element-context:read",
  "evidence-fitness:read",
  "supply-chain-impact:evaluate",
] as const;

// CDD-074: local Keycloak has no resource-qualification requirement and
// already works with the bare capability names above -- this value is
// unset locally/in CI, preserving that exact behavior. Microsoft Entra
// External ID requires each custom-API scope to be qualified with the
// backend's own Application ID URI (`api://<backend-client-id>`), or the
// bare name is resolved against Microsoft Graph instead (AADSTS650053,
// CDD-074 SS1-3). `openid`/`profile` are OIDC-standard, provider-hosted
// scopes and are never qualified.
//
// AUTH-BUG-R1: `resourceUri` is taken as a parameter, not read internally
// via `process.env.NEXT_PUBLIC_OIDC_API_RESOURCE_URI`. Next.js/Turbopack's
// build-time NEXT_PUBLIC_* inlining was empirically found (a/b tested
// against the real ACR remote build agent, which runs a more constrained
// 2-CPU/1-worker environment than a typical local machine) to silently
// fail to inline this one reference when it lived inside this nested
// helper -- every sign-in request was then submitted with bare,
// unqualified capability scopes, which Entra resolves against Microsoft
// Graph instead of the backend API and rejects with AADSTS650053. Reading
// the same env var directly in `browserAuthConfig()` below (identical
// pattern to every other NEXT_PUBLIC_* value here, all of which inline
// correctly) and passing it in as a plain argument avoids whatever
// specific code shape triggers the failure, with zero behavior change on
// any build where it already worked.
function defaultScope(resourceUri: string): string {
  const capabilityScopes = resourceUri
    ? BACKEND_CAPABILITY_SCOPES.map((scope) => `${resourceUri}/${scope}`)
    : BACKEND_CAPABILITY_SCOPES;
  return ["openid", "profile", ...capabilityScopes].join(" ");
}

export function browserAuthConfig(): BrowserAuthConfig {
  const values = {
    authority: process.env.NEXT_PUBLIC_OIDC_AUTHORITY ?? "",
    clientId: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
    redirectUri: process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI ?? "",
    postLogoutRedirectUri:
      process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI ?? "",
    apiOrigin: process.env.NEXT_PUBLIC_CTEC_API_ORIGIN ?? "",
    // "||", not "??": an empty-string build-time value (e.g. an unset
    // Docker build arg passed through as "") must fall back to this
    // default too, not be treated as an explicit empty scope request.
    scope:
      process.env.NEXT_PUBLIC_OIDC_SCOPE ||
      defaultScope(process.env.NEXT_PUBLIC_OIDC_API_RESOURCE_URI ?? ""),
  };
  if (
    Object.entries(values).some(([key, value]) => key !== "scope" && !value)
  ) {
    throw new Error("Browser authentication configuration is incomplete");
  }
  return values;
}
