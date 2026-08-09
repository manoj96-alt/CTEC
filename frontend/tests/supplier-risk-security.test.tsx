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
test("API client omits cookies and persistent caching", () => {
  const source = readFileSync(
    join(process.cwd(), "lib/supplier-risk/api-client.ts"),
    "utf8",
  );
  expect(source).toContain('credentials: "omit"');
  expect(source).toContain('cache: "no-store"');
});
