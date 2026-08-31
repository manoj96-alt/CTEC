import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

// CDD-045 §29 -- mechanical enforcement of the frozen UI Truth Table.
// For every governed state, render the exact component that owns that
// state and assert (a) the allowed phrase appears and (b) none of the
// governed "must not say" phrases for that row appear anywhere in the
// rendered output. Mirrors gate-x-honesty.test.tsx's own per-state
// enforcement pattern rather than a single ungoverned whole-app grep,
// which would produce false positives across unrelated states (e.g. the
// legitimate NO_IMPACT copy would otherwise collide with the IMPACT_UNKNOWN
// prohibition).
import { ReliancePanel } from "@/app/quality/findings/[findingId]/_components/reliance-panel";
import { OntologyImpactPanel } from "@/app/quality/findings/[findingId]/_components/ontology-impact-panel";
import { BusinessImpactPanel } from "@/app/quality/findings/[findingId]/_components/business-impact-panel";
import { EvidencePanel } from "@/app/quality/findings/[findingId]/_components/evidence-panel";
import { AgentInvestigationPanel } from "@/app/quality/findings/[findingId]/_components/agent-investigation-panel";
import { RemediationPanel } from "@/app/quality/findings/[findingId]/_components/remediation-panel";

function assertForbidden(container: HTMLElement, forbidden: RegExp[]) {
  for (const pattern of forbidden) {
    expect(container.textContent).not.toMatch(pattern);
  }
}

describe("CDD-045 §29 UI Truth Table — mechanical enforcement", () => {
  it("RELIANCE_SUPPORTED: may say Reliance Supported, must not say Trusted/100% correct/Verified true", () => {
    const { container } = render(
      <ReliancePanel
        reliance={{
          state: "RELIANCE_SUPPORTED",
          reason_codes: [],
          contributing_finding_ids: [],
          history: [],
        }}
      />,
    );
    expect(screen.getByText("Reliance Supported")).toBeInTheDocument();
    assertForbidden(container, [
      /\btrusted\b/i,
      /100% correct/i,
      /verified true/i,
    ]);
  });

  it("RELIANCE_AT_RISK: may say Reliance At Risk, must not say False/Wrong/Broken", () => {
    const { container } = render(
      <ReliancePanel
        reliance={{
          state: "RELIANCE_AT_RISK",
          reason_codes: [],
          contributing_finding_ids: [],
          history: [],
        }}
      />,
    );
    expect(screen.getByText("Reliance At Risk")).toBeInTheDocument();
    assertForbidden(container, [/\bfalse\b/i, /\bwrong\b/i, /\bbroken\b/i]);
  });

  it("RELIANCE_UNKNOWN: may say insufficient evidence to assess, must not say Low Risk", () => {
    const { container } = render(
      <ReliancePanel
        reliance={{
          state: "RELIANCE_UNKNOWN",
          reason_codes: [],
          contributing_finding_ids: [],
          history: [],
        }}
      />,
    );
    expect(
      screen.getByText(/insufficient evidence to assess/i),
    ).toBeInTheDocument();
    assertForbidden(container, [/low risk/i]);
  });

  it("IMPACT_UNKNOWN: may say cannot currently be determined, must not say No impact/Low impact", () => {
    const { container } = render(
      <OntologyImpactPanel
        impact={{
          outcome: "IMPACT_UNKNOWN",
          direct_entity_id: null,
          direct_entity_type: null,
          propagated_path: null,
        }}
      />,
    );
    expect(
      screen.getByText(/ontology impact cannot currently be determined/i),
    ).toBeInTheDocument();
    assertForbidden(container, [/\bno impact\b/i, /\blow impact\b/i]);
  });

  it("NO_KNOWN_BUSINESS_IMPACT: may say No known business impact, must not say No business impact exists/Safe", () => {
    const { container } = render(
      <BusinessImpactPanel
        impact={{ outcome: "NO_KNOWN_BUSINESS_IMPACT", dependencies: [] }}
      />,
    );
    expect(screen.getByText(/no known business impact/i)).toBeInTheDocument();
    assertForbidden(container, [/no business impact exists/i, /\bsafe\b/i]);
  });

  it("BUSINESS_IMPACT_UNKNOWN: may say cannot currently be determined, must not say 0 impact / be blank", () => {
    const { container } = render(
      <BusinessImpactPanel
        impact={{ outcome: "BUSINESS_IMPACT_UNKNOWN", dependencies: [] }}
      />,
    );
    expect(
      screen.getByText(/business impact cannot currently be determined/i),
    ).toBeInTheDocument();
    assertForbidden(container, [/0 impact/i]);
    expect(container.textContent?.trim().length).toBeGreaterThan(0);
  });

  it("N governed peers observed value: may say observed, must not say is correct", () => {
    const { container } = render(
      <EvidencePanel
        evidence={{
          participants: [
            {
              source_system: "SAP",
              observed_value: "ABC123",
              is_missing: false,
              is_authoritative: false,
              is_conflicting: false,
            },
            {
              source_system: "PLM",
              observed_value: "ABC123",
              is_missing: false,
              is_authoritative: false,
              is_conflicting: false,
            },
          ],
          candidate: null,
        }}
      />,
    );
    expect(
      screen.getByText("2 governed peers observed ABC123"),
    ).toBeInTheDocument();
    assertForbidden(container, [/is correct/i]);
  });

  it("Source marked authoritative: may say Governed authoritative source, must not say Truth", () => {
    const { container } = render(
      <EvidencePanel
        evidence={{
          participants: [
            {
              source_system: "System of Record",
              observed_value: "ABC123",
              is_missing: false,
              is_authoritative: true,
              is_conflicting: false,
            },
          ],
          candidate: null,
        }}
      />,
    );
    expect(
      screen.getByText("Governed authoritative source"),
    ).toBeInTheDocument();
    assertForbidden(container, [/\btruth\b/i]);
  });

  it("RemediationCandidate exists: may say Candidate — not established truth, must not say Correct value / Golden value", () => {
    const { container } = render(
      <EvidencePanel
        evidence={{
          participants: [],
          candidate: {
            candidate_id: "c1",
            proposed_value: "ABC123",
            supporting_participant_count: 4,
            status: "CANDIDATE_NOT_TRUTH",
          },
        }}
      />,
    );
    expect(
      screen.getByText("Candidate — not established truth"),
    ).toBeInTheDocument();
    assertForbidden(container, [/correct value/i, /golden value/i]);
  });

  it("AgentAssessment: may say Specialist Assessment, must not say Fact", () => {
    const { container } = render(
      <AgentInvestigationPanel
        investigation={{
          specialists: [
            {
              role_id: "evidence-analyst",
              result_state: "SUCCEEDED",
              assessment_text: "Analysis text",
              referenced_candidate_id: null,
            },
          ],
          recommendation: null,
        }}
      />,
    );
    expect(screen.getByText("Specialist Assessment")).toBeInTheDocument();
    assertForbidden(container, [/\bfact\b/i]);
  });

  it("RECOMMEND_CANDIDATE: may say Recommendation, must not say Decision", () => {
    const { container } = render(
      <RemediationPanel
        remediation={{
          case_status: "PENDING",
          candidate: null,
          recommendation: {
            recommendation_type: "RECOMMEND_CANDIDATE",
            candidate_id: "c1",
            rationale: "peers agree",
            basis: "SPECIALIST_SUPPORTED",
          },
          authorization: null,
          external_execution: null,
        }}
      />,
    );
    expect(screen.getByText("Agent Recommendation")).toBeInTheDocument();
    assertForbidden(container, [/\bdecision\b/i]);
  });

  it("RemediationAuthorization decided: may say Authorized by, must not say Remediated/Fixed", () => {
    const { container } = render(
      <RemediationPanel
        remediation={{
          case_status: "AUTHORIZED",
          candidate: null,
          recommendation: null,
          authorization: {
            principal: "steward@example.com",
            decided_on: "2026-01-01T00:00:00Z",
            instruction: "Correct value",
            authorized_against_state_revision: 1,
            is_stale: false,
            status: "APPROVED",
          },
          external_execution: null,
        }}
      />,
    );
    expect(
      screen.getByText(/Authorized by steward@example.com/),
    ).toBeInTheDocument();
    assertForbidden(container, [/\bremediated\b/i, /\bfixed\b/i]);
  });

  it("External remediation reported: may say awaiting fresh evidence, must not say Finding resolved/Quality restored", () => {
    const { container } = render(
      <RemediationPanel
        remediation={{
          case_status: "EXTERNAL_EXECUTION_REPORTED",
          candidate: null,
          recommendation: null,
          authorization: null,
          external_execution: { reported_at: "2026-01-01T00:00:00Z" },
        }}
      />,
    );
    expect(
      screen.getByText(
        "External remediation reported — awaiting fresh evidence",
      ),
    ).toBeInTheDocument();
    assertForbidden(container, [/finding resolved/i, /quality restored/i]);
  });

  it("NOT_EVALUABLE reason code renders as insufficient evidence, never Passed", () => {
    const { container } = render(
      <ReliancePanel
        reliance={{
          state: "RELIANCE_UNKNOWN",
          reason_codes: ["INSUFFICIENT_QUALITY_COVERAGE"],
          contributing_finding_ids: [],
          history: [],
        }}
      />,
    );
    expect(
      screen.getByText(/insufficient quality coverage/i),
    ).toBeInTheDocument();
    assertForbidden(container, [/\bpassed\b/i]);
  });
});
