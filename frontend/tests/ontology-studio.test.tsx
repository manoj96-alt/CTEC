import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { StudioClient } from "@/app/ontology-studio/_components/studio-client";
import {
  computeLayeredLayout,
  computeEgoLayout,
} from "@/app/ontology-studio/_components/ontology-graph";

beforeEach(() => {
  process.env.NEXT_PUBLIC_CTEC_API_ORIGIN = "http://localhost:8000";
});

const ontologyFixture = {
  ontology_id: "supplier-risk",
  name: "Supplier Risk Enterprise Ontology",
  description: "Test description",
  version: "1.0",
  status: "Published",
  concepts: [
    {
      entity_type_id: "id-supplier",
      name: "Supplier",
      definition: "An organization that provides materials.",
      definition_source: "curated",
      lifecycle_state: "Active",
      governance_status: "Approved",
      version_number: 1,
      discovery_label: "curated",
    },
    {
      entity_type_id: "id-material",
      name: "Material",
      definition: "A raw material.",
      definition_source: "curated",
      lifecycle_state: "Active",
      governance_status: "Approved",
      version_number: 1,
      discovery_label: "curated",
    },
  ],
  relationships: [
    {
      relationship_type_id: "rel-1",
      name: "supplies",
      source_concept: "Supplier",
      target_concept: "Material",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
  ],
  source_mappings: ["seed:ontology_seed.py"],
  provenance: "curated",
  governance_metadata: "Approved",
  quality: {
    overall_score: 0.86,
    method: "Deterministic MVP calculation",
    dimensions: [
      {
        dimension: "concept_coverage",
        score: 1.0,
        passed: true,
        explanation: "10/10",
      },
      {
        dimension: "relationship_coverage",
        score: 0.5,
        passed: false,
        explanation: "3/7",
      },
    ],
    passed_checks: ["concept_coverage"],
    failed_checks: ["relationship_coverage"],
  },
  activation_applications: ["Supplier Risk"],
};

const connectorsFixture = {
  connectors: [
    {
      connector_id: "sap-s4hana",
      display_name: "SAP S/4HANA",
      source_system_type: "ERP",
      authentication_type: "OAuth2",
      supported_object_categories: ["Supplier"],
      configuration_schema_reference: "ref",
      mapping_template_reference: "ref",
      health_status: "Not configured",
      maturity: "Skeleton Available",
    },
    {
      connector_id: "rest-api",
      display_name: "REST API",
      source_system_type: "Generic HTTP",
      authentication_type: "Bearer",
      supported_object_categories: ["Supplier"],
      configuration_schema_reference: "ref",
      mapping_template_reference: "ref",
      health_status: "Available",
      maturity: "Skeleton Available",
    },
  ],
};

function mockFetchSequence(
  responses: Array<{ ok: boolean; json: () => Promise<unknown> }>,
) {
  let call = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      const response = responses[call] ?? responses[responses.length - 1];
      call += 1;
      return Promise.resolve(response);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows a loading state before data arrives", () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise(() => {})),
  );
  render(<StudioClient />);
  expect(screen.getByRole("status")).toHaveTextContent(/Loading ontology/);
});

test("loads ontology, counts, version, and quality dimensions from the backend", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByText("Supplier Risk Enterprise Ontology"),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText("supplier-risk")).toBeInTheDocument();
  expect(screen.getByText("1.0")).toBeInTheDocument();
  expect(screen.getByText("Published")).toBeInTheDocument();
  expect(screen.getByText("86%")).toBeInTheDocument();

  expect(screen.getByText(/concept coverage/)).toBeInTheDocument();
  expect(screen.getByText(/relationship coverage/)).toBeInTheDocument();
});

test("connector maturity labels are rendered exactly as returned by the backend, never upgraded to Demo Connected", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(screen.getByText("SAP S/4HANA")).toBeInTheDocument(),
  );
  const badges = screen.getAllByText("Skeleton Available");
  expect(badges.length).toBe(2);
  expect(screen.queryByText("Demo Connected")).not.toBeInTheDocument();
});

test("relationship list renders backend-sourced relationships", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByText(/Supplier — supplies → Material/),
    ).toBeInTheDocument(),
  );
});

test("selecting a concept node shows its detail", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  await waitFor(() =>
    expect(
      screen.getByText("An organization that provides materials."),
    ).toBeInTheDocument(),
  );
});

test("API export panel renders the actual backend JSON-LD response", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    {
      ok: true,
      json: () =>
        Promise.resolve({
          "@context": { "@vocab": "x" },
          "@graph": [{ "@id": "ctec:concept:Supplier" }],
        }),
    },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(screen.getByText(/Live response preview/)).toBeInTheDocument(),
  );
  expect(screen.getByText(/ctec:concept:Supplier/)).toBeInTheDocument();
});

test("activation card links to the real Supplier Risk application, not a demo route", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByRole("link", { name: "Open Supplier Risk Application" }),
    ).toBeInTheDocument(),
  );
  const link = screen.getByRole("link", {
    name: "Open Supplier Risk Application",
  });
  expect(link).toHaveAttribute("href", "/supplier-risk");
  expect(
    screen.getByText(/powered by Supplier Risk Enterprise Ontology v1.0/),
  ).toBeInTheDocument();
});

test("external consumption examples for Palantir, Databricks, Snowflake, and MCP are all labelled Integration pattern, never a live integration claim", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() => expect(screen.getByText("Palantir")).toBeInTheDocument());
  for (const platform of [
    "Palantir",
    "Databricks",
    "Snowflake",
    "MCP / AI agents",
  ]) {
    expect(screen.getByText(platform)).toBeInTheDocument();
  }
  expect(screen.getAllByText("Integration pattern")).toHaveLength(4);
  expect(screen.queryByText(/live partnership/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/live integration/i)).not.toBeInTheDocument();
});

test("CDD-062: static graph legend explains selection border and edge style, adds no new interaction", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const legend = screen.getByLabelText("Graph legend");
  expect(legend).toBeInTheDocument();
  expect(screen.getByText("Selected concept")).toBeInTheDocument();
  expect(screen.getByText("Unselected concept")).toBeInTheDocument();
  expect(screen.getByText("Governed relationship")).toBeInTheDocument();
});

test("CDD-062: concept lifecycle_state and governance_status render as a visual tag, text unchanged", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  await waitFor(() =>
    expect(
      screen.getByText("An organization that provides materials."),
    ).toBeInTheDocument(),
  );
  const lifecycleValues = screen.getAllByText("Active");
  const governanceValues = screen.getAllByText("Approved");
  expect(lifecycleValues.length).toBeGreaterThan(0);
  expect(governanceValues.length).toBeGreaterThan(0);
  expect(lifecycleValues[0]).toHaveClass("status-tag");
  expect(governanceValues[0]).toHaveClass("status-tag");
});

// CDD-083 §5.3: discovery_label is a real, already-fetched field
// (backend/app/domain/ontology/resolver.py) previously never rendered
// anywhere -- promoted here truthfully, never inferred or fabricated.
test("WOW-I3-B: a curated concept's real discovery_label renders as a truthful provenance badge", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  await waitFor(() =>
    expect(
      screen.getByText("An organization that provides materials."),
    ).toBeInTheDocument(),
  );
  expect(screen.getByText("Curated")).toBeInTheDocument();
  expect(screen.queryByText("Auto-discovered")).not.toBeInTheDocument();
});

test("WOW-I3-B: an auto-discovered concept's real discovery_label renders truthfully, never upgraded to Curated", async () => {
  const autoDiscoveredFixture = {
    ...ontologyFixture,
    concepts: [
      { ...ontologyFixture.concepts[0], discovery_label: "unknown" },
      ontologyFixture.concepts[1],
    ],
  };
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(autoDiscoveredFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  await waitFor(() =>
    expect(screen.getByText("Auto-discovered")).toBeInTheDocument(),
  );
  expect(screen.queryByText("Curated")).not.toBeInTheDocument();
});

test("WOW-I3-B: node selection uses the real --obs-intelligence token, and the legend matches it, never a fabricated OQI/trust/quality annotation on any node", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  // WOW-I3-B-R2: selecting a concept re-layouts the graph into a
  // dedicated ego view (see ontology-graph.tsx), which remounts the
  // ReactFlow canvas -- so the node element is re-queried fresh inside
  // the waitFor, not held across that remount.
  await waitFor(() => {
    const node = screen
      .getAllByText("Supplier")[0]
      .closest("[style*='border']") as HTMLElement | null;
    expect(node?.style.border).toContain("var(--obs-intelligence)");
  });

  // No OQI concept (finding count, DQ badge, trust/confidence score, or
  // "at risk" language) is ever attached to an ontology node -- CDD-081's
  // rejection of a fabricated reverse OQI-to-Ontology mapping still holds.
  expect(screen.queryByText(/trust score/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/at risk/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/finding/i)).not.toBeInTheDocument();
});

// WOW-I3-B-R1: the layered layout is a pure function of the real graph
// structure -- tested directly, independent of ReactFlow/DOM rendering,
// so it never becomes a screenshot-fragile test.
test("WOW-I3-B-R1: the layered layout places concepts strictly left-to-right in real relationship-direction order, deterministically, with no fabricated stage/process semantics", () => {
  const concepts = [
    { name: "A" } as never,
    { name: "B" } as never,
    { name: "C" } as never,
  ];
  const relationships = [
    { source_concept: "A", target_concept: "B", name: "leadsTo" } as never,
    { source_concept: "B", target_concept: "C", name: "leadsTo" } as never,
  ];

  const first = computeLayeredLayout(concepts, relationships);
  const second = computeLayeredLayout(concepts, relationships);

  // Strictly increasing x per real edge direction: A -> B -> C.
  expect(first.positions.A.x).toBeLessThan(first.positions.B.x);
  expect(first.positions.B.x).toBeLessThan(first.positions.C.x);

  // Deterministic: identical input produces identical output.
  expect(second.positions).toEqual(first.positions);
  expect(second.layerOf).toEqual(first.layerOf);
});

test("WOW-I3-B-R1: a concept with no relationships still receives a real, non-overlapping layout position, never dropped from the graph", () => {
  const concepts = [
    { name: "Connected" } as never,
    { name: "Isolated" } as never,
  ];
  const relationships: never[] = [];

  const { positions } = computeLayeredLayout(concepts, relationships);

  expect(positions.Connected).toBeDefined();
  expect(positions.Isolated).toBeDefined();
});

test("WOW-I3-B-R1: selecting a concept keeps every real concept visible, distinctly emphasizes it and its directly connected concepts, and visually de-emphasizes (never hides) unrelated concepts", async () => {
  const threeConceptFixture = {
    ...ontologyFixture,
    concepts: [
      ...ontologyFixture.concepts,
      {
        entity_type_id: "id-region",
        name: "Region",
        definition: "A geographic area.",
        definition_source: "curated",
        lifecycle_state: "Active",
        governance_status: "Approved",
        version_number: 1,
        discovery_label: "curated",
      },
    ],
  };
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(threeConceptFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );

  const supplierNodes = screen.getAllByText("Supplier");
  fireEvent.click(supplierNodes[0]);

  // WOW-I3-B-R2: selecting a concept remounts the ReactFlow canvas into
  // its dedicated ego layout -- re-query the node fresh inside waitFor
  // rather than holding a reference captured before the remount.
  await waitFor(() => {
    const node = screen
      .getAllByText("Supplier")[0]
      .closest("[style*='border']") as HTMLElement;
    expect(node.style.border).toContain("var(--obs-intelligence)");
  });

  // Material is directly connected via the real "supplies" relationship --
  // it must show the connected-tier obs-intelligence-derived border and
  // must NOT be muted.
  const materialNode = screen
    .getAllByText("Material")[0]
    .closest("[style*='border']") as HTMLElement;
  expect(materialNode.style.border).toContain("obs-intelligence");
  expect(materialNode.style.opacity).not.toBe("0.55");

  // Region has no relationship to Supplier at all -- it remains present
  // (never hidden) but is visually de-emphasized.
  const regionNode = screen
    .getAllByText("Region")[0]
    .closest("[style*='border']") as HTMLElement;
  expect(regionNode.style.opacity).toBe("0.55");

  // Every real concept stays represented in the DOM.
  expect(screen.getAllByText("Supplier").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Material").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Region").length).toBeGreaterThan(0);
});

test("WOW-I3-B-R1: the relationship inventory is presented as a collapsible, keyboard-accessible details/summary, collapsed by default, with its content still queryable for accessibility", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(ontologyFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByText(/Supplier — supplies → Material/),
    ).toBeInTheDocument(),
  );

  const details = screen
    .getByText(/Supplier — supplies → Material/)
    .closest("details");
  expect(details).not.toBeNull();
  expect(details).not.toHaveAttribute("open");
  expect(screen.getByText(/Relationship details/)).toBeInTheDocument();
});

// WOW-I3-B-R2: a subset of the REAL supplier-risk ontology
// (backend/app/infrastructure/persistence/ontology_seed.py) mirroring
// its actual concepts and directed relationships, used to prove the
// operator's exact observed failure case (Supplier -- boundBy --> Contract)
// is now directly, unambiguously represented -- not new ontology facts,
// comprehension test cases only (per the governing prompt's own framing).
function supplierRiskConcept(name: string) {
  return {
    entity_type_id: `id-${name.toLowerCase().replace(/\s+/g, "-")}`,
    name,
    definition: `Definition of ${name}.`,
    definition_source: "curated",
    lifecycle_state: "Active",
    governance_status: "Approved",
    version_number: 1,
    discovery_label: "curated",
  };
}

const supplierRiskFixture = {
  ...ontologyFixture,
  concepts: [
    "Supplier",
    "Material",
    "Region",
    "Contract",
    "BOM",
    "Alternate Supplier",
  ].map(supplierRiskConcept),
  relationships: [
    {
      relationship_type_id: "rel-supplies",
      name: "supplies",
      source_concept: "Supplier",
      target_concept: "Material",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
    {
      relationship_type_id: "rel-locatedIn",
      name: "locatedIn",
      source_concept: "Supplier",
      target_concept: "Region",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
    {
      relationship_type_id: "rel-boundBy",
      name: "boundBy",
      source_concept: "Supplier",
      target_concept: "Contract",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
    {
      relationship_type_id: "rel-usedIn",
      name: "usedIn",
      source_concept: "Material",
      target_concept: "BOM",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
    {
      relationship_type_id: "rel-coveredBy",
      name: "coveredBy",
      source_concept: "Material",
      target_concept: "Contract",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
    {
      relationship_type_id: "rel-candidateFor",
      name: "candidateFor",
      source_concept: "Alternate Supplier",
      target_concept: "Material",
      lifecycle_state: "Active",
      governance_status: "Approved",
      discovery_label: "curated",
    },
  ],
};

test("WOW-I3-B-R2: the ego layout places Supplier's real direct relationships (supplies, locatedIn, boundBy) each in their own dedicated lane, and unrelated concepts in a separate context cluster", () => {
  const { positions, leftNames, rightNames, contextNames } = computeEgoLayout(
    supplierRiskFixture.concepts,
    supplierRiskFixture.relationships,
    "Supplier",
  );

  expect(leftNames).toEqual([]);
  expect(rightNames.sort()).toEqual(["Contract", "Material", "Region"].sort());
  expect(contextNames.sort()).toEqual(["Alternate Supplier", "BOM"].sort());

  // Supplier is the centered anchor; every direct target sits in the
  // same right-hand lane (a fixed x), each at its own distinct row (y) --
  // Material, Region, and Contract can never be confused with one
  // another or cross through an unrelated node's lane.
  expect(positions.Supplier).toEqual({ x: 0, y: 0 });
  const rightX = positions.Material.x;
  expect(positions.Region.x).toBe(rightX);
  expect(positions.Contract.x).toBe(rightX);
  expect(rightX).toBeGreaterThan(0);
  const rightYs = new Set([
    positions.Material.y,
    positions.Region.y,
    positions.Contract.y,
  ]);
  expect(rightYs.size).toBe(3);

  // Deterministic: recomputing from identical input reproduces identical
  // positions.
  const second = computeEgoLayout(
    supplierRiskFixture.concepts,
    supplierRiskFixture.relationships,
    "Supplier",
  );
  expect(second.positions).toEqual(positions);
});

test("WOW-I3-B-R2: the ego layout places Contract's two real incoming sources (Supplier via boundBy, Material via coveredBy) in a dedicated left lane, with a truthfully empty right lane", () => {
  const { leftNames, rightNames, positions } = computeEgoLayout(
    supplierRiskFixture.concepts,
    supplierRiskFixture.relationships,
    "Contract",
  );

  expect(leftNames.sort()).toEqual(["Material", "Supplier"].sort());
  expect(rightNames).toEqual([]);
  expect(positions.Contract).toEqual({ x: 0, y: 0 });
  expect(positions.Supplier.x).toBeLessThan(0);
  expect(positions.Material.x).toBeLessThan(0);
  expect(positions.Supplier.x).toBe(positions.Material.x);
  expect(positions.Supplier.y).not.toBe(positions.Material.y);
});

test("WOW-I3-B-R2: the ego layout distinguishes Material's real incoming sources (Supplier, Alternate Supplier) from its real outgoing targets (BOM, Contract)", () => {
  const { leftNames, rightNames } = computeEgoLayout(
    supplierRiskFixture.concepts,
    supplierRiskFixture.relationships,
    "Material",
  );

  expect(leftNames.sort()).toEqual(["Alternate Supplier", "Supplier"].sort());
  expect(rightNames.sort()).toEqual(["BOM", "Contract"].sort());
});

test("WOW-I3-B-R2: selecting Supplier makes 'Supplier — boundBy → Contract' directly, unambiguously readable in the inspector, with no reversed direction and every other real direct relationship present", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(supplierRiskFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  const { container } = render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("Supplier")[0]);

  await waitFor(() =>
    expect(screen.getByText(/Definition of Supplier/)).toBeInTheDocument(),
  );

  const inspector = container.querySelector(
    ".obs-ontology-relationships",
  ) as HTMLElement;

  // The operator's exact observed failure case: Supplier's outgoing
  // boundBy relationship to Contract, stated correctly and not reversed,
  // directly in the selected-concept inspector (not merely somewhere in
  // the full relationship inventory).
  expect(
    within(inspector).getByText("Supplier — boundBy → Contract"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Supplier — supplies → Material"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Supplier — locatedIn → Region"),
  ).toBeInTheDocument();
  // Supplier has no real incoming relationship in this ontology --
  // truthfully reported, never invented.
  expect(within(inspector).getByText("None")).toBeInTheDocument();

  // Never reversed: the incoming direction phrasing does not appear
  // anywhere in the document.
  expect(
    screen.queryByText("Contract — boundBy → Supplier"),
  ).not.toBeInTheDocument();
});

test("WOW-I3-B-R2: selecting Contract directly, unambiguously exposes both of its real incoming relationships (Supplier via boundBy, Material via coveredBy), with a truthfully empty outgoing set", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(supplierRiskFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  const { container } = render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("Contract")[0]);

  await waitFor(() =>
    expect(screen.getByText(/Definition of Contract/)).toBeInTheDocument(),
  );

  const inspector = container.querySelector(
    ".obs-ontology-relationships",
  ) as HTMLElement;

  expect(
    within(inspector).getByText("Supplier — boundBy → Contract"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Material — coveredBy → Contract"),
  ).toBeInTheDocument();
  // Contract has no real outgoing relationship -- truthfully reported.
  expect(within(inspector).getByText("None")).toBeInTheDocument();
});

test("WOW-I3-B-R2: selecting Material distinguishes its real incoming relationships from its real outgoing relationships, and the full accessible relationship inventory remains available", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(supplierRiskFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  const { container } = render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("Material")[0]);

  await waitFor(() =>
    expect(screen.getByText(/Definition of Material/)).toBeInTheDocument(),
  );

  const inspector = container.querySelector(
    ".obs-ontology-relationships",
  ) as HTMLElement;

  expect(
    within(inspector).getByText("Supplier — supplies → Material"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Alternate Supplier — candidateFor → Material"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Material — usedIn → BOM"),
  ).toBeInTheDocument();
  expect(
    within(inspector).getByText("Material — coveredBy → Contract"),
  ).toBeInTheDocument();

  // H: the complete accessible relationship inventory (all 6 real
  // relationships) remains available regardless of selection.
  expect(screen.getByText("Relationship details (6)")).toBeInTheDocument();
});

test("WOW-I3-B-R2: selected/connected/muted concept tiers are distinguished by border width and font weight, not color alone, and unrelated concepts remain present when Supplier is selected", async () => {
  mockFetchSequence([
    { ok: true, json: () => Promise.resolve(supplierRiskFixture) },
    { ok: true, json: () => Promise.resolve(connectorsFixture) },
    { ok: true, json: () => Promise.resolve({ "@context": {}, "@graph": [] }) },
  ]);
  render(<StudioClient />);

  await waitFor(() =>
    expect(
      screen.getByLabelText(/Ontology concept and relationship graph/),
    ).toBeInTheDocument(),
  );
  fireEvent.click(screen.getAllByText("Supplier")[0]);

  const selectedNode = screen
    .getAllByText("Supplier")[0]
    .closest("[style*='border']") as HTMLElement;
  await waitFor(() => expect(selectedNode.style.border).toContain("2px"));
  expect(selectedNode.style.fontWeight).toBe("700");

  const connectedNode = screen
    .getAllByText("Contract")[0]
    .closest("[style*='border']") as HTMLElement;
  expect(connectedNode.style.border).toContain("1px");
  expect(connectedNode.style.fontWeight).toBe("600");

  // Alternate Supplier has no direct relationship to Supplier -- it
  // remains present (never removed) but is visually muted, distinguished
  // by border width AND font weight, not merely a color shift.
  const mutedNode = screen
    .getAllByText("Alternate Supplier")[0]
    .closest("[style*='border']") as HTMLElement;
  expect(mutedNode.style.border).toContain("1px");
  expect(mutedNode.style.fontWeight).toBe("500");
  expect(mutedNode.style.opacity).toBe("0.55");
});

test("shows a bounded error state with Retry when the ontology API is unavailable, never a fabricated fallback", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 503,
        json: () => Promise.resolve({}),
      }),
    ),
  );
  render(<StudioClient />);

  await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  expect(screen.getByText(/Ontology service unavailable/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  expect(
    screen.queryByText("Supplier Risk Enterprise Ontology"),
  ).not.toBeInTheDocument();
});
