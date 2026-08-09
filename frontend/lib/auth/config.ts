export interface BrowserAuthConfig {
  authority: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  apiOrigin: string;
  scope: string;
}
export function browserAuthConfig(): BrowserAuthConfig {
  const values = {
    authority: process.env.NEXT_PUBLIC_OIDC_AUTHORITY ?? "",
    clientId: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
    redirectUri: process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI ?? "",
    postLogoutRedirectUri:
      process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI ?? "",
    apiOrigin: process.env.NEXT_PUBLIC_CTEC_API_ORIGIN ?? "",
    scope:
      process.env.NEXT_PUBLIC_OIDC_SCOPE ?? "openid profile supplier-risk:read",
  };
  if (
    Object.entries(values).some(([key, value]) => key !== "scope" && !value)
  ) {
    throw new Error("Browser authentication configuration is incomplete");
  }
  return values;
}
