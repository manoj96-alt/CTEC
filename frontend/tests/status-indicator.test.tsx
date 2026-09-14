import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  StatusIndicator,
  type ObservatoryStatus,
} from "../components/design-system/status-indicator";

// CDD-079 (WOW-I1) §10/§25: every supported state must render a real
// text label -- status must never depend on color alone.
const ALL_STATES: ObservatoryStatus[] = [
  "verified",
  "conflict",
  "attention",
  "pending",
  "unknown",
  "deferred",
  "not-invoked",
  "not-exercised",
  "unavailable",
  "error",
];

describe("StatusIndicator", () => {
  it.each(ALL_STATES)("renders a non-empty text label for '%s'", (status) => {
    render(<StatusIndicator status={status} />);
    const el = screen.getByText(
      (_, node) => (node as HTMLElement | null)?.dataset?.status === status,
    );
    expect(el.textContent?.trim().length).toBeGreaterThan(0);
  });

  it("marks its shape indicator as decorative (aria-hidden) so the label alone carries the accessible name", () => {
    render(<StatusIndicator status="conflict" />);
    const dot = document.querySelector(".obs-status-indicator-dot");
    expect(dot).toHaveAttribute("aria-hidden", "true");
  });

  it("renders distinct visual shapes for a settled vs. an unsettled state (never color alone)", () => {
    const { container: verifiedContainer } = render(
      <StatusIndicator status="verified" />,
    );
    const { container: pendingContainer } = render(
      <StatusIndicator status="pending" />,
    );
    const verifiedDot = verifiedContainer.querySelector(
      ".obs-status-indicator-dot",
    ) as HTMLElement;
    const pendingDot = pendingContainer.querySelector(
      ".obs-status-indicator-dot",
    ) as HTMLElement;
    // "verified" is a solid dot; "pending" is a ring -- the underlying
    // shape/border treatment must genuinely differ, not just the color.
    expect(verifiedDot.style.border).not.toBe(pendingDot.style.border);
  });
});
