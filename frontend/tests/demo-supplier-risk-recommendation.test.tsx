import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { RecommendationStage } from "@/app/demo/supplier-risk/_components/recommendation-stage";
import {
  DecisionHistory,
  type DecisionHistoryEntry,
} from "@/app/demo/supplier-risk/_components/decision-history";
import { evaluateDecision } from "@/lib/demo/decision-rules";
import { buildTestScenarioFacts } from "./helpers/demo-fixture";

test("shows the recommendation summary and key terms", () => {
  const evaluation = evaluateDecision(buildTestScenarioFacts());
  render(
    <RecommendationStage
      evaluation={evaluation}
      onDecision={() => {}}
      hasDecided={false}
    />,
  );

  expect(
    screen.getByText(
      /Activate Nova Energy Systems as a secondary supplier for 40%/,
    ),
  ).toBeInTheDocument();
  expect(screen.getByText("21 days")).toBeInTheDocument();
});

test("approving calls onDecision with Approved and the entered comment", () => {
  const evaluation = evaluateDecision(buildTestScenarioFacts());
  const onDecision = vi.fn();
  render(
    <RecommendationStage
      evaluation={evaluation}
      onDecision={onDecision}
      hasDecided={false}
    />,
  );

  fireEvent.change(screen.getByLabelText(/Decision comment/), {
    target: { value: "Looks good, proceed." },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Approve Recommendation" }),
  );

  expect(onDecision).toHaveBeenCalledWith("Approved", "Looks good, proceed.");
});

test("rejecting calls onDecision with Rejected", () => {
  const evaluation = evaluateDecision(buildTestScenarioFacts());
  const onDecision = vi.fn();
  render(
    <RecommendationStage
      evaluation={evaluation}
      onDecision={onDecision}
      hasDecided={false}
    />,
  );

  fireEvent.click(
    screen.getByRole("button", { name: "Reject Recommendation" }),
  );

  expect(onDecision).toHaveBeenCalledWith("Rejected", "");
});

test("BUG-001 regression: once hasDecided is true, both buttons are disabled", () => {
  const evaluation = evaluateDecision(buildTestScenarioFacts());
  const onDecision = vi.fn();
  render(
    <RecommendationStage
      evaluation={evaluation}
      onDecision={onDecision}
      hasDecided={true}
    />,
  );

  const approveButton = screen.getByRole("button", {
    name: "Approve Recommendation",
  });
  const rejectButton = screen.getByRole("button", {
    name: "Reject Recommendation",
  });
  expect(approveButton).toBeDisabled();
  expect(rejectButton).toBeDisabled();

  fireEvent.click(approveButton);
  fireEvent.click(rejectButton);
  expect(onDecision).not.toHaveBeenCalled();
});

test("decision history renders entries as an append-only log", () => {
  const entries: DecisionHistoryEntry[] = [
    {
      id: "2",
      decision: "Rejected",
      user: "Demo Reviewer",
      timestamp: "1/1/2026, 10:05:00 AM",
      recommendationSummary: "Activate Nova Energy Systems...",
      allocationPct: 40,
      comment: "Need more evidence.",
      evidenceReference: "4 source facts, 5 source rows",
    },
    {
      id: "1",
      decision: "Approved",
      user: "Demo Reviewer",
      timestamp: "1/1/2026, 10:00:00 AM",
      recommendationSummary: "Activate Nova Energy Systems...",
      allocationPct: 40,
      comment: "",
      evidenceReference: "4 source facts, 5 source rows",
    },
  ];
  render(<DecisionHistory entries={entries} />);

  const history = screen.getByTestId("decision-history");
  expect(history).toHaveTextContent("Rejected");
  expect(history).toHaveTextContent("Approved");
  expect(history).toHaveTextContent("Need more evidence.");
});

test("decision history renders nothing when there are no entries yet", () => {
  const { container } = render(<DecisionHistory entries={[]} />);
  expect(container).toBeEmptyDOMElement();
});
