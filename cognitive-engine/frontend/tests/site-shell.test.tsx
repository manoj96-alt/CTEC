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
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
      "href",
      "/",
    );
    expect(screen.getByRole("link", { name: "Architecture" })).toHaveAttribute(
      "href",
      "/architecture",
    );
    expect(screen.getByText("Page content")).toBeInTheDocument();
    expect(
      screen.getByText(/Enterprise Cognitive Operating Model prototype/),
    ).toBeInTheDocument();
  });
});
