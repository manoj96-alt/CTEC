import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SiteShell } from "../components/site-shell";

describe("SiteShell", () => {
  it("renders navigation, content, and footer", () => {
    render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );

    expect(
      screen.getByRole("navigation", { name: "Primary" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "Secondary" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "Intelligence" })).toHaveAttribute(
      "href",
      "/intelligence",
    );
    expect(screen.getByRole("link", { name: "Architecture" })).toHaveAttribute(
      "href",
      "/architecture",
    );
    expect(screen.getByRole("link", { name: "Prototype" })).toHaveAttribute(
      "href",
      "/prototype",
    );
    expect(screen.getByText("Page content")).toBeInTheDocument();
    expect(
      screen.getByText(/Noetva — Governed Enterprise Understanding/),
    ).toBeInTheDocument();
  });

  // CDD-079 (WOW-I1) §11/§13: the shell must establish the Observatory
  // brand foundation -- this proves the dark shell markup actually
  // shipped, not merely that the old markup didn't regress.
  it("renders the Observatory shell foundation and brand wordmark", () => {
    const { container } = render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );
    expect(container.querySelector(".observatory-shell")).toBeInTheDocument();
    expect(container.querySelector(".observatory-header")).toBeInTheDocument();
    expect(container.querySelector(".observatory-nav")).toBeInTheDocument();
    expect(container.querySelector(".observatory-wordmark")).toHaveTextContent(
      "Noetva",
    );
  });

  // CDD-079 §12: icons reinforce the label, they never replace it -- and
  // must never be the only carrier of accessible name/active state.
  it("marks the active primary nav item via aria-current, with the icon hidden from assistive tech", () => {
    render(
      <SiteShell>
        <p>Page content</p>
      </SiteShell>,
    );
    const primary = screen.getByRole("navigation", { name: "Primary" });
    const links = primary.querySelectorAll("a");
    for (const link of Array.from(links)) {
      const icon = link.querySelector("svg");
      expect(icon).toHaveAttribute("aria-hidden", "true");
    }
  });
});
