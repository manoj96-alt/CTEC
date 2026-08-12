import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import Page from "@/app/about/page";

test("renders exactly one accessible h1", () => {
  render(<Page />);
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(
    screen.getByRole("heading", { level: 1, name: "About" }),
  ).toBeInTheDocument();
});

test("the five established stages appear, in order, within a semantic ordered list, with no sixth stage", () => {
  render(<Page />);
  const list = screen.getAllByRole("list").find((el) => el.tagName === "OL")!;
  const items = Array.from(list.querySelectorAll(":scope > li"));
  expect(items.map((item) => item.textContent)).toEqual([
    "Import Data",
    "Map Schema",
    "Explore Ontology",
    "Decision Flow",
    "Recommendation",
  ]);
  expect(items).toHaveLength(5);
});

test("states that seven controlled sample CSV fixtures are used", () => {
  render(<Page />);
  expect(
    screen.getByText(/seven controlled sample CSV fixtures/),
  ).toBeInTheDocument();
});

test("recommendation conditions are distinguished from AI, LLM, or agent reasoning, without claiming rules make the reviewer's decision", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /Recommendation conditions are evaluated by deterministic rules—not AI, LLM, or agent reasoning/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/decisions are made by deterministic rules/i);
  expect(bodyText).not.toMatch(/rules approve or reject/i);
  expect(bodyText).not.toMatch(
    /automatic(ally)? (records?|makes?) the reviewer/i,
  );
  expect(bodyText).not.toMatch(/the reviewer decision is automatic/i);
});

test("traceability is limited to factors, conditions, sample filenames, and row indexes", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /Recommendation factors and rule conditions reference sample fixture filenames and row indexes/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/complete recommendation lineage/i);
  expect(bodyText).not.toMatch(/immutable evidence/i);
  expect(bodyText).not.toMatch(/production traceability/i);
  expect(bodyText).not.toMatch(/enterprise lineage/i);
});

test("Approve/Reject is described as recording one reviewer decision in the current rendered demo session", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /Approve or Reject records one reviewer decision in the current rendered demo session/,
    ),
  ).toBeInTheDocument();
});

test("no operational action is executed and no enterprise system is updated", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /No operational action is executed and no enterprise system is updated/,
    ),
  ).toBeInTheDocument();
});

test("the walkthrough is described as demonstrating, not proving, enterprise value", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /demonstrates how a supplier disruption can be connected through controlled sample data to an evidence-supported recommendation for human review/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/\bproves\b/i);
});

test("CTEC is described as a prototype or demonstration, not a production platform", () => {
  render(<Page />);
  expect(
    screen.getByText(/ontology-backed decision-support prototype and/),
  ).toBeInTheDocument();
  expect(screen.getByText(/not a production platform/)).toBeInTheDocument();
});

test("no YC reference or other unsupported affiliation, funding, founder, testimonial, contact, legal-status, or product-availability claim appears", () => {
  render(<Page />);
  const bodyText = document.body.textContent ?? "";

  expect(bodyText).not.toMatch(/\bYC\b/);
  expect(bodyText).not.toMatch(/founder/i);
  expect(bodyText).not.toMatch(/funding/i);
  expect(bodyText).not.toMatch(/partnership/i);
  expect(bodyText).not.toMatch(/testimonial/i);
  expect(bodyText).not.toMatch(/contact us/i);
  expect(bodyText).not.toMatch(/@[a-z0-9.-]+\.[a-z]{2,}/i); // email pattern
  expect(bodyText).not.toMatch(/available now/i);
  expect(bodyText).not.toMatch(/pricing/i);
});

test("the audience is framed as who the demo may be relevant to, not as existing customers or validated adoption", () => {
  render(<Page />);
  expect(
    screen.getByText(/not a claim of current customers or adoption/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /may be relevant to supply-chain leaders, data and governance practitioners/,
    ),
  ).toBeInTheDocument();
});

test("no CTA, form, or external link is introduced in About content", () => {
  render(<Page />);
  const main = document.querySelector(".max-w-3xl") as HTMLElement;
  expect(within(main).queryAllByRole("link")).toHaveLength(0);
  expect(within(main).queryAllByRole("button")).toHaveLength(0);
  expect(main.querySelectorAll("form")).toHaveLength(0);
});

test("no unsupported live connectivity, persistence, production deployment, autonomous decision-making, or enterprise-authentication claim appears as implemented", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /does not provide live enterprise connectivity, persistent decision or evidence storage, operational execution, enterprise authentication or authorization, or AI, LLM, or agent decision-making/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/dynamically calculated confidence/i);
  expect(bodyText).not.toMatch(/autonomous decision/i);
  expect(bodyText).not.toMatch(
    /comprehensive (enterprise )?ontology reasoning/i,
  );
});

test("the eyebrow is About-specific, not a copy-pasted label from another page", () => {
  render(<Page />);
  expect(screen.getByText("About This Demonstration")).toBeInTheDocument();
  expect(screen.queryByText("Sample Dataset")).not.toBeInTheDocument();
  expect(screen.queryByText("Working Demo")).not.toBeInTheDocument();
});
