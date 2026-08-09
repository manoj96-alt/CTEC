import { render, screen } from "@testing-library/react";
import { AssessmentTable } from "@/components/supplier-risk/assessment-table";
import { AttemptHistory } from "@/components/supplier-risk/attempt-history";
import { StageTimeline } from "@/components/supplier-risk/stage-timeline";
test("renders empty and populated work queues", () => {
  const { rerender } = render(<AssessmentTable items={[]} />);
  expect(screen.getByText("No assessments yet")).toBeInTheDocument();
  rerender(
    <AssessmentTable
      items={[
        {
          logical_execution_identifier: "logical",
          current_execution_identifier: "attempt",
          subject_summary: "supplier-risk",
          submitted_at: "2026-01-01T00:00:00Z",
          execution_status: "Completed",
          current_or_terminal_stage: "GRM",
          terminal_classification: "APPROVED",
          retry_eligible: false,
          replay_eligible: true,
          last_updated_at: "2026-01-01T00:00:00Z",
          revision: 1,
        },
      ]}
    />,
  );
  expect(screen.getByRole("link", { name: /supplier-risk/ })).toHaveAttribute(
    "href",
    "/supplier-risk/executions/logical",
  );
});
test("renders attempts and stages accessibly", () => {
  render(
    <>
      <AttemptHistory
        logicalId="logical"
        attempts={[
          {
            execution_identifier: "attempt",
            logical_execution_identifier: "logical",
            state: "Failed",
            admitted_at: "2026-01-01T00:00:00Z",
            completed_at: "2026-01-01T00:01:00Z",
            revision: 2,
          },
        ]}
      />
      <StageTimeline
        stages={[
          {
            stage_identifier: "stage",
            stage_name: "ERM",
            stage_ordinal: 0,
            status: "COMMITTED",
            started_at: "2026-01-01T00:00:00Z",
            completed_at: "2026-01-01T00:01:00Z",
            safe_failure_code: null,
            produced_record_references: [],
          },
        ]}
      />
    </>,
  );
  expect(screen.getByRole("link", { name: "Attempt 1" })).toBeInTheDocument();
  expect(
    screen.getByRole("list", { name: "Capability stage progress" }),
  ).toBeInTheDocument();
});
