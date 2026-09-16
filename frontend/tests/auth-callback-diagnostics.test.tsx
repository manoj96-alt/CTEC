import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const routerReplaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: routerReplaceMock }),
}));

// CDD-082 (WOW-I3-A-R3): safe, narrow diagnostic coverage for the live-
// reproducible "Sign-in failed" callback defect. Two independent things
// are proven here:
//
// 1. The callback page's diagnostic rendering never exposes a code,
//    token, verifier, nonce, state value, or the raw callback query
//    string -- only a sanitized error class/message, a coarse phase
//    marker, and boolean signals (§3 of CDD-082).
// 2. A concrete, deterministic proof of the architectural gap R3
//    identified by reading the source: signIn() has no mutual-exclusion
//    guard against a bootstrap silent-renewal signinRedirect() already
//    in flight on the same page load -- unlike the *cross-page-reload*
//    renewal race browser-session.test.ts already proves is fixed, this
//    *same-page-load* concurrency is untested and unguarded.

const { getUserMock, signinRedirectMock, signinRedirectCallbackMock } =
  vi.hoisted(() => ({
    getUserMock: vi.fn(),
    signinRedirectMock: vi.fn(),
    signinRedirectCallbackMock: vi.fn(),
  }));

class FakeErrorResponse extends Error {
  error: string;
  error_description: string | null;
  state: unknown;
  constructor(args: {
    error: string;
    error_description?: string;
    userState?: unknown;
  }) {
    super(args.error_description || args.error);
    this.name = "ErrorResponse";
    this.error = args.error;
    this.error_description = args.error_description ?? null;
    this.state = args.userState;
  }
}

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
    async signinRedirectCallback(...args: unknown[]): Promise<unknown> {
      return signinRedirectCallbackMock(...args);
    }
  }
  class FakeWebStorageStateStore {}
  return {
    UserManager: FakeUserManager,
    WebStorageStateStore: FakeWebStorageStateStore,
    ErrorResponse: FakeErrorResponse,
  };
});

const OIDC_ENV: Record<string, string> = {
  NEXT_PUBLIC_OIDC_AUTHORITY: "http://localhost:8081/realms/CTEC",
  NEXT_PUBLIC_OIDC_CLIENT_ID: "ctec-frontend",
  NEXT_PUBLIC_OIDC_REDIRECT_URI: "http://localhost:3000/auth/callback",
  NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI: "http://localhost:3000/",
  NEXT_PUBLIC_CTEC_API_ORIGIN: "http://localhost:8000",
};

describe("CDD-082: same-page-load silent-renewal vs explicit sign-in concurrency", () => {
  beforeEach(() => {
    for (const [key, value] of Object.entries(OIDC_ENV)) {
      process.env[key] = value;
    }
    getUserMock.mockReset();
    signinRedirectMock.mockReset();
    sessionStorage.clear();
    vi.resetModules();
  });

  test("signIn() waits out an in-flight bootstrap silent renewal before starting its own redirect -- the two are never concurrent", async () => {
    getUserMock.mockResolvedValue(null);
    // The silent renewal's own signinRedirect() call is deliberately left
    // unresolved (simulating the real in-flight window between the
    // renewal guard being set and the navigation actually completing).
    let resolveSilent: (() => void) | undefined;
    signinRedirectMock.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          resolveSilent = resolve;
        }),
    );
    signinRedirectMock.mockResolvedValueOnce(undefined);

    const { accessToken, signIn } = await import("@/lib/auth/browser-session");

    const bootstrapRenewal = accessToken(); // fires restoredUser() -> signinRedirect(prompt:none), left pending
    // Deterministically wait until the bootstrap renewal has actually
    // reached and passed its guard and started its own signinRedirect()
    // call -- not a fixed microtask/timer guess -- before the user's
    // explicit click below.
    await waitFor(() => expect(signinRedirectMock).toHaveBeenCalledTimes(1));

    const explicitSignIn = signIn("/quality"); // the user's explicit click, while the renewal above is still unresolved

    // CDD-082/WOW-I3-A-R3 fix: signIn() must NOT start its own redirect
    // while the silent one is still unresolved -- proving the two calls
    // are strictly sequential, never concurrent (the exact condition the
    // pre-fix version of this test proved was absent).
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(signinRedirectMock).toHaveBeenCalledTimes(1);

    resolveSilent?.();
    await bootstrapRenewal;
    await explicitSignIn;

    expect(signinRedirectMock).toHaveBeenCalledTimes(2);
    const explicitCall = signinRedirectMock.mock.calls[1]?.[0] as {
      prompt?: string;
    };
    expect(explicitCall.prompt).toBeUndefined(); // this is the explicit call, distinct from the silent one
  });

  test("signIn() proceeds immediately when no silent renewal is in flight (no regression to ordinary sign-in latency)", async () => {
    signinRedirectMock.mockResolvedValue(undefined);
    const { signIn } = await import("@/lib/auth/browser-session");

    await signIn("/quality");

    expect(signinRedirectMock).toHaveBeenCalledTimes(1);
  });
});

describe("CDD-082: callback diagnostic classification and redaction", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  test("classifies a state-store-lookup failure as AUTH_CALLBACK_STATE_LOOKUP", async () => {
    const { classifyCallbackFailure } =
      await import("@/app/auth/callback/page");
    const result = classifyCallbackFailure(
      new Error("No matching state found in storage"),
    );
    expect(result.phase).toBe("AUTH_CALLBACK_STATE_LOOKUP");
    expect(result.errorMessage).toBe("No matching state found in storage");
  });

  test("classifies an ErrorResponse using only its safe error/error_description fields", async () => {
    const { classifyCallbackFailure } =
      await import("@/app/auth/callback/page");
    const failure = new FakeErrorResponse({
      error: "invalid_grant",
      error_description: "AADSTS9002313: Invalid request.",
    });
    const result = classifyCallbackFailure(failure);
    expect(result.phase).toBe("AUTH_CALLBACK_TOKEN_EXCHANGE_OR_REDIRECT_ERROR");
    expect(result.errorMessage).toBe(
      "invalid_grant: AADSTS9002313: Invalid request.",
    );
  });

  test("an unrecognized failure classifies as AUTH_CALLBACK_UNKNOWN, never silently swallowed", async () => {
    const { classifyCallbackFailure } =
      await import("@/app/auth/callback/page");
    const result = classifyCallbackFailure(new TypeError("Failed to fetch"));
    expect(result.phase).toBe("AUTH_CALLBACK_UNKNOWN");
    expect(result.errorClass).toBe("TypeError");
  });

  test("the query-string duplicate-consumption hash never stores the raw query string", async () => {
    const { sha256Hex } = await import("@/app/auth/callback/page");
    const hash = await sha256Hex("?code=super-secret-code&state=abc123");
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
    expect(hash).not.toContain("super-secret-code");
    expect(hash).not.toContain("abc123");
  });
});

describe("CDD-082: AuthCallback failure rendering never exposes secret material", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    for (const [key, value] of Object.entries(OIDC_ENV)) {
      process.env[key] = value;
    }
    getUserMock.mockResolvedValue(null);
    signinRedirectCallbackMock.mockReset();
    sessionStorage.clear();
    vi.resetModules();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: {
        ...originalLocation,
        pathname: "/auth/callback",
        search: "?code=super-secret-code&state=abc123",
      },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      configurable: true,
      value: originalLocation,
    });
  });

  test("a generic (non-ErrorResponse) failure renders a sanitized diagnostic with no code/state/query string", async () => {
    signinRedirectCallbackMock.mockRejectedValue(
      new Error("No matching state found in storage"),
    );
    const { default: AuthCallback } = await import("@/app/auth/callback/page");

    render(<AuthCallback />);

    const diagnostic = await screen.findByTestId("auth-callback-diagnostic");
    expect(diagnostic.textContent).toContain("AUTH_CALLBACK_STATE_LOOKUP");
    expect(diagnostic.textContent).not.toContain("super-secret-code");
    expect(diagnostic.textContent).not.toContain("abc123");
    expect(document.body.innerHTML).not.toContain("super-secret-code");
  });

  test("a silent (bounded-renewal) failure shows no diagnostic and no error at all", async () => {
    signinRedirectCallbackMock.mockRejectedValue(
      new FakeErrorResponse({
        error: "login_required",
        userState: { returnPath: "/quality", silent: true },
      }),
    );
    const { default: AuthCallback } = await import("@/app/auth/callback/page");

    render(<AuthCallback />);

    await vi.waitFor(() => {
      expect(
        screen.queryByTestId("auth-callback-diagnostic"),
      ).not.toBeInTheDocument();
    });
    expect(screen.queryByText("Sign-in failed")).not.toBeInTheDocument();
  });
});
