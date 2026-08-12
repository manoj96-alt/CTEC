import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { StudioClient } from "@/app/ontology-studio/_components/studio-client";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  process.env.NEXT_PUBLIC_CTEC_API_ORIGIN = "http://localhost:8000";
  // jsdom does not implement ResizeObserver, which reactflow requires at mount.
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
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
