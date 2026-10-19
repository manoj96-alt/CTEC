import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// WOW-I4-A (CDD-084 §11 item 1): a permanent regression guard against the
// legacy "CTEC" product name re-leaking into USER-VISIBLE copy, mirroring
// gate-x-runtime-architecture.test.tsx's static-file-inspection pattern
// rather than a full render harness.
//
// This is deliberately NOT a naive "the repository contains zero CTEC
// strings" sweep -- CDD-084 explicitly authorizes several categories of
// CTEC string to remain exactly as-is (NEXT_PUBLIC_CTEC_API_ORIGIN, the
// backend-owned `ctec:`/`urn:ctec:` contracts, technical/internal
// identifiers, code comments, historical governance prose). Asserting
// "zero CTEC anywhere" would fail on those legitimate retained occurrences
// and would not be testing the thing that actually matters: that the
// SPECIFIC real product copy a user reads has been migrated. So each case
// below is a (old user-visible phrase absent, new Noetva phrase present)
// pair, anchored to the exact file and exact real phrase migrated in this
// phase -- not a name-wide ban.
const REPOSITORY_ROOT = join(process.cwd(), "..");

function read(relativePath: string): string {
  return readFileSync(join(REPOSITORY_ROOT, relativePath), "utf-8");
}

const MIGRATIONS: Array<{
  file: string;
  oldPhrase: string;
  newPhrase: string;
}> = [
  {
    file: "frontend/app/layout.tsx",
    oldPhrase: "Cognitive Twin Enterprise Core",
    newPhrase: "Ontology-driven decision intelligence",
  },
  {
    file: "frontend/app/_components/home/hero-section.tsx",
    oldPhrase: "CTEC connects supplier",
    newPhrase: "Noetva connects supplier",
  },
  {
    file: "frontend/app/_components/home/supplier-risk-example.tsx",
    oldPhrase: "CTEC traces the connected path",
    newPhrase: "Noetva traces the connected",
  },
  {
    file: "frontend/app/_components/home/capabilities-section.tsx",
    oldPhrase: "What CTEC does",
    newPhrase: "What Noetva does",
  },
  {
    file: "frontend/app/_components/home/explainability-section.tsx",
    oldPhrase: "CTEC does not use an opaque model",
    newPhrase: "Noetva does not use an opaque model",
  },
  {
    file: "frontend/app/about/page.tsx",
    oldPhrase: "What CTEC is",
    newPhrase: "What Noetva is",
  },
  {
    file: "frontend/app/administration/page.tsx",
    oldPhrase: "Not managed by CTEC",
    newPhrase: "Not managed by Noetva",
  },
  {
    file: "frontend/app/governance/page.tsx",
    oldPhrase: "This is CTEC",
    newPhrase: "This is Noetva",
  },
  {
    file: "frontend/app/integrations/page.tsx",
    oldPhrase: "CTEC can discover MCP",
    newPhrase: "Noetva can discover MCP",
  },
  {
    file: "frontend/app/intelligence/page.tsx",
    oldPhrase: '"Ask CTEC"',
    newPhrase: '"Ask Noetva"',
  },
  {
    file: "frontend/app/intelligence/supplier-risk/page.tsx",
    oldPhrase: "backed by CTEC",
    newPhrase: "backed by Noetva",
  },
  {
    file: "frontend/app/simulation/page.tsx",
    oldPhrase: "CTEC can compute a hypothetical",
    newPhrase: "Noetva can compute a hypothetical",
  },
  {
    file: "frontend/app/supplier-risk/new/page.tsx",
    oldPhrase: "assessment · CTEC",
    newPhrase: "assessment · Noetva",
  },
  {
    file: "frontend/app/ontology-studio/_components/ask-ctec-link-card.tsx",
    oldPhrase: ">Ask CTEC<",
    newPhrase: ">Ask Noetva<",
  },
  {
    file: "frontend/app/ontology-studio/ask/_components/ask-ctec-workspace.tsx",
    oldPhrase: ">Ask CTEC<",
    newPhrase: ">Ask Noetva<",
  },
  {
    file: "frontend/app/overview/_components/overview-cards.tsx",
    oldPhrase: "<h3>Ask CTEC</h3>",
    newPhrase: "<h3>Ask Noetva</h3>",
  },
  {
    file: "frontend/app/quality/findings/[findingId]/_components/report-execution-dialog.tsx",
    oldPhrase: "executed. CTEC does not perform",
    newPhrase: "executed. Noetva does not perform",
  },
  {
    file: "frontend/app/supply-chain-impact/_components/human-authority-banner.tsx",
    oldPhrase: "CTEC recommends. A human decides.",
    newPhrase: "Noetva recommends. A human decides.",
  },
  {
    file: "frontend/app/supply-chain-impact/_components/recommendation-panel.tsx",
    oldPhrase: "CTEC recommendation",
    newPhrase: "Noetva recommendation",
  },
  {
    file: "frontend/app/supply-chain-impact/page.tsx",
    oldPhrase: "unavailable. CTEC does not guess",
    newPhrase: "unavailable. Noetva does not guess",
  },
  {
    file: "frontend/components/supplier-risk/assessment-form.tsx",
    oldPhrase: "references. CTEC",
    newPhrase: "references. Noetva",
  },
];

describe("Gate X brand", () => {
  it.each(MIGRATIONS)(
    "$file no longer renders the legacy CTEC phrase, and renders the Noetva replacement",
    ({ file, oldPhrase, newPhrase }) => {
      const content = read(file);
      expect(content).not.toContain(oldPhrase);
      expect(content).toContain(newPhrase);
    },
  );

  it("the persistent wordmark now navigates to /overview, not the legacy root page", () => {
    const content = read("frontend/components/site-shell.tsx");
    expect(content).toContain(
      '<Link className="observatory-wordmark" href="/overview">',
    );
  });

  it("does not touch the forbidden technical/build-contract CTEC identifier NEXT_PUBLIC_CTEC_API_ORIGIN", () => {
    // Proves this is a scoped user-visible-copy migration, not a blind
    // repository-wide rename -- the real Docker/CI build-arg name (used by
    // every `az acr build` invocation) must remain exactly as-is.
    const content = read("frontend/app/administration/page.tsx");
    expect(content).toContain("NEXT_PUBLIC_CTEC_API_ORIGIN");
  });
});
