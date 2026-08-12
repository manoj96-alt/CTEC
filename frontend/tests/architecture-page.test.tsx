import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import Page from "@/app/architecture/page";
import { sampleRelationships } from "@/app/_components/architecture/sample-relationships";
import { buildOntologyModel } from "@/lib/demo/ontology-model";
import { buildTestScenarioFacts } from "./helpers/demo-fixture";

test("the five established journey stages appear, in the correct order, as an ordered list", () => {
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
});

test("no competing sixth primary stage is introduced", () => {
  render(<Page />);
  const list = screen.getAllByRole("list").find((el) => el.tagName === "OL")!;
  expect(list.querySelectorAll(":scope > li")).toHaveLength(5);
});

test("impact analysis is explained within Explore Ontology, not as a separate stage", () => {
  render(<Page />);
  expect(screen.getByText(/enables impact analysis/)).toBeInTheDocument();
  expect(
    screen.getByText(/Impact analysis is a capability within this stage/),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("listitem", { name: /^Impact Analysis$/ }),
  ).not.toBeInTheDocument();
});

test("identifies the demo as parsing the seven controlled sample files, without implying live connectivity", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /seven controlled sample CSV files are parsed into the demo's known dataset structure/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText(/any csv is converted automatically/i),
  ).not.toBeInTheDocument();
});

test("names all seven sample files by filename, labeled as fixed demo fixtures", () => {
  render(<Page />);
  for (const file of [
    "suppliers.csv",
    "materials.csv",
    "products.csv",
    "facilities.csv",
    "supply_agreements.csv",
    "risk_events.csv",
    "revenue_exposure.csv",
  ]) {
    expect(screen.getByText(file)).toBeInTheDocument();
  }
  expect(
    screen.getByText(/fixed demo fixtures, not live connectors/),
  ).toBeInTheDocument();
});

test("recommendation traceability is qualified precisely, and demo-fixture-reference status is disclosed", () => {
  render(<Page />);
  expect(
    screen.getByText(
      /Recommendation factors and rule conditions are traceable to sample source rows/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /not persisted enterprise lineage or immutable evidence records/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Every recommendation traces to source rows"),
  ).not.toBeInTheDocument();
});

test("approval is described as recording a demo decision, not executing an action", () => {
  render(<Page />);
  expect(
    screen.getByText(/proposes a recommendation for human review/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /records the reviewer's decision in the current demo session/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /No operational action is executed and no enterprise system is updated/,
    ),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Nothing acts without human approval"),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByText("Approval is required before execution"),
  ).not.toBeInTheDocument();
});

test("mapping confidence is identified as predefined demo metadata, not a computed score", () => {
  render(<Page />);
  expect(
    screen.getByText(/predefined sample mapping confidence value/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(
      /not a dynamically calculated or inferred confidence score/,
    ),
  ).toBeInTheDocument();
});

test("implemented, architectural-direction, and not-implemented capabilities are visually distinguishable columns", () => {
  render(<Page />);
  expect(screen.getByText("Implemented in this demo")).toBeInTheDocument();
  expect(screen.getByText("Architectural direction")).toBeInTheDocument();
  expect(screen.getByText("Not implemented")).toBeInTheDocument();

  const notImplementedHeading = screen.getByText("Not implemented");
  const notImplementedColumn = notImplementedHeading.closest("div")!;
  for (const item of [
    "Live enterprise connectors",
    "Persistent decisions",
    "Operational execution",
    "Production evidence storage",
    "Multi-scenario ontology reasoning",
    "AI, LLM, or agent decision-making",
    "Dynamically calculated confidence",
    "Enterprise authentication or authorization",
  ]) {
    expect(within(notImplementedColumn).getByText(item)).toBeInTheDocument();
  }
});

test("architectural direction is not described as already available", () => {
  render(<Page />);
  expect(
    screen.getByText(/is not already available in this demo/),
  ).toBeInTheDocument();
});

test("relationships are labeled as sample-only, not universal or comprehensive", () => {
  render(<Page />);
  expect(
    screen.getByText("Sample Supplier Risk Relationships"),
  ).toBeInTheDocument();
  expect(screen.getByText(/not a universal ontology/)).toBeInTheDocument();
  expect(
    screen.getByText(/comprehensive enterprise model/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/automatically discovered semantic graph/),
  ).toBeInTheDocument();
});

// Explicit, tested mapping from the customer-facing entity names used on
// the Architecture page to the actual ontology node kinds implemented in
// lib/demo/ontology-model.ts. Used only to verify displayed relationships
// below — never used at runtime.
const ENTITY_NAME_TO_KIND: Record<string, string> = {
  Supplier: "supplier",
  "Candidate Supplier": "candidateSupplier",
  Material: "material",
  Product: "product",
  Facility: "facility",
  "Revenue Exposure": "revenue",
  Region: "region",
  "Risk Event": "riskEvent",
  "Supply Agreement": "agreement",
};

test("every displayed relationship triple (source kind, label, target kind) matches a real edge in the implemented ontology model", () => {
  const model = buildOntologyModel(buildTestScenarioFacts());
  const nodeIdToKind = new Map(model.nodes.map((node) => [node.id, node.kind]));

  const realTriples = new Set(
    model.edges.map((edge) => {
      const sourceKind = nodeIdToKind.get(edge.source);
      const targetKind = nodeIdToKind.get(edge.target);
      return `${sourceKind}|${edge.label}|${targetKind}`;
    }),
  );

  for (const relationship of sampleRelationships) {
    const sourceKind = ENTITY_NAME_TO_KIND[relationship.source];
    const targetKind = ENTITY_NAME_TO_KIND[relationship.target];

    expect(
      sourceKind,
      `No node-kind mapping for displayed source "${relationship.source}"`,
    ).toBeDefined();
    expect(
      targetKind,
      `No node-kind mapping for displayed target "${relationship.target}"`,
    ).toBeDefined();

    const triple = `${sourceKind}|${relationship.label}|${targetKind}`;
    expect(
      realTriples.has(triple),
      `Displayed relationship "${relationship.source} —${relationship.label}→ ${relationship.target}" ` +
        `(triple: ${triple}) does not match any real edge in the implemented ontology model.`,
    ).toBe(true);
  }
});

test("the technical section uses a native details/summary element and mentions no clickable file links", () => {
  render(<Page />);
  const summary = screen.getByText("How this demo works");
  const details = summary.closest("details");
  expect(details).not.toBeNull();
  expect(details?.tagName).toBe("DETAILS");
  expect(summary.tagName).toBe("SUMMARY");

  const fileLinks = within(details!).queryAllByRole("link");
  expect(fileLinks).toHaveLength(0);
});

test("no live connector, persistence, AI, LLM, agent, execution, or production-lineage claim appears as an implemented capability", () => {
  render(<Page />);
  const bodyText = document.body.textContent ?? "";

  // These phrases are only acceptable inside the "Not implemented" column
  // or the explicit qualification sentences already tested above — a raw
  // substring check across the whole page would false-positive on those,
  // so this test targets the specific over-claims the correction forbids.
  expect(bodyText).not.toContain("Nothing acts without human approval");
  expect(bodyText).not.toContain("Approval is required before execution");
  expect(bodyText).not.toContain("Approve/Reject is an execution gate");
  expect(bodyText).not.toContain("Every recommendation traces to source rows");
  expect(bodyText).not.toMatch(/any csv is converted automatically/i);
  expect(bodyText).not.toContain("model confidence");
  expect(bodyText).not.toContain("recommendation confidence");
});

test("semantic heading structure: exactly one h1, and h2 sections present", () => {
  render(<Page />);
  expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  expect(
    screen.getAllByRole("heading", { level: 2 }).length,
  ).toBeGreaterThanOrEqual(2);
});
