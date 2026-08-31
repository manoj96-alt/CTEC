import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
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

// AUTH-UX-I: shared-authenticated-User-lifecycle coverage (accessToken(),
// principalId(), bounded renewal). Mocks oidc-client-ts the same way
// browser-session-signout.test.ts already does, so no real network/storage
// is ever touched.
const { getUserMock, signinRedirectMock } = vi.hoisted(() => ({
  getUserMock: vi.fn(),
  signinRedirectMock: vi.fn(),
}));

vi.mock("oidc-client-ts", () => {
  class FakeUserManager {
    events = {
      addUserLoaded: vi.fn(() => vi.fn()),
      addUserUnloaded: vi.fn(() => vi.fn()),
    };
    async getUser(...args: unknown[]): Promise<unknown> {
      return getUserMock(...args);
    }
    async signinRedirect(...args: unknown[]): Promise<unknown> {
      return signinRedirectMock(...args);
    }
  }
  class FakeWebStorageStateStore {}
  return {
    UserManager: FakeUserManager,
    WebStorageStateStore: FakeWebStorageStateStore,
  };
});

const LIFECYCLE_OIDC_ENV: Record<string, string> = {
  NEXT_PUBLIC_OIDC_AUTHORITY: "http://localhost:8081/realms/CTEC",
  NEXT_PUBLIC_OIDC_CLIENT_ID: "ctec-frontend",
  NEXT_PUBLIC_OIDC_REDIRECT_URI: "http://localhost:3000/auth/callback",
  NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI: "http://localhost:3000/",
  NEXT_PUBLIC_CTEC_API_ORIGIN: "http://localhost:8000",
};

function fakeUser(
  overrides: Partial<{
    expired: boolean;
    access_token: string;
    profile: Record<string, unknown>;
  }> = {},
): {
  expired: boolean;
  access_token: string;
  profile: Record<string, unknown>;
} {
  return {
    expired: false,
    access_token: "a-real-access-token",
    profile: { sub: "user-sub-123" },
    ...overrides,
  };
}

// Scoped to this describe block only: LIFECYCLE_OIDC_ENV must never leak
// into the top-level config tests below (e.g. "browser auth configuration
// fails closed", which requires no OIDC env vars to be set at all).
describe("shared authenticated-user lifecycle (accessToken/principalId/bounded renewal)", () => {
  beforeEach(() => {
    for (const [key, value] of Object.entries(LIFECYCLE_OIDC_ENV)) {
      process.env[key] = value;
    }
    getUserMock.mockReset();
    signinRedirectMock.mockReset();
    signinRedirectMock.mockResolvedValue(undefined);
    window.history.pushState({}, "", "/supplier-risk");
    vi.resetModules();
  });

  test("a valid non-expired in-memory User is returned by accessToken() without triggering renewal", async () => {
    getUserMock.mockResolvedValue(fakeUser());
    const { accessToken } = await import("@/lib/auth/browser-session");

    expect(await accessToken()).toBe("a-real-access-token");
    expect(signinRedirectMock).not.toHaveBeenCalled();
  });

  test("a missing User triggers exactly one bounded prompt=none signinRedirect carrying the validated current path and a silent marker", async () => {
    window.history.pushState({}, "", "/quality");
    getUserMock.mockResolvedValue(null);
    const { accessToken } = await import("@/lib/auth/browser-session");

    expect(await accessToken()).toBeNull();
    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
    const call = signinRedirectMock.mock.calls[0]?.[0] as {
      prompt?: string;
      state?: { returnPath?: string; silent?: boolean };
    };
    expect(call.prompt).toBe("none");
    expect(call.state?.silent).toBe(true);
    expect(call.state?.returnPath).toBe("/quality");
  });

  test("concurrent callers sharing the same module lifetime do not each initiate a renewal redirect", async () => {
    getUserMock.mockResolvedValue(null);
    const { accessToken, principalId } =
      await import("@/lib/auth/browser-session");

    const [token, sub] = await Promise.all([accessToken(), principalId()]);

    expect(token).toBeNull();
    expect(sub).toBeNull();
    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
  });

  test("a caller arriving after the one-shot renewal attempt also fails closed without a second redirect", async () => {
    getUserMock.mockResolvedValue(null);
    const { accessToken } = await import("@/lib/auth/browser-session");

    expect(await accessToken()).toBeNull();
    expect(await accessToken()).toBeNull();
    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
  });

  test("an expired in-memory User is never returned by accessToken() or principalId(), and triggers the same bounded renewal path", async () => {
    getUserMock.mockResolvedValue(fakeUser({ expired: true }));
    const { accessToken, principalId } =
      await import("@/lib/auth/browser-session");

    expect(await accessToken()).toBeNull();
    expect(await principalId()).toBeNull();
    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
  });

  test("principalId() returns profile.sub only for a valid in-memory User, never preferred_username/email/name", async () => {
    getUserMock.mockResolvedValue(
      fakeUser({
        profile: {
          sub: "user-sub-123",
          preferred_username: "demo",
          email: "demo@example.invalid",
          name: "Demo User",
        },
      }),
    );
    const { principalId } = await import("@/lib/auth/browser-session");

    expect(await principalId()).toBe("user-sub-123");
  });

  test("explicit signIn() remains interactive: no prompt=none is set, and the provided return path is preserved", async () => {
    const { signIn } = await import("@/lib/auth/browser-session");

    await signIn("/quality");

    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
    const call = signinRedirectMock.mock.calls[0]?.[0] as {
      prompt?: string;
      state?: { returnPath?: string; silent?: boolean };
    };
    expect(call.prompt).toBeUndefined();
    expect(call.state?.silent).toBeUndefined();
    expect(call.state?.returnPath).toBe("/quality");
  });

  test("explicit signIn() rejects an unsafe (open-redirect) return path and falls back to the safe default", async () => {
    const { signIn } = await import("@/lib/auth/browser-session");

    await signIn("//evil.example.com");

    const call = signinRedirectMock.mock.calls[0]?.[0] as {
      state?: { returnPath?: string };
    };
    expect(call.state?.returnPath).toBe("/supplier-risk");
  });
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
