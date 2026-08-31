import { afterEach, expect, test } from "vitest";
import { browserAuthConfig } from "@/lib/auth/config";

const OIDC_ENV_KEYS = [
  "NEXT_PUBLIC_OIDC_AUTHORITY",
  "NEXT_PUBLIC_OIDC_CLIENT_ID",
  "NEXT_PUBLIC_OIDC_REDIRECT_URI",
  "NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI",
  "NEXT_PUBLIC_CTEC_API_ORIGIN",
  "NEXT_PUBLIC_OIDC_SCOPE",
] as const;
const originalEnv = Object.fromEntries(
  OIDC_ENV_KEYS.map((key) => [key, process.env[key]]),
);

afterEach(() => {
  for (const key of OIDC_ENV_KEYS) {
    if (originalEnv[key] === undefined) delete process.env[key];
    else process.env[key] = originalEnv[key];
  }
});

test("browser auth configuration fails closed", () => {
  expect(() => browserAuthConfig()).toThrow("configuration is incomplete");
});

test("canonical default scope is exactly the least-privilege demo-persona set plus openid/profile, with no write/decide scope beyond the two frozen OQI remediation capabilities", () => {
  process.env.NEXT_PUBLIC_OIDC_AUTHORITY = "http://localhost:8081/realms/CTEC";
  process.env.NEXT_PUBLIC_OIDC_CLIENT_ID = "ctec-frontend";
  process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI =
    "http://localhost:3000/auth/callback";
  process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI =
    "http://localhost:3000/";
  process.env.NEXT_PUBLIC_CTEC_API_ORIGIN = "http://localhost:8000";
  delete process.env.NEXT_PUBLIC_OIDC_SCOPE;

  const config = browserAuthConfig();

  expect(config.scope).toBe(
    "openid profile supplier-risk:read entity-resolution:read ontology-copilot:ask ontology-modeling:read oqi-remediation:authorize oqi-remediation:report-execution",
  );
  expect(config.scope).not.toContain("entity-resolution:decide");
  expect(config.scope).not.toContain("supplier-risk:submit");
  expect(config.scope).not.toContain("supplier-risk:retry");
  expect(config.scope).not.toContain("supplier-risk:replay");
  expect(config.scope).not.toContain("ontology-modeling:propose");
  expect(config.scope).not.toContain("ontology-modeling:approve");
  expect(config.scope).not.toContain("ontology-modeling:publish");
});

test("an empty-string NEXT_PUBLIC_OIDC_SCOPE (e.g. an unset Docker build arg passed through) falls back to the canonical default, not an empty scope", () => {
  process.env.NEXT_PUBLIC_OIDC_AUTHORITY = "http://localhost:8081/realms/CTEC";
  process.env.NEXT_PUBLIC_OIDC_CLIENT_ID = "ctec-frontend";
  process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI =
    "http://localhost:3000/auth/callback";
  process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI =
    "http://localhost:3000/";
  process.env.NEXT_PUBLIC_CTEC_API_ORIGIN = "http://localhost:8000";
  process.env.NEXT_PUBLIC_OIDC_SCOPE = "";

  const config = browserAuthConfig();

  expect(config.scope).toBe(
    "openid profile supplier-risk:read entity-resolution:read ontology-copilot:ask ontology-modeling:read oqi-remediation:authorize oqi-remediation:report-execution",
  );
});

test("an explicit non-empty NEXT_PUBLIC_OIDC_SCOPE overrides the canonical default", () => {
  process.env.NEXT_PUBLIC_OIDC_AUTHORITY = "http://localhost:8081/realms/CTEC";
  process.env.NEXT_PUBLIC_OIDC_CLIENT_ID = "ctec-frontend";
  process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI =
    "http://localhost:3000/auth/callback";
  process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI =
    "http://localhost:3000/";
  process.env.NEXT_PUBLIC_CTEC_API_ORIGIN = "http://localhost:8000";
  process.env.NEXT_PUBLIC_OIDC_SCOPE = "openid";

  const config = browserAuthConfig();

  expect(config.scope).toBe("openid");
});
