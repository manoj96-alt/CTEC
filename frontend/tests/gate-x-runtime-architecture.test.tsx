import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Frontend file-boundary enforcement mirroring the backend's own
// `AUTHORIZED_CHANGED_PATHS` discipline (backend/app/tests/
// test_runtime_architecture.py), scoped to exactly this Artifact
// Authorization's §5 allowlist -- the frozen 29-file Gate X surface.
const REPOSITORY_ROOT = join(process.cwd(), "..");

const AUTHORIZED_CHANGED_PATHS = new Set<string>([
  "frontend/components/site-shell.tsx",
  "frontend/app/ontology-studio/_components/quality-panel.tsx",
  "frontend/app/overview/page.tsx",
  "frontend/app/overview/_components/overview-cards.tsx",
  "frontend/app/data/page.tsx",
  "frontend/app/data/entity-resolution/page.tsx",
  "frontend/app/ontology/explorer/page.tsx",
  "frontend/app/ontology/modeling/page.tsx",
  "frontend/app/context/page.tsx",
  "frontend/app/context/_components/context-lookup.tsx",
  "frontend/lib/context/contracts.ts",
  "frontend/lib/context/api-client.ts",
  "frontend/lib/context/context-provider.tsx",
  "frontend/app/quality/page.tsx",
  "frontend/app/quality/evidence-fitness/page.tsx",
  "frontend/app/intelligence/page.tsx",
  "frontend/app/intelligence/ask-ctec/page.tsx",
  "frontend/app/intelligence/decisions/page.tsx",
  "frontend/app/intelligence/supplier-risk/page.tsx",
  "frontend/app/simulation/page.tsx",
  "frontend/app/integrations/page.tsx",
  "frontend/app/governance/page.tsx",
  "frontend/app/administration/page.tsx",
  "frontend/components/design-system/page-header.tsx",
  "frontend/components/design-system/capability-status-badge.tsx",
  "frontend/components/design-system/empty-state.tsx",
  "frontend/tests/gate-x-navigation.test.tsx",
  "frontend/tests/gate-x-honesty.test.tsx",
  "frontend/tests/gate-x-runtime-architecture.test.tsx",
  // X-PR5-D1: narrowly authorized regression-test maintenance exception,
  // a mechanically necessary consequence of item 1's nav rewrite -- not a
  // 30th Gate X product artifact.
  "frontend/tests/site-shell.test.tsx",
  // X-PR5-D2: narrowly authorized correctness fix -- administration/page
  // .tsx must not depend on the full OIDC config for a genuinely
  // unauthenticated /health call. Not a 30th Gate X product artifact.
  "frontend/app/administration/page.tsx",
]);

function gitChangedPaths(): string[] {
  const tracked = execSync("git diff --name-only HEAD", {
    cwd: REPOSITORY_ROOT,
    encoding: "utf-8",
  });
  const untracked = execSync("git ls-files --others --exclude-standard", {
    cwd: REPOSITORY_ROOT,
    encoding: "utf-8",
  });
  return [...tracked.split("\n"), ...untracked.split("\n")].filter(Boolean);
}

// Paths authorized to change in PR5 that are NOT among the 29 Artifact
// Authorization items themselves (X-PR5-D1). administration/page.tsx
// (X-PR5-D2) is not listed here: it IS one of the 29 items (item 23,
// created in PR4) -- PR5 only corrects it, it doesn't add a 30th file.
const EXCEPTION_PATHS = new Set<string>(["frontend/tests/site-shell.test.tsx"]);

describe("Gate X runtime architecture", () => {
  it("touches only the frozen Artifact Authorization allowlist plus the authorized exceptions", () => {
    const changed = gitChangedPaths();
    for (const path of changed) {
      expect(AUTHORIZED_CHANGED_PATHS.has(path)).toBe(true);
    }
  });

  it("contains exactly the 29 authorized Gate X product artifacts on disk", () => {
    const productArtifacts = [...AUTHORIZED_CHANGED_PATHS].filter(
      (path) => !EXCEPTION_PATHS.has(path),
    );
    expect(productArtifacts).toHaveLength(29);
    for (const path of productArtifacts) {
      expect(existsSync(join(REPOSITORY_ROOT, path))).toBe(true);
    }
  });

  // frontend/app/quality/findings/page.tsx was narrowly authorized as a live
  // route by CDD-045 (OQI7) and the CDD-033 OQI7 companion amendment, which
  // supersedes this file's historical PLANNED/no-active-route prohibition
  // for /quality/findings specifically (CDD-045 Artifact Authorization
  // GC2 test-path correction). /quality/rules and /quality/impact remain
  // unauthorized and must still have no active route.
  it("never creates an active route for a PLANNED generalized-DQ capability not authorized by governance", () => {
    for (const forbidden of [
      "frontend/app/quality/rules/page.tsx",
      "frontend/app/quality/impact/page.tsx",
    ]) {
      expect(existsSync(join(REPOSITORY_ROOT, forbidden))).toBe(false);
    }
  });

  it("never touches a backend, persistence, migration, or Keycloak path", () => {
    const changed = gitChangedPaths();
    for (const path of changed) {
      expect(path.startsWith("backend/")).toBe(false);
      expect(path.startsWith("keycloak/")).toBe(false);
      expect(path).not.toMatch(/migrations?\//);
    }
  });

  it("preserves every legacy deep-link route relocated across PR1-PR4", () => {
    for (const legacy of [
      "frontend/app/ontology-studio/page.tsx",
      "frontend/app/ontology-studio/ask/page.tsx",
      "frontend/app/ontology-studio/entity-resolution/page.tsx",
      "frontend/app/ontology-studio/ontology-modeling/page.tsx",
      "frontend/app/supplier-risk/page.tsx",
      "frontend/app/supply-chain-impact/page.tsx",
    ]) {
      expect(existsSync(join(REPOSITORY_ROOT, legacy))).toBe(true);
    }
  });
});
