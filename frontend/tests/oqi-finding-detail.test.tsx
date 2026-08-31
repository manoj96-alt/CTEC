import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// CDD-045 §17/§28-29 -- the flagship investigation workspace. Covers the
// bulk of the required 24-item adversarial matrix: N-source agreement/
// dissent/missingness, authority-conflict, candidate-not-truth,
// contextual criticality, IMPACT_UNKNOWN/BUSINESS_IMPACT_UNKNOWN/
// RELIANCE_UNKNOWN, specialist disagreement, synthesizer-only,
// recommendation-vs-authorization separation, stale authorization,
// remediation≠resolution, hostile source/agent content, deep linking, and
// the accessible non-graph impact fallback.
const {
  findingDetailMock,
  evidenceMock,
  ontologyImpactMock,
  businessImpactMock,
  relianceMock,
  agentInvestigationMock,
  remediationMock,
} = vi.hoisted(() => ({
  findingDetailMock: vi.fn(),
  evidenceMock: vi.fn(),
  ontologyImpactMock: vi.fn(),
  businessImpactMock: vi.fn(),
  relianceMock: vi.fn(),
  agentInvestigationMock: vi.fn(),
  remediationMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useParams: () => ({ findingId: "22222222-2222-2222-2222-222222222222" }),
}));

vi.mock("@/lib/oqi/api-client", () => ({
  oqiApi: {
    findingDetail: findingDetailMock,
    evidence: evidenceMock,
    ontologyImpact: ontologyImpactMock,
    businessImpact: businessImpactMock,
    reliance: relianceMock,
    agentInvestigation: agentInvestigationMock,
    remediation: remediationMock,
  },
  OqiApiError: class OqiApiError extends Error {
    constructor(
      public code: string,
      public status: number,
    ) {
      super(code);
    }
  },
}));

import FindingDetailPage from "@/app/quality/findings/[findingId]/page";

const BASE_FINDING = {
  finding_id: "22222222-2222-2222-2222-222222222222",
  finding_family: "OQI2",
  condition_label: "Manufacturer Part Number conflict",
  status: "OPEN",
  state_revision: 3,
  first_seen_at: "2026-01-01T00:00:00Z",
  last_seen_at: "2026-01-02T00:00:00Z",
};

const EMPTY_IMPACT = { outcome: "NO_IMPACT", direct_entity_id: null, direct_entity_type: null, propagated_path: null };
const EMPTY_BUSINESS_IMPACT = { outcome: "NO_KNOWN_BUSINESS_IMPACT", dependencies: [] };
const EMPTY_RELIANCE = { state: "RELIANCE_UNKNOWN", reason_codes: [], contributing_finding_ids: [], history: [] };
const EMPTY_AGENT = { specialists: [], recommendation: null };
const EMPTY_REMEDIATION = { case_status: null, candidate: null, recommendation: null, authorization: null, external_execution: null };

function mockAll(overrides: {
  finding?: Partial<typeof BASE_FINDING>;
  evidence?: unknown;
  impact?: unknown;
  businessImpact?: unknown;
  reliance?: unknown;
  agent?: unknown;
  remediation?: unknown;
}) {
  findingDetailMock.mockResolvedValue({ ...BASE_FINDING, ...overrides.finding });
  evidenceMock.mockResolvedValue(overrides.evidence ?? { participants: [], candidate: null });
  ontologyImpactMock.mockResolvedValue(overrides.impact ?? EMPTY_IMPACT);
  businessImpactMock.mockResolvedValue(overrides.businessImpact ?? EMPTY_BUSINESS_IMPACT);
  relianceMock.mockResolvedValue(overrides.reliance ?? EMPTY_RELIANCE);
  agentInvestigationMock.mockResolvedValue(overrides.agent ?? EMPTY_AGENT);
  remediationMock.mockResolvedValue(overrides.remediation ?? EMPTY_REMEDIATION);
}

async function renderTab(tabLabel: string) {
  render(<FindingDetailPage />);
  const tab = await screen.findByRole("button", { name: tabLabel });
  fireEvent.click(tab);
}

describe("OQI Finding Detail — evidence", () => {
  it("N-source agreement: 4 governed peers + 1 missing, candidate labeled not-truth", async () => {
    mockAll({
      evidence: {
        participants: [
          { source_system: "SAP", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "PLM", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "MES", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "Supplier Portal", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "PIM", observed_value: null, is_missing: true, is_authoritative: false, is_conflicting: false },
        ],
        candidate: { candidate_id: "c1", proposed_value: "ABC123", supporting_participant_count: 4, status: "CANDIDATE_NOT_TRUTH" },
      },
    });
    await renderTab("Evidence");

    for (const source of ["SAP", "PLM", "MES", "Supplier Portal", "PIM"]) {
      expect(screen.getByText(source)).toBeInTheDocument();
    }
    expect(screen.getByText("Missing")).toBeInTheDocument();
    expect(screen.getByText("4 governed peers observed ABC123")).toBeInTheDocument();
    expect(screen.getByText("Candidate — not established truth")).toBeInTheDocument();
    expect(screen.queryByText(/correct value/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/golden value/i)).not.toBeInTheDocument();
  });

  it("N-source dissent: agreement, dissent, and missingness all survive simultaneously", async () => {
    mockAll({
      evidence: {
        participants: [
          { source_system: "SAP", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "PLM", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "MES", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: false },
          { source_system: "Supplier Portal", observed_value: "XYZ999", is_missing: false, is_authoritative: false, is_conflicting: true },
          { source_system: "PIM", observed_value: null, is_missing: true, is_authoritative: false, is_conflicting: false },
        ],
        candidate: null,
      },
    });
    await renderTab("Evidence");

    expect(screen.getAllByText("ABC123").length).toBeGreaterThan(0);
    expect(screen.getByText("XYZ999")).toBeInTheDocument();
    expect(screen.getByText("Missing")).toBeInTheDocument();
    expect(screen.getByText("3 governed peers observed ABC123")).toBeInTheDocument();
    expect(screen.getAllByText("Conflicting").length).toBeGreaterThan(0);
  });

  it("authority conflict: majority cluster and authoritative dissent both preserved, neither declared correct", async () => {
    mockAll({
      evidence: {
        participants: [
          { source_system: "PeerA", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: true },
          { source_system: "PeerB", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: true },
          { source_system: "PeerC", observed_value: "ABC123", is_missing: false, is_authoritative: false, is_conflicting: true },
          { source_system: "System of Record", observed_value: "XYZ999", is_missing: false, is_authoritative: true, is_conflicting: true },
          { source_system: "PIM", observed_value: null, is_missing: true, is_authoritative: false, is_conflicting: false },
        ],
        candidate: null,
      },
    });
    await renderTab("Evidence");

    expect(screen.getByText("3 governed peers observed ABC123")).toBeInTheDocument();
    expect(screen.getByText("XYZ999")).toBeInTheDocument();
    expect(screen.getByText("Governed authoritative source")).toBeInTheDocument();
    expect(screen.queryByText(/is correct/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^truth$/i)).not.toBeInTheDocument();
  });

  it("hostile source content survives as inert text, never executable markup", async () => {
    mockAll({
      evidence: {
        participants: [
          {
            source_system: "SAP",
            observed_value: "<script>alert('x')</script>",
            is_missing: false,
            is_authoritative: false,
            is_conflicting: false,
          },
        ],
        candidate: null,
      },
    });
    await renderTab("Evidence");

    expect(screen.getByText("<script>alert('x')</script>")).toBeInTheDocument();
    expect(document.querySelector("script[data-injected]")).toBeNull();
    expect(document.body.innerHTML).not.toContain("<script>alert");
  });
});

describe("OQI Finding Detail — ontology impact", () => {
  it("IMPACT_UNKNOWN renders explicit unknown, never a confident empty graph", async () => {
    mockAll({ impact: { outcome: "IMPACT_UNKNOWN", direct_entity_id: null, direct_entity_type: null, propagated_path: null } });
    await renderTab("Ontology Impact");
    expect(
      screen.getByText(/ontology impact cannot currently be determined/i),
    ).toBeInTheDocument();
    expect(screen.queryByText(/no impact/i)).not.toBeInTheDocument();
  });

  it("provides an accessible non-graph path representation", async () => {
    mockAll({
      impact: {
        outcome: "IMPACTED",
        direct_entity_id: "e1",
        direct_entity_type: "MATERIAL",
        propagated_path: [{ relationship_instance_id: "r1", path_ordinal: 1, direction: "OUTBOUND" }],
      },
    });
    await renderTab("Ontology Impact");
    const details = screen.getByText("Accessible path detail").closest("details");
    expect(details).not.toBeNull();
    expect(within(details as HTMLElement).getByText(/Direct impact: MATERIAL/)).toBeInTheDocument();
    expect(within(details as HTMLElement).getByText(/Propagated step 1/)).toBeInTheDocument();
  });
});

describe("OQI Finding Detail — business impact", () => {
  it("BUSINESS_IMPACT_UNKNOWN renders explicit unknown, never zero/blank", async () => {
    mockAll({ businessImpact: { outcome: "BUSINESS_IMPACT_UNKNOWN", dependencies: [] } });
    await renderTab("Business Impact");
    expect(
      screen.getByText(/business impact cannot currently be determined/i),
    ).toBeInTheDocument();
  });

  it("contextual criticality: same subject, two dependencies, both preserved distinctly", async () => {
    mockAll({
      businessImpact: {
        outcome: "BUSINESS_IMPACT_IDENTIFIED",
        dependencies: [
          { business_process_name: "Production Planning", criticality: "CRITICAL", business_dependency_version: 1 },
          { business_process_name: "Management Reporting", criticality: "MEDIUM", business_dependency_version: 1 },
        ],
      },
    });
    await renderTab("Business Impact");
    expect(screen.getByText("Production Planning")).toBeInTheDocument();
    expect(screen.getByText("CRITICAL")).toBeInTheDocument();
    expect(screen.getByText("Management Reporting")).toBeInTheDocument();
    expect(screen.getByText("MEDIUM")).toBeInTheDocument();
  });
});

describe("OQI Finding Detail — reliance", () => {
  it("RELIANCE_UNKNOWN renders with reason codes, never as low risk", async () => {
    mockAll({
      reliance: {
        state: "RELIANCE_UNKNOWN",
        reason_codes: ["INSUFFICIENT_QUALITY_COVERAGE"],
        contributing_finding_ids: [],
        history: [],
      },
    });
    await renderTab("Explainable Reliance");
    expect(screen.getByText(/Reliance Unknown/)).toBeInTheDocument();
    expect(screen.getByText(/Insufficient quality coverage/i)).toBeInTheDocument();
    expect(screen.queryByText(/low risk/i)).not.toBeInTheDocument();
  });
});

describe("OQI Finding Detail — agent investigation", () => {
  it("specialist disagreement is preserved, never voted into a fabricated consensus", async () => {
    mockAll({
      agent: {
        specialists: [
          { role_id: "evidence-analyst", result_state: "SUCCEEDED", assessment_text: "Favors ABC123", referenced_candidate_id: "c1" },
          { role_id: "impact-analyst", result_state: "SUCCEEDED", assessment_text: "Favors XYZ999", referenced_candidate_id: "c2" },
        ],
        recommendation: { recommendation_type: "RECOMMEND_CANDIDATE", candidate_id: "c1", rationale: "Four peers agree", basis: "SPECIALIST_SUPPORTED" },
      },
    });
    await renderTab("Agent Investigation");
    expect(screen.getByText("Favors ABC123")).toBeInTheDocument();
    expect(screen.getByText("Favors XYZ999")).toBeInTheDocument();
    expect(screen.getByText("Based on specialist assessments")).toBeInTheDocument();
    expect(screen.queryByText(/consensus/i)).not.toBeInTheDocument();
  });

  it("synthesizer-only basis is distinguished from specialist-supported, from the API field alone", async () => {
    mockAll({
      agent: {
        specialists: [],
        recommendation: { recommendation_type: "RECOMMEND_CANDIDATE", candidate_id: "c1", rationale: "synthesizer reasoning", basis: "SYNTHESIZER_ONLY" },
      },
    });
    await renderTab("Agent Investigation");
    expect(
      screen.getByText("Specialist assessments unavailable — synthesizer reasoning only"),
    ).toBeInTheDocument();
  });

  it("hostile agent text survives as inert text", async () => {
    mockAll({
      agent: {
        specialists: [
          { role_id: "evidence-analyst", result_state: "SUCCEEDED", assessment_text: "<img src=x onerror=alert(1)>", referenced_candidate_id: null },
        ],
        recommendation: null,
      },
    });
    await renderTab("Agent Investigation");
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelectorAll("img[onerror]").length).toBe(0);
  });
});

describe("OQI Finding Detail — remediation, authorization, resolution", () => {
  it("recommendation without authorization never looks approved", async () => {
    mockAll({
      remediation: {
        case_status: "PENDING",
        candidate: { candidate_id: "c1", proposed_value: "ABC123", status: "CANDIDATE_NOT_TRUTH" },
        recommendation: { recommendation_type: "RECOMMEND_CANDIDATE", candidate_id: "c1", rationale: "peers agree", basis: "SPECIALIST_SUPPORTED" },
        authorization: null,
        external_execution: null,
      },
    });
    await renderTab("Remediation");
    expect(screen.getByText("RECOMMEND_CANDIDATE")).toBeInTheDocument();
    expect(screen.getByText("No human authorization exists for this Finding.")).toBeInTheDocument();
    expect(screen.queryByText(/authorized/i)).not.toBeInTheDocument();
  });

  it("recommendation and a separately-added authorization remain distinct concepts", async () => {
    mockAll({
      remediation: {
        case_status: "AUTHORIZED",
        candidate: { candidate_id: "c1", proposed_value: "ABC123", status: "CANDIDATE_NOT_TRUTH" },
        recommendation: { recommendation_type: "RECOMMEND_CANDIDATE", candidate_id: "c1", rationale: "peers agree", basis: "SPECIALIST_SUPPORTED" },
        authorization: {
          principal: "steward@example.com",
          decided_on: "2026-01-03T00:00:00Z",
          instruction: "Correct Manufacturer Part Number to ABC123",
          authorized_against_state_revision: 3,
          is_stale: false,
          status: "APPROVED",
        },
        external_execution: null,
      },
    });
    await renderTab("Remediation");
    expect(screen.getByText("RECOMMEND_CANDIDATE")).toBeInTheDocument();
    expect(screen.getByText(/Authorized by steward@example.com/)).toBeInTheDocument();
    expect(screen.queryByText(/remediated/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^fixed$/i)).not.toBeInTheDocument();
  });

  it("stale authorization is visibly non-actionable", async () => {
    mockAll({
      remediation: {
        case_status: "AUTHORIZED",
        candidate: null,
        recommendation: null,
        authorization: {
          principal: "steward@example.com",
          decided_on: "2026-01-01T00:00:00Z",
          instruction: "Correct value",
          authorized_against_state_revision: 1,
          is_stale: true,
          status: "APPROVED",
        },
        external_execution: null,
      },
    });
    await renderTab("Remediation");
    expect(screen.getByText(/Stale/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply|execute|use authorization/i })).not.toBeInTheDocument();
  });

  it("external remediation reported keeps the Finding OPEN, never says Resolved", async () => {
    mockAll({
      finding: { status: "OPEN" },
      remediation: {
        case_status: "EXTERNAL_EXECUTION_REPORTED",
        candidate: null,
        recommendation: null,
        authorization: null,
        external_execution: { reported_at: "2026-01-04T00:00:00Z" },
      },
    });
    render(<FindingDetailPage />);
    expect(await screen.findByText(/Status: OPEN/)).toBeInTheDocument();
    const tab = screen.getByRole("button", { name: "Remediation" });
    fireEvent.click(tab);
    expect(
      screen.getByText("External remediation reported — awaiting fresh evidence"),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^resolved$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/quality restored/i)).not.toBeInTheDocument();
  });

  it("Finding only reads Resolved after real evaluator resolution is reported by the API", async () => {
    mockAll({ finding: { status: "RESOLVED" } });
    render(<FindingDetailPage />);
    expect(
      await screen.findByText(/Resolved — confirmed by fresh evidence and re-evaluation/),
    ).toBeInTheDocument();
  });
});

describe("OQI Finding Detail — deep linking", () => {
  it("loads the Finding identified by the route parameter", async () => {
    mockAll({});
    render(<FindingDetailPage />);
    await screen.findByText(BASE_FINDING.condition_label);
    expect(findingDetailMock).toHaveBeenCalledWith("22222222-2222-2222-2222-222222222222");
  });
});
