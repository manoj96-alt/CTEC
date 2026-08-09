import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { RetryDialog } from "@/components/supplier-risk/retry-dialog";
import { ReplayDialog } from "@/components/supplier-risk/replay-dialog";
vi.mock("@/lib/supplier-risk/api-client", () => ({
  supplierRiskApi: {
    retry: vi.fn().mockResolvedValue({}),
    replay: vi.fn().mockResolvedValue({}),
  },
}));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});
test("retry is server eligibility controlled", () => {
  render(
    <RetryDialog
      logicalId="logical"
      eligibility={{
        eligible: false,
        governing_attempt_identifier: "attempt",
        reason_code: "ATTEMPT_NOT_FAILED",
        safe_constraint: null,
        revision: 1,
        action: null,
      }}
      onAccepted={vi.fn()}
    />,
  );
  expect(screen.getByRole("button", { name: "Request retry" })).toBeDisabled();
});
test("eligible retry submits one revision-bound request", async () => {
  const accepted = vi.fn();
  render(
    <RetryDialog
      logicalId="logical"
      eligibility={{
        eligible: true,
        governing_attempt_identifier: "attempt",
        reason_code: "RETRY_ELIGIBLE",
        safe_constraint: null,
        revision: 3,
        action: "/retry",
      }}
      onAccepted={accepted}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Request retry" }));
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Evidence corrected" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Confirm retry" }));
  await waitFor(() => expect(accepted).toHaveBeenCalled());
});
test("replay displays only server-authorized options", () => {
  render(
    <ReplayDialog
      logicalId="logical"
      options={[
        {
          option_reference: "option",
          source_attempt_identifier: "attempt",
          stage_label: "ERM",
          checkpoint_at: "2026-01-01T00:00:00Z",
          eligible: true,
          reason_code: "REPLAY_ELIGIBLE",
          revision: 2,
        },
      ]}
      onAccepted={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  expect(screen.getByLabelText("Server-authorized checkpoint")).toHaveValue(
    "option",
  );
  expect(screen.getByText(/will not be overwritten/)).toBeInTheDocument();
});
test("confirmed replay submits only the server option", async () => {
  const accepted = vi.fn();
  render(
    <ReplayDialog
      logicalId="logical"
      options={[
        {
          option_reference: "option",
          source_attempt_identifier: "attempt",
          stage_label: "ERM",
          checkpoint_at: "2026-01-01T00:00:00Z",
          eligible: true,
          reason_code: "REPLAY_ELIGIBLE",
          revision: 2,
        },
      ]}
      onAccepted={accepted}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Privileged replay" }));
  fireEvent.change(screen.getByLabelText("Reason"), {
    target: { value: "Authorized recovery" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm privileged replay" }),
  );
  await waitFor(() => expect(accepted).toHaveBeenCalled());
});
