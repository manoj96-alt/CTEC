import { render, screen } from "@testing-library/react";
import { RecommendationPanel } from "@/components/supplier-risk/recommendation-panel";
import { StatusSummary } from "@/components/supplier-risk/status-summary";
const result = {
  execution_identifier: "e",
  governance_standing: "CONDITIONALLY_APPROVED",
  recommendation: "QUALIFY_SECOND_SOURCE",
  actionable: false,
  completed_at: new Date().toISOString(),
  produced_record_references: ["record"],
  terminal_classification: "CONDITIONALLY_APPROVED" as const,
  safe_diagnostic_code: null,
  conditions: ["Verify capacity"],
  verified_conditions: [],
  safe_business_explanation: "Policy evaluation complete",
  evidence_references: ["evidence"],
  provenance_references: ["source"],
  policy_reference: "policy",
  policy_version: "1",
  policy_rule: "rule",
  decision_reference: "decision",
  contract_version: "PAS-001-v1.1" as const,
};
test("renders recommendation without hiding unverified conditions", () => {
  render(<RecommendationPanel result={result} />);
  expect(screen.getByText("QUALIFY_SECOND_SOURCE")).toBeInTheDocument();
  expect(screen.getByText(/Not verified/)).toBeInTheDocument();
  expect(screen.getByText("evidence")).toBeInTheDocument();
});
test("renders empty optional references without inventing content", () => {
  render(
    <RecommendationPanel
      result={{
        ...result,
        conditions: [],
        evidence_references: [],
        provenance_references: [],
        produced_record_references: [],
        safe_business_explanation: null,
        policy_reference: null,
      }}
    />,
  );
  expect(
    screen.getAllByText("No permitted references were returned."),
  ).toHaveLength(3);
});
test("renders the actionable state when the recommendation is actionable", () => {
  render(<RecommendationPanel result={{ ...result, actionable: true }} />);
  expect(screen.getByText(/Actionable/)).toBeInTheDocument();
});
test("separates execution and business status", () => {
  render(
    <StatusSummary execution="Completed" outcome="REJECTED" stage="GRM" />,
  );
  expect(screen.getByText("Completed")).toBeInTheDocument();
  expect(screen.getByText("rejected")).toBeInTheDocument();
});
