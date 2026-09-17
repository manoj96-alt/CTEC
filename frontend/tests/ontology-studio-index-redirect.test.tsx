import { expect, test, vi } from "vitest";

// CDD-083 §3: the bare /ontology-studio index is genuinely orphaned (no
// real inbound link anywhere in the app -- independently reverified)
// and duplicated the canonically-linked /ontology/explorer experience.
// Proves the redirect target exactly, without deleting the route file
// (frontend/tests/gate-x-runtime-architecture.test.tsx's own
// existsSync check on this exact path continues to pass unmodified).
const { redirectMock } = vi.hoisted(() => ({ redirectMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

test("the /ontology-studio index redirects to the canonical /ontology/explorer, never a competing landing page", async () => {
  const { default: Page } = await import("@/app/ontology-studio/page");
  Page();
  expect(redirectMock).toHaveBeenCalledTimes(1);
  expect(redirectMock).toHaveBeenCalledWith("/ontology/explorer");
});
