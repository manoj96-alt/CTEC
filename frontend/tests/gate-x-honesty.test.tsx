import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// The load-bearing defense against CDD-033's own two founding findings ever
// regressing: the Gate F/H-U disconnection (Finding 1) and the Quality
// naming collision (Finding 2). Every assertion here checks *rendered
// content*, not implementation details, so it fails the moment the product
// starts to overstate what CTEC actually does.

const {
  supplierRiskQueueMock,
  entityResolutionQueueMock,
  listProposalsMock,
  getConnectorsMock,
} = vi.hoisted(() => ({
  supplierRiskQueueMock: vi.fn(),
  entityResolutionQueueMock: vi.fn(),
  listProposalsMock: vi.fn(),
  getConnectorsMock: vi.fn(),
}));

vi.mock("@/lib/supplier-risk/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/supplier-risk/api-client")
  >("@/lib/supplier-risk/api-client");
  return { ...actual, supplierRiskApi: { queue: supplierRiskQueueMock } };
});

vi.mock("@/lib/entity-resolution/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/entity-resolution/api-client")
  >("@/lib/entity-resolution/api-client");
  return {
    ...actual,
    entityResolutionApi: { queue: entityResolutionQueueMock },
  };
});

vi.mock("@/lib/ontology-modeling/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/ontology-modeling/api-client")
  >("@/lib/ontology-modeling/api-client");
  return {
    ...actual,
    ontologyModelingApi: { listProposals: listProposalsMock },
  };
});

vi.mock("@/lib/ontology-studio/api-client", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/ontology-studio/api-client")
  >("@/lib/ontology-studio/api-client");
  return {
    ...actual,
    ontologyApi: { ...actual.ontologyApi, getConnectors: getConnectorsMock },
  };
});

import AdministrationPage from "@/app/administration/page";
import GovernancePage from "@/app/governance/page";
import IntegrationsPage from "@/app/integrations/page";
import OverviewPage from "@/app/overview/page";
import EvidenceFitnessPage from "@/app/quality/evidence-fitness/page";
import QualityPage from "@/app/quality/page";
import SimulationPage from "@/app/simulation/page";
import { QualityPanel } from "@/app/ontology-studio/_components/quality-panel";
import { useContextIdentifiers } from "@/lib/context/context-provider";
import { ContextIdentifiersProvider } from "@/lib/context/context-provider";

describe("Gate X honesty", () => {
  it("Overview never shows a fabricated count when a source is unavailable", async () => {
    supplierRiskQueueMock.mockRejectedValue(new Error("down"));
    entityResolutionQueueMock.mockRejectedValue(new Error("down"));
    listProposalsMock.mockRejectedValue(new Error("down"));
    getConnectorsMock.mockRejectedValue(new Error("down"));

    render(<OverviewPage />);

    expect(await screen.findAllByText("Unavailable")).toHaveLength(4);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("Overview shows only the real fetched counts, never a static number", async () => {
    supplierRiskQueueMock.mockResolvedValue({ items: [1, 2, 3] });
    entityResolutionQueueMock.mockResolvedValue({ items: [1] });
    listProposalsMock.mockResolvedValue({ proposals: [] });
    getConnectorsMock.mockResolvedValue({ connectors: [1, 2] });

    render(<OverviewPage />);

    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("Ontology Model Completeness is never labeled Quality or Data Quality", () => {
    render(
      <QualityPanel
        quality={{
          overall_score: 0.86,
          method: "deterministic",
          dimensions: [],
          passed_checks: [],
          failed_checks: [],
        }}
      />,
    );
    expect(screen.getByText("Ontology Model Completeness")).toBeInTheDocument();
    expect(screen.queryByText(/^Quality$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Data Quality/)).not.toBeInTheDocument();
  });

  it("the Quality landing page renders no capability detail", () => {
    render(<QualityPage />);
    for (const forbidden of ["FIT", "STALE", "CONFLICTING"]) {
      expect(screen.queryByText(forbidden)).not.toBeInTheDocument();
    }
  });

  it("generalized Data Quality concepts remain visibly Planned and non-interactive", () => {
    render(<QualityPage />);
    for (const name of ["Rules", "Findings", "DQ Impact", "Remediation"]) {
      const heading = screen.getByRole("heading", { name });
      const card = heading.closest("section");
      expect(card).not.toBeNull();
      expect(
        within(card as HTMLElement).queryByRole("link"),
      ).not.toBeInTheDocument();
      expect(
        within(card as HTMLElement).queryByRole("button"),
      ).not.toBeInTheDocument();
      expect(
        within(card as HTMLElement).getByText("Planned"),
      ).toBeInTheDocument();
    }
  });

  // The prior invariant here ("never renders a live query result or
  // execution action") was narrowly superseded by the merged CDD-034
  // Evidence Fitness Frontend Exposure Authorization, which explicitly
  // authorizes exactly one live "Check Evidence Fitness" consumer action.
  // This assertion protects the surviving honesty boundary: the page is a
  // pure consumer of the governed backend result, it fabricates nothing
  // before a real response arrives, and it claims no capability beyond
  // Evidence Fitness itself.
  it("Evidence Fitness exposes only the authorized live consumer action and claims no unauthorized capability", () => {
    render(<EvidenceFitnessPage />);
    expect(
      screen.getByRole("button", { name: /Check Evidence Fitness/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Governed result")).not.toBeInTheDocument();
    expect(
      screen.getByText(/is not part of, and does not imply/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/[Ss]imulation/)).not.toBeInTheDocument();
    expect(screen.queryByText(/remediat/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/autonomous/i)).not.toBeInTheDocument();
  });

  it("Simulation always displays the required non-authority marker set and no execution control", () => {
    render(<SimulationPage />);
    for (const marker of [
      "SIMULATION",
      "HYPOTHETICAL",
      "NON-AUTHORITATIVE",
      "NO PERSISTENCE",
      "NO EXECUTION",
    ]) {
      expect(screen.getByText(marker)).toBeInTheDocument();
    }
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByText(/%|\$[0-9]/)).not.toBeInTheDocument();
  });

  it("Integrations never offers an MCP execution affordance", () => {
    getConnectorsMock.mockResolvedValue({ connectors: [] });
    render(<IntegrationsPage />);
    expect(screen.getByText("MCP")).toBeInTheDocument();
    for (const forbidden of ["Connect", "Invoke", "Execute", "Authorize"]) {
      expect(screen.queryByText(forbidden)).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("Governance never exposes an Approve/Reject action or a live approval queue", () => {
    render(<GovernancePage />);
    expect(
      screen.getByText(/runtime human approval is not available/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reject/i }),
    ).not.toBeInTheDocument();
  });

  it("Administration never invents tenant, user, or role management authority", () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "healthy" }),
    }) as unknown as typeof fetch;

    render(<AdministrationPage />);
    expect(screen.getByText(/not managed by CTEC/i)).toBeInTheDocument();
    for (const forbidden of ["Add user", "Manage roles", "Tenant settings"]) {
      expect(screen.queryByText(forbidden)).not.toBeInTheDocument();
    }
  });

  it("frontend context carries identifiers only, never a cached domain object", () => {
    let captured: ReturnType<typeof useContextIdentifiers> | null = null;
    function Probe() {
      captured = useContextIdentifiers();
      return null;
    }
    render(
      <ContextIdentifiersProvider>
        <Probe />
      </ContextIdentifiersProvider>,
    );
    expect(Object.keys(captured ?? {}).sort()).toEqual(
      [
        "blueprintId",
        "informationElementRequirementId",
        "setContextIdentifiers",
      ].sort(),
    );
  });
});
