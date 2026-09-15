import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// CDD-080 §7/§13: the Enterprise Understanding panel is a pure,
// real-data-only composition -- every assertion here checks rendered
// content, not implementation details, so it fails the moment the panel
// starts to fabricate a metric, imply progress that hasn't occurred, or
// collide with the pre-existing OQI `CommandCenter` naming on /quality.
const { commandCenterMock, listFindingsMock } = vi.hoisted(() => ({
  commandCenterMock: vi.fn(),
  listFindingsMock: vi.fn(),
}));

vi.mock("@/lib/oqi/api-client", () => ({
  oqiApi: { commandCenter: commandCenterMock, listFindings: listFindingsMock },
  OqiApiError: class OqiApiError extends Error {
    constructor(
      public code: string,
      public status: number,
    ) {
      super(code);
    }
  },
}));

import { OqiApiError } from "@/lib/oqi/api-client";
import { EnterpriseUnderstandingPanel } from "@/app/overview/_components/enterprise-understanding-panel";

const COMMAND_CENTER_FIXTURE = {
  reliance_supported_count: 412,
  reliance_at_risk_count: 37,
  reliance_unknown_count: 118,
  critical_dependencies_at_risk_count: 6,
  open_findings_count: 4,
  active_agent_investigations_count: 0,
  pending_human_authorizations_count: 0,
};

const GOLDEN_THREAD_FINDING = {
  finding_id: "finding-country-of-origin",
  finding_family: "CROSS_SOURCE_VALUE_CONFLICT",
  condition_label: "Country of Origin",
  status: "OPEN",
  first_seen_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-02T00:00:00Z",
  affected_entity_id: "entity-1",
  affected_entity_type: "Supplier",
  highest_criticality: "HIGH",
  reliance_state: "RELIANCE_AT_RISK",
};

describe("Enterprise Understanding panel (Overview)", () => {
  it("never shows a semantic zero while loading, and shows no fabricated score/percentage", () => {
    commandCenterMock.mockReturnValue(new Promise(() => {}));
    listFindingsMock.mockReturnValue(new Promise(() => {}));

    render(<EnterpriseUnderstandingPanel />);

    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/\s*100/)).not.toBeInTheDocument();
    expect(screen.getAllByRole("status").length).toBeGreaterThan(0);
  });

  it("renders the real hero count and never displays the literal string 'Command Center'", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });

    render(<EnterpriseUnderstandingPanel />);

    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.queryByText(/Command Center/i)).not.toBeInTheDocument();
  });

  it("selects the highest-criticality open finding generically (no hardcoded finding ID), and renders its real fields", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({
      items: [
        {
          ...GOLDEN_THREAD_FINDING,
          finding_id: "low-1",
          highest_criticality: "LOW",
        },
        {
          ...GOLDEN_THREAD_FINDING,
          finding_id: "medium-1",
          highest_criticality: "MEDIUM",
        },
        GOLDEN_THREAD_FINDING,
        {
          ...GOLDEN_THREAD_FINDING,
          finding_id: "critical-1",
          highest_criticality: "CRITICAL",
        },
      ],
      next_cursor: null,
    });

    render(<EnterpriseUnderstandingPanel />);

    // The CRITICAL item must win the sort, not the fixture literally named
    // after the Golden Thread -- proving the selection is data-driven, not
    // an identity check against a specific finding.
    const link = await screen.findByRole("link", { name: /Open finding/i });
    expect(link).toHaveAttribute("href", "/quality/findings/critical-1");
  });

  it("surfaces the certified Country-of-Origin finding truthfully when it is the only/highest-priority open finding, with no unsupported inference", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({
      items: [GOLDEN_THREAD_FINDING],
      next_cursor: null,
    });

    render(<EnterpriseUnderstandingPanel />);

    expect(await screen.findByText("Country of Origin")).toBeInTheDocument();
    expect(screen.getByText(/Criticality — HIGH/)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: /Open finding/i });
    expect(link).toHaveAttribute(
      "href",
      "/quality/findings/finding-country-of-origin",
    );
    // Never assert facts beyond the real payload -- no "Supplier Portal"
    // or "Specification missing" text this component never receives.
    expect(screen.queryByText(/Supplier Portal/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Specification/i)).not.toBeInTheDocument();
  });

  it("renders a truthful empty state when there are genuinely zero open findings, never a fabricated spotlight", async () => {
    commandCenterMock.mockResolvedValue({
      ...COMMAND_CENTER_FIXTURE,
      open_findings_count: 0,
    });
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });

    render(<EnterpriseUnderstandingPanel />);

    expect(await screen.findByText("No open findings")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /Open finding/i }),
    ).not.toBeInTheDocument();
  });

  it("renders the real Reliance triplet with non-color-only status semantics", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });

    render(<EnterpriseUnderstandingPanel />);

    const group = await screen.findByRole("group", {
      name: "Enterprise knowledge reliance",
    });
    expect(within(group).getByText("412")).toBeInTheDocument();
    expect(within(group).getByText("37")).toBeInTheDocument();
    expect(within(group).getByText("118")).toBeInTheDocument();
    expect(within(group).getByText("Verified")).toBeInTheDocument();
    expect(within(group).getByText("Conflict")).toBeInTheDocument();
    expect(within(group).getByText("Unknown")).toBeInTheDocument();
  });

  it("renders a real, truthful zero for pending human authorization and active agent investigations", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });

    render(<EnterpriseUnderstandingPanel />);

    const group = await screen.findByRole("group", {
      name: "Governed human and agent attention",
    });
    expect(within(group).getAllByText("0")).toHaveLength(2);
    expect(within(group).getByText("Not exercised")).toBeInTheDocument();
    expect(within(group).getByText("Not invoked")).toBeInTheDocument();
    expect(screen.queryByText(/AI is investigating/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/agent confidence/i)).not.toBeInTheDocument();
  });

  it("renders nonzero pending human authorization and active agent investigations truthfully, distinct from recommendation/authorization", async () => {
    commandCenterMock.mockResolvedValue({
      ...COMMAND_CENTER_FIXTURE,
      active_agent_investigations_count: 3,
      pending_human_authorizations_count: 2,
    });
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });

    render(<EnterpriseUnderstandingPanel />);

    const group = await screen.findByRole("group", {
      name: "Governed human and agent attention",
    });
    expect(within(group).getByText("2")).toBeInTheDocument();
    expect(within(group).getByText("3")).toBeInTheDocument();
    expect(within(group).getByText("Attention")).toBeInTheDocument();
    expect(within(group).getByText("Pending")).toBeInTheDocument();
  });

  it("backend error never becomes a fabricated zero or a Reliance determination", async () => {
    commandCenterMock.mockRejectedValue(new OqiApiError("BACKEND_DOWN", 503));
    listFindingsMock.mockRejectedValue(new OqiApiError("BACKEND_DOWN", 503));

    render(<EnterpriseUnderstandingPanel />);

    const alerts = await screen.findAllByRole("alert");
    expect(alerts.length).toBeGreaterThan(0);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("unauthorized never implies a healthy, zero, or unknown Reliance state", async () => {
    commandCenterMock.mockRejectedValue(new OqiApiError("AUTH_REQUIRED", 401));
    listFindingsMock.mockRejectedValue(new OqiApiError("AUTH_REQUIRED", 401));

    render(<EnterpriseUnderstandingPanel />);

    expect(
      await screen.findAllByText(
        /does not indicate anything about the underlying/i,
      ),
    ).not.toHaveLength(0);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
  });

  it("every CTA resolves to a real, existing route", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({
      items: [GOLDEN_THREAD_FINDING],
      next_cursor: null,
    });

    render(<EnterpriseUnderstandingPanel />);

    await screen.findByText("Country of Origin");
    expect(screen.getByRole("link", { name: /Open finding/i })).toHaveAttribute(
      "href",
      "/quality/findings/finding-country-of-origin",
    );

    const group = screen.getByRole("group", {
      name: "Enterprise knowledge reliance",
    });
    for (const link of within(group).getAllByRole("link")) {
      expect(link).toHaveAttribute("href", "/quality");
    }

    const attentionGroup = screen.getByRole("group", {
      name: "Governed human and agent attention",
    });
    for (const link of within(attentionGroup).getAllByRole("link")) {
      expect(link).toHaveAttribute("href", "/quality/findings");
    }
  });

  it("applies the one-shot spotlight entry animation only once real finding data has arrived", async () => {
    commandCenterMock.mockResolvedValue(COMMAND_CENTER_FIXTURE);
    listFindingsMock.mockResolvedValue({
      items: [GOLDEN_THREAD_FINDING],
      next_cursor: null,
    });

    const { container } = render(<EnterpriseUnderstandingPanel />);
    await screen.findByText("Country of Origin");

    expect(
      container.querySelector(".obs-eu-spotlight-enter"),
    ).toBeInTheDocument();
  });
});
