import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ContentPage } from "../components/content-page";

describe("ContentPage", () => {
  it("renders its title and content", () => {
    render(<ContentPage title="Architecture">Placeholder</ContentPage>);
    expect(
      screen.getByRole("heading", { name: "Architecture" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Placeholder")).toBeInTheDocument();
  });
});
