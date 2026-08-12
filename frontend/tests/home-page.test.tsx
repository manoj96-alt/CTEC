import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import Home from "@/app/page";

test("renders the hero value statement", () => {
  render(<Home />);
  expect(
    screen.getByRole("heading", {
      name: /From fragmented enterprise data to explainable decisions/,
    }),
  ).toBeInTheDocument();
});

test("journey lists the exact five established stages in order, with impact analysis folded into Explore Ontology", () => {
  render(<Home />);
  const stageHeadings = screen
    .getAllByText(/^Stage \d$/)
    .map((el) => el.nextElementSibling?.textContent);

  expect(stageHeadings).toEqual([
    "Import Data",
    "Map Schema",
    "Explore Ontology",
    "Decision Flow",
    "Recommendation",
  ]);

  // Impact analysis is described within Explore Ontology, not a separate stage.
  expect(screen.queryByText(/^Impact Analysis$/)).not.toBeInTheDocument();
  expect(screen.getByText(/reveal business impact/)).toBeInTheDocument();
});

test("the journey's Recommendation stage says presented for human review, not proposed for human approval", () => {
  render(<Home />);
  expect(
    screen.getAllByText(/presented for human review/).length,
  ).toBeGreaterThan(0);
  expect(
    screen.queryByText(/proposed for human approval/),
  ).not.toBeInTheDocument();
});

test("the supplier-risk example contains no specific dollar figures", () => {
  render(<Home />);
  const example = screen
    .getByText(/Supplier risk, made explainable/)
    .closest("section");
  expect(example?.textContent).not.toMatch(/\$\d/);
});

test("the primary CTA links to the public walkthrough, not the authenticated workspace", () => {
  render(<Home />);
  const cta = screen.getByRole("link", { name: "Explore Supplier Risk" });
  expect(cta).toHaveAttribute("href", "/demo/supplier-risk");
});

test("no secondary CTA links to the still-placeholder Dataset page", () => {
  render(<Home />);
  const datasetLinks = screen.queryAllByRole("link", { name: /dataset/i });
  expect(datasetLinks).toHaveLength(0);
});

test("explainability section uses the qualified source-reference claim, not a broad complete-traceability claim", () => {
  render(<Home />);
  expect(
    screen.getByText(/Deterministic rules, human decisions/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /Recommendation factors and rule conditions reference sample fixture filenames and row indexes/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(
    /Every recommendation traces back to imported source facts/,
  );
});

test("explainability section describes human review without implying an enterprise approval workflow", () => {
  render(<Home />);
  const explainabilitySection = screen
    .getByText(/Deterministic rules, human decisions/)
    .closest("section")!;

  expect(
    within(explainabilitySection).getByText(
      /The recommendation is presented for human review/,
    ),
  ).toBeInTheDocument();
  expect(
    within(explainabilitySection).getByText(
      /Approve or Reject records one reviewer decision in the current rendered demo session/,
    ),
  ).toBeInTheDocument();
  expect(
    within(explainabilitySection).getByText(
      /No operational action is executed and no enterprise system is updated/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/approves or rejects each recommendation/);
});
