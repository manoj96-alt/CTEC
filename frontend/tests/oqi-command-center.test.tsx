import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// CDD-045 §12/§16/§29: Command Center renders real Reliance counts with
// zero score, zero percentage, and equal visual weight for UNKNOWN --
// never a quieter/neutral variant of AT_RISK.
const { commandCenterMock } = vi.hoisted(() => ({
  commandCenterMock: vi.fn(),
}));

vi.mock("@/lib/oqi/api-client", () => ({
  oqiApi: { commandCenter: commandCenterMock },
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
import { CommandCenter } from "@/app/quality/_components/command-center";

describe("OQI Command Center", () => {
  it("renders Supported / At Risk / Unknown as distinct real counts, with no score field anywhere", async () => {
    commandCenterMock.mockResolvedValue({
      reliance_supported_count: 412,
      reliance_at_risk_count: 37,
      reliance_unknown_count: 118,
      critical_dependencies_at_risk_count: 6,
      open_findings_count: 61,
      active_agent_investigations_count: 5,
      pending_human_authorizations_count: 2,
    });

    render(<CommandCenter />);

    const group = await screen.findByRole("group", {
      name: "Enterprise knowledge reliance",
    });
    expect(within(group).getByText("412")).toBeInTheDocument();
    expect(within(group).getByText("37")).toBeInTheDocument();
    expect(within(group).getByText("118")).toBeInTheDocument();
    expect(within(group).getByText("Reliance Supported")).toBeInTheDocument();
    expect(within(group).getByText("Reliance At Risk")).toBeInTheDocument();
    expect(within(group).getByText("Reliance Unknown")).toBeInTheDocument();

    // No score/percentage anywhere in the rendered output.
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/\s*100/)).not.toBeInTheDocument();
  });

  it("never shows a semantic zero while loading", () => {
    commandCenterMock.mockReturnValue(new Promise(() => {}));
    render(<CommandCenter />);
    expect(screen.queryByText("0")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("backend error never becomes a Reliance Unknown determination", async () => {
    commandCenterMock.mockRejectedValue(new OqiApiError("BACKEND_DOWN", 503));
    render(<CommandCenter />);
    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toMatch(/temporarily unavailable/i);
    expect(alert.textContent).not.toMatch(/reliance unknown/i);
  });
});
