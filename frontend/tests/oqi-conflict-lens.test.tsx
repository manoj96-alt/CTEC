import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConflictLens } from "@/app/quality/findings/[findingId]/_components/conflict-lens";
import type {
  BusinessImpactResponse,
  EvidenceResponse,
  FindingDetailResponse,
  OntologyImpactResponse,
  RelianceResponse,
} from "@/lib/oqi/contracts";

// CDD-081 §12: Conflict Lens replaces the raw PageHeader(eyebrow=
// finding_family, title=condition_label) usage on the finding-detail
// shell. It is composed entirely from data the shell has already
// fetched -- these tests assert the real family-label mapping, the
// preserved-verbatim technical identifier, the exact "Status: {status}"/
// "Resolved — ..." strings the deep-linking tests in
// oqi-finding-detail.test.tsx depend on, and that no score/confidence/
// trust metric is ever fabricated.
const FINDING: FindingDetailResponse = {
  finding_id: "22222222-2222-2222-2222-222222222222",
  finding_family: "OQI2",
  condition_label: "oqi-demo-supplier-country-of-origin",
  status: "OPEN",
  state_revision: 1,
  first_seen_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-02T00:00:00Z",
};

const EMPTY_EVIDENCE: EvidenceResponse = { participants: [], candidate: null };
const EMPTY_IMPACT: OntologyImpactResponse = {
  outcome: "NO_IMPACT",
  direct_entity_id: null,
  direct_entity_type: null,
  propagated_path: null,
};
const EMPTY_BUSINESS_IMPACT: BusinessImpactResponse = {
  outcome: "NO_KNOWN_BUSINESS_IMPACT",
  dependencies: [],
};
const EMPTY_RELIANCE: RelianceResponse = {
  state: "RELIANCE_UNKNOWN",
  reason_codes: [],
  contributing_finding_ids: [],
  history: [],
};

describe("Conflict Lens — identity", () => {
  it("maps the real finding_family to its human-readable label as the primary heading", () => {
    render(
      <ConflictLens
        finding={FINDING}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Cross-Source Consistency" }),
    ).toBeInTheDocument();
  });

  it("preserves condition_label verbatim, demoted but present, subordinate to the family heading", () => {
    render(
      <ConflictLens
        finding={FINDING}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    const id = screen.getByText("oqi-demo-supplier-country-of-origin");
    expect(id).toBeInTheDocument();
    // Machine-ID demotion (CDD-081 §10): the technical identifier keeps a
    // distinct, subordinate typographic treatment -- never removed, never
    // promoted to share the primary heading's own markup.
    expect(id).toHaveClass("obs-cl-id");
    expect(id.tagName).not.toBe("H1");
    expect(
      screen.getByRole("heading", { name: "Cross-Source Consistency" }),
    ).toBeInTheDocument();
  });

  it("INTEGRITY and TIMELINESS map to their own real label, never collapsed into OQI1-3 or invented", () => {
    const { rerender } = render(
      <ConflictLens
        finding={{ ...FINDING, finding_family: "INTEGRITY" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Integrity" }),
    ).toBeInTheDocument();

    rerender(
      <ConflictLens
        finding={{ ...FINDING, finding_family: "TIMELINESS" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.getByRole("heading", { name: "Timeliness" }),
    ).toBeInTheDocument();
  });

  it("an unmapped family code falls back to itself, never a blank heading", () => {
    render(
      <ConflictLens
        finding={{ ...FINDING, finding_family: "OQI9" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(screen.getByRole("heading", { name: "OQI9" })).toBeInTheDocument();
  });
});

describe("Conflict Lens — status truth", () => {
  it("renders exactly Status: {status} for a non-resolved Finding", () => {
    render(
      <ConflictLens
        finding={{ ...FINDING, status: "OPEN" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(screen.getByText("Status: OPEN")).toBeInTheDocument();
  });

  it("renders the exact Resolved confirmation string for a resolved Finding", () => {
    render(
      <ConflictLens
        finding={{ ...FINDING, status: "RESOLVED" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.getByText(
        /Resolved — confirmed by fresh evidence and re-evaluation/,
      ),
    ).toBeInTheDocument();
  });
});

describe("Conflict Lens — family-aware evidence signal", () => {
  it("OQI2 with conflicting participants reads as a real evidence conflict", () => {
    render(
      <ConflictLens
        finding={FINDING}
        evidence={{
          participants: [
            {
              source_system: "SAP",
              observed_value: "US",
              is_missing: false,
              is_authoritative: false,
              is_conflicting: true,
            },
            {
              source_system: "PLM",
              observed_value: "MX",
              is_missing: false,
              is_authoritative: false,
              is_conflicting: true,
            },
          ],
          candidate: null,
        }}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(screen.getByText("Sources disagree")).toBeInTheDocument();
  });

  it("OQI2 with zero participants is described as a real evidence gap", () => {
    render(
      <ConflictLens
        finding={{ ...FINDING, finding_family: "OQI2" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(screen.getByText("No source evidence recorded")).toBeInTheDocument();
  });

  it("OQI1 with zero participants is described as not comparing sources, never as a gap", () => {
    render(
      <ConflictLens
        finding={{ ...FINDING, finding_family: "OQI1" }}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.getByText("Does not compare multiple sources"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("No source evidence recorded"),
    ).not.toBeInTheDocument();
  });
});

describe("Conflict Lens — no fabricated metrics", () => {
  it("never renders a score, confidence, or trust metric", () => {
    render(
      <ConflictLens
        finding={FINDING}
        evidence={EMPTY_EVIDENCE}
        impact={{
          outcome: "IMPACTED",
          direct_entity_id: "e1",
          direct_entity_type: "MATERIAL",
          propagated_path: null,
        }}
        businessImpact={{
          outcome: "BUSINESS_IMPACT_IDENTIFIED",
          dependencies: [
            {
              business_process_name: "Supplier Qualification (Demo)",
              criticality: "CRITICAL",
              business_dependency_version: 1,
            },
          ],
        }}
        reliance={{ ...EMPTY_RELIANCE, state: "RELIANCE_AT_RISK" }}
      />,
    );
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
    expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/confidence/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/trust/i)).not.toBeInTheDocument();
    expect(screen.getByText("Business impact — CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("Reliance At Risk")).toBeInTheDocument();
  });
});

describe("Conflict Lens — WOW-I3-A-R5 visual hierarchy (chain + verdict)", () => {
  it("renders exactly three supporting signals in the chain and Reliance as a visually distinct verdict, never a fourth identical badge", () => {
    const { container } = render(
      <ConflictLens
        finding={FINDING}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={{ ...EMPTY_RELIANCE, state: "RELIANCE_AT_RISK" }}
      />,
    );
    const chainSteps = container.querySelectorAll(".obs-cl-chain-step");
    expect(chainSteps).toHaveLength(3);
    const verdict = container.querySelector(".obs-cl-verdict");
    expect(verdict).not.toBeNull();
    expect(verdict?.textContent).toContain("Reliance");
    expect(verdict?.textContent).toContain("Reliance At Risk");
    // The verdict is a structurally separate element from the chain, not
    // a fourth .obs-cl-chain-step sibling.
    expect(verdict?.classList.contains("obs-cl-chain-step")).toBe(false);
  });

  it("the chain never asserts a causal claim beyond the three real, independently-computed outcomes", () => {
    render(
      <ConflictLens
        finding={FINDING}
        evidence={EMPTY_EVIDENCE}
        impact={EMPTY_IMPACT}
        businessImpact={EMPTY_BUSINESS_IMPACT}
        reliance={EMPTY_RELIANCE}
      />,
    );
    expect(
      screen.queryByText(/causes|caused by|results in|leads to/i),
    ).not.toBeInTheDocument();
  });
});
