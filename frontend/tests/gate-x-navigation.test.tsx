import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteShell } from "../components/site-shell";

// Asserts the rendered primary navigation matches CDD-033 §8's enterprise
// information architecture exactly -- same domains, same order, same
// routes. This is the mechanical proof that the frozen IA (not some other
// structure) actually shipped.
const FROZEN_DOMAINS = [
  { label: "Overview", href: "/overview" },
  { label: "Data", href: "/data" },
  { label: "Ontology", href: "/ontology/explorer" },
  { label: "Context", href: "/context" },
  { label: "Quality", href: "/quality" },
  { label: "Intelligence", href: "/intelligence" },
  { label: "Integrations", href: "/integrations" },
  { label: "Governance", href: "/governance" },
  { label: "Administration", href: "/administration" },
];

describe("Gate X primary navigation", () => {
  it("renders exactly the frozen CDD-033 §8 domains, in order, with correct hrefs", () => {
    render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );

    const primary = screen.getByRole("navigation", { name: "Primary" });
    const links = within(primary).getAllByRole("link");

    expect(links.map((link) => link.textContent)).toEqual(
      FROZEN_DOMAINS.map((domain) => domain.label),
    );

    FROZEN_DOMAINS.forEach((domain, index) => {
      expect(links[index]).toHaveAttribute("href", domain.href);
    });
  });

  it("does not render any NOT SUPPORTED / MUST NOT APPEAR nav item", () => {
    render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );

    const primary = screen.getByRole("navigation", { name: "Primary" });
    for (const forbidden of [
      "Ingestion",
      "Blueprints",
      "Semantic Mappings",
      "Evidence",
      "Approvals",
      "Policies",
      "Users & Access",
      "APIs",
      "MCP",
    ]) {
      expect(within(primary).queryByText(forbidden)).not.toBeInTheDocument();
    }
  });

  it("preserves the existing utility links in a secondary navigation group", () => {
    render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );

    const secondary = screen.getByRole("navigation", { name: "Secondary" });
    for (const [label, href] of [
      ["Home", "/"],
      ["Architecture", "/architecture"],
      ["Dataset", "/dataset"],
      ["Prototype", "/prototype"],
      ["About", "/about"],
    ]) {
      expect(
        within(secondary).getByRole("link", { name: label }),
      ).toHaveAttribute("href", href);
    }
  });
});
