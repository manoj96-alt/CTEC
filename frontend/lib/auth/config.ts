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
// never maintain a second, manually duplicated copy of these names.
const BACKEND_CAPABILITY_SCOPES = [
  "supplier-risk:read",
  "entity-resolution:read",
  "ontology-copilot:ask",
  "ontology-modeling:read",
  "oqi-remediation:prepare",
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
function defaultScope(resourceUri: string): string {
  const capabilityScopes = resourceUri
    ? BACKEND_CAPABILITY_SCOPES.map((scope) => `${resourceUri}/${scope}`)
    : BACKEND_CAPABILITY_SCOPES;
  return ["openid", "profile", ...capabilityScopes].join(" ");
}

// AUTH-BUG-R1: Next.js/Turbopack's build-time NEXT_PUBLIC_* inlining was
// empirically found unreliable for this one reference specifically,
// reproduced repeatedly against the real ACR remote build agent at this
// application's real, full size (a resource-constrained 2-CPU/1-worker
// environment) -- both reading it directly in a nested helper and
// reading it at the top level of browserAuthConfig() (matching every
// other NEXT_PUBLIC_* value here, all of which inline reliably) still
// intermittently produced a build where this one value was missing,
// causing every sign-in request to submit unqualified capability
// scopes, which Entra resolves against Microsoft Graph instead of the
// backend API and rejects with AADSTS650053.
//
// This placeholder is substituted with the real build-time value by a
// single `sed` step in frontend/Dockerfile, run on the raw source file
// BEFORE `next build` even starts -- so there is no `process.env.*`
// reference left for Turbopack to inline at all for this specific
// value, removing the unreliable step entirely. Every context that
// doesn't go through that Dockerfile step (local dev, `npm run build`
// outside Docker, CI, the frontend test suite, Keycloak builds) leaves
// this exact placeholder string untouched -- treated as "not
// configured" below, identical to today's already-correct behavior for
// those contexts.
const BUILD_TIME_API_RESOURCE_URI_PLACEHOLDER =
  "__NEXT_PUBLIC_OIDC_API_RESOURCE_URI__";

function resolvedApiResourceUri(): string {
  // The real NEXT_PUBLIC_* runtime/build-time value still works whenever
  // Turbopack's automatic inlining *does* succeed (smaller builds, local
  // builds, and the test suite's direct `process.env` assignment below
  // all rely on exactly this) -- the placeholder is only a fallback for
  // when it doesn't.
  const runtime = process.env.NEXT_PUBLIC_OIDC_API_RESOURCE_URI;
  if (runtime) return runtime;
  return BUILD_TIME_API_RESOURCE_URI_PLACEHOLDER.startsWith("__")
    ? ""
    : BUILD_TIME_API_RESOURCE_URI_PLACEHOLDER;
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
      defaultScope(resolvedApiResourceUri()),
  };
  if (
    Object.entries(values).some(([key, value]) => key !== "scope" && !value)
  ) {
    throw new Error("Browser authentication configuration is incomplete");
  }
  return values;
}
