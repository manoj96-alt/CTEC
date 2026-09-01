import { readFileSync } from "node:fs";
import { join } from "node:path";
test("browser session does not use persistent token storage", () => {
  const source = readFileSync(
    join(process.cwd(), "lib/auth/browser-session.ts"),
    "utf8",
  );
  expect(source).not.toContain("localStorage");
  expect(source).not.toContain("access_token,");
  expect(source).toContain("memoryStore");
});
test("userStore is memoryStore-backed, never sessionStorage-backed, while stateStore's legitimate sessionStorage transaction-correlation use is preserved", () => {
  const source = readFileSync(
    join(process.cwd(), "lib/auth/browser-session.ts"),
    "utf8",
  );
  // The authenticated OIDC User (and therefore its access/ID tokens) is
  // wired through `userStore`, never through `stateStore`. `stateStore`
  // legitimately uses sessionStorage for OIDC transaction correlation
  // (state/nonce/code_verifier) only -- BSP-001 prohibits sessionStorage
  // for the User/token itself, not for that unrelated correlation data.
  const userStoreLine = source
    .split("\n")
    .find((line) => line.includes("userStore:"));
  const stateStoreLine = source
    .split("\n")
    .find((line) => line.includes("stateStore:"));
  expect(userStoreLine).toContain("memoryStore()");
  expect(userStoreLine).not.toContain("sessionStorage");
  expect(stateStoreLine).toContain("sessionStorage");
});
test("bounded renewal never calls signinSilent/signinSilentCallback or configures silent_redirect_uri", () => {
  const browserSession = readFileSync(
    join(process.cwd(), "lib/auth/browser-session.ts"),
    "utf8",
  );
  const callback = readFileSync(
    join(process.cwd(), "app/auth/callback/page.tsx"),
    "utf8",
  );
  // Non-comment lines only: this repository's own AUTH-UX-G/I governance
  // comments legitimately name signinSilent() by way of explaining why it
  // is deliberately not used (blocked by this app's own frozen
  // frame-ancestors 'none' CSP -- see BSP-001). What must never exist is an
  // actual call site or config key.
  for (const source of [browserSession, callback]) {
    const code = source
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"))
      .join("\n");
    expect(code).not.toMatch(/\.signinSilent(Callback)?\(/);
    expect(code).not.toContain("silent_redirect_uri");
  }
});
test("API client omits cookies and persistent caching", () => {
  const source = readFileSync(
    join(process.cwd(), "lib/supplier-risk/api-client.ts"),
    "utf8",
  );
  expect(source).toContain('credentials: "omit"');
  expect(source).toContain('cache: "no-store"');
});
