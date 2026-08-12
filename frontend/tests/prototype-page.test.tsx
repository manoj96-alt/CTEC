import { readFileSync } from "node:fs";
import { join } from "node:path";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import Page from "@/app/prototype/page";

const PAGE_SOURCE = readFileSync(
  join(process.cwd(), "app", "prototype", "page.tsx"),
  "utf-8",
);

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      throw new Error(
        "fetch should never be called on the Prototype page — it is a static launcher only.",
      );
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders exactly one accessible h1", () => {
  render(<Page />);
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(
    screen.getByRole("heading", { level: 1, name: "Prototype" }),
  ).toBeInTheDocument();
});

test("shows a Prototype-specific eyebrow, not the Dataset page's label", () => {
  render(<Page />);
  expect(screen.getByText("Working Demo")).toBeInTheDocument();
  expect(screen.queryByText("Sample Dataset")).not.toBeInTheDocument();
});

test("the five established stages appear, in order, within a semantic ordered list, with no sixth stage", () => {
  render(<Page />);
  const list = screen.getAllByRole("list").find((el) => el.tagName === "OL")!;
  const items = Array.from(list.querySelectorAll(":scope > li"));
  const labels = items.map((item) => item.querySelector("p")?.textContent);

  expect(labels).toEqual([
    "Import Data",
    "Map Schema",
    "Explore Ontology",
    "Decision Flow",
    "Recommendation",
  ]);
  expect(items).toHaveLength(5);
});

test("the uniquely named launch CTA points exactly to /demo/supplier-risk, and no Prototype-local CTA points to /supplier-risk", () => {
  render(<Page />);
  const cta = screen.getByRole("link", {
    name: "Launch the Supplier Risk Walkthrough",
  });
  expect(cta).toHaveAttribute("href", "/demo/supplier-risk");

  // Scoped to Prototype's own content, not the shared nav (which may
  // legitimately contain /supplier-risk).
  const main = document.querySelector(".max-w-3xl") as HTMLElement;
  const localSupplierRiskLink = within(main)
    .queryAllByRole("link")
    .find((link) => link.getAttribute("href") === "/supplier-risk");
  expect(localSupplierRiskLink).toBeUndefined();
});

test("human review is described as recording a demo decision, not authorizing execution", () => {
  render(<Page />);
  expect(screen.getByText(/presented for human review/)).toBeInTheDocument();
  expect(
    screen.getByText(
      /Approve or Reject records one reviewer decision in the current demo session/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /No operational action is executed and no enterprise system is updated/i,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toContain(
    "A recommendation always requires human Approve/Reject",
  );
  expect(bodyText).not.toContain("Approval is required before execution");
  expect(bodyText).not.toContain("hasDecided guard");
});

test("deterministic rules are distinguished from AI or LLM decision-making", () => {
  render(<Page />);
  expect(
    screen.getByText(/Deterministic demo rules, not AI or LLM reasoning/),
  ).toBeInTheDocument();
});

test("traceability is limited to factors/conditions and sample source-row references, not generalized lineage claims", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /Recommendation factors and rule conditions reference sample fixture filenames and row indexes/,
    ),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/production evidence/i);
  expect(bodyText).not.toMatch(/immutable enterprise traceability/i);
  expect(bodyText).not.toMatch(/complete recommendation lineage/i);
});

test("session behavior is described precisely, without over-claiming what Reset Demo proves", () => {
  render(<Page />);
  expect(
    screen.getByText(/clears the current in-memory walkthrough state/),
  ).toBeInTheDocument();

  const bodyText = document.body.textContent ?? "";
  expect(bodyText).not.toMatch(/durable authenticated server session/i);
  expect(bodyText).not.toMatch(/proves there is no persistence/i);
});

test("no scenario inputs, Approve/Reject controls, upload controls, or other interactive engine controls appear on the page", () => {
  render(<Page />);
  expect(screen.queryAllByRole("button")).toHaveLength(0);
  expect(screen.queryAllByRole("slider")).toHaveLength(0);
  expect(screen.queryAllByRole("textbox")).toHaveLength(0);
  expect(
    screen.queryByRole("button", { name: /Approve/i }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: /Reject/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/upload/i)).not.toBeInTheDocument();
});

test("rendering the page never calls fetch — proves no data loading occurs", () => {
  render(<Page />);
  expect(fetch).not.toHaveBeenCalled();
});

test("the page source imports no scenario-controller, rule-engine, ontology-building, or fixture-loading modules", () => {
  const importLines = PAGE_SOURCE.split("\n").filter((line) =>
    line.trim().startsWith("import "),
  );
  const importSource = importLines.join("\n");

  expect(importSource).not.toMatch(/demo-scenario-controller/);
  expect(importSource).not.toMatch(/lib\/demo\/decision-rules/);
  expect(importSource).not.toMatch(/lib\/demo\/ontology-model/);
  expect(importSource).not.toMatch(/lib\/demo\/fixture-loader/);
  expect(importSource).not.toMatch(/lib\/demo\/scenario-facts/);
});

test("controlled sample data and no live enterprise connectivity are stated plainly", () => {
  render(<Page />);
  expect(
    screen.getByText(/not a live enterprise connection/),
  ).toBeInTheDocument();
});
