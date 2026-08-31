import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// CDD-045 §10/§25-26/§29: Finding list respects API-owned pagination and
// filters; no composite priority score exists anywhere -- criticality,
// Reliance, and age remain independent, separately-visible columns.
const { listFindingsMock } = vi.hoisted(() => ({ listFindingsMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@/lib/oqi/api-client", () => ({
  oqiApi: { listFindings: listFindingsMock },
  OqiApiError: class OqiApiError extends Error {
    constructor(
      public code: string,
      public status: number,
    ) {
      super(code);
    }
  },
}));

import FindingsPage from "@/app/quality/findings/page";

describe("OQI Findings workspace", () => {
  it("renders condition, status, criticality, and Reliance as independent columns with no priority score", async () => {
    listFindingsMock.mockResolvedValue({
      items: [
        {
          finding_id: "11111111-1111-1111-1111-111111111111",
          finding_family: "OQI2",
          condition_label: "Manufacturer Part Number conflict",
          status: "OPEN",
          first_seen_at: "2026-01-01T00:00:00Z",
          last_seen_at: "2026-01-02T00:00:00Z",
          affected_entity_id: null,
          affected_entity_type: null,
          highest_criticality: "CRITICAL",
          reliance_state: "RELIANCE_AT_RISK",
        },
      ],
      next_cursor: null,
    });

    render(<FindingsPage />);

    expect(
      await screen.findByText("Manufacturer Part Number conflict"),
    ).toBeInTheDocument();
    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("Reliance At Risk")).toBeInTheDocument();
    expect(screen.queryByText(/priority/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
  });

  it("empty filtered result is honestly empty, never 'healthy'", async () => {
    listFindingsMock.mockResolvedValue({ items: [], next_cursor: null });
    render(<FindingsPage />);
    expect(
      await screen.findByText("No Findings match this view"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/healthy/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/all clear/i)).not.toBeInTheDocument();
  });

  it("does not render a semantic zero while loading", () => {
    listFindingsMock.mockReturnValue(new Promise(() => {}));
    render(<FindingsPage />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
