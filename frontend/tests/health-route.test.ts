import { describe, expect, test } from "vitest";
import { GET } from "@/app/health/route";

// CDD-070: proves the frontend's own health route is truthful, deterministic,
// and dependency-free -- it must never call the backend, /administration,
// the OIDC authority, Key Vault, or a database, and must succeed with no
// authentication and no browser OIDC configuration present.
describe("frontend /health route", () => {
  test("returns a successful, deterministic response with no arguments", async () => {
    const response = await GET();
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body).toEqual({ status: "healthy" });
  });

  test("does not require any NEXT_PUBLIC_OIDC_* configuration", async () => {
    const OIDC_ENV_KEYS = [
      "NEXT_PUBLIC_OIDC_AUTHORITY",
      "NEXT_PUBLIC_OIDC_CLIENT_ID",
      "NEXT_PUBLIC_OIDC_REDIRECT_URI",
      "NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI",
      "NEXT_PUBLIC_CTEC_API_ORIGIN",
      "NEXT_PUBLIC_OIDC_SCOPE",
    ] as const;
    const original = Object.fromEntries(
      OIDC_ENV_KEYS.map((key) => [key, process.env[key]]),
    );
    for (const key of OIDC_ENV_KEYS) delete process.env[key];
    try {
      const response = await GET();
      expect(response.status).toBe(200);
    } finally {
      for (const key of OIDC_ENV_KEYS) {
        if (original[key] !== undefined) process.env[key] = original[key];
      }
    }
  });
});
