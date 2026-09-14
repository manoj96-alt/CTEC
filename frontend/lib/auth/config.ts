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
function defaultScope(): string {
  const resourceUri = process.env.NEXT_PUBLIC_OIDC_API_RESOURCE_URI;
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
    scope: process.env.NEXT_PUBLIC_OIDC_SCOPE || defaultScope(),
  };
  if (
    Object.entries(values).some(([key, value]) => key !== "scope" && !value)
  ) {
    throw new Error("Browser authentication configuration is incomplete");
  }
  return values;
}
