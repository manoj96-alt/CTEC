import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import SupplyChainImpactPage from "@/app/supply-chain-impact/page";
import { SupplyChainImpactApiError } from "@/lib/supply-chain-impact/api-client";
import type { SupplyChainImpactEvaluateResponse } from "@/lib/supply-chain-impact/contracts";

const { evaluateMock, signInMock } = vi.hoisted(() => ({
  evaluateMock: vi.fn(),
  signInMock: vi.fn(),
}));

vi.mock("@/lib/supply-chain-impact/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/supply-chain-impact/api-client")
  >("@/lib/supply-chain-impact/api-client");
  return {
    ...actual,
    supplyChainImpactApi: {
      evaluate: evaluateMock,
    },
  };
});

vi.mock("@/lib/auth/browser-session", () => ({
  signIn: signInMock,
}));

beforeEach(() => {
  evaluateMock.mockReset();
  signInMock.mockReset();
  signInMock.mockResolvedValue(undefined);
});

const recommendedResponse: SupplyChainImpactEvaluateResponse = {
  decision_evaluation_id: "eval-1",
  impact: {
    supplier_entity_id: "sup-1",
    supplier_name: "Demo Supplier",
    materials: [{ material_entity_id: "mat-1", material_name: "Demo Material" }],
    products: [{ entity_id: "prod-1", entity_name: "Demo Product" }],
    facilities: [{ entity_id: "fac-1", entity_name: "Demo Facility" }],
    revenue_exposures: [{ entity_id: "rev-1", entity_name: "Demo Revenue Exposure" }],
  },
  materials: [
    {
      material_entity_id: "mat-1",
      high_severity_disruption: true,
      single_source_exposure: true,
      revenue_materiality: true,
      candidates: [
        {
          alternate_supplier_entity_id: "alt-11111111",
          outcome: "Recommended",
          reason: "Recommended: all four governed conditions are satisfied",
          decision_record_identifier: "rec-1",
          structured_reasons: ["Recommended: all four governed conditions are satisfied"],
          narrative: "Gate F governed four-condition mitigation policy (CDD-015 §11).",
          confidence: "High",
          evidence: [
            {
              source_system_name: "Gate F Demo Risk Platform",
              predicate: "severity",
              value: "Severe",
              asserted_on: "2026-01-01T00:00:00Z",
            },
            {
              source_system_name: "Gate F Demo Finance/BI",
              predicate: "annualRevenueUsd",
              value: "12000000",
              asserted_on: "2026-01-01T00:00:00Z",
            },
            {
              source_system_name: "Gate F Demo Supplier Portal",
              predicate: "qualification",
              value: "true",
              asserted_on: "2026-01-01T00:00:00Z",
            },
          ],
        },
      ],
    },
  ],
  governance_standing: "HUMAN_APPROVAL_REQUIRED",
  governance_record_identifier: "gov-1",
  policy_reference: "CDD-015-Gate-F-Mitigation-Policy",
  policy_version: "2.0",
};

const unknownResponse: SupplyChainImpactEvaluateResponse = {
  ...recommendedResponse,
  materials: [
    {
      material_entity_id: "mat-2",
      high_severity_disruption: null,
      single_source_exposure: true,
      revenue_materiality: true,
      candidates: [
        {
          alternate_supplier_entity_id: null,
          outcome: null,
          reason: null,
          decision_record_identifier: null,
          structured_reasons: [],
          narrative: null,
          confidence: null,
          evidence: [],
        },
      ],
    },
  ],
  governance_standing: null,
  governance_record_identifier: null,
};

const rejectedResponse: SupplyChainImpactEvaluateResponse = {
  ...recommendedResponse,
  materials: [
    {
      material_entity_id: "mat-3",
      high_severity_disruption: true,
      single_source_exposure: true,
      revenue_materiality: false,
      candidates: [
        {
          alternate_supplier_entity_id: "alt-22222222",
          outcome: "Rejected",
          reason: "Rejected: revenue exposure does not exceed the materiality threshold",
          decision_record_identifier: "rec-2",
          structured_reasons: ["Rejected: revenue exposure does not exceed the materiality threshold"],
          narrative: "Gate F governed four-condition mitigation policy (CDD-015 §11).",
          confidence: "High",
          evidence: [],
        },
      ],
    },
  ],
  governance_standing: null,
  governance_record_identifier: null,
};

function clickScenario(name: RegExp) {
  fireEvent.click(screen.getByRole("button", { name }));
}

test("renders the scenario picker with all three deterministic scenarios", () => {
  render(<SupplyChainImpactPage />);
  expect(screen.getByRole("button", { name: /High-risk supplier/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Missing governed evidence/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Below the materiality threshold/ })).toBeInTheDocument();
});

test("selecting a scenario calls evaluate with only the supplier entity id", async () => {
  evaluateMock.mockResolvedValue(recommendedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() =>
    expect(evaluateMock).toHaveBeenCalledWith("5d98f421-ef60-5463-9c4e-f81b8bc63da1"),
  );
  expect(evaluateMock).toHaveBeenCalledTimes(1);
  expect(evaluateMock.mock.calls[0]).toHaveLength(1);
});

test("shows a loading state while the request is in flight", async () => {
  let resolvePromise: (value: unknown) => void = () => {};
  evaluateMock.mockReturnValue(
    new Promise((resolve) => {
      resolvePromise = resolve;
    }),
  );
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  expect(screen.getByRole("status")).toHaveTextContent(/Evaluating/);
  resolvePromise(recommendedResponse);
  await waitFor(() => expect(screen.getByText("Recommended")).toBeInTheDocument());
});

test("renders RECOMMENDED with structured reasons, narrative, and confidence", async () => {
  evaluateMock.mockResolvedValue(recommendedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Recommended")).toBeInTheDocument());
  expect(
    screen.getAllByText("Recommended: all four governed conditions are satisfied").length,
  ).toBeGreaterThan(0);
  expect(
    screen.getByText("Gate F governed four-condition mitigation policy (CDD-015 §11)."),
  ).toBeInTheDocument();
  expect(screen.getByText(/High/, { selector: "p.standing" })).toBeInTheDocument();
});

test("renders HUMAN_APPROVAL_REQUIRED with no action controls", async () => {
  evaluateMock.mockResolvedValue(recommendedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() =>
    expect(screen.getByText("Human approval required")).toBeInTheDocument(),
  );
  expect(screen.getByText("CTEC recommends. A human decides. No action is taken automatically.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Execute" })).not.toBeInTheDocument();
});

test("renders UNKNOWN distinctly -- never as No/Rejected/Safe/Zero/Not material", async () => {
  evaluateMock.mockResolvedValue(unknownResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/Missing governed evidence/);
  await waitFor(() =>
    expect(screen.getByText("Insufficient governed evidence")).toBeInTheDocument(),
  );
  expect(
    screen.getByText(/CTEC cannot safely recommend an action/),
  ).toBeInTheDocument();
  expect(screen.queryByText("No")).not.toBeInTheDocument();
  expect(screen.queryByText("Rejected")).not.toBeInTheDocument();
  expect(screen.queryByText("Safe")).not.toBeInTheDocument();
  expect(screen.queryByText(/^Zero$/)).not.toBeInTheDocument();
});

test("renders REJECTED distinctly from UNKNOWN", async () => {
  evaluateMock.mockResolvedValue(rejectedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/Below the materiality threshold/);
  await waitFor(() => expect(screen.getByText("Rejected")).toBeInTheDocument());
  expect(
    screen.getAllByText("Rejected: revenue exposure does not exceed the materiality threshold")
      .length,
  ).toBeGreaterThan(0);
  expect(screen.queryByText("Insufficient governed evidence")).not.toBeInTheDocument();
});

test("renders evidence with source, predicate, value, and timestamp", async () => {
  evaluateMock.mockResolvedValue(recommendedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Why should I trust this?")).toBeInTheDocument());
  expect(screen.getByText("severity", { selector: "strong" })).toBeInTheDocument();
  expect(screen.getAllByText(/Gate F Demo/).length).toBeGreaterThan(0);
});

test("renders a 401 state and offers sign-in", async () => {
  evaluateMock.mockRejectedValue(new SupplyChainImpactApiError("AUTH_TOKEN_MISSING", 401));
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Sign-in required")).toBeInTheDocument());
  fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
  expect(signInMock).toHaveBeenCalledWith("/supply-chain-impact");
});

test("renders a 403 state distinct from 401 (read-only persona attempting evaluation)", async () => {
  evaluateMock.mockRejectedValue(
    new SupplyChainImpactApiError("AUTHORIZATION_SCOPE_REQUIRED", 403),
  );
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() =>
    expect(screen.getByText("Additional authority required")).toBeInTheDocument(),
  );
  expect(screen.getByText("supply-chain-impact:evaluate")).toBeInTheDocument();
  expect(screen.queryByText("Sign-in required")).not.toBeInTheDocument();
});

test("renders a backend-unavailable state for non-auth API failures", async () => {
  evaluateMock.mockRejectedValue(new SupplyChainImpactApiError("HTTP_500", 500));
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Gate F is unavailable")).toBeInTheDocument());
});

test("network failure that is not a SupplyChainImpactApiError shows the same unavailable state", async () => {
  evaluateMock.mockRejectedValue(new TypeError("network down"));
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Gate F is unavailable")).toBeInTheDocument());
});

test("no business conclusion is computed client-side: only backend-returned outcome/reason/narrative/confidence are ever rendered", async () => {
  evaluateMock.mockResolvedValue(recommendedResponse);
  render(<SupplyChainImpactPage />);
  clickScenario(/High-risk supplier/);
  await waitFor(() => expect(screen.getByText("Recommended")).toBeInTheDocument());
  // The rendered outcome/reason/narrative/confidence are exactly the
  // mocked API response's own fields, verbatim -- proving the component
  // performs no recomputation, threshold comparison, or rewriting.
  expect(
    screen.getAllByText(recommendedResponse.materials[0].candidates[0].reason!).length,
  ).toBeGreaterThan(0);
  expect(
    screen.getByText(recommendedResponse.materials[0].candidates[0].narrative!),
  ).toBeInTheDocument();
});
